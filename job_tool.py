#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : job_tool.py
Rel. Path   : job_tool.py
Family      : Job Management / Subsystem 5
Purpose     : High-density, stateful Job Manager & Urgent Deployment Engine
              implementing the Loaded Chamber Pattern for managing saved
              JobMaker BEJSON 104a jobs and Markdown task briefs.
              Enables listing, creating, selecting (locking into chamber),
              inspecting, editing, adding tasks, and deploying saved jobs
              directly into the urgent jobs folder ($JOBS_FOLDER).
Version     : 1.5.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-05
RELATIONAL_ID : bb348f5c-4862-4e96-b2ea-f57092c2c14d
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Self-Locating Path Preambles (Policy §4.1) ────────────────────────────────
def get_script_path() -> Path:
    """Resolve and return script directory."""
    return Path(__file__).resolve().parent

SCRIPT_PATH: Path = get_script_path()
LOCAL_LIB_DIRECTORY: Path = SCRIPT_PATH / "lib"
LOCAL_CONFIG_DIRECTORY: Path = SCRIPT_PATH / "config"
LOCAL_DATA_DIRECTORY: Path = SCRIPT_PATH / "data"
LOCAL_SAVED_JOBS_DIRECTORY: Path = LOCAL_DATA_DIRECTORY / "saved_jobs"
LOCAL_STATE_FILE_PATH: Path = LOCAL_CONFIG_DIRECTORY / "state.json"
LOCAL_CONFIG_FILE_PATH: Path = LOCAL_CONFIG_DIRECTORY / "config.json"

if str(LOCAL_LIB_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(LOCAL_LIB_DIRECTORY))

# ── Policy §8.1 Tri-Color Palette & 57-Column Discipline ─────────────────────
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

# ── Canonical Environment Resolution (Policy §4.5) ───────────────────────────
DEFINITIONS_STORE_PATH: Path = Path("/storage/emulated/0/.env/user/definitions.json")
DEFAULT_JOBS_FOLDER: Path = Path("/storage/emulated/0/Admin/System/Job_Management/Jobs")
DEFAULT_COMPLETED_JOBS_FOLDER: Path = Path("/storage/emulated/0/Admin/System/Job_Management/Completed_Jobs")
DEFAULT_TEMPLATES_FOLDER: Path = Path("/storage/emulated/0/Admin/System/Job_Management/Job_Templates")


def resolve_canonical_environment_paths() -> Dict[str, Path]:
    """Resolve environment paths dynamically from definitions store or defaults."""
    resolved_paths_dictionary: Dict[str, Path] = {
        "JOBS_FOLDER": DEFAULT_JOBS_FOLDER,
        "COMPLETED_JOBS_FOLDER": DEFAULT_COMPLETED_JOBS_FOLDER,
        "JOB_TEMPLATES": DEFAULT_TEMPLATES_FOLDER,
        "SAVED_JOBS": LOCAL_SAVED_JOBS_DIRECTORY
    }

    if DEFINITIONS_STORE_PATH.exists():
        try:
            with open(DEFINITIONS_STORE_PATH, "r", encoding="utf-8") as definitions_file_handle:
                definitions_data_payload: Dict[str, Any] = json.load(definitions_file_handle)
                definitions_records_values: List[List[Any]] = definitions_data_payload.get("Values", [])
                for definition_row_record in definitions_records_values:
                    if isinstance(definition_row_record, list) and len(definition_row_record) >= 2:
                        variable_name_key: str = str(definition_row_record[0]).strip()
                        variable_value_path_string: str = str(definition_row_record[1]).strip()
                        if variable_name_key in ("JOBS_FOLDER", "COMPLETED_JOBS_FOLDER", "JOB_TEMPLATES"):
                            resolved_paths_dictionary[variable_name_key] = Path(variable_value_path_string)
        except Exception:
            pass

    return resolved_paths_dictionary


# ── Canonical JobMaker BEJSON 104a Specification Helpers ─────────────────────
CANONICAL_JOB_FIELDS: List[Dict[str, str]] = [
    {"name": "task_id", "type": "string"},
    {"name": "task_order", "type": "integer"},
    {"name": "task_name", "type": "string"},
    {"name": "task_description", "type": "string"},
    {"name": "task_completed", "type": "boolean"},
    {"name": "audit_enabled", "type": "boolean"},
    {"name": "audit_passed", "type": "boolean"},
    {"name": "audit_fail_reason", "type": "string"},
    {"name": "task_context", "type": "array"},
    {"name": "task_reference", "type": "array"},
    {"name": "task_mandatory", "type": "boolean"}
]


def compile_bejson_field_map(bejson_document_payload: Dict[str, Any]) -> Dict[str, int]:
    """Compile an O(1) field name to column index lookup cache per Policy §6.2."""
    field_descriptor_collection: List[Dict[str, Any]] = bejson_document_payload.get("Fields", [])
    field_map_lookup_table: Dict[str, int] = {}
    for column_ordinal_index, field_descriptor_dictionary in enumerate(field_descriptor_collection):
        field_name_identifier: str = field_descriptor_dictionary.get("name", "")
        if field_name_identifier:
            field_map_lookup_table[field_name_identifier] = column_ordinal_index
    return field_map_lookup_table


def create_blank_bejson_job_document(
    job_goal_description: str,
    job_type_classification: str = "coding",
    job_subtype_classification: str = "general"
) -> Dict[str, Any]:
    """Generate canonical JobMaker BEJSON 104a document structure."""
    current_calendar_date_string: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": "Job Schema",
        "Schema_Version": "1.0",
        "Records_Type": ["JobTask"],
        "Job_Goal": job_goal_description,
        "Job_Type": job_type_classification,
        "Job_Subtype": job_subtype_classification,
        "Contextualize_Plan": True,
        "Contextualize_Last": True,
        "Job_Complete": False,
        "Creation_Date": current_calendar_date_string,
        "Completion_Date": "",
        "Fields": CANONICAL_JOB_FIELDS,
        "Values": []
    }


def create_blank_markdown_job_document(
    job_goal_description: str,
    job_type_classification: str = "general"
) -> str:
    """Generate canonical Markdown job brief document."""
    current_calendar_date_string: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"# Job: {job_goal_description}\n\n"
        f"**Date**: {current_calendar_date_string}\n"
        f"**Domain**: {job_type_classification}\n"
        f"**Status**: Pending\n\n"
        f"## Mission Goal\n"
        f"{job_goal_description}\n\n"
        f"## Tasks\n"
        f"- [ ] Step 1: Initial task analysis and staging.\n"
        f"- [ ] Step 2: Implementation and validation.\n"
    )


# ── Job Manager Engine (Loaded Chamber Pattern) ──────────────────────────────
class JobManagerEngine:
    """
    Stateful Job Manager and Deployment Engine implementing the Loaded Chamber Pattern:
      Phase 1: Discovery (List saved, deployed, completed, templates)
      Phase 2: Target Lock (Select job into persistent chamber)
      Phase 3: Execution Actions (View, edit, add-task, deploy, delete)
    """

    def __init__(self) -> None:
        self.paths_dictionary: Dict[str, Path] = resolve_canonical_environment_paths()
        self.saved_jobs_directory: Path = self.paths_dictionary["SAVED_JOBS"]
        self.jobs_folder_path: Path = self.paths_dictionary["JOBS_FOLDER"]
        self.completed_jobs_folder_path: Path = self.paths_dictionary["COMPLETED_JOBS_FOLDER"]
        self.templates_folder_path: Path = self.paths_dictionary["JOB_TEMPLATES"]
        self.state_file_path: Path = LOCAL_STATE_FILE_PATH

        self.ensure_storage_directories()

    def ensure_storage_directories(self) -> None:
        """Ensure all required local directories exist."""
        self.saved_jobs_directory.mkdir(parents=True, exist_ok=True)
        LOCAL_CONFIG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # ── State Store Handling ─────────────────────────────────────────────────
    def load_state_store(self) -> Dict[str, Any]:
        """Load persistent shared state."""
        if not self.state_file_path.exists():
            return {"active_mode": "jobs", "active_job": None, "active_job_path": None}
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as state_file_handle:
                return json.load(state_file_handle)
        except Exception:
            return {"active_mode": "jobs", "active_job": None, "active_job_path": None}

    def persist_state_store(self, state_payload_dictionary: Dict[str, Any]) -> None:
        """Atomically persist state."""
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_state_file_path: Path = self.state_file_path.with_suffix(".tmp")
        with open(temporary_state_file_path, "w", encoding="utf-8") as temporary_file_handle:
            json.dump(state_payload_dictionary, temporary_file_handle, indent=2)
            temporary_file_handle.write("\n")
        temporary_state_file_path.replace(self.state_file_path)

    # ── Loaded Chamber Accessors ─────────────────────────────────────────────
    def get_loaded_job_identifier(self) -> Optional[str]:
        """Return the filename or slug of the currently locked chamber job."""
        state_data: Dict[str, Any] = self.load_state_store()
        return state_data.get("active_job")

    def get_loaded_job_path(self) -> Optional[Path]:
        """Return the resolved Path of the currently locked chamber job if it exists."""
        job_identifier: Optional[str] = self.get_loaded_job_identifier()
        if not job_identifier:
            return None
        candidate_path: Path = self.saved_jobs_directory / job_identifier
        if candidate_path.exists():
            return candidate_path
        # Search without extension
        for candidate_file in self.saved_jobs_directory.iterdir():
            if candidate_file.is_file() and candidate_file.stem.lower() == job_identifier.lower():
                return candidate_file
        return None

    def lock_job_into_chamber(self, job_target_path: Path) -> None:
        """Lock target job into the persistent chamber."""
        state_data: Dict[str, Any] = self.load_state_store()
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()
        state_data["active_mode"] = "jobs"
        state_data["active_job"] = job_target_path.name
        state_data["active_job_path"] = str(job_target_path)
        state_data["active_job_format"] = "bejson" if job_target_path.suffix.lower() == ".bejson" else "markdown"
        state_data["updated_at"] = current_iso_timestamp
        self.persist_state_store(state_data)

    def clear_chamber_lock(self) -> None:
        """Clear the chamber target lock."""
        state_data: Dict[str, Any] = self.load_state_store()
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()
        state_data["active_job"] = None
        state_data["active_job_path"] = None
        state_data["active_job_format"] = None
        state_data["updated_at"] = current_iso_timestamp
        self.persist_state_store(state_data)

    # ── Phase 1: Discovery ───────────────────────────────────────────────────
    def list_saved_jobs(self) -> List[Dict[str, Any]]:
        """List all saved jobs in data/saved_jobs/."""
        saved_job_records: List[Dict[str, Any]] = []
        if not self.saved_jobs_directory.exists():
            return saved_job_records

        candidate_files: List[Path] = sorted(
            [entry for entry in self.saved_jobs_directory.iterdir() if entry.is_file() and entry.suffix.lower() in (".bejson", ".md", ".json")],
            key=lambda file_path_entry: file_path_entry.stat().st_mtime,
            reverse=True
        )

        for ordinal_index, file_path_entry in enumerate(candidate_files, start=1):
            is_bejson: bool = file_path_entry.suffix.lower() in (".bejson", ".json")
            task_count_metric: int = 0
            tasks_completed_metric: int = 0
            goal_summary_title: str = file_path_entry.stem.replace("_", " ")

            if is_bejson:
                try:
                    with open(file_path_entry, "r", encoding="utf-8") as file_handle:
                        payload: Dict[str, Any] = json.load(file_handle)
                        goal_summary_title = payload.get("Job_Goal", goal_summary_title)
                        values_collection: List[List[Any]] = payload.get("Values", [])
                        field_map: Dict[str, int] = compile_bejson_field_map(payload)
                        task_completed_index: Optional[int] = field_map.get("task_completed")
                        task_count_metric = len(values_collection)
                        if task_completed_index is not None:
                            for task_row in values_collection:
                                if len(task_row) > task_completed_index and task_row[task_completed_index] is True:
                                    tasks_completed_metric += 1
                except Exception:
                    pass
            else:
                try:
                    lines_collection: List[str] = file_path_entry.read_text(encoding="utf-8").splitlines()
                    for line_item in lines_collection:
                        line_stripped: str = line_item.strip()
                        if line_stripped.startswith("- [ ]") or line_stripped.startswith("* [ ]"):
                            task_count_metric += 1
                        elif line_stripped.startswith("- [x]") or line_stripped.startswith("* [x]"):
                            task_count_metric += 1
                            tasks_completed_metric += 1
                except Exception:
                    pass

            modification_timestamp_string: str = datetime.fromtimestamp(
                file_path_entry.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M")

            saved_job_records.append({
                "index": ordinal_index,
                "filename": file_path_entry.name,
                "stem": file_path_entry.stem,
                "format": "BEJSON" if is_bejson else "Markdown",
                "title": goal_summary_title,
                "task_count": task_count_metric,
                "tasks_completed": tasks_completed_metric,
                "modified": modification_timestamp_string,
                "path": file_path_entry
            })

        return saved_job_records

    def list_deployed_jobs(self) -> List[Dict[str, Any]]:
        """List active jobs currently present in $JOBS_FOLDER."""
        deployed_job_records: List[Dict[str, Any]] = []
        if not self.jobs_folder_path.exists():
            return deployed_job_records

        for entry_file in sorted(self.jobs_folder_path.iterdir()):
            if entry_file.is_file() and entry_file.name.upper() not in ("AGENTS.MD", "README.MD", ".GITIGNORE"):
                stat_metadata = entry_file.stat()
                modification_timestamp_string: str = datetime.fromtimestamp(
                    stat_metadata.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M")
                deployed_job_records.append({
                    "filename": entry_file.name,
                    "size_bytes": stat_metadata.st_size,
                    "modified": modification_timestamp_string,
                    "path": entry_file
                })
        return deployed_job_records

    def list_completed_jobs(self) -> List[Dict[str, Any]]:
        """List archived jobs in $COMPLETED_JOBS_FOLDER."""
        completed_records: List[Dict[str, Any]] = []
        if not self.completed_jobs_folder_path.exists():
            return completed_records

        for entry_path in sorted(self.completed_jobs_folder_path.iterdir()):
            if entry_path.name.upper() not in ("AGENTS.MD", "README.MD", ".GITIGNORE"):
                completed_records.append({
                    "name": entry_path.name,
                    "is_directory": entry_path.is_dir(),
                    "path": entry_path
                })
        return completed_records

    # ── Phase 2: Target Lock Operation ───────────────────────────────────────
    def select_job_by_query(self, query_identifier: str) -> Optional[Path]:
        """Find and lock saved job by index ordinal, filename, or partial slug."""
        available_jobs: List[Dict[str, Any]] = self.list_saved_jobs()
        if not available_jobs:
            return None

        # 1. Try matching numerical index
        if query_identifier.isdigit():
            target_index: int = int(query_identifier)
            for record_item in available_jobs:
                if record_item["index"] == target_index:
                    self.lock_job_into_chamber(record_item["path"])
                    return record_item["path"]

        # 2. Try exact filename match
        for record_item in available_jobs:
            if record_item["filename"].lower() == query_identifier.lower():
                self.lock_job_into_chamber(record_item["path"])
                return record_item["path"]

        # 3. Try exact stem match
        for record_item in available_jobs:
            if record_item["stem"].lower() == query_identifier.lower():
                self.lock_job_into_chamber(record_item["path"])
                return record_item["path"]

        # 4. Try prefix or substring match
        for record_item in available_jobs:
            if query_identifier.lower() in record_item["stem"].lower():
                self.lock_job_into_chamber(record_item["path"])
                return record_item["path"]

        return None

    # ── Phase 3: Execution Actions ───────────────────────────────────────────
    def create_new_saved_job(
        self,
        job_name_raw: str,
        job_format_type: str = "bejson",
        job_goal_text: Optional[str] = None,
        job_subtype_text: str = "general"
    ) -> Path:
        """Create a new job in saved storage."""
        slugified_file_stem: str = "".join(
            character_element if character_element.isalnum() or character_element in ("-", "_") else "_"
            for character_element in job_name_raw.strip()
        ).strip("_")

        if not slugified_file_stem:
            slugified_file_stem = f"Job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        goal_resolved: str = job_goal_text or job_name_raw.replace("_", " ")

        if job_format_type.lower() == "bejson":
            file_extension: str = ".bejson"
            target_job_path: Path = self.saved_jobs_directory / f"{slugified_file_stem}{file_extension}"
            job_payload_dictionary: Dict[str, Any] = create_blank_bejson_job_document(
                job_goal_description=goal_resolved,
                job_type_classification="coding",
                job_subtype_classification=job_subtype_text
            )
            with open(target_job_path, "w", encoding="utf-8") as target_file_handle:
                json.dump(job_payload_dictionary, target_file_handle, indent=2)
                target_file_handle.write("\n")
        else:
            file_extension = ".md"
            target_job_path = self.saved_jobs_directory / f"{slugified_file_stem}{file_extension}"
            markdown_content_string: str = create_blank_markdown_job_document(
                job_goal_description=goal_resolved,
                job_type_classification=job_subtype_text
            )
            target_job_path.write_text(markdown_content_string, encoding="utf-8")

        # Auto-lock newly created job into chamber
        self.lock_job_into_chamber(target_job_path)
        return target_job_path

    def add_task_to_bejson_job(
        self,
        job_target_path: Path,
        task_name_title: str,
        task_description_body: str = "",
        is_task_mandatory: bool = True,
        is_audit_enabled: bool = True
    ) -> bool:
        """Append a canonical JobTask row to a BEJSON 104a job."""
        if job_target_path.suffix.lower() not in (".bejson", ".json"):
            return False

        with open(job_target_path, "r", encoding="utf-8") as file_handle:
            payload: Dict[str, Any] = json.load(file_handle)

        field_map: Dict[str, int] = compile_bejson_field_map(payload)
        values_collection: List[List[Any]] = payload.get("Values", [])
        next_task_order_index: int = len(values_collection) + 1
        new_task_uuid_identifier: str = str(uuid.uuid4())

        # Construct row according to canonical field order
        task_row_item: List[Any] = [None] * len(payload.get("Fields", []))
        if "task_id" in field_map:
            task_row_item[field_map["task_id"]] = new_task_uuid_identifier
        if "task_order" in field_map:
            task_row_item[field_map["task_order"]] = next_task_order_index
        if "task_name" in field_map:
            task_row_item[field_map["task_name"]] = task_name_title
        if "task_description" in field_map:
            task_row_item[field_map["task_description"]] = task_description_body
        if "task_completed" in field_map:
            task_row_item[field_map["task_completed"]] = False
        if "audit_enabled" in field_map:
            task_row_item[field_map["audit_enabled"]] = is_audit_enabled
        if "audit_passed" in field_map:
            task_row_item[field_map["audit_passed"]] = False
        if "audit_fail_reason" in field_map:
            task_row_item[field_map["audit_fail_reason"]] = ""
        if "task_context" in field_map:
            task_row_item[field_map["task_context"]] = []
        if "task_reference" in field_map:
            task_row_item[field_map["task_reference"]] = []
        if "task_mandatory" in field_map:
            task_row_item[field_map["task_mandatory"]] = is_task_mandatory

        values_collection.append(task_row_item)
        payload["Values"] = values_collection
        payload["Job_Complete"] = False

        with open(job_target_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)
            file_handle.write("\n")
        return True

    def toggle_bejson_task_completion(
        self,
        job_target_path: Path,
        task_selector: str
    ) -> Optional[bool]:
        """Toggle task_completed status in BEJSON job."""
        if job_target_path.suffix.lower() not in (".bejson", ".json"):
            return None

        with open(job_target_path, "r", encoding="utf-8") as file_handle:
            payload: Dict[str, Any] = json.load(file_handle)

        field_map: Dict[str, int] = compile_bejson_field_map(payload)
        values_collection: List[List[Any]] = payload.get("Values", [])
        task_order_idx: Optional[int] = field_map.get("task_order")
        task_completed_idx: Optional[int] = field_map.get("task_completed")
        task_id_idx: Optional[int] = field_map.get("task_id")

        if task_completed_idx is None:
            return None

        updated_state_result: Optional[bool] = None
        for row in values_collection:
            matches_order: bool = task_order_idx is not None and str(row[task_order_idx]) == task_selector
            matches_id: bool = task_id_idx is not None and str(row[task_id_idx]).startswith(task_selector)
            if matches_order or matches_id:
                row[task_completed_idx] = not row[task_completed_idx]
                updated_state_result = row[task_completed_idx]
                break

        if updated_state_result is not None:
            # Check if all tasks completed
            all_done: bool = all(
                bool(row[task_completed_idx]) for row in values_collection if len(row) > task_completed_idx
            )
            payload["Job_Complete"] = all_done
            if all_done:
                payload["Completion_Date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            else:
                payload["Completion_Date"] = ""

            with open(job_target_path, "w", encoding="utf-8") as file_handle:
                json.dump(payload, file_handle, indent=2)
                file_handle.write("\n")

        return updated_state_result

    def deploy_job_to_urgent_folder(
        self,
        source_job_path: Path,
        force_overwrite: bool = False
    ) -> Tuple[bool, str, Optional[Path]]:
        """
        Deploy (copy) saved job directly into $JOBS_FOLDER to trigger urgent agent execution.
        Returns: (success_boolean, status_message_string, destination_file_path)
        """
        if not source_job_path.exists():
            return False, f"Source job file not found: {source_job_path.name}", None

        # Ensure destination directory exists
        self.jobs_folder_path.mkdir(parents=True, exist_ok=True)
        destination_target_file_path: Path = self.jobs_folder_path / source_job_path.name

        if destination_target_file_path.exists() and not force_overwrite:
            return (
                False,
                f"Job already exists in urgent queue: {destination_target_file_path.name}. Use --force to overwrite.",
                destination_target_file_path
            )

        try:
            shutil.copy2(source_job_path, destination_target_file_path)
            return True, f"Deployed successfully to {destination_target_file_path}", destination_target_file_path
        except Exception as copy_exception_error:
            return False, f"Deployment failed: {copy_exception_error}", None

    def delete_saved_job(self, job_target_path: Path) -> bool:
        """Remove a saved job file and clear chamber if it was locked."""
        if not job_target_path.exists():
            return False
        job_name_string: str = job_target_path.name
        job_target_path.unlink()
        if self.get_loaded_job_identifier() == job_name_string:
            self.clear_chamber_lock()
        return True


# ── Formatting & 57-Column Visual Rendering (Policy §8.1 / §8.4) ─────────────
def print_chamber_status_banner(engine: JobManagerEngine) -> None:
    """Render 57-column chamber status banner."""
    loaded_job_name: Optional[str] = engine.get_loaded_job_identifier()
    loaded_job_path: Optional[Path] = engine.get_loaded_job_path()
    deployed_records: List[Dict[str, Any]] = engine.list_deployed_jobs()
    deployed_count: int = len(deployed_records)

    print(DIVIDER_57)
    print(f" {ACCENT}JOB MANAGEMENT SYSTEM [LOADED CHAMBER]{RESET}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}MODE:{RESET}     JOBS             {ACCENT}URGENT QUEUE:{RESET} {deployed_count:<2} active")

    if loaded_job_path and loaded_job_path.exists():
        is_bejson: bool = loaded_job_path.suffix.lower() in (".bejson", ".json")
        format_display: str = "BEJSON 104a" if is_bejson else "Markdown"
        print(f" {ACCENT}CHAMBER:{RESET}  [LOCKED]         {ACCENT}FORMAT:{RESET}       {format_display}")
        print(f" {ACCENT}TARGET:{RESET}   {loaded_job_path.name[:45]}")

        if is_bejson:
            try:
                with open(loaded_job_path, "r", encoding="utf-8") as file_handle:
                    payload: Dict[str, Any] = json.load(file_handle)
                    goal_text: str = payload.get("Job_Goal", "")
                    values_collection: List[List[Any]] = payload.get("Values", [])
                    field_map: Dict[str, int] = compile_bejson_field_map(payload)
                    task_completed_idx: Optional[int] = field_map.get("task_completed")
                    done_count: int = 0
                    if task_completed_idx is not None:
                        for row in values_collection:
                            if len(row) > task_completed_idx and row[task_completed_idx] is True:
                                done_count += 1
                    total_count: int = len(values_collection)
                    print(f" {ACCENT}GOAL:{RESET}     {goal_text[:45]}")
                    print(f" {ACCENT}PROGRESS:{RESET} {done_count}/{total_count} tasks completed")
            except Exception:
                pass
        else:
            file_size_bytes: int = loaded_job_path.stat().st_size
            print(f" {ACCENT}SIZE:{RESET}     {file_size_bytes} bytes")
    else:
        print(f" {ACCENT}CHAMBER:{RESET}  (empty - no job loaded in chamber)")
        print(f" {DIM}Use --list to view saved jobs and --select-job <id> to lock.{RESET}")

    print(DIVIDER_57)


def print_saved_jobs_table(saved_jobs: List[Dict[str, Any]], active_job_name: Optional[str] = None) -> None:
    """Render saved jobs in 57-column table."""
    print(DIVIDER_57)
    print(f" {ACCENT}{'#':<3} {'FORMAT':<8} {'TASKS':<7} {'NAME'}{RESET}")
    print(SUBDIVIDER_57)
    if not saved_jobs:
        print(f" {DIM}No saved jobs found in data/saved_jobs/{RESET}")
        print(f" {DIM}Create one with: --new <job_name>{RESET}")
    else:
        for job_record in saved_jobs:
            marker_indicator: str = f"{ACCENT}*{RESET}" if job_record["filename"] == active_job_name else " "
            idx_str: str = f"{job_record['index']}{marker_indicator}"
            fmt_str: str = job_record["format"][:8]
            progress_str: str = f"{job_record['tasks_completed']}/{job_record['task_count']}"
            name_str: str = job_record["stem"][:34]
            print(f" {idx_str:<4} {fmt_str:<8} {progress_str:<7} {name_str}")
    print(DIVIDER_57)


def print_deployed_jobs_table(deployed_jobs: List[Dict[str, Any]]) -> None:
    """Render active urgent queue jobs in 57-column table."""
    print(DIVIDER_57)
    print(f" {ACCENT}URGENT JOBS QUEUE ($JOBS_FOLDER){RESET}")
    print(SUBDIVIDER_57)
    if not deployed_jobs:
        print(f" {DIM}Queue is empty. No jobs waiting for urgent execution.{RESET}")
    else:
        for deployed_record in deployed_jobs:
            size_kb: float = deployed_record["size_bytes"] / 1024.0
            print(f" • {deployed_record['filename'][:36]:<36} {size_kb:>5.1f}KB")
            print(f"   {DIM}Modified: {deployed_record['modified']}{RESET}")
    print(DIVIDER_57)


def print_job_detailed_view(job_path: Path) -> None:
    """Render comprehensive view of a job document."""
    if not job_path.exists():
        print(f"{ACCENT}[✗] Error:{RESET} Job file does not exist: {job_path.name}")
        return

    is_bejson: bool = job_path.suffix.lower() in (".bejson", ".json")

    print(DIVIDER_57)
    print(f" {ACCENT}JOB DETAIL:{RESET} {job_path.name}")
    print(SUBDIVIDER_57)

    if is_bejson:
        try:
            with open(job_path, "r", encoding="utf-8") as file_handle:
                payload: Dict[str, Any] = json.load(file_handle)

            print(f" {ACCENT}Goal:{RESET}       {payload.get('Job_Goal', '(none)')}")
            print(f" {ACCENT}Type:{RESET}       {payload.get('Job_Type', 'coding')} / {payload.get('Job_Subtype', 'general')}")
            print(f" {ACCENT}Complete:{RESET}   {payload.get('Job_Complete', False)}")
            print(f" {ACCENT}Created:{RESET}    {payload.get('Creation_Date', '')}")
            if payload.get("Completion_Date"):
                print(f" {ACCENT}Finished:{RESET}   {payload.get('Completion_Date')}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}TASKS LIST:{RESET}")

            field_map: Dict[str, int] = compile_bejson_field_map(payload)
            values_collection: List[List[Any]] = payload.get("Values", [])
            order_idx: Optional[int] = field_map.get("task_order")
            name_idx: Optional[int] = field_map.get("task_name")
            completed_idx: Optional[int] = field_map.get("task_completed")
            audit_idx: Optional[int] = field_map.get("audit_enabled")
            mandatory_idx: Optional[int] = field_map.get("task_mandatory")

            if not values_collection:
                print(f"  {DIM}(no tasks defined - add with --add-task){RESET}")
            else:
                for row in values_collection:
                    order_val = row[order_idx] if order_idx is not None and len(row) > order_idx else "?"
                    name_val = row[name_idx] if name_idx is not None and len(row) > name_idx else "(unnamed)"
                    is_done = row[completed_idx] if completed_idx is not None and len(row) > completed_idx else False
                    is_mand = row[mandatory_idx] if mandatory_idx is not None and len(row) > mandatory_idx else False
                    is_aud = row[audit_idx] if audit_idx is not None and len(row) > audit_idx else False

                    check_mark: str = f"[{ACCENT}✓{RESET}]" if is_done else "[ ]"
                    flags_tag: str = f"({ 'M' if is_mand else '' }{ 'A' if is_aud else '' })"
                    print(f"  {check_mark} Step {order_val}: {name_val[:38]} {DIM}{flags_tag}{RESET}")
        except Exception as parse_error:
            print(f" {ACCENT}[✗] Failed to parse BEJSON job:{RESET} {parse_error}")
    else:
        text_content: str = job_path.read_text(encoding="utf-8")
        for text_line in text_content.splitlines()[:30]:
            print(f"  {text_line[:54]}")
        if len(text_content.splitlines()) > 30:
            print(f"  {DIM}... (truncated for display){RESET}")

    print(DIVIDER_57)


# ── Command-Line Parser Configuration ─────────────────────────────────────────
def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for Job Manager."""
    parser = argparse.ArgumentParser(
        prog="job_tool.py",
        description="Stateful Job Manager & Urgent Deployment Engine (Mode 5, Loaded Chamber Pattern).",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Phase 1: Discovery
    parser.add_argument("--list-saved", "--list", "-l", action="store_true", help="List all saved job files in storage")
    parser.add_argument("--list-deployed", "--deployed", action="store_true", help="List active jobs in urgent queue")
    parser.add_argument("--list-completed", "--completed", action="store_true", help="List archived completed jobs")
    parser.add_argument("--status", action="store_true", help="Display 57-column chamber status banner")

    # Phase 2: Target Lock
    parser.add_argument("--select-job", "-s", metavar="TARGET", help="Lock job into chamber by index, name, or slug")
    parser.add_argument("--clear-job", action="store_true", help="Clear currently locked job from chamber")
    parser.add_argument("--show-chamber", action="store_true", help="Display details of loaded chamber job")

    # Phase 3: Execution Actions
    parser.add_argument("--new", "--create-job", metavar="NAME", help="Create a new saved job document")
    parser.add_argument("--type", choices=["bejson", "md"], default="bejson", help="Job document format (default: bejson)")
    parser.add_argument("--goal", metavar="GOAL", help="Mission goal for the new job")
    parser.add_argument("--subtype", default="general", help="Subtype domain classification")

    parser.add_argument("--view", action="store_true", help="View full details and task list of loaded job")
    parser.add_argument("--add-task", metavar="TITLE", help="Append a new task to loaded BEJSON job")
    parser.add_argument("--task-desc", default="", help="Detailed description for the new task")
    parser.add_argument("--non-mandatory", action="store_true", help="Mark new task as non-mandatory")
    parser.add_argument("--no-audit", action="store_true", help="Disable audit requirement on new task")

    parser.add_argument("--toggle-task", metavar="ORDER", help="Toggle completion of task by step order")
    parser.add_argument("--deploy", action="store_true", help="Deploy loaded saved job to urgent queue ($JOBS_FOLDER)")
    parser.add_argument("--force", action="store_true", help="Force overwrite when deploying or deleting")
    parser.add_argument("--delete", action="store_true", help="Delete loaded saved job from storage")
    parser.add_argument("--pull-deployed", metavar="FILE", help="Pull a job from urgent queue into saved jobs")

    return parser


# ── Main Entrypoint ──────────────────────────────────────────────────────────
def main() -> int:
    """Execute Job Manager CLI routine."""
    engine = JobManagerEngine()
    parser = build_argument_parser()
    parsed_arguments = parser.parse_args()

    # Default to status if no arguments provided
    if len(sys.argv) == 1:
        print_chamber_status_banner(engine)
        print()
        parser.print_help()
        return 0

    # Phase 1: Discovery Commands
    if parsed_arguments.status:
        print_chamber_status_banner(engine)
        return 0

    if parsed_arguments.list_saved:
        saved_items = engine.list_saved_jobs()
        active_target_name = engine.get_loaded_job_identifier()
        print_saved_jobs_table(saved_items, active_target_name)
        return 0

    if parsed_arguments.list_deployed:
        deployed_items = engine.list_deployed_jobs()
        print_deployed_jobs_table(deployed_items)
        return 0

    if parsed_arguments.list_completed:
        completed_items = engine.list_completed_jobs()
        print(DIVIDER_57)
        print(f" {ACCENT}COMPLETED JOBS ARCHIVE ($COMPLETED_JOBS_FOLDER){RESET}")
        print(SUBDIVIDER_57)
        if not completed_items:
            print(f" {DIM}No archived completed jobs found.{RESET}")
        else:
            for item in completed_items:
                dir_marker = "/" if item["is_directory"] else ""
                print(f" • {item['name']}{dir_marker}")
        print(DIVIDER_57)
        return 0

    # Phase 2: Target Lock Commands
    if parsed_arguments.select_job:
        target_query: str = parsed_arguments.select_job.strip()
        matched_job_path: Optional[Path] = engine.select_job_by_query(target_query)
        if matched_job_path:
            print(f"{ACCENT}[✓] Chamber Locked:{RESET} {matched_job_path.name}")
            print_chamber_status_banner(engine)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} No saved job matched query '{target_query}'.", file=sys.stderr)
            return 1

    if parsed_arguments.clear_job:
        engine.clear_chamber_lock()
        print(f"{ACCENT}[✓] Chamber target cleared.{RESET}")
        return 0

    if parsed_arguments.show_chamber:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[!] Warning:{RESET} Chamber is empty. No job currently locked.")
            return 1
        print_job_detailed_view(loaded_path)
        return 0

    # Phase 3: Execution Actions
    if parsed_arguments.new:
        new_name_raw: str = parsed_arguments.new
        created_path = engine.create_new_saved_job(
            job_name_raw=new_name_raw,
            job_format_type=parsed_arguments.type,
            job_goal_text=parsed_arguments.goal,
            job_subtype_text=parsed_arguments.subtype
        )
        print(f"{ACCENT}[✓] Created and locked into chamber:{RESET} {created_path.name}")
        print_job_detailed_view(created_path)
        return 0

    if parsed_arguments.view:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber. Use --select-job <id> first.", file=sys.stderr)
            return 1
        print_job_detailed_view(loaded_path)
        return 0

    if parsed_arguments.add_task:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber. Use --select-job <id> first.", file=sys.stderr)
            return 1
        success = engine.add_task_to_bejson_job(
            job_target_path=loaded_path,
            task_name_title=parsed_arguments.add_task,
            task_description_body=parsed_arguments.task_desc,
            is_task_mandatory=not parsed_arguments.non_mandatory,
            is_audit_enabled=not parsed_arguments.no_audit
        )
        if success:
            print(f"{ACCENT}[✓] Task added successfully:{RESET} {parsed_arguments.add_task}")
            print_job_detailed_view(loaded_path)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} Failed to add task (ensure target is a BEJSON job).", file=sys.stderr)
            return 1

    if parsed_arguments.toggle_task:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber. Use --select-job <id> first.", file=sys.stderr)
            return 1
        result = engine.toggle_bejson_task_completion(loaded_path, parsed_arguments.toggle_task)
        if result is not None:
            status_text = "Completed" if result else "Pending"
            print(f"{ACCENT}[✓] Task status toggled to:{RESET} [{status_text}]")
            print_job_detailed_view(loaded_path)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} Could not find or toggle task '{parsed_arguments.toggle_task}'.", file=sys.stderr)
            return 1

    if parsed_arguments.deploy:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber to deploy. Use --select-job <id> first.", file=sys.stderr)
            return 1

        success, message, dest_path = engine.deploy_job_to_urgent_folder(
            source_job_path=loaded_path,
            force_overwrite=parsed_arguments.force
        )

        if success and dest_path:
            print(DIVIDER_57)
            print(f" {ACCENT}URGENT JOB DEPLOYMENT CONFIRMATION{RESET}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}SOURCE:{RESET}      {loaded_path.name}")
            print(f" {ACCENT}DESTINATION:{RESET} {dest_path}")
            print(f" {ACCENT}SIZE:{RESET}        {dest_path.stat().st_size} bytes")
            print(f" {ACCENT}TIMESTAMP:{RESET}   {datetime.now(timezone.utc).isoformat()}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}[✓] STATUS: DEPLOYED TO URGENT QUEUE!{RESET}")
            print(f" {DIM}Next session startup scan will pick up this job.{RESET}")
            print(DIVIDER_57)
            return 0
        else:
            print(f"{ACCENT}[✗] Deployment failed:{RESET} {message}", file=sys.stderr)
            return 1

    if parsed_arguments.delete:
        loaded_path = engine.get_loaded_job_path()
        if not loaded_path:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber. Use --select-job <id> first.", file=sys.stderr)
            return 1

        if not parsed_arguments.force:
            print(f"{ACCENT}[!] Confirm Deletion:{RESET} Pass --force to permanently delete '{loaded_path.name}'.")
            return 1

        target_name_str = loaded_path.name
        engine.delete_saved_job(loaded_path)
        print(f"{ACCENT}[✓] Deleted job:{RESET} {target_name_str}")
        return 0

    if parsed_arguments.pull_deployed:
        candidate_filename = parsed_arguments.pull_deployed
        source_in_deployed = engine.jobs_folder_path / candidate_filename
        source_in_completed = engine.completed_jobs_folder_path / candidate_filename
        target_source: Optional[Path] = None

        if source_in_deployed.exists():
            target_source = source_in_deployed
        elif source_in_completed.exists():
            target_source = source_in_completed

        if not target_source or not target_source.is_file():
            print(f"{ACCENT}[✗] Error:{RESET} File not found in deployed or completed folders: {candidate_filename}", file=sys.stderr)
            return 1

        destination_saved_path = engine.saved_jobs_directory / candidate_filename
        shutil.copy2(target_source, destination_saved_path)
        engine.lock_job_into_chamber(destination_saved_path)
        print(f"{ACCENT}[✓] Pulled into saved jobs and locked:{RESET} {candidate_filename}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
