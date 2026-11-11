#!/data/data/com.termux/files/usr/bin/env python3
"""
# Name:           blogger_tool.py
# Description:    Modular System Management Subtool for Google Blogger API v3, Content Publishing, Post Ingestion & Sync
# Version:        100
# Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# License:        PolyForm-Noncommercial-1.0.0
# RELATIONAL_ID:  blogger-subsystem-001
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_PATH: Path = Path(__file__).resolve()
SUITE_ROOT: Path = SCRIPT_PATH.parent.parent if SCRIPT_PATH.parent.name == "tools" else SCRIPT_PATH
LIB_DIR: Path = SUITE_ROOT / "lib"
CONFIG_DIR: Path = SUITE_ROOT / "config"
SECURE_ENV_FILE: Path = Path("/storage/emulated/0/.env/secure/secureenv_file.json")
DEFINITIONS_FILE: Path = Path("/storage/emulated/0/.env/user/definitions.json")
TOKEN_STORAGE_PATH: Path = Path(os.path.expanduser("~/.env/blogger_token.json"))

MD_TO_HTML_PY: Path = Path("/storage/emulated/0/Admin/System/tools/MD_To_HTML/MD_To_HTML.py")

if str(MD_TO_HTML_PY.parent) not in sys.path:
    sys.path.insert(0, str(MD_TO_HTML_PY.parent))

try:
    import MD_To_HTML
except ImportError:
    MD_To_HTML = None

# ANSI Tri-Color Palette Clamped to 49 Columns
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"
COLOR_ANSI_RED: str = "\033[1;31m"
COLOR_RESET: str = "\033[0m"
COLOR_WHITE: str = "\033[1;37m"
COLOR_NEUTRAL: str = "\033[0;37m"
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


def print_positive(message: str) -> None:
    print(f"{WHITE}[✓] {message.lower()}{RESET}")


def print_fail(message: str) -> None:
    print(f"{ACCENT}[✗] {message.upper()}{RESET}", file=sys.stderr)


def load_secure_env() -> Dict[str, str]:
    if not SECURE_ENV_FILE.exists():
        raise FileNotFoundError(f"Secure env not found: {SECURE_ENV_FILE}")
    with open(SECURE_ENV_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    fields = [f["name"] for f in data["Fields"]]
    name_idx = fields.index("var_name")
    val_idx = fields.index("var_value")
    return {row[name_idx]: row[val_idx] for row in data["Values"]}


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    token_url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data["access_token"]


def get_access_token() -> str:
    env_vars = load_secure_env()
    client_id = env_vars.get("BLOGGER_CLIENT_ID")
    client_secret = env_vars.get("BLOGGER_CLIENT_SECRET")
    refresh_token = env_vars.get("BLOGGER_REFRESH_TOKEN")

    if not refresh_token and TOKEN_STORAGE_PATH.exists():
        try:
            with open(TOKEN_STORAGE_PATH, "r", encoding="utf-8") as fh:
                refresh_token = json.load(fh).get("refresh_token")
        except Exception:
            pass

    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError("Missing Blogger credentials in secureenv_file.json")

    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    token_cache = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id
    }
    TOKEN_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_STORAGE_PATH, "w", encoding="utf-8") as fh:
        json.dump(token_cache, fh, indent=2)

    return access_token


def get_blog_metadata(blog_id: str, access_token: str) -> Dict[str, Any]:
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_posts(blog_id: str, access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?maxResults={max_results}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("items", [])


def publish_post(
    blog_id: str,
    access_token: str,
    title: str,
    content: str,
    labels: List[str],
    is_draft: bool = False
) -> Dict[str, Any]:
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?isDraft={'true' if is_draft else 'false'}"
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def delete_post(blog_id: str, access_token: str, post_id: str) -> bool:
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"}, method="DELETE")
    with urllib.request.urlopen(req, timeout=15):
        return True


def render_file_for_post(file_path: Path, use_style: bool = False, theme: str = "light") -> Tuple[str, str]:
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() in (".html", ".htm"):
        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
        return title, text

    if MD_To_HTML is None:
        raise RuntimeError(f"MD_To_HTML engine unavailable at {MD_TO_HTML_PY}")

    cfg = MD_To_HTML.load_config()
    fallback_title = file_path.stem.replace("_", " ").replace("-", " ").title()
    title = MD_To_HTML.extract_title(text, fallback_title)
    content_fragment = MD_To_HTML.convert_markdown(text)

    if use_style:
        template_str = MD_To_HTML.get_template("becss_styled")
        desc = MD_To_HTML.extract_description(text, cfg.get("default_description", "Document converted from Markdown."))
        html = (
            template_str
            .replace("{title}", MD_To_HTML._escape_html(title))
            .replace("{description}", MD_To_HTML._escape_html(desc))
            .replace("{content}", content_fragment)
            .replace("{theme}", theme)
            .replace("{date}", time.strftime("%Y-%m-%d"))
            .replace("{version}", MD_To_HTML.VERSION)
            .replace("{author_name}", cfg.get("author_name", "Elton Boehnen"))
            .replace("{author_email}", cfg.get("author_email", "eltonboehnen@gmail.com"))
            .replace("{author_site}", cfg.get("author_site", "https://boehnenelton2024.pages.dev"))
            .replace("{author_github}", cfg.get("author_github", "https://github.com/boehnenelton"))
        )
    else:
        template_str = MD_To_HTML.get_template("style_agnostic")
        html = template_str.replace("{title}", MD_To_HTML._escape_html(title)).replace("{content}", content_fragment)

    return title, html


def command_info() -> None:
    env_vars = load_secure_env()
    blog_id = env_vars.get("BLOGGER_BLOG_ID", "")
    token = get_access_token()
    meta = get_blog_metadata(blog_id, token)

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}GOOGLE BLOGGER SUBSYSTEM [MODE 7]{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    print(f" {ACCENT}Blog Name:{RESET}   {WHITE}{meta.get('name', 'N/A')}{RESET}")
    print(f" {ACCENT}Blog ID:{RESET}     {NEUTRAL}{meta.get('id')}{RESET}")
    print(f" {ACCENT}Blog URL:{RESET}    {meta.get('url')}")
    print(f" {ACCENT}Total Posts:{RESET} {WHITE}{meta.get('posts', {}).get('totalItems', 0)}{RESET}")
    print(f" {ACCENT}Total Pages:{RESET} {meta.get('pages', {}).get('totalItems', 0)}")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")


def command_posts(limit: int = 10) -> None:
    env_vars = load_secure_env()
    blog_id = env_vars.get("BLOGGER_BLOG_ID", "")
    token = get_access_token()
    posts = list_posts(blog_id, token, limit)

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}RECENT BLOGGER POSTS ({len(posts)}){RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    if not posts:
        print(f"  {DIM}(no posts found){RESET}")
        print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
        return

    for idx, post in enumerate(posts, 1):
        title = post.get("title", "(Untitled)")[:44]
        published = post.get("published", "")[:10]
        post_id = post.get("id", "")
        print(f"  {WHITE}[{idx:02d}]{RESET} {WHITE}{title}{RESET}")
        print(f"       {DIM}{published} · ID: {post_id}{RESET}")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")


def command_post(
    file_path_str: str,
    title_override: Optional[str] = None,
    labels: Optional[List[str]] = None,
    use_style: bool = False,
    theme: str = "light",
    is_draft: bool = False
) -> None:
    target_file = Path(file_path_str).resolve()
    if not target_file.exists():
        print_fail(f"FILE NOT FOUND: {target_file}")
        sys.exit(1)

    env_vars = load_secure_env()
    blog_id = env_vars.get("BLOGGER_BLOG_ID", "")
    token = get_access_token()

    doc_title, html_body = render_file_for_post(target_file, use_style=use_style, theme=theme)
    final_title = title_override or doc_title
    final_labels = labels if labels else ["BEJSON"]

    print(f"{WHITE}[*] Publishing '{final_title}' ({'Draft' if is_draft else 'Live'})...{RESET}")
    res = publish_post(blog_id, token, final_title, html_body, final_labels, is_draft=is_draft)
    print_positive(f"post published: {res.get('url', 'N/A')}")
    print(f"     {DIM}ID: {res.get('id')}{RESET}")


def command_delete(post_id: str) -> None:
    env_vars = load_secure_env()
    blog_id = env_vars.get("BLOGGER_BLOG_ID", "")
    token = get_access_token()
    delete_post(blog_id, token, post_id)
    print_positive(f"post {post_id} successfully deleted")


def print_help() -> None:
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}BLOGGER SUBSYSTEM CLI - AGENT GUIDE{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    print(f"{ACCENT}USAGE SYNTAX:{RESET}")
    print(f"  {NEUTRAL}python3 blogger_tool.py <command> [args]{RESET}")
    print()
    print(f"{ACCENT}COMMANDS:{RESET}")
    print(f"  • {ACCENT}info{RESET}          {NEUTRAL}Display blog status & metadata{RESET}")
    print(f"  • {ACCENT}posts [-n N]{RESET}  {NEUTRAL}List recent blog posts{RESET}")
    print(f"  • {ACCENT}publish <f>{RESET}   {NEUTRAL}Render & publish MD or HTML file{RESET}")
    print(f"  • {ACCENT}delete <id>{RESET}   {NEUTRAL}Delete a specific post by ID{RESET}")
    print()
    print(f"{ACCENT}PUBLISH OPTIONS:{RESET}")
    print(f"  • {ACCENT}--style{RESET}       {NEUTRAL}Apply BECSS Tri-Color styling{RESET}")
    print(f"  • {ACCENT}--theme T{RESET}     {NEUTRAL}Theme ('light' or 'dark'){RESET}")
    print(f"  • {ACCENT}--draft{RESET}       {NEUTRAL}Publish as draft{RESET}")
    print(f"  • {ACCENT}-t <title>{RESET}    {NEUTRAL}Override post title{RESET}")
    print(f"  • {ACCENT}-l <tag>{RESET}      {NEUTRAL}Add label/tag (multi allowed){RESET}")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return 0

    cmd = args[0].strip().lower()

    if cmd in ("info", "status"):
        command_info()
        return 0

    if cmd in ("posts", "list"):
        limit = 10
        if "-n" in args:
            idx = args.index("-n")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        elif "--limit" in args:
            idx = args.index("--limit")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        command_posts(limit)
        return 0

    if cmd in ("publish", "post"):
        parser = argparse.ArgumentParser(prog="blogger_tool publish")
        parser.add_argument("file", type=str)
        parser.add_argument("--title", "-t", type=str, default=None)
        parser.add_argument("--label", "-l", action="append", default=[])
        parser.add_argument("--style", action="store_true")
        parser.add_argument("--theme", choices=["light", "dark"], default="light")
        parser.add_argument("--draft", action="store_true")
        p_args = parser.parse_args(args[1:])
        command_post(
            p_args.file,
            title_override=p_args.title,
            labels=p_args.label,
            use_style=p_args.style,
            theme=p_args.theme,
            is_draft=p_args.draft
        )
        return 0

    if cmd in ("delete", "rm"):
        if len(args) < 2:
            print_fail("POST ID REQUIRED FOR DELETE")
            return 1
        command_delete(args[1])
        return 0

    print_fail(f"UNKNOWN COMMAND: {cmd}")
    print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
