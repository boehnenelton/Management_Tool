#!/data/data/com.termux/files/usr/bin/env python3
"""
Name:           stateful_context_engine.py
Description:    Multi-Mode Stateful Context Engine implementing the Loaded Chamber Pattern
                Supports Mode 1 (Logging) and Mode 2 (Research Reports & Tracking)
Version:        1.1.0
Author:         Elton Boehnen
License:        MIT / BEJSON Standard
"""

from __future__ import annotations
import glob
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_application_root_path() -> Path:
    """Resolve and return the absolute application root directory."""
    return Path(__file__).resolve().parent.parent


APPLICATION_ROOT_PATH: Path = get_application_root_path()


class StatefulContextEngine:
    """
    Multi-Mode Stateful Context Engine implementing the Loaded Chamber Pattern.
    Mode 1: Logging State & Log Record Operations
    Mode 2: Research Papers & Report Tracking, Categorization, Indexing, and Pulling
    """

    SUPPORTED_MODES: Dict[str, str] = {
        "1": "logging",
        "logging": "logging",
        "2": "reports",
        "reports": "reports"
    }

    def __init__(self, application_base_directory: Optional[Path] = None) -> None:
        self.application_directory: Path = application_base_directory or APPLICATION_ROOT_PATH
        self.configuration_file_path: Path = self.application_directory / "config" / "config.json"
        self.state_file_path: Path = self.application_directory / "config" / "state.json"
        self.registry_file_path: Path = self.application_directory / "data" / "registry.bejson"
        self.reports_index_file_path: Path = self.application_directory / "data" / "reports_index.bejson"

        # In-memory cached representations
        self.configuration_cache_dictionary: Dict[str, Any] = {}
        self.state_cache_dictionary: Dict[str, Any] = {}
        self.registry_cache_dictionary: Dict[str, Any] = {}
        self.reports_index_cache_dictionary: Dict[str, Any] = {}

        # Field map caches (Policy §6.2)
        self.registry_field_map_cache: Dict[str, int] = {}
        self.reports_index_field_map_cache: Dict[str, int] = {}
        self.state_field_map_cache: Dict[str, int] = {}

        self.initialize_engine_environment()

    def initialize_engine_environment(self) -> None:
        """Verify directories and load initial configuration, state, and index stores."""
        self.load_configuration_store()
        self.load_state_store()
        self.load_registry_store()
        self.load_reports_index_store()

    # -------------------------------------------------------------------------
    # BEJSON Field Map Cache Compilation (Policy §6.2)
    # -------------------------------------------------------------------------

    @staticmethod
    def compile_bejson_field_map(bejson_document_payload: Dict[str, Any]) -> Dict[str, int]:
        """Compile an O(1) field name to column index lookup cache."""
        field_descriptor_collection: List[Dict[str, Any]] = bejson_document_payload.get("Fields", [])
        field_map_lookup_table: Dict[str, int] = {}
        for column_ordinal_index, field_descriptor_dictionary in enumerate(field_descriptor_collection):
            field_name_identifier: str = field_descriptor_dictionary.get("name", "")
            if field_name_identifier:
                field_map_lookup_table[field_name_identifier] = column_ordinal_index
        return field_map_lookup_table

    # -------------------------------------------------------------------------
    # Store Loading & Persistence
    # -------------------------------------------------------------------------

    def load_configuration_store(self) -> Dict[str, Any]:
        """Load and cache the script configuration."""
        if not self.configuration_file_path.exists():
            return {}
        with open(self.configuration_file_path, "r", encoding="utf-8") as configuration_file_handle:
            self.configuration_cache_dictionary = json.load(configuration_file_handle)
        return self.configuration_cache_dictionary

    def load_state_store(self) -> Dict[str, Any]:
        """Load persistent state and compile field map cache."""
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()
        if not self.state_file_path.exists():
            self.state_cache_dictionary = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Records_Type": ["StatefulContextState"],
                "active_mode": "reports",
                "active_category": None,
                "active_entry": None,
                "updated_at": current_iso_timestamp,
                "Fields": [
                    {"name": "state_key", "type": "string"},
                    {"name": "state_value", "type": "any"},
                    {"name": "last_modified", "type": "string"}
                ],
                "Values": [
                    ["active_mode", "reports", current_iso_timestamp],
                    ["active_category", None, current_iso_timestamp],
                    ["active_entry", None, current_iso_timestamp]
                ]
            }
            self.persist_state_store()
        else:
            with open(self.state_file_path, "r", encoding="utf-8") as state_file_handle:
                self.state_cache_dictionary = json.load(state_file_handle)

            # Ensure active_mode exists in legacy state files
            if "active_mode" not in self.state_cache_dictionary:
                self.state_cache_dictionary["active_mode"] = "reports"
            if "active_category" not in self.state_cache_dictionary:
                self.state_cache_dictionary["active_category"] = self.state_cache_dictionary.get("active_group")
            if "active_entry" not in self.state_cache_dictionary:
                self.state_cache_dictionary["active_entry"] = self.state_cache_dictionary.get("active_target")

        self.state_field_map_cache = self.compile_bejson_field_map(self.state_cache_dictionary)
        return self.state_cache_dictionary

    def persist_state_store(self) -> None:
        """Atomically persist state store using temporary file swap."""
        temporary_state_file_path: Path = self.state_file_path.with_suffix(".tmp")
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temporary_state_file_path, "w", encoding="utf-8") as temporary_file_handle:
            json.dump(self.state_cache_dictionary, temporary_file_handle, indent=2)
            temporary_file_handle.write("\n")
        temporary_state_file_path.replace(self.state_file_path)

    def load_registry_store(self) -> Dict[str, Any]:
        """Load target registry and compile field map cache."""
        if not self.registry_file_path.exists():
            self.registry_cache_dictionary = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Records_Type": ["DomainTarget"],
                "Fields": [
                    {"name": "domain_id", "type": "string"},
                    {"name": "group_name", "type": "string"},
                    {"name": "target_id", "type": "string"},
                    {"name": "target_label", "type": "string"},
                    {"name": "payload_content", "type": "string"},
                    {"name": "created_at", "type": "string"}
                ],
                "Values": []
            }
            self.persist_registry_store()
        else:
            with open(self.registry_file_path, "r", encoding="utf-8") as registry_file_handle:
                self.registry_cache_dictionary = json.load(registry_file_handle)

        self.registry_field_map_cache = self.compile_bejson_field_map(self.registry_cache_dictionary)
        return self.registry_cache_dictionary

    def persist_registry_store(self) -> None:
        """Atomically persist registry store using temporary file swap."""
        temporary_registry_file_path: Path = self.registry_file_path.with_suffix(".tmp")
        self.registry_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temporary_registry_file_path, "w", encoding="utf-8") as temporary_file_handle:
            json.dump(self.registry_cache_dictionary, temporary_file_handle, indent=2)
            temporary_file_handle.write("\n")
        temporary_registry_file_path.replace(self.registry_file_path)

    def load_reports_index_store(self) -> Dict[str, Any]:
        """Load research reports index and compile field map cache."""
        if not self.reports_index_file_path.exists():
            self.reports_index_cache_dictionary = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Records_Type": ["ReportIndexRecord"],
                "Fields": [
                    {"name": "doc_id", "type": "string"},
                    {"name": "category_name", "type": "string"},
                    {"name": "file_name", "type": "string"},
                    {"name": "doc_title", "type": "string"},
                    {"name": "doc_path", "type": "string"},
                    {"name": "file_size_kb", "type": "float"},
                    {"name": "created_at", "type": "string"},
                    {"name": "updated_at", "type": "string"},
                    {"name": "tags", "type": "string"}
                ],
                "Values": []
            }
            self.persist_reports_index_store()
        else:
            with open(self.reports_index_file_path, "r", encoding="utf-8") as index_file_handle:
                self.reports_index_cache_dictionary = json.load(index_file_handle)

        self.reports_index_field_map_cache = self.compile_bejson_field_map(self.reports_index_cache_dictionary)
        return self.reports_index_cache_dictionary

    def persist_reports_index_store(self) -> None:
        """Atomically persist reports index store using temporary file swap."""
        temporary_index_file_path: Path = self.reports_index_file_path.with_suffix(".tmp")
        self.reports_index_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temporary_index_file_path, "w", encoding="utf-8") as temporary_file_handle:
            json.dump(self.reports_index_cache_dictionary, temporary_file_handle, indent=2)
            temporary_file_handle.write("\n")
        temporary_index_file_path.replace(self.reports_index_file_path)

    # -------------------------------------------------------------------------
    # Mode Management (--select-mode 1 logging / 2 reports)
    # -------------------------------------------------------------------------

    def list_modes(self) -> List[Dict[str, str]]:
        """Return available operational modes."""
        return [
            {"mode_id": "1", "mode_name": "logging", "description": "BEJSON 105 Standardized Logging & Log Sink Management"},
            {"mode_id": "2", "mode_name": "reports", "description": "Research Papers & Reports Tracking, Categorization, Indexing & Pulling"}
        ]

    def get_active_mode(self) -> str:
        """Return the currently selected operational mode."""
        return self.state_cache_dictionary.get("active_mode", "reports")

    def select_mode(self, mode_identifier_or_name: str) -> str:
        """Select operational mode (1/logging or 2/reports) and reset active context."""
        normalized_mode_token: str = mode_identifier_or_name.strip().lower()
        if normalized_mode_token not in self.SUPPORTED_MODES:
            raise ValueError(f"Invalid mode '{mode_identifier_or_name}'. Allowed: 1 (logging) or 2 (reports).")

        canonical_mode_name: str = self.SUPPORTED_MODES[normalized_mode_token]
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()

        self.state_cache_dictionary["active_mode"] = canonical_mode_name
        self.state_cache_dictionary["active_category"] = None
        self.state_cache_dictionary["active_entry"] = None
        self.state_cache_dictionary["active_group"] = None
        self.state_cache_dictionary["active_target"] = None
        self.state_cache_dictionary["updated_at"] = current_iso_timestamp

        self.persist_state_store()
        return canonical_mode_name

    # -------------------------------------------------------------------------
    # Context State Management (The Loaded Chamber)
    # -------------------------------------------------------------------------

    def get_active_context(self) -> Dict[str, Optional[str]]:
        """Return the currently loaded chamber context dictionary."""
        return {
            "active_mode": self.state_cache_dictionary.get("active_mode", "reports"),
            "active_category": self.state_cache_dictionary.get("active_category"),
            "active_entry": self.state_cache_dictionary.get("active_entry"),
            "updated_at": self.state_cache_dictionary.get("updated_at")
        }

    def update_active_context(
        self,
        category_name: Optional[str] = None,
        entry_identifier: Optional[str] = None,
        clear_category_flag: bool = False,
        clear_entry_flag: bool = False
    ) -> Dict[str, Optional[str]]:
        """Update persistent state values with timestamp and field map synchronization."""
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()

        if clear_category_flag:
            self.state_cache_dictionary["active_category"] = None
            self.state_cache_dictionary["active_entry"] = None
            self.state_cache_dictionary["active_group"] = None
            self.state_cache_dictionary["active_target"] = None
        elif category_name is not None:
            self.state_cache_dictionary["active_category"] = category_name
            self.state_cache_dictionary["active_group"] = category_name
            # Changing category clears previously loaded entry
            self.state_cache_dictionary["active_entry"] = None
            self.state_cache_dictionary["active_target"] = None

        if clear_entry_flag:
            self.state_cache_dictionary["active_entry"] = None
            self.state_cache_dictionary["active_target"] = None
        elif entry_identifier is not None:
            self.state_cache_dictionary["active_entry"] = entry_identifier
            self.state_cache_dictionary["active_target"] = entry_identifier

        self.state_cache_dictionary["updated_at"] = current_iso_timestamp

        # Synchronize positional Values table
        key_column_index: int = self.state_field_map_cache.get("state_key", 0)
        val_column_index: int = self.state_field_map_cache.get("state_value", 1)
        mod_column_index: int = self.state_field_map_cache.get("last_modified", 2)

        for state_table_row in self.state_cache_dictionary.get("Values", []):
            state_key_name: str = state_table_row[key_column_index]
            if state_key_name in self.state_cache_dictionary:
                state_table_row[val_column_index] = self.state_cache_dictionary[state_key_name]
                state_table_row[mod_column_index] = current_iso_timestamp

        self.persist_state_store()
        return self.get_active_context()

    # -------------------------------------------------------------------------
    # Persistent Selection Commands
    # -------------------------------------------------------------------------

    def select_category(self, category_name: str) -> Dict[str, Optional[str]]:
        """Lock category into state chamber; clears any previously selected entry."""
        available_categories: List[str] = self.list_categories()
        # Case-insensitive matching fallback
        matched_category_name: Optional[str] = None
        for existing_category in available_categories:
            if existing_category.lower() == category_name.strip().lower():
                matched_category_name = existing_category
                break

        chosen_category_name: str = matched_category_name or category_name.strip()
        return self.update_active_context(category_name=chosen_category_name)

    def select_entry(self, entry_identifier_or_name: str) -> Dict[str, Optional[str]]:
        """Lock specific document or record entry into the chamber."""
        current_mode: str = self.get_active_mode()
        if current_mode == "reports":
            report_record = self.find_report_entry(entry_identifier_or_name)
            if not report_record:
                raise ValueError(f"Report entry '{entry_identifier_or_name}' not found in index.")
            # Auto-align category
            self.state_cache_dictionary["active_category"] = report_record["category_name"]
            return self.update_active_context(
                category_name=report_record["category_name"],
                entry_identifier=report_record["doc_id"]
            )
        else:
            # Mode 1: Logging mode entry
            return self.update_active_context(entry_identifier=entry_identifier_or_name)

    def clear_category(self) -> Dict[str, Optional[str]]:
        """Clear active category and active entry from chamber."""
        return self.update_active_context(clear_category_flag=True)

    def clear_entry(self) -> Dict[str, Optional[str]]:
        """Unload active entry from chamber while preserving category."""
        return self.update_active_context(clear_entry_flag=True)

    def clear_all(self) -> Dict[str, Optional[str]]:
        """Clear all active selections from chamber."""
        return self.update_active_context(clear_category_flag=True, clear_entry_flag=True)

    # -------------------------------------------------------------------------
    # Discovery Operations (--list-categories / --list-entries)
    # -------------------------------------------------------------------------

    def list_categories(self) -> List[str]:
        """Return list of distinct categories in the active mode."""
        current_mode: str = self.get_active_mode()
        if current_mode == "reports":
            category_column_index: int = self.reports_index_field_map_cache.get("category_name", 1)
            distinct_categories_set = set()
            for index_row in self.reports_index_cache_dictionary.get("Values", []):
                distinct_categories_set.add(index_row[category_column_index])
            return sorted(list(distinct_categories_set))
        else:
            # Mode 1: Logging categories / subsystems
            return ["system", "audit", "jobs", "auth", "database", "network"]

    def list_entries(self, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List entries in active mode.
        Context-aware: If no category_filter is specified, but active_category is loaded,
        filters by that category. Otherwise returns all entries.
        """
        current_mode: str = self.get_active_mode()
        effective_category: Optional[str] = category_filter or self.state_cache_dictionary.get("active_category")

        if current_mode == "reports":
            doc_id_idx: int = self.reports_index_field_map_cache.get("doc_id", 0)
            category_idx: int = self.reports_index_field_map_cache.get("category_name", 1)
            file_name_idx: int = self.reports_index_field_map_cache.get("file_name", 2)
            title_idx: int = self.reports_index_field_map_cache.get("doc_title", 3)
            path_idx: int = self.reports_index_field_map_cache.get("doc_path", 4)
            size_idx: int = self.reports_index_field_map_cache.get("file_size_kb", 5)
            created_idx: int = self.reports_index_field_map_cache.get("created_at", 6)
            updated_idx: int = self.reports_index_field_map_cache.get("updated_at", 7)
            tags_idx: int = self.reports_index_field_map_cache.get("tags", 8)

            filtered_entries_collection: List[Dict[str, Any]] = []
            for row in self.reports_index_cache_dictionary.get("Values", []):
                if effective_category and row[category_idx].lower() != effective_category.lower():
                    continue
                filtered_entries_collection.append({
                    "doc_id": row[doc_id_idx],
                    "category_name": row[category_idx],
                    "file_name": row[file_name_idx],
                    "doc_title": row[title_idx],
                    "doc_path": row[path_idx],
                    "file_size_kb": row[size_idx],
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx],
                    "tags": row[tags_idx]
                })
            return filtered_entries_collection
        else:
            # Mode 1: Logging entries from recent log sinks
            global_logs_dir: str = self.configuration_cache_dictionary.get(
                "global_logs_directory", "/storage/emulated/0/Admin/System/Global_Logs"
            )
            log_files_list = sorted(glob.glob(os.path.join(global_logs_dir, "Log-*.bejson")), reverse=True)
            entries_list = []
            for log_file in log_files_list[:10]:
                stem_name = Path(log_file).stem
                entries_list.append({
                    "entry_id": stem_name,
                    "category_name": "daily_partition",
                    "file_name": os.path.basename(log_file),
                    "doc_title": f"Daily Log {stem_name.replace('Log-', '')}",
                    "doc_path": log_file
                })
            return entries_list

    # -------------------------------------------------------------------------
    # Reports Mode: Import & Indexing Features
    # -------------------------------------------------------------------------

    def import_report_file(
        self,
        source_markdown_path: str,
        category_name: Optional[str] = None,
        custom_file_name: Optional[str] = None,
        custom_title: Optional[str] = None,
        tags_string: str = "research,report"
    ) -> Dict[str, Any]:
        """
        Target a markdown file, assign it a category, import it into the category folder
        inside the research folder set by configuration, let you name it, update the index,
        and automatically lock it as active_entry in the chamber!
        """
        source_path_object: Path = Path(source_markdown_path).resolve()
        if not source_path_object.exists():
            raise FileNotFoundError(f"Source markdown file not found: {source_markdown_path}")

        # Resolve category: explicit parameter -> active chamber category -> default
        resolved_category: str = category_name or self.state_cache_dictionary.get("active_category") or "General"
        
        # Resolve destination root directory from config
        research_root_directory_string: str = self.configuration_cache_dictionary.get(
            "research_root_directory", "/storage/emulated/0/Admin/Resources/Reports"
        )
        research_root_path: Path = Path(research_root_directory_string)
        target_category_directory: Path = research_root_path / resolved_category
        target_category_directory.mkdir(parents=True, exist_ok=True)

        # Resolve filename
        if custom_file_name:
            clean_name: str = custom_file_name.strip()
            if not clean_name.endswith(".md"):
                clean_name += ".md"
        else:
            clean_name = source_path_object.name

        destination_file_path: Path = target_category_directory / clean_name

        # Copy source markdown file to target category directory
        shutil.copy2(source_path_object, destination_file_path)

        # Extract title from markdown H1 if not provided
        document_title: str = custom_title or self.extract_markdown_title(destination_file_path) or clean_name

        # Calculate file size in KB
        file_size_kb: float = round(destination_file_path.stat().st_size / 1024, 1)
        current_iso_timestamp: str = datetime.now(timezone.utc).isoformat()

        # Generate sequential doc_id
        doc_id_idx: int = self.reports_index_field_map_cache.get("doc_id", 0)
        existing_rows: List[List[Any]] = self.reports_index_cache_dictionary.get("Values", [])
        next_seq_number: int = len(existing_rows) + 1
        generated_doc_id: str = f"rep_{next_seq_number:03d}"

        # Append to reports index table
        new_index_row: List[Any] = [
            generated_doc_id,
            resolved_category,
            clean_name,
            document_title,
            str(destination_file_path),
            file_size_kb,
            current_iso_timestamp,
            current_iso_timestamp,
            tags_string
        ]

        # Check if file path already exists in index; update if so, else append
        path_idx: int = self.reports_index_field_map_cache.get("doc_path", 4)
        entry_updated_flag: bool = False
        for row in existing_rows:
            if row[path_idx] == str(destination_file_path):
                row[0] = row[0]  # keep existing id
                row[1] = resolved_category
                row[2] = clean_name
                row[3] = document_title
                row[5] = file_size_kb
                row[7] = current_iso_timestamp
                generated_doc_id = row[0]
                entry_updated_flag = True
                break

        if not entry_updated_flag:
            existing_rows.append(new_index_row)

        self.persist_reports_index_store()

        # AUTOMATICALLY LOCK INTO CHAMBER AS ACTIVE ENTRY
        self.state_cache_dictionary["active_mode"] = "reports"
        self.state_cache_dictionary["active_category"] = resolved_category
        self.state_cache_dictionary["active_entry"] = generated_doc_id
        self.persist_state_store()

        return {
            "status": "success",
            "doc_id": generated_doc_id,
            "category": resolved_category,
            "file_name": clean_name,
            "title": document_title,
            "destination_path": str(destination_file_path),
            "size_kb": file_size_kb,
            "chamber_locked": True
        }

    @staticmethod
    def extract_markdown_title(markdown_file_path: Path) -> Optional[str]:
        """Extract the first H1 title from a markdown file."""
        try:
            with open(markdown_file_path, "r", encoding="utf-8", errors="ignore") as file_handle:
                for line in file_handle:
                    stripped = line.strip()
                    if stripped.startswith("# "):
                        return stripped[2:].strip()
        except Exception:
            pass
        return None

    def find_report_entry(self, entry_identifier_or_name: str) -> Optional[Dict[str, Any]]:
        """Lookup report entry by doc_id, file_name, or substring match."""
        doc_id_idx: int = self.reports_index_field_map_cache.get("doc_id", 0)
        category_idx: int = self.reports_index_field_map_cache.get("category_name", 1)
        file_name_idx: int = self.reports_index_field_map_cache.get("file_name", 2)
        title_idx: int = self.reports_index_field_map_cache.get("doc_title", 3)
        path_idx: int = self.reports_index_field_map_cache.get("doc_path", 4)
        size_idx: int = self.reports_index_field_map_cache.get("file_size_kb", 5)
        created_idx: int = self.reports_index_field_map_cache.get("created_at", 6)
        updated_idx: int = self.reports_index_field_map_cache.get("updated_at", 7)
        tags_idx: int = self.reports_index_field_map_cache.get("tags", 8)

        token: str = entry_identifier_or_name.strip().lower()

        # 1. Exact doc_id match
        for row in self.reports_index_cache_dictionary.get("Values", []):
            if row[doc_id_idx].lower() == token:
                return {
                    "doc_id": row[doc_id_idx],
                    "category_name": row[category_idx],
                    "file_name": row[file_name_idx],
                    "doc_title": row[title_idx],
                    "doc_path": row[path_idx],
                    "file_size_kb": row[size_idx],
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx],
                    "tags": row[tags_idx]
                }

        # 2. Exact file_name match
        for row in self.reports_index_cache_dictionary.get("Values", []):
            if row[file_name_idx].lower() == token or Path(row[file_name_idx]).stem.lower() == token:
                return {
                    "doc_id": row[doc_id_idx],
                    "category_name": row[category_idx],
                    "file_name": row[file_name_idx],
                    "doc_title": row[title_idx],
                    "doc_path": row[path_idx],
                    "file_size_kb": row[size_idx],
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx],
                    "tags": row[tags_idx]
                }

        # 3. Substring in title or file_name
        for row in self.reports_index_cache_dictionary.get("Values", []):
            if token in row[title_idx].lower() or token in row[file_name_idx].lower():
                return {
                    "doc_id": row[doc_id_idx],
                    "category_name": row[category_idx],
                    "file_name": row[file_name_idx],
                    "doc_title": row[title_idx],
                    "doc_path": row[path_idx],
                    "file_size_kb": row[size_idx],
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx],
                    "tags": row[tags_idx]
                }
        return None

    def get_loaded_entry(self) -> Optional[Dict[str, Any]]:
        """Return the document entry currently loaded in the chamber."""
        active_entry_identifier: Optional[str] = self.state_cache_dictionary.get("active_entry")
        if not active_entry_identifier:
            return None
        current_mode: str = self.get_active_mode()
        if current_mode == "reports":
            return self.find_report_entry(active_entry_identifier)
        else:
            # Mode 1: Logging entry
            return {"entry_id": active_entry_identifier, "mode": "logging"}

    # -------------------------------------------------------------------------
    # Execution Actions (View, Edit, Pull, Delete, Query)
    # -------------------------------------------------------------------------

    def action_view(self) -> Dict[str, Any]:
        """View the content of the currently loaded research report."""
        loaded_entry: Optional[Dict[str, Any]] = self.get_loaded_entry()
        if not loaded_entry:
            raise RuntimeError("No entry loaded in chamber. Use --select-entry <id> first.")

        document_file_path: str = loaded_entry.get("doc_path", "")
        if not os.path.exists(document_file_path):
            raise FileNotFoundError(f"Underlying file missing on disk: {document_file_path}")

        with open(document_file_path, "r", encoding="utf-8", errors="ignore") as file_handle:
            file_content: str = file_handle.read()

        return {
            "status": "success",
            "entry": loaded_entry,
            "content": file_content
        }

    def action_pull(self, destination_directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Pull / copy the currently loaded research document to a destination directory,
        or copy content to clipboard if termux-clipboard-set exists.
        """
        loaded_entry: Optional[Dict[str, Any]] = self.get_loaded_entry()
        if not loaded_entry:
            raise RuntimeError("No entry loaded in chamber. Use --select-entry <id> first.")

        source_file_path: str = loaded_entry.get("doc_path", "")
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"Document file missing on disk: {source_file_path}")

        pulled_destination_path: Optional[str] = None
        if destination_directory:
            dest_dir_path = Path(destination_directory).resolve()
            dest_dir_path.mkdir(parents=True, exist_ok=True)
            pulled_destination_path = str(dest_dir_path / loaded_entry["file_name"])
            shutil.copy2(source_file_path, pulled_destination_path)

        # Also attempt Termux clipboard copy of path and content
        clipboard_flag: bool = False
        if shutil.which("termux-clipboard-set"):
            try:
                proc = subprocess.Popen(["termux-clipboard-set"], stdin=subprocess.PIPE)
                proc.communicate(input=source_file_path.encode("utf-8"))
                if proc.returncode == 0:
                    clipboard_flag = True
            except Exception:
                pass

        return {
            "status": "success",
            "action": "pull",
            "entry_id": loaded_entry.get("doc_id"),
            "file_name": loaded_entry.get("file_name"),
            "source_path": source_file_path,
            "destination_path": pulled_destination_path,
            "path_copied_to_clipboard": clipboard_flag
        }

    def action_edit(self) -> Dict[str, Any]:
        """Launch configured editor ($EDITOR or nano) on loaded document."""
        loaded_entry: Optional[Dict[str, Any]] = self.get_loaded_entry()
        if not loaded_entry:
            raise RuntimeError("No entry loaded in chamber. Use --select-entry <id> first.")

        source_file_path: str = loaded_entry.get("doc_path", "")
        editor_executable: str = os.getenv("EDITOR", "nano")

        return {
            "status": "ready_to_edit",
            "editor": editor_executable,
            "file_path": source_file_path
        }

    def action_delete(self) -> Dict[str, Any]:
        """
        Delete loaded research report from index and disk,
        and automatically nullify active_entry in state to prevent ghost actions.
        """
        loaded_entry: Optional[Dict[str, Any]] = self.get_loaded_entry()
        if not loaded_entry:
            raise RuntimeError("No entry loaded in chamber. Use --select-entry <id> first.")

        deleted_id: str = loaded_entry["doc_id"]
        deleted_file_path: str = loaded_entry.get("doc_path", "")

        # 1. Remove from disk if present
        if os.path.exists(deleted_file_path):
            try:
                os.remove(deleted_file_path)
            except OSError as error:
                raise RuntimeError(f"Failed to delete file on disk: {error}")

        # 2. Remove from reports index
        doc_id_idx: int = self.reports_index_field_map_cache.get("doc_id", 0)
        original_rows: List[List[Any]] = self.reports_index_cache_dictionary.get("Values", [])
        retained_rows: List[List[Any]] = [
            row for row in original_rows if row[doc_id_idx] != deleted_id
        ]
        self.reports_index_cache_dictionary["Values"] = retained_rows
        self.persist_reports_index_store()

        # 3. NULLIFY ACTIVE ENTRY IN STATE (Fail-Safe Law)
        self.clear_entry()

        return {
            "status": "success",
            "action": "delete",
            "deleted_entry_id": deleted_id,
            "file_deleted": deleted_file_path,
            "chamber_state": "nullified"
        }

    def query_reports(self, query_term: str) -> List[Dict[str, Any]]:
        """Search reports index by title, category, tags, or file content."""
        search_token: str = query_term.strip().lower()
        matching_results: List[Dict[str, Any]] = []

        all_entries: List[Dict[str, Any]] = self.list_entries(category_filter=None)
        for entry in all_entries:
            match_score: int = 0
            if search_token in entry["doc_title"].lower():
                match_score += 10
            if search_token in entry["file_name"].lower():
                match_score += 8
            if search_token in entry["category_name"].lower():
                match_score += 5
            if search_token in entry.get("tags", "").lower():
                match_score += 3

            # Search within document content if file exists
            doc_path = entry.get("doc_path", "")
            if os.path.isfile(doc_path):
                try:
                    with open(doc_path, "r", encoding="utf-8", errors="ignore") as handle:
                        body = handle.read().lower()
                        if search_token in body:
                            match_score += 2
                except Exception:
                    pass

            if match_score > 0:
                result_item = dict(entry)
                result_item["match_score"] = match_score
                matching_results.append(result_item)

        matching_results.sort(key=lambda item: item["match_score"], reverse=True)
        return matching_results
