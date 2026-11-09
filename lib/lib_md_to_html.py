#!/usr/bin/env python3
# =============================================================================
# Script:       MD_To_HTML.py
# Description:  Converts Markdown files to standardized HTML5.
#               Default output is style-agnostic semantic HTML wrapped in
#               <article class="bejson-cms-article"> with functional containment.
#               Use --style for standalone documents with BECSS Tri-Color styling.
# Version:      3.1.0
# Date Created: 2026-05-29
# Last Updated: 2026-11-02
# Author:       Elton Boehnen
# Email:        eltonboehnen@gmail.com
# Website:      https://boehnenelton2024.pages.dev
# GitHub:       https://github.com/boehnenelton
# RELATIONAL_ID: md-to-html-cli-001
# =============================================================================

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

VERSION: str = "1.6.0"
VERSION_INT: int = 310
PACKAGE_VERSION: int = 100


def get_script_path() -> Path:
    """Resolve script root directory reliably and portably."""
    return Path(__file__).resolve().parent


SCRIPT_PATH: Path = get_script_path()
CONFIG_FILE: Path = SCRIPT_PATH / "config" / "config.json"
TEMPLATES_DIR: Path = SCRIPT_PATH / "templates"


def load_config() -> dict:
    """Load configuration using O(1) field map caching."""
    if not CONFIG_FILE.exists():
        return {
            "output_folder_name": "MD_TO_HTML",
            "default_description": "Document converted from Markdown.",
            "default_theme": "light",
            "default_style_mode": "style_agnostic",
            "author_name": "Elton Boehnen",
            "author_email": "eltonboehnen@gmail.com",
            "author_site": "https://boehnenelton2024.pages.dev",
            "author_github": "https://github.com/boehnenelton",
        }

    try:
        raw_doc = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        field_names = [f["name"] for f in raw_doc.get("Fields", [])]
        field_map = {name: idx for idx, name in enumerate(field_names)}
        key_idx = field_map.get("setting_name", 0)
        val_idx = field_map.get("setting_value", 1)

        cfg = {}
        for row in raw_doc.get("Values", []):
            if len(row) > max(key_idx, val_idx):
                cfg[row[key_idx]] = row[val_idx]
        return cfg
    except Exception as err:
        sys.stderr.write(f"Warning: Failed to parse config.json: {err}\n")
        return {}


# =============================================================================
# MARKDOWN → HTML CONVERSION ENGINE
# =============================================================================

def _escape_html(text: str) -> str:
    """Escape characters that are special in HTML content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _slugify(text: str) -> str:
    """Generate clean URL anchor slugs from heading text."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


def _inline(text: str) -> str:
    """Convert inline Markdown elements while preserving code literals."""
    parts = []
    last = 0
    # Process inline code first to preserve raw code literals
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(_inline_spans(text[last:m.start()]))
        parts.append(f"<code>{_escape_html(m.group(1))}</code>")
        last = m.end()
    parts.append(_inline_spans(text[last:]))
    return "".join(parts)


def _inline_spans(text: str) -> str:
    """Handle bold, italic, strikethrough, links, and images."""
    # Images before links (images start with !)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{_escape_html(m.group(1))}" loading="lazy">',
        text,
    )
    # Links
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}">{_escape_html(m.group(1))}</a>',
        text,
    )
    # Bold + italic (***text*** or ___text___)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", text)
    # Bold (**text** or __text__)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic (*text* or _text_)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_([^_\s][^_]*)_(?!\w)", r"<em>\1</em>", text)
    # Strikethrough (~~text~~)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    return text


def _is_table_separator(line: str) -> bool:
    """Check if line is a Markdown table separator."""
    return bool(re.match(r"^\|?[\s\-:|]+[\|\-:]+[\s\-:|]*\|?$", line.strip()))


def _is_table_row(line: str) -> bool:
    """Check if line contains table delimiters."""
    return "|" in line


def _parse_table(lines: list) -> str:
    """Convert Markdown table lines into responsive HTML wrapped in .table-container."""
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return "<p>" + _inline(" ".join(lines)) + "</p>"

    html = [
        '<div class="table-container">',
        "<table>",
        "<thead>",
        "<tr>",
    ]
    for cell in rows[0]:
        html.append(f"  <th>{_inline(cell)}</th>")
    html += ["</tr>", "</thead>", "<tbody>"]

    # Skip separator row at index 1
    for row in rows[2:]:
        html.append("<tr>")
        for cell in row:
            html.append(f"  <td>{_inline(cell)}</td>")
        html.append("</tr>")
    html += ["</tbody>", "</table>", "</div>"]
    return "\n".join(html)


def sanitize_html(html_str: str) -> str:
    """Sanitize output by removing MS Word/Office XML tags and attributes."""
    # Strip <o:p> tags
    html_str = re.sub(r"</?o:p[^>]*>", "", html_str, flags=re.IGNORECASE)
    # Strip mso-* styles
    html_str = re.sub(r'style="[^"]*mso-[^"]*"', "", html_str, flags=re.IGNORECASE)
    return html_str


def convert_markdown(md_text: str) -> str:
    """
    Convert full Markdown document to an HTML fragment.
    Guarantees:
    - Fenced code blocks are never wrapped in paragraph tags.
    - Code content is HTML-escaped and carries class="language-{lang}".
    - Tables are wrapped in <div class="table-container">.
    - Headings carry id slugs.
    - Alerts/callouts map to styled callout blockquotes.
    - Task lists map to checkbox items.
    """
    lines = md_text.splitlines()
    output = []
    i = 0

    def flush_paragraph(buf: list):
        if buf:
            content = _inline(" ".join(buf))
            output.append(f"<p>{content}</p>")
            buf.clear()

    para_buf = []

    while i < len(lines):
        line = lines[i]

        # --- Fenced code block (``` or ~~~) with optional leading whitespace ---
        fence_match = re.match(r"^\s*(`{3,}|~{3,})\s*([^\s`~]*)", line)
        if fence_match:
            flush_paragraph(para_buf)
            fence_char = fence_match.group(1)
            lang = fence_match.group(2).strip().lower()
            lang_attr = f' class="language-{_escape_html(lang)}"' if lang else ""
            code_lines = []
            i += 1
            while i < len(lines):
                # Check for closing fence
                if re.match(rf"^\s*{re.escape(fence_char[:3])}+\s*$", lines[i]):
                    break
                code_lines.append(_escape_html(lines[i]))
                i += 1
            joined_code = "\n".join(code_lines)
            output.append(f"<pre><code{lang_attr}>{joined_code}</code></pre>")
            i += 1
            continue

        # --- Horizontal rule ---
        if re.match(r"^(\*{3,}|-{3,}|_{3,})\s*$", line.strip()):
            flush_paragraph(para_buf)
            output.append("<hr>")
            i += 1
            continue

        # --- ATX Headings (# through ######) ---
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            flush_paragraph(para_buf)
            level = len(heading_match.group(1))
            heading_raw = heading_match.group(2).strip()
            slug = _slugify(heading_raw)
            text = _inline(heading_raw)
            output.append(f'<h{level} id="{slug}">{text}</h{level}>')
            i += 1
            continue

        # --- GitHub-style Callouts / Alerts (> [!NOTE]) ---
        callout_match = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)", line, flags=re.IGNORECASE)
        if callout_match:
            flush_paragraph(para_buf)
            kind = callout_match.group(1).lower()
            extra = callout_match.group(2).strip()
            bq_lines = []
            if extra:
                bq_lines.append(extra)
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                clean_line = lines[i].lstrip("> ").rstrip()
                if clean_line:
                    bq_lines.append(clean_line)
                i += 1
            inner_content = _inline(" ".join(bq_lines)) if bq_lines else ""
            output.append(
                f'<blockquote class="callout callout-{kind}"><p><strong>{kind.title()}:</strong> {inner_content}</p></blockquote>'
            )
            continue

        # --- Standard Blockquote ---
        if line.startswith(">"):
            flush_paragraph(para_buf)
            bq_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                bq_lines.append(lines[i].lstrip("> ").rstrip())
                i += 1
            inner = convert_markdown("\n".join(bq_lines))
            output.append(f"<blockquote>\n{inner}\n</blockquote>")
            continue

        # --- Task list (- [ ] or - [x]) ---
        task_match = re.match(r"^\s*[\*\-\+]\s+\[([ xX])\]\s+(.*)", line)
        if task_match:
            flush_paragraph(para_buf)
            output.append('<ul class="task-list">')
            while i < len(lines):
                tm = re.match(r"^\s*[\*\-\+]\s+\[([ xX])\]\s+(.*)", lines[i])
                if not tm:
                    break
                checked = ' checked="checked"' if tm.group(1).lower() == "x" else ""
                item_text = _inline(tm.group(2).strip())
                output.append(
                    f'<li class="task-item"><input type="checkbox" disabled{checked}> <span>{item_text}</span></li>'
                )
                i += 1
            output.append("</ul>")
            continue

        # --- Standard Unordered list ---
        if re.match(r"^\s*[\*\-\+]\s+(.*)", line):
            flush_paragraph(para_buf)
            output.append("<ul>")
            while i < len(lines) and re.match(r"^\s*[\*\-\+]\s+(.*)", lines[i]):
                # Make sure it is not a task list
                if re.match(r"^\s*[\*\-\+]\s+\[([ xX])\]\s+", lines[i]):
                    break
                m = re.match(r"^\s*[\*\-\+]\s+(.*)", lines[i])
                item_text = _inline(m.group(1).strip())
                output.append(f"<li>{item_text}</li>")
                i += 1
            output.append("</ul>")
            continue

        # --- Ordered list ---
        if re.match(r"^\s*\d+\.\s+(.*)", line):
            flush_paragraph(para_buf)
            output.append("<ol>")
            while i < len(lines) and re.match(r"^\s*\d+\.\s+(.*)", lines[i]):
                m = re.match(r"^\s*\d+\.\s+(.*)", lines[i])
                item_text = _inline(m.group(1).strip())
                output.append(f"<li>{item_text}</li>")
                i += 1
            output.append("</ol>")
            continue

        # --- Table (detect header row + separator row) ---
        if (
            _is_table_row(line)
            and i + 1 < len(lines)
            and _is_table_separator(lines[i + 1])
        ):
            flush_paragraph(para_buf)
            table_lines = []
            while i < len(lines) and _is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            output.append(_parse_table(table_lines))
            continue

        # --- Blank line: flush buffer ---
        if line.strip() == "":
            flush_paragraph(para_buf)
            i += 1
            continue

        # --- Normal paragraph text ---
        para_buf.append(line.strip())
        i += 1

    flush_paragraph(para_buf)
    result = "\n".join(output)
    return sanitize_html(result)


def extract_title(md_text: str, fallback: str) -> str:
    """Pull first H1 heading from Markdown text, otherwise use fallback."""
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.*)", line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def extract_description(md_text: str, default: str) -> str:
    """Extract clean SEO description snippet from first paragraph."""
    for line in md_text.splitlines():
        line = line.strip()
        if (
            line
            and not line.startswith("#")
            and not line.startswith("|")
            and not line.startswith(">")
            and not line.startswith("`")
            and not line.startswith("-")
            and not line.startswith("*")
        ):
            plain = re.sub(r"\*{1,3}|_{1,3}|~~|`", "", line)
            plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", plain).strip()
            if plain:
                return (plain[:152] + "...") if len(plain) > 155 else plain
    return default


def get_template(name: str) -> str:
    """Retrieve template from disk or fallback to built-in default."""
    target_file = TEMPLATES_DIR / f"{name}.html"
    if target_file.exists():
        return target_file.read_text(encoding="utf-8")

    # Hardened fallbacks in case templates/ is relocated
    if name == "style_agnostic":
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 1.5rem; }
    .bejson-cms-article { width: 100%; max-width: 900px; margin: 0 auto; }
    img { max-width: 100% !important; height: auto !important; display: block; }
    pre, code, table, div { max-width: 100% !important; overflow-x: auto; }
    .table-container { width: 100%; max-width: 100%; overflow-x: auto; margin: 1.5rem 0; }
    table { width: 100%; border-collapse: collapse; min-width: 600px; }
  </style>
</head>
<body>
<article class="bejson-cms-article">
{content}
</article>
</body>
</html>"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body>
<article class="bejson-cms-article">
{content}
</article>
</body>
</html>"""


def convert_file(
    md_path: Path,
    output_dir: Path,
    use_style: bool,
    theme: str,
    cfg: dict,
) -> Path:
    """Convert a single Markdown file to HTML atomically."""
    md_text = md_path.read_text(encoding="utf-8")
    content_html = convert_markdown(md_text)

    fallback_title = md_path.stem.replace("_", " ").replace("-", " ").title()
    title = extract_title(md_text, fallback_title)
    output_path = output_dir / f"{md_path.stem}.html"

    if use_style:
        template_str = get_template("becss_styled")
        desc = extract_description(md_text, cfg.get("default_description", "Document converted from Markdown."))
        html = (
            template_str
            .replace("{title}", _escape_html(title))
            .replace("{description}", _escape_html(desc))
            .replace("{content}", content_html)
            .replace("{theme}", theme)
            .replace("{date}", date.today().isoformat())
            .replace("{version}", VERSION)
            .replace("{author_name}", cfg.get("author_name", "Elton Boehnen"))
            .replace("{author_email}", cfg.get("author_email", "eltonboehnen@gmail.com"))
            .replace("{author_site}", cfg.get("author_site", "https://boehnenelton2024.pages.dev"))
            .replace("{author_github}", cfg.get("author_github", "https://github.com/boehnenelton"))
        )
    else:
        template_str = get_template("style_agnostic")
        html = (
            template_str
            .replace("{title}", _escape_html(title))
            .replace("{content}", content_html)
        )

    # Atomic write to temporary file before replacing
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_file = output_path.with_suffix(".tmp")
    temp_file.write_text(html, encoding="utf-8")
    os.replace(temp_file, output_path)

    mode_label = f"[styled:{theme}]" if use_style else "[style-agnostic]"
    print(f"  {mode_label:<18} {md_path.name} → {output_path.name}")
    return output_path


def process_target(
    target_str: str,
    use_style: bool = False,
    theme_override: str = None,
    output_dir_override: str = None,
):
    """Process file or directory target."""
    target = Path(target_str).resolve()
    cfg = load_config()

    theme = theme_override or cfg.get("default_theme", "light")
    folder_name = cfg.get("output_folder_name", "MD_TO_HTML")

    if target.is_file():
        if target.suffix.lower() != ".md":
            sys.stderr.write(f"Error: '{target.name}' is not a Markdown file (.md required).\n")
            sys.exit(1)
        output_dir = Path(output_dir_override).resolve() if output_dir_override else (target.parent / folder_name)
        print(f"Target: {target}")
        print(f"Output: {output_dir}")
        convert_file(target, output_dir, use_style, theme, cfg)

    elif target.is_dir():
        output_dir = Path(output_dir_override).resolve() if output_dir_override else (target / folder_name)
        md_files = sorted(target.glob("*.md"))
        if not md_files:
            print(f"No .md files found in target directory: {target}")
            sys.exit(0)
        print(f"Target: {target}")
        print(f"Output: {output_dir}")
        print(f"Files:  {len(md_files)} Markdown file(s) discovered\n")
        for f in md_files:
            convert_file(f, output_dir, use_style, theme, cfg)

    else:
        sys.stderr.write(f"Error: '{target_str}' is neither an existing file nor a directory.\n")
        sys.exit(1)

    print(f"\nDone. Converted output saved in: {output_dir}")


def register_project() -> int:
    """Register tool with Project Chunker if available."""
    internal_storage = os.environ.get("INTERNAL_STORAGE", "/storage/emulated/0")
    chunker_cli = Path(internal_storage) / "Admin" / "System" / "Project_Chunker" / "CLI" / "project_chunker.py"
    if chunker_cli.exists():
        print(f"Registering MD_To_HTML with Project Chunker at: {chunker_cli}")
        cmd = [sys.executable, str(chunker_cli), "--track", str(SCRIPT_PATH)]
        return subprocess.call(cmd)
    print("Project Chunker not found; skipping registration.")
    return 0


def cmd_about():
    """Display program details, authorship, and operational instructions."""
    print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║  MD_To_HTML — Markdown to Standardized HTML5 Converter                     ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Version:  {VERSION:<63}║
║  Package:  PKG{PACKAGE_VERSION:<60}║
║  Date:     2026-11-02                                                      ║
╠════════════════════════════════════════════════════════════════════════════╣
║  Author:   Elton Boehnen                                                   ║
║  Email:    eltonboehnen@gmail.com                                          ║
║  Site:     https://boehnenelton2024.pages.dev                              ║
║  GitHub:   https://github.com/boehnenelton                                 ║
╚════════════════════════════════════════════════════════════════════════════╝

Converts Markdown documentation into standardized HTML5 with responsive containment.

Operational Modes:
  Default:  Style-agnostic semantic HTML wrapped in <article class="bejson-cms-article">
            with zero hardcoded styling, responsive table wrapping (.table-container),
            fenced code blocks (<pre><code class="language-*">), and callout blockquotes.
  --style:  Full standalone HTML5 page with embedded BECSS Tri-Color (#DE2626) styling,
            typography (Inter + Roboto Mono), SEO meta, and author attribution footer.
            Supports --theme light and --theme dark.
""")


def cmd_config():
    """Display active BEJSON 104a configuration."""
    cfg = load_config()
    print("Current MD_To_HTML Configuration (BEJSON 104a):")
    for k, v in cfg.items():
        print(f"  {k:<24} : {v}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="MD_To_HTML",
        description="Convert Markdown files to standardized HTML5 for offline viewing and BEJSON CMS ingestion.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Path to a .md file or directory containing .md files.",
    )
    parser.add_argument(
        "--style",
        action="store_true",
        help="Enable full standalone styled HTML template with BECSS Tri-Color styling.",
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="light",
        help="Select visual theme for --style output (default: light).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Override output directory path (default: MD_TO_HTML folder inside target).",
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Display tool overview, authorship, and architecture info.",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Display active BEJSON 104a configuration.",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register MD_To_HTML with Project Chunker.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"MD_To_HTML v{VERSION} (PKG{PACKAGE_VERSION})",
    )

    args = parser.parse_args()

    if args.about:
        cmd_about()
        return 0

    if args.config:
        cmd_config()
        return 0

    if args.register:
        return register_project()

    if not args.target:
        parser.print_help()
        return 1

    process_target(
        args.target,
        use_style=args.style,
        theme_override=args.theme,
        output_dir_override=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
