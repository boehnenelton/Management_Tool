#!/data/data/com.termux/files/usr/bin/env python3
"""
Library:        notes_mfdb_engine.py
Family:         Notes / MFDB
Description:    Dedicated Multi-File Database (MFDB v1.31) engine and Loaded Chamber
                state controller for categorized notes, category management, Markdown
                import/export with hashtag metadata headers, and keyword querying.
Version:        1.0.0
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date:           2026-11-03
RELATIONAL_ID:  bb348f5c-4862-4e96-b2ea-f57092c2c14d
"""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_current_iso_timestamp() -> str:
    """Return ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def slugify_text(input_text: str) -> str:
    """Convert input string to normalized URL-safe slug."""
    normalized_text: str = input_text.strip().lower()
    clean_slug: str = re.sub(r"[^a-z0-9_-]+", "-", normalized_text)
    return clean_slug.strip("-") or "note"


class NotesMFDBEngine:
    """
    Core engine managing the MFDB multi-file database and loaded chamber context for notes.
    Structure:
      - 104a.mfdb.bejson (Master Manifest)
      - data/category.bejson (Category entity table)
      - data/note.bejson (Note entity table)
      - config/config.json (Engine settings)
      - config/state.json (Loaded chamber persistent state)
    """

    def __init__(self, base_directory: Optional[Path] = None) -> None:
        self.base_directory: Path = (base_directory or Path(__file__).resolve().parent.parent).resolve()
        self.config_dir: Path = self.base_directory / "config"
        self.data_dir: Path = self.base_directory / "data"
        self.mfdb_dir: Path = self.data_dir / "mfdb"
        self.mfdb_data_dir: Path = self.mfdb_dir / "data"
        self.exports_dir: Path = self.base_directory / "exports"

        self.manifest_path: Path = self.mfdb_dir / "104a.mfdb.bejson"
        self.category_file_path: Path = self.mfdb_data_dir / "category.bejson"
        self.note_file_path: Path = self.mfdb_data_dir / "note.bejson"
        self.config_file_path: Path = self.config_dir / "config.json"
        self.state_file_path: Path = self.config_dir / "state.json"

        # In-memory document caches
        self.manifest_document_cache: Dict[str, Any] = {}
        self.category_document_cache: Dict[str, Any] = {}
        self.note_document_cache: Dict[str, Any] = {}
        self.config_document_cache: Dict[str, Any] = {}
        self.state_document_cache: Dict[str, Any] = {}

        # O(1) Field Map Caches (Policy §6.2)
        self.manifest_field_map_cache: Dict[str, int] = {}
        self.category_field_map_cache: Dict[str, int] = {}
        self.note_field_map_cache: Dict[str, int] = {}
        self.state_field_map_cache: Dict[str, int] = {}

        self.bootstrap_storage()

    # -------------------------------------------------------------------------
    # Helper: O(1) Field Map Compiler
    # -------------------------------------------------------------------------
    @staticmethod
    def compile_field_map(bejson_document: Dict[str, Any]) -> Dict[str, int]:
        """Compile field descriptor list into dictionary mapping field name to index."""
        field_descriptors: List[Dict[str, Any]] = bejson_document.get("Fields", [])
        field_map_lookup: Dict[str, int] = {}
        for column_index, field_spec in enumerate(field_descriptors):
            if isinstance(field_spec, dict):
                field_name = field_spec.get("name", "")
                if field_name:
                    field_map_lookup[field_name] = column_index
            elif isinstance(field_spec, str):
                field_map_lookup[field_spec] = column_index
        return field_map_lookup

    # -------------------------------------------------------------------------
    # Atomic Persistence (Policy §4.4)
    # -------------------------------------------------------------------------
    @staticmethod
    def atomic_write_json(target_file_path: Path, document_payload: Dict[str, Any]) -> None:
        """Write JSON document safely using temporary file replacement and fsync."""
        target_file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_file_path: Path = target_file_path.with_suffix(".tmp")
        with open(temporary_file_path, "w", encoding="utf-8") as file_handle:
            json.dump(document_payload, file_handle, indent=2)
            file_handle.write("\n")
            file_handle.flush()
            os.fsync(file_handle.fileno())
        temporary_file_path.replace(target_file_path)

    # -------------------------------------------------------------------------
    # Bootstrapping & Self-Healing
    # -------------------------------------------------------------------------
    def bootstrap_storage(self) -> None:
        """Initialize directories, MFDB manifest, entity tables, and state."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.mfdb_data_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        current_timestamp: str = get_current_iso_timestamp()

        # 1. Config Store
        if not self.config_file_path.exists():
            self.config_document_cache = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Records_Type": ["ScriptConfig"],
                "Fields": [
                    {"name": "setting_name", "type": "string"},
                    {"name": "setting_value", "type": "any"},
                    {"name": "description", "type": "string"}
                ],
                "Values": [
                    ["app_name", "Categorized Notes Manager", "Application human-readable name"],
                    ["app_version", "1.0.0", "Application version"],
                    ["default_category", "General", "Fallback category for unassigned notes"],
                    ["terminal_columns_max", 57, "Maximum viewport width for 57-col discipline"],
                    ["accent_color_hex", "#DE2626", "Policy 8.1 Truecolor active accent color"],
                    ["exports_directory", str(self.exports_dir), "Default directory for exported notes"]
                ]
            }
            self.atomic_write_json(self.config_file_path, self.config_document_cache)
        else:
            with open(self.config_file_path, "r", encoding="utf-8") as file_handle:
                self.config_document_cache = json.load(file_handle)

        # 2. State Store (Loaded Chamber)
        if not self.state_file_path.exists():
            self.state_document_cache = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Records_Type": ["NotesChamberState"],
                "active_mode": "notes",
                "active_category": None,
                "active_note": None,
                "updated_at": current_timestamp,
                "Fields": [
                    {"name": "state_key", "type": "string"},
                    {"name": "state_value", "type": "any"},
                    {"name": "last_modified", "type": "string"}
                ],
                "Values": [
                    ["active_mode", "notes", current_timestamp],
                    ["active_category", None, current_timestamp],
                    ["active_note", None, current_timestamp]
                ]
            }
            self.atomic_write_json(self.state_file_path, self.state_document_cache)
        else:
            with open(self.state_file_path, "r", encoding="utf-8") as file_handle:
                self.state_document_cache = json.load(file_handle)

        self.state_field_map_cache = self.compile_field_map(self.state_document_cache)

        # 3. Category Entity Table
        if not self.category_file_path.exists():
            self.category_document_cache = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Parent_Hierarchy": "../104a.mfdb.bejson",
                "Records_Type": ["Category"],
                "Fields": [
                    {"name": "cat_id", "type": "string"},
                    {"name": "cat_name", "type": "string"},
                    {"name": "cat_slug", "type": "string"},
                    {"name": "cat_description", "type": "string"},
                    {"name": "created_at", "type": "string"},
                    {"name": "updated_at", "type": "string"}
                ],
                "Values": [
                    [
                        "cat_001",
                        "General",
                        "general",
                        "Default category for general notes and scratchpads",
                        current_timestamp,
                        current_timestamp
                    ]
                ]
            }
            self.atomic_write_json(self.category_file_path, self.category_document_cache)
        else:
            with open(self.category_file_path, "r", encoding="utf-8") as file_handle:
                self.category_document_cache = json.load(file_handle)

        self.category_field_map_cache = self.compile_field_map(self.category_document_cache)

        # 4. Note Entity Table
        if not self.note_file_path.exists():
            self.note_document_cache = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "Parent_Hierarchy": "../104a.mfdb.bejson",
                "Records_Type": ["Note"],
                "Fields": [
                    {"name": "note_id", "type": "string"},
                    {"name": "cat_id", "type": "string"},
                    {"name": "cat_name", "type": "string"},
                    {"name": "title", "type": "string"},
                    {"name": "slug", "type": "string"},
                    {"name": "content", "type": "string"},
                    {"name": "tags", "type": "string"},
                    {"name": "created_at", "type": "string"},
                    {"name": "updated_at", "type": "string"}
                ],
                "Values": []
            }
            self.atomic_write_json(self.note_file_path, self.note_document_cache)
        else:
            with open(self.note_file_path, "r", encoding="utf-8") as file_handle:
                self.note_document_cache = json.load(file_handle)

        self.note_field_map_cache = self.compile_field_map(self.note_document_cache)

        # 5. Master Manifest
        category_rows_count: int = len(self.category_document_cache.get("Values", []))
        note_rows_count: int = len(self.note_document_cache.get("Values", []))

        if not self.manifest_path.exists():
            self.manifest_document_cache = {
                "Format": "BEJSON",
                "Format_Version": "104a",
                "Format_Creator": "Elton Boehnen",
                "MFDB_Version": "1.31",
                "Network_Role": "Master",
                "DB_Name": "Management Notes Master",
                "DB_Description": "Categorized notes database with MFDB multi-file persistence.",
                "Schema_Version": "1.0.0",
                "Author": "Elton Boehnen",
                "Created_At": current_timestamp,
                "Records_Type": ["mfdb"],
                "Fields": [
                    {"name": "entity_name", "type": "string"},
                    {"name": "file_path", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "record_count", "type": "integer"},
                    {"name": "schema_version", "type": "string"},
                    {"name": "primary_key", "type": "string"}
                ],
                "Values": [
                    [
                        "Category",
                        "data/category.bejson",
                        "Categorized note collections",
                        category_rows_count,
                        "1.0",
                        "cat_id"
                    ],
                    [
                        "Note",
                        "data/note.bejson",
                        "Individual note records",
                        note_rows_count,
                        "1.0",
                        "note_id"
                    ]
                ]
            }
            self.atomic_write_json(self.manifest_path, self.manifest_document_cache)
        else:
            with open(self.manifest_path, "r", encoding="utf-8") as file_handle:
                self.manifest_document_cache = json.load(file_handle)

        self.manifest_field_map_cache = self.compile_field_map(self.manifest_document_cache)
        self.sync_manifest_counts()

    # -------------------------------------------------------------------------
    # Manifest Record Count Synchronizer
    # -------------------------------------------------------------------------
    def sync_manifest_counts(self) -> None:
        """Keep manifest record_count columns strictly in sync with entity row lengths."""
        entity_name_idx: int = self.manifest_field_map_cache.get("entity_name", 0)
        record_count_idx: int = self.manifest_field_map_cache.get("record_count", 3)

        category_count: int = len(self.category_document_cache.get("Values", []))
        note_count: int = len(self.note_document_cache.get("Values", []))

        updated_flag: bool = False
        for manifest_row in self.manifest_document_cache.get("Values", []):
            entity_name: str = str(manifest_row[entity_name_idx])
            if entity_name == "Category" and manifest_row[record_count_idx] != category_count:
                manifest_row[record_count_idx] = category_count
                updated_flag = True
            elif entity_name == "Note" and manifest_row[record_count_idx] != note_count:
                manifest_row[record_count_idx] = note_count
                updated_flag = True

        if updated_flag:
            self.atomic_write_json(self.manifest_path, self.manifest_document_cache)

    # -------------------------------------------------------------------------
    # Configuration Management (Policy §4.4)
    # -------------------------------------------------------------------------
    def get_configuration(self) -> Dict[str, Any]:
        """Compile and return current configuration dictionary using field map cache."""
        field_map = self.compile_field_map(self.config_document_cache)
        key_idx = field_map.get("setting_name", 0)
        val_idx = field_map.get("setting_value", 1)
        config_map: Dict[str, Any] = {}
        for row in self.config_document_cache.get("Values", []):
            if len(row) > max(key_idx, val_idx):
                config_map[str(row[key_idx])] = row[val_idx]
        return config_map

    def get_config_value(self, setting_name: str, fallback_value: Any = None) -> Any:
        """Retrieve single configuration setting."""
        return self.get_configuration().get(setting_name, fallback_value)

    def set_config_value(self, setting_name: str, setting_value: Any, description: Optional[str] = None) -> Dict[str, Any]:
        """Atomically set configuration setting and persist to config/config.json."""
        field_map = self.compile_field_map(self.config_document_cache)
        key_idx = field_map.get("setting_name", 0)
        val_idx = field_map.get("setting_value", 1)
        desc_idx = field_map.get("description", 2)

        rows = self.config_document_cache.get("Values", [])
        found = False
        for row in rows:
            if str(row[key_idx]) == setting_name:
                row[val_idx] = setting_value
                if description:
                    row[desc_idx] = description
                found = True
                break

        if not found:
            rows.append([setting_name, setting_value, description or f"Setting for {setting_name}"])

        self.atomic_write_json(self.config_file_path, self.config_document_cache)
        return self.get_configuration()

    # -------------------------------------------------------------------------
    # Loaded Chamber State Management
    # -------------------------------------------------------------------------
    def get_active_context(self) -> Dict[str, Optional[str]]:
        """Return currently loaded chamber context."""
        return {
            "active_mode": self.state_document_cache.get("active_mode", "notes"),
            "active_category": self.state_document_cache.get("active_category"),
            "active_note": self.state_document_cache.get("active_note"),
            "updated_at": self.state_document_cache.get("updated_at")
        }

    def persist_chamber_state(self) -> None:
        """Synchronize in-memory chamber dictionary to Values table and persist."""
        current_timestamp: str = get_current_iso_timestamp()
        self.state_document_cache["updated_at"] = current_timestamp

        key_idx: int = self.state_field_map_cache.get("state_key", 0)
        val_idx: int = self.state_field_map_cache.get("state_value", 1)
        mod_idx: int = self.state_field_map_cache.get("last_modified", 2)

        for row in self.state_document_cache.get("Values", []):
            key_name: str = row[key_idx]
            if key_name in self.state_document_cache:
                row[val_idx] = self.state_document_cache[key_name]
                row[mod_idx] = current_timestamp

        self.atomic_write_json(self.state_file_path, self.state_document_cache)

    def select_category(self, category_identifier_or_name: str) -> Dict[str, Any]:
        """Lock active category into chamber; clears active note selection."""
        category_record = self.find_category(category_identifier_or_name)
        if not category_record:
            raise ValueError(f"Category '{category_identifier_or_name}' not found.")

        canonical_category_name: str = category_record["cat_name"]
        self.state_document_cache["active_category"] = canonical_category_name
        self.state_document_cache["active_note"] = None
        self.persist_chamber_state()
        return category_record

    def select_note(self, note_identifier_or_title: str) -> Dict[str, Any]:
        """Lock note into chamber; automatically locks its parent category."""
        note_record = self.find_note(note_identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{note_identifier_or_title}' not found.")

        self.state_document_cache["active_note"] = note_record["note_id"]
        self.state_document_cache["active_category"] = note_record["cat_name"]
        self.persist_chamber_state()
        return note_record

    def clear_category(self) -> Dict[str, Optional[str]]:
        """Unload active category and active note from chamber."""
        self.state_document_cache["active_category"] = None
        self.state_document_cache["active_note"] = None
        self.persist_chamber_state()
        return self.get_active_context()

    def clear_note(self) -> Dict[str, Optional[str]]:
        """Unload active note from chamber while preserving loaded category."""
        self.state_document_cache["active_note"] = None
        self.persist_chamber_state()
        return self.get_active_context()

    def clear_all(self) -> Dict[str, Optional[str]]:
        """Clear entire chamber state."""
        self.state_document_cache["active_category"] = None
        self.state_document_cache["active_note"] = None
        self.persist_chamber_state()
        return self.get_active_context()

    def get_loaded_note(self) -> Optional[Dict[str, Any]]:
        """Return the Note currently loaded in the chamber."""
        active_note_id: Optional[str] = self.state_document_cache.get("active_note")
        if not active_note_id:
            return None
        return self.find_note(active_note_id)

    def get_loaded_category(self) -> Optional[Dict[str, Any]]:
        """Return the Category currently loaded in the chamber."""
        active_cat_name: Optional[str] = self.state_document_cache.get("active_category")
        if not active_cat_name:
            return None
        return self.find_category(active_cat_name)

    # -------------------------------------------------------------------------
    # Category Operations (CRUD)
    # -------------------------------------------------------------------------
    def list_categories(self) -> List[Dict[str, Any]]:
        """List all registered categories with live note counts."""
        id_idx: int = self.category_field_map_cache.get("cat_id", 0)
        name_idx: int = self.category_field_map_cache.get("cat_name", 1)
        slug_idx: int = self.category_field_map_cache.get("cat_slug", 2)
        desc_idx: int = self.category_field_map_cache.get("cat_description", 3)
        created_idx: int = self.category_field_map_cache.get("created_at", 4)
        updated_idx: int = self.category_field_map_cache.get("updated_at", 5)

        # Precompute note counts per category
        note_cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
        category_counts: Dict[str, int] = {}
        for note_row in self.note_document_cache.get("Values", []):
            cat_name: str = str(note_row[note_cat_name_idx]).lower()
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        categories_list: List[Dict[str, Any]] = []
        for row in self.category_document_cache.get("Values", []):
            c_name: str = row[name_idx]
            categories_list.append({
                "cat_id": row[id_idx],
                "cat_name": c_name,
                "cat_slug": row[slug_idx],
                "cat_description": row[desc_idx] or "",
                "note_count": category_counts.get(c_name.lower(), 0),
                "created_at": row[created_idx],
                "updated_at": row[updated_idx]
            })

        categories_list.sort(key=lambda item: item["cat_name"].lower())
        return categories_list

    def find_category(self, identifier_or_name: str) -> Optional[Dict[str, Any]]:
        """Lookup category by ID, slug, or case-insensitive name."""
        token: str = identifier_or_name.strip().lower()
        id_idx: int = self.category_field_map_cache.get("cat_id", 0)
        name_idx: int = self.category_field_map_cache.get("cat_name", 1)
        slug_idx: int = self.category_field_map_cache.get("cat_slug", 2)
        desc_idx: int = self.category_field_map_cache.get("cat_description", 3)
        created_idx: int = self.category_field_map_cache.get("created_at", 4)
        updated_idx: int = self.category_field_map_cache.get("updated_at", 5)

        for row in self.category_document_cache.get("Values", []):
            if row[id_idx].lower() == token or row[slug_idx].lower() == token or row[name_idx].lower() == token:
                return {
                    "cat_id": row[id_idx],
                    "cat_name": row[name_idx],
                    "cat_slug": row[slug_idx],
                    "cat_description": row[desc_idx] or "",
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx]
                }
        return None

    def create_category(self, category_name: str, description: str = "") -> Dict[str, Any]:
        """Create new category in MFDB."""
        clean_name: str = category_name.strip()
        if not clean_name:
            raise ValueError("Category name cannot be empty.")

        existing = self.find_category(clean_name)
        if existing:
            raise ValueError(f"Category '{clean_name}' already exists (ID: {existing['cat_id']}).")

        id_idx: int = self.category_field_map_cache.get("cat_id", 0)
        current_rows = self.category_document_cache.get("Values", [])
        next_seq: int = len(current_rows) + 1
        generated_cat_id: str = f"cat_{next_seq:03d}"

        # Ensure ID uniqueness
        existing_ids = {r[id_idx] for r in current_rows}
        while generated_cat_id in existing_ids:
            next_seq += 1
            generated_cat_id = f"cat_{next_seq:03d}"

        timestamp: str = get_current_iso_timestamp()
        cat_slug: str = slugify_text(clean_name)

        new_row: List[Any] = [
            generated_cat_id,
            clean_name,
            cat_slug,
            description.strip(),
            timestamp,
            timestamp
        ]

        current_rows.append(new_row)
        self.atomic_write_json(self.category_file_path, self.category_document_cache)
        self.sync_manifest_counts()

        # Automatically lock newly created category
        self.select_category(clean_name)

        return {
            "cat_id": generated_cat_id,
            "cat_name": clean_name,
            "cat_slug": cat_slug,
            "cat_description": description.strip(),
            "created_at": timestamp,
            "updated_at": timestamp
        }

    def update_category(
        self,
        identifier_or_name: str,
        new_name: Optional[str] = None,
        new_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Edit category name and/or description, propagating changes to notes."""
        category_record = self.find_category(identifier_or_name)
        if not category_record:
            raise ValueError(f"Category '{identifier_or_name}' not found.")

        old_name: str = category_record["cat_name"]
        cat_id: str = category_record["cat_id"]

        name_idx: int = self.category_field_map_cache.get("cat_name", 1)
        slug_idx: int = self.category_field_map_cache.get("cat_slug", 2)
        desc_idx: int = self.category_field_map_cache.get("cat_description", 3)
        updated_idx: int = self.category_field_map_cache.get("updated_at", 5)

        timestamp: str = get_current_iso_timestamp()

        # Check name collision
        updated_name: str = old_name
        if new_name and new_name.strip() and new_name.strip().lower() != old_name.lower():
            if self.find_category(new_name):
                raise ValueError(f"Cannot rename: Category '{new_name.strip()}' already exists.")
            updated_name = new_name.strip()

        # Apply update to category table
        id_idx: int = self.category_field_map_cache.get("cat_id", 0)
        for row in self.category_document_cache.get("Values", []):
            if row[id_idx] == cat_id:
                row[name_idx] = updated_name
                row[slug_idx] = slugify_text(updated_name)
                if new_description is not None:
                    row[desc_idx] = new_description.strip()
                row[updated_idx] = timestamp
                break

        self.atomic_write_json(self.category_file_path, self.category_document_cache)

        # Propagate rename to all notes referencing this category
        if updated_name != old_name:
            note_cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
            note_updated_idx: int = self.note_field_map_cache.get("updated_at", 8)
            notes_updated_count: int = 0
            for note_row in self.note_document_cache.get("Values", []):
                if note_row[note_cat_name_idx].lower() == old_name.lower():
                    note_row[note_cat_name_idx] = updated_name
                    note_row[note_updated_idx] = timestamp
                    notes_updated_count += 1
            if notes_updated_count > 0:
                self.atomic_write_json(self.note_file_path, self.note_document_cache)

            # Update loaded chamber if active category was renamed
            if self.state_document_cache.get("active_category") == old_name:
                self.state_document_cache["active_category"] = updated_name
                self.persist_chamber_state()

        return self.find_category(cat_id)  # type: ignore

    def delete_category(
        self,
        identifier_or_name: str,
        reassign_to_category: str = "General"
    ) -> Dict[str, Any]:
        """
        Delete category row and reassign orphaned notes to fallback category.
        If deleted category is currently loaded in chamber, chamber is cleared.
        """
        category_record = self.find_category(identifier_or_name)
        if not category_record:
            raise ValueError(f"Category '{identifier_or_name}' not found.")

        cat_id: str = category_record["cat_id"]
        cat_name: str = category_record["cat_name"]

        if cat_name.lower() == reassign_to_category.lower():
            raise ValueError(f"Cannot delete default fallback category '{reassign_to_category}'.")

        # Ensure fallback category exists
        fallback = self.find_category(reassign_to_category)
        if not fallback:
            fallback = self.create_category(reassign_to_category, "Default fallback category")

        fallback_id: str = fallback["cat_id"]
        fallback_name: str = fallback["cat_name"]
        timestamp: str = get_current_iso_timestamp()

        # 1. Reassign notes
        note_cat_id_idx: int = self.note_field_map_cache.get("cat_id", 1)
        note_cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
        note_updated_idx: int = self.note_field_map_cache.get("updated_at", 8)
        reassigned_notes_count: int = 0

        for note_row in self.note_document_cache.get("Values", []):
            if note_row[note_cat_id_idx] == cat_id or note_row[note_cat_name_idx].lower() == cat_name.lower():
                note_row[note_cat_id_idx] = fallback_id
                note_row[note_cat_name_idx] = fallback_name
                note_row[note_updated_idx] = timestamp
                reassigned_notes_count += 1

        if reassigned_notes_count > 0:
            self.atomic_write_json(self.note_file_path, self.note_document_cache)

        # 2. Delete row from category table
        id_idx: int = self.category_field_map_cache.get("cat_id", 0)
        retained_categories = [
            row for row in self.category_document_cache.get("Values", [])
            if row[id_idx] != cat_id
        ]
        self.category_document_cache["Values"] = retained_categories
        self.atomic_write_json(self.category_file_path, self.category_document_cache)
        self.sync_manifest_counts()

        # 3. Chamber nullification if active category was deleted
        if self.state_document_cache.get("active_category") == cat_name:
            self.clear_category()

        return {
            "status": "success",
            "action": "delete_category",
            "deleted_category_id": cat_id,
            "deleted_category_name": cat_name,
            "reassigned_notes": reassigned_notes_count,
            "reassigned_to": fallback_name
        }

    # -------------------------------------------------------------------------
    # Note Operations (CRUD)
    # -------------------------------------------------------------------------
    @staticmethod
    def parse_tags_list(raw_tags: Any) -> List[str]:
        """Normalize raw tags string or list into clean list of lowercase tag strings."""
        if not raw_tags:
            return []
        if isinstance(raw_tags, list):
            tokens = [str(item).strip() for item in raw_tags]
        elif isinstance(raw_tags, str):
            clean_str = raw_tags.strip()
            if clean_str.startswith("[") and clean_str.endswith("]"):
                try:
                    tokens = [str(item).strip() for item in json.loads(clean_str)]
                except Exception:
                    tokens = [t.strip() for t in clean_str.split(",") if t.strip()]
            else:
                tokens = [t.strip() for t in clean_str.split(",") if t.strip()]
        else:
            tokens = [str(raw_tags).strip()]

        cleaned_tags: List[str] = []
        for token in tokens:
            t = token.lstrip("#").strip().lower()
            if t and t not in cleaned_tags:
                cleaned_tags.append(t)
        return cleaned_tags

    def list_notes(self, category_filter: Optional[str] = None, all_notes: bool = False) -> List[Dict[str, Any]]:
        """List notes, optionally filtered by category or loaded chamber category."""
        if all_notes or category_filter in ("*", "__ALL__"):
            effective_category = None
        else:
            effective_category = category_filter or self.state_document_cache.get("active_category")

        id_idx: int = self.note_field_map_cache.get("note_id", 0)
        cat_id_idx: int = self.note_field_map_cache.get("cat_id", 1)
        cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
        title_idx: int = self.note_field_map_cache.get("title", 3)
        slug_idx: int = self.note_field_map_cache.get("slug", 4)
        content_idx: int = self.note_field_map_cache.get("content", 5)
        tags_idx: int = self.note_field_map_cache.get("tags", 6)
        created_idx: int = self.note_field_map_cache.get("created_at", 7)
        updated_idx: int = self.note_field_map_cache.get("updated_at", 8)

        filtered_notes: List[Dict[str, Any]] = []
        for row in self.note_document_cache.get("Values", []):
            row_cat_name: str = str(row[cat_name_idx])
            if effective_category and row_cat_name.lower() != effective_category.lower():
                continue

            content_text: str = row[content_idx] or ""
            words_count: int = len(content_text.split())

            filtered_notes.append({
                "note_id": row[id_idx],
                "cat_id": row[cat_id_idx],
                "cat_name": row_cat_name,
                "title": row[title_idx],
                "slug": row[slug_idx],
                "content": content_text,
                "tags": self.parse_tags_list(row[tags_idx]),
                "word_count": words_count,
                "created_at": row[created_idx],
                "updated_at": row[updated_idx]
            })

        filtered_notes.sort(key=lambda item: item["updated_at"], reverse=True)
        return filtered_notes

    def find_note(self, identifier_or_title: str) -> Optional[Dict[str, Any]]:
        """Lookup note by note_id, slug, or substring in title."""
        token: str = identifier_or_title.strip().lower()

        id_idx: int = self.note_field_map_cache.get("note_id", 0)
        cat_id_idx: int = self.note_field_map_cache.get("cat_id", 1)
        cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
        title_idx: int = self.note_field_map_cache.get("title", 3)
        slug_idx: int = self.note_field_map_cache.get("slug", 4)
        content_idx: int = self.note_field_map_cache.get("content", 5)
        tags_idx: int = self.note_field_map_cache.get("tags", 6)
        created_idx: int = self.note_field_map_cache.get("created_at", 7)
        updated_idx: int = self.note_field_map_cache.get("updated_at", 8)

        rows = self.note_document_cache.get("Values", [])

        # 1. Exact note_id match
        for row in rows:
            if row[id_idx].lower() == token:
                return {
                    "note_id": row[id_idx],
                    "cat_id": row[cat_id_idx],
                    "cat_name": row[cat_name_idx],
                    "title": row[title_idx],
                    "slug": row[slug_idx],
                    "content": row[content_idx] or "",
                    "tags": self.parse_tags_list(row[tags_idx]),
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx]
                }

        # 2. Exact slug match
        for row in rows:
            if row[slug_idx].lower() == token:
                return {
                    "note_id": row[id_idx],
                    "cat_id": row[cat_id_idx],
                    "cat_name": row[cat_name_idx],
                    "title": row[title_idx],
                    "slug": row[slug_idx],
                    "content": row[content_idx] or "",
                    "tags": self.parse_tags_list(row[tags_idx]),
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx]
                }

        # 3. Substring match in title
        for row in rows:
            if token in row[title_idx].lower():
                return {
                    "note_id": row[id_idx],
                    "cat_id": row[cat_id_idx],
                    "cat_name": row[cat_name_idx],
                    "title": row[title_idx],
                    "slug": row[slug_idx],
                    "content": row[content_idx] or "",
                    "tags": self.parse_tags_list(row[tags_idx]),
                    "created_at": row[created_idx],
                    "updated_at": row[updated_idx]
                }

        return None

    def create_note(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new note in the MFDB and lock it into the active chamber."""
        clean_title: str = title.strip()
        if not clean_title:
            raise ValueError("Note title cannot be empty.")

        # Resolve category: parameter -> chamber -> default ("General")
        chosen_cat_name: str = category_name or self.state_document_cache.get("active_category") or "General"
        category_record = self.find_category(chosen_cat_name)
        if not category_record:
            # Auto-create category if missing
            category_record = self.create_category(chosen_cat_name)

        cat_id: str = category_record["cat_id"]
        canonical_cat_name: str = category_record["cat_name"]

        # Generate unique note ID
        current_rows = self.note_document_cache.get("Values", [])
        id_idx: int = self.note_field_map_cache.get("note_id", 0)
        existing_ids = {r[id_idx] for r in current_rows}
        next_seq: int = len(current_rows) + 1
        generated_note_id: str = f"not_{next_seq:03d}"
        while generated_note_id in existing_ids:
            next_seq += 1
            generated_note_id = f"not_{next_seq:03d}"

        timestamp: str = get_current_iso_timestamp()
        note_slug: str = slugify_text(clean_title)
        tags_list: List[str] = self.parse_tags_list(tags)
        tags_json_string: str = json.dumps(tags_list)

        new_row: List[Any] = [
            generated_note_id,
            cat_id,
            canonical_cat_name,
            clean_title,
            note_slug,
            content,
            tags_json_string,
            timestamp,
            timestamp
        ]

        current_rows.append(new_row)
        self.atomic_write_json(self.note_file_path, self.note_document_cache)
        self.sync_manifest_counts()

        # AUTOMATICALLY LOCK INTO CHAMBER (Loaded Chamber Law)
        self.select_note(generated_note_id)

        return {
            "note_id": generated_note_id,
            "cat_id": cat_id,
            "cat_name": canonical_cat_name,
            "title": clean_title,
            "slug": note_slug,
            "content": content,
            "tags": tags_list,
            "created_at": timestamp,
            "updated_at": timestamp
        }

    def update_note(
        self,
        identifier_or_title: str,
        new_title: Optional[str] = None,
        new_content: Optional[str] = None,
        new_category_name: Optional[str] = None,
        new_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update fields of an existing note."""
        note_record = self.find_note(identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{identifier_or_title}' not found.")

        note_id: str = note_record["note_id"]
        id_idx: int = self.note_field_map_cache.get("note_id", 0)
        cat_id_idx: int = self.note_field_map_cache.get("cat_id", 1)
        cat_name_idx: int = self.note_field_map_cache.get("cat_name", 2)
        title_idx: int = self.note_field_map_cache.get("title", 3)
        slug_idx: int = self.note_field_map_cache.get("slug", 4)
        content_idx: int = self.note_field_map_cache.get("content", 5)
        tags_idx: int = self.note_field_map_cache.get("tags", 6)
        updated_idx: int = self.note_field_map_cache.get("updated_at", 8)

        timestamp: str = get_current_iso_timestamp()

        # Handle category change if requested
        updated_cat_id: Optional[str] = None
        updated_cat_name: Optional[str] = None
        if new_category_name:
            cat_record = self.find_category(new_category_name)
            if not cat_record:
                cat_record = self.create_category(new_category_name)
            updated_cat_id = cat_record["cat_id"]
            updated_cat_name = cat_record["cat_name"]

        for row in self.note_document_cache.get("Values", []):
            if row[id_idx] == note_id:
                if new_title is not None and new_title.strip():
                    row[title_idx] = new_title.strip()
                    row[slug_idx] = slugify_text(new_title)
                if new_content is not None:
                    row[content_idx] = new_content
                if updated_cat_id and updated_cat_name:
                    row[cat_id_idx] = updated_cat_id
                    row[cat_name_idx] = updated_cat_name
                if new_tags is not None:
                    parsed_tags = self.parse_tags_list(new_tags)
                    row[tags_idx] = json.dumps(parsed_tags)
                row[updated_idx] = timestamp
                break

        self.atomic_write_json(self.note_file_path, self.note_document_cache)

        # Reselect in chamber to keep fresh
        self.select_note(note_id)
        return self.find_note(note_id)  # type: ignore

    def delete_note(self, identifier_or_title: str) -> Dict[str, Any]:
        """
        Delete note from MFDB entity table and automatically nullify
        active_note in chamber state (Fail-Safe Law).
        """
        note_record = self.find_note(identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{identifier_or_title}' not found.")

        deleted_note_id: str = note_record["note_id"]
        deleted_title: str = note_record["title"]

        id_idx: int = self.note_field_map_cache.get("note_id", 0)
        retained_rows = [
            row for row in self.note_document_cache.get("Values", [])
            if row[id_idx] != deleted_note_id
        ]

        self.note_document_cache["Values"] = retained_rows
        self.atomic_write_json(self.note_file_path, self.note_document_cache)
        self.sync_manifest_counts()

        # NULLIFY ACTIVE NOTE IN CHAMBER STATE
        if self.state_document_cache.get("active_note") == deleted_note_id:
            self.clear_note()

        return {
            "status": "success",
            "action": "delete_note",
            "deleted_note_id": deleted_note_id,
            "deleted_title": deleted_title,
            "chamber_state": "nullified"
        }

    # -------------------------------------------------------------------------
    # Tag Operations (Add / Remove)
    # -------------------------------------------------------------------------
    def add_note_tags(self, identifier_or_title: str, tags_to_add: List[str]) -> Dict[str, Any]:
        """Append one or more tags to an existing note."""
        note_record = self.find_note(identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{identifier_or_title}' not found.")

        existing_tags: List[str] = note_record["tags"]
        new_tag_tokens: List[str] = self.parse_tags_list(tags_to_add)

        for token in new_tag_tokens:
            if token not in existing_tags:
                existing_tags.append(token)

        return self.update_note(note_record["note_id"], new_tags=existing_tags)

    def remove_note_tags(self, identifier_or_title: str, tags_to_remove: List[str]) -> Dict[str, Any]:
        """Remove one or more tags from an existing note."""
        note_record = self.find_note(identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{identifier_or_title}' not found.")

        existing_tags: List[str] = note_record["tags"]
        remove_tokens = set(self.parse_tags_list(tags_to_remove))

        retained_tags = [t for t in existing_tags if t not in remove_tokens]
        return self.update_note(note_record["note_id"], new_tags=retained_tags)

    def set_note_category(self, identifier_or_title: str, target_category_name: str) -> Dict[str, Any]:
        """Move note to target category."""
        return self.update_note(identifier_or_title, new_category_name=target_category_name)

    # -------------------------------------------------------------------------
    # Markdown Export & Import (Specific Format Law)
    # -------------------------------------------------------------------------
    @staticmethod
    def format_exported_markdown(title: str, category_name: str, tags: List[str], content: str) -> str:
        """
        Enforce user's exact specification:
        #tag1 #tag2 ...
        # <title>
        # <category>
        <2x line breaks>
        <note body>
        """
        tag_tokens: List[str] = []
        for raw_tag in tags:
            clean_tag = raw_tag.strip().lstrip("#")
            if clean_tag:
                tag_tokens.append(f"#{clean_tag}")

        tags_line: str = " ".join(tag_tokens)

        header_lines: List[str] = []
        if tags_line:
            header_lines.append(tags_line)
        header_lines.append(f"# {title.strip()}")
        header_lines.append(f"# {category_name.strip()}")

        header_block: str = "\n".join(header_lines)
        return f"{header_block}\n\n{content}\n"

    def export_note(
        self,
        identifier_or_title: str,
        destination_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export note to Markdown file with hashtags, title, and category headers."""
        note_record = self.find_note(identifier_or_title)
        if not note_record:
            raise ValueError(f"Note '{identifier_or_title}' not found.")

        rendered_markdown: str = self.format_exported_markdown(
            title=note_record["title"],
            category_name=note_record["cat_name"],
            tags=note_record["tags"],
            content=note_record["content"]
        )

        if destination_path:
            output_file: Path = Path(destination_path).resolve()
            if output_file.is_dir():
                output_file = output_file / f"{note_record['slug']}.md"
        else:
            output_file = self.exports_dir / f"{note_record['slug']}.md"

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as file_handle:
            file_handle.write(rendered_markdown)

        return {
            "status": "success",
            "note_id": note_record["note_id"],
            "title": note_record["title"],
            "category": note_record["cat_name"],
            "tags": note_record["tags"],
            "destination_path": str(output_file),
            "rendered_content": rendered_markdown
        }

    def import_markdown_file(
        self,
        source_file_path: str,
        category_name: Optional[str] = None,
        custom_title: Optional[str] = None,
        custom_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Import markdown file, automatically parsing:
          Line 1: #tag1 #tag2 (if hashtags present)
          Line 2: # Title
          Line 3: # Category
          Rest: Note content body
        """
        source_path: Path = Path(source_file_path).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")

        with open(source_path, "r", encoding="utf-8", errors="ignore") as file_handle:
            file_lines = file_handle.readlines()

        extracted_tags: List[str] = []
        extracted_title: Optional[str] = custom_title
        extracted_category: Optional[str] = category_name

        line_index: int = 0
        total_lines: int = len(file_lines)

        # Check line 0 for tags (e.g. #tag1 #tag2)
        if line_index < total_lines:
            first_line = file_lines[line_index].strip()
            # If line is hashtag tokens (starts with # and each word starts with #)
            words = first_line.split()
            if words and all(w.startswith("#") for w in words) and len(words) > 1:
                for w in words:
                    tag_clean = w.lstrip("#").strip()
                    if tag_clean:
                        extracted_tags.append(tag_clean)
                line_index += 1
            elif words and len(words) == 1 and words[0].startswith("#") and not words[0].startswith("# "):
                tag_clean = words[0].lstrip("#").strip()
                if tag_clean:
                    extracted_tags.append(tag_clean)
                line_index += 1

        # Check for # Title
        if line_index < total_lines:
            second_line = file_lines[line_index].strip()
            if second_line.startswith("# ") and not extracted_title:
                extracted_title = second_line[2:].strip()
                line_index += 1
            elif second_line.startswith("#"):
                if not extracted_title:
                    extracted_title = second_line.lstrip("#").strip()
                line_index += 1

        # Check for # Category
        if line_index < total_lines:
            third_line = file_lines[line_index].strip()
            if third_line.startswith("# ") and not extracted_category:
                candidate_category = third_line[2:].strip()
                # If candidate matches a known category or valid token
                if candidate_category:
                    extracted_category = candidate_category
                    line_index += 1
            elif third_line.startswith("#") and not extracted_category:
                candidate_category = third_line.lstrip("#").strip()
                if candidate_category:
                    extracted_category = candidate_category
                    line_index += 1

        # Skip any empty lines before content body
        while line_index < total_lines and not file_lines[line_index].strip():
            line_index += 1

        # Remainder is body content
        content_body: str = "".join(file_lines[line_index:]).strip()

        # Merge custom tags
        if custom_tags:
            for ct in self.parse_tags_list(custom_tags):
                if ct not in extracted_tags:
                    extracted_tags.append(ct)

        final_title: str = extracted_title or source_path.stem.replace("-", " ").replace("_", " ").title()
        final_category: str = extracted_category or self.state_document_cache.get("active_category") or "General"

        return self.create_note(
            title=final_title,
            content=content_body,
            category_name=final_category,
            tags=extracted_tags
        )

    # -------------------------------------------------------------------------
    # Query Engine
    # -------------------------------------------------------------------------
    def query_notes(self, search_term: str) -> List[Dict[str, Any]]:
        """Search notes by title, category, tags, or body text with relevance ranking."""
        token: str = search_term.strip().lower()
        if not token:
            return self.list_notes()

        all_notes = self.list_notes(category_filter=None)
        matching_results: List[Dict[str, Any]] = []

        for note in all_notes:
            match_score: int = 0
            title_lower: str = note["title"].lower()
            cat_lower: str = note["cat_name"].lower()
            tags_lower: List[str] = [t.lower() for t in note["tags"]]
            content_lower: str = note["content"].lower()

            if token == title_lower:
                match_score += 30
            elif token in title_lower:
                match_score += 15

            if token == cat_lower:
                match_score += 12
            elif token in cat_lower:
                match_score += 6

            if token in tags_lower:
                match_score += 20
            elif any(token in t for t in tags_lower):
                match_score += 10

            if token in content_lower:
                match_score += 5

            if match_score > 0:
                result_item = dict(note)
                result_item["match_score"] = match_score
                matching_results.append(result_item)

        matching_results.sort(key=lambda item: item["match_score"], reverse=True)
        return matching_results
