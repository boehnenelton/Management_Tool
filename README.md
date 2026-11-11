<div align="center">
  <img src="assets/Management_CLI_Banner_1280x640.svg" alt="Management CLI Header Banner Logo" width="100%" />
</div>

# System Management Tool Suite

> Unified master router, structured logging, technical report indexing, categorized notes management, stateful job execution, and launch reminder automation.

[![Platform](https://img.shields.io/badge/Platform-Linux%20%2F%20Android%20Termux-blue.svg)](#prerequisites--setup)
[![Format](https://img.shields.io/badge/Format-BEJSON%20104a%20%2F%20105-DE2626.svg)](#technical-specifications--storage)
[![Terminal](https://img.shields.io/badge/Discipline-57--Column%20Portrait-black.svg)](#terminal-display--color-standards)
[![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial-DE2626.svg)](#license--attribution)

---

## Table of Contents

- [Prerequisites & Setup](#prerequisites--setup)
- [Architecture & Subsystem Routing](#architecture--subsystem-routing)
- [Operational Modes](#operational-modes)
  - [Mode 1: Logging Tool](#mode-1-logging-tool-logging_toolpy)
  - [Mode 2: Research Reports Indexer](#mode-2-research-reports-indexer-report_indexerpy)
  - [Mode 3: Categorized Notes Manager](#mode-3-categorized-notes-manager-notes_toolpy)
  - [Mode 4: Stateful Job Chamber & Standing Maintenance](#mode-4-stateful-job-chamber--standing-maintenance-job_toolpy)
  - [Mode 5: Launch Reminders & Active Tasks](#mode-5-launch-reminders--active-tasks-reminder_toolpy)
  - [Mode 6: Taxonomy Cartographer](#mode-6-taxonomy-cartographer)
- [Terminal Display & Color Standards](#terminal-display--color-standards)
- [CLI Reference Guide](#cli-reference-guide)
- [Repository Structure](#repository-structure)
- [Verification & Testing](#verification--testing)
- [License & Attribution](#license--attribution)

---

## Prerequisites & Setup

### Environment Requirements
- **Python**: 3.10 or higher
- **Operating System**: Linux / Android Termux (ARM64, x86_64)
- **Terminal**: Modern ANSI terminal supporting 24-bit Truecolor (`COLORTERM=truecolor` or `COLORTERM=24bit`) with automatic fallback to standard 16-color ANSI bold red.

### Quick Start
Clone the repository and verify environment execution:

```bash
git clone https://github.com/boehnenelton/Management_Tool.git
cd Management_Tool

# Display unified system status
python3 management_tool.py --status

# Inspect AI-optimized command guide
python3 management_tool.py --help
```

---

## Architecture & Subsystem Routing

The **Management Tool Suite** provides a single deterministic entry router that coordinates system logging, technical documentation indexing, hierarchical notes persistence, stateful job tracking, and startup task reminders:

```
                      ┌────────────────────────────────────────┐
                      │   management_tool.py (management.sh)   │
                      │         [UNIFIED MASTER ROUTER]        │
                      └───────────────────┬────────────────────┘
                                          │
       ┌──────────────┬───────────────────┼───────────────────┬──────────────┬──────────────┐
       │              │                   │                   │              │              │
       ▼              ▼                   ▼                   ▼              ▼              ▼
┌─────────────┐┌──────────────┐   ┌───────────────┐   ┌──────────────┐┌──────────────┐┌──────────────┐
│   Mode 1    ││    Mode 2    │   │    Mode 3     │   │    Mode 4    ││    Mode 5    ││    Mode 6    │
│Logging Tool ││Report Indexer│   │  Notes Tool   │   │   Job Tool   ││Reminder Tool ││   Taxonomy   │
│(logging_tool││(report_index)│   │ (notes_tool)  │   │  (job_tool)  ││ (remind.sh)  ││ (cartography)│
└──────┬──────┘└──────┬───────┘   └───────┬───────┘   └──────┬───────┘└──────┬───────┘└──────┬───────┘
       │              │                   │                  │               │               │
       ▼              ▼                   ▼                  ▼               ▼               ▼
• BEJSON 105   • Papers Index     • MFDB v1.31        • Job Registry • Active Queue  • AST Analysis
• Daily UTC    • Categorization   • Loaded Chamber    • Maintenance  • Completed Arc • Symbol Graphs
• HTML Reports • Query & Search   • Wiki Categories   • Task Stepping• Termux Launch • Entity Prefixes
• Log Rotation • Paper Pulling    • Web Editor (Flask)• Auto Recovery• Clean Filter  • Route Matrix
```

---

## Operational Modes

### Mode 1: Logging Tool (`tools/logging_tool/logging_tool.py`)
- **Persistence**: Daily UTC date partitions backed by standardized records and dual-path encrypted secure sinks.
- **Context Machine**: Locks session metadata (`subsystem`, `category`, `actor`, `session_id`) into persistent state once, emitting subsequent logs with zero argument friction.
- **HTML & Markdown Reporting**: Serializes log streams into templated Markdown and compiles standalone responsive HTML reports via `lib_md_to_html.py`.
- **Integrity Gates**: Structural validation, SHA-256 hash chaining, checksum verification, and automatic daily rotation.

### Mode 2: Research Reports Indexer (`tools/report_indexer/report_indexer.py`)
- **Persistence**: Central index table (`data/reports_index.bejson`) backed by tabular record schemas.
- **Workflow**: Catalog, categorize, import, pull, view, and search technical specifications, audit papers, and research documents.
- **Chamber Locking**: Lock an active entry or category into chamber context to execute operations like viewing, editing, or pulling without repeating identifiers.

### Mode 3: Categorized Notes Manager (`tools/notes_tool/notes_tool.py`)
- **Persistence**: Multi-File Database (MFDB v1.31) with central manifest coordinating entity tables (`category.bejson`, `note.bejson`) linked by parent hierarchy.
- **Context Machine**: Lock active category and active note persistently in configuration state. Operations execute directly on loaded note targets.
- **Strict Markdown Header Standard**: Exported and imported notes adhere to literal metadata headers:
  ```markdown
  #tag1 #tag2 #tag3
  # Note Title
  # Category Name

  Note body content here...
  ```
- **Static Documentation Site Generator (`notes_site_exporter.py`)**: Compiles notes into a clean, searchable static site:
  - Layout: `notes/<category>/<note-slug>/index.html` + raw `<note-slug>.md`
  - Navigation: Clean wiki-style 2-column link grid of categories on main hub; category headers strictly use `Notes - <Category>`.
  - Accessible Assets: Full `sitemap.html`, `sitemap.xml`, and `robots.txt`.
- **Interactive Web Editor Workspace (`tools/notes_tool/notes_web_server.py`)**: Localhost workspace running on port 5050 with dual-pane real-time markdown editor, live preview, and chamber state synchronization.

### Mode 4: Stateful Job Chamber & Standing Maintenance (`tools/job_manager/job_tool.py`)
- **Active Job Registry**: Tracks active jobs in `data/job_registry.104a.bejson` with sequential tasks, priority classifications, and instructions.
- **Completed Archive**: Atomically archives completed jobs into `data/completed_jobs_registry.104a.bejson` with resolution summaries and execution timestamps.
- **Standing Maintenance Jobs Registry (`data/maintenance_jobs_registry.104a.bejson`)**:
  - Standing maintenance tasks are perpetual (status remains `standing`).
  - Audited on session start via `--init-check`.
  - Directly queryable via `--maintenance`.
  - Execution runs are recorded via `--record-maintenance <id> [--maintenance-result <summary>]`, updating `run_count`, `last_run_timestamp`, and `last_result`.
- **Loaded Chamber Workflow**: Lock active job into chamber (`--select <id>`), inspect task cards (`--view`), toggle task states (`--toggle-task <idx>`), and add tasks (`--add-task <text>`).

### Mode 5: Launch Reminders & Active Tasks (`tools/reminder_tool/reminder_tool.py`)
- **Dual Registries**:
  - Active Queue: `data/reminders.104a.bejson`
  - Completed Archive: `data/completed_reminders.104a.bejson`
- **Auto-Removal on Completion**: Marking a reminder complete atomically removes it from the active queue and transfers it to the completed archive.
- **Termux Launch Integration**: Surface active reminders directly upon terminal initialization. When zero active reminders exist, the check produces zero terminal output to avoid terminal clutter.
- **Priorities**: `urgent`, `high`, `normal`, `low`.

### Mode 6: Taxonomy Cartographer
- External subsystem bridge routing to repository cartography, AST parsing, and symbol taxonomy scanning.

---

## Terminal Display & Color Standards

All output strictly implements 57-column portrait terminal discipline with a high-contrast tri-color palette:

| Element | Format Specification | ANSI / Hex Sequence |
|---|---|---|
| **Headers & Labels** | Literal Functional Headers & Field Keys | `#DE2626` Truecolor (`\033[38;2;222;38;38m`) / ANSI Bold Red (`\033[1;31m`) |
| **Status Messages (Positive)** | `[✓]` with message in **white lowercase** | `\033[1;37m[✓] message in lowercase\033[0m` |
| **Failures & Errors** | `[✗]` with message in **#DE2626 UPPERCASE RED** | `\033[38;2;222;38;38m[✗] ERROR: MESSAGE IN UPPERCASE\033[0m` |
| **Neutral Content** | Descriptions, data values, timestamps, dividers | Standard White (`\033[0;37m` / `\033[1;37m`) |

---

## CLI Reference Guide

### Master Router Operations

```bash
# Display 57-column unified status banner
python3 management_tool.py --status

# List supported operational modes
python3 management_tool.py --list-modes

# Switch active persistent mode (1 to 6)
python3 management_tool.py --select-mode 1    # logging
python3 management_tool.py --select-mode 2    # reports
python3 management_tool.py --select-mode 3    # notes
python3 management_tool.py --select-mode 4    # jobs
python3 management_tool.py --select-mode 5    # reminders
python3 management_tool.py --select-mode 6    # taxonomy

# AI-optimized context specification
python3 management_tool.py --help
python3 management_tool.py --agent-context
```

### Reminders & Active Tasks (Mode 5)

```bash
# Add reminder (priority: urgent, high, normal, low)
python3 management_tool.py remind add "Update release documentation" -p high

# Complete and remove reminder (by ID or index)
python3 management_tool.py remind done 1
python3 management_tool.py remind done rem_20261109_024441

# List active reminders
python3 management_tool.py remind list

# View completed reminder archive
python3 management_tool.py remind completed

# Termux startup banner check
python3 management_tool.py remind print
```

### Job Chamber & Maintenance (Mode 4)

```bash
# Session startup initialization audit
python3 management_tool.py job --init-check

# Query standing maintenance jobs
python3 management_tool.py job --maintenance
python3 management_tool.py job --record-maintenance maint-001 -r "verified"

# Job queue discovery
python3 management_tool.py job --list
python3 management_tool.py job --list-completed
python3 management_tool.py job --query "optimization"

# Chamber locking & task stepping
python3 management_tool.py job --select "job_id_or_name"
python3 management_tool.py job --view
python3 management_tool.py job --add-task "Verify O(1) field cache"
python3 management_tool.py job --toggle-task 1

# Complete job and move to archive
python3 management_tool.py job --complete-job -m "All tasks completed and verified"
```

### Structured Logging (Mode 1)

```bash
# Write structured log entry
python3 management_tool.py log write -m "Refactor complete" -l INFO -s Core

# Read recent log entries
python3 management_tool.py log read --min-level WARN --limit 20

# Compile standalone HTML log report
python3 management_tool.py log report --limit 50 --theme dark
```

### Notes Manager (Mode 3)

```bash
# Category management
python3 management_tool.py note --list-categories
python3 management_tool.py note --category-create "Architecture" --desc "System specs"
python3 management_tool.py note --select-category "Architecture"

# Note authoring & chamber operations
python3 management_tool.py note --note-new -t "MFDB Spec" -c "Manifests use 104a." --tags "mfdb,spec"
python3 management_tool.py note --select-note "MFDB Spec"
python3 management_tool.py note --add-tag "v140"
python3 management_tool.py note --export

# Static documentation website build
python3 management_tool.py note --export-site

# Launch localhost web editor (port 5050)
python3 management_tool.py note --web
```

---

## Repository Structure

```
Management_Tool/
├── management_tool.py        # Master Router Entry Point (Modes 1-6)
├── management.sh             # Master Shell Launcher Wrapper
├── __main__.py               # Package Invocation Entry Point
├── bejson_project.json       # Project Metadata & Identity Descriptor
├── .gitignore                # Runtime State, Log & Temp File Exclusions
├── assets/
│   └── Management_CLI_Banner_1280x640.svg # Visual Header Graphic
├── config/
│   ├── config.json           # Default System Configuration Store
│   └── state.json            # Loaded Chamber Persistent Context State
├── data/
│   ├── maintenance_jobs_registry.104a.bejson # Standing Maintenance Tasks Registry
│   └── saved_jobs/           # Saved Job Documents & Workflow Templates
├── dev/
│   └── flask_notes_editor_plan.md # Subsystem Architecture Specification
├── lib/
│   ├── lib_log_report_generator.py # Markdown & HTML Report Generator
│   ├── lib_md_to_html.py           # Standalone Markdown-to-HTML Parser
│   └── templates/                  # High-Contrast Dark HTML Templates
└── tools/
    ├── job_manager/          # Mode 4: Stateful Job Chamber & Maintenance Manager
    │   ├── job_tool.py
    │   └── job_manager.py
    ├── logging_tool/         # Mode 1: Structured Logging Engine
    │   └── logging_tool.py
    ├── notes_tool/           # Mode 3: Categorized Notes MFDB Manager & Web Server
    │   ├── notes_tool.py
    │   ├── notes_web_server.py
    │   └── notes.sh
    ├── reminder_tool/        # Mode 5: Launch Reminders & Active Tasks Engine
    │   ├── reminder_tool.py
    │   ├── remind.sh
    │   └── data/
    └── report_indexer/       # Mode 2: Research Reports Indexer
        └── report_indexer.py
    ├── notes_mfdb_engine.py        # Notes MFDB Engine & Context Machine
    ├── notes_site_exporter.py      # Static Documentation Site Generator
    ├── lib_bejson_Core_*           # BEJSON Core Primitives & Field Map Engine
    └── lib_bejson_Standards_*      # BEJSON 105 Standards Logging Engine
```

---

## Verification & Testing

Verify end-to-end routing, color standards, and subsystem operations:

```bash
# Status banner check
python3 management_tool.py --status

# Subsystem delegation checks
python3 management_tool.py remind list
python3 management_tool.py job --init-check
python3 management_tool.py report --status
python3 management_tool.py note --status

# Mode selection verification
python3 management_tool.py --select-mode 5
python3 management_tool.py --select-mode 99  # verifies uppercase red error output
```

---

## License & Attribution

Authored by **Elton Boehnen** (`boehnenelton2024@gmail.com`).  
Project Website: [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev) · GitHub: [boehnenelton](https://github.com/boehnenelton)  
Licensed under the **PolyForm Noncommercial License 1.0.0** ([`LICENSE`](LICENSE) · [SPDX: PolyForm-Noncommercial-1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)).  
All rights reserved. Personal, educational, and research use permitted. Commercial use prohibited without explicit license from the author.
