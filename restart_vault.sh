#!/bin/bash
# Quick script to restart the Vault server

echo "Stopping existing server..."
pkill -f "uvicorn main:app" || echo "No server running"

sleep 2

echo "Starting server..."
cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

