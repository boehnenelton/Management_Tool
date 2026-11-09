#!/data/data/com.termux/files/usr/bin/env python3
"""
Package Entrypoint: __main__.py
Tool Family:        Management Tool Suite
Author:             Elton Boehnen · boehnenelton2024@gmail.com
Purpose:            Enables directory execution (python3 /path/to/management_tool [args...])
Version:            1.5.1
"""
import sys
from pathlib import Path

PACKAGE_ROOT_DIRECTORY: Path = Path(__file__).resolve().parent
if str(PACKAGE_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT_DIRECTORY))

import management_tool

if __name__ == "__main__":
    sys.exit(management_tool.main())
