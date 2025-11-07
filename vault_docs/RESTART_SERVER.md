# ⚠️ IMPORTANT: Restart Server After Code Changes

The `/v1/sys/seal-status` endpoint has been added to the code, but **you must restart the server** for it to work.

## How to Restart

### Option 1: If server is running in terminal
1. Press `Ctrl+C` to stop the server
2. Restart with:
   ```bash
   cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Option 2: Kill and restart
```bash
# Kill existing server
pkill -f "uvicorn main:app"

# Start fresh
cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Option 3: Check if running and restart
```bash
# Check if server is running
ps aux | grep uvicorn

# If running, kill it
pkill -f "uvicorn main:app"

# Start server
cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Verify the Endpoint Works

After restarting, test the endpoint:
```bash
curl http://127.0.0.1:8000/v1/sys/seal-status
```

You should see JSON response with seal status information.

## Then Run Demo

```bash
export VAULT_ADDR=http://127.0.0.1:8000
./vault_docs/vault_comprehensive_demo.sh admin@example.com admin123
```

