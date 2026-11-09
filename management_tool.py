#!/data/data/com.termux/files/usr/bin/env python3
"""
# Name:           management_tool.py
# Description:    Unified System Management Tool & Entry Router for Logging, Reports, Notes, Taxonomy & Jobs
# Version:        1.5.0
# Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# License:        MIT / BEJSON Standard
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR: Path = Path(__file__).resolve().parent
LIB_DIR: Path = SCRIPT_DIR / "lib"
CONFIG_DIR: Path = SCRIPT_DIR / "config"
LOGGING_TOOL_PATH: Path = SCRIPT_DIR / "logging_tool.py"
REPORT_INDEXER_PATH: Path = SCRIPT_DIR / "report_indexer.py"
NOTES_TOOL_PATH: Path = SCRIPT_DIR / "notes_tool.py"
JOB_TOOL_PATH: Path = SCRIPT_DIR / "job_tool.py"
TAXONOMY_CARTOGRAPHER_PATH: Path = Path("/storage/emulated/0/Admin/Dev/Tools/Taxonomy_Cartographer/taxonomy_cartographer.py")
STATE_FILE_PATH: Path = CONFIG_DIR / "state.json"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# Policy §8.1 Tri-Color Palette
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"
COLOR_ANSI_RED: str = "\033[1;31m"
COLOR_RESET: str = "\033[0m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM
ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and sys.stdout.isatty() else ""
RESET: str = COLOR_RESET if not NO_COLOR and sys.stdout.isatty() else ""

SUPPORTED_MODES: Dict[str, str] = {
    "1": "logging",
    "logging": "logging",
    "2": "reports",
    "reports": "reports",
    "3": "notes",
    "notes": "notes",
    "4": "jobs",
    "job": "jobs",
    "jobs": "jobs",
    "5": "taxonomy",
    "taxonomy": "taxonomy",
    "cartography": "taxonomy"
}


def load_shared_state() -> Dict[str, Any]:
    """Load persistent mode and chamber state."""
    if not STATE_FILE_PATH.exists():
        return {"active_mode": "reports", "active_category": None, "active_entry": None}
    try:
        with open(STATE_FILE_PATH, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        return {"active_mode": "reports", "active_category": None, "active_entry": None}


def persist_shared_state(state_dictionary: Dict[str, Any]) -> None:
    """Save persistent state atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp_state_file: Path = STATE_FILE_PATH.with_suffix(".tmp")
    with open(temp_state_file, "w", encoding="utf-8") as file_handle:
        json.dump(state_dictionary, file_handle, indent=2)
        file_handle.write("\n")
    temp_state_file.replace(STATE_FILE_PATH)


def forward_command(target_script: Path, forward_arguments: List[str]) -> int:
    """Forward command-line invocation to dedicated subsystem script."""
    if not target_script.is_file():
        print(f"{ACCENT}[✗] Subsystem script not found:{RESET} {target_script}", file=sys.stderr)
        return 1
    command_vector: List[str] = [sys.executable, str(target_script)] + forward_arguments
    execution_result = subprocess.run(command_vector)
    return execution_result.returncode


def print_unified_status() -> None:
    """Print high-density status banner across all management subsystems."""
    state_data: Dict[str, Any] = load_shared_state()
    current_mode: str = state_data.get("active_mode", "reports").upper()
    current_cat: str = state_data.get("active_category") or "(none)"
    current_ent: str = state_data.get("active_entry") or "(none)"
    current_job: str = state_data.get("active_job") or "(none)"

    print("=" * 57)
    print(f" {ACCENT}SYSTEM MANAGEMENT TOOL [UNIFIED ROUTER]{RESET}")
    print("-" * 57)
    print(f" {ACCENT}ACTIVE MODE:{RESET}  [{current_mode}]")
    print(f" {ACCENT}CATEGORY:{RESET}     {current_cat:<38}")
    print(f" {ACCENT}ENTRY:{RESET}        {current_ent:<38}")
    print(f" {ACCENT}JOB:{RESET}          {current_job:<38}")
    print("-" * 57)
    print(" Subsystems:")
    print("  • [1] Logging:   BEJSON 105 Standardized Logging Tool")
    print("  • [2] Reports:   Research Papers Tracking & Indexer")
    print("  • [3] Notes:     Categorized Notes & MFDB Notebook Manager")
    print("  • [4] Jobs:      Stateful Job Chamber & Urgent Deployment Manager")
    print("=" * 57)


def print_help_guide() -> None:
    """Print AI-optimized command specification and context delivery."""
    print("=" * 57)
    print(f" {ACCENT}SYSTEM MANAGEMENT TOOL - AI-OPTIMIZED AGENT GUIDE{RESET}")
    print("-" * 57)
    print("USAGE SYNTAX:")
    print("  python3 management_tool.py <subsystem|flags> [args...]")
    print("  bash /storage/emulated/0/Admin/System/tools/management_tool/management.sh <subsystem|flags> [args...]")
    print()
    print(f"{ACCENT}SESSION STARTUP & MAINTENANCE DIRECTIVES:{RESET}")
    print("  • Composite Init Check:  python3 management_tool.py job --init-check")
    print("  • Query Maintenance:     python3 management_tool.py job --maintenance")
    print("  • Record Maint Run:      python3 management_tool.py job --record-maintenance <id>")
    print("  • AI Context JSON:       python3 management_tool.py --agent-context")
    print()
    print(f"{ACCENT}SUBSYSTEM ROUTING:{RESET}")
    print("  job    Stateful Job Chamber, Queues & Maintenance (Mode 4)")
    print("  log    BEJSON 105 Standardized Logging Tool (Mode 1)")
    print("  note   Notes & MFDB Notebook Manager (Mode 3)")
    print("  report Research Papers Tracking & Indexer (Mode 2)")
    print("  tax    Taxonomy Cartographer (Mode 5)")
    print()
    print(f"{ACCENT}SUBSYSTEM QUICK CLI MATRIX:{RESET}")
    print("  [job]    --list | --list-completed | --query <term>")
    print("           --select <id> | --view | --add-task <t> | --toggle-task <idx>")
    print("           --complete-job -m <summary> | --new -n <name> -i <instructions>")
    print("           --maintenance | --init-check | --record-maintenance <id>")
    print("  [log]    write -m \"<msg>\" [-l <level>] [-s <subsystem>]")
    print("           read [--min-level <lvl>] [--since <iso|today>]")
    print("  [note]   --list-notes | --select-note | --note-new | --web")
    print("  [report] --list-entries | --query <term> | --action-view")
    print("  [tax]    --map | --signatures | --ast | --scan")
    print()
    print(f"{ACCENT}MODE CONFIGURATION:{RESET}")
    print("  --select-mode <1|2|3|4|5>   Switch active persistent mode")
    print("  --list-modes                Display supported modes")
    print("  --status                    Display 57-column chamber status")
    print("=" * 57)


def main() -> int:
    arguments: List[str] = sys.argv[1:]

    if not arguments:
        print_unified_status()
        print()
        print_help_guide()
        return 0

    first_argument: str = arguments[0].strip().lower()

    # 0. AI Context & Universal Help Interception
    if first_argument in ("-h", "--help", "help"):
        print_help_guide()
        return 0

    if first_argument in ("--agent-context", "--ai-help"):
        return forward_command(JOB_TOOL_PATH, ["--agent-context"])

    # 1. Direct subsystem routing: 'log', 'report', 'note', 'taxonomy', or 'job'
    if first_argument in ("log", "logging"):
        return forward_command(LOGGING_TOOL_PATH, arguments[1:])

    if first_argument in ("report", "reports", "indexer"):
        return forward_command(REPORT_INDEXER_PATH, arguments[1:])

    if first_argument in ("note", "notes"):
        return forward_command(NOTES_TOOL_PATH, arguments[1:])

    if first_argument in ("tax", "taxonomy", "cartographer", "cartography"):
        return forward_command(TAXONOMY_CARTOGRAPHER_PATH, arguments[1:])

    if first_argument in ("job", "jobs", "jobmaker"):
        return forward_command(JOB_TOOL_PATH, arguments[1:])

    # 2. Mode management
    if first_argument in ("--select-mode", "-m"):
        if len(arguments) < 2:
            print(f"{ACCENT}[✗] Error:{RESET} Mode value required (1/logging, 2/reports, 3/notes, 4/taxonomy, or 5/jobs).", file=sys.stderr)
            return 1
        mode_token = arguments[1].strip().lower()
        if mode_token not in SUPPORTED_MODES:
            print(f"{ACCENT}[✗] Error:{RESET} Invalid mode '{mode_token}'. Allowed: 1, 2, 3, 4, or 5.", file=sys.stderr)
            return 1
        chosen_mode = SUPPORTED_MODES[mode_token]
        state = load_shared_state()
        state["active_mode"] = chosen_mode
        persist_shared_state(state)
        # Also sync to report_indexer state if applicable
        if chosen_mode in ("logging", "reports"):
            forward_command(REPORT_INDEXER_PATH, ["--select-mode", chosen_mode])
        print(f"{ACCENT}[✓] Operational mode set to:{RESET} [{chosen_mode.upper()}]")
        return 0

    if first_argument == "--list-modes":
        print("=" * 57)
        print(f" {ACCENT}SUPPORTED OPERATIONAL MODES{RESET}")
        print("-" * 57)
        print(f" [{ACCENT}1{RESET}] logging   - BEJSON 105 Standardized Logging Tool")
        print(f" [{ACCENT}2{RESET}] reports   - Research Papers Tracking & Indexing")
        print(f" [{ACCENT}3{RESET}] notes     - Categorized Notes & MFDB Notebook Manager")
        print(f" [{ACCENT}4{RESET}] jobs      - Stateful Job Chamber & Urgent Deployment Manager")
        print(f" [{ACCENT}* {RESET}] taxonomy  - External: Admin/Dev/Tools/Taxonomy_Cartographer")
        print("=" * 57)
        return 0

    if first_argument in ("--status", "--info", "status"):
        print_unified_status()
        return 0

    # 3. Transparent Delegation based on Active Mode or Explicit Flags
    state = load_shared_state()
    active_mode = state.get("active_mode", "reports")

    # If job-specific flags passed -> route to job_tool
    if any(arg in ("--deploy", "--list-deployed", "--list-saved", "--list-completed", "--maintenance", "--list-maintenance", "--init-check") or arg.startswith("--select-job") or arg.startswith("--add-task") or arg.startswith("--toggle-task") or arg.startswith("--record-maintenance") or arg.startswith("--query-maintenance") or arg in ("--new", "--create-job", "--show-chamber", "--clear-job") for arg in arguments):
        return forward_command(JOB_TOOL_PATH, arguments)

    # If taxonomy-specific flags passed -> route to taxonomy_cartographer
    if any(arg in ("--map", "--signatures", "--ast", "--scan", "--export-schema") or arg.startswith("--scan") for arg in arguments):
        return forward_command(TAXONOMY_CARTOGRAPHER_PATH, arguments)

    # If note-specific flags passed -> route to notes_tool
    if any(arg.startswith("--note") or arg.startswith("--add-tag") or arg.startswith("--remove-tag") or arg.startswith("--set-category") or arg in ("--list-notes", "--clear-note", "--web", "--serve") for arg in arguments):
        return forward_command(NOTES_TOOL_PATH, arguments)

    # If write, read, export, report-log, audit, archive passed -> route to logging_tool
    if first_argument in ("write", "read", "export", "report-log", "audit", "archive", "context"):
        if first_argument == "report-log":
            return forward_command(LOGGING_TOOL_PATH, ["report"] + arguments[1:])
        return forward_command(LOGGING_TOOL_PATH, arguments)

    # If report flags passed -> route to report_indexer
    if any(arg.startswith("--import") or arg.startswith("--query") or "category" in arg or "entry" in arg or "pull" in arg for arg in arguments):
        if active_mode == "notes":
            return forward_command(NOTES_TOOL_PATH, arguments)
        if active_mode in ("job", "jobs"):
            return forward_command(JOB_TOOL_PATH, arguments)
        return forward_command(REPORT_INDEXER_PATH, arguments)

    # Otherwise route to active mode tool
    if active_mode == "logging":
        target_tool = LOGGING_TOOL_PATH
    elif active_mode == "notes":
        target_tool = NOTES_TOOL_PATH
    elif active_mode == "taxonomy":
        target_tool = TAXONOMY_CARTOGRAPHER_PATH
    elif active_mode in ("job", "jobs"):
        target_tool = JOB_TOOL_PATH
    else:
        target_tool = REPORT_INDEXER_PATH
    return forward_command(target_tool, arguments)


if __name__ == "__main__":
    sys.exit(main())
