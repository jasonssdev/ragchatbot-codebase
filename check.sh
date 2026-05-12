#!/bin/bash
# Run code quality checks. Pass --fix to auto-format instead of just checking.

set -e

FIX=false
if [[ "$1" == "--fix" ]]; then
    FIX=true
fi

echo "Running code quality checks..."

if $FIX; then
    echo "  Formatting with black..."
    uv run black backend/ main.py
    echo "  Done."
else
    echo "  Checking formatting with black..."
    uv run black --check --diff backend/ main.py
    echo "  All checks passed."
fi
