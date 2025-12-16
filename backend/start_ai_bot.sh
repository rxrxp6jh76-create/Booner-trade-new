#!/bin/bash

echo "🤖 Starting AI Trading Bot..."
echo "=============================="
echo ""

cd /app/backend

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run bot
python ai_trading_bot.py
