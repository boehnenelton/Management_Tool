#!/data/data/com.termux/files/usr/bin/env bash
# ==============================================================================
# Name:           management.sh
# Description:    Unified Management Tool Entrypoint Router
# Version:        120
# Author:         Elton Boehnen
# License:        MIT / BEJSON Standard
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

SCRIPT_PATH="$(get_script_path)"
ENTRYPOINT="$SCRIPT_PATH/management_tool.py"

exec python3 "$ENTRYPOINT" "$@"
