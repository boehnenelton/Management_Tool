#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : environment_tool.py
Rel. Path   : tools/environment_tool/environment_tool.py
Family      : System Management / Environment & Definitions
Purpose     : Authoritative BEJSON 104a Environment & Definitions Management Engine.
              Safely queries, mutates, audits, exports, and creates environment files:
                - Public Definitions: /storage/emulated/0/.env/user/definitions.json
                - Secure Environment: /storage/emulated/0/.env/secure/secureenv_file.json
                - Custom Stores: created from canonical schema templates in .env folders
              Enforces O(1) field map caching, physical path existence validation,
              atomic POSIX replacement with PID locks, and 49-column mobile portrait formatting.
Version     : 10200
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-11
RELATIONAL_ID : e9f2a1b4-7832-4d51-9e20-5c6e83d91b42
License     : PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Dynamic Path & Suite Resolution (Policy §4.1 & §4.5) ─────────────────────
def get_script_path() -> Path:
    return Path(__file__).resolve().parent

SCRIPT_PATH: Path = get_script_path()
SUITE_ROOT: Path = SCRIPT_PATH.parent.parent if SCRIPT_PATH.parent.name == "tools" else SCRIPT_PATH
LIB_DIR: Path = SUITE_ROOT / "lib"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# Canonical Environment Stores & Directories
ENV_USER_DIR: Path = Path("/storage/emulated/0/.env/user")
ENV_SECURE_DIR: Path = Path("/storage/emulated/0/.env/secure")
DEFINITIONS_STORE_PATH: Path = ENV_USER_DIR / "definitions.json"
SECUREENV_STORE_PATH: Path = ENV_SECURE_DIR / "secureenv_file.json"

# Canonical BEJSON 104a Schema Templates
TEMPLATE_DEFINITIONS: Dict[str, Any] = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "Schema_Name": "UserPaths",
    "Records_Type": ["EnvironmentVariable"],
    "Fields": [
        {"name": "var_name", "type": "string", "description": "The name of the environment variable"},
        {"name": "var_value", "type": "string", "description": "The literal value of the variable"},
        {"name": "var_type", "type": "string", "description": "The data type: string, int, boolean, or secret"},
        {"name": "Type", "type": "string", "description": "Variable classification: Path, URL, Flag, or String"},
        {"name": "Flag", "type": "string", "description": "Optional environment flag tag"},
        {"name": "Description", "type": "string", "description": "Human-readable description of variable"}
    ],
    "Values": []
}

TEMPLATE_SECUREENV: Dict[str, Any] = {
    "Format": "BEJSON",
    "Format_Version": "104a",
    "Format_Creator": "Elton Boehnen",
    "Schema_Name": "SecureEnv",
    "Records_Type": ["SecureEnvironmentVariable"],
    "Fields": [
        {"name": "var_name", "type": "string", "description": "The name of the environment variable"},
        {"name": "var_value", "type": "string", "description": "The literal value of the variable"},
        {"name": "var_type", "type": "string", "description": "The data type: string, int, boolean, or secret"}
    ],
    "Values": []
}

# Import Canonical BEJSON Core Primitives
try:
    import lib_bejson_Core_bejson_core as bejson_core
    import lib_bejson_Core_bejson_validator as bejson_validator
except ImportError:
    bejson_core = None
    bejson_validator = None

# ── Policy §8.1 Tri-Color Palette & 49-Column Geometry ──────────────────────
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

logger = logging.getLogger("environment_tool")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def print_positive(message: str) -> None:
    print(f"{WHITE}[✓] {message.lower()}{RESET}")


def print_fail(message: str) -> None:
    print(f"{ACCENT}[✗] {message.upper()}{RESET}", file=sys.stderr)


# ── Store Path Resolution ───────────────────────────────────────────────────
def resolve_target_store(file_arg: Optional[str] = None, is_secure: bool = False, custom_dir: Optional[str] = None) -> Path:
    """Resolves target store path based on flags, filename, or directory."""
    if file_arg:
        arg_path = Path(file_arg)
        if arg_path.is_absolute() and arg_path.exists():
            return arg_path
        # Look in custom_dir or canonical .env folder
        base_folder = Path(custom_dir) if custom_dir else (ENV_SECURE_DIR if is_secure else ENV_USER_DIR)
        candidate = base_folder / file_arg
        if not candidate.suffix:
            candidate = candidate.with_suffix(".json")
        return candidate

    if is_secure:
        return SECUREENV_STORE_PATH
    return DEFINITIONS_STORE_PATH


# ── Core BEJSON Document Handling ───────────────────────────────────────────
def load_store(target_file_path: Path) -> Dict[str, Any]:
    """Loads a BEJSON document using core library or strict fallback."""
    if not target_file_path.exists():
        raise FileNotFoundError(f"Store not found: {target_file_path}")
    if bejson_core and hasattr(bejson_core, "bejson_core_load_file"):
        return bejson_core.bejson_core_load_file(target_file_path)
    with open(target_file_path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def get_field_map(document: Dict[str, Any]) -> Dict[str, int]:
    """Retrieves O(1) field map cache per Policy §6.2."""
    if bejson_core and hasattr(bejson_core, "bejson_core_get_field_map"):
        return bejson_core.bejson_core_get_field_map(document)
    fields = document.get("Fields", [])
    return {field["name"]: index for index, field in enumerate(fields)}


def save_store_atomic(target_file_path: Path, document: Dict[str, Any]) -> None:
    """Atomically commits BEJSON document with lock and backup."""
    if bejson_core and hasattr(bejson_core, "bejson_core_atomic_write"):
        bejson_core.bejson_core_atomic_write(target_file_path, document)
        return

    target_dir = target_file_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_file = target_file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temp_file.replace(target_file_path)


def mask_secret(value: str) -> str:
    """Masks sensitive values for safe mobile display."""
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}...{value[-4:]}"


# ── Action Handlers ──────────────────────────────────────────────────────────
def action_create_file(args: argparse.Namespace) -> int:
    """Creates a new BEJSON environment file from authoritative template in .env folder."""
    filename = args.filename.strip()
    if not (filename.endswith(".json") or filename.endswith(".bejson")):
        filename += ".json"

    base_dir = Path(args.path) if args.path else (ENV_SECURE_DIR if args.secure else ENV_USER_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    target_file = base_dir / filename

    if target_file.exists() and not args.force:
        print_fail(f"FILE ALREADY EXISTS: {target_file}. USE --force TO OVERWRITE.")
        return 10

    # Select canonical template
    template_data = dict(TEMPLATE_SECUREENV if args.secure else TEMPLATE_DEFINITIONS)
    # Deep copy Fields list
    template_data["Fields"] = [dict(f) for f in template_data["Fields"]]
    template_data["Values"] = []
    if args.name:
        template_data["Schema_Name"] = args.name

    try:
        save_store_atomic(target_file, template_data)
        mode_label = "secure environment" if args.secure else "definitions"
        print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
        print(f" {ACCENT}CREATED NEW ENVIRONMENT FILE{RESET}")
        print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
        print(f" {ACCENT}Type:{RESET}     {WHITE}{mode_label}{RESET}")
        print(f" {ACCENT}Location:{RESET} {NEUTRAL}{str(target_file)[:37]}{RESET}")
        print(f" {ACCENT}Schema:{RESET}   {NEUTRAL}{template_data['Schema_Name']}{RESET}")
        print(f" {ACCENT}Fields:{RESET}   {WHITE}{len(template_data['Fields'])} canonical fields{RESET}")
        print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
        print_positive(f"new environment file created successfully from template")
        return 0
    except Exception as err:
        print_fail(f"FAILED TO CREATE FILE: {err}")
        return 30


def action_list_files(args: argparse.Namespace) -> int:
    """Lists all environment stores in .env directories."""
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}REGISTERED ENVIRONMENT STORES{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")

    folders = [("USER DEFINITIONS", ENV_USER_DIR), ("SECURE ENVIRONMENT", ENV_SECURE_DIR)]
    total_found = 0

    for label, folder in folders:
        print(f" {ACCENT}[{label}]{RESET}")
        if not folder.exists():
            print(f"   {DIM}(directory missing){RESET}")
            continue

        store_files = sorted(folder.glob("*.json")) + sorted(folder.glob("*.bejson"))
        # Exclude temporary or backup files
        store_files = [f for f in store_files if not f.name.endswith(".bak") and not f.name.endswith(".tmp")]

        if not store_files:
            print(f"   {DIM}(no json/bejson stores found){RESET}")
            continue

        for sf in store_files:
            total_found += 1
            size_kb = sf.stat().st_size / 1024
            rec_count = "?"
            try:
                d = load_store(sf)
                rec_count = str(len(d.get("Values", [])))
            except Exception:
                pass
            print(f"  • {WHITE}{sf.name:<24}{RESET} {NEUTRAL}{rec_count:>3} vars {size_kb:>5.1f}k{RESET}")
        print()

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print_positive(f"discovered {total_found} active environment store(s)")
    return 0


def action_list(args: argparse.Namespace) -> int:
    """Lists environment variables with filtering and 49-column clamping."""
    target_path = resolve_target_store(args.file, args.secure, args.path)
    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap.get("var_name", 0)
    val_idx = fmap.get("var_value", 1)
    type_idx = fmap.get("Type") or fmap.get("var_type", 2)
    flag_idx = fmap.get("Flag")

    rows = doc.get("Values", [])
    filtered_rows = []

    for row in rows:
        var_name = str(row[name_idx])
        var_type = str(row[type_idx]) if type_idx < len(row) else "string"
        var_flag = str(row[flag_idx]) if flag_idx is not None and flag_idx < len(row) else ""

        if args.type and args.type.lower() != var_type.lower():
            continue
        if args.flag and args.flag.lower() != var_flag.lower():
            continue
        if args.query and args.query.lower() not in var_name.lower():
            continue
        filtered_rows.append(row)

    if args.json:
        output_payload = [
            {
                "var_name": r[name_idx],
                "var_value": mask_secret(str(r[val_idx])) if args.secure and not args.reveal else str(r[val_idx]),
                "type": r[type_idx] if type_idx < len(r) else "string",
            }
            for r in filtered_rows
        ]
        print(json.dumps(output_payload, indent=2))
        return 0

    store_label = target_path.name.upper()
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}{store_label} ({len(filtered_rows)} VARS){RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")

    for row in filtered_rows:
        var_name = str(row[name_idx])
        raw_val = str(row[val_idx])
        var_type = str(row[type_idx]) if type_idx < len(row) else "string"
        display_val = mask_secret(raw_val) if args.secure and not args.reveal else raw_val

        # 49-column discipline
        display_line = f" {ACCENT}•{RESET} {WHITE}{var_name}{RESET} ({DIM}{var_type}{RESET})"
        print(display_line[:49])
        val_line = f"   {NEUTRAL}{display_val}{RESET}"
        print(val_line[:49])

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    return 0


def action_get(args: argparse.Namespace) -> int:
    """Retrieves metadata for a specific variable."""
    var_name_target = args.var_name.strip()
    target_path = resolve_target_store(args.file, args.secure, args.path)

    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap.get("var_name", 0)

    for row in doc.get("Values", []):
        if str(row[name_idx]).lower() == var_name_target.lower():
            if args.json:
                data_record = {field["name"]: row[fmap[field["name"]]] for field in doc.get("Fields", [])}
                if args.secure and not args.reveal:
                    data_record["var_value"] = mask_secret(str(data_record.get("var_value", "")))
                print(json.dumps(data_record, indent=2))
                return 0

            print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
            print(f" {ACCENT}VARIABLE: {WHITE}{row[name_idx]}{RESET}")
            print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
            for field in doc.get("Fields", []):
                fname = field["name"]
                fval = str(row[fmap[fname]])
                if fname == "var_value" and args.secure and not args.reveal:
                    fval = mask_secret(fval)
                print(f" {ACCENT}{fname:<14}:{RESET} {NEUTRAL}{fval[:32]}{RESET}")
            print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
            return 0

    print_fail(f"VARIABLE '{var_name_target}' NOT FOUND IN STORE.")
    return 20


def action_set(args: argparse.Namespace) -> int:
    """Inserts or updates an environment variable with validation."""
    var_name = args.var_name.strip()
    var_val = args.var_value.strip()
    var_type = args.type.strip()
    var_flag = args.flag.strip() if args.flag else ""
    var_desc = args.desc.strip() if args.desc else ""

    # Path integrity verification per Policy §4.5
    if var_type.lower() == "path":
        resolved_path = Path(var_val).resolve()
        if not resolved_path.exists():
            print_fail(f"PATH VERIFICATION FAILED: '{var_val}' DOES NOT EXIST ON DISK.")
            return 10

    target_path = resolve_target_store(args.file, args.secure, args.path)
    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap["var_name"]
    val_idx = fmap["var_value"]
    type_idx = fmap.get("Type") or fmap.get("var_type")

    updated = False
    for row in doc.get("Values", []):
        if str(row[name_idx]).lower() == var_name.lower():
            row[val_idx] = var_val
            if type_idx is not None and type_idx < len(row):
                row[type_idx] = var_type
            if "Flag" in fmap and fmap["Flag"] < len(row) and var_flag:
                row[fmap["Flag"]] = var_flag
            if "Description" in fmap and fmap["Description"] < len(row) and var_desc:
                row[fmap["Description"]] = var_desc
            updated = True
            break

    if not updated:
        new_row = [None] * len(doc.get("Fields", []))
        new_row[name_idx] = var_name
        new_row[val_idx] = var_val
        if type_idx is not None:
            new_row[type_idx] = var_type
        if "var_type" in fmap and fmap["var_type"] != type_idx:
            new_row[fmap["var_type"]] = "secret" if args.secure else "string"
        if "Flag" in fmap:
            new_row[fmap["Flag"]] = var_flag
        if "Description" in fmap:
            new_row[fmap["Description"]] = var_desc
        doc["Values"].append(new_row)

    try:
        save_store_atomic(target_path, doc)
        action_verb = "updated" if updated else "created"
        print_positive(f"variable {var_name} successfully {action_verb} in {target_path.name}")
        return 0
    except Exception as err:
        print_fail(f"FAILED TO SAVE STORE: {err}")
        return 30


def action_unset(args: argparse.Namespace) -> int:
    """Removes a variable from the store."""
    var_name = args.var_name.strip()
    target_path = resolve_target_store(args.file, args.secure, args.path)

    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap["var_name"]
    original_count = len(doc.get("Values", []))

    doc["Values"] = [r for r in doc.get("Values", []) if str(r[name_idx]).lower() != var_name.lower()]

    if len(doc["Values"]) == original_count:
        print_fail(f"VARIABLE '{var_name}' NOT FOUND IN {target_path.name}.")
        return 20

    try:
        save_store_atomic(target_path, doc)
        print_positive(f"variable {var_name} removed from {target_path.name}")
        return 0
    except Exception as err:
        print_fail(f"FAILED TO SAVE STORE: {err}")
        return 30


def action_audit(args: argparse.Namespace) -> int:
    """Audits all Path entries in definitions.json for existence."""
    target_path = resolve_target_store(args.file, args.secure, args.path)
    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap["var_name"]
    val_idx = fmap["var_value"]
    type_idx = fmap.get("Type") or fmap.get("var_type", 2)

    total_paths = 0
    missing_paths = []

    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    print(f" {ACCENT}AUDITING CANONICAL PATH DEFINITIONS{RESET}")
    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")

    for row in doc.get("Values", []):
        var_type = str(row[type_idx]) if type_idx < len(row) else ""
        if var_type.lower() == "path":
            total_paths += 1
            var_name = str(row[name_idx])
            var_val = str(row[val_idx])
            path_obj = Path(var_val)
            if not path_obj.exists():
                missing_paths.append((var_name, var_val))
                print(f" {ACCENT}[✗] MISSING:{RESET} {WHITE}{var_name}{RESET}")
                print(f"     {NEUTRAL}{var_val[:43]}{RESET}")
            elif args.verbose:
                print(f" {WHITE}[✓]{RESET} {var_name[:40]}")

    print(f"{NEUTRAL}{SUBDIVIDER_49}{RESET}")
    if missing_paths:
        print_fail(f"AUDIT FAILED: {len(missing_paths)}/{total_paths} PATHS MISSING ON DISK.")
        return 1
    print_positive(f"all {total_paths} canonical path definitions verified on disk")
    print(f"{NEUTRAL}{DIVIDER_49}{RESET}")
    return 0


def action_export(args: argparse.Namespace) -> int:
    """Exports definitions as bash shell exports."""
    target_path = resolve_target_store(args.file, args.secure, args.path)
    try:
        doc = load_store(target_path)
    except Exception as err:
        print_fail(f"FAILED TO LOAD STORE: {err}")
        return 10

    fmap = get_field_map(doc)
    name_idx = fmap["var_name"]
    val_idx = fmap["var_value"]

    for row in doc.get("Values", []):
        vname = str(row[name_idx])
        vval = str(row[val_idx]).replace('"', '\\"')
        print(f'export {vname}="{vval}"')
    return 0


# ── CLI Router & Parser ──────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="environment_tool.py",
        description="Unified Environment & Definitions Manager (Policy §4.5)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Operational Subcommands")

    # create-file
    p_create = subparsers.add_parser("create-file", help="Create new environment file from template in .env folder")
    p_create.add_argument("filename", help="File name (e.g. project_env.json)")
    p_create.add_argument("--secure", action="store_true", help="Use SecureEnv template and save to secure/ folder")
    p_create.add_argument("--path", help="Override destination directory (default: same folder as definitions)")
    p_create.add_argument("--name", help="Custom Schema_Name")
    p_create.add_argument("--force", action="store_true", help="Overwrite if file exists")

    # list-files
    subparsers.add_parser("list-files", help="List all environment stores in .env directories")

    # list
    p_list = subparsers.add_parser("list", help="List environment variables")
    p_list.add_argument("-t", "--type", help="Filter by variable type (Path, string, secret)")
    p_list.add_argument("-f", "--flag", help="Filter by flag (AI_PLUS, AI_PRO)")
    p_list.add_argument("-q", "--query", help="Filter by substring")
    p_list.add_argument("--file", help="Specific env filename or path")
    p_list.add_argument("--path", help="Specific directory for file")
    p_list.add_argument("--secure", action="store_true", help="Query secureenv instead of definitions")
    p_list.add_argument("--reveal", action="store_true", help="Reveal unmasked secret values")
    p_list.add_argument("--json", action="store_true", help="Output raw JSON array")

    # get
    p_get = subparsers.add_parser("get", help="Get variable metadata")
    p_get.add_argument("var_name", help="Name of the environment variable")
    p_get.add_argument("--file", help="Specific env filename or path")
    p_get.add_argument("--path", help="Specific directory for file")
    p_get.add_argument("--secure", action="store_true", help="Query secureenv instead of definitions")
    p_get.add_argument("--reveal", action="store_true", help="Reveal unmasked secret value")
    p_get.add_argument("--json", action="store_true", help="Output raw JSON")

    # set
    p_set = subparsers.add_parser("set", help="Insert or update an environment variable")
    p_set.add_argument("var_name", help="Name of the environment variable")
    p_set.add_argument("var_value", help="Literal value of the variable")
    p_set.add_argument("-t", "--type", default="string", help="Type (Path, string, secret, boolean, integer)")
    p_set.add_argument("-f", "--flag", default="", help="Flag tag (e.g. AI_PLUS, AI_PRO)")
    p_set.add_argument("-d", "--desc", default="", help="Human-readable description")
    p_set.add_argument("--file", help="Specific env filename or path")
    p_set.add_argument("--path", help="Specific directory for file")
    p_set.add_argument("--secure", action="store_true", help="Write to secureenv instead of definitions")

    # unset
    p_unset = subparsers.add_parser("unset", help="Delete a variable from the store")
    p_unset.add_argument("var_name", help="Name of the variable to delete")
    p_unset.add_argument("--file", help="Specific env filename or path")
    p_unset.add_argument("--path", help="Specific directory for file")
    p_unset.add_argument("--secure", action="store_true", help="Delete from secureenv instead of definitions")

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit all Path definitions on physical disk")
    p_audit.add_argument("--file", help="Specific env filename or path")
    p_audit.add_argument("--path", help="Specific directory for file")
    p_audit.add_argument("--secure", action="store_true", help="Audit paths in secure store")
    p_audit.add_argument("-v", "--verbose", action="store_true", help="Show all verified paths")

    # export
    p_export = subparsers.add_parser("export", help="Output bash export statements")
    p_export.add_argument("--file", help="Specific env filename or path")
    p_export.add_argument("--path", help="Specific directory for file")
    p_export.add_argument("--secure", action="store_true", help="Export secureenv instead of definitions")

    return parser


def main() -> int:
    parser = build_parser()
    if len(sys.argv) == 1:
        args = parser.parse_args(["list"])
        return action_list(args)

    args = parser.parse_args()
    if args.command == "create-file":
        return action_create_file(args)
    if args.command == "list-files":
        return action_list_files(args)
    if args.command == "list":
        return action_list(args)
    if args.command == "get":
        return action_get(args)
    if args.command == "set":
        return action_set(args)
    if args.command == "unset":
        return action_unset(args)
    if args.command == "audit":
        return action_audit(args)
    if args.command == "export":
        return action_export(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
