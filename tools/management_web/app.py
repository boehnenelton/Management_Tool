#!/data/data/com.termux/files/usr/bin/env python3
"""
# Name:           app.py
# Description:    Flask Web Wrapper for System Management Tool — All 7 Subsystems via Hamburger Sidebar
# Version:        100
# Date Created:   2026-11-11
# Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# License:        PolyForm-Noncommercial-1.0.0
# RELATIONAL_ID:  management-web-001
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, render_template, request

# ─── Canonical Path Roots ───────────────────────────────────────────────────
SCRIPT_PATH: Path = Path(__file__).resolve()
SUITE_ROOT: Path = SCRIPT_PATH.parent.parent.parent  # management_tool root
TOOLS_DIR: Path = SUITE_ROOT / "tools"
WEB_ROOT: Path = SCRIPT_PATH.parent

PYTHON: str = sys.executable

TOOL_PATHS: Dict[str, Path] = {
    "logging":     TOOLS_DIR / "logging_tool"     / "logging_tool.py",
    "reports":     TOOLS_DIR / "report_indexer"   / "report_indexer.py",
    "notes":       TOOLS_DIR / "notes_tool"       / "notes_tool.py",
    "jobs":        TOOLS_DIR / "job_manager"      / "job_tool.py",
    "reminders":   TOOLS_DIR / "reminder_tool"    / "reminder_tool.py",
    "environment": TOOLS_DIR / "environment_tool" / "environment_tool.py",
    "blogger":     TOOLS_DIR / "blogger_tool"     / "blogger_tool.py",
}

# ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=str(WEB_ROOT / "templates"),
    static_folder=str(WEB_ROOT / "static"),
)
app.config["SECRET_KEY"] = os.urandom(24)

# ─── CLI Runner ──────────────────────────────────────────────────────────────
def run_cli(tool_key: str, args: List[str], timeout: int = 30) -> Dict[str, Any]:
    """Execute a management CLI tool and return stdout/stderr/returncode."""
    tool_path = TOOL_PATHS.get(tool_key)
    if not tool_path or not tool_path.exists():
        return {"ok": False, "stdout": "", "stderr": f"Tool not found: {tool_key}", "code": 1}
    cmd = [PYTHON, str(tool_path)] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NO_COLOR": "1"},
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Command timed out", "code": 124}
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "code": 1}


def run_cli_json(tool_key: str, args: List[str]) -> Tuple[bool, Any]:
    """Run CLI tool and parse JSON output."""
    res = run_cli(tool_key, args)
    if not res["ok"] and not res["stdout"]:
        return False, res["stderr"]
    try:
        return True, json.loads(res["stdout"])
    except (json.JSONDecodeError, ValueError):
        return True, res["stdout"]


# ─── Main SPA Route ──────────────────────────────────────────────────────────
@app.route("/")
@app.route("/<tool>")
@app.route("/<tool>/<tab>")
def index(tool: str = "logging", tab: str = "read"):
    return render_template("index.html", active_tool=tool, active_tab=tab)


# ═══════════════════════════════════════════════════════════════════════════════
# API: LOGGING  (Mode 1)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/logging/read")
def api_logging_read():
    limit = request.args.get("limit", "50")
    since = request.args.get("since", "")
    min_level = request.args.get("min_level", "")
    args = ["read", "--limit", limit]
    if since:
        args += ["--since", since]
    if min_level:
        args += ["--min-level", min_level]
    res = run_cli("logging", args)
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/logging/write", methods=["POST"])
def api_logging_write():
    body = request.get_json(force=True) or {}
    message = body.get("message", "").strip()
    level = body.get("level", "INFO")
    priority = body.get("priority", "2")
    category = body.get("category", "operational")
    if not message:
        return jsonify({"ok": False, "error": "message required"}), 400
    args = ["write", "-m", message, "-l", level, "-p", str(priority), "--category", category]
    res = run_cli("logging", args)
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: REPORTS  (Mode 2)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/reports/list")
def api_reports_list():
    res = run_cli("reports", ["--list-entries"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/reports/categories")
def api_reports_categories():
    res = run_cli("reports", ["--list-categories"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/reports/search")
def api_reports_search():
    term = request.args.get("q", "")
    if not term:
        return jsonify({"ok": False, "error": "q required"}), 400
    res = run_cli("reports", ["--query", term])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: NOTES  (Mode 3)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/notes/categories")
def api_notes_categories():
    res = run_cli("notes", ["--list-categories"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/notes/list")
def api_notes_list():
    res = run_cli("notes", ["--list-notes"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/notes/search")
def api_notes_search():
    term = request.args.get("q", "")
    if not term:
        return jsonify({"ok": False, "error": "q required"}), 400
    res = run_cli("notes", ["-q", term])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/notes/create", methods=["POST"])
def api_notes_create():
    body = request.get_json(force=True) or {}
    title = body.get("title", "").strip()
    content = body.get("content", "").strip()
    category = body.get("category", "").strip()
    if not title or not content:
        return jsonify({"ok": False, "error": "title and content required"}), 400
    args = ["--note-new", "-t", title, "-c", content]
    if category:
        args += ["--category", category]
    res = run_cli("notes", args)
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: JOBS  (Mode 4)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/jobs/list")
def api_jobs_list():
    res = run_cli("jobs", ["--list"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/jobs/completed")
def api_jobs_completed():
    res = run_cli("jobs", ["--list-completed"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/jobs/maintenance")
def api_jobs_maintenance():
    res = run_cli("jobs", ["--maintenance"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/jobs/search")
def api_jobs_search():
    term = request.args.get("q", "")
    if not term:
        return jsonify({"ok": False, "error": "q required"}), 400
    res = run_cli("jobs", ["--query", term])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: REMINDERS  (Mode 5)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/reminders/list")
def api_reminders_list():
    ok, data = run_cli_json("reminders", ["--json"])
    if isinstance(data, dict):
        return jsonify({"ok": ok, "data": data})
    return jsonify({"ok": ok, "output": data})


@app.route("/api/reminders/add", methods=["POST"])
def api_reminders_add():
    body = request.get_json(force=True) or {}
    text = body.get("text", "").strip()
    priority = body.get("priority", "normal")
    if not text:
        return jsonify({"ok": False, "error": "text required"}), 400
    args = ["add", text, "-p", priority]
    res = run_cli("reminders", args)
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


@app.route("/api/reminders/done", methods=["POST"])
def api_reminders_done():
    body = request.get_json(force=True) or {}
    reminder_id = body.get("id", "").strip()
    if not reminder_id:
        return jsonify({"ok": False, "error": "id required"}), 400
    res = run_cli("reminders", ["done", reminder_id])
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


@app.route("/api/reminders/delete", methods=["POST"])
def api_reminders_delete():
    body = request.get_json(force=True) or {}
    reminder_id = body.get("id", "").strip()
    if not reminder_id:
        return jsonify({"ok": False, "error": "id required"}), 400
    res = run_cli("reminders", ["rm", reminder_id])
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: ENVIRONMENT  (Mode 6 / Extra)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/environment/list")
def api_env_list():
    store = request.args.get("store", "definitions")
    args = ["list"]
    if store == "secure":
        args += ["--secure"]
    res = run_cli("environment", args)
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/environment/get")
def api_env_get():
    var = request.args.get("var", "").strip()
    secure = request.args.get("secure", "0") == "1"
    if not var:
        return jsonify({"ok": False, "error": "var required"}), 400
    args = ["get", var]
    if secure:
        args += ["--secure"]
    res = run_cli("environment", args)
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/environment/set", methods=["POST"])
def api_env_set():
    body = request.get_json(force=True) or {}
    var_name = body.get("name", "").strip()
    var_value = body.get("value", "").strip()
    var_type = body.get("type", "string")
    secure = body.get("secure", False)
    desc = body.get("desc", "")
    if not var_name or not var_value:
        return jsonify({"ok": False, "error": "name and value required"}), 400
    args = ["set", var_name, var_value, "-t", var_type]
    if desc:
        args += ["-d", desc]
    if secure:
        args += ["--secure"]
    res = run_cli("environment", args)
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


# ═══════════════════════════════════════════════════════════════════════════════
# API: BLOGGER  (Mode 7)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/blogger/info")
def api_blogger_info():
    res = run_cli("blogger", ["info"])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/blogger/posts")
def api_blogger_posts():
    limit = request.args.get("limit", "10")
    res = run_cli("blogger", ["posts", "-n", limit])
    return jsonify({"output": res["stdout"], "error": res["stderr"], "ok": res["ok"]})


@app.route("/api/blogger/publish", methods=["POST"])
def api_blogger_publish():
    body = request.get_json(force=True) or {}
    file_path = body.get("file", "").strip()
    title = body.get("title", "").strip()
    labels = body.get("labels", [])
    use_style = body.get("style", False)
    theme = body.get("theme", "light")
    draft = body.get("draft", False)
    if not file_path:
        return jsonify({"ok": False, "error": "file path required"}), 400
    args = ["publish", file_path]
    if title:
        args += ["-t", title]
    for label in labels:
        args += ["-l", label]
    if use_style:
        args += ["--style", "--theme", theme]
    if draft:
        args += ["--draft"]
    res = run_cli("blogger", args, timeout=60)
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


@app.route("/api/blogger/delete", methods=["POST"])
def api_blogger_delete():
    body = request.get_json(force=True) or {}
    post_id = body.get("id", "").strip()
    if not post_id:
        return jsonify({"ok": False, "error": "id required"}), 400
    res = run_cli("blogger", ["delete", post_id])
    return jsonify({"ok": res["ok"], "output": res["stdout"], "error": res["stderr"]})


# ─── Health ───────────────────────────────────────────────────────────────────
@app.route("/api/health")
def api_health():
    tools_status = {}
    for key, path in TOOL_PATHS.items():
        tools_status[key] = path.exists()
    return jsonify({"ok": True, "tools": tools_status, "ts": int(time.time())})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog="management_web")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    parsed = parser.parse_args()
    app.run(host=parsed.host, port=parsed.port, debug=parsed.debug)
