#!/bin/bash

set -euo pipefail

PROJECT_ROOT="/work/brash/dept-llm-assistant"
REMOTE="gdrive:"
DEST="${PROJECT_ROOT}/storage/raw_drive"
LOG_DIR="${PROJECT_ROOT}/storage/logs"

mkdir -p "$DEST" "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/sync_drive_${TIMESTAMP}.log"

echo "Starting Google Drive sync..."
echo "Remote: $REMOTE"
echo "Destination: $DEST"
echo "Log: $LOG_FILE"
echo

rclone sync "$REMOTE" "$DEST" \
    --progress \
    --log-file "$LOG_FILE" \
    --log-level INFO

echo
echo "Sync complete."
