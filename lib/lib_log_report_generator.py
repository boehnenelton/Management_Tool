#!/usr/bin/env python3
"""
Module Name : lib_log_report_generator.py
Family      : Logging / Management Subsystem
Purpose     : Transforms BEJSON 105 Standards schema log entries into templated Markdown
              and compiles them via md2html (MD_To_HTML) into single-page HTML reports
              with Policy §8.1 BECSS Tri-Color styling (#05070B, #0B0F17, #DE2626).
Version     : 1.0.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-03
RELATIONAL_ID : bb348f5c-4862-4e96-b2ea-f57092c2c14d
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

try:
    from lib_md_to_html import convert_markdown, get_template, _escape_html
except ImportError:
    # Direct fallback if imported from sibling
    MD_TOOL_PATH = Path("/storage/emulated/0/Admin/System/tools/MD_To_HTML")
    if str(MD_TOOL_PATH) not in sys.path:
        sys.path.insert(0, str(MD_TOOL_PATH))
    from MD_To_HTML import convert_markdown, get_template, _escape_html


def get_utc_now_iso() -> str:
    """Return formatted ISO UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_log_markdown_report(
    rows: List[Dict[str, Any]],
    title: Optional[str] = None,
    filter_summary: str = "none",
    log_path: Optional[str] = None,
) -> str:
    """Transform log entry dictionaries from BEJSON schema into structured templated Markdown."""
    total_rows: int = len(rows)
    fatal_count: int = sum(1 for r in rows if str(r.get("log_event_level_kind", "")).upper() in ("FATAL", "CRITICAL"))
    error_count: int = sum(1 for r in rows if str(r.get("log_event_level_kind", "")).upper() == "ERROR")
    warn_count: int = sum(1 for r in rows if str(r.get("log_event_level_kind", "")).upper() in ("WARN", "WARNING"))
    info_count: int = sum(1 for r in rows if str(r.get("log_event_level_kind", "")).upper() == "INFO")
    debug_count: int = sum(1 for r in rows if str(r.get("log_event_level_kind", "")).upper() in ("DEBUG", "TRACE"))

    subsystems: List[str] = sorted(list(set(str(r.get("log_sender_subsystem_name") or "unknown") for r in rows if r.get("log_sender_subsystem_name"))))
    categories: List[str] = sorted(list(set(str(r.get("log_event_category_key") or "general") for r in rows if r.get("log_event_category_key"))))
    actors: List[str] = sorted(list(set(str(r.get("log_sender_actor_name") or "system") for r in rows if r.get("log_sender_actor_name"))))

    report_title = title or f"System Log Audit Report ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})"
    health_status = "CRITICAL" if fatal_count > 0 else ("DEGRADED / ERRORS" if error_count > 0 else ("WARNINGS" if warn_count > 0 else "OPERATIONAL / CLEAN"))

    subsystems_str = ", ".join(subsystems) if subsystems else "(all subsystems)"
    categories_str = ", ".join(categories) if categories else "(general)"
    actors_str = ", ".join(actors) if actors else "(system)"
    source_str = log_path or "Global Logs Daily Partition"

    lines: List[str] = []
    lines.append(f"# {report_title}")
    lines.append("")
    lines.append(f"> **Report Subsystem**: System Log Telemetry & Executive Audit  ")
    lines.append(f"> **Source Log Sink**: `{source_str}`  ")
    lines.append(f"> **Generated UTC**: `{get_utc_now_iso()}` | **Filter Scope**: `{filter_summary}`  ")
    lines.append(f"> **Total Log Rows**: `{total_rows}` | **Health Metric**: `{health_status}`  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Executive Telemetry Summary")
    lines.append("")
    lines.append("| Metric Parameter | Recorded State / Value |")
    lines.append("|---|---|")
    lines.append(f"| **Total Processed Records** | `{total_rows}` |")
    lines.append(f"| **System Health Status** | `{health_status}` |")
    lines.append(f"| **Fatal / Emergency Events** | `{fatal_count}` |")
    lines.append(f"| **Error Events** | `{error_count}` |")
    lines.append(f"| **Warning Events** | `{warn_count}` |")
    lines.append(f"| **Informational Events** | `{info_count}` |")
    lines.append(f"| **Debug / Trace Events** | `{debug_count}` |")
    lines.append(f"| **Subsystems Represented** | {subsystems_str} |")
    lines.append(f"| **Active Categories** | {categories_str} |")
    lines.append(f"| **Identified Actors** | {actors_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Chronological Log Records")
    lines.append("")

    if not rows:
        lines.append("_No log records matched the requested filter criteria._")
        lines.append("")
    else:
        for index, row in enumerate(rows, start=1):
            level = str(row.get("log_event_level_kind") or "INFO").upper()
            event_key = str(row.get("log_event_key") or "system.event")
            timestamp = str(row.get("log_event_timestamp") or "N/A")
            subsystem = str(row.get("log_sender_subsystem_name") or "(none)")
            actor = str(row.get("log_sender_actor_name") or "(anonymous)")
            pid = str(row.get("log_sender_process_id_metric") or "N/A")
            cat = str(row.get("log_event_category_key") or "general")
            flags = str(row.get("log_event_flags_payload") or "[]")
            priority = str(row.get("log_event_priority_metric") or "default")
            session = str(row.get("log_sender_session_key") or "N/A")
            message = str(row.get("log_event_message_text") or "").strip()
            raw_context = row.get("log_event_context_payload")

            lines.append(f"### {index}. [{level}] `{event_key}`")
            lines.append("")
            lines.append(f"- **Timestamp**: `{timestamp}`")
            lines.append(f"- **Subsystem**: `{subsystem}` | **Actor**: `{actor}` | **PID**: `{pid}`")
            lines.append(f"- **Category**: `{cat}` | **Flags**: `{flags}` | **Priority**: `{priority}`")
            if session and session != "N/A":
                lines.append(f"- **Session ID**: `{session}`")
            lines.append("")
            lines.append(f"**Message**:")
            lines.append(f"> {message}")
            lines.append("")

            if raw_context:
                formatted_context = ""
                if isinstance(raw_context, dict):
                    formatted_context = json.dumps(raw_context, indent=2)
                elif isinstance(raw_context, str):
                    try:
                        parsed_json = json.loads(raw_context)
                        formatted_context = json.dumps(parsed_json, indent=2)
                    except Exception:
                        formatted_context = raw_context
                else:
                    formatted_context = str(raw_context)

                if formatted_context:
                    lines.append("**Context Payload**:")
                    lines.append("```json")
                    lines.append(formatted_context)
                    lines.append("```")
                    lines.append("")

            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def export_log_html_report(
    rows: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    md_output_path: Optional[str] = None,
    title: Optional[str] = None,
    theme: str = "dark",
    filter_summary: str = "none",
    log_path: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compile log entries into templated Markdown and convert to standalone single-page HTML report."""
    cfg = config_dict or {}
    report_title = title or f"System Log Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    # 1. Generate templated Markdown
    markdown_content = generate_log_markdown_report(
        rows=rows,
        title=report_title,
        filter_summary=filter_summary,
        log_path=log_path,
    )

    # 2. Write Markdown output if requested
    saved_md_path: Optional[str] = None
    if md_output_path:
        md_target = Path(md_output_path).resolve()
        md_target.parent.mkdir(parents=True, exist_ok=True)
        temp_md = md_target.with_suffix(".tmp")
        temp_md.write_text(markdown_content, encoding="utf-8")
        temp_md.replace(md_target)
        saved_md_path = str(md_target)

    # 3. Resolve destination HTML file
    if output_path:
        html_target = Path(output_path).resolve()
    else:
        # Default destination in exports/log_reports/
        base_exports = Path("/storage/emulated/0/Admin/System/tools/logging_tool/exports/log_reports")
        base_exports.mkdir(parents=True, exist_ok=True)
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        html_target = base_exports / f"Log-Report-{timestamp_slug}.html"

    html_target.parent.mkdir(parents=True, exist_ok=True)

    # 4. Convert Markdown to HTML via md2html conversion engine
    content_html = convert_markdown(markdown_content)
    template_str = get_template("becss_styled")

    report_desc = f"System log execution report with {len(rows)} record(s) compiled via md2html."
    full_html = (
        template_str
        .replace("{title}", _escape_html(report_title))
        .replace("{description}", _escape_html(report_desc))
        .replace("{content}", content_html)
        .replace("{theme}", theme)
        .replace("{date}", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        .replace("{version}", "1.0.0")
        .replace("{author_name}", cfg.get("author_name", "Elton Boehnen"))
        .replace("{author_email}", cfg.get("author_email", "boehnenelton2024@gmail.com"))
        .replace("{author_site}", cfg.get("author_site", "https://boehnenelton2024.pages.dev"))
        .replace("{author_github}", cfg.get("author_github", "https://github.com/boehnenelton"))
    )

    # 5. Atomic file persistence
    temp_html = html_target.with_suffix(".tmp")
    temp_html.write_text(full_html, encoding="utf-8")
    temp_html.replace(html_target)

    return {
        "ok": True,
        "rows_processed": len(rows),
        "html_path": str(html_target),
        "md_path": saved_md_path,
        "title": report_title,
        "theme": theme,
        "timestamp": get_utc_now_iso(),
    }
