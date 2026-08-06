"""PartPilot backend package."""

import os

# Brain 1 runs on TensorFlow and Brain 2 on PyTorch, and on Windows each ships
# its own OpenMP runtime (libiomp5md.dll and libomp140.x86_64.dll). Loading
# both into one process aborts with "OMP: Error #15", which kills the server
# mid-prediction as soon as a request touches both brains.
#
# This tells OpenMP to tolerate the second runtime. The documented risk is
# degraded performance or, in theory, incorrect results - but the alternative
# here is a hard abort, and inference is short-lived and single-threaded per
# request.
#
# It lives in the package __init__ rather than main.py because it has to be set
# before anything imports torch or tensorflow: with reload enabled Uvicorn
# re-imports the app in a worker process, so exporting it in the parent shell
# does not reliably reach the code that needs it.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
