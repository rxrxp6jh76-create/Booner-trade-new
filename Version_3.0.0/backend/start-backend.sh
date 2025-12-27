#!/bin/bash
cd ~/Booner-App/backend
source venv/bin/activate

while true; do
    echo "$(date): Starting backend..."
    python3 server.py
    
    # Falls crashed, warte 5 Sekunden und starte neu
    echo "$(date): Backend stopped. Restarting in 5 seconds..."
    sleep 5
done
