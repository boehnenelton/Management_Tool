#!/usr/bin/env python3
"""
Tool Name   : logging_tool.py
Rel. Path   : logging_tool.py
Family      : Standards / Tools
Purpose     : Command-line interface and management engine for BEJSON 105 Standards
              standardized logging (schema v3, 17 columns). Manages daily-partitioned
              global log files (Log-<YYYY-MM-DD>.bejson) in /storage/emulated/0/Admin/System/Global_Logs,
              supporting write, query/read, multi-format export, structural audit,
              directory cataloging, and automated archiving. Enforces Policy §8.1 #DE2626
              Truecolor and 57-column terminal user interface discipline.
Version     : 1.2.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-10-31
RELATIONAL_ID : b1f72944-934d-4a11-b4ef-cf24785b8390
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Python 3.10+ Runtime Guard ──────────────────────────────────────────────
if sys.version_info < (3, 10):
    sys.stderr.write("Fatal Error: Python 3.10+ is strictly required.\n")
    sys.exit(1)

# ── Self-Locating Path Preambles ─────────────────────────────────────────────
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

# ── Local Standards Family Imports ──────────────────────────────────────────
import lib_bejson_Standards_registry as standards_registry
import lib_bejson_Standards_validator as standards_validator
import lib_bejson_Standards_export as standards_export
import lib_bejson_Standards_errors as standards_errors
import lib_bejson_Standards_core as standards_core
from lib_bejson_Core_bejson_core import bejson_core_load_file, bejson_core_get_field_map
from lib_log_report_generator import generate_log_markdown_report, export_log_html_report

TOOL_VERSION: str = "1.3.1"
TOOL_AUTHOR: str = "Elton Boehnen"
TOOL_CONTACT: str = "boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton"

# ── TUI Telemetry & Color Discipline (Policy §8.1 & bejson-tui-menu-builder) ─
TUI_COLOR_ACCENT_RED: str = "\033[38;2;222;38;38m"  # Policy §8.1 #DE2626 Truecolor
TUI_COLOR_FALLBACK_RED: str = "\033[1;31m"          # ANSI Bold Red fallback
TUI_COLOR_RESET: str = "\033[0m"
TUI_COLOR_DIM: str = "\033[2m"
TUI_COLOR_BOLD: str = "\033[1m"
TUI_CONSOLE_CLEAR: str = "\033[2J\033[H"
TUI_DIVIDER_57: str = "=" * 57
TUI_SUBDIVIDER_57: str = "-" * 57

# Terminal color capability detection
NO_COLOR_ENABLED: bool = os.getenv("NO_COLOR") is not None
COLORTERM_ENV: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM_ENV or "24bit" in COLORTERM_ENV


def get_tui_accent_color() -> str:
    if NO_COLOR_ENABLED or not sys.stdout.isatty():
        return ""
    return TUI_COLOR_ACCENT_RED if SUPPORTS_TRUECOLOR else TUI_COLOR_FALLBACK_RED


def get_tui_reset_color() -> str:
    if NO_COLOR_ENABLED or not sys.stdout.isatty():
        return ""
    return TUI_COLOR_RESET


def get_tui_dim_color() -> str:
    if NO_COLOR_ENABLED or not sys.stdout.isatty():
        return ""
    return TUI_COLOR_DIM


def clear_terminal_screen() -> None:
    if sys.stdout.isatty() and not NO_COLOR_ENABLED:
        sys.stdout.write(TUI_CONSOLE_CLEAR)
        sys.stdout.flush()


# ── Structured Logging Configuration ────────────────────────────────────────
tool_logger: logging.Logger = logging.getLogger("logging_tool")
_console_handler: logging.StreamHandler = logging.StreamHandler(sys.stderr)
_console_formatter: logging.Formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_console_handler.setFormatter(_console_formatter)
tool_logger.addHandler(_console_handler)
tool_logger.setLevel(logging.INFO)


# ── Configuration Loader ───────────────────────────────────────────────────
def load_tool_configuration() -> Dict[str, Any]:
    configuration_file_path: Path = LOCAL_CONFIG_DIRECTORY / "config.json"
    fallback_configuration_map: Dict[str, Any] = {
        "global_logs_directory": "/storage/emulated/0/Admin/System/Global_Logs",
        "default_bejson_dir": "/storage/emulated/0/Admin/System/Global_Logs/bejson",
        "default_md_dir": "/storage/emulated/0/Admin/System/Global_Logs/md",
        "default_html_dir": "/storage/emulated/0/Admin/System/Global_Logs/html",
        "default_archive_dir": "/storage/emulated/0/Admin/System/Global_Logs/archives",
        "default_secure_dir": "/storage/emulated/0/Admin/System/Global_Logs/secure",
        "default_subsystem": "system",
        "default_min_level": "INFO",
        "default_row_cap": 10000,
        "default_archive_period": "daily",
    }
    if not configuration_file_path.is_file():
        return fallback_configuration_map

    try:
        loaded_configuration_doc: Dict[str, Any] = bejson_core_load_file(str(configuration_file_path))
        field_map_cache: Dict[str, int] = bejson_core_get_field_map(loaded_configuration_doc)
        setting_name_index: int = field_map_cache.get("setting_name", 0)
        setting_value_index: int = field_map_cache.get("setting_value", 1)

        merged_configuration_map: Dict[str, Any] = dict(fallback_configuration_map)
        for configuration_row in loaded_configuration_doc.get("Values", []):
            extracted_key: str = str(configuration_row[setting_name_index])
            extracted_val: Any = configuration_row[setting_value_index]
            merged_configuration_map[extracted_key] = extracted_val

        return merged_configuration_map
    except Exception as configuration_exception:
        tool_logger.warning("Failed to parse config.json, using fallback defaults: %s", configuration_exception)
        return fallback_configuration_map


def get_current_utc_date_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def resolve_target_log_paths(
    configuration_map: Dict[str, Any],
    explicit_log_file: Optional[str] = None,
    target_date_string: Optional[str] = None,
) -> Tuple[str, str, str]:
    global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
    default_bejson_directory: str = configuration_map.get("default_bejson_dir", os.path.join(global_logs_directory, "bejson"))
    default_archive_directory: str = configuration_map.get("default_archive_dir", os.path.join(global_logs_directory, "archives"))
    default_secure_directory: str = configuration_map.get("default_secure_dir", os.path.join(global_logs_directory, "secure"))

    os.makedirs(global_logs_directory, exist_ok=True)
    os.makedirs(default_bejson_directory, exist_ok=True)
    os.makedirs(default_archive_directory, exist_ok=True)
    os.makedirs(default_secure_directory, exist_ok=True)

    if explicit_log_file:
        resolved_main_path: str = os.path.abspath(explicit_log_file)
        main_file_stem: str = Path(resolved_main_path).stem
        resolved_secure_path: str = os.path.join(default_secure_directory, f"{main_file_stem}-secure.bejson")
        return resolved_main_path, resolved_secure_path, default_archive_directory

    active_date_token: str = target_date_string or get_current_utc_date_string()
    resolved_main_log_file: str = os.path.join(default_bejson_directory, f"Log-{active_date_token}.bejson")
    if not os.path.isfile(resolved_main_log_file):
        legacy_path: str = os.path.join(global_logs_directory, f"Log-{active_date_token}.bejson")
        if os.path.isfile(legacy_path):
            resolved_main_log_file = legacy_path

    resolved_secure_log_file: str = os.path.join(default_secure_directory, f"Log-{active_date_token}-secure.bejson")

    return resolved_main_log_file, resolved_secure_log_file, default_archive_directory


def ensure_sink_configured(
    target_log_file_path: str,
    target_secure_file_path: Optional[str],
    target_archive_dir_path: Optional[str],
    configuration_map: Dict[str, Any],
) -> None:
    standards_registry.bejson_standards_configure_sink(
        log_path=target_log_file_path,
        row_cap=int(configuration_map.get("default_row_cap", 10000)),
        min_level=str(configuration_map.get("default_min_level", "INFO")),
        secure_path=target_secure_file_path,
        archive_dir=target_archive_dir_path,
        archive_period=str(configuration_map.get("default_archive_period", "daily")),
    )


def auto_compile_log_reports(log_file_path: str, configuration_map: Dict[str, Any]) -> Tuple[str, str]:
    """Compile Markdown (.md) and HTML (.html) counterparts in format-based sibling folders alongside the log file via MD_To_HTML."""
    log_file_path = os.path.abspath(log_file_path)
    if not os.path.isfile(log_file_path):
        return "", ""
    doc = standards_core.bejson_standards_core_load(log_file_path)
    if not doc:
        return "", ""
    rows = list(standards_core.bejson_standards_core_rows_to_dicts(doc))
    stem = Path(log_file_path).stem
    date_token = stem.replace("Log-", "").replace("-secure", "")

    global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
    default_md_directory: str = configuration_map.get("default_md_dir", os.path.join(global_logs_directory, "md"))
    default_html_directory: str = configuration_map.get("default_html_dir", os.path.join(global_logs_directory, "html"))
    os.makedirs(default_md_directory, exist_ok=True)
    os.makedirs(default_html_directory, exist_ok=True)

    md_target = os.path.join(default_md_directory, f"{stem}.md")
    html_target = os.path.join(default_html_directory, f"{stem}.html")

    export_log_html_report(
        rows=rows,
        output_path=html_target,
        md_output_path=md_target,
        title=f"Daily System Log Audit Report — {date_token}",
        theme="dark",
        filter_summary=f"Daily Log Partition ({date_token})",
        log_path=log_file_path,
        config_dict=configuration_map,
    )
    return md_target, html_target


# ── Action Handlers ────────────────────────────────────────────────────────
def handle_write_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    resolved_main_path, resolved_secure_path, resolved_archive_dir = resolve_target_log_paths(
        configuration_map,
        explicit_log_file=parsed_arguments.log_file,
        target_date_string=parsed_arguments.date,
    )
    resolved_subsystem: str = parsed_arguments.subsystem or configuration_map.get("default_subsystem", "system")

    ensure_sink_configured(resolved_main_path, resolved_secure_path, resolved_archive_dir, configuration_map)

    # Parse context payload if provided
    parsed_context_dictionary: Optional[Dict[str, Any]] = None
    if parsed_arguments.context:
        try:
            parsed_context_dictionary = json.loads(parsed_arguments.context)
        except Exception:
            parsed_context_dictionary = {"raw_context": parsed_arguments.context}

    # Parse flags if provided
    resolved_flags_list: Optional[List[str]] = None
    if parsed_arguments.flag:
        resolved_flags_list = []
        for individual_flag_item in parsed_arguments.flag:
            resolved_flags_list.extend([flag_chunk.strip() for flag_chunk in individual_flag_item.split(",") if flag_chunk.strip()])

    logged_successfully: bool = standards_registry.bejson_standards_log(
        log_path=resolved_main_path,
        level=parsed_arguments.level,
        event_key=parsed_arguments.key,
        message=parsed_arguments.message,
        subsystem=resolved_subsystem,
        priority=parsed_arguments.priority,
        category=parsed_arguments.category,
        subject=parsed_arguments.subject,
        error_code=parsed_arguments.error_code,
        actor=parsed_arguments.actor,
        session=parsed_arguments.session,
        target_uuid=parsed_arguments.target,
        flags=resolved_flags_list,
        context=parsed_context_dictionary,
        secure=parsed_arguments.secure,
    )

    # Flush main sink (which automatically flushes paired secure sink)
    standards_registry.bejson_standards_flush(resolved_main_path)

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()

    if logged_successfully:
        destination_label: str = resolved_secure_path if parsed_arguments.secure else resolved_main_path
        sys.stdout.write(f"[{accent_color}✓{reset_color}] Committed log entry to: {destination_label}\n")
        # Automatically compile Markdown & HTML counterparts per Log Document Synchronization Invariant
        try:
            auto_compile_log_reports(resolved_main_path, configuration_map)
        except Exception as compile_exc:
            tool_logger.warning("Could not auto-compile log report: %s", compile_exc)
        return 0
    else:
        sys.stdout.write(f"[{accent_color}✗{reset_color}] Log entry dropped (filtered by level or schema violation).\n")
        return 1


def handle_read_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    resolved_main_path, resolved_secure_path, resolved_archive_dir = resolve_target_log_paths(
        configuration_map,
        explicit_log_file=parsed_arguments.log_file,
        target_date_string=parsed_arguments.date,
    )

    target_files_to_read: List[Tuple[str, str, str]] = []
    if parsed_arguments.all:
        global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
        bejson_directory: str = configuration_map.get("default_bejson_dir", os.path.join(global_logs_directory, "bejson"))
        discovered_log_paths = sorted(glob.glob(os.path.join(bejson_directory, "Log-*.bejson")))
        for root_p in sorted(glob.glob(os.path.join(global_logs_directory, "Log-*.bejson"))):
            if root_p not in discovered_log_paths:
                discovered_log_paths.append(root_p)
        for discovered_path in discovered_log_paths:
            date_stem = Path(discovered_path).stem.replace("Log-", "").replace("-secure", "")
            target_files_to_read.append(resolve_target_log_paths(configuration_map, explicit_log_file=discovered_path, target_date_string=date_stem))
    else:
        target_files_to_read.append((resolved_main_path, resolved_secure_path, resolved_archive_dir))

    aggregated_records: List[Dict[str, Any]] = []
    for main_path, sec_path, arch_dir in target_files_to_read:
        if not os.path.isfile(main_path):
            continue
        ensure_sink_configured(main_path, sec_path, arch_dir, configuration_map)
        file_records: List[Dict[str, Any]] = standards_registry.bejson_standards_read_logs(
            log_path=main_path,
            min_level=parsed_arguments.min_level,
            max_priority=parsed_arguments.max_priority,
            subsystem=parsed_arguments.subsystem,
            actor=parsed_arguments.actor,
            session=parsed_arguments.session,
            category=parsed_arguments.category,
            flag=parsed_arguments.flag,
            event_key=parsed_arguments.key,
            since=parsed_arguments.since,
            until=parsed_arguments.until,
            limit=parsed_arguments.limit or 100,
            secure=parsed_arguments.secure,
        )
        aggregated_records.extend(file_records)

    aggregated_records.sort(key=lambda r: str(r.get(standards_validator.F_EVENT_TIMESTAMP, "")))
    if parsed_arguments.limit and len(aggregated_records) > parsed_arguments.limit:
        aggregated_records = aggregated_records[-parsed_arguments.limit:]

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()
    dim_color: str = get_tui_dim_color()

    query_label: str = "ALL GLOBAL LOGS" if parsed_arguments.all else (
        os.path.basename(resolved_secure_path) if parsed_arguments.secure else os.path.basename(resolved_main_path)
    )

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}LOG TELEMETRY STRIP{reset_color} {query_label:>36}\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}{'TIME (UTC)':<12} {'LVL':<5} {'PRI':<3} {'SUBSYSTEM':<12} {'EVENT / MESSAGE':<20}{reset_color}\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")

    if not aggregated_records:
        sys.stdout.write(f" {dim_color}No records matched query criteria.{reset_color}\n")
    else:
        for record_entry in aggregated_records:
            full_ts: str = record_entry.get(standards_validator.F_EVENT_TIMESTAMP, "")
            # Truncate timestamp to HH:MM:SS or MM-DD HH:MM
            short_ts: str = full_ts[11:19] if len(full_ts) >= 19 else full_ts
            level_str: str = str(record_entry.get(standards_validator.F_EVENT_LEVEL, ""))[:5]
            prio_val: Any = record_entry.get(standards_validator.F_EVENT_PRIORITY)
            prio_display: str = str(prio_val) if prio_val is not None else "-"
            subsystem_str: str = str(record_entry.get(standards_validator.F_SENDER_SUBSYSTEM, ""))[:12]
            event_key_str: str = str(record_entry.get(standards_validator.F_EVENT_KEY, ""))
            message_str: str = str(record_entry.get(standards_validator.F_EVENT_MESSAGE, ""))
            event_body: str = f"{event_key_str}: {message_str}"
            if len(event_body) > 20:
                event_body = event_body[:17] + "..."

            # Level tag coloring
            level_tag: str = f"[{level_str:<4}]"
            sys.stdout.write(
                f" {short_ts:<12} {accent_color}{level_tag}{reset_color} {prio_display:<3} {subsystem_str:<12} {event_body:<20}\n"
            )

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    return 0


def handle_export_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    resolved_main_path, resolved_secure_path, resolved_archive_dir = resolve_target_log_paths(
        configuration_map,
        explicit_log_file=parsed_arguments.log_file,
        target_date_string=parsed_arguments.date,
    )
    if not os.path.isfile(resolved_main_path):
        tool_logger.error("Target log file does not exist: %s", resolved_main_path)
        return 1

    if parsed_arguments.format == "report":
        return handle_report_command(parsed_arguments, configuration_map)

    ensure_sink_configured(resolved_main_path, resolved_secure_path, resolved_archive_dir, configuration_map)

    resolved_export_destination: Optional[str] = parsed_arguments.out
    if resolved_export_destination and not os.path.isabs(resolved_export_destination):
        resolved_export_destination = str(LOCAL_EXPORTS_DIRECTORY / resolved_export_destination)

    export_execution_result: Dict[str, Any] = standards_registry.bejson_standards_export_logs(
        log_path=resolved_main_path,
        fmt=parsed_arguments.format,
        dest=resolved_export_destination,
        min_level=parsed_arguments.min_level,
        max_priority=parsed_arguments.max_priority,
        subsystem=parsed_arguments.subsystem,
        actor=parsed_arguments.actor,
        category=parsed_arguments.category,
        flag=parsed_arguments.flag,
        event_key=parsed_arguments.key,
        since=parsed_arguments.since,
        until=parsed_arguments.until,
        sort=parsed_arguments.sort,
        limit=parsed_arguments.limit,
        include_context=parsed_arguments.include_context,
        theme=parsed_arguments.theme,
        secure=parsed_arguments.secure,
    )

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()

    if not export_execution_result.get("ok"):
        sys.stdout.write(f"[{accent_color}✗{reset_color}] Export failed: {export_execution_result.get('error')} (Code: {export_execution_result.get('code')})\n")
        return 1

    if resolved_export_destination:
        sys.stdout.write(f"[{accent_color}✓{reset_color}] Exported {export_execution_result.get('rows', 0)} row(s) to: {resolved_export_destination}\n")
    else:
        sys.stdout.write(export_execution_result.get("text", "") + "\n")
    return 0


def handle_report_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()

    if getattr(parsed_arguments, "all", False):
        global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
        bejson_directory: str = configuration_map.get("default_bejson_dir", os.path.join(global_logs_directory, "bejson"))
        discovered_paths = sorted(glob.glob(os.path.join(bejson_directory, "Log-*.bejson")))
        for root_file in sorted(glob.glob(os.path.join(global_logs_directory, "Log-*.bejson"))):
            if root_file not in discovered_paths:
                discovered_paths.append(root_file)
        if not discovered_paths:
            sys.stdout.write(f"[{accent_color}!{reset_color}] No log files discovered in {bejson_directory} or {global_logs_directory}\n")
            return 0
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        sys.stdout.write(f" {accent_color}BATCH COMPILED LOG REPORTS [md2html]{reset_color}\n")
        sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
        for log_p in discovered_paths:
            md_p, html_p = auto_compile_log_reports(log_p, configuration_map)
            stem = os.path.basename(log_p)
            sys.stdout.write(f" {accent_color}✓{reset_color} {stem:<24} → md/ & html/\n")
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        return 0

    resolved_main_path, resolved_secure_path, resolved_archive_dir = resolve_target_log_paths(
        configuration_map,
        explicit_log_file=getattr(parsed_arguments, "log_file", None),
        target_date_string=getattr(parsed_arguments, "date", None),
    )
    target_path = resolved_secure_path if getattr(parsed_arguments, "secure", False) else resolved_main_path
    if not os.path.isfile(target_path):
        tool_logger.error("Target log file does not exist: %s", target_path)
        return 1

    doc = standards_core.bejson_standards_core_load(target_path)
    if not doc:
        tool_logger.error("Failed to load log file: %s", target_path)
        return 1

    all_rows = list(standards_core.bejson_standards_core_rows_to_dicts(doc))
    matching_rows = list(standards_export.bejson_standards_export_filter_rows(
        all_rows,
        min_level=getattr(parsed_arguments, "min_level", None),
        subsystem=getattr(parsed_arguments, "subsystem", None),
        category=getattr(parsed_arguments, "category", None),
        actor=getattr(parsed_arguments, "actor", None),
        flag=getattr(parsed_arguments, "flag", None),
        max_priority=getattr(parsed_arguments, "max_priority", None),
        session=getattr(parsed_arguments, "session", None),
        event_key=getattr(parsed_arguments, "key", None),
        since=getattr(parsed_arguments, "since", None),
        until=getattr(parsed_arguments, "until", None),
        include_secure_rows=getattr(parsed_arguments, "secure", False),
    ))

    limit_val = getattr(parsed_arguments, "limit", None)
    if limit_val and len(matching_rows) > limit_val:
        matching_rows = matching_rows[-limit_val:]

    stem = Path(target_path).stem
    stem_date = stem.replace("Log-", "").replace("-secure", "")
    global_logs_directory = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
    default_md_directory = configuration_map.get("default_md_dir", os.path.join(global_logs_directory, "md"))
    default_html_directory = configuration_map.get("default_html_dir", os.path.join(global_logs_directory, "html"))

    resolved_html_out = getattr(parsed_arguments, "out", None)
    if not resolved_html_out:
        resolved_html_out = os.path.join(default_html_directory, f"{stem}.html")
    elif not os.path.isabs(resolved_html_out):
        resolved_html_out = str(LOCAL_EXPORTS_DIRECTORY / "log_reports" / resolved_html_out)

    resolved_md_out = getattr(parsed_arguments, "md_out", None)
    if not resolved_md_out:
        resolved_md_out = os.path.join(default_md_directory, f"{stem}.md")
    elif not os.path.isabs(resolved_md_out):
        resolved_md_out = str(LOCAL_EXPORTS_DIRECTORY / "log_reports" / resolved_md_out)

    filter_tokens = []
    if getattr(parsed_arguments, "min_level", None):
        filter_tokens.append(f"level>={parsed_arguments.min_level}")
    if getattr(parsed_arguments, "subsystem", None):
        filter_tokens.append(f"subsystem={parsed_arguments.subsystem}")
    if getattr(parsed_arguments, "category", None):
        filter_tokens.append(f"category={parsed_arguments.category}")
    filter_summary = ", ".join(filter_tokens) if filter_tokens else "none (full sink)"

    custom_title = getattr(parsed_arguments, "title", None) or f"Daily System Log Audit Report — {stem_date}"
    theme = getattr(parsed_arguments, "theme", "dark") or "dark"

    report_result = export_log_html_report(
        rows=matching_rows,
        output_path=resolved_html_out,
        md_output_path=resolved_md_out,
        title=custom_title,
        theme=theme,
        filter_summary=filter_summary,
        log_path=target_path,
        config_dict=configuration_map,
    )

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}SYSTEM LOG REPORT COMPILED [md2html]{reset_color}\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}SOURCE SINK:{reset_color}   {os.path.basename(target_path)}\n")
    sys.stdout.write(f" {accent_color}ROWS INCLUDED:{reset_color} {report_result['rows_processed']}\n")
    sys.stdout.write(f" {accent_color}HTML REPORT:{reset_color}   {report_result['html_path']}\n")
    if report_result.get("md_path"):
        sys.stdout.write(f" {accent_color}MARKDOWN:{reset_color}      {report_result['md_path']}\n")
    sys.stdout.write(f" {accent_color}THEME:{reset_color}         {report_result['theme']}\n")
    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    return 0


def handle_audit_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
    bejson_directory: str = configuration_map.get("default_bejson_dir", os.path.join(global_logs_directory, "bejson"))
    files_to_audit: List[str] = []

    if parsed_arguments.all:
        files_to_audit.extend(sorted(glob.glob(os.path.join(bejson_directory, "Log-*.bejson"))))
        for root_f in sorted(glob.glob(os.path.join(global_logs_directory, "Log-*.bejson"))):
            if root_f not in files_to_audit:
                files_to_audit.append(root_f)
        files_to_audit.extend(sorted(glob.glob(os.path.join(global_logs_directory, "secure", "Log-*.bejson"))))
        files_to_audit.extend(sorted(glob.glob(os.path.join(global_logs_directory, "archives", "*.bejson"))))
    else:
        resolved_main_path, resolved_secure_path, _ = resolve_target_log_paths(
            configuration_map,
            explicit_log_file=parsed_arguments.log_file,
            target_date_string=parsed_arguments.date,
        )
        target_check_path: str = resolved_secure_path if parsed_arguments.secure else resolved_main_path
        if not os.path.isfile(target_check_path):
            tool_logger.error("Target log file does not exist: %s", target_check_path)
            return 1
        files_to_audit.append(target_check_path)

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}BEJSON STANDARDS AUDIT GATE{reset_color}            57-COL\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
    sys.stdout.write(f" {'STATUS':<7} {'TARGET LOG FILE':<47}\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")

    all_audits_passed: bool = True
    for file_path_entry in files_to_audit:
        audit_evaluation_result: Dict[str, Any] = standards_registry.bejson_standards_audit_log_file(file_path_entry)
        passed_audit_check: bool = audit_evaluation_result.get("passed", False)
        detected_problems_list: List[str] = audit_evaluation_result.get("problems", [])

        status_tag: str = f"[{accent_color}✓{reset_color}]" if passed_audit_check else f"[{accent_color}✗{reset_color}]"
        shortened_file_path: str = file_path_entry
        if len(shortened_file_path) > 47:
            shortened_file_path = "..." + shortened_file_path[-44:]

        sys.stdout.write(f" {status_tag:<16} {shortened_file_path:<47}\n")
        if detected_problems_list:
            all_audits_passed = False
            for problem_entry in detected_problems_list:
                sys.stdout.write(f"    {accent_color}!{reset_color} {problem_entry}\n")

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    return 0 if all_audits_passed else 1


def handle_list_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    clear_terminal_screen()
    global_logs_directory: str = configuration_map.get("global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs")
    bejson_directory: str = configuration_map.get("default_bejson_dir", os.path.join(global_logs_directory, "bejson"))
    default_md_directory: str = configuration_map.get("default_md_dir", os.path.join(global_logs_directory, "md"))
    default_html_directory: str = configuration_map.get("default_html_dir", os.path.join(global_logs_directory, "html"))
    default_secure_directory: str = configuration_map.get("default_secure_dir", os.path.join(global_logs_directory, "secure"))
    default_archive_directory: str = configuration_map.get("default_archive_dir", os.path.join(global_logs_directory, "archives"))

    main_log_files = sorted(glob.glob(os.path.join(bejson_directory, "Log-*.bejson")))
    if not main_log_files:
        main_log_files = sorted(glob.glob(os.path.join(global_logs_directory, "Log-*.bejson")))

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()
    dim_color: str = get_tui_dim_color()

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}GLOBAL LOGS CATALOG [57-COL]{reset_color}      ~/.../Global_Logs\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
    sys.stdout.write(f" {accent_color}{'FILENAME':<22} {'ROWS':<5} {'SIZE':<6} {'MD':<3} {'HTM':<4} {'SEC'}{reset_color}\n")
    sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")

    if not main_log_files:
        sys.stdout.write(f" {dim_color}No daily log files present yet in Global_Logs.{reset_color}\n")
    else:
        for main_file_path in main_log_files:
            file_name_label: str = os.path.basename(main_file_path)
            file_size_kb: float = round(os.path.getsize(main_file_path) / 1024, 1)

            row_count_display: str = "?"
            try:
                loaded_doc = bejson_core_load_file(main_file_path)
                row_count_display = str(len(loaded_doc.get("Values", [])))
            except Exception:
                row_count_display = "ERR"

            date_token: str = file_name_label.replace("Log-", "").replace(".bejson", "")
            secure_companion_path: str = os.path.join(default_secure_directory, f"Log-{date_token}-secure.bejson")
            has_secure_pair: str = "Yes" if os.path.isfile(secure_companion_path) else "No"

            md_companion_path: str = os.path.join(default_md_directory, f"Log-{date_token}.md")
            has_md: str = "Yes" if os.path.isfile(md_companion_path) else "No"

            html_companion_path: str = os.path.join(default_html_directory, f"Log-{date_token}.html")
            has_html: str = "Yes" if os.path.isfile(html_companion_path) else "No"

            sys.stdout.write(
                f" {file_name_label:<22} {row_count_display:<5} {f'{file_size_kb}K':<6} {has_md:<3} {has_html:<4} {has_secure_pair}\n"
            )

    sys.stdout.write(f"{TUI_DIVIDER_57}\n")
    return 0


def handle_archive_command(parsed_arguments: argparse.Namespace, configuration_map: Dict[str, Any]) -> int:
    resolved_main_path, resolved_secure_path, resolved_archive_dir = resolve_target_log_paths(
        configuration_map,
        explicit_log_file=parsed_arguments.log_file,
        target_date_string=parsed_arguments.date,
    )

    ensure_sink_configured(resolved_main_path, resolved_secure_path, resolved_archive_dir, configuration_map)

    archived_row_count: int = standards_registry.bejson_standards_archive_now(
        log_path=resolved_main_path,
        include_current=parsed_arguments.include_current,
    )
    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()
    sys.stdout.write(f"[{accent_color}✓{reset_color}] Archived {archived_row_count} row(s) to: {resolved_archive_dir}\n")
    return 0


# ── CLI Argument Parser Builder ────────────────────────────────────────────
def build_cli_argument_parser() -> argparse.ArgumentParser:
    root_parser = argparse.ArgumentParser(
        prog="logging_tool.py",
        description="BEJSON 105 Standards Global Logging Tool (Schema v3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    root_parser.add_argument("-v", "--version", action="store_true", help="Display tool version and schema information.")
    root_parser.add_argument("--about", action="store_true", help="Display author and architecture metadata.")
    root_parser.add_argument("--config", action="store_true", help="Display active configuration settings.")

    subcommand_parsers = root_parser.add_subparsers(dest="command", help="Command to execute")

    # Subcommand: write
    write_subparser = subcommand_parsers.add_parser("write", help="Write a standardized log entry to the sink.")
    write_subparser.add_argument("-m", "--message", required=True, help="Log message text.")
    write_subparser.add_argument("-l", "--level", default="INFO", help="Log level (DEBUG, INFO, WARN, ERROR, FATAL). Default: INFO.")
    write_subparser.add_argument("-k", "--key", default="system.event", help="Event natural key (e.g. app.init, db.query).")
    write_subparser.add_argument("-s", "--subsystem", help="Sender subsystem name (defaults to config default_subsystem).")
    write_subparser.add_argument("-p", "--priority", type=int, choices=[1, 2, 3, 4], help="Priority metric (1=now, 2=high, 3=medium, 4=background).")
    write_subparser.add_argument("--category", help="Categorical tag token.")
    write_subparser.add_argument("--subject", help="Subject identifier.")
    write_subparser.add_argument("--error-code", type=int, help="Numeric error code metric.")
    write_subparser.add_argument("--context", help="JSON dictionary string or text for context payload.")
    write_subparser.add_argument("--flag", action="append", help="Flag tag token (repeatable or comma-separated).")
    write_subparser.add_argument("--actor", help="Actor or user name.")
    write_subparser.add_argument("--session", help="Session token or UUID.")
    write_subparser.add_argument("--target", help="Target entity UUID foreign key.")
    write_subparser.add_argument("--secure", action="store_true", help="Route entry exclusively to the secure log file.")
    write_subparser.add_argument("-d", "--date", help="Target specific daily log date (YYYY-MM-DD). Defaults to current UTC date.")
    write_subparser.add_argument("--log-file", help="Override destination log file path directly.")

    # Subcommand: read
    read_subparser = subcommand_parsers.add_parser("read", help="Query and read standardized log entries.")
    read_subparser.add_argument("--min-level", help="Minimum level threshold (DEBUG, INFO, WARN, ERROR, FATAL).")
    read_subparser.add_argument("--max-priority", type=int, choices=[1, 2, 3, 4], help="Maximum priority threshold.")
    read_subparser.add_argument("-s", "--subsystem", help="Filter by sender subsystem name.")
    read_subparser.add_argument("--actor", help="Filter by actor name.")
    read_subparser.add_argument("--session", help="Filter by session key.")
    read_subparser.add_argument("--category", help="Filter by category key.")
    read_subparser.add_argument("--flag", help="Filter by flag presence.")
    read_subparser.add_argument("-k", "--key", help="Filter by event key.")
    read_subparser.add_argument("--since", help="Filter entries since timestamp (inclusive ISO-8601).")
    read_subparser.add_argument("--until", help="Filter entries until timestamp (exclusive ISO-8601).")
    read_subparser.add_argument("--limit", type=int, default=50, help="Maximum number of newest records to retrieve (default: 50).")
    read_subparser.add_argument("--secure", action="store_true", help="Read from secure log file.")
    read_subparser.add_argument("-d", "--date", help="Query specific daily log date (YYYY-MM-DD). Defaults to current UTC date.")
    read_subparser.add_argument("--all", action="store_true", help="Query and aggregate across all daily log files in Global_Logs.")
    read_subparser.add_argument("--log-file", help="Path to specific log file to query.")

    # Subcommand: export
    export_subparser = subcommand_parsers.add_parser("export", help="Filter and export log entries to json, ndjson, markdown, html, or single-page report.")
    export_subparser.add_argument("-f", "--format", choices=["json", "ndjson", "markdown", "html", "report"], default="markdown", help="Target export format.")
    export_subparser.add_argument("-o", "--out", help="Output file path (relative to exports/ or absolute; default: stdout).")
    export_subparser.add_argument("--min-level", help="Minimum level threshold.")
    export_subparser.add_argument("--max-priority", type=int, choices=[1, 2, 3, 4], help="Maximum priority threshold.")
    export_subparser.add_argument("-s", "--subsystem", help="Filter by subsystem.")
    export_subparser.add_argument("--actor", help="Filter by actor.")
    export_subparser.add_argument("--category", help="Filter by category.")
    export_subparser.add_argument("--flag", help="Filter by flag.")
    export_subparser.add_argument("-k", "--key", help="Filter by event key.")
    export_subparser.add_argument("--since", help="Filter entries since timestamp.")
    export_subparser.add_argument("--until", help="Filter entries until timestamp.")
    export_subparser.add_argument("--sort", choices=["time", "priority"], default="time", help="Sorting order.")
    export_subparser.add_argument("--limit", type=int, help="Limit number of exported records.")
    export_subparser.add_argument("--include-context", action="store_true", help="Include serialized context payload in export.")
    export_subparser.add_argument("--theme", choices=["light", "dark"], default="dark", help="Color theme for HTML export.")
    export_subparser.add_argument("--secure", action="store_true", help="Export from secure log sink.")
    export_subparser.add_argument("-d", "--date", help="Target specific daily log date (YYYY-MM-DD).")
    export_subparser.add_argument("--log-file", help="Path to source log file.")

    # Subcommand: report
    report_subparser = subcommand_parsers.add_parser("report", help="Compile single-page HTML & templated Markdown reports via md2html.")
    report_subparser.add_argument("-o", "--out", help="Output file path (default: exports/log_reports/Log-Report-<timestamp>.html).")
    report_subparser.add_argument("--md-out", help="Optional output path for raw templated Markdown report.")
    report_subparser.add_argument("-t", "--title", help="Custom report title.")
    report_subparser.add_argument("--min-level", help="Minimum level threshold.")
    report_subparser.add_argument("--max-priority", type=int, choices=[1, 2, 3, 4], help="Maximum priority threshold.")
    report_subparser.add_argument("-s", "--subsystem", help="Filter by subsystem.")
    report_subparser.add_argument("--actor", help="Filter by actor.")
    report_subparser.add_argument("--category", help="Filter by category.")
    report_subparser.add_argument("--flag", help="Filter by flag.")
    report_subparser.add_argument("-k", "--key", help="Filter by event key.")
    report_subparser.add_argument("--since", help="Filter entries since timestamp.")
    report_subparser.add_argument("--until", help="Filter entries until timestamp.")
    report_subparser.add_argument("--limit", type=int, default=100, help="Maximum number of records to report (default: 100).")
    report_subparser.add_argument("--theme", choices=["light", "dark"], default="dark", help="Color theme for HTML report (default: dark).")
    report_subparser.add_argument("--secure", action="store_true", help="Report from secure log sink.")
    report_subparser.add_argument("-d", "--date", help="Target specific daily log date (YYYY-MM-DD).")
    report_subparser.add_argument("--log-file", help="Path to source log file.")
    report_subparser.add_argument("--all", action="store_true", help="Compile MD & HTML reports for all daily log files.")

    # Subcommand: list
    subcommand_parsers.add_parser("list", help="Catalog and list all daily log files in Global_Logs.")

    # Subcommand: audit
    audit_subparser = subcommand_parsers.add_parser("audit", help="Audit structural and schema integrity of log files.")
    audit_subparser.add_argument("-d", "--date", help="Audit specific daily log date (YYYY-MM-DD).")
    audit_subparser.add_argument("--secure", action="store_true", help="Audit secure log file.")
    audit_subparser.add_argument("--all", action="store_true", help="Audit all log files in Global_Logs, secure/, and archives/.")
    audit_subparser.add_argument("--log-file", help="Path to specific log file to audit.")

    # Subcommand: archive
    archive_subparser = subcommand_parsers.add_parser("archive", help="Trigger manual slice archiving of completed periods.")
    archive_subparser.add_argument("--include-current", action="store_true", help="Archive all records including the active current period.")
    archive_subparser.add_argument("-d", "--date", help="Target specific daily log date (YYYY-MM-DD).")
    archive_subparser.add_argument("--log-file", help="Path to specific log file to archive.")

    return root_parser


# ── Main Entry Point ───────────────────────────────────────────────────────
def main() -> int:
    parser = build_cli_argument_parser()
    parsed_arguments = parser.parse_args()

    accent_color: str = get_tui_accent_color()
    reset_color: str = get_tui_reset_color()

    if parsed_arguments.version:
        sys.stdout.write(f"logging_tool.py Version {TOOL_VERSION} ({accent_color}BEJSON Standards Schema v{standards_validator.SCHEMA_VERSION}{reset_color})\n")
        return 0

    if parsed_arguments.about:
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        sys.stdout.write(f" {accent_color}BEJSON 105 STANDARDS LOGGING TOOL{reset_color}\n")
        sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
        sys.stdout.write(f" Author  : {TOOL_AUTHOR}\n")
        sys.stdout.write(f" Contact : {TOOL_CONTACT}\n")
        sys.stdout.write(f" Format  : BEJSON 104a | Records_Type: StandardsLogEntry\n")
        sys.stdout.write(f" Columns : 17 | Viewport: 57-Column Telemetry\n")
        sys.stdout.write(f" Target  : /storage/emulated/0/Admin/System/Global_Logs\n")
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        return 0

    configuration_map: Dict[str, Any] = load_tool_configuration()

    if parsed_arguments.config:
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        sys.stdout.write(f" {accent_color}ACTIVE SINK CONFIGURATION{reset_color}\n")
        sys.stdout.write(f"{TUI_SUBDIVIDER_57}\n")
        for configuration_key, configuration_value in configuration_map.items():
            sys.stdout.write(f"  {accent_color}{configuration_key:<25}{reset_color}: {configuration_value}\n")
        sys.stdout.write(f"{TUI_DIVIDER_57}\n")
        return 0

    if not parsed_arguments.command:
        parser.print_help(sys.stderr)
        return 1

    if parsed_arguments.command == "write":
        return handle_write_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "read":
        return handle_read_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "export":
        return handle_export_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "report":
        return handle_report_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "list":
        return handle_list_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "audit":
        return handle_audit_command(parsed_arguments, configuration_map)
    elif parsed_arguments.command == "archive":
        return handle_archive_command(parsed_arguments, configuration_map)
    else:
        parser.print_help(sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
