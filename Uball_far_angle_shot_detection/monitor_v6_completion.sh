#!/bin/bash

echo "Monitoring V6 Game Runs..."
echo "Started: $(date)"
echo ""

while true; do
    # Check if any game processes are still running
    game_count=$(ps aux | grep -E "main.py.*game.*farright" | grep -v grep | grep python | wc -l)
    
    if [ $game_count -eq 0 ]; then
        echo ""
        echo "✅ All V6 games completed at: $(date)"
        echo ""
        echo "Results directories:"
        ls -ltr results/ | tail -5
        break
    fi
    
    # Show current CPU time for running processes
    clear
    echo "V6 Game Runs In Progress... ($(date))"
    echo "=========================================="
    ps aux | grep -E "main.py.*game.*farright" | grep python | grep -v grep | awk '{print "Game: " $11 " | CPU Time: " $10 " | PID: " $2}'
    echo ""
    echo "Waiting for completion... (checking every 2 minutes)"
    
    sleep 120
done
