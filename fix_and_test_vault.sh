#!/bin/bash
# Comprehensive script to fix and test all Vault endpoints

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Vault Fix & Test Script                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0

# Step 1: Stop existing server
echo "Step 1: Stopping existing server..."
pkill -f "uvicorn main:app" || echo "No server running"
sleep 2

# Step 2: Start server in background
echo "Step 2: Starting server..."
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/vault_server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Step 3: Wait for server to be ready
echo "Step 3: Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/v1/sys/health > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Server failed to start"
        cat /tmp/vault_server.log
        exit 1
    fi
    sleep 1
done

# Step 4: Test endpoints
echo ""
echo "Step 4: Testing endpoints..."
export VAULT_ADDR=http://127.0.0.1:8000

# Authenticate
RESPONSE=$(curl -s -X POST "$VAULT_ADDR/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}')

TOKEN=$(echo "$RESPONSE" | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)
export VAULT_TOKEN="$TOKEN"

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed!"
    exit 1
fi

echo "✅ Authenticated"

# Test seal-status
echo -n "Testing /v1/sys/seal-status... "
if curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/seal-status" | grep -q "initialized"; then
    echo "✅"
else
    echo "❌"
fi

# Test leader
echo -n "Testing /v1/sys/leader... "
if curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/leader" | grep -q "ha_enabled"; then
    echo "✅"
else
    echo "❌"
fi

# Test internal UI mounts
echo -n "Testing /v1/sys/internal/ui/mounts/secret... "
RESULT=$(curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/internal/ui/mounts/secret")
if echo "$RESULT" | grep -q "type"; then
    echo "✅"
else
    echo "❌ ($RESULT)"
fi

# Test KV put
echo -n "Testing vault kv put... "
if vault kv put secret/test key=value > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
fi

# Test KV get
echo -n "Testing vault kv get... "
if vault kv get secret/test > /dev/null 2>&1; then
    echo "✅"
else
    echo "❌"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Server is running!                                       ║"
echo "║     PID: $SERVER_PID                                         ║"
echo "║     Logs: /tmp/vault_server.log                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "You can now run:"
echo "  export VAULT_ADDR=http://127.0.0.1:8000"
echo "  ./vault_docs/vault_comprehensive_demo.sh admin@example.com admin123"
echo ""
echo "To stop the server: kill $SERVER_PID"

