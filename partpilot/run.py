"""Convenience entrypoint - run with `python run.py` from this directory.

Equivalent to `python -m backend.main`; kept as a thin wrapper so the
Uvicorn startup logic has one home (backend/main.py).
"""

from backend.main import run

if __name__ == "__main__":
    run()
