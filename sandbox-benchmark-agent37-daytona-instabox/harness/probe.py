"""Runs INSIDE the sandbox (python3 stdlib only). Prints one JSON line per probe.
probe.py sysinfo
probe.py cpu SECONDS NPROC           sustained all-core load; per-5s work rate per process (throttling shows as a falling rate)
probe.py mem MAX_MB             allocate+touch 128 MB steps until failure or MAX_MB; progress to /tmp/mem.prog (survives our death)
probe.py disk DIR MAX_GB        write 256 MB files until ENOSPC or MAX_GB
probe.py clone REPO MODE DIR    git clone (full|shallow); wall time, bytes received, disk used"""

import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time


def rd(p):
    try:
        return open(p).read().strip()
    except Exception:
        return None


def netrx():
    tot = 0
    for l in open("/proc/net/dev").readlines()[2:]:
        n, v = l.split(":", 1)
        if n.strip() != "lo":
            tot += int(v.split()[0])
    return tot


def du(p):
    try:
        return int(
            subprocess.run(["du", "-sb", p], capture_output=True, text=True).stdout.split()[0]
        )
    except Exception:
        return None


def sysinfo():
    mi = {l.split(":")[0]: l.split(":")[1].strip() for l in open("/proc/meminfo")}
    st = os.statvfs(os.environ.get("HOME_DIR", "/"))
    return dict(
        nproc=os.cpu_count(),
        affinity=len(os.sched_getaffinity(0)),
        mem_total_kb=int(mi["MemTotal"].split()[0]),
        cg_mem_max=rd("/sys/fs/cgroup/memory.max"),
        cg_cpu_max=rd("/sys/fs/cgroup/cpu.max"),
        kernel=os.uname().release,
        cpu_model=next(
            (l.split(":")[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")),
            None,
        ),
        home_free_b=st.f_bavail * st.f_frsize,
        home_total_b=st.f_blocks * st.f_frsize,
        root_free_b=(lambda s: s.f_bavail * s.f_frsize)(os.statvfs("/")),
        dmesg_ok=subprocess.run("dmesg >/dev/null 2>&1", shell=True).returncode == 0,
        git=subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip(),
    )


def _burn(sec, q):
    end = time.time() + sec
    w = []
    t0 = time.time()
    n = 0
    h = b"x" * 64
    while time.time() < end:
        for _ in range(2000):
            h = hashlib.sha256(h).digest()
        n += 2000
        if time.time() - t0 >= 5:
            w.append(round(n / (time.time() - t0)))
            n = 0
            t0 = time.time()
    q.put(w)


def cpu(sec, k=None):
    k = int(k or os.cpu_count())
    q = mp.Queue()
    ps = [mp.Process(target=_burn, args=(sec, q)) for _ in range(k)]
    t = time.time()
    [p.start() for p in ps]
    res = [q.get() for _ in ps]
    [p.join() for p in ps]
    per = [sum(r[i] for r in res if i < len(r)) for i in range(min(len(r) for r in res))]
    st = rd("/sys/fs/cgroup/cpu.stat")
    return dict(
        procs=k,
        seconds=round(time.time() - t, 1),
        window_rate=per,
        first=per[0] if per else None,
        last=per[-1] if per else None,
        min=min(per) if per else None,
        max=max(per) if per else None,
        cg_cpu_stat=st,
    )


def mem(maxmb):
    blocks = []
    step = 128
    prog = "/tmp/mem.prog"
    t = time.time()
    with open(prog, "w") as f:
        try:
            while len(blocks) * step < maxmb:
                b = bytearray(step << 20)
                for i in range(0, len(b), 4096):
                    b[i] = 1
                blocks.append(b)
                f.write(f"{len(blocks) * step} {round(time.time() - t, 2)}\n")
                f.flush()
                os.fsync(f.fileno())
            out = "reached_max"
        except MemoryError:
            out = "MemoryError"
    return dict(
        result=out,
        allocated_mb=len(blocks) * step,
        seconds=round(time.time() - t, 1),
        cg_events=rd("/sys/fs/cgroup/memory.events"),
        cg_peak=rd("/sys/fs/cgroup/memory.peak"),
    )


def disk(d, maxgb):
    os.makedirs(d, exist_ok=True)
    n = 0
    t = time.time()
    err = None
    buf = os.urandom(1 << 20)
    try:
        while n < maxgb * 4:
            with open(f"{d}/fill{n}", "wb") as f:
                for _ in range(256):
                    f.write(buf)
                f.flush()
                os.fsync(f.fileno())
            n += 1
        res = "reached_max"
    except OSError as e:
        res = f"OSError {e.errno}"
        err = str(e)[:120]
    w = du(d)
    st = os.statvfs(d)
    subprocess.run(f"rm -rf {d}", shell=True)
    return dict(
        result=res,
        written_b=w,
        seconds=round(time.time() - t, 1),
        mb_per_s=round((w or 0) / 1e6 / max(time.time() - t, 1e-3), 1),
        err=err,
        free_after_b=st.f_bavail * st.f_frsize,
    )


def clone(repo, mode, d):
    args = (
        ["git", "clone", "-q"]
        + (["--depth", "1", "--single-branch", "--no-tags"] if mode == "shallow" else [])
        + [f"https://github.com/{repo}.git", d]
    )
    rx = netrx()
    t = time.time()
    p = subprocess.run(args, capture_output=True, text=True)
    s = time.time() - t
    got = netrx() - rx
    return dict(
        repo=repo,
        mode=mode,
        rc=p.returncode,
        seconds=round(s, 2),
        rx_b=got,
        mbit_s=round(got * 8 / 1e6 / max(s, 1e-3), 1),
        disk_b=du(d),
        err=p.stderr[-300:] if p.returncode else None,
    )


if __name__ == "__main__":
    a = sys.argv[1:]
    f = {
        "sysinfo": lambda: sysinfo(),
        "cpu": lambda: cpu(float(a[1]), a[2] if len(a) > 2 else None),
        "mem": lambda: mem(int(a[1])),
        "disk": lambda: disk(a[1], float(a[2])),
        "clone": lambda: clone(a[1], a[2], a[3]),
    }[a[0]]
    print(json.dumps(dict(probe=a[0], **f())), flush=True)
