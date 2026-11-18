"""Provider abstraction: the same job spec runs on Daytona, Agent37, InstaBox, and Vercel Sandbox.
Keys come from the environment (DAYTONA_API_KEY, AGENT37_API_KEY, INSTABOX_API_KEY,
VERCEL_TOKEN, VERCEL_TEAM_ID, VERCEL_PROJECT_ID) and are never printed or written.
Every create/delete is appended to ../results/sandboxes.jsonl (provider, id, tag, event, time) so spend can be audited."""

import base64
import fcntl
import json
import os
import random
import threading
import time

H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(H)
TRACK = f"{ROOT}/results/sandboxes.jsonl"
_L = threading.Lock()
LABEL = "sandbox-a37-vs-dt"


def track(rec):
    rec = dict(rec, t=time.time())
    os.makedirs(os.path.dirname(TRACK), exist_ok=True)
    with _L, open(TRACK, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(rec) + "\n")


# Shapes. Agent37 has no 1 vCPU / 1 GiB shape, so our earlier "Small" has no counterpart.
SHAPES = {
    "medium": (2, 4, 8),
    "large": (4, 8, 10),
}  # vCPU, GiB RAM, GiB disk (same on both providers)
A37_TYPES = {
    "default": 1.0,
    "vm": 2.5,
    "performance": 4.0,
}  # compute-rate multiplier; disk unchanged


# Vercel Sandbox list prices (Pro, iad1): https://vercel.com/docs/vercel-sandbox/pricing
# Active CPU is billed only while the vCPU is busy; memory is billed the whole time (1 min minimum).
# Creations are $0.60 per million. Snapshot storage is not included in vc_cost (see vercel/analysis/spend_vercel.py).
VC_CPU_H, VC_GB_H, VC_CREATE = 0.128, 0.0212, 0.60 / 1e6


def vc_cost(life_s, shape, cpu_busy_s=0.0):
    """Modeled Vercel cost of one sandbox: provisioned memory over its lifetime
    (1 min minimum) + Active CPU (busy vCPU-seconds, read inside the guest from
    /proc/stat) + the creation."""
    return (
        max(life_s, 60) / 3600 * SHAPES[shape][1] * VC_GB_H
        + cpu_busy_s / 3600 * VC_CPU_H
        + VC_CREATE
    )


def rate_per_s(provider, shape, typ="default"):
    if provider == "vercel":
        # memory only; Active CPU is added per job from the measured busy time (vc_cost)
        return SHAPES[shape][1] * VC_GB_H / 3600
    c, m, d = SHAPES[shape]
    if provider == "instabox":
        return (
            (c * 0.004 + m * 0.00225 + 20 * 0.00011) / 3600
        )  # compute + the fixed 20 GiB /data at the list rate (upper bound: Pro includes 200 GiB across machines)
    if provider == "daytona":
        return (c * 0.0504 + m * 0.0162 + max(0, d - 5) * 0.000108) / 3600
    return ((c * 0.80 + m * 0.70) * A37_TYPES[typ] + d * 0.09) / 730 / 3600


class Box:
    def __init__(s, provider, id, home, raw=None, shape=None, typ=None):
        s.provider, s.id, s.home, s.raw, s.shape, s.typ = provider, id, home, raw, shape, typ


class ProviderError(Exception):
    def __init__(s, code, msg, http=None):
        super().__init__(f"{http} {code}: {msg}")
        s.code, s.http = code, http


class Daytona:
    name = "daytona"

    def __init__(s):
        from daytona import Daytona as D

        s.c = D()

    def create(s, shape, typ="default", tag="", image=None):
        from daytona import CreateSandboxFromSnapshotParams as P

        t = time.time()
        sb = s.c.create(
            P(
                snapshot=image or f"daytona-{shape}",
                labels={"exp": LABEL, "tag": tag[:60]},
                auto_stop_interval=0 if "keep" in tag else 30,
                auto_delete_interval=-1 if "keep" in tag else 0,
                ttl_minutes=None if "keep" in tag else 90,
            ),
            timeout=900,
        )
        b = Box("daytona", sb.id, "/home/daytona", sb, shape, typ)
        track(
            {
                "provider": "daytona",
                "id": sb.id,
                "tag": tag,
                "event": "created",
                "shape": shape,
                "type": typ,
            }
        )
        return b, time.time() - t

    def exec(s, b, cmd, timeout=900, root=False):
        if root:
            cmd = f"sudo -n sh -c {json.dumps(cmd)}"
        r = b.raw.process.exec(cmd, timeout=timeout)
        return r.exit_code, (r.result or "")

    def upload(s, b, data, path):
        b.raw.fs.upload_file(data, path)

    def delete(s, b, tag=""):
        for i in range(4):
            try:
                s.c.delete(b.raw)
                track({"provider": "daytona", "id": b.id, "tag": tag, "event": "deleted"})
                return True
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(3)
        track(
            {
                "provider": "daytona",
                "id": b.id,
                "tag": tag,
                "event": "delete_failed",
                "err": str(err)[:200],
            }
        )
        return False

    def sleep(s, b):
        b.raw.stop()  # Daytona has no checkpointed sleep: stop keeps the disk, drops memory

    def wake(s, b):
        b.raw.start(timeout=900)

    def list_ours(s, keep=True):
        from daytona import ListSandboxesQuery as Q

        return [
            x.id
            for x in s.c.list(Q(labels={"exp": LABEL}))
            if keep or "soak" not in ((x.labels or {}).get("tag", ""))
        ]

    def delete_id(s, i):
        s.c.delete(s.c.get(i))
        track({"provider": "daytona", "id": i, "event": "deleted_by_cleanup"})


class Agent37:
    name = "agent37"
    API = "https://api.agent37.com/v1"
    SBX = "https://sandbox.agent37.app/v1"

    def __init__(s):
        import requests

        s.r = requests.Session()
        s.k = os.environ["AGENT37_API_KEY"]

    def _api(s, method, path, body=None, timeout=900, params=None):
        resp = s.r.request(
            method,
            s.API + path,
            headers={"Authorization": "Bearer " + s.k},
            json=body,
            timeout=timeout,
            params=params,
        )
        if resp.status_code >= 400:
            try:
                e = resp.json().get("error")
                code, msg = (e.get("code"), e.get("message")) if isinstance(e, dict) else (e, "")
            except Exception:  # noqa: BLE001
                code, msg = "http", resp.text[:200]
            raise ProviderError(code, (msg or "")[:300], resp.status_code)
        return resp.json() if resp.content else {}

    def get(s, path, **kw):
        return s._api("GET", path, **kw)

    def create(s, shape, typ="default", tag="", image=None):
        c, m, d = SHAPES[shape]
        t = time.time()
        body = {
            "template": image or ("agent37-ubuntu" if typ == "vm" else "agent37-base"),
            "resources": {"cpu": c, "memory": m, "disk": d},
            "type": typ,
            "region": "us",
            "name": tag[:60] or LABEL,
            "metadata": {"exp": LABEL, "tag": tag[:60]},
            "network": "allow-all",
        }
        j = s._api("POST", "/instances", body, timeout=900)
        b = Box("agent37", j["id"], "/home/node", j, shape, typ)
        track(
            {
                "provider": "agent37",
                "id": j["id"],
                "tag": tag,
                "event": "created",
                "shape": shape,
                "type": typ,
                "status": j.get("status"),
                "resources": j.get("resources"),
            }
        )
        return b, time.time() - t

    def exec(s, b, cmd, timeout=840, root=True):
        resp = s.r.post(
            f"{s.SBX}/instances/{b.id}/exec",
            headers={"X-Agent37-Key": s.k},
            json={"command": cmd, **({"user": "root"} if root else {})},
            timeout=min(timeout, 900) + 30,
        )
        if resp.status_code >= 400:
            try:
                e = resp.json().get("error")
                code = e.get("code") if isinstance(e, dict) else e
            except Exception:  # noqa: BLE001
                code = "http"
            raise ProviderError(code, resp.text[:200], resp.status_code)
        j = resp.json()
        return j["exit_code"], (j.get("stdout") or "") + (j.get("stderr") or "")

    def upload(s, b, data, path):
        b64 = base64.b64encode(data).decode()
        CH = 48000
        s.exec(b, f"mkdir -p $(dirname {path}) && : > {path}.b64")
        for i in range(0, len(b64), CH):
            s.exec(b, f"printf %s '{b64[i : i + CH]}' >> {path}.b64")
        rc, out = s.exec(b, f"base64 -d {path}.b64 > {path} && rm {path}.b64")
        assert rc == 0, out

    def delete(s, b, tag=""):
        for i in range(4):
            try:
                s._api("DELETE", f"/instances/{b.id}")
                track({"provider": "agent37", "id": b.id, "tag": tag, "event": "deleted"})
                return True
            except ProviderError as e:
                if e.http == 404:
                    track(
                        {
                            "provider": "agent37",
                            "id": b.id,
                            "tag": tag,
                            "event": "deleted",
                            "note": "404",
                        }
                    )
                    return True
                err = e
                time.sleep(3)
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(3)
        track(
            {
                "provider": "agent37",
                "id": b.id,
                "tag": tag,
                "event": "delete_failed",
                "err": str(err)[:200],
            }
        )
        return False

    def sleep(s, b):
        s._api("POST", f"/instances/{b.id}/sleep")

    def wake(s, b):
        s.exec(b, "true")  # exec wakes a sleeping instance; we time it

    def metrics(s, b, hours=1):
        return s.get(f"/instances/{b.id}/metrics", params={"hours": hours})

    def list_ours(s, keep=True):
        return [
            x["id"]
            for x in s.get("/instances").get("data", [])
            if (x.get("metadata") or {}).get("exp") == LABEL
            and (keep or "soak" not in (x.get("metadata") or {}).get("tag", ""))
        ]

    def delete_id(s, i):
        s._api("DELETE", f"/instances/{i}")
        track({"provider": "agent37", "id": i, "event": "deleted_by_cleanup"})


class InstaBox:
    """InstaBox (Firecracker microVMs), Pro workspace. API https://api.instabox.sh, X-API-Key from INSTABOX_API_KEY (never printed or stored).
    Lifecycle calls (create, delete, suspend, resume) return an operation, followed with GET /v1/operations/{id}?wait=25s.
    Starts are limited (Pro 30 a minute, more is a retryable 429 rate_limited) and exec is limited to 64 at once per workspace (429 quota_exceeded):
    those, 503 no_capacity and 503 host_unavailable are retried with the server's Retry-After and counted in self.retries.
    Disk is the fixed 20 GiB /data (not settable at create); home is /data/home; exec runs as the unprivileged user `user` (sudo available)."""

    name = "instabox"
    API = "https://api.instabox.sh"
    TEMPLATE = os.environ.get("INSTABOX_TEMPLATE", "agent-browser")

    def __init__(s):
        import requests

        s.r = requests.Session()
        s.k = os.environ["INSTABOX_API_KEY"]
        s.retry = True
        s.retries = {}
        s._rl = threading.Lock()
        s._tl = threading.local()
        a = requests.adapters.HTTPAdapter(pool_connections=128, pool_maxsize=128)
        s.r.mount("https://", a)

    def _count(s, code):
        with s._rl:
            s.retries[code] = s.retries.get(code, 0) + 1

    def _raw(
        s,
        method,
        path,
        body=None,
        timeout=900,
        params=None,
        headers=None,
        data=None,
        retryable=True,
    ):
        import uuid

        h = {"X-API-Key": s.k, **(headers or {})}
        if method in ("POST", "DELETE", "PATCH") and not path.endswith("/exec"):
            h.setdefault("Idempotency-Key", str(uuid.uuid4()))
        tries = 0
        while True:
            tries += 1
            try:
                resp = s.r.request(
                    method,
                    s.API + path,
                    headers=h,
                    json=body if data is None else None,
                    data=data,
                    timeout=timeout,
                    params=params,
                )
            except Exception as e:
                if (
                    retryable
                    and s.retry
                    and tries <= 4
                    and ("Timeout" in type(e).__name__ or "Connection" in type(e).__name__)
                    and method == "GET"
                ):
                    s._count("conn_" + type(e).__name__)
                    time.sleep(2)
                    continue
                raise
            if resp.status_code >= 400:
                try:
                    e = resp.json().get("error") or {}
                except Exception:  # noqa: BLE001
                    e = {}
                code = e.get("code") or "http"
                ra = e.get("retryAfterSeconds") or resp.headers.get("Retry-After")
                if (
                    retryable
                    and s.retry
                    and e.get("retryable")
                    and code
                    in (
                        "rate_limited",
                        "quota_exceeded",
                        "no_capacity",
                        "host_unavailable",
                        "machine_cooldown",
                    )
                    and tries <= 12
                ):
                    s._count(code)
                    w = min(float(ra or 5), 60) if code != "host_unavailable" else 3
                    time.sleep(w)
                    s._tl.wait = getattr(s._tl, "wait", 0) + w
                    continue
                raise ProviderError(code, (e.get("message") or resp.text)[:300], resp.status_code)
            return resp

    def _api(s, method, path, body=None, **kw):
        r = s._raw(method, path, body, **kw)
        return r.json() if r.content else {}

    def _wait(s, op, timeout=900):
        t = time.time()
        while True:
            o = s._api("GET", f"/v1/operations/{op['id']}", params={"wait": "25s"}, timeout=60)
            if o["state"] == "succeeded":
                return o
            if o["state"] == "failed":
                e = o.get("error") or {}
                raise ProviderError(
                    e.get("code") or "operation_failed", (e.get("message") or "")[:300], None
                )
            if time.time() - t > timeout:
                raise ProviderError("operation_timeout", f"{op['id']} still {o['state']}", None)

    def create(s, shape, typ="default", tag="", image=None, auto_suspend=None):
        import re
        import uuid

        c, m, _d = SHAPES[shape]
        name = (
            (re.sub(r"[^a-z0-9-]", "-", tag.lower())[:48].strip("-") or "job")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        body = {
            "name": name,
            "templateId": image or s.TEMPLATE,
            "vcpus": c,
            "memMiB": m * 1024,
            "metadata": {"exp": LABEL, "tag": tag[:60]},
        }
        if auto_suspend is not None:
            body["autoSuspendAfterSeconds"] = auto_suspend
        for att in range(
            6
        ):  # a create whose operation failed (e.g. no_capacity) replays for the same key: retry with a new key
            t = time.time()
            w0 = getattr(s._tl, "wait", 0)
            try:
                op = s._api("POST", "/v1/machines", body, timeout=120)
                post_s = time.time() - t - (getattr(s._tl, "wait", 0) - w0)
                o = s._wait(op)
                break
            except ProviderError as e:
                if att < 5 and s.retry and e.code in ("no_capacity", "operation_failed"):
                    s._count("create_op_" + str(e.code))
                    time.sleep(10)
                    continue
                raise
        mid = op["machineId"]
        mach = o.get("machine") or {}
        b = Box("instabox", mid, "/data/home", mach, shape, typ)
        b.post_s = round(post_s, 3)
        b.name = name
        b.wait_s = round(
            getattr(s._tl, "wait", 0) - w0, 2
        )  # seconds spent waiting out 429 Retry-After inside this create; create_s and post_s exclude it
        track(
            {
                "provider": "instabox",
                "id": mid,
                "tag": tag,
                "event": "created",
                "shape": shape,
                "type": typ,
                "template": s.TEMPLATE,
                "spec": mach.get("spec"),
            }
        )
        return b, time.time() - t - b.wait_s

    def exec(s, b, cmd, timeout=840, root=False):
        if root:
            cmd = f"sudo -n sh -c {json.dumps(cmd)}"
        t = min(int(timeout), 600)
        j = s._api(
            "POST", f"/v1/machines/{b.id}/exec", {"cmd": cmd, "timeoutSeconds": t}, timeout=t + 30
        )
        return j.get("exitCode"), (j.get("stdout") or "") + (j.get("stderr") or "")

    def upload(s, b, data, path):
        s._raw(
            "PUT",
            f"/v1/machines/{b.id}/files",
            params={"path": path, "parents": "true"},
            data=data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=120,
        )

    def delete(s, b, tag=""):
        err = None
        for i in range(5):
            try:
                s._wait(
                    s._api(
                        "DELETE",
                        f"/v1/machines/{b.id}",
                        headers={"X-Confirm-Delete": b.id},
                        timeout=120,
                    ),
                    timeout=300,
                )
                track({"provider": "instabox", "id": b.id, "tag": tag, "event": "deleted"})
                return True
            except ProviderError as e:
                if e.http == 404 or e.code == "not_found":
                    track(
                        {
                            "provider": "instabox",
                            "id": b.id,
                            "tag": tag,
                            "event": "deleted",
                            "note": "404",
                        }
                    )
                    return True
                err = e
                time.sleep(3 + 3 * i)
            except Exception as e:  # noqa: BLE001
                err = e
                time.sleep(3 + 3 * i)
        track(
            {
                "provider": "instabox",
                "id": b.id,
                "tag": tag,
                "event": "delete_failed",
                "err": str(err)[:200],
            }
        )
        return False

    def sleep(s, b):
        s._wait(
            s._api("POST", f"/v1/machines/{b.id}/suspend", timeout=120), timeout=600
        )  # pause: memory and processes kept

    def wake(s, b):
        t = time.time()
        s._wait(s._api("POST", f"/v1/machines/{b.id}/resume", timeout=120), timeout=900)
        b.last_wake_s = round(time.time() - t, 3)  # a manual pause does not wake on exec

    def get(s, path, **kw):
        return s._api("GET", path, **kw)

    def list_ours(s, keep=True):
        out = []
        cur = None
        while True:
            j = s.get("/v1/machines", params={"limit": 200, **({"cursor": cur} if cur else {})})
            out += [
                x["id"]
                for x in j.get("machines", [])
                if (x.get("metadata") or {}).get("exp") == LABEL
                and (keep or "soak" not in (x.get("metadata") or {}).get("tag", ""))
            ]
            cur = j.get("nextCursor")
            if not cur:
                return out

    def list_all(s):
        out = []
        cur = None
        while True:
            j = s.get("/v1/machines", params={"limit": 200, **({"cursor": cur} if cur else {})})
            out += [x["id"] for x in j.get("machines", [])]
            cur = j.get("nextCursor")
            if not cur:
                return out

    def delete_id(s, i):
        s.delete(Box("instabox", i, "/data/home"), "cleanup") or (_ for _ in ()).throw(
            RuntimeError("delete failed " + i)
        )


class Vercel:
    """Vercel Sandbox (Firecracker microVMs). Official Python SDK `vercel-sandbox`
    (sync API: `vercel.sandbox.sync`). Auth from VERCEL_TOKEN, VERCEL_TEAM_ID, and
    VERCEL_PROJECT_ID (never printed).

    Shapes: 2 vCPU -> 4 GiB, 4 vCPU -> 8 GiB (2 GiB per vCPU is fixed). Disk is 64 GB
    ephemeral NVMe on every size (fixed, not settable). Default image
    `vercel/sandbox/universal`. Exec runs as `ubuntu` with sudo; home is `/home/ubuntu`.

    Persistence is the SDK default: stop() writes a filesystem snapshot and ends the
    session; memory and processes are not kept. The grid and bursts destroy running
    sandboxes (no stop, so no snapshot). Exec is run_command('sh', ['-c', cmd]).

    The SDK itself retries 429/5xx twice with short backoff. This client counts every
    retry (self.retries) and can switch them off (self.retry=False) for no-retry burst
    waves. That hook patches vercel.sandbox._internal.retry, which is not a public API.
    """

    name = "vercel"

    def __init__(s):
        import vercel.sandbox._internal.retry as R
        from vercel.sandbox import sync as S

        s.S = S
        s.retry = True
        s.retries = {}
        s._rl = threading.Lock()
        s._tl = threading.local()
        orig = R._retry_delay

        def patched(error, failures):
            code = f"http_{getattr(error, 'status_code', None) or type(error).__name__}"
            if not s.retry:
                return None
            d = orig(error, failures)
            if d is not None:
                with s._rl:
                    s.retries[code] = s.retries.get(code, 0) + 1
                s._tl.wait = getattr(s._tl, "wait", 0) + d
            return d

        R._retry_delay = patched

    @staticmethod
    def _err(e):
        http = getattr(e, "status_code", None)
        code = getattr(e, "code", None) or type(e).__name__
        return ProviderError(code, str(e)[:300], http)

    def create(
        s, shape, typ="default", tag="", image=None, persistent=None, timeout_s=3600, name=None
    ):
        import re

        from vercel.sandbox import SandboxResources

        c, m, _d = SHAPES[shape]
        t = time.time()
        s._tl.wait = 0
        kw = {
            "resources": SandboxResources(vcpus=c, memory=m * 1024),
            "execution_time_limit": timeout_s,
            "tags": {"exp": LABEL, "tag": re.sub(r"[^A-Za-z0-9._-]", "-", tag)[:60] or "job"},
        }
        if persistent is not None:
            kw["persistent"] = persistent
        if name:
            kw["name"] = name
        if image:
            kw["image"] = image
        tries = 0
        while True:
            # The SDK retried twice already. A vCPU-allocation 429 (Pro starts at
            # 150 vCPUs/min and ramps) is retried here after ~1.5 s, counted, and
            # the wait is excluded from create_s (as for InstaBox).
            tries += 1
            try:
                sb = s.S.create_sandbox(**kw)
                break
            except Exception as e:  # noqa: BLE001
                if s.retry and tries <= 25 and getattr(e, "status_code", None) == 429:
                    with s._rl:
                        s.retries["harness_429"] = s.retries.get("harness_429", 0) + 1
                    w = 1.5 + random.random()
                    time.sleep(w)
                    s._tl.wait = getattr(s._tl, "wait", 0) + w
                    continue
                raise s._err(e)
        cs = time.time() - t
        b = Box("vercel", sb.name, "/home/ubuntu", sb, shape, typ)
        # wait_s: seconds the SDK slept in its own 429/5xx retry backoff inside this
        # create. create_s returned excludes it; raw_create_s keeps it.
        b.wait_s = round(getattr(s._tl, "wait", 0), 2)
        b.raw_create_s = round(cs, 3)
        b.sandbox_id = getattr(sb, "current_session_id", None)
        track(
            {
                "provider": "vercel",
                "id": sb.name,
                "tag": tag,
                "event": "created",
                "shape": shape,
                "type": typ,
                "session": b.sandbox_id,
                "status": str(getattr(sb, "status", None)),
            }
        )
        return b, cs - b.wait_s

    def exec(s, b, cmd, timeout=840, root=False):
        try:
            r = b.raw.run_command(
                "sh",
                ["-c", cmd],
                sudo=root,
                kill_after=min(float(timeout), 3600),
                capture_output=True,
            )
        except Exception as e:  # noqa: BLE001
            raise s._err(e)
        return r.returncode, ((r.stdout or b"").decode(errors="replace")) + (
            (r.stderr or b"").decode(errors="replace")
        )

    def upload(s, b, data, path):
        try:
            b.raw.fs.write_bytes(path, data)
        except Exception as e:  # noqa: BLE001
            raise s._err(e)

    def delete(s, b, tag=""):
        err = None
        for i in range(5):
            try:
                b.raw.destroy()
                track({"provider": "vercel", "id": b.id, "tag": tag, "event": "deleted"})
                return True
            except Exception as e:  # noqa: BLE001
                if getattr(e, "status_code", None) == 404:
                    track(
                        {
                            "provider": "vercel",
                            "id": b.id,
                            "tag": tag,
                            "event": "deleted",
                            "note": "404",
                        }
                    )
                    return True
                err = e
                time.sleep(2 + 2 * i)
        track(
            {
                "provider": "vercel",
                "id": b.id,
                "tag": tag,
                "event": "delete_failed",
                "err": str(err)[:200],
            }
        )
        return False

    def sleep(s, b):
        """Stop the session. Vercel snapshots the filesystem automatically
        (persistent sandbox); memory and processes are not kept."""
        try:
            b.raw.stop()
        except Exception as e:  # noqa: BLE001
            raise s._err(e)

    def wake(s, b):
        """Explicit resume: a new session boots from the saved filesystem
        (resume_sandbox by name). Timed separately as last_wake_s."""
        t = time.time()
        try:
            b.raw = s.S.resume_sandbox(name=b.id)
        except Exception as e:  # noqa: BLE001
            raise s._err(e)
        b.last_wake_s = round(time.time() - t, 3)

    def list_ours(s, keep=True):
        out = []
        for x in s.S.query_sandboxes():
            tg = getattr(x, "tags", None) or {}
            if tg.get("exp") == LABEL and (keep or "soak" not in tg.get("tag", "")):
                out.append(x.name)
        return out

    def list_all(s):
        return [x.name for x in s.S.query_sandboxes()]

    def list_snapshots(s):
        return [x.id for x in s.S.query_snapshots()]

    def delete_id(s, i):
        sb = s.S.get_sandbox(name=i)
        sb.destroy()
        track({"provider": "vercel", "id": i, "event": "deleted_by_cleanup"})


def provider(name):
    return {
        "daytona": Daytona,
        "agent37": Agent37,
        "instabox": InstaBox,
        "vercel": Vercel,
    }[name]()
