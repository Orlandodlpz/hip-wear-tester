#!/bin/bash
# launch.sh — start the Hip Wear Tester GUI from a desktop shortcut or
# from the LXDE autostart entry.
#
# This script:
#   1. Locates the project directory (one level up from the script).
#   2. Activates the project's Python venv if it exists.
#   3. Runs main.py.
#
# Logs stdout/stderr to a rotating log file under ~/.hip-wear-tester/ so
# crashes are diagnosable after the fact.

set -e

# Resolve the project root (parent of the directory containing this script),
# regardless of where the user invokes it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Set up log directory.
LOG_DIR="$HOME/.hip-wear-tester"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/app.log"

cd "$PROJECT_DIR"

# Activate the venv if one was created during setup.
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Append a separator + timestamp on each launch so log entries are easier to
# find when something goes wrong.
{
    echo ""
    echo "===================================================================="
    echo "Launch: $(date)"
    echo "Project: $PROJECT_DIR"
    echo "===================================================================="
} >> "$LOG_FILE"

# Run the app, capturing both stdout and stderr to the log. exec so this
# shell doesn't stick around as a parent process.
exec python3 main.py >> "$LOG_FILE" 2>&1
