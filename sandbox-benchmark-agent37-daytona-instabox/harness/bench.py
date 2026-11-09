"""One job = one fresh sandbox on one provider: create -> probes -> delete. Same job spec on both providers.
Usage: bench.py <jobs.json> <outdir> [--a37-workers N] [--dt-workers N] [--ib-workers N]
Job: {kind: lifecycle|clone|mem|disk, provider, shape, type, rep, repo?, mode?}
Env: SPEND_CAP_A37 / SPEND_CAP_DT / SPEND_CAP_IB (USD, modeled from sandbox life x published rate; new jobs stop at the cap). STOP file in outdir stops new jobs.
Resumable: skips jobs whose result file exists. Every failure is kept (result file with 'error')."""

import argparse
import glob
import json
import os
import sys
import threading
import time
import traceback

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import providers as P

PROBE = open(f"{H}/probe.py", "rb").read()


def fname(outdir, j):
    return f"{outdir}/{j['provider']}__{j['type']}__{j['shape']}__{j['kind']}{('__' + j['repo'].split('/')[1] + '-' + j['mode']) if j['kind'] == 'clone' else ''}__r{j['rep']}.json"


def run_probe(pv, b, args, timeout=1500):
    """Long probes run detached inside the sandbox and are polled: a synchronous exec that stays silent for minutes gets its
    HTTP connection dropped at ~270 s on both providers, and the Daytona SDK then re-sends the command."""
    t = time.time()
    n = f"p{int(t * 1000) % 10**9}"
    pv.exec(
        b,
        f"cd {b.home} && nohup sh -c 'HOME_DIR={b.home} python3 {b.home}/probe.py {args} > /tmp/{n}.out 2>&1; echo $? > /tmp/{n}.rc' > /dev/null 2>&1 &",
    )
    polls = 0
    perr = []
    while time.time() - t < timeout:
        time.sleep(5 if time.time() - t < 60 else 10)
        polls += 1
        try:
            rc, out = pv.exec(b, f"cat /tmp/{n}.rc 2>/dev/null && cat /tmp/{n}.out", timeout=60)
        except Exception as e:
            perr.append(str(e)[:160])
            continue
        if rc == 0 and out.strip():
            code = out.split("\n", 1)[0].strip()
            body = out.split("\n", 1)[1] if "\n" in out else ""
            js = [l for l in body.splitlines() if l.startswith('{"probe"')]
            return dict(
                rc=int(code) if code.lstrip("-").isdigit() else code,
                wall_s=round(time.time() - t, 2),
                out=json.loads(js[-1]) if js else None,
                tail=None if js else body[-600:],
                polls=polls,
                poll_errors=perr[-5:] or None,
            )
    return dict(
        rc="timeout",
        wall_s=round(time.time() - t, 2),
        out=None,
        tail=None,
        polls=polls,
        poll_errors=perr[-5:] or None,
    )


def job(pv, j, outdir):
    path = fname(outdir, j)
    if os.path.exists(path):
        return "skip", 0
    R = dict(job=j, start=time.time())
    b = None
    t0 = time.time()
    tag = os.path.basename(path)[:-5]
    try:
        try:
            b, cs = pv.create(j["shape"], j["type"], tag)
        except P.ProviderError as e:
            R["create_error"] = {"http": e.http, "code": e.code, "msg": str(e)[:300]}
            raise
        R["id"] = b.id
        R["create_s"] = round(cs, 2)
        if pv.name == "instabox":
            R["create_post_s"] = getattr(b, "post_s", None)
            R["create_rl_wait_s"] = getattr(b, "wait_s", None)
            R["create_s_excludes_rl_wait"] = True
            R["retries_so_far"] = dict(pv.retries)
        t = time.time()
        rc, out = pv.exec(b, "true")
        R["first_cmd_s"] = round(time.time() - t, 3)
        R["ready_s"] = round(time.time() - t0, 2)
        rtt = []
        for _ in range(10):
            t = time.time()
            pv.exec(b, "true")
            rtt.append(round(time.time() - t, 3))
        R["exec_rtt_s"] = rtt
        pv.upload(b, PROBE, f"{b.home}/probe.py")
        R["sysinfo"] = run_probe(pv, b, "sysinfo")
        c, m, d = P.SHAPES[j["shape"]]
        k = j["kind"]
        if pv.name == "instabox":
            d = 20  # fixed 20 GiB /data on every InstaBox size (others: 8 / 10)
        if k == "lifecycle":
            R["cpu"] = run_probe(pv, b, f"cpu 180 {c}")
        elif k == "clone":
            R["clone"] = run_probe(pv, b, f"clone {j['repo']} {j['mode']} {b.home}/repo")
        elif k == "mem":
            try:
                R["mem"] = run_probe(pv, b, f"mem {m * 1024 * 2}", timeout=420)
            except Exception as e:
                R["mem"] = {"exec_error": str(e)[:300]}
            time.sleep(5)
            try:
                rc, out = pv.exec(
                    b,
                    "cat /tmp/mem.prog | tail -1; cat /sys/fs/cgroup/memory.events 2>/dev/null; uptime",
                )
                R["mem_after"] = {"alive": True, "out": out[-500:]}
            except Exception as e:
                R["mem_after"] = {"alive": False, "err": str(e)[:300]}
        elif k == "disk":
            R["disk_home"] = run_probe(pv, b, f"disk {b.home}/fill {d * 2}")
            R["disk_root"] = run_probe(
                pv, b, "disk /var/tmp/fill 12"
            )  # OS layer (Agent37: separate 10 GB layer; Daytona: same volume)
        if pv.name == "instabox":
            try:
                R["machine_end"] = pv.get(f"/v1/machines/{b.id}")
                R["machine_end"].pop("metadata", None)
            except Exception as e:
                R["machine_end_err"] = str(e)[:200]
        if pv.name == "agent37":
            try:
                R["metrics"] = pv.metrics(b)
            except Exception as e:
                R["metrics_err"] = str(e)[:200]
    except Exception as e:
        R["error"] = traceback.format_exc()[-1500:]
    finally:
        if b is not None:
            td = time.time()
            R["deleted"] = pv.delete(b, tag)
            R["delete_s"] = round(time.time() - td, 2)
        R["life_s"] = round(time.time() - t0, 2)
    json.dump(R, open(path, "w"))
    return ("ERR" if "error" in R else "ok"), (R["life_s"] if b else 0) * P.rate_per_s(
        j["provider"], j["shape"], j["type"]
    )


def spent(outdir, prov):
    s = 0.0
    for f in glob.glob(f"{outdir}/{prov}__*.json"):
        try:
            r = json.load(open(f))
            j = r["job"]
            s += (
                (r.get("life_s") or 0) * P.rate_per_s(prov, j["shape"], j["type"])
                if r.get("id")
                else 0
            )
        except Exception:
            pass
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("outdir")
    ap.add_argument("--a37-workers", type=int, default=10)
    ap.add_argument("--dt-workers", type=int, default=50)
    ap.add_argument("--ib-workers", type=int, default=50)
    a = ap.parse_args()
    jobs = json.load(open(a.jobs))
    os.makedirs(a.outdir, exist_ok=True)
    CAP = {
        "agent37": float(os.environ.get("SPEND_CAP_A37", "5")),
        "daytona": float(os.environ.get("SPEND_CAP_DT", "10")),
        "instabox": float(os.environ.get("SPEND_CAP_IB", "10")),
    }
    L = threading.Lock()
    cnt = {}
    S = {p: spent(a.outdir, p) for p in CAP}
    stop = f"{a.outdir}/STOP"

    def runq(prov, W):
        pv = P.provider(prov)
        Q = [j for j in jobs if j["provider"] == prov and not os.path.exists(fname(a.outdir, j))]

        def w():
            while not os.path.exists(stop):
                with L:
                    if not Q or S[prov] >= CAP[prov]:
                        return
                    j = Q.pop(0)
                try:
                    res, c = job(pv, j, a.outdir)
                except Exception as e:
                    res, c = "EXC " + str(e)[:80], 0
                with L:
                    S[prov] += c
                    cnt[res] = cnt.get(res, 0) + 1
                    print(
                        time.strftime("%H:%M:%S"),
                        prov,
                        j["type"],
                        j["shape"],
                        j["kind"],
                        j.get("repo", ""),
                        j.get("mode", ""),
                        j["rep"],
                        res,
                        f"${S[prov]:.3f}",
                        flush=True,
                    )

        ts = [threading.Thread(target=w, daemon=True) for _ in range(W)]
        [t.start() for t in ts]
        return ts

    ths = []
    if any(j["provider"] == "agent37" for j in jobs):
        ths += runq("agent37", a.a37_workers)
    if any(j["provider"] == "daytona" for j in jobs):
        ths += runq("daytona", a.dt_workers)
    if any(j["provider"] == "instabox" for j in jobs):
        ths += runq("instabox", a.ib_workers)
    [t.join() for t in ths]
    print("DONE", cnt, {k: round(v, 3) for k, v in S.items()}, flush=True)
