#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : job_tool.py
Rel. Path   : job_tool.py
Family      : Job Management / Subsystem 4
Purpose     : Authoritative BEJSON 104a Job Management Engine & CLI Interface.
              Stores active and completed jobs directly in formal BEJSON schemas:
                - Active Registry:    job_registry.104a.bejson
                - Completed Registry: Completed_Jobs/completed_jobs_registry.104a.bejson
              Implements the Loaded Chamber Pattern persisting active job ID and
              subdirectory ('active', 'saved', 'completed').
              Functions:
                - Creating jobs with Name, Instructions, Context Notes, Priority
                - Marking active / inactive (moving between active and saved)
                - Setting priority (urgent, high, normal, low)
                - Marking complete (moving to Completed_Jobs & recording in completed registry)
                - Persistent selection, high-density 57-column viewing, task stepping
Version     : 1.6.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-09
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

# ── Path Preambles (Policy §4.1 & §4.5) ──────────────────────────────────────
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
DEFAULT_JOB_ROOT: Path = LOCAL_DATA_DIRECTORY
DEFAULT_JOBS_FOLDER: Path = DEFAULT_JOB_ROOT / "jobs"
DEFAULT_COMPLETED_FOLDER: Path = DEFAULT_JOB_ROOT / "completed_jobs"
DEFAULT_TEMPLATES_FOLDER: Path = DEFAULT_JOB_ROOT / "saved_jobs"


def resolve_canonical_paths() -> Dict[str, Path]:
    """Resolve job environment paths dynamically."""
    paths_map: Dict[str, Path] = {
        "JOB_ROOT": DEFAULT_JOB_ROOT,
        "JOBS_FOLDER": DEFAULT_JOBS_FOLDER,
        "COMPLETED_JOBS_FOLDER": DEFAULT_COMPLETED_FOLDER,
        "JOB_TEMPLATES": DEFAULT_TEMPLATES_FOLDER,
        "SAVED_JOBS": LOCAL_SAVED_JOBS_DIRECTORY,
        "ACTIVE_REGISTRY": DEFAULT_JOB_ROOT / "job_registry.104a.bejson",
        "COMPLETED_REGISTRY": DEFAULT_JOB_ROOT / "completed_jobs_registry.104a.bejson",
        "MAINTENANCE_REGISTRY": DEFAULT_JOB_ROOT / "maintenance_jobs_registry.104a.bejson",
    }

    if DEFINITIONS_STORE_PATH.exists():
        try:
            with open(DEFINITIONS_STORE_PATH, "r", encoding="utf-8") as file_handle:
                doc = json.load(file_handle)
                for row in doc.get("Values", []):
                    if isinstance(row, list) and len(row) >= 2:
                        k, v = str(row[0]).strip(), str(row[1]).strip()
                        if k == "JOBS_FOLDER":
                            paths_map["JOBS_FOLDER"] = Path(v)
                            paths_map["ACTIVE_REGISTRY"] = Path(v).parent / "job_registry.104a.bejson"
                        elif k == "COMPLETED_JOBS_FOLDER":
                            paths_map["COMPLETED_JOBS_FOLDER"] = Path(v)
                            paths_map["COMPLETED_REGISTRY"] = Path(v).parent / "completed_jobs_registry.104a.bejson"
                        elif k == "MAINTENANCE_JOBS_REGISTRY":
                            paths_map["MAINTENANCE_REGISTRY"] = Path(v)
                        elif k == "JOB_TEMPLATES":
                            paths_map["JOB_TEMPLATES"] = Path(v)
        except Exception:
            pass

    return paths_map


# ── Canonical BEJSON 104a Schemas ────────────────────────────────────────────
ACTIVE_REGISTRY_FIELDS: List[Dict[str, str]] = [
    {"name": "job_id", "type": "string"},
    {"name": "job_name", "type": "string"},
    {"name": "priority", "type": "string"},
    {"name": "status", "type": "string"},
    {"name": "creation_date", "type": "string"},
    {"name": "assigned_actor", "type": "string"},
    {"name": "job_instructions", "type": "string"},
    {"name": "job_context_notes", "type": "string"},
    {"name": "task_count", "type": "integer"},
    {"name": "tasks_completed", "type": "integer"},
    {"name": "tasks_json", "type": "string"},
    {"name": "job_file_path", "type": "string"},
    {"name": "tags", "type": "string"},
]

COMPLETED_REGISTRY_FIELDS: List[Dict[str, str]] = [
    {"name": "job_id", "type": "string"},
    {"name": "job_name", "type": "string"},
    {"name": "priority", "type": "string"},
    {"name": "creation_date", "type": "string"},
    {"name": "completion_date", "type": "string"},
    {"name": "duration_seconds", "type": "integer"},
    {"name": "completed_by", "type": "string"},
    {"name": "resolution_summary", "type": "string"},
    {"name": "artifacts_produced", "type": "string"},
    {"name": "job_instructions", "type": "string"},
    {"name": "job_context_notes", "type": "string"},
    {"name": "tasks_json", "type": "string"},
    {"name": "archive_file_path", "type": "string"},
    {"name": "tags", "type": "string"},
]

MAINTENANCE_REGISTRY_FIELDS: List[Dict[str, str]] = [
    {"name": "job_id", "type": "string"},
    {"name": "job_name", "type": "string"},
    {"name": "priority", "type": "string"},
    {"name": "frequency", "type": "string"},
    {"name": "governing_skill", "type": "string"},
    {"name": "command_to_run", "type": "string"},
    {"name": "job_instructions", "type": "string"},
    {"name": "job_context_notes", "type": "string"},
    {"name": "status", "type": "string"},
    {"name": "last_run_timestamp", "type": "string"},
    {"name": "run_count", "type": "integer"},
    {"name": "last_result", "type": "string"},
    {"name": "tags", "type": "string"},
]


def compile_bejson_field_map(doc_payload: Dict[str, Any]) -> Dict[str, int]:
    """Compile O(1) field name to column index lookup cache per Policy §6.2."""
    fields: List[Dict[str, Any]] = doc_payload.get("Fields", [])
    return {f.get("name", ""): idx for idx, f in enumerate(fields) if f.get("name")}


def load_bejson_file(file_path: Path, default_fields: Optional[List[Dict[str, str]]] = None, schema_name: str = "Schema") -> Dict[str, Any]:
    """Load a BEJSON 104a file or initialize a fresh template if missing."""
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to parse {file_path.name}: {e}\n")

    return {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": schema_name,
        "Schema_Version": "1.0.0",
        "Records_Type": [schema_name.replace(" ", "")],
        "Fields": default_fields or [],
        "Values": [],
    }


def save_bejson_atomic(file_path: Path, doc_payload: Dict[str, Any]) -> None:
    """Save BEJSON document atomically via temporary swap."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(doc_payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp_path.replace(file_path)


# ── Job Manager Engine ───────────────────────────────────────────────────────
class JobManagerEngine:
    """
    Authoritative Job Manager Engine implementing the Loaded Chamber Pattern
    persisting job ID and subdirectory ('active', 'saved', 'completed').
    """

    def __init__(self) -> None:
        self.paths: Dict[str, Path] = resolve_canonical_paths()
        self.ensure_storage_directories()

    def ensure_storage_directories(self) -> None:
        """Verify and create directories and initial registries."""
        for p in (self.paths["JOB_ROOT"], self.paths["JOBS_FOLDER"], self.paths["COMPLETED_JOBS_FOLDER"], self.paths["SAVED_JOBS"], LOCAL_CONFIG_DIRECTORY):
            p.mkdir(parents=True, exist_ok=True)

        if not self.paths["ACTIVE_REGISTRY"].exists():
            save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], load_bejson_file(self.paths["ACTIVE_REGISTRY"], ACTIVE_REGISTRY_FIELDS, "Active Job Registry Schema"))

        if not self.paths["COMPLETED_REGISTRY"].exists():
            save_bejson_atomic(self.paths["COMPLETED_REGISTRY"], load_bejson_file(self.paths["COMPLETED_REGISTRY"], COMPLETED_REGISTRY_FIELDS, "Completed Job Registry Schema"))

        if not self.paths["MAINTENANCE_REGISTRY"].exists():
            save_bejson_atomic(self.paths["MAINTENANCE_REGISTRY"], load_bejson_file(self.paths["MAINTENANCE_REGISTRY"], MAINTENANCE_REGISTRY_FIELDS, "Maintenance Jobs Registry Schema"))

    # ── Chamber State Management ─────────────────────────────────────────────
    def load_state(self) -> Dict[str, Any]:
        """Load persistent chamber state."""
        if not LOCAL_STATE_FILE_PATH.exists():
            return {"active_mode": "jobs", "active_job": None, "active_job_subdir": None}
        try:
            with open(LOCAL_STATE_FILE_PATH, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {"active_mode": "jobs", "active_job": None, "active_job_subdir": None}

    def persist_state(self, state_data: Dict[str, Any]) -> None:
        """Save persistent chamber state atomically."""
        LOCAL_CONFIG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        tmp = LOCAL_STATE_FILE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(state_data, handle, indent=2)
            handle.write("\n")
        tmp.replace(LOCAL_STATE_FILE_PATH)

    def lock_job(self, job_id: str, job_name: str, subdir: str = "active", file_path: str = "") -> None:
        """Lock job into chamber, persisting active_job, active_job_name, and active_job_subdir."""
        state = self.load_state()
        state["active_mode"] = "jobs"
        state["active_job"] = job_id
        state["active_job_name"] = job_name
        state["active_job_subdir"] = subdir
        state["active_job_path"] = file_path
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.persist_state(state)

    def clear_chamber(self) -> None:
        """Clear active job and subdir from chamber."""
        state = self.load_state()
        state["active_job"] = None
        state["active_job_name"] = None
        state["active_job_subdir"] = None
        state["active_job_path"] = None
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.persist_state(state)

    def get_loaded_job_info(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return (active_job_id, active_job_name, active_job_subdir)."""
        state = self.load_state()
        return (state.get("active_job"), state.get("active_job_name"), state.get("active_job_subdir"))

    # ── Registry CRUD Operations ─────────────────────────────────────────────
    def get_active_registry(self) -> Dict[str, Any]:
        return load_bejson_file(self.paths["ACTIVE_REGISTRY"], ACTIVE_REGISTRY_FIELDS, "Active Job Registry Schema")

    def get_completed_registry(self) -> Dict[str, Any]:
        return load_bejson_file(self.paths["COMPLETED_REGISTRY"], COMPLETED_REGISTRY_FIELDS, "Completed Job Registry Schema")

    def list_active_jobs(self) -> List[Dict[str, Any]]:
        """Return list of all active/pending/inactive jobs from active registry."""
        doc = self.get_active_registry()
        fmap = compile_bejson_field_map(doc)
        results = []
        for idx, row in enumerate(doc.get("Values", []), 1):
            results.append({
                "index": idx,
                "job_id": str(row[fmap.get("job_id", 0)]),
                "job_name": str(row[fmap.get("job_name", 1)]),
                "priority": str(row[fmap.get("priority", 2)]),
                "status": str(row[fmap.get("status", 3)]),
                "creation_date": str(row[fmap.get("creation_date", 4)]),
                "assigned_actor": str(row[fmap.get("assigned_actor", 5)]),
                "job_instructions": str(row[fmap.get("job_instructions", 6)]),
                "job_context_notes": str(row[fmap.get("job_context_notes", 7)]),
                "task_count": int(row[fmap.get("task_count", 8)] or 0),
                "tasks_completed": int(row[fmap.get("tasks_completed", 9)] or 0),
                "tasks_json": str(row[fmap.get("tasks_json", 10)] or "[]"),
                "job_file_path": str(row[fmap.get("job_file_path", 11)]),
                "tags": str(row[fmap.get("tags", 12)]),
                "subdir": "active" if str(row[fmap.get("status", 3)]).lower() == "active" else "saved",
            })
        return results

    def list_completed_jobs(self) -> List[Dict[str, Any]]:
        """Return list of all completed jobs from completed registry."""
        doc = self.get_completed_registry()
        fmap = compile_bejson_field_map(doc)
        results = []
        for idx, row in enumerate(doc.get("Values", []), 1):
            results.append({
                "index": idx,
                "job_id": str(row[fmap.get("job_id", 0)]),
                "job_name": str(row[fmap.get("job_name", 1)]),
                "priority": str(row[fmap.get("priority", 2)]),
                "creation_date": str(row[fmap.get("creation_date", 3)]),
                "completion_date": str(row[fmap.get("completion_date", 4)]),
                "duration_seconds": int(row[fmap.get("duration_seconds", 5)] or 0),
                "completed_by": str(row[fmap.get("completed_by", 6)]),
                "resolution_summary": str(row[fmap.get("resolution_summary", 7)]),
                "artifacts_produced": str(row[fmap.get("artifacts_produced", 8)]),
                "job_instructions": str(row[fmap.get("job_instructions", 9)]),
                "job_context_notes": str(row[fmap.get("job_context_notes", 10)]),
                "tasks_json": str(row[fmap.get("tasks_json", 11)] or "[]"),
                "archive_file_path": str(row[fmap.get("archive_file_path", 12)]),
                "tags": str(row[fmap.get("tags", 13)]),
                "subdir": "completed",
            })
        return results

    def list_saved_files(self) -> List[Dict[str, Any]]:
        """List draft templates or saved jobs in data/saved_jobs/."""
        results = []
        if self.paths["SAVED_JOBS"].exists():
            for idx, entry in enumerate(sorted(self.paths["SAVED_JOBS"].iterdir()), 1):
                if entry.is_file() and entry.suffix.lower() in (".bejson", ".md", ".json"):
                    results.append({
                        "index": idx,
                        "filename": entry.name,
                        "path": str(entry),
                        "size": entry.stat().st_size,
                        "subdir": "saved",
                    })
        return results

    # ── Maintenance Registry Operations (Standing Recurring) ─────────────────
    def get_maintenance_registry(self) -> Dict[str, Any]:
        return load_bejson_file(self.paths["MAINTENANCE_REGISTRY"], MAINTENANCE_REGISTRY_FIELDS, "Maintenance Jobs Registry Schema")

    def list_maintenance_jobs(self) -> List[Dict[str, Any]]:
        """Return list of all standing recurring maintenance jobs from registry."""
        doc = self.get_maintenance_registry()
        fmap = compile_bejson_field_map(doc)
        results = []
        for idx, row in enumerate(doc.get("Values", []), 1):
            results.append({
                "index": idx,
                "job_id": str(row[fmap.get("job_id", 0)]),
                "job_name": str(row[fmap.get("job_name", 1)]),
                "priority": str(row[fmap.get("priority", 2)]),
                "frequency": str(row[fmap.get("frequency", 3)]),
                "governing_skill": str(row[fmap.get("governing_skill", 4)]),
                "command_to_run": str(row[fmap.get("command_to_run", 5)]),
                "job_instructions": str(row[fmap.get("job_instructions", 6)]),
                "job_context_notes": str(row[fmap.get("job_context_notes", 7)]),
                "status": str(row[fmap.get("status", 8)]),
                "last_run_timestamp": str(row[fmap.get("last_run_timestamp", 9)]),
                "run_count": int(row[fmap.get("run_count", 10)] or 0),
                "last_result": str(row[fmap.get("last_result", 11)]),
                "tags": str(row[fmap.get("tags", 12)]),
                "standing": True,
            })
        return results

    def query_maintenance_jobs(self, term: str) -> List[Dict[str, Any]]:
        """Search maintenance jobs by keyword across id, name, skill, instructions, and tags."""
        term_clean = term.lower()
        return [
            j for j in self.list_maintenance_jobs()
            if term_clean in j["job_id"].lower()
            or term_clean in j["job_name"].lower()
            or term_clean in j["governing_skill"].lower()
            or term_clean in j["job_instructions"].lower()
            or term_clean in j["tags"].lower()
        ]

    def record_maintenance_run(self, job_id: str, result: str = "verified") -> Optional[Dict[str, Any]]:
        """
        Record verified execution of a standing maintenance job.
        Updates last_run_timestamp and increments run_count.
        NOTE: Maintenance jobs are NEVER marked completed; status remains 'standing'.
        """
        doc = self.get_maintenance_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("job_id", 0)
        time_idx = fmap.get("last_run_timestamp", 9)
        count_idx = fmap.get("run_count", 10)
        res_idx = fmap.get("last_result", 11)
        stat_idx = fmap.get("status", 8)

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        updated_job = None

        for row in doc.get("Values", []):
            if str(row[id_idx]).strip().lower() == job_id.strip().lower() or str(row[fmap.get("job_name", 1)]).strip().lower() == job_id.strip().lower():
                row[time_idx] = now_utc
                current_count = int(row[count_idx] or 0)
                row[count_idx] = current_count + 1
                row[res_idx] = result
                row[stat_idx] = "standing"  # Invariant: Never completed
                save_bejson_atomic(self.paths["MAINTENANCE_REGISTRY"], doc)
                updated_job = {
                    "job_id": str(row[id_idx]),
                    "job_name": str(row[fmap.get("job_name", 1)]),
                    "status": "standing",
                    "last_run_timestamp": now_utc,
                    "run_count": current_count + 1,
                    "last_result": result,
                }
                break

        return updated_job

    def check_pending_urgent_files(self) -> List[str]:
        """Scan JOBS_FOLDER for pending job files."""
        jobs_folder = self.paths["JOBS_FOLDER"]
        if jobs_folder.exists() and jobs_folder.is_dir():
            try:
                return [p.name for p in jobs_folder.iterdir() if not p.name.startswith(".") and p.name.upper() != "AGENTS.MD"]
            except Exception:
                pass
        return []

    # ── Job Selection & Resolution ───────────────────────────────────────────
    def select_job(self, query: str) -> Optional[Dict[str, Any]]:
        """Find job across active, completed, and saved stores, then lock into chamber."""
        query_clean = query.strip().lower()

        # Check Active Registry first
        active_list = self.list_active_jobs()
        for item in active_list:
            if query_clean in (item["job_id"].lower(), item["job_name"].lower(), str(item["index"])):
                self.lock_job(item["job_id"], item["job_name"], subdir=item["subdir"], file_path=item["job_file_path"])
                return item

        for item in active_list:
            if query_clean in item["job_name"].lower() or query_clean in item["job_id"].lower():
                self.lock_job(item["job_id"], item["job_name"], subdir=item["subdir"], file_path=item["job_file_path"])
                return item

        # Check Completed Registry
        completed_list = self.list_completed_jobs()
        for item in completed_list:
            if query_clean in (item["job_id"].lower(), item["job_name"].lower(), str(item["index"])):
                self.lock_job(item["job_id"], item["job_name"], subdir="completed", file_path=item["archive_file_path"])
                return item

        for item in completed_list:
            if query_clean in item["job_name"].lower():
                self.lock_job(item["job_id"], item["job_name"], subdir="completed", file_path=item["archive_file_path"])
                return item

        # Check saved files
        saved_list = self.list_saved_files()
        for item in saved_list:
            if query_clean in (item["filename"].lower(), Path(item["filename"]).stem.lower(), str(item["index"])):
                self.lock_job(item["filename"], item["filename"], subdir="saved", file_path=item["path"])
                return item

        return None

    def get_loaded_job_record(self) -> Optional[Dict[str, Any]]:
        """Retrieve full dictionary of the currently loaded chamber job."""
        job_id, _, subdir = self.get_loaded_job_info()
        if not job_id:
            return None

        if subdir == "completed":
            for item in self.list_completed_jobs():
                if item["job_id"] == job_id or item["job_name"] == job_id:
                    return item
        else:
            for item in self.list_active_jobs():
                if item["job_id"] == job_id or item["job_name"] == job_id:
                    return item

        # Fallback check both
        for item in self.list_active_jobs() + self.list_completed_jobs():
            if item["job_id"] == job_id or item["job_name"] == job_id:
                return item

        return None

    # ── Job Creation ─────────────────────────────────────────────────────────
    def create_job(
        self,
        name: str,
        instructions: str = "",
        context_notes: str = "",
        priority: str = "normal",
        status: str = "active",
        tasks: Optional[List[str]] = None,
        tags: str = "",
    ) -> Dict[str, Any]:
        """Create new job, record in active registry, and lock into chamber."""
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        job_id = f"job_{timestamp_slug}"

        task_records: List[Dict[str, Any]] = []
        if tasks:
            for idx, t_name in enumerate(tasks, 1):
                task_records.append({
                    "task_id": str(uuid.uuid4())[:8],
                    "task_order": idx,
                    "task_name": t_name.strip(),
                    "task_description": "",
                    "task_completed": False,
                })

        tasks_json = json.dumps(task_records)
        target_dir = self.paths["JOBS_FOLDER"] if status.lower() == "active" else self.paths["SAVED_JOBS"]
        job_file_name = f"{job_id}_{name.replace(' ', '_')[:32]}.bejson"
        job_file_path = target_dir / job_file_name

        # Create canonical individual job document
        job_doc = {
            "Format": "BEJSON",
            "Format_Version": "104a",
            "Format_Creator": "Elton Boehnen",
            "Schema_Name": "Job Document Schema",
            "Schema_Version": "1.0.0",
            "Records_Type": ["JobTask"],
            "Job_Id": job_id,
            "Job_Name": name,
            "Job_Instructions": instructions,
            "Job_Context_Notes": context_notes,
            "Job_Priority": priority.lower(),
            "Job_Status": status.lower(),
            "Creation_Date": current_date,
            "Job_Complete": False,
            "Fields": [
                {"name": "task_id", "type": "string"},
                {"name": "task_order", "type": "integer"},
                {"name": "task_name", "type": "string"},
                {"name": "task_description", "type": "string"},
                {"name": "task_completed", "type": "boolean"},
            ],
            "Values": [[t["task_id"], t["task_order"], t["task_name"], t["task_description"], t["task_completed"]] for t in task_records],
        }
        save_bejson_atomic(job_file_path, job_doc)

        # Append to Active Registry
        doc = self.get_active_registry()
        doc.get("Values", []).append([
            job_id,
            name,
            priority.lower(),
            status.lower(),
            current_date,
            "Elton Boehnen",
            instructions,
            context_notes,
            len(task_records),
            0,
            tasks_json,
            str(job_file_path),
            tags,
        ])
        save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], doc)

        # Lock into chamber
        subdir_name = "active" if status.lower() == "active" else "saved"
        self.lock_job(job_id, name, subdir=subdir_name, file_path=str(job_file_path))

        return {
            "job_id": job_id,
            "job_name": name,
            "priority": priority.lower(),
            "status": status.lower(),
            "job_file_path": str(job_file_path),
            "subdir": subdir_name,
        }

    # ── Job Status & Priority Mutation ───────────────────────────────────────
    def set_job_status(self, new_status: str, target_id: Optional[str] = None) -> bool:
        """Update job status and move between Jobs/ and saved_jobs/ accordingly."""
        target = target_id or self.get_loaded_job_info()[0]
        if not target:
            return False

        doc = self.get_active_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("job_id", 0)
        status_idx = fmap.get("status", 3)
        path_idx = fmap.get("job_file_path", 11)

        found = False
        new_subdir = "active" if new_status.lower() == "active" else "saved"

        for row in doc.get("Values", []):
            if str(row[id_idx]).lower() == target.lower():
                row[status_idx] = new_status.lower()
                current_path = Path(str(row[path_idx]))
                if current_path.exists():
                    target_dir = self.paths["JOBS_FOLDER"] if new_subdir == "active" else self.paths["SAVED_JOBS"]
                    new_path = target_dir / current_path.name
                    if current_path.resolve() != new_path.resolve():
                        shutil.move(current_path, new_path)
                        row[path_idx] = str(new_path)
                found = True
                save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], doc)
                # Update chamber if this was loaded
                cur_id, cur_name, _ = self.get_loaded_job_info()
                if cur_id == target or cur_name == target:
                    self.lock_job(str(row[id_idx]), str(row[fmap.get("job_name", 1)]), subdir=new_subdir, file_path=str(row[path_idx]))
                break

        return found

    def set_job_priority(self, new_priority: str, target_id: Optional[str] = None) -> bool:
        """Update job priority in active registry and document."""
        target = target_id or self.get_loaded_job_info()[0]
        if not target:
            return False

        doc = self.get_active_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("job_id", 0)
        prio_idx = fmap.get("priority", 2)

        for row in doc.get("Values", []):
            if str(row[id_idx]).lower() == target.lower():
                row[prio_idx] = new_priority.lower()
                save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], doc)
                return True

        return False

    # ── Task Operations ──────────────────────────────────────────────────────
    def add_task(self, task_title: str, task_desc: str = "", target_id: Optional[str] = None) -> bool:
        """Add task to job's tasks_json and increment task_count."""
        target = target_id or self.get_loaded_job_info()[0]
        if not target:
            return False

        doc = self.get_active_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("job_id", 0)
        tcount_idx = fmap.get("task_count", 8)
        tjson_idx = fmap.get("tasks_json", 10)

        for row in doc.get("Values", []):
            if str(row[id_idx]).lower() == target.lower():
                try:
                    tasks_list = json.loads(str(row[tjson_idx]) or "[]")
                except Exception:
                    tasks_list = []
                new_order = len(tasks_list) + 1
                tasks_list.append({
                    "task_id": str(uuid.uuid4())[:8],
                    "task_order": new_order,
                    "task_name": task_title.strip(),
                    "task_description": task_desc.strip(),
                    "task_completed": False,
                })
                row[tjson_idx] = json.dumps(tasks_list)
                row[tcount_idx] = len(tasks_list)
                save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], doc)
                return True

        return False

    def toggle_task(self, order_or_id: str, target_id: Optional[str] = None) -> Optional[bool]:
        """Toggle task completion state in tasks_json."""
        target = target_id or self.get_loaded_job_info()[0]
        if not target:
            return None

        doc = self.get_active_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("job_id", 0)
        tdone_idx = fmap.get("tasks_completed", 9)
        tjson_idx = fmap.get("tasks_json", 10)

        for row in doc.get("Values", []):
            if str(row[id_idx]).lower() == target.lower():
                try:
                    tasks_list = json.loads(str(row[tjson_idx]) or "[]")
                except Exception:
                    tasks_list = []

                toggled_state: Optional[bool] = None
                done_count = 0

                for t in tasks_list:
                    if str(t.get("task_order")) == str(order_or_id) or str(t.get("task_id")) == str(order_or_id):
                        t["task_completed"] = not t.get("task_completed", False)
                        toggled_state = t["task_completed"]
                    if t.get("task_completed"):
                        done_count += 1

                if toggled_state is not None:
                    row[tjson_idx] = json.dumps(tasks_list)
                    row[tdone_idx] = done_count
                    save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], doc)
                    return toggled_state

        return None

    # ── Mark Complete (Moving it IS marking it complete!) ─────────────────────
    def complete_job(
        self,
        resolution_summary: str = "Job completed successfully.",
        artifacts: str = "",
        target_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Mark job complete:
          - Extract from active registry
          - Mark all tasks complete
          - Move file to Completed_Jobs/
          - Record in completed_jobs_registry.104a.bejson
          - Update chamber to subdir='completed' or clear
        """
        target = target_id or self.get_loaded_job_info()[0]
        if not target:
            return None

        active_doc = self.get_active_registry()
        fmap = compile_bejson_field_map(active_doc)
        id_idx = fmap.get("job_id", 0)

        target_row: Optional[List[Any]] = None
        remaining_values: List[List[Any]] = []

        for row in active_doc.get("Values", []):
            if str(row[id_idx]).lower() == target.lower() and target_row is None:
                target_row = row
            else:
                remaining_values.append(row)

        if not target_row:
            return None

        active_doc["Values"] = remaining_values
        save_bejson_atomic(self.paths["ACTIVE_REGISTRY"], active_doc)

        # Move underlying file to Completed_Jobs/
        original_path_str = str(target_row[fmap.get("job_file_path", 11)])
        original_path = Path(original_path_str) if original_path_str else None
        archive_dest_path = ""

        if original_path and original_path.exists():
            dest_file = self.paths["COMPLETED_JOBS_FOLDER"] / original_path.name
            shutil.move(original_path, dest_file)
            archive_dest_path = str(dest_file)

        # Complete tasks in tasks_json
        try:
            tasks_list = json.loads(str(target_row[fmap.get("tasks_json", 10)]) or "[]")
            for t in tasks_list:
                t["task_completed"] = True
            updated_tasks_json = json.dumps(tasks_list)
        except Exception:
            updated_tasks_json = str(target_row[fmap.get("tasks_json", 10)])

        completion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Record into Completed Registry
        completed_doc = self.get_completed_registry()
        completed_doc.get("Values", []).append([
            str(target_row[fmap.get("job_id", 0)]),
            str(target_row[fmap.get("job_name", 1)]),
            str(target_row[fmap.get("priority", 2)]),
            str(target_row[fmap.get("creation_date", 4)]),
            completion_date,
            0,
            "Elton Boehnen",
            resolution_summary,
            artifacts,
            str(target_row[fmap.get("job_instructions", 6)]),
            str(target_row[fmap.get("job_context_notes", 7)]),
            updated_tasks_json,
            archive_dest_path,
            str(target_row[fmap.get("tags", 12)]),
        ])
        save_bejson_atomic(self.paths["COMPLETED_REGISTRY"], completed_doc)

        # Persist completed state in chamber
        self.lock_job(str(target_row[fmap.get("job_id", 0)]), str(target_row[fmap.get("job_name", 1)]), subdir="completed", file_path=archive_dest_path)

        return {
            "job_id": str(target_row[fmap.get("job_id", 0)]),
            "job_name": str(target_row[fmap.get("job_name", 1)]),
            "completion_date": completion_date,
            "resolution_summary": resolution_summary,
            "archive_path": archive_dest_path,
        }

    # ── Search & Legacy Migration ────────────────────────────────────────────
    def query_jobs(self, term: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search term across active and completed job registries."""
        term_clean = term.lower()
        active_matches = [
            j for j in self.list_active_jobs()
            if term_clean in j["job_name"].lower() or term_clean in j["job_instructions"].lower() or term_clean in j["job_context_notes"].lower() or term_clean in j["tags"].lower()
        ]
        completed_matches = [
            j for j in self.list_completed_jobs()
            if term_clean in j["job_name"].lower() or term_clean in j["resolution_summary"].lower() or term_clean in j["job_instructions"].lower()
        ]
        return {"active": active_matches, "completed": completed_matches}

    def migrate_legacy_completed_jobs(self) -> int:
        """Scan loose files in Completed_Jobs/ and register them in completed_jobs_registry."""
        completed_doc = self.get_completed_registry()
        fmap = compile_bejson_field_map(completed_doc)
        existing_names = {str(row[fmap.get("job_name", 1)]) for row in completed_doc.get("Values", [])}

        migrated_count = 0
        comp_folder = self.paths["COMPLETED_JOBS_FOLDER"]

        for entry in sorted(comp_folder.iterdir()):
            if entry.name == "completed_jobs_registry.104a.bejson" or entry.name.startswith("."):
                continue

            job_title = entry.stem if entry.is_file() else entry.name
            if job_title in existing_names:
                continue

            content_text = ""
            if entry.is_file():
                try:
                    content_text = entry.read_text(encoding="utf-8")
                except Exception:
                    pass

            c_date = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            synthetic_id = f"job_legacy_{len(completed_doc.get('Values', [])) + 1:03d}"

            completed_doc.get("Values", []).append([
                synthetic_id,
                job_title,
                "normal",
                c_date,
                c_date,
                0,
                "Elton Boehnen",
                f"Historical job migrated from {entry.name}",
                "",
                content_text[:500],
                "",
                "[]",
                str(entry),
                "legacy,migrated",
            ])
            migrated_count += 1

        if migrated_count > 0:
            save_bejson_atomic(self.paths["COMPLETED_REGISTRY"], completed_doc)

        return migrated_count


# ── Terminal Display Formatting (Policy §8.1 Tri-Color) ───────────────────────
def print_status_banner(engine: JobManagerEngine) -> None:
    """Print high-density 57-column chamber status banner."""
    job_id, job_name, subdir = engine.get_loaded_job_info()
    loaded_record = engine.get_loaded_job_record()

    print(DIVIDER_57)
    print(f" {ACCENT}JOB MANAGEMENT CHAMBER [BEJSON 104a]{RESET}")
    print(SUBDIVIDER_57)
    if not job_id:
        print(f" {ACCENT}LOCKED JOB:{RESET}  (none - chamber empty)")
        print(f" {ACCENT}SUBDIR:{RESET}      (none)")
        print(f" {DIM}Use --list to view jobs, --select <id> to lock chamber.{RESET}")
    else:
        status_str = loaded_record.get("status", "").upper() if loaded_record else ""
        prio_str = loaded_record.get("priority", "").upper() if loaded_record else ""
        display_title = (job_name or job_id)[:36]

        print(f" {ACCENT}LOCKED JOB:{RESET}  {display_title}")
        print(f" {ACCENT}ID:{RESET}          {job_id}")
        print(f" {ACCENT}SUBDIR:{RESET}      [{subdir or 'active'}]")
        if status_str:
            print(f" {ACCENT}STATUS:{RESET}      [{status_str}]  {ACCENT}PRIORITY:{RESET} [{prio_str}]")
        if loaded_record and loaded_record.get("task_count"):
            print(f" {ACCENT}PROGRESS:{RESET}    {loaded_record.get('tasks_completed', 0)}/{loaded_record.get('task_count', 0)} tasks complete")

    print(DIVIDER_57)


def print_active_jobs_table(jobs: List[Dict[str, Any]], active_job_id: Optional[str] = None) -> None:
    """Print 57-column table of active registry jobs."""
    print(DIVIDER_57)
    print(f" {ACCENT}ACTIVE JOBS REGISTRY (job_registry.104a.bejson){RESET}")
    print(SUBDIVIDER_57)
    if not jobs:
        print(f" {DIM}No active jobs in registry.{RESET}")
        print(f" {DIM}Create one with: --new -n <name> -i <instructions>{RESET}")
    else:
        print(f" {ACCENT}{'#':<3} {'STATUS':<9} {'PRIO':<7} {'TASKS':<7} {'NAME'}{RESET}")
        print(SUBDIVIDER_57)
        for j in jobs:
            is_locked = (j["job_id"] == active_job_id or j["job_name"] == active_job_id)
            marker = f"{ACCENT}*{RESET}" if is_locked else " "
            idx_label = f"{j['index']}{marker}"
            stat_label = f"[{j['status'][:7]}]"
            prio_label = j["priority"][:6]
            progress = f"{j['tasks_completed']}/{j['task_count']}"
            name_label = j["job_name"][:26]
            print(f" {idx_label:<4} {stat_label:<9} {prio_label:<7} {progress:<7} {name_label}")
    print(DIVIDER_57)


def print_completed_jobs_table(jobs: List[Dict[str, Any]]) -> None:
    """Print 57-column table of completed registry jobs."""
    print(DIVIDER_57)
    print(f" {ACCENT}COMPLETED JOBS REGISTRY{RESET}")
    print(SUBDIVIDER_57)
    if not jobs:
        print(f" {DIM}No completed jobs registered yet.{RESET}")
        print(f" {DIM}Mark complete via: --complete-job -m \"summary\"{RESET}")
    else:
        print(f" {ACCENT}{'#':<3} {'DATE':<10} {'NAME':<24} {'SUMMARY'}{RESET}")
        print(SUBDIVIDER_57)
        for j in jobs:
            idx_str = f"{j['index']:<3}"
            date_str = j["completion_date"][:10]
            name_str = j["job_name"][:23]
            summ_str = j["resolution_summary"][:16]
            print(f" {idx_str} {date_str:<10} {name_str:<24} {summ_str}")
    print(DIVIDER_57)


def print_job_card(record: Dict[str, Any]) -> None:
    """Render full 57-column job card."""
    print(DIVIDER_57)
    print(f" {ACCENT}JOB:{RESET} {record.get('job_name', '(unnamed)')}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}ID:{RESET}           {record.get('job_id')}")
    print(f" {ACCENT}Subdirectory:{RESET} [{record.get('subdir', 'active')}]")
    if record.get("status"):
        print(f" {ACCENT}Status:{RESET}       {record.get('status').upper()}")
    if record.get("priority"):
        print(f" {ACCENT}Priority:{RESET}     {record.get('priority').upper()}")
    print(f" {ACCENT}Created:{RESET}      {record.get('creation_date')}")
    if record.get("completion_date"):
        print(f" {ACCENT}Completed:{RESET}    {record.get('completion_date')}")
    if record.get("resolution_summary"):
        print(f" {ACCENT}Resolution:{RESET}   {record.get('resolution_summary')}")

    if record.get("job_instructions"):
        print(SUBDIVIDER_57)
        print(f" {ACCENT}INSTRUCTIONS:{RESET}")
        for line in record["job_instructions"].splitlines()[:15]:
            print(f"  {line[:53]}")

    if record.get("job_context_notes"):
        print(SUBDIVIDER_57)
        print(f" {ACCENT}CONTEXT NOTES:{RESET}")
        for line in record["job_context_notes"].splitlines()[:10]:
            print(f"  {line[:53]}")

    try:
        tasks = json.loads(record.get("tasks_json", "[]"))
        if tasks:
            print(SUBDIVIDER_57)
            print(f" {ACCENT}TASKS ({record.get('tasks_completed', 0)}/{len(tasks)} complete):{RESET}")
            for t in tasks:
                chk = f"[{ACCENT}✓{RESET}]" if t.get("task_completed") else "[ ]"
                ord_n = t.get("task_order", "?")
                t_title = t.get("task_name", "(unnamed)")[:42]
                print(f"  {chk} Step {ord_n}: {t_title}")
    except Exception:
        pass

    print(DIVIDER_57)


def print_maintenance_jobs_table(jobs: List[Dict[str, Any]]) -> None:
    """Print 57-column table of standing recurring maintenance jobs."""
    print(DIVIDER_57)
    print(f" {ACCENT}MAINTENANCE JOBS REGISTRY [STANDING RECURRING]{RESET}")
    print(SUBDIVIDER_57)
    if not jobs:
        print(f" {DIM}No maintenance jobs registered.{RESET}")
    else:
        print(f" {ACCENT}{'#':<3} {'PRIO':<7} {'STATUS':<9} {'FREQ':<9} {'NAME'}{RESET}")
        print(SUBDIVIDER_57)
        for j in jobs:
            idx_str = f"{j['index']:<3}"
            prio_str = j['priority'][:6]
            stat_str = f"[{j['status'][:7]}]"
            freq_str = j['frequency'][:8]
            name_str = j['job_name'][:22]
            print(f" {idx_str} {prio_str:<7} {stat_str:<9} {freq_str:<9} {name_str}")
            print(f"     {DIM}Cmd: {j['command_to_run'][:48]}{RESET}")
            if j.get("last_run_timestamp"):
                print(f"     {DIM}Last: {j['last_run_timestamp'][:19]} | Runs: {j.get('run_count', 0)} | Res: {j.get('last_result', 'pending')}{RESET}")
    print(DIVIDER_57)


def print_init_check(engine: JobManagerEngine) -> None:
    """High-density composite initialization audit for AI agents on session start."""
    print(DIVIDER_57)
    print(f" {ACCENT}SESSION STARTUP AUDIT & INITIALIZATION DIRECTIVES{RESET}")
    print(SUBDIVIDER_57)

    # 1. Urgent Jobs Queue Check
    pending_files = engine.check_pending_urgent_files()
    if pending_files:
        print(f" {ACCENT}[!] URGENT JOBS PENDING ({len(pending_files)}):{RESET}")
        for pf in pending_files:
            print(f"     • {pf}")
        print(f"     {BOLD}Directive:{RESET} Process pending job start-to-finish without stopping!")
    else:
        print(f" {ACCENT}[✓] Urgent Jobs Queue:{RESET} Clean (0 pending files in $JOBS_FOLDER)")

    # 2. Chamber Status
    job_id, job_name, subdir = engine.get_loaded_job_info()
    if job_id:
        print(f" {ACCENT}[*] Loaded Chamber:{RESET} {job_name or job_id} [{subdir}]")
    else:
        print(f" {ACCENT}[*] Loaded Chamber:{RESET} None (chamber unlocked)")

    print(SUBDIVIDER_57)

    # 3. Standing Maintenance Jobs
    maint_jobs = engine.list_maintenance_jobs()
    print(f" {ACCENT}STANDING MAINTENANCE JOBS ({len(maint_jobs)}):{RESET}")
    print(f" {DIM}(Never completed; executed/verified on session start){RESET}")
    print(SUBDIVIDER_57)
    for j in maint_jobs:
        run_txt = f"{j['run_count']} runs" if j['run_count'] > 0 else "never run"
        last_dt = j['last_run_timestamp'][:10] if j.get('last_run_timestamp') else "never"
        print(f"  [{j['priority'].upper()[:4]}] {j['job_id']}: {j['job_name']}")
        print(f"        Skill : {j['governing_skill']}")
        print(f"        Cmd   : {j['command_to_run'][:45]}")
        print(f"        Status: {j['status']} | Last: {last_dt} ({run_txt}) | Result: {j['last_result']}")
    print(DIVIDER_57)


def emit_agent_context_json(engine: JobManagerEngine) -> None:
    """Emit machine-readable JSON context of active jobs, maintenance jobs, and paths."""
    context = {
        "engine": "JobManagerEngine",
        "version": "1.7.0",
        "paths": {k: str(v) for k, v in engine.paths.items()},
        "loaded_chamber": {
            "job_id": engine.get_loaded_job_info()[0],
            "job_name": engine.get_loaded_job_info()[1],
            "subdir": engine.get_loaded_job_info()[2],
        },
        "pending_urgent_files": engine.check_pending_urgent_files(),
        "active_jobs": engine.list_active_jobs(),
        "maintenance_jobs": engine.list_maintenance_jobs(),
    }
    print(json.dumps(context, indent=2))


def print_ai_optimized_help() -> None:
    """Print high-density, structured, AI-optimized command specification."""
    print(DIVIDER_57)
    print(f" {ACCENT}JOB MANAGEMENT TOOL - AI-OPTIMIZED COMMAND SPECIFICATION{RESET}")
    print(SUBDIVIDER_57)
    print("ENTRYPOINTS:")
    print("  python3 /storage/emulated/0/Admin/System/tools/management_tool/job_tool.py [FLAGS]")
    print("  bash /storage/emulated/0/Admin/System/tools/management_tool/management.sh job [FLAGS]")
    print()
    print(f"{ACCENT}PHASE 0: SESSION INIT & STANDING MAINTENANCE (Never Completed){RESET}")
    print("  --init-check                 Composite startup check: urgent jobs + maint")
    print("  --maintenance                List all standing maintenance jobs")
    print("  --query-maintenance <TERM>   Search maintenance jobs by keyword or skill")
    print("  --record-maintenance <ID>    Record run timestamp and increment run count")
    print("  --maintenance-result <CODE>  Result status (verified|clean|drift_detected)")
    print()
    print(f"{ACCENT}PHASE 1: DISCOVERY & REGISTRY QUERIES{RESET}")
    print("  --list, -l                   List active queued jobs in registry")
    print("  --list-completed             List archived completed jobs in registry")
    print("  --list-saved                 List draft/saved job files")
    print("  --query, -q <TERM>           Search active and completed registries")
    print("  --status                     Print 57-column chamber status banner")
    print()
    print(f"{ACCENT}PHASE 2: LOADED CHAMBER TARGET LOCK{RESET}")
    print("  --select, -s <TARGET>        Lock chamber by index, ID, or job name")
    print("  --clear                      Clear loaded chamber target lock")
    print()
    print(f"{ACCENT}PHASE 3: EXECUTION ON LOADED CHAMBER{RESET}")
    print("  --view                       View full job card with instructions & tasks")
    print("  --set-priority <LEVEL>       urgent | high | normal | low")
    print("  --set-status <STATUS>        active | inactive | pending | paused")
    print("  --activate                   Move to active queue & $JOBS_FOLDER")
    print("  --deactivate                 Move to inactive & saved_jobs/")
    print("  --add-task <TITLE>           Append task to loaded job")
    print("  --task-desc <TEXT>           Description for new task")
    print("  --toggle-task <ORDER|ID>     Toggle step completion status")
    print("  --complete-job               Archive to $COMPLETED_JOBS_FOLDER & update registry")
    print("  -m, --summary <TEXT>         Resolution summary for completed job")
    print("  --artifacts <PATHS>          Comma-separated artifact paths produced")
    print()
    print(f"{ACCENT}PHASE 4: CREATION & INGESTION{RESET}")
    print("  --new -n <NAME>              Create new job (requires -n/--name)")
    print("  -i <INSTRUCTIONS>            Job execution instructions")
    print("  --notes <CONTEXT>            Context notes, paths, constraints")
    print("  --priority <LEVEL>           Job priority (default: normal)")
    print("  --tasks <T1,T2,...>          Comma-separated initial task list")
    print("  --migrate-legacy             Ingest loose completed files into registry")
    print()
    print(f"{ACCENT}AI CONTEXT DIRECTIVES:{RESET}")
    print("  --agent-context, --ai-help   Emit machine-readable JSON context state")
    print(DIVIDER_57)


# ── CLI Parser ───────────────────────────────────────────────────────────────
def build_argument_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for Job Manager."""
    parser = argparse.ArgumentParser(
        prog="job_tool.py",
        description="Authoritative BEJSON 104a Job Manager & Registry CLI (Mode 4).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Phase 0: Session Init & Maintenance
    maint_grp = parser.add_argument_group("Phase 0: Session Initialization & Maintenance (Standing)")
    maint_grp.add_argument("--maintenance", "--list-maintenance", action="store_true", help="List standing recurring maintenance jobs (never completed)")
    maint_grp.add_argument("--query-maintenance", metavar="TERM", help="Search standing maintenance jobs by keyword or skill")
    maint_grp.add_argument("--record-maintenance", metavar="JOB_ID", help="Record verified execution of a maintenance job (updates run count & timestamp)")
    maint_grp.add_argument("--maintenance-result", default="verified", help="Result code for maintenance record (default: verified)")
    maint_grp.add_argument("--init-check", action="store_true", help="Composite session startup check: urgent jobs, staged downloads, & standing maintenance")
    maint_grp.add_argument("--agent-context", "--ai-help", action="store_true", help="Emit high-density AI-optimized context & command specification")

    # Discovery
    disc_grp = parser.add_argument_group("Phase 1: Discovery")
    disc_grp.add_argument("--list", "--list-jobs", "--list-active", "-l", action="store_true", help="List active & queued jobs in registry")
    disc_grp.add_argument("--list-completed", action="store_true", help="List archived completed jobs in registry")
    disc_grp.add_argument("--list-saved", action="store_true", help="List draft/saved job files")
    disc_grp.add_argument("--status", action="store_true", help="Display 57-column chamber status banner")
    disc_grp.add_argument("--query", "-q", metavar="TERM", help="Search across active and completed job registries")

    # Chamber Lock
    lock_grp = parser.add_argument_group("Phase 2: Target Lock (Loaded Chamber)")
    lock_grp.add_argument("--select", "--select-job", "-s", metavar="TARGET", help="Lock job into chamber by index, name, or ID")
    lock_grp.add_argument("--clear", "--clear-job", action="store_true", help="Clear chamber target lock")

    # Chamber Actions
    act_grp = parser.add_argument_group("Phase 3: Execution Actions on Loaded Chamber")
    act_grp.add_argument("--view", "--view-job", action="store_true", help="View full card of loaded job (or specify target)")
    act_grp.add_argument("--set-priority", "-p", choices=["urgent", "high", "normal", "low"], help="Set priority of loaded job")
    act_grp.add_argument("--set-status", choices=["active", "inactive", "pending", "paused"], help="Set status of loaded job")
    act_grp.add_argument("--activate", action="store_true", help="Activate job (ensures in active registry & Jobs/)")
    act_grp.add_argument("--deactivate", action="store_true", help="Deactivate job (marks inactive in saved_jobs/)")
    act_grp.add_argument("--add-task", metavar="TITLE", help="Append new task to loaded job")
    act_grp.add_argument("--task-desc", default="", help="Description for new task")
    act_grp.add_argument("--toggle-task", metavar="ORDER", help="Toggle completion of task by step order or ID")
    act_grp.add_argument("--complete-job", "--mark-complete", action="store_true", help="Mark job complete: archive to Completed_Jobs & update completed registry")
    act_grp.add_argument("-m", "--summary", default="Completed successfully.", help="Resolution summary for completed job")
    act_grp.add_argument("--artifacts", default="", help="Artifacts produced by completed job")

    # Creation & Ingestion
    creat_grp = parser.add_argument_group("Phase 4: Creation & Ingestion")
    creat_grp.add_argument("--new", "--create-job", action="store_true", help="Create a new job in registry")
    creat_grp.add_argument("-n", "--name", metavar="NAME", help="Name/title for the new job")
    creat_grp.add_argument("-i", "--instructions", metavar="TEXT", help="Detailed actionable instructions for the job")
    creat_grp.add_argument("--notes", metavar="TEXT", help="Context notes (paths, references, requirements)")
    creat_grp.add_argument("--priority", choices=["urgent", "high", "normal", "low"], default="normal", help="Job priority (default: normal)")
    creat_grp.add_argument("--status-val", dest="new_status", choices=["active", "inactive", "pending"], default="active", help="Initial job status (default: active)")
    creat_grp.add_argument("--tasks", metavar="T1,T2...", help="Comma-separated initial tasks list")
    creat_grp.add_argument("--tags", default="", help="Comma-separated search tags")
    creat_grp.add_argument("--migrate-legacy", action="store_true", help="Scan loose completed jobs and index into completed registry")

    return parser


# ── Main Entrypoint ──────────────────────────────────────────────────────────
def main() -> int:
    """Execute Job Manager CLI routine."""
    engine = JobManagerEngine()

    if any(h in sys.argv[1:] for h in ("-h", "--help")):
        print_ai_optimized_help()
        return 0

    if any(a in sys.argv[1:] for a in ("--agent-context", "--ai-help")):
        emit_agent_context_json(engine)
        return 0

    parser = build_argument_parser()
    args = parser.parse_args()

    # Default to status if no arguments
    if len(sys.argv) == 1:
        print_status_banner(engine)
        print()
        print_ai_optimized_help()
        return 0

    # 0. Session Initialization & Maintenance
    if args.init_check:
        print_init_check(engine)
        return 0

    if args.maintenance:
        jobs = engine.list_maintenance_jobs()
        print_maintenance_jobs_table(jobs)
        return 0

    if args.query_maintenance:
        jobs = engine.query_maintenance_jobs(args.query_maintenance)
        print_maintenance_jobs_table(jobs)
        return 0

    if args.record_maintenance:
        rec = engine.record_maintenance_run(args.record_maintenance, result=args.maintenance_result)
        if rec:
            print(DIVIDER_57)
            print(f" {ACCENT}[✓] MAINTENANCE RUN RECORDED (STANDING){RESET}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}Job ID:{RESET}     {rec['job_id']}")
            print(f" {ACCENT}Job Name:{RESET}   {rec['job_name']}")
            print(f" {ACCENT}Status:{RESET}     [{rec['status'].upper()}] (perpetual standing)")
            print(f" {ACCENT}Run Count:{RESET}  {rec['run_count']}")
            print(f" {ACCENT}Timestamp:{RESET}  {rec['last_run_timestamp']}")
            print(f" {ACCENT}Result:{RESET}     {rec['last_result']}")
            print(DIVIDER_57)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} Maintenance job '{args.record_maintenance}' not found in registry.", file=sys.stderr)
            return 1

    # 1. Status & Discovery
    if args.status:
        print_status_banner(engine)
        return 0

    if args.list:
        jobs = engine.list_active_jobs()
        cur_id, cur_name, _ = engine.get_loaded_job_info()
        print_active_jobs_table(jobs, cur_id or cur_name)
        return 0

    if args.list_completed:
        jobs = engine.list_completed_jobs()
        print_completed_jobs_table(jobs)
        return 0

    if args.list_saved:
        files = engine.list_saved_files()
        print(DIVIDER_57)
        print(f" {ACCENT}SAVED DRAFT JOBS & TEMPLATES{RESET}")
        print(SUBDIVIDER_57)
        if not files:
            print(f" {DIM}No draft job files in data/saved_jobs/{RESET}")
        else:
            for f in files:
                print(f" {f['index']:<3} {f['filename']} ({f['size']} bytes)")
        print(DIVIDER_57)
        return 0

    if args.query:
        res = engine.query_jobs(args.query)
        print(DIVIDER_57)
        print(f" {ACCENT}JOB QUERY RESULTS:{RESET} '{args.query}'")
        print(SUBDIVIDER_57)
        print(f" {BOLD}Active Matches ({len(res['active'])}):{RESET}")
        for j in res["active"]:
            print(f"  • [{j['priority'].upper()}] {j['job_name']} ({j['job_id']})")
        print(f" {BOLD}Completed Matches ({len(res['completed'])}):{RESET}")
        for j in res["completed"]:
            print(f"  • {j['job_name']} - {j['resolution_summary'][:30]} ({j['completion_date'][:10]})")
        print(DIVIDER_57)
        return 0

    # 2. Chamber Selection & Clearing
    if args.select:
        match = engine.select_job(args.select)
        if match:
            print(f"{ACCENT}[✓] Chamber Locked:{RESET} {match.get('job_name', match.get('filename'))}")
            print_status_banner(engine)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} No job matched query '{args.select}'.", file=sys.stderr)
            return 1

    if args.clear:
        engine.clear_chamber()
        print(f"{ACCENT}[✓] Chamber target cleared.{RESET}")
        return 0

    # 3. Creation
    if args.new:
        if not args.name:
            print(f"{ACCENT}[✗] Error:{RESET} Flag -n/--name is required to create a new job.", file=sys.stderr)
            return 1

        t_list = [t.strip() for t in args.tasks.split(",") if t.strip()] if args.tasks else []
        created = engine.create_job(
            name=args.name,
            instructions=args.instructions or "",
            context_notes=args.notes or "",
            priority=args.priority or "normal",
            status=args.new_status or "active",
            tasks=t_list,
            tags=args.tags or "",
        )
        print(f"{ACCENT}[✓] Created and locked into chamber:{RESET} {created['job_name']} ({created['job_id']})")
        loaded = engine.get_loaded_job_record()
        if loaded:
            print_job_card(loaded)
        return 0

    # 4. View Loaded Job
    if args.view:
        rec = engine.get_loaded_job_record()
        if not rec:
            print(f"{ACCENT}[✗] Error:{RESET} No job loaded in chamber. Use --select <id> first.", file=sys.stderr)
            return 1
        print_job_card(rec)
        return 0

    # 5. Status & Priority Mutation
    if args.set_status:
        success = engine.set_job_status(args.set_status)
        if success:
            print(f"{ACCENT}[✓] Job status updated to:{RESET} [{args.set_status.upper()}]")
            print_status_banner(engine)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Could not update status. Check loaded chamber.", file=sys.stderr)
        return 1

    if args.activate:
        success = engine.set_job_status("active")
        if success:
            print(f"{ACCENT}[✓] Job activated and moved to active queue!{RESET}")
            print_status_banner(engine)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Could not activate job. Check loaded chamber.", file=sys.stderr)
        return 1

    if args.deactivate:
        success = engine.set_job_status("inactive")
        if success:
            print(f"{ACCENT}[✓] Job deactivated and moved to saved drafts.{RESET}")
            print_status_banner(engine)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Could not deactivate job. Check loaded chamber.", file=sys.stderr)
        return 1

    if args.set_priority:
        success = engine.set_job_priority(args.set_priority)
        if success:
            print(f"{ACCENT}[✓] Job priority updated to:{RESET} [{args.set_priority.upper()}]")
            print_status_banner(engine)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Could not update priority. Check loaded chamber.", file=sys.stderr)
        return 1

    # 6. Task Management
    if args.add_task:
        success = engine.add_task(args.add_task, args.task_desc)
        if success:
            print(f"{ACCENT}[✓] Task added successfully:{RESET} {args.add_task}")
            rec = engine.get_loaded_job_record()
            if rec:
                print_job_card(rec)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Failed to add task. Check loaded chamber.", file=sys.stderr)
        return 1

    if args.toggle_task:
        state = engine.toggle_task(args.toggle_task)
        if state is not None:
            status_text = "Completed" if state else "Pending"
            print(f"{ACCENT}[✓] Task toggled to:{RESET} [{status_text}]")
            rec = engine.get_loaded_job_record()
            if rec:
                print_job_card(rec)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Task '{args.toggle_task}' not found in loaded job.", file=sys.stderr)
        return 1

    # 7. Complete Job (Moving it IS marking it complete!)
    if args.complete_job:
        res = engine.complete_job(
            resolution_summary=args.summary,
            artifacts=args.artifacts,
        )
        if res:
            print(DIVIDER_57)
            print(f" {ACCENT}[✓] JOB COMPLETED & ARCHIVED{RESET}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}JOB:{RESET}        {res['job_name']} ({res['job_id']})")
            print(f" {ACCENT}COMPLETED:{RESET}  {res['completion_date']}")
            print(f" {ACCENT}RESOLUTION:{RESET} {res['resolution_summary']}")
            if res.get("archive_path"):
                print(f" {ACCENT}ARCHIVED TO:{RESET} {res['archive_path']}")
            print(SUBDIVIDER_57)
            print(f" {DIM}Moved from active to completed_jobs_registry.104a.bejson.{RESET}")
            print(DIVIDER_57)
            return 0
        print(f"{ACCENT}[✗] Error:{RESET} Could not complete job. Check loaded chamber.", file=sys.stderr)
        return 1

    # 8. Legacy Migration
    if args.migrate_legacy:
        migrated = engine.migrate_legacy_completed_jobs()
        print(f"{ACCENT}[✓] Migrated {migrated} legacy files into completed_jobs_registry.104a.bejson.{RESET}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
