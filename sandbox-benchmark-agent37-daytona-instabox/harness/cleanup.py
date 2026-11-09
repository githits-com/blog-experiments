"""Delete every sandbox (except the 24 h soak instances unless --all) this experiment created (label/metadata exp=sandbox-a37-vs-dt) on the given providers, then verify none remain.
Usage: cleanup.py agent37 daytona"""

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
        except Exception as e:
            print("ERR", name, i, str(e)[:120])
    time.sleep(5)
    print(name, "remaining:", pv.list_ours())
