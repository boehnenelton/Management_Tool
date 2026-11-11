#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Script Name:    env.sh
# Description:    Shell launcher for Environment & Definitions Management Tool.
# Version:        100
# Author:         Elton Boehnen · boehnenelton2024@gmail.com
# License:        PolyForm-Noncommercial-1.0.0
# Relational ID:  e9f2a1b4-7832-4d51-9e20-5c6e83d91b42
# ==============================================================================

set -euo pipefail

get_script_path() {
    local source="${BASH_SOURCE[0]}"
    while [ -h "$source" ]; do
        local dir="$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
        source="$(readlink "$source")"
        [[ $source != /* ]] && source="$dir/$source"
    done
    echo "$( cd -P "$( dirname "$source" )" >/dev/null 2>&1 && pwd )"
}

SCRIPT_PATH=$(get_script_path)
exec python3 "$SCRIPT_PATH/environment_tool.py" "$@"
