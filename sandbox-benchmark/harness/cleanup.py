"""Delete every sandbox (except the 24 h soak instances unless --all) this experiment created (label/metadata exp=sandbox-a37-vs-dt) on the given providers, then verify none remain.
Usage: cleanup.py agent37 daytona instabox vercel [--all]"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import providers as P

ALL = "--all" in sys.argv
for name in [a for a in sys.argv[1:] if not a.startswith("--")]:
    pv = P.provider(name)
    for i in pv.list_ours(keep=ALL):
        try:
            pv.delete_id(i)
            print("deleted", name, i)
        except Exception as e:  # noqa: BLE001
            print("ERR", name, i, str(e)[:120])
    if name == "vercel":
        for sn in pv.S.query_snapshots():
            if str(getattr(sn, "status", "")).lower() != "deleted":
                try:
                    sn.delete()
                    print("deleted snapshot", sn.id)
                except Exception as e:  # noqa: BLE001
                    print("ERR snapshot", sn.id, str(e)[:120])
    time.sleep(5)
    print(name, "remaining:", pv.list_ours())
    if hasattr(pv, "list_all"):
        print(name, "all sandboxes in project:", pv.list_all())
    if name == "vercel":
        print(
            "vercel snapshots not deleted:",
            [
                x.id
                for x in pv.S.query_snapshots()
                if str(getattr(x, "status", "")).lower() != "deleted"
            ],
        )
