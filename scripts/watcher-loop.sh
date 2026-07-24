#!/bin/bash
# watcher-loop.sh — Auto-restart bridge on exit
# Usage: ./watcher-loop.sh [config.yaml]
CONFIG="${1:-bridge.yaml}"
while true; do
    echo "[$(date)] Starting hermes-bridge..."
    python -m hermes_bridge -c "$CONFIG" run
    echo "[$(date)] Bridge exited (code $?), restarting in 5s..."
    sleep 5
done
