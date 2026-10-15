#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "=========================================================="
echo " 🚀 ENI Chain Telegram & Twitter Automation Platform"
echo " 🌐 Web Console: http://127.0.0.1:8080"
echo "=========================================================="

python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
