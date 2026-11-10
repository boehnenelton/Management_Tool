#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : notes_web_server.py
Rel. Path   : notes_web_server.py
Family      : Notes / Web Management Subsystem
Purpose     : Stateful, zero-cloud, zero-SQL Flask web application wrapping the
              BEJSON MFDB Notes Engine (notes_mfdb_engine.py). Implements the Loaded
              Chamber pattern in an interactive web workspace adhering strictly to
              Policy §8.1 Tri-Color (#05070B / #F1F5F9 / #DE2626), §8.2-§8.3 Cube Branding,
              §8.4 Mobile-First Responsive Layout, and §8.6 Server Lifecycle Protocols.
Version     : 1.0.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-06
RELATIONAL_ID : bb348f5c-4862-4e96-b2ea-f57092c2c14d
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, render_template_string, request

# ── Self-Locating Path Preambles (Policy §4.1) ────────────────────────────────
def get_script_path() -> Path:
    """Resolve and return absolute directory of this script."""
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
import lib_md_to_html as markdown_engine

# ── Policy §8.1 Tri-Color Palette & 57-Column Terminal Styling ───────────────
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"  # Policy §8.1 #DE2626 Truecolor
COLOR_ANSI_RED: str = "\033[1;31m"          # ANSI Bold Red fallback
COLOR_RESET: str = "\033[0m"
COLOR_DIM: str = "\033[2m"
COLOR_BOLD: str = "\033[1m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM

ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and sys.stdout.isatty() else ""
RESET: str = COLOR_RESET if not NO_COLOR and sys.stdout.isatty() else ""
DIM: str = COLOR_DIM if not NO_COLOR and sys.stdout.isatty() else ""
BOLD: str = COLOR_BOLD if not NO_COLOR and sys.stdout.isatty() else ""

DIVIDER_57: str = "=" * 57
SUBDIVIDER_57: str = "-" * 57

# ── Server Default Configuration (Policy §8.6) ───────────────────────────────
DEFAULT_SERVER_PORT: int = 5050
DEFAULT_SERVER_HOST: str = "127.0.0.1"


# ── Flask Application Factory ────────────────────────────────────────────────
def create_notes_web_application(engine_instance: Optional[NotesMFDBEngine] = None) -> Flask:
    """Create and configure the Flask notes management application."""
    database_engine: NotesMFDBEngine = engine_instance or NotesMFDBEngine(base_directory=SUITE_ROOT)
    site_exporter_instance: NotesSiteExporter = NotesSiteExporter(
        mfdb_engine=database_engine,
        output_directory=LOCAL_EXPORTS_DIRECTORY / "notes_site"
    )

    flask_application_instance: Flask = Flask(__name__)
    flask_application_instance.config["JSON_SORT_KEYS"] = False

    # Suppress verbose default flask logging in favor of structured logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # ─────────────────────────────────────────────────────────────────────────
    # REST API Endpoints (Policy §10 / Plan Section 6)
    # ─────────────────────────────────────────────────────────────────────────

    @flask_application_instance.route("/api/v1/context", methods=["GET"])
    def get_active_chamber_context_endpoint() -> Response:
        """Retrieve active chamber selection, loaded note, and category."""
        active_context_dictionary: Dict[str, Optional[str]] = database_engine.get_active_context()
        loaded_note_record: Optional[Dict[str, Any]] = database_engine.get_loaded_note()
        loaded_category_record: Optional[Dict[str, Any]] = database_engine.get_loaded_category()

        response_payload_dictionary: Dict[str, Any] = {
            "status": "success",
            "active_mode": active_context_dictionary.get("active_mode", "notes"),
            "active_category": active_context_dictionary.get("active_category"),
            "active_entry": active_context_dictionary.get("active_entry"),
            "loaded_note": loaded_note_record,
            "loaded_category": loaded_category_record
        }
        return jsonify(response_payload_dictionary)

    @flask_application_instance.route("/api/v1/chamber/select", methods=["POST"])
    def select_chamber_target_endpoint() -> Response:
        """Lock category or note into chamber."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        target_note_identifier: Optional[str] = request_incoming_json.get("note_identifier")
        target_category_identifier: Optional[str] = request_incoming_json.get("category_identifier")

        result_note_record: Optional[Dict[str, Any]] = None
        result_category_record: Optional[Dict[str, Any]] = None

        if target_category_identifier:
            result_category_record = database_engine.select_category(target_category_identifier)

        if target_note_identifier:
            result_note_record = database_engine.select_note(target_note_identifier)

        return jsonify({
            "status": "success",
            "selected_note": result_note_record,
            "selected_category": result_category_record
        })

    @flask_application_instance.route("/api/v1/chamber/clear", methods=["POST"])
    def clear_chamber_selection_endpoint() -> Response:
        """Clear chamber selection."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        clear_scope_target: str = request_incoming_json.get("scope", "note")

        if clear_scope_target == "all":
            database_engine.clear_all()
        elif clear_scope_target == "category":
            database_engine.clear_category()
        else:
            database_engine.clear_note()

        return jsonify({"status": "success", "cleared_scope": clear_scope_target})

    @flask_application_instance.route("/api/v1/categories", methods=["GET"])
    def list_categories_endpoint() -> Response:
        """Return all categories with note count metrics."""
        category_records_list: List[Dict[str, Any]] = database_engine.list_categories()
        return jsonify({
            "status": "success",
            "categories": category_records_list,
            "total_count": len(category_records_list)
        })

    @flask_application_instance.route("/api/v1/categories", methods=["POST"])
    def create_category_endpoint() -> Response:
        """Create a new category in MFDB."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        category_name_string: str = str(request_incoming_json.get("cat_name", "")).strip()
        category_description_string: str = str(request_incoming_json.get("cat_description", "")).strip()

        if not category_name_string:
            return jsonify({"status": "error", "message": "Category name is required"}), 400

        try:
            created_category_record: Dict[str, Any] = database_engine.create_category(
                category_name=category_name_string,
                description=category_description_string
            )
            return jsonify({"status": "success", "category": created_category_record}), 201
        except Exception as operation_exception_error:
            return jsonify({"status": "error", "message": str(operation_exception_error)}), 400

    @flask_application_instance.route("/api/v1/notes", methods=["GET"])
    def list_notes_endpoint() -> Response:
        """Query notes with optional category filter or search keyword."""
        category_filter_parameter: Optional[str] = request.args.get("category")
        search_query_keyword: Optional[str] = request.args.get("query")
        include_all_flag: bool = request.args.get("all", "false").lower() in ("true", "1")

        if search_query_keyword and search_query_keyword.strip():
            notes_collection: List[Dict[str, Any]] = database_engine.query_notes(search_query_keyword.strip())
        else:
            notes_collection = database_engine.list_notes(
                category_filter=category_filter_parameter,
                all_notes=include_all_flag or (category_filter_parameter is None)
            )

        return jsonify({
            "status": "success",
            "notes": notes_collection,
            "total_count": len(notes_collection)
        })

    @flask_application_instance.route("/api/v1/notes/<string:note_identifier>", methods=["GET"])
    def get_single_note_endpoint(note_identifier: str) -> Response:
        """Retrieve full note payload."""
        found_note_record: Optional[Dict[str, Any]] = database_engine.find_note(note_identifier)
        if not found_note_record:
            return jsonify({"status": "error", "message": f"Note '{note_identifier}' not found"}), 404

        # Auto-lock loaded note into chamber
        database_engine.select_note(note_identifier)
        return jsonify({"status": "success", "note": found_note_record})

    @flask_application_instance.route("/api/v1/notes", methods=["POST"])
    def create_note_endpoint() -> Response:
        """Create a new note in MFDB."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        note_title_string: str = str(request_incoming_json.get("title", "")).strip()
        note_category_string: str = str(request_incoming_json.get("category_name", "")).strip()
        note_content_markdown: str = str(request_incoming_json.get("content", ""))
        note_tags_array: List[str] = request_incoming_json.get("tags", [])

        if not note_title_string:
            return jsonify({"status": "error", "message": "Note title is required"}), 400
        if not note_category_string:
            return jsonify({"status": "error", "message": "Category name is required"}), 400

        try:
            created_note_record: Dict[str, Any] = database_engine.create_note(
                title=note_title_string,
                category_name=note_category_string,
                content=note_content_markdown,
                tags=note_tags_array
            )
            # Auto-lock new note into chamber
            database_engine.select_note(created_note_record["note_id"])
            return jsonify({"status": "success", "note": created_note_record}), 201
        except Exception as operation_exception_error:
            return jsonify({"status": "error", "message": str(operation_exception_error)}), 400

    @flask_application_instance.route("/api/v1/notes/<string:note_identifier>", methods=["PUT"])
    def update_note_endpoint(note_identifier: str) -> Response:
        """Update existing note properties and content."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        note_title_string: Optional[str] = request_incoming_json.get("title")
        note_content_markdown: Optional[str] = request_incoming_json.get("content")
        note_category_string: Optional[str] = request_incoming_json.get("category_name")
        note_tags_array: Optional[List[str]] = request_incoming_json.get("tags")

        try:
            updated_note_record: Dict[str, Any] = database_engine.update_note(
                identifier_or_title=note_identifier,
                new_title=note_title_string,
                new_category_name=note_category_string,
                new_content=note_content_markdown,
                new_tags=note_tags_array
            )
            return jsonify({"status": "success", "note": updated_note_record})
        except Exception as operation_exception_error:
            return jsonify({"status": "error", "message": str(operation_exception_error)}), 400

    @flask_application_instance.route("/api/v1/notes/<string:note_identifier>", methods=["DELETE"])
    def delete_note_endpoint(note_identifier: str) -> Response:
        """Delete note record from MFDB."""
        try:
            deletion_result: Dict[str, Any] = database_engine.delete_note(note_identifier)
            return jsonify({"status": "success", "result": deletion_result})
        except Exception as operation_exception_error:
            return jsonify({"status": "error", "message": str(operation_exception_error)}), 400

    @flask_application_instance.route("/api/v1/preview", methods=["POST"])
    def render_markdown_preview_endpoint() -> Response:
        """Render raw Markdown text into structured HTML."""
        request_incoming_json: Dict[str, Any] = request.get_json(silent=True) or {}
        raw_markdown_text: str = str(request_incoming_json.get("markdown", ""))
        rendered_html_string: str = markdown_engine.convert_markdown(raw_markdown_text)
        return jsonify({"status": "success", "html": rendered_html_string})

    @flask_application_instance.route("/api/v1/export/all", methods=["POST"])
    def export_entire_site_endpoint() -> Response:
        """Trigger static site export using NotesSiteExporter."""
        try:
            export_manifest_summary: Dict[str, Any] = site_exporter_instance.export_entire_site()
            return jsonify({"status": "success", "manifest": export_manifest_summary})
        except Exception as operation_exception_error:
            return jsonify({"status": "error", "message": str(operation_exception_error)}), 500

    # ─────────────────────────────────────────────────────────────────────────
    # Primary Responsive Web UI (Single Page Application)
    # ─────────────────────────────────────────────────────────────────────────

    @flask_application_instance.route("/", methods=["GET"])
    def serve_primary_web_interface_endpoint() -> str:
        """Serve self-contained HTML/CSS/JavaScript editor workspace."""
        return render_template_string(PRIMARY_INTERFACE_HTML_TEMPLATE)

    return flask_application_instance


# ── Inline Single-Page Application HTML/CSS/JS Template ──────────────────────
# Adheres strictly to Policy §8.1 Tri-Color (#05070B / #F1F5F9 / #DE2626),
# §8.2 Cubes Branding, §8.4 Layout & Toolbars, §9.2 Author Credits.
PRIMARY_INTERFACE_HTML_TEMPLATE: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>BEJSON Notes Editor</title>
  <style>
    /* ── Policy §8.1 Tri-Color Brand Tokens ────────────────────────────── */
    :root {
      --bg-canvas: #05070B;
      --bg-surface: #0B0F17;
      --bg-elevated: #111827;
      --bg-editor: #04060A;
      --border-subtle: #1E293B;
      --border-accent: #DE2626;
      --accent-red: #DE2626;
      --accent-hover: #EF4444;
      --accent-dim: rgba(222, 38, 38, 0.15);
      --text-main: #F1F5F9;
      --text-muted: #94A3B8;
      --text-dim: #64748B;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
      --sidebar-width: 280px;
      --header-height: 52px;
      --toolbar-height: 48px;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: var(--bg-canvas);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }

    /* ── App Shell Grid ───────────────────────────────────────────────── */
    #app-container-root {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
    }

    /* ── Global Header (Policy §8.4) ──────────────────────────────────── */
    #header-global-navigation-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: var(--header-height);
      padding: 0 16px;
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      flex-shrink: 0;
      z-index: 50;
    }

    .brand-group-container {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .button-mobile-hamburger-toggle {
      display: none;
      background: none;
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
      min-width: 36px;
      min-height: 36px;
    }

    .brand-title-heading {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-accent-tag {
      background-color: var(--accent-dim);
      color: var(--accent-red);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 3px;
      border: 1px solid var(--accent-red);
    }

    .chamber-status-container {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-mono);
      font-size: 12px;
    }

    .status-indicator-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--accent-red);
      display: inline-block;
    }

    .status-indicator-dot.synced {
      background-color: #22C55E;
    }

    /* ── Main Workspace Split Layout ──────────────────────────────────── */
    #workspace-main-flex-layout {
      display: flex;
      flex: 1;
      height: calc(100vh - var(--header-height));
      overflow: hidden;
      position: relative;
    }

    /* ── Sidebar Navigation Tree (Principle 2) ────────────────────────── */
    #sidebar-navigation-drawer {
      width: var(--sidebar-width);
      height: 100%;
      background-color: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 40;
    }

    .sidebar-search-container {
      padding: 12px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .input-standard-text {
      width: 100%;
      background-color: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 8px 12px;
      font-size: 13px;
      border-radius: 4px;
      outline: none;
      transition: border-color 0.15s;
    }

    .input-standard-text:focus {
      border-color: var(--accent-red);
    }

    .sidebar-categories-tree {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .category-tree-node-button {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 8px 10px;
      background: none;
      border: 1px solid transparent;
      color: var(--text-muted);
      border-radius: 4px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      text-align: left;
    }

    .category-tree-node-button:hover {
      background-color: var(--bg-elevated);
      color: var(--text-main);
    }

    .category-tree-node-button.active {
      background-color: var(--accent-dim);
      color: var(--accent-red);
      border-color: var(--border-accent);
    }

    .category-count-badge {
      font-family: var(--font-mono);
      font-size: 11px;
      background-color: var(--bg-canvas);
      padding: 2px 6px;
      border-radius: 10px;
      color: var(--text-dim);
    }

    .sidebar-notes-card-list {
      flex: 1.5;
      overflow-y: auto;
      border-top: 1px solid var(--border-subtle);
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .note-list-card-item {
      padding: 10px;
      background-color: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }

    .note-list-card-item:hover {
      border-color: var(--text-dim);
      transform: translateY(-1px);
    }

    .note-list-card-item.active {
      border-left: 4px solid var(--accent-red);
      background-color: var(--bg-elevated);
      border-color: var(--border-accent);
    }

    .note-card-title-label {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .note-card-meta-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--font-mono);
    }

    /* ── Central Editor & Preview Canvas ──────────────────────────────── */
    #editor-viewport-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
      background-color: var(--bg-canvas);
    }

    /* ── Principle 6: Top Feature Action Toolbar (Single-Row Horizontal) ─ */
    #toolbar-top-feature-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      height: var(--toolbar-height);
      padding: 0 16px;
      background-color: var(--bg-elevated);
      border-bottom: 1px solid var(--border-subtle);
      overflow-x: auto;
      white-space: nowrap;
      flex-shrink: 0;
      -webkit-overflow-scrolling: touch;
    }

    #toolbar-top-feature-actions::-webkit-scrollbar {
      height: 3px;
    }

    #toolbar-top-feature-actions::-webkit-scrollbar-thumb {
      background-color: var(--border-accent);
    }

    .action-button-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-size: 12px;
      font-weight: 500;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
      flex-shrink: 0;
      min-height: 32px;
    }

    .action-button-pill:hover {
      background-color: var(--bg-canvas);
      border-color: var(--accent-red);
      color: var(--accent-red);
    }

    .action-button-pill.primary {
      background-color: var(--accent-red);
      border-color: var(--accent-red);
      color: #FFFFFF;
    }

    .action-button-pill.primary:hover {
      background-color: var(--accent-hover);
    }

    .select-standard-dropdown {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 6px 10px;
      font-size: 12px;
      border-radius: 4px;
      outline: none;
      min-height: 32px;
      cursor: pointer;
    }

    .select-standard-dropdown:focus {
      border-color: var(--accent-red);
    }

    /* ── Note Title Bar ───────────────────────────────────────────────── */
    .note-metadata-header-strip {
      padding: 12px 16px;
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex-shrink: 0;
    }

    .input-headline-title {
      width: 100%;
      background: none;
      border: none;
      color: var(--text-main);
      font-size: 18px;
      font-weight: 700;
      outline: none;
      padding: 2px 0;
    }

    .input-tags-subfield {
      width: 100%;
      background: none;
      border: none;
      color: var(--accent-red);
      font-family: var(--font-mono);
      font-size: 12px;
      outline: none;
    }

    /* ── Split Work Area ──────────────────────────────────────────────── */
    #workspace-split-canvas-area {
      display: flex;
      flex: 1;
      height: 100%;
      overflow: hidden;
    }

    .editor-pane-surface {
      flex: 1;
      height: 100%;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border-subtle);
      background-color: var(--bg-editor);
    }

    #textarea-markdown-editor-surface {
      width: 100%;
      height: 100%;
      background-color: transparent;
      border: none;
      color: var(--text-main);
      font-family: var(--font-mono);
      font-size: 13px;
      line-height: 1.6;
      padding: 16px;
      resize: none;
      outline: none;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    .preview-pane-surface {
      flex: 1;
      height: 100%;
      overflow-y: auto;
      padding: 20px 24px;
      background-color: var(--bg-canvas);
      color: var(--text-main);
    }

    /* ── Rendered Preview Content Typography (Ry=32px) ────────────────── */
    .preview-content-article h1, .preview-content-article h2, .preview-content-article h3 {
      color: var(--text-main);
      margin-top: 1.2em;
      margin-bottom: 0.5em;
      font-weight: 700;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 4px;
    }

    .preview-content-article h1 { font-size: 22px; color: var(--accent-red); }
    .preview-content-article h2 { font-size: 18px; }
    .preview-content-article h3 { font-size: 15px; }

    .preview-content-article p {
      margin-bottom: 1em;
      color: var(--text-main);
      line-height: 1.7;
    }

    .preview-content-article code {
      font-family: var(--font-mono);
      background-color: var(--bg-elevated);
      color: var(--accent-red);
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 12px;
    }

    .preview-content-article pre {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 1em 0;
    }

    .preview-content-article pre code {
      background: none;
      color: var(--text-main);
      padding: 0;
    }

    .preview-content-article ul, .preview-content-article ol {
      margin-left: 20px;
      margin-bottom: 1em;
    }

    .preview-content-article li {
      margin-bottom: 4px;
    }

    .preview-content-article blockquote {
      border-left: 3px solid var(--accent-red);
      padding-left: 12px;
      color: var(--text-muted);
      margin: 1em 0;
    }

    /* ── Principle 7: Bottom Confirmation Toolbar (Single-Row) ────────── */
    #toolbar-bottom-confirmation-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 44px;
      padding: 0 16px;
      background-color: var(--bg-surface);
      border-top: 1px solid var(--border-subtle);
      flex-shrink: 0;
    }

    .footer-action-buttons-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .footer-metrics-strip {
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-dim);
    }

    /* ── Mobile Responsive Overrides (Principle 1 & 4) ─────────────────── */
    @media (max-width: 768px) {
      .button-mobile-hamburger-toggle {
        display: inline-block;
      }

      #sidebar-navigation-drawer {
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        transform: translateX(-100%);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.7);
      }

      #sidebar-navigation-drawer.open {
        transform: translateX(0);
      }

      #mobile-drawer-backdrop-scrim {
        display: none;
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.6);
        z-index: 35;
      }

      #mobile-drawer-backdrop-scrim.open {
        display: block;
      }

      #workspace-split-canvas-area {
        flex-direction: column;
      }

      .editor-pane-surface.hidden-on-mobile,
      .preview-pane-surface.hidden-on-mobile {
        display: none;
      }

      .editor-pane-surface {
        border-right: none;
      }
    }
  </style>
</head>
<body>

<div id="app-container-root">

  <!-- Global Header Bar -->
  <header id="header-global-navigation-bar">
    <div class="brand-group-container">
      <button id="button-hamburger-menu" class="button-mobile-hamburger-toggle" aria-label="Toggle Navigation">☰</button>
      
      <!-- MFDB Cube Brand Anchor (Policy §8.2 / §8.3e) -->
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="8" width="8" height="8" fill="#DE2626" />
        <rect x="2" y="2" width="4" height="4" stroke="#DE2626" stroke-width="1.5" />
        <rect x="18" y="2" width="4" height="4" stroke="#DE2626" stroke-width="1.5" />
        <rect x="2" y="18" width="4" height="4" stroke="#DE2626" stroke-width="1.5" />
        <rect x="18" y="18" width="4" height="4" stroke="#DE2626" stroke-width="1.5" />
        <line x1="6" y1="4" x2="8" y2="8" stroke="#DE2626" stroke-width="1.2" />
        <line x1="18" y1="4" x2="16" y2="8" stroke="#DE2626" stroke-width="1.2" />
        <line x1="6" y1="20" x2="8" y2="16" stroke="#DE2626" stroke-width="1.2" />
        <line x1="18" y1="20" x2="16" y2="16" stroke="#DE2626" stroke-width="1.2" />
      </svg>
      <span class="brand-title-heading">BEJSON NOTES <span class="badge-accent-tag">WEB</span></span>
    </div>

    <div class="chamber-status-container">
      <span id="indicator-status-dot" class="status-indicator-dot synced"></span>
      <span id="label-active-note-display" style="color: var(--text-muted);">(No note selected)</span>
    </div>
  </header>

  <!-- Workspace Area -->
  <div id="workspace-main-flex-layout">
    
    <div id="mobile-drawer-backdrop-scrim"></div>

    <!-- Sidebar Drawer -->
    <aside id="sidebar-navigation-drawer">
      <div class="sidebar-search-container">
        <input type="text" id="input-sidebar-search-filter" class="input-standard-text" placeholder="Search notes & tags..." />
        <button id="button-create-new-category" class="action-button-pill" style="width: 100%; justify-content: center;">+ New Category</button>
      </div>

      <!-- Categories Tree -->
      <div id="container-category-tree-nodes" class="sidebar-categories-tree">
        <!-- Rendered via JavaScript -->
      </div>

      <!-- Notes Card Stream -->
      <div id="container-notes-card-stream" class="sidebar-notes-card-list">
        <!-- Rendered via JavaScript -->
      </div>
    </aside>

    <!-- Center Workspace -->
    <main id="editor-viewport-container">
      
      <!-- Top Action Toolbar (Principle 6) -->
      <nav id="toolbar-top-feature-actions">
        <button id="button-action-new-note" class="action-button-pill primary">+ New Note</button>
        <select id="select-note-category-picker" class="select-standard-dropdown">
          <option value="">Select Category...</option>
        </select>
        <button id="button-view-toggle-mode" class="action-button-pill">View: Split</button>
        <button id="button-action-export-static-site" class="action-button-pill">Export Site</button>
        <button id="button-action-close-note" class="action-button-pill">Close Note</button>
      </nav>

      <!-- Headline & Tags Strip -->
      <div class="note-metadata-header-strip">
        <input type="text" id="input-note-title-field" class="input-headline-title" placeholder="Untitled Note Title..." />
        <input type="text" id="input-note-tags-field" class="input-tags-subfield" placeholder="#tags #comma-separated" />
      </div>

      <!-- Split Canvas -->
      <div id="workspace-split-canvas-area">
        <section id="pane-markdown-editor-surface" class="editor-pane-surface">
          <textarea id="textarea-markdown-editor-surface" placeholder="Type Markdown content here..." spellcheck="false"></textarea>
        </section>

        <section id="pane-html-preview-surface" class="preview-pane-surface">
          <article id="article-preview-html-content" class="preview-content-article">
            <p style="color: var(--text-dim);">(Preview will render here...)</p>
          </article>
        </section>
      </div>

      <!-- Bottom Confirmation Toolbar (Principle 7) -->
      <footer id="toolbar-bottom-confirmation-bar">
        <div class="footer-action-buttons-group">
          <button id="button-action-save-note" class="action-button-pill primary">💾 Save Note</button>
          <button id="button-action-delete-note" class="action-button-pill">🗑 Delete</button>
          <span id="label-save-status-text" style="font-size: 11px; font-family: var(--font-mono); color: var(--text-dim);">Idle</span>
        </div>

        <div class="footer-metrics-strip">
          <span id="label-metrics-word-count">Words: 0</span>
          <span>·</span>
          <span>Elton Boehnen</span>
        </div>
      </footer>

    </main>

  </div>

</div>

<!-- ── Application Logic (JavaScript - Policy §6.1 / §8.4) ──────────────── -->
<script>
  // ── Global Application State ──────────────────────────────────────────────
  let current_loaded_note_identifier = null;
  let current_active_category_name = null;
  let current_categories_list = [];
  let current_notes_list = [];
  let is_document_dirty_flag = false;
  let active_viewport_display_mode = "split"; // "split", "editor", "preview"
  let markdown_preview_debounce_timer = null;

  // ── DOM Element Cached References (Policy §6.1) ───────────────────────────
  const dom_hamburger_toggle_button = document.getElementById("button-hamburger-menu");
  const dom_sidebar_drawer_element = document.getElementById("sidebar-navigation-drawer");
  const dom_drawer_scrim_element = document.getElementById("mobile-drawer-backdrop-scrim");
  const dom_category_tree_container = document.getElementById("container-category-tree-nodes");
  const dom_notes_stream_container = document.getElementById("container-notes-card-stream");
  const dom_search_filter_input = document.getElementById("input-sidebar-search-filter");
  const dom_category_dropdown_picker = document.getElementById("select-note-category-picker");
  const dom_note_title_input = document.getElementById("input-note-title-field");
  const dom_note_tags_input = document.getElementById("input-note-tags-field");
  const dom_markdown_textarea = document.getElementById("textarea-markdown-editor-surface");
  const dom_preview_html_article = document.getElementById("article-preview-html-content");
  const dom_active_note_label_display = document.getElementById("label-active-note-display");
  const dom_status_indicator_dot = document.getElementById("indicator-status-dot");
  const dom_save_status_label = document.getElementById("label-save-status-text");
  const dom_word_count_label = document.getElementById("label-metrics-word-count");
  const dom_save_button_element = document.getElementById("button-action-save-note");
  const dom_delete_button_element = document.getElementById("button-action-delete-note");
  const dom_new_note_button = document.getElementById("button-action-new-note");
  const dom_view_toggle_button = document.getElementById("button-view-toggle-mode");
  const dom_export_site_button = document.getElementById("button-action-export-static-site");
  const dom_close_note_button = document.getElementById("button-action-close-note");
  const dom_new_category_button = document.getElementById("button-create-new-category");
  const dom_editor_pane_surface = document.getElementById("pane-markdown-editor-surface");
  const dom_preview_pane_surface = document.getElementById("pane-html-preview-surface");

  // ── Network API Dispatchers ───────────────────────────────────────────────
  async function fetch_categories_data() {
    try {
      const response = await fetch("/api/v1/categories");
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        current_categories_list = json_payload.categories;
        render_categories_tree();
        render_categories_dropdown();
      }
    } catch (error) {
      console.error("Failed to fetch categories:", error);
    }
  }

  async function fetch_notes_data(category_filter = null, search_keyword = null) {
    try {
      let query_url = "/api/v1/notes?";
      if (category_filter) query_url += `category=${encodeURIComponent(category_filter)}&`;
      if (search_keyword) query_url += `query=${encodeURIComponent(search_keyword)}&`;
      if (!category_filter && !search_keyword) query_url += "all=true";

      const response = await fetch(query_url);
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        current_notes_list = json_payload.notes;
        render_notes_card_stream();
      }
    } catch (error) {
      console.error("Failed to fetch notes:", error);
    }
  }

  async function load_single_note_by_identifier(note_identifier) {
    if (is_document_dirty_flag) {
      if (!confirm("You have unsaved changes. Discard and load target note?")) {
        return;
      }
    }

    try {
      set_status_display("Loading note...", false);
      const response = await fetch(`/api/v1/notes/${encodeURIComponent(note_identifier)}`);
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        const note_record = json_payload.note;
        current_loaded_note_identifier = note_record.note_id;
        dom_note_title_input.value = note_record.title;
        dom_category_dropdown_picker.value = note_record.category_name;
        dom_note_tags_input.value = (note_record.tags || []).map(t => `#${t}`).join(" ");
        dom_markdown_textarea.value = note_record.content || "";
        
        is_document_dirty_flag = false;
        update_active_note_header_display(note_record.title, note_record.note_id);
        trigger_markdown_preview_render(note_record.content || "");
        update_word_count_metric(note_record.content || "");
        set_status_display("Loaded · MFDB", true);
        render_notes_card_stream();

        // On mobile, close drawer automatically after selection
        close_mobile_drawer();
      }
    } catch (error) {
      console.error("Failed to load note:", error);
      set_status_display("Error loading note", false);
    }
  }

  async function save_active_note_payload() {
    const title_value = dom_note_title_input.value.trim();
    const category_value = dom_category_dropdown_picker.value;
    const content_value = dom_markdown_textarea.value;
    const raw_tags_value = dom_note_tags_input.value;
    const tags_array = raw_tags_value.split(/[ ,#]+/).filter(Boolean);

    if (!title_value) {
      alert("Note title cannot be empty.");
      dom_note_title_input.focus();
      return;
    }
    if (!category_value) {
      alert("Please select a valid category.");
      dom_category_dropdown_picker.focus();
      return;
    }

    set_status_display("Saving to MFDB...", false);

    try {
      let response;
      if (current_loaded_note_identifier) {
        // Update existing note
        response = await fetch(`/api/v1/notes/${encodeURIComponent(current_loaded_note_identifier)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title_value,
            category_name: category_value,
            content: content_value,
            tags: tags_array
          })
        });
      } else {
        // Create brand new note
        response = await fetch("/api/v1/notes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title_value,
            category_name: category_value,
            content: content_value,
            tags: tags_array
          })
        });
      }

      const json_payload = await response.json();
      if (json_payload.status === "success") {
        current_loaded_note_identifier = json_payload.note.note_id;
        is_document_dirty_flag = false;
        update_active_note_header_display(title_value, current_loaded_note_identifier);
        set_status_display(`Saved · ${new Date().toLocaleTimeString()}`, true);
        await fetch_categories_data();
        await fetch_notes_data(current_active_category_name);
      } else {
        alert(`Failed to save: ${json_payload.message}`);
        set_status_display("Save error", false);
      }
    } catch (error) {
      console.error("Save failed:", error);
      set_status_display("Network save error", false);
    }
  }

  async function delete_active_note() {
    if (!current_loaded_note_identifier) {
      alert("No note is currently loaded to delete.");
      return;
    }

    if (!confirm(`Permanently delete note '${dom_note_title_input.value}' from MFDB?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/notes/${encodeURIComponent(current_loaded_note_identifier)}`, {
        method: "DELETE"
      });
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        clear_editor_form();
        await fetch_categories_data();
        await fetch_notes_data(current_active_category_name);
        set_status_display("Deleted note", true);
      } else {
        alert(`Delete failed: ${json_payload.message}`);
      }
    } catch (error) {
      console.error("Delete failed:", error);
    }
  }

  async function trigger_markdown_preview_render(markdown_source_text) {
    try {
      const response = await fetch("/api/v1/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: markdown_source_text })
      });
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        dom_preview_html_article.innerHTML = json_payload.html || "<p style='color: var(--text-dim);'>(Empty document)</p>";
      }
    } catch (error) {
      console.error("Preview render failed:", error);
    }
  }

  // ── UI Rendering & View Logic ─────────────────────────────────────────────
  function render_categories_tree() {
    dom_category_tree_container.innerHTML = "";
    
    // "All Categories" Node
    const all_node_button = document.createElement("button");
    all_node_button.className = `category-tree-node-button ${current_active_category_name === null ? "active" : ""}`;
    const total_notes_count = current_categories_list.reduce((sum, c) => sum + (c.note_count || 0), 0);
    all_node_button.innerHTML = `<span>📂 All Categories</span><span class="category-count-badge">${total_notes_count}</span>`;
    all_node_button.onclick = () => {
      current_active_category_name = null;
      render_categories_tree();
      fetch_notes_data(null, dom_search_filter_input.value);
    };
    dom_category_tree_container.appendChild(all_node_button);

    // Individual Category Nodes
    current_categories_list.forEach(category => {
      const node_button = document.createElement("button");
      const is_active = current_active_category_name === category.cat_name;
      node_button.className = `category-tree-node-button ${is_active ? "active" : ""}`;
      node_button.innerHTML = `<span>• ${escape_html(category.cat_name)}</span><span class="category-count-badge">${category.note_count || 0}</span>`;
      node_button.onclick = () => {
        current_active_category_name = category.cat_name;
        render_categories_tree();
        fetch_notes_data(category.cat_name, dom_search_filter_input.value);
      };
      dom_category_tree_container.appendChild(node_button);
    });
  }

  function render_categories_dropdown() {
    dom_category_dropdown_picker.innerHTML = "<option value=''>Select Category...</option>";
    current_categories_list.forEach(category => {
      const option = document.createElement("option");
      option.value = category.cat_name;
      option.textContent = category.cat_name;
      dom_category_dropdown_picker.appendChild(option);
    });
  }

  function render_notes_card_stream() {
    dom_notes_stream_container.innerHTML = "";
    if (current_notes_list.length === 0) {
      dom_notes_stream_container.innerHTML = "<div style='color: var(--text-dim); padding: 12px; font-size: 12px; text-align: center;'>No notes found.</div>";
      return;
    }

    current_notes_list.forEach(note => {
      const card_element = document.createElement("div");
      const is_active = current_loaded_note_identifier === note.note_id;
      card_element.className = `note-list-card-item ${is_active ? "active" : ""}`;
      
      const words = (note.content || "").split(/\\s+/).filter(Boolean).length;
      const tags_display = (note.tags || []).slice(0, 2).map(t => `#${t}`).join(" ");

      card_element.innerHTML = `
        <div class="note-card-title-label">${escape_html(note.title)}</div>
        <div class="note-card-meta-row">
          <span>${escape_html(note.category_name || "General")}</span>
          <span>${words}w</span>
        </div>
      `;
      card_element.onclick = () => load_single_note_by_identifier(note.note_id);
      dom_notes_stream_container.appendChild(card_element);
    });
  }

  function clear_editor_form() {
    current_loaded_note_identifier = null;
    dom_note_title_input.value = "";
    dom_markdown_textarea.value = "";
    dom_note_tags_input.value = "";
    if (current_active_category_name) {
      dom_category_dropdown_picker.value = current_active_category_name;
    }
    is_document_dirty_flag = false;
    update_active_note_header_display("(No note selected)", null);
    trigger_markdown_preview_render("");
    update_word_count_metric("");
    set_status_display("New Draft", true);
    render_notes_card_stream();
  }

  function update_active_note_header_display(title, identifier) {
    if (identifier) {
      dom_active_note_label_display.textContent = `[${identifier}] ${title.substring(0, 36)}`;
      dom_active_note_label_display.style.color = "var(--text-main)";
    } else {
      dom_active_note_label_display.textContent = "(No note selected)";
      dom_active_note_label_display.style.color = "var(--text-dim)";
    }
  }

  function set_status_display(status_message, is_synced) {
    dom_save_status_label.textContent = status_message;
    if (is_synced) {
      dom_status_indicator_dot.classList.add("synced");
    } else {
      dom_status_indicator_dot.classList.remove("synced");
    }
  }

  function update_word_count_metric(text_content) {
    const words = text_content.trim().split(/\\s+/).filter(Boolean).length;
    const est_reading_mins = Math.max(1, Math.ceil(words / 200));
    dom_word_count_label.textContent = `Words: ${words} · Read: ~${est_reading_mins}m`;
  }

  function toggle_viewport_display_mode() {
    if (active_viewport_display_mode === "split") {
      active_viewport_display_mode = "editor";
      dom_view_toggle_button.textContent = "View: Editor";
      dom_editor_pane_surface.style.display = "flex";
      dom_preview_pane_surface.style.display = "none";
    } else if (active_viewport_display_mode === "editor") {
      active_viewport_display_mode = "preview";
      dom_view_toggle_button.textContent = "View: Preview";
      dom_editor_pane_surface.style.display = "none";
      dom_preview_pane_surface.style.display = "block";
    } else {
      active_viewport_display_mode = "split";
      dom_view_toggle_button.textContent = "View: Split";
      dom_editor_pane_surface.style.display = "flex";
      dom_preview_pane_surface.style.display = "block";
    }
  }

  function open_mobile_drawer() {
    dom_sidebar_drawer_element.classList.add("open");
    dom_drawer_scrim_element.classList.add("open");
  }

  function close_mobile_drawer() {
    dom_sidebar_drawer_element.classList.remove("open");
    dom_drawer_scrim_element.classList.remove("open");
  }

  function escape_html(str) {
    return (str || "").replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // ── Event Handlers & Keybindings ──────────────────────────────────────────
  dom_hamburger_toggle_button.onclick = open_mobile_drawer;
  dom_drawer_scrim_element.onclick = close_mobile_drawer;
  dom_new_note_button.onclick = clear_editor_form;
  dom_save_button_element.onclick = save_active_note_payload;
  dom_delete_button_element.onclick = delete_active_note;
  dom_view_toggle_button.onclick = toggle_viewport_display_mode;

  dom_close_note_button.onclick = async () => {
    await fetch("/api/v1/chamber/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: "note" })
    });
    clear_editor_form();
  };

  dom_new_category_button.onclick = async () => {
    const category_name_input = prompt("Enter new category name:");
    if (!category_name_input || !category_name_input.trim()) return;
    try {
      const response = await fetch("/api/v1/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cat_name: category_name_input.trim() })
      });
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        await fetch_categories_data();
      } else {
        alert(json_payload.message);
      }
    } catch (e) {
      alert("Failed to create category");
    }
  };

  dom_export_site_button.onclick = async () => {
    set_status_display("Exporting static site...", false);
    try {
      const response = await fetch("/api/v1/export/all", { method: "POST" });
      const json_payload = await response.json();
      if (json_payload.status === "success") {
        alert("Static site generated successfully in exports/notes_site!");
        set_status_display("Site exported", true);
      } else {
        alert(`Export failed: ${json_payload.message}`);
      }
    } catch (e) {
      alert("Export failed: network error");
    }
  };

  // Live input synchronization & debounced preview
  dom_markdown_textarea.addEventListener("input", (e) => {
    is_document_dirty_flag = true;
    set_status_display("Unsaved changes...", false);
    update_word_count_metric(dom_markdown_textarea.value);
    
    clearTimeout(markdown_preview_debounce_timer);
    markdown_preview_debounce_timer = setTimeout(() => {
      trigger_markdown_preview_render(dom_markdown_textarea.value);
    }, 300);
  });

  dom_note_title_input.addEventListener("input", () => {
    is_document_dirty_flag = true;
    set_status_display("Unsaved changes...", false);
  });

  dom_search_filter_input.addEventListener("input", () => {
    fetch_notes_data(current_active_category_name, dom_search_filter_input.value);
  });

  // Hotkey: Ctrl+S or Cmd+S to Save
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      save_active_note_payload();
    }
  });

  // Tab key indent handling in textarea
  dom_markdown_textarea.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = dom_markdown_textarea.selectionStart;
      const end = dom_markdown_textarea.selectionEnd;
      dom_markdown_textarea.value = dom_markdown_textarea.value.substring(0, start) + "  " + dom_markdown_textarea.value.substring(end);
      dom_markdown_textarea.selectionStart = dom_markdown_textarea.selectionEnd = start + 2;
    }
  });

  // ── Bootstrap Initialization ──────────────────────────────────────────────
  window.addEventListener("DOMContentLoaded", async () => {
    await fetch_categories_data();
    await fetch_notes_data();
    
    // Fetch initial context to restore chamber selection
    try {
      const context_resp = await fetch("/api/v1/context");
      const context_data = await context_resp.json();
      if (context_data.loaded_note) {
        await load_single_note_by_identifier(context_data.loaded_note.note_id);
      }
    } catch (e) {
      console.log("No previous active chamber note.");
    }
  });
</script>

</body>
</html>
"""


# ── Launch Helpers (Policy §8.6) ─────────────────────────────────────────────
def copy_url_to_clipboard(target_url_string: str) -> bool:
    """Attempt copying target URL to Android clipboard."""
    candidate_commands: List[List[str]] = [
        ["termux-clipboard-set", target_url_string],
        ["wl-copy", target_url_string],
        ["xclip", "-selection", "clipboard"]
    ]
    for command_vector in candidate_commands:
        if shutil.which(command_vector[0]):
            try:
                subprocess.run(command_vector, input=target_url_string.encode("utf-8"), check=False)
                return True
            except Exception:
                continue
    return False


def launch_browser_background(target_url_string: str) -> None:
    """Launch browser asynchronously via Termux API or system browser."""
    def _execute_open() -> None:
        time.sleep(0.8)
        candidate_openers: List[List[str]] = [
            ["termux-open-url", target_url_string],
            ["termux-open", target_url_string],
            ["xdg-open", target_url_string]
        ]
        for command_vector in candidate_openers:
            if shutil.which(command_vector[0]):
                try:
                    subprocess.run(command_vector, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    continue

    threading.Thread(target=_execute_open, daemon=True).start()


def print_server_status_banner(host_address: str, port_number: int) -> None:
    """Print high-density 57-column startup banner per Policy §8.4."""
    server_url: str = f"http://{host_address}:{port_number}"
    print(DIVIDER_57)
    print(f" {ACCENT}BEJSON NOTES WEB SERVER [FLASK CHAMBER]{RESET}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}URL:{RESET}          {server_url}")
    print(f" {ACCENT}STORAGE:{RESET}      data/mfdb/ (BEJSON 104a)")
    print(f" {ACCENT}STATUS:{RESET}       Listening · Loopback Active")
    print(f" {ACCENT}AUTHOR:{RESET}       Elton Boehnen · boehnenelton2024")
    print(SUBDIVIDER_57)
    print(f" {DIM}Press Ctrl+C to stop the web server gracefully.{RESET}")
    print(DIVIDER_57)


# ── CLI Argument Parser & Entrypoint ─────────────────────────────────────────
def build_cli_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for the notes web server."""
    parser = argparse.ArgumentParser(
        prog="notes_web_server.py",
        description="Stateful Flask Web Application for BEJSON Notes Management (Policy §8.1-§8.7).",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_SERVER_PORT, help=f"Port to bind server (default: {DEFAULT_SERVER_PORT})")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST, help=f"Host address to bind (default: {DEFAULT_SERVER_HOST})")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically launch browser in Termux")
    return parser


def main() -> int:
    """Main execution routine."""
    parser = build_cli_argument_parser()
    parsed_arguments = parser.parse_args()

    server_host: str = parsed_arguments.host
    server_port: int = parsed_arguments.port
    server_url: str = f"http://{server_host}:{server_port}"

    engine = NotesMFDBEngine(base_directory=SUITE_ROOT)
    flask_app = create_notes_web_application(engine_instance=engine)

    # Print high-density 57-column status banner
    print_server_status_banner(server_host, server_port)

    # Copy URL to clipboard
    copy_url_to_clipboard(server_url)

    # Auto-launch browser unless suppressed
    if not parsed_arguments.no_open:
        launch_browser_background(server_url)

    try:
        flask_app.run(host=server_host, port=server_port, debug=False, use_reloader=False)
        return 0
    except KeyboardInterrupt:
        print(f"\n{ACCENT}[✓] Server stopped gracefully.{RESET}")
        return 0
    except Exception as server_exception_error:
        print(f"\n{ACCENT}[✗] Server failed:{RESET} {server_exception_error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
