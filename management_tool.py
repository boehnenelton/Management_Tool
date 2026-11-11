#!/data/data/com.termux/files/usr/bin/env python3
"""
# Name:           management_tool.py
# Description:    Unified System Management Tool & Entry Router for Logging, Reports, Notes, Taxonomy & Jobs
# Version:        152
# Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# License:        PolyForm-Noncommercial-1.0.0
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
TOOLS_DIR: Path = SCRIPT_DIR / "tools"
LOGGING_TOOL_PATH: Path = TOOLS_DIR / "logging_tool" / "logging_tool.py"
REPORT_INDEXER_PATH: Path = TOOLS_DIR / "report_indexer" / "report_indexer.py"
NOTES_TOOL_PATH: Path = TOOLS_DIR / "notes_tool" / "notes_tool.py"
JOB_TOOL_PATH: Path = TOOLS_DIR / "job_manager" / "job_tool.py"
REMINDER_TOOL_PATH: Path = TOOLS_DIR / "reminder_tool" / "reminder_tool.py"
TAXONOMY_CARTOGRAPHER_PATH: Path = Path("/storage/emulated/0/Admin/Dev/Tools/Taxonomy_Cartographer/taxonomy_cartographer.py")
STATE_FILE_PATH: Path = CONFIG_DIR / "state.json"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# Policy §8.1 Tri-Color Palette
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"  # Policy §8.1 #DE2626 Truecolor
COLOR_ANSI_RED: str = "\033[1;31m"          # ANSI Bold Red fallback
COLOR_RESET: str = "\033[0m"
COLOR_WHITE: str = "\033[1;37m"             # Bright White
COLOR_NEUTRAL: str = "\033[0;37m"           # Standard White
COLOR_DIM: str = "\033[2m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM
IS_TTY: bool = sys.stdout.isatty() or sys.stderr.isatty()

ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and IS_TTY else ""
WHITE: str = COLOR_WHITE if not NO_COLOR and IS_TTY else ""
NEUTRAL: str = COLOR_NEUTRAL if not NO_COLOR and IS_TTY else ""
RESET: str = COLOR_RESET if not NO_COLOR and IS_TTY else ""
DIM: str = COLOR_DIM if not NO_COLOR and IS_TTY else ""

DIVIDER_49: str = "=" * 49
SUBDIVIDER_49: str = "-" * 49
DIVIDER_57: str = DIVIDER_49
SUBDIVIDER_57: str = SUBDIVIDER_49


def print_positive(message: str) -> None:
    """Print positive status message in white lowercase."""
    print(f"{WHITE}[✓] {message.lower()}{RESET}")


def print_fail(message: str) -> None:
    """Print failure error message in #DE2626 UPPERCASE RED."""
    err_stream = sys.stderr
    print(f"{ACCENT}[✗] {message.upper()}{RESET}", file=err_stream)


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
    "5": "reminders",
    "remind": "reminders",
    "reminder": "reminders",
    "reminders": "reminders",
    "6": "taxonomy",
    "taxonomy": "taxonomy",
    "cartography": "taxonomy",
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
        print_fail(f"SUBSYSTEM SCRIPT NOT FOUND: {target_script}")
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

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}SYSTEM MANAGEMENT TOOL [UNIFIED ROUTER]{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    print(f" {ACCENT}ACTIVE MODE:{RESET}  {WHITE}[{current_mode}]{RESET}")
    print(f" {ACCENT}CATEGORY:{RESET}     {NEUTRAL}{current_cat[:30]:<30}{RESET}")
    print(f" {ACCENT}ENTRY:{RESET}        {NEUTRAL}{current_ent[:30]:<30}{RESET}")
    print(f" {ACCENT}JOB:{RESET}          {NEUTRAL}{current_job[:30]:<30}{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    print(f" {ACCENT}Subsystems:{RESET}")
    print(f"  • [{ACCENT}1{RESET}] {ACCENT}Logging:{RESET}   {NEUTRAL}BEJSON 105 Logging Tool{RESET}")
    print(f"  • [{ACCENT}2{RESET}] {ACCENT}Reports:{RESET}   {NEUTRAL}Research Tracking & Indexer{RESET}")
    print(f"  • [{ACCENT}3{RESET}] {ACCENT}Notes:{RESET}     {NEUTRAL}Categorized Notes & MFDB{RESET}")
    print(f"  • [{ACCENT}4{RESET}] {ACCENT}Jobs:{RESET}      {NEUTRAL}Stateful Job Chamber{RESET}")
    print(f"  • [{ACCENT}5{RESET}] {ACCENT}Reminders:{RESET} {NEUTRAL}Launch Reminders & Tasks{RESET}")
    print(f"  • [{ACCENT}6{RESET}] {ACCENT}Taxonomy:{RESET}  {NEUTRAL}Taxonomy Cartographer{RESET}")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")


def print_help_guide() -> None:
    """Print AI-optimized command specification clamped to 49 columns."""
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}SYSTEM MANAGEMENT TOOL - AGENT GUIDE{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    print(f"{ACCENT}USAGE SYNTAX:{RESET}")
    print(f"  {NEUTRAL}python3 management_tool.py <subsystem> [args]{RESET}")
    print(f"  {NEUTRAL}bash management.sh <subsystem> [args]{RESET}")
    print()
    print(f"{ACCENT}SESSION STARTUP & MAINTENANCE:{RESET}")
    print(f"  • {ACCENT}Init Check:{RESET}     {NEUTRAL}job --init-check{RESET}")
    print(f"  • {ACCENT}Maintenance:{RESET}    {NEUTRAL}job --maintenance{RESET}")
    print(f"  • {ACCENT}Record Maint:{RESET}   {NEUTRAL}job --record-maint <id>{RESET}")
    print(f"  • {ACCENT}Reminders:{RESET}      {NEUTRAL}remind print{RESET}")
    print(f"  • {ACCENT}AI Context:{RESET}     {NEUTRAL}--agent-context{RESET}")
    print()
    print(f"{ACCENT}SUBSYSTEM ROUTING:{RESET}")
    print(f"  {ACCENT}remind{RESET}  {NEUTRAL}Reminders & Active Tasks (Mode 5){RESET}")
    print(f"  {ACCENT}job{RESET}     {NEUTRAL}Stateful Job Chamber (Mode 4){RESET}")
    print(f"  {ACCENT}log{RESET}     {NEUTRAL}BEJSON 105 Logging (Mode 1){RESET}")
    print(f"  {ACCENT}note{RESET}    {NEUTRAL}Notes & MFDB Manager (Mode 3){RESET}")
    print(f"  {ACCENT}report{RESET}  {NEUTRAL}Research Paper Indexer (Mode 2){RESET}")
    print(f"  {ACCENT}tax{RESET}     {NEUTRAL}Taxonomy Cartographer (Mode 6){RESET}")
    print()
    print(f"{ACCENT}QUICK CLI MATRIX:{RESET}")
    print(f"  [{ACCENT}remind{RESET}] {NEUTRAL}add <text> [-p <prio>] | done <id>{RESET}")
    print(f"           {NEUTRAL}list | completed | print | --json{RESET}")
    print(f"  [{ACCENT}job{RESET}]    {NEUTRAL}--list | --query <term> | --view{RESET}")
    print(f"           {NEUTRAL}--select <id> | --add-task <t>{RESET}")
    print(f"           {NEUTRAL}--maintenance | --init-check{RESET}")
    print(f"  [{ACCENT}log{RESET}]    {NEUTRAL}write -m \"<msg>\" [-l <level>]{RESET}")
    print(f"           {NEUTRAL}read [--min-level <lvl>] [--since]{RESET}")
    print(f"  [{ACCENT}note{RESET}]   {NEUTRAL}--list-notes | --note-new | --web{RESET}")
    print(f"  [{ACCENT}report{RESET}] {NEUTRAL}--list-entries | --query <term>{RESET}")
    print(f"  [{ACCENT}tax{RESET}]    {NEUTRAL}--map | --signatures | --ast{RESET}")
    print()
    print(f"{ACCENT}MODE CONFIGURATION:{RESET}")
    print(f"  {ACCENT}--select-mode <1-6>{RESET} {NEUTRAL}Switch active mode{RESET}")
    print(f"  {ACCENT}--list-modes{RESET}        {NEUTRAL}Display modes{RESET}")
    print(f"  {ACCENT}--status{RESET}            {NEUTRAL}Display status banner{RESET}")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")


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

    if first_argument in ("remind", "reminders", "reminder"):
        return forward_command(REMINDER_TOOL_PATH, arguments[1:])

    # 2. Mode management
    if first_argument in ("--select-mode", "-m"):
        if len(arguments) < 2:
            print_fail("MODE VALUE REQUIRED (1/LOGGING, 2/REPORTS, 3/NOTES, 4/JOBS, 5/REMINDERS, OR 6/TAXONOMY).")
            return 1
        mode_token = arguments[1].strip().lower()
        if mode_token not in SUPPORTED_MODES:
            print_fail(f"INVALID MODE '{mode_token.upper()}'. ALLOWED: 1, 2, 3, 4, 5, OR 6.")
            return 1
        chosen_mode = SUPPORTED_MODES[mode_token]
        state = load_shared_state()
        state["active_mode"] = chosen_mode
        persist_shared_state(state)
        # Also sync to report_indexer state if applicable
        if chosen_mode in ("logging", "reports"):
            forward_command(REPORT_INDEXER_PATH, ["--select-mode", chosen_mode])
        print_positive(f"operational mode set to: [{chosen_mode.lower()}]")
        return 0

    if first_argument == "--list-modes":
        print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
        print(f" {ACCENT}SUPPORTED OPERATIONAL MODES{RESET}")
        print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
        print(f" [{ACCENT}1{RESET}] {ACCENT}logging{RESET}   - {NEUTRAL}BEJSON 105 Logging Tool{RESET}")
        print(f" [{ACCENT}2{RESET}] {ACCENT}reports{RESET}   - {NEUTRAL}Research Papers Indexing{RESET}")
        print(f" [{ACCENT}3{RESET}] {ACCENT}notes{RESET}     - {NEUTRAL}Categorized Notes & MFDB{RESET}")
        print(f" [{ACCENT}4{RESET}] {ACCENT}jobs{RESET}      - {NEUTRAL}Stateful Job Chamber{RESET}")
        print(f" [{ACCENT}5{RESET}] {ACCENT}reminders{RESET} - {NEUTRAL}Launch Reminders & Tasks{RESET}")
        print(f" [{ACCENT}6{RESET}] {ACCENT}taxonomy{RESET}  - {NEUTRAL}Taxonomy Cartographer{RESET}")
        print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
        return 0

    if first_argument in ("--status", "--info", "status"):
        print_unified_status()
        return 0

    # 3. Transparent Delegation based on Active Mode or Explicit Flags
    state = load_shared_state()
    active_mode = state.get("active_mode", "reports")

    # If reminder flags passed -> route to reminder_tool
    if any(arg in ("--print-termux", "print", "launch") for arg in arguments):
        return forward_command(REMINDER_TOOL_PATH, arguments)

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
        if active_mode in ("remind", "reminders", "reminder"):
            return forward_command(REMINDER_TOOL_PATH, arguments)
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
    elif active_mode in ("remind", "reminders", "reminder"):
        target_tool = REMINDER_TOOL_PATH
    else:
        target_tool = REPORT_INDEXER_PATH
    return forward_command(target_tool, arguments)


if __name__ == "__main__":
    sys.exit(main())
