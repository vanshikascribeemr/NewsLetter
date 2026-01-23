#!/bin/bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
CRON_SCHEDULE="0 9 * * 5" # Every Friday at 9:00 AM
JOB_COMMAND="cd $SCRIPT_DIR && $PYTHON_EXEC -m src.main >> $SCRIPT_DIR/cron.log 2>&1"

# Check if cron job already exists
existing_job=$(crontab -l 2>/dev/null | grep "$SCRIPT_DIR")

if [ -n "$existing_job" ]; then
    echo "Cron job already exists:"
    echo "$existing_job"
    echo "To remove it, run: crontab -e"
else
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $JOB_COMMAND") | crontab -
    echo "Successfully scheduled newsletter for every Friday at 9 AM."
    echo "Command: $JOB_COMMAND"
    echo "Logs will be written to: $SCRIPT_DIR/cron.log"
fi
