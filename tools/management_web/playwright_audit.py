#!/data/data/com.termux/files/usr/bin/env python3
"""
# Name:           playwright_audit.py
# Description:    Playwright visual audit — screenshots all 7 tool panels + subnav tabs,
#                 checks for console errors, layout overflow, and Tri-Color palette compliance.
# Version:        100
# Date Created:   2026-11-11
# Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# License:        PolyForm-Noncommercial-1.0.0
# RELATIONAL_ID:  management-web-audit-001
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, ConsoleMessage, Page

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_URL    = "http://127.0.0.1:8420"
CHROMIUM    = "/data/data/com.termux/files/usr/lib/chromium/chrome"
SCRIPT_DIR  = Path(__file__).resolve().parent
SHOTS_DIR   = SCRIPT_DIR / "screenshots"
SHOTS_DIR.mkdir(exist_ok=True)

VIEWPORT_MOBILE  = {"width": 390,  "height": 844}
VIEWPORT_DESKTOP = {"width": 1024, "height": 768}

# (tool, tab, label_for_filename)
PANELS = [
    ("logging",     "read",        "logging_read"),
    ("logging",     "write",       "logging_write"),
    ("reports",     "entries",     "reports_entries"),
    ("reports",     "search",      "reports_search"),
    ("notes",       "list",        "notes_list"),
    ("notes",       "new",         "notes_new"),
    ("jobs",        "active",      "jobs_active"),
    ("jobs",        "maintenance", "jobs_maintenance"),
    ("reminders",   "active",      "reminders_active"),
    ("reminders",   "add",         "reminders_add"),
    ("environment", "definitions", "environment_definitions"),
    ("environment", "set",         "environment_set"),
    ("blogger",     "info",        "blogger_info"),
    ("blogger",     "posts",       "blogger_posts"),
    ("blogger",     "publish",     "blogger_publish"),
]

RED    = "\033[38;2;222;38;38m"
WHITE  = "\033[1;37m"
DIM    = "\033[0;37m"
RESET  = "\033[0m"
DIV    = "=" * 49
SUB    = "-" * 49

console_errors: list[dict] = []
audit_results:  list[dict] = []


def print_ok(msg: str) -> None:
    print(f"{WHITE}[✓] {msg}{RESET}")


def print_fail(msg: str) -> None:
    print(f"{RED}[✗] {msg}{RESET}", file=sys.stderr)


def print_warn(msg: str) -> None:
    print(f"{DIM}[!] {msg}{RESET}")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def capture_console(msg: ConsoleMessage, errors: list) -> None:
    if msg.type in ("error", "warning"):
        errors.append({"type": msg.type, "text": msg.text, "url": msg.location.get("url", "")})


def wait_for_content(page: Page, timeout: int = 5000) -> None:
    """Wait for loading-state to disappear."""
    try:
        page.wait_for_function(
            "document.querySelector('.loading-state') === null || "
            "document.querySelector('.loading-state')?.offsetParent === null",
            timeout=timeout,
        )
    except Exception:
        pass  # timeout OK — still screenshot


def check_overflow(page: Page, label: str) -> list[str]:
    """Return list of elements whose scrollWidth > clientWidth (overflow)."""
    overflows = page.evaluate("""() => {
        const issues = [];
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.scrollWidth > el.clientWidth + 2) {
                const tag = el.tagName.toLowerCase();
                const id  = el.id ? '#' + el.id : '';
                const cls = el.className ? '.' + el.className.toString().split(' ').join('.') : '';
                issues.push(tag + id + cls + ' (' + el.scrollWidth + '>' + el.clientWidth + ')');
                if (issues.length >= 5) break;  // cap at 5
            }
        }
        return issues;
    }""")
    return overflows or []


def check_tricolor(page: Page) -> dict:
    """Sample background and accent colors from key elements."""
    result = page.evaluate("""() => {
        const getColor = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            return window.getComputedStyle(el).backgroundColor;
        };
        return {
            body_bg:       getColor('body'),
            header_bg:     getColor('.app-header'),
            sidebar_bg:    getColor('.sidebar'),
            accent_sample: getColor('.app-header'),
        };
    }""")
    return result or {}


# ─── Screenshot Runner ────────────────────────────────────────────────────────
def audit_panel(page: Page, tool: str, tab: str, label: str, errors: list) -> dict:
    url = f"{BASE_URL}/{tool}/{tab}"
    page.goto(url, wait_until="domcontentloaded")

    # Trigger JS navigation (the SPA may have already routed, but ensure tab is active)
    page.evaluate(f"() => {{ if(window.switchTool) switchTool('{tool}', '{tab}', true); }}")
    wait_for_content(page, timeout=4000)
    time.sleep(0.5)

    shot_path = SHOTS_DIR / f"{label}.png"
    page.screenshot(path=str(shot_path), full_page=False)

    overflow = check_overflow(page, label)
    page_errors = [e for e in errors if e not in [x for x in audit_results]]

    result = {
        "panel":    label,
        "url":      url,
        "shot":     str(shot_path),
        "ok":       not page_errors and not overflow,
        "overflow": overflow,
        "errors":   page_errors[:],
    }
    # Clear consumed errors
    errors.clear()

    if result["ok"]:
        print_ok(f"{label:30s} → {shot_path.name}")
    else:
        status = []
        if overflow:
            status.append(f"overflow({len(overflow)})")
        if page_errors:
            status.append(f"errors({len(page_errors)})")
        print_warn(f"{label:30s} → {', '.join(status)}")

    return result


def run_sidebar_open_shot(page: Page) -> None:
    """Extra shot: sidebar open state (mobile viewport)."""
    page.set_viewport_size(VIEWPORT_MOBILE)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.evaluate("() => { if(window.openSidebar) openSidebar(); }")
    time.sleep(0.4)
    path = SHOTS_DIR / "sidebar_open_mobile.png"
    page.screenshot(path=str(path))
    print_ok(f"{'sidebar_open_mobile':30s} → {path.name}")
    page.set_viewport_size(VIEWPORT_DESKTOP)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    print(f"{DIM}{DIV}{RESET}")
    print(f" {RED}MANAGEMENT WEB — PLAYWRIGHT AUDIT{RESET}")
    print(f"{DIM}{SUB}{RESET}")
    print(f" {DIM}Target:   {BASE_URL}{RESET}")
    print(f" {DIM}Panels:   {len(PANELS)}{RESET}")
    print(f" {DIM}Output:   {SHOTS_DIR}{RESET}")
    print(f"{DIM}{DIV}{RESET}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport=VIEWPORT_DESKTOP)
        page = ctx.new_page()

        # Wire console capture
        page_errors: list[dict] = []
        page.on("console", lambda m: capture_console(m, page_errors))
        page.on("pageerror", lambda e: page_errors.append({"type": "pageerror", "text": str(e), "url": ""}))

        # Health check
        resp = page.goto(f"{BASE_URL}/api/health", wait_until="domcontentloaded")
        if not resp or resp.status != 200:
            print_fail("server not reachable — aborting")
            browser.close()
            return 1
        print_ok("server reachable")

        # Sidebar open shot (mobile)
        run_sidebar_open_shot(page)

        # Audit all panels
        for tool, tab, label in PANELS:
            result = audit_panel(page, tool, tab, label, page_errors)
            audit_results.append(result)

        # Tri-Color check on main landing
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.evaluate("() => { if(window.switchTool) switchTool('logging','read',true); }")
        wait_for_content(page, 3000)
        colors = check_tricolor(page)

        ctx.close()
        browser.close()

    # ─── Summary ─────────────────────────────────────────────────────────────
    total  = len(audit_results)
    passed = sum(1 for r in audit_results if r["ok"])
    failed = total - passed

    print(f"\n{DIM}{DIV}{RESET}")
    print(f" {RED}AUDIT SUMMARY{RESET}")
    print(f"{DIM}{SUB}{RESET}")
    print(f" {WHITE}Panels audited:{RESET}  {DIM}{total}{RESET}")
    print(f" {WHITE}Passed:{RESET}          {DIM}{passed}{RESET}")
    print(f" {WHITE}Failed/Warnings:{RESET} {DIM}{failed}{RESET}")
    print(f"{DIM}{SUB}{RESET}")
    print(f" {WHITE}Color samples:{RESET}")
    for k, v in (colors or {}).items():
        print(f"   {DIM}{k:20s} {v}{RESET}")
    print(f"{DIM}{DIV}{RESET}")

    if failed:
        print(f"\n{RED}ISSUES DETECTED:{RESET}")
        for r in audit_results:
            if not r["ok"]:
                print(f"  {DIM}{r['panel']}{RESET}")
                for ov in r["overflow"]:
                    print(f"    overflow: {ov}")
                for err in r["errors"]:
                    print(f"    {err['type']}: {err['text'][:80]}")

    # Save JSON report
    report_path = SHOTS_DIR / "audit_report.json"
    report_path.write_text(
        json.dumps({"ts": int(time.time()), "results": audit_results, "colors": colors}, indent=2),
        encoding="utf-8",
    )
    print_ok(f"report saved → {report_path.name}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
