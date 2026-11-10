#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : job_manager.py
Rel. Path   : tools/job_manager/job_manager.py
Family      : Job Management / Subsystem 4
Purpose     : Entrypoint alias executing job_tool.py
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License     : PolyForm Noncommercial License 1.0.0
"""
from __future__ import annotations
import sys
from pathlib import Path

SCRIPT_DIR: Path = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import job_tool

if __name__ == "__main__":
    sys.exit(job_tool.main())
