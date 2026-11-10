#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : notes_tool.py
Rel. Path   : notes_tool.py
Family      : Notes / Management Subsystem
Purpose     : High-density, zero-SQL Categorized Notes & Notebook Management Engine
              backed by a dedicated BEJSON 104a MFDB (Multi-File Database v1.31).
              Implements the Loaded Chamber Pattern for persistent category and note
              selection, note creation, editing, category transfers, tag management,
              keyword querying, and Markdown import/export with hashtag metadata headers.
Version     : 1.1.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-03
RELATIONAL_ID : bb348f5c-4862-4e96-b2ea-f57092c2c14d
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Self-Locating Path Preambles (Policy §4.1) ────────────────────────────────
def get_script_path() -> Path:
    return Path(__file__).resolve().parent

SCRIPT_PATH: Path = get_script_path()
SUITE_ROOT: Path = SCRIPT_PATH.parent.parent if SCRIPT_PATH.parent.name == "tools" else SCRIPT_PATH
LOCAL_LIB_DIRECTORY: Path = SUITE_ROOT / "lib"
LOCAL_CONFIG_DIRECTORY: Path = SUITE_ROOT / "config"
LOCAL_DATA_DIRECTORY: Path = SUITE_ROOT / "data"
LOCAL_EXPORTS_DIRECTORY: Path = SUITE_ROOT / "exports"

if str(LOCAL_LIB_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(LOCAL_LIB_DIRECTORY))

from notes_mfdb_engine import NotesMFDBEngine, slugify_text
from notes_site_exporter import NotesSiteExporter

# ── Policy §8.1 Tri-Color Palette & 57-Column Discipline ─────────────────────
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"  # Policy §8.1 #DE2626 Truecolor
COLOR_ANSI_RED: str = "\033[1;31m"          # ANSI Bold Red fallback
COLOR_RESET: str = "\033[0m"
COLOR_DIM: str = "\033[2m"
COLOR_BOLD: str = "\033[1m"
COLOR_WHITE_BOLD: str = "\033[1;37m"
COLOR_WHITE_PLAIN: str = "\033[0;37m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM

IS_TTY: bool = sys.stdout.isatty() or sys.stderr.isatty()
ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and IS_TTY else ""
RESET: str = COLOR_RESET if not NO_COLOR and IS_TTY else ""
DIM: str = COLOR_DIM if not NO_COLOR and IS_TTY else ""
BOLD: str = COLOR_BOLD if not NO_COLOR and IS_TTY else ""
WHITE: str = COLOR_WHITE_BOLD if not NO_COLOR and IS_TTY else ""
NEUTRAL: str = COLOR_WHITE_PLAIN if not NO_COLOR and IS_TTY else ""

DIVIDER_57: str = "=" * 57
SUBDIVIDER_57: str = "-" * 57


def print_positive(message: str) -> None:
    """Print positive status message in white lowercase."""
    print(f"{WHITE}[✓] {message.lower()}{RESET}")


def print_fail(message: str) -> None:
    """Print failure error message in #DE2626 UPPERCASE RED."""
    err_stream = sys.stderr
    print(f"{ACCENT}[✗] {message.upper()}{RESET}", file=err_stream)



def print_status_banner(engine: NotesMFDBEngine) -> None:
    """Print high-density 57-column status banner showing chamber state."""
    context = engine.get_active_context()
    cat_name: str = context["active_category"] or "(all categories)"
    loaded_note = engine.get_loaded_note()

    print(DIVIDER_57)
    print(f" {ACCENT}NOTES MANAGEMENT SYSTEM [MFDB CHAMBER]{RESET}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}MODE:{RESET}     NOTES            {ACCENT}CATEGORY:{RESET} {cat_name[:18]:<18}")
    if loaded_note:
        note_id: str = loaded_note["note_id"]
        title: str = loaded_note["title"]
        tags_display: str = " ".join([f"#{t}" for t in loaded_note["tags"]]) or "(no tags)"
        words: int = len(loaded_note["content"].split())
        print(f" {ACCENT}NOTE ID:{RESET}  {note_id:<16} {ACCENT}WORDS:{RESET}    {words:<18}")
        print(f" {ACCENT}TITLE:{RESET}    {title[:45]}")
        print(f" {ACCENT}TAGS:{RESET}     {tags_display[:45]}")
        print(f" {ACCENT}UPDATED:{RESET}  {loaded_note['updated_at'][:19]}")
    else:
        print(f" {ACCENT}NOTE:{RESET}     (empty - no note loaded in chamber)")
    print(DIVIDER_57)


def print_categories_table(categories: List[Dict[str, Any]]) -> None:
    """Print categories in clean 57-column layout."""
    print(DIVIDER_57)
    print(f" {ACCENT}{'ID':<10} {'CATEGORY NAME':<26} {'NOTES':<8} {'SLUG'}{RESET}")
    print(SUBDIVIDER_57)
    if not categories:
        print(f" {DIM}No categories found.{RESET}")
    else:
        for cat in categories:
            cid: str = cat["cat_id"][:9]
            cname: str = cat["cat_name"][:25]
            cnt: int = cat["note_count"]
            slug: str = cat["cat_slug"][:10]
            print(f" {cid:<10} {cname:<26} {cnt:<8} {slug}")
    print(DIVIDER_57)


def print_notes_table(notes: List[Dict[str, Any]], active_category: Optional[str] = None) -> None:
    """Print notes in clean 57-column layout."""
    scope_desc = f"Category: '{active_category}'" if active_category else "All Categories"
    print(DIVIDER_57)
    print(f" {ACCENT}NOTES CATALOG{RESET} {f'[{scope_desc}]':>41}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}{'ID':<10} {'CATEGORY':<14} {'TITLE / SLUG':<29}{RESET}")
    print(SUBDIVIDER_57)
    if not notes:
        print(f" {DIM}No notes found matching criteria.{RESET}")
    else:
        for note in notes:
            nid: str = note["note_id"][:9]
            ncat: str = note["cat_name"][:13]
            ntitle: str = note["title"][:28]
            print(f" {nid:<10} {ncat:<14} {ntitle:<29}")
    print(DIVIDER_57)


def print_configuration_table(config: Dict[str, Any]) -> None:
    """Print configuration parameters in clean 57-column layout."""
    print(DIVIDER_57)
    print(f" {ACCENT}NOTES SYSTEM & SITE CONFIGURATION{RESET}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}{'SETTING':<22} {'VALUE'}{RESET}")
    print(SUBDIVIDER_57)
    for key, val in config.items():
        k_str = key.upper()[:21]
        v_str = str(val)[:32]
        print(f" {k_str:<22} {v_str}")
    print(DIVIDER_57)


def build_cli_parser() -> argparse.ArgumentParser:
    """Build pure CLI argument parser for Notes Manager."""
    parser = argparse.ArgumentParser(
        prog="notes_tool.py",
        description="Categorized Notes Manager with MFDB v1.31 and Loaded Chamber State.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Workflows:
  # 1. Category Operations
  ./notes_tool.py --list-categories
  ./notes_tool.py --select-category "Work"         # Lock category into chamber
  ./notes_tool.py --category-create "Projects"     # Create category & lock it
  ./notes_tool.py --category-edit "Projects" --new-name "NewProjects"
  ./notes_tool.py --category-delete "OldCat"       # Reassigns notes to General

  # 2. Note Operations (Create, Select, Edit, Set Category)
  ./notes_tool.py --note-create -t "System Spec" -c "Details..." --tags "arch,bejson"
  ./notes_tool.py --list-notes                     # Filtered by active category
  ./notes_tool.py --select-note "System Spec"      # Lock note into chamber
  ./notes_tool.py --note-edit --new-title "Updated Spec"
  ./notes_tool.py --set-category "Work"            # Move note to another category
  ./notes_tool.py --add-tags "security,v1"         # Append tags
  ./notes_tool.py --remove-tags "v1"               # Remove tags
  ./notes_tool.py --note-delete                    # Delete loaded note and nullify chamber

  # 3. Markdown Import & Export
  ./notes_tool.py --import my_note.md --category "Research"
  ./notes_tool.py --export                         # Exports formatted markdown with #tags
  ./notes_tool.py --action-view                    # View loaded note in terminal

  # 4. Search & Telemetry
  ./notes_tool.py --query "architecture"           # Rank-ordered search
  ./notes_tool.py --status                         # Print active chamber status

  # 5. Configuration & Static Site Generation
  ./notes_tool.py --config                         # Display system & site settings
  ./notes_tool.py --config-set site_title "My Hub" # Update configuration setting
  ./notes_tool.py --export-site                    # Build complete static HTML site
"""
    )

    parser.add_argument("-v", "--version", action="version", version="Notes Tool v1.1.0 (MFDB v1.31)")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON structured output")

    # Chamber Status & Inspection
    status_group = parser.add_argument_group("Chamber Telemetry")
    status_group.add_argument("--status", "--info", action="store_true", help="Print active chamber context status")
    status_group.add_argument("--clear-category", action="store_true", help="Unload active category and active note")
    status_group.add_argument("--clear-note", action="store_true", help="Unload active note while preserving category")
    status_group.add_argument("--clear-all", "--clear", action="store_true", help="Clear all chamber selections")

    # Category Management
    cat_group = parser.add_argument_group("Category Management")
    cat_group.add_argument("--list-categories", "--list-cats", action="store_true", help="List all registered categories")
    cat_group.add_argument("--select-category", "--cat", type=str, metavar="<name|id>", help="Lock active category into chamber")
    cat_group.add_argument("--category-create", "--create-category", type=str, metavar="<name>", help="Create new category")
    cat_group.add_argument("--category-edit", "--edit-category", type=str, metavar="<name|id>", help="Select category to edit")
    cat_group.add_argument("--new-name", type=str, metavar="<name>", help="New name for category being edited")
    cat_group.add_argument("--desc", type=str, metavar="<description>", help="Description for category create/edit")
    cat_group.add_argument("--category-delete", "--delete-category", type=str, metavar="<name|id>", help="Delete category")
    cat_group.add_argument("--reassign", type=str, metavar="<cat_name>", default="General", help="Fallback category for deleted category notes")

    # Note Management
    note_group = parser.add_argument_group("Note Management")
    note_group.add_argument("--list-notes", "--list", action="store_true", help="List notes (filtered by active category if set)")
    note_group.add_argument("--select-note", "--note", type=str, metavar="<title|id>", help="Lock note into chamber")
    note_group.add_argument("--note-new", "--note-create", "--create-note", action="store_true", help="Create new note")
    note_group.add_argument("-t", "--title", type=str, metavar="<title>", help="Note title")
    note_group.add_argument("-c", "--content", type=str, metavar="<content>", help="Note content text")
    note_group.add_argument("--category", type=str, metavar="<category>", help="Category for new note (defaults to chamber)")
    note_group.add_argument("--tags", type=str, metavar="<tag1,tag2>", help="Comma-separated tags for note")

    note_group.add_argument("--note-edit", "--edit-note", action="store_true", help="Edit loaded note (or specify with --note)")
    note_group.add_argument("--new-title", type=str, metavar="<title>", help="New title for note edit")
    note_group.add_argument("--new-content", type=str, metavar="<content>", help="New content for note edit")
    note_group.add_argument("--set-category", type=str, metavar="<category>", help="Change category of loaded note")

    note_group.add_argument("--note-delete", "--delete-note", action="store_true", help="Delete loaded note and nullify chamber")

    # Tag Operations
    tag_group = parser.add_argument_group("Tag Management")
    tag_group.add_argument("--add-tag", "--add-tags", type=str, metavar="<tags>", help="Add comma-separated tag(s) to loaded note")
    tag_group.add_argument("--remove-tag", "--remove-tags", type=str, metavar="<tags>", help="Remove comma-separated tag(s) from loaded note")

    # Actions: View, Pull, Edit in Editor, Export, Import, Static Site
    action_group = parser.add_argument_group("Execution Actions")
    action_group.add_argument("--action-view", "--view", action="store_true", help="Display loaded note content and telemetry")
    action_group.add_argument("--action-edit", action="store_true", help="Open loaded note content in system $EDITOR")
    action_group.add_argument("--action-pull", "--pull", action="store_true", help="Pull loaded note markdown to destination")
    action_group.add_argument("--dest", "--destination", type=str, metavar="<path>", help="Destination path for pull/export")
    action_group.add_argument("--export", "--action-export", action="store_true", help="Export loaded note to formatted Markdown")
    action_group.add_argument("--import", "--import-file", type=str, metavar="<file.md>", dest="import_file", help="Import markdown note into MFDB")
    action_group.add_argument("--export-site", "--build-site", action="store_true", help="Compile complete static HTML website for all notes into taxonomy hierarchy")
    action_group.add_argument("--site-dir", type=str, metavar="<path>", help="Destination directory for static site export (default: exports/notes_site)")
    action_group.add_argument("--web", "--serve", action="store_true", help="Launch interactive Flask web editor workspace on localhost (Policy §8.1-§8.7)")
    action_group.add_argument("--port", type=int, default=5050, help="Port for web server (default: 5050)")

    # Configuration Management
    config_group = parser.add_argument_group("Configuration Management")
    config_group.add_argument("--config", action="store_true", help="Display current system and static site configuration")
    config_group.add_argument("--config-set", nargs=2, metavar=("<key>", "<value>"), help="Set configuration key to value")

    # Query
    query_group = parser.add_argument_group("Search & Query")
    query_group.add_argument("-q", "--query", type=str, metavar="<search_term>", help="Search notes by keyword across title, tags, and content")

    return parser


def handle_export(engine: NotesMFDBEngine, dest_path: Optional[str], as_json: bool) -> int:
    """Export loaded note to markdown file with #tags header."""
    loaded_note = engine.get_loaded_note()
    if not loaded_note:
        print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
        return 1

    export_result = engine.export_note(loaded_note["note_id"], destination_path=dest_path)
    if as_json:
        print(json.dumps(export_result, indent=2))
    else:
        print_positive(f"exported note to: {export_result['destination_path']}")
        print(f"    Title:    {export_result['title']}")
        print(f"    Category: {export_result['category']}")
        print(f"    Tags:     {' '.join(['#' + t for t in export_result['tags']])}")
    return 0


def main() -> int:
    parser = build_cli_parser()

    if len(sys.argv) == 1:
        engine = NotesMFDBEngine()
        print_status_banner(engine)
        print()
        parser.print_help()
        return 0

    args = parser.parse_args()
    engine = NotesMFDBEngine()

    try:
        # 1. Chamber Status & Inspection
        if args.status:
            if args.json:
                print(json.dumps({
                    "context": engine.get_active_context(),
                    "loaded_note": engine.get_loaded_note(),
                    "loaded_category": engine.get_loaded_category()
                }, indent=2))
            else:
                print_status_banner(engine)
            return 0

        if args.clear_category:
            ctx = engine.clear_category()
            if args.json:
                print(json.dumps(ctx, indent=2))
            else:
                print(f"{ACCENT}[*] Active category and note unloaded from chamber.{RESET}")
            return 0

        if args.clear_note:
            ctx = engine.clear_note()
            if args.json:
                print(json.dumps(ctx, indent=2))
            else:
                print(f"{ACCENT}[*] Active note unloaded from chamber.{RESET}")
            return 0

        if args.clear_all:
            ctx = engine.clear_all()
            if args.json:
                print(json.dumps(ctx, indent=2))
            else:
                print(f"{ACCENT}[*] Entire chamber context cleared.{RESET}")
            return 0

        # 2. Category Operations
        if args.list_categories:
            cats = engine.list_categories()
            if args.json:
                print(json.dumps(cats, indent=2))
            else:
                print_categories_table(cats)
            return 0

        if args.select_category:
            cat = engine.select_category(args.select_category)
            if args.json:
                print(json.dumps(cat, indent=2))
            else:
                print_positive(f"category locked into chamber: {cat['cat_name']} (note cleared)")
            return 0

        if args.category_create:
            new_cat = engine.create_category(args.category_create, description=args.desc or "")
            if args.json:
                print(json.dumps(new_cat, indent=2))
            else:
                print_positive(f"category created & locked: {new_cat['cat_name']} (ID: {new_cat['cat_id']})")
            return 0

        if args.category_edit:
            updated_cat = engine.update_category(
                args.category_edit,
                new_name=args.new_name,
                new_description=args.desc
            )
            if args.json:
                print(json.dumps(updated_cat, indent=2))
            else:
                print_positive(f"category updated: {updated_cat['cat_name']} (ID: {updated_cat['cat_id']})")
            return 0

        if args.category_delete:
            del_res = engine.delete_category(args.category_delete, reassign_to_category=args.reassign)
            if args.json:
                print(json.dumps(del_res, indent=2))
            else:
                print_positive(f"category deleted: {del_res['deleted_category_name']}")
                print(f"    Reassigned {del_res['reassigned_notes']} note(s) to '{del_res['reassigned_to']}'")
            return 0

        # 3. Note Selection & Creation
        if args.select_note:
            note_rec = engine.select_note(args.select_note)
            if args.json:
                print(json.dumps(note_rec, indent=2))
            else:
                print_positive(f"note locked into chamber: {note_rec['title']} (ID: {note_rec['note_id']})")
                print(f"    Category: {note_rec['cat_name']}")
                print(f"    Tags:     {' '.join(['#' + t for t in note_rec['tags']]) or '(none)'}")
            return 0

        if args.note_new:
            # Determine title and content
            note_title: str = args.title or ""
            note_content: str = args.content or ""

            if not note_title:
                print_fail("NOTE TITLE REQUIRED (-T / --TITLE).")
                return 1

            if not note_content and not sys.stdin.isatty():
                note_content = sys.stdin.read().strip()

            new_note = engine.create_note(
                title=note_title,
                content=note_content,
                category_name=args.category,
                tags=[t.strip() for t in args.tags.split(",")] if args.tags else []
            )

            if args.json:
                print(json.dumps(new_note, indent=2))
            else:
                print_positive(f"note created & locked in chamber: {new_note['title']}")
                print(f"    ID:       {new_note['note_id']}")
                print(f"    Category: {new_note['cat_name']}")
                print(f"    Tags:     {' '.join(['#' + t for t in new_note['tags']]) or '(none)'}")
            return 0

        # 4. Note Listing
        if args.list_notes:
            notes = engine.list_notes()
            active_cat = engine.get_active_context()["active_category"]
            if args.json:
                print(json.dumps(notes, indent=2))
            else:
                print_notes_table(notes, active_category=active_cat)
            return 0

        # 5. Note Editing & Category Transfer
        if args.note_edit:
            target_note = engine.get_loaded_note()
            if not target_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            edit_res = engine.update_note(
                target_note["note_id"],
                new_title=args.new_title,
                new_content=args.new_content,
                new_category_name=args.category,
                new_tags=[t.strip() for t in args.tags.split(",")] if args.tags else None
            )
            if args.json:
                print(json.dumps(edit_res, indent=2))
            else:
                print_positive(f"note updated: {edit_res['title']}")
                print(f"    Category: {edit_res['cat_name']}")
                print(f"    Tags:     {' '.join(['#' + t for t in edit_res['tags']]) or '(none)'}")
            return 0

        if args.set_category:
            target_note = engine.get_loaded_note()
            if not target_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            move_res = engine.set_note_category(target_note["note_id"], args.set_category)
            if args.json:
                print(json.dumps(move_res, indent=2))
            else:
                print_positive(f"note category set to: {move_res['cat_name']}")
                print(f"    Note: {move_res['title']} (ID: {move_res['note_id']})")
            return 0

        # 6. Tag Operations
        if args.add_tag:
            target_note = engine.get_loaded_note()
            if not target_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            tags_to_add = [t.strip() for t in args.add_tag.split(",") if t.strip()]
            tag_res = engine.add_note_tags(target_note["note_id"], tags_to_add)
            if args.json:
                print(json.dumps(tag_res, indent=2))
            else:
                print_positive(f"added tag(s): {', '.join(tags_to_add)}")
                print(f"    Active Tags: {' '.join(['#' + t for t in tag_res['tags']])}")
            return 0

        if args.remove_tag:
            target_note = engine.get_loaded_note()
            if not target_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            tags_to_rm = [t.strip() for t in args.remove_tag.split(",") if t.strip()]
            tag_res = engine.remove_note_tags(target_note["note_id"], tags_to_rm)
            if args.json:
                print(json.dumps(tag_res, indent=2))
            else:
                print_positive(f"removed tag(s): {', '.join(tags_to_rm)}")
                print(f"    Active Tags: {' '.join(['#' + t for t in tag_res['tags']]) or '(none)'}")
            return 0

        # 7. Note Deletion
        if args.note_delete:
            target_note = engine.get_loaded_note()
            if not target_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            del_res = engine.delete_note(target_note["note_id"])
            if args.json:
                print(json.dumps(del_res, indent=2))
            else:
                print_positive(f"note deleted: {del_res['deleted_title']} (ID: {del_res['deleted_note_id']})")
                print(f"{ACCENT}[*] Chamber state:{RESET} Nullified (no ghost references).")
            return 0

        # 8. Execution Actions: View, Pull, Export, Import
        if args.action_view:
            loaded_note = engine.get_loaded_note()
            if not loaded_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
            print(f" {ACCENT}NOTE TELEMETRY & CONTENT{RESET}")
            print(f"{NEUTRAL}{SUBDIVIDER_57}{RESET}")
            print(f" {ACCENT}ID:{RESET}       {NEUTRAL}{loaded_note['note_id']}{RESET}")
            print(f" {ACCENT}TITLE:{RESET}    {NEUTRAL}{loaded_note['title']}{RESET}")
            print(f" {ACCENT}CATEGORY:{RESET} {NEUTRAL}{loaded_note['cat_name']}{RESET}")
            print(f" {ACCENT}TAGS:{RESET}     {NEUTRAL}{' '.join(['#' + t for t in loaded_note['tags']]) or '(none)'}{RESET}")
            print(f" {ACCENT}WORDS:{RESET}    {NEUTRAL}{len(loaded_note['content'].split())}{RESET}")
            print(f" {ACCENT}UPDATED:{RESET}  {NEUTRAL}{loaded_note['updated_at']}{RESET}")
            print(f"{NEUTRAL}{SUBDIVIDER_57}{RESET}")
            print(loaded_note["content"])
            print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
            return 0

        if args.export:
            return handle_export(engine, args.dest, args.json)

        if args.web:
            import notes_web_server
            sys.argv = [sys.argv[0], "--port", str(args.port)]
            return notes_web_server.main()

        if args.export_site:
            custom_dir = Path(args.site_dir).resolve() if args.site_dir else None
            site_builder = NotesSiteExporter(engine, output_directory=custom_dir)
            build_report = site_builder.export_entire_site()
            if args.json:
                print(json.dumps(build_report, indent=2))
            else:
                print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
                print(f" {ACCENT}STATIC DOCUMENTATION SITE COMPILED{RESET}")
                print(f"{NEUTRAL}{SUBDIVIDER_57}{RESET}")
                print(f" {ACCENT}DESTINATION:{RESET}  {NEUTRAL}{build_report['output_directory']}{RESET}")
                print(f" {ACCENT}CATEGORIES:{RESET}   {NEUTRAL}{build_report['categories_built']}{RESET}")
                print(f" {ACCENT}NOTES BUILT:{RESET}  {NEUTRAL}{build_report['notes_built']}{RESET}")
                print(f" {ACCENT}PORTAL HUB:{RESET}   {NEUTRAL}{build_report['portal_index']}{RESET}")
                print(f" {ACCENT}SITE MAP:{RESET}     {NEUTRAL}{build_report['sitemap_html']}{RESET}")
                print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
            return 0

        if args.action_pull:
            loaded_note = engine.get_loaded_note()
            if not loaded_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            dest_target = args.dest or str(LOCAL_EXPORTS_DIRECTORY / f"{loaded_note['slug']}.md")
            export_res = engine.export_note(loaded_note["note_id"], destination_path=dest_target)

            clipboard_copied: bool = False
            if shutil.which("termux-clipboard-set"):
                try:
                    proc = subprocess.Popen(["termux-clipboard-set"], stdin=subprocess.PIPE)
                    proc.communicate(input=export_res["rendered_content"].encode("utf-8"))
                    if proc.returncode == 0:
                        clipboard_copied = True
                except Exception:
                    pass

            if args.json:
                export_res["clipboard_copied"] = clipboard_copied
                print(json.dumps(export_res, indent=2))
            else:
                print_positive(f"note pulled to: {export_res['destination_path']}")
                if clipboard_copied:
                    print(f"    {ACCENT}[*]{RESET} Content copied to Termux clipboard.")
            return 0

        if args.action_edit:
            loaded_note = engine.get_loaded_note()
            if not loaded_note:
                print_fail("NO NOTE LOADED IN CHAMBER. USE --SELECT-NOTE FIRST.")
                return 1

            editor_exe = os.getenv("EDITOR", "nano")
            # Write temporary file for editing
            temp_edit_file = LOCAL_DATA_DIRECTORY / f"edit_{loaded_note['note_id']}.md"
            with open(temp_edit_file, "w", encoding="utf-8") as f:
                f.write(loaded_note["content"])

            subprocess.run([editor_exe, str(temp_edit_file)])

            # Read back content
            if temp_edit_file.exists():
                with open(temp_edit_file, "r", encoding="utf-8") as f:
                    new_content = f.read()
                temp_edit_file.unlink(missing_ok=True)
                engine.update_note(loaded_note["note_id"], new_content=new_content)
                print_positive("note updated from editor.")
            return 0

        if args.import_file:
            imp_res = engine.import_markdown_file(
                source_file_path=args.import_file,
                category_name=args.category,
                custom_title=args.title,
                custom_tags=[t.strip() for t in args.tags.split(",")] if args.tags else None
            )
            if args.json:
                print(json.dumps(imp_res, indent=2))
            else:
                print_positive("markdown file imported into mfdb!")
                print(f"    ID:       {imp_res['note_id']}")
                print(f"    Title:    {imp_res['title']}")
                print(f"    Category: {imp_res['cat_name']}")
                print(f"    Tags:     {' '.join(['#' + t for t in imp_res['tags']]) or '(none)'}")
                print(f"{ACCENT}[*] Chamber status:{RESET} Automatically locked into chamber as active note.")
            return 0

        # 9. Query & Search
        if args.query:
            query_results = engine.query_notes(args.query)
            if args.json:
                print(json.dumps(query_results, indent=2))
            else:
                print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
                print(f" {ACCENT}QUERY RESULTS:{RESET} '{args.query}' {f'({len(query_results)} found)':>30}")
                print(f"{NEUTRAL}{SUBDIVIDER_57}{RESET}")
                if not query_results:
                    print(f" {DIM}No matching notes found.{RESET}")
                else:
                    for res in query_results:
                        score = res.get("match_score", 0)
                        tags_disp = " ".join([f"#{t}" for t in res["tags"]])
                        print(f" [{ACCENT}{res['note_id']}{RESET}] {BOLD}{res['title'][:32]}{RESET} (Score: {score})")
                        print(f"   Category: {res['cat_name']:<16} Tags: {tags_disp[:24]}")
                        preview = res["content"].strip().replace("\n", " ")[:48]
                        if preview:
                            print(f"   {DIM}{preview}...{RESET}")
                        print(f"{NEUTRAL}{SUBDIVIDER_57}{RESET}")
                print(f"{NEUTRAL}{DIVIDER_57}{RESET}")
            return 0

        # 10. Configuration Management
        if args.config:
            cfg = engine.get_configuration()
            if args.json:
                print(json.dumps(cfg, indent=2))
            else:
                print_configuration_table(cfg)
            return 0

        if args.config_set:
            setting_key, raw_setting_val = args.config_set
            parsed_val: Any = raw_setting_val
            lower_val = raw_setting_val.lower()
            if lower_val == "true":
                parsed_val = True
            elif lower_val == "false":
                parsed_val = False
            else:
                try:
                    parsed_val = int(raw_setting_val)
                except ValueError:
                    try:
                        parsed_val = float(raw_setting_val)
                    except ValueError:
                        parsed_val = raw_setting_val

            updated_cfg = engine.set_config_value(setting_key, parsed_val)
            if args.json:
                print(json.dumps({
                    "status": "success",
                    "key": setting_key,
                    "value": parsed_val
                }, indent=2))
            else:
                print_positive(f"configuration updated: {setting_key} = {parsed_val}")
            return 0

        # If none of the specific flags matched, show status and help
        print_status_banner(engine)
        print()
        parser.print_help()
        return 0

    except Exception as error_instance:
        print_fail(f"{error_instance}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
