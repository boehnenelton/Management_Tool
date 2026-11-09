#!/data/data/com.termux/files/usr/bin/env python3
"""
Name:           report_indexer.py
Description:    Management Tool Suite: Research Papers & Technical Report Indexer (Mode 2)
Version:        1.4.0
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        MIT / BEJSON Standard
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

# Add lib/ to Python path
CURRENT_SCRIPT_DIR: Path = Path(__file__).resolve().parent
LIB_DIR: Path = CURRENT_SCRIPT_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stateful_context_engine import StatefulContextEngine

# Policy §8.1 Tri-Color Palette Constants
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"
COLOR_ANSI_RED: str = "\033[1;31m"
COLOR_RESET: str = "\033[0m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM
COLOR_WHITE_BOLD: str = "\033[1;37m"
COLOR_WHITE_PLAIN: str = "\033[0;37m"

IS_TTY: bool = sys.stdout.isatty() or sys.stderr.isatty()
ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and IS_TTY else ""
WHITE: str = COLOR_WHITE_BOLD if not NO_COLOR and IS_TTY else ""
NEUTRAL: str = COLOR_WHITE_PLAIN if not NO_COLOR and IS_TTY else ""
RESET: str = COLOR_RESET if not NO_COLOR and IS_TTY else ""


def print_positive(message: str) -> None:
    """Print positive status message in white lowercase."""
    print(f"{WHITE}[✓] {message.lower()}{RESET}")


def print_fail(message: str) -> None:
    """Print failure error message in #DE2626 UPPERCASE RED."""
    err_stream = sys.stderr
    print(f"{ACCENT}[✗] {message.upper()}{RESET}", file=err_stream)



def build_cli_parser() -> argparse.ArgumentParser:
    """Build pure CLI argument parser without TUI dependencies."""
    parser = argparse.ArgumentParser(
        prog="context_cli.py",
        description="Stateful Context CLI - Loaded Chamber Pattern for Multi-Mode Operations (No TUI, Pure CLI).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Modes:
  Mode 1 (logging):  BEJSON 105 Standards Logging & Log Sink Management
  Mode 2 (reports):  Research Papers & Report Tracking, Category Folders & Indexing
  Mode 3 (notes):    Categorized Notes & MFDB Notebook Manager
  Mode 4 (jobs):     Stateful Job Chamber & Urgent Deployment Manager

Workflow Examples:
  # Direct Management Router Invocations
  management_tool.py report --list-categories
  management_tool.py report --list-entries
  management_tool.py report --select-category Audits
  management_tool.py report --select-entry rep_009
  management_tool.py report --status
  management_tool.py report --action-view
  management_tool.py report --import my_paper.md --category AI --name deep_research.md
  management_tool.py report --query "architecture"
"""
    )

    parser.add_argument("-v", "--version", action="version", version="Management Tool Suite: Report Indexer v1.4.0")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON structured output for automation")

    # Mode Selection
    mode_group = parser.add_argument_group("Mode Configuration")
    mode_group.add_argument("-M", "--select-mode", type=str, metavar="<1|2|logging|reports>", help="Switch active mode (1=logging, 2=reports)")
    mode_group.add_argument("--list-modes", action="store_true", help="List available operational modes")

    # Phase 1: Discovery
    discovery_group = parser.add_argument_group("Phase 1: Discovery")
    discovery_group.add_argument("--list-categories", "--list-group", "--list-groups", action="store_true", dest="list_categories", help="List categories within active mode")
    discovery_group.add_argument("--list-entries", "--list-target", "--list-targets", action="store_true", dest="list_entries", help="Context-aware entry list (filtered by category if set)")

    # Phase 2: Target Lock
    lock_group = parser.add_argument_group("Phase 2: Target Lock (Loaded Chamber)")
    lock_group.add_argument("--select-category", "--select-categories", "--select-group", type=str, metavar="<name>", dest="select_category", help="Lock active category (clears entry)")
    lock_group.add_argument("--select-entry", "--select-target", type=str, metavar="<id_or_name>", dest="select_entry", help="Lock document or record entry into the chamber")
    lock_group.add_argument("--clear-category", "--clear-group", action="store_true", dest="clear_category", help="Clear active category and entry from chamber")
    lock_group.add_argument("--clear-entry", "--clear-target", action="store_true", dest="clear_entry", help="Unload entry from chamber while keeping category")
    lock_group.add_argument("--clear-all", "--clear", action="store_true", dest="clear_all", help="Clear all chamber selections")
    lock_group.add_argument("--status", "--info", action="store_true", dest="status", help="Print currently loaded chamber context")

    # Phase 3: Action Execution
    action_group = parser.add_argument_group("Phase 3: Execution Actions (Against Loaded Target)")
    action_group.add_argument("--action-view", action="store_true", help="View loaded document content or record payload")
    action_group.add_argument("--action-edit", action="store_true", help="Open loaded document in editor")
    action_group.add_argument("--action-pull", action="store_true", help="Pull/copy loaded document to destination or stdout")
    action_group.add_argument("--dest", "--destination", type=str, metavar="<path>", help="Destination directory for --action-pull")
    action_group.add_argument("--action-delete", action="store_true", help="Destroy loaded document/record and nullify chamber state")

    # Feature: Import & Query
    feature_group = parser.add_argument_group("Reports Tracking & Query Features")
    feature_group.add_argument("--import", "--import-file", type=str, metavar="<source.md>", dest="import_file", help="Import markdown file into category folder and index")
    feature_group.add_argument("--category", type=str, metavar="<name>", help="Target category for import (defaults to active chamber category)")
    feature_group.add_argument("--name", type=str, metavar="<filename.md>", help="Custom destination filename on import")
    feature_group.add_argument("--title", type=str, metavar="<title>", help="Custom document title on import")
    feature_group.add_argument("--query", "-q", type=str, metavar="<search_term>", help="Search research papers index by keyword")

    return parser


def print_status_banner(engine: StatefulContextEngine) -> None:
    """Print high-density 57-column status banner."""
    context = engine.get_active_context()
    mode = context["active_mode"]
    category = context["active_category"] or "(none)"
    entry = context["active_entry"] or "(empty - no entry loaded)"

    loaded = engine.get_loaded_entry()

    print("=" * 57)
    print(f" {ACCENT}STATEFUL CONTEXT CLI [LOADED CHAMBER]{RESET}")
    print("-" * 57)
    print(f" {ACCENT}MODE:{RESET}     {mode.upper():<16} {ACCENT}CATEGORY:{RESET} {category:<20}")
    print(f" {ACCENT}ENTRY:{RESET}    {entry:<46}")
    if loaded and mode == "reports":
        print("-" * 57)
        print(f" {ACCENT}TITLE:{RESET}    {loaded.get('doc_title', '')[:46]}")
        print(f" {ACCENT}FILE:{RESET}     {loaded.get('file_name', '')[:46]}")
        print(f" {ACCENT}PATH:{RESET}     {loaded.get('doc_path', '')[:46]}")
        print(f" {ACCENT}SIZE:{RESET}     {loaded.get('file_size_kb', 0)} KB")
    print("=" * 57)


def print_tabular_entries(entries_list: list[dict[str, Any]], mode: str) -> None:
    """Format entries into clean 57-column output."""
    if not entries_list:
        print(f" {ACCENT}[!]{RESET} No entries found matching criteria.")
        return

    print("=" * 57)
    if mode == "reports":
        print(f" {ACCENT}{'ID':<10} {'CATEGORY':<14} {'TITLE / FILE':<30}{RESET}")
        print("-" * 57)
        for item in entries_list:
            doc_id = item["doc_id"][:9]
            cat = item["category_name"][:13]
            name = (item["doc_title"] or item["file_name"])[:29]
            print(f" {doc_id:<10} {cat:<14} {name:<30}")
    else:
        print(f" {ACCENT}{'ENTRY_ID':<20} {'CATEGORY':<15} {'PATH':<19}{RESET}")
        print("-" * 57)
        for item in entries_list:
            eid = item.get("entry_id", "")[:19]
            cat = item.get("category_name", "")[:14]
            pth = os.path.basename(item.get("doc_path", ""))[:18]
            print(f" {eid:<20} {cat:<15} {pth:<19}")
    print("=" * 57)


def main() -> int:
    """Pure CLI entrypoint router."""
    parser = build_cli_parser()
    
    # If no arguments passed, print status banner and help guide (NO TUI)
    if len(sys.argv) == 1:
        engine = StatefulContextEngine()
        print_status_banner(engine)
        print()
        parser.print_help()
        return 0

    args = parser.parse_args()
    engine = StatefulContextEngine()

    try:
        # Mode Selection
        if args.select_mode:
            new_mode = engine.select_mode(args.select_mode)
            if args.json:
                print(json.dumps({"status": "success", "active_mode": new_mode}, indent=2))
            else:
                print_positive(f"mode switched to: [{new_mode.lower()}] (category and entry cleared)")
            return 0

        if args.list_modes:
            modes = engine.list_modes()
            if args.json:
                print(json.dumps({"modes": modes}, indent=2))
            else:
                print(f"{NEUTRAL}{'=' * 57}{RESET}")
                print(f" {ACCENT}SUPPORTED OPERATIONAL MODES{RESET}")
                print(f"{NEUTRAL}{'-' * 57}{RESET}")
                for item in modes:
                    print(f" [{ACCENT}{item['mode_id']}{RESET}] {item['mode_name']:<10} - {item['description']}")
                print(f"{NEUTRAL}{'=' * 57}{RESET}")
            return 0

        # Phase 1: Discovery
        if args.list_categories:
            categories = engine.list_categories()
            if args.json:
                print(json.dumps({"mode": engine.get_active_mode(), "categories": categories}, indent=2))
            else:
                mode = engine.get_active_mode()
                print(f"{ACCENT}Categories in mode [{mode}]:{RESET}")
                for category_item in categories:
                    print(f"  • {category_item}")
            return 0

        if args.list_entries:
            entries = engine.list_entries()
            if args.json:
                print(json.dumps({"entries": entries}, indent=2))
            else:
                active_category = engine.get_active_context()["active_category"]
                cat_desc = f"category '{active_category}'" if active_category else "all categories"
                print(f"{ACCENT}Entries in {cat_desc}:{RESET}")
                print_tabular_entries(entries, engine.get_active_mode())
            return 0

        # Phase 2: Target Lock
        if args.select_category:
            new_state = engine.select_category(args.select_category)
            if args.json:
                print(json.dumps(new_state, indent=2))
            else:
                print_positive(f"category locked: {args.select_category} (entry cleared)")
            return 0

        if args.select_entry:
            new_state = engine.select_entry(args.select_entry)
            loaded = engine.get_loaded_entry()
            if args.json:
                print(json.dumps({"state": new_state, "entry": loaded}, indent=2))
            else:
                print_positive(f"entry locked into chamber: {args.select_entry}")
                if loaded and engine.get_active_mode() == "reports":
                    print(f"    Title:    {loaded.get('doc_title')}")
                    print(f"    Category: {loaded.get('category_name')}")
                    print(f"    Path:     {loaded.get('doc_path')}")
            return 0

        if args.clear_category:
            new_state = engine.clear_category()
            if args.json:
                print(json.dumps(new_state, indent=2))
            else:
                print_positive("active category and entry cleared.")
            return 0

        if args.clear_entry:
            new_state = engine.clear_entry()
            if args.json:
                print(json.dumps(new_state, indent=2))
            else:
                print_positive("active entry unloaded from chamber.")
            return 0

        if args.clear_all:
            new_state = engine.clear_all()
            if args.json:
                print(json.dumps(new_state, indent=2))
            else:
                print_positive("entire chamber context cleared.")
            return 0

        if args.status:
            if args.json:
                print(json.dumps({
                    "context": engine.get_active_context(),
                    "loaded_entry": engine.get_loaded_entry()
                }, indent=2))
            else:
                print_status_banner(engine)
            return 0

        # Import Feature
        if args.import_file:
            result = engine.import_report_file(
                source_markdown_path=args.import_file,
                category_name=args.category,
                custom_file_name=args.name,
                custom_title=args.title
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print_positive("document imported successfully!")
                print(f"    Doc ID:      {result['doc_id']}")
                print(f"    Category:    {result['category']}")
                print(f"    File:        {result['file_name']}")
                print(f"    Title:       {result['title']}")
                print(f"    Destination: {result['destination_path']}")
                print(f"    Size:        {result['size_kb']} KB")
                print(f"{ACCENT}[*] Chamber Status:{RESET} Automatically locked into chamber as active entry.")
            return 0

        # Query Feature
        if args.query:
            results = engine.query_reports(args.query)
            if args.json:
                print(json.dumps({"query": args.query, "matches": results}, indent=2))
            else:
                print(f"{ACCENT}Query results for '{args.query}':{RESET} ({len(results)} matches)")
                print_tabular_entries(results, "reports")
            return 0

        # Phase 3: Action Execution
        if args.action_view:
            result = engine.action_view()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                entry = result["entry"]
                print("=" * 57)
                print(f" {ACCENT}VIEW: {entry.get('doc_title', entry.get('file_name', ''))}{RESET}")
                print(f" Path: {entry.get('doc_path', '')}")
                print("-" * 57)
                print(result["content"])
                print("=" * 57)
            return 0

        if args.action_pull:
            result = engine.action_pull(destination_directory=args.dest)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get("destination_path"):
                    print_positive(f"document pulled to: {result['destination_path']}")
                else:
                    clip_msg = "Path copied to Termux clipboard!" if result.get("path_copied_to_clipboard") else ""
                    print_positive(f"document ready: {result['source_path']} {clip_msg}")
            return 0

        if args.action_edit:
            result = engine.action_edit()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                editor_cmd = result["editor"]
                file_target = result["file_path"]
                print(f"{ACCENT}[*] Launching editor:{RESET} {editor_cmd} \"{file_target}\"")
                os.system(f"{editor_cmd} \"{file_target}\"")
            return 0

        if args.action_delete:
            result = engine.action_delete()
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print_positive(f"document '{result['deleted_entry_id']}' destroyed.")
                print(f"    File removed: {result['file_deleted']}")
                print(f"{ACCENT}[*] Chamber Status:{RESET} Active entry nullified to prevent ghost actions.")
            return 0

        # Fallback
        parser.print_help()
        return 1

    except Exception as execution_error:
        if args.json:
            print(json.dumps({"error": str(execution_error)}, indent=2))
        else:
            print_fail(f"{execution_error}")
        return 1
        return 1


if __name__ == "__main__":
    sys.exit(main())
