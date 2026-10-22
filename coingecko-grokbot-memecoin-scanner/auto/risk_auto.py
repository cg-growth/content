#!/usr/bin/env python3
"""Risk engine for the AI book: same risk.py, BOOK=auto + PAPER_DB=auto.db (all exits automatic)."""
import os, runpy
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
os.environ["BOOK"] = "auto"; os.environ["PAPER_DB"] = _ROOT + "/auto.db"
runpy.run_path(_ROOT + "/risk/risk.py", run_name="__main__")
