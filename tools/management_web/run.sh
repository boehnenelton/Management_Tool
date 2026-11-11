#!/data/data/com.termux/files/usr/bin/env bash
# Name:    run.sh
# Version: 100
# Launcher shortcut for management_web server_manager

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
exec python3 "$SCRIPT_DIR/server_manager.py" "$@"
