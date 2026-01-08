#!/bin/bash

# DJI Footage Processing - Background Runner
# Runs the processing pipeline in the background with logging

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/process_footage.py"
LOG_FILE="$SCRIPT_DIR/process_footage.log"
PID_FILE="$SCRIPT_DIR/process_footage.pid"

# Get Python executable (try pyenv first, then system python)
PYTHON_BIN="/home/darkangel/.pyenv/versions/homeai/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python3)
fi

echo "Starting DJI footage processing in background..."
echo "Log file: $LOG_FILE"

# Run with nohup to survive terminal close
nohup "$PYTHON_BIN" "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1 &

# Save PID
echo $! > "$PID_FILE"
echo "Process started with PID: $(cat $PID_FILE)"
echo ""
echo "To monitor progress:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To stop the process:"
echo "  kill \$(cat $PID_FILE)"
echo ""
