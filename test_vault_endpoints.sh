#!/bin/bash
# Test script to verify all Vault endpoints work correctly

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8000}"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-admin123}"

echo "=========================================="
echo "Testing Vault Endpoints"
echo "=========================================="
echo ""

# Step 1: Authenticate
echo "Step 1: Authenticating..."
RESPONSE=$(curl -s -X POST "$VAULT_ADDR/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$RESPONSE" | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed!"
    echo "Response: $RESPONSE"
    exit 1
fi

export VAULT_TOKEN="$TOKEN"
export VAULT_ADDR="$VAULT_ADDR"

echo "✅ Authenticated successfully!"
echo ""

# Step 2: Test seal-status
echo "Step 2: Testing /v1/sys/seal-status..."
curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/seal-status" | head -5
echo ""

# Step 3: Test leader
echo "Step 3: Testing /v1/sys/leader..."
curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/leader" | head -5
echo ""

# Step 4: Test mounts
echo "Step 4: Testing /v1/sys/mounts..."
curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/mounts" | head -10
echo ""

# Step 5: Test internal UI mounts
echo "Step 5: Testing /v1/sys/internal/ui/mounts/secret..."
curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/sys/internal/ui/mounts/secret" | head -10
echo ""

# Step 6: Test KV put (with /data/)
echo "Step 6: Testing PUT /v1/secret/data/test..."
curl -s -X PUT -H "X-Vault-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"key1":"value1","key2":"value2"}}' \
  "$VAULT_ADDR/v1/secret/data/test" | head -10
echo ""

# Step 7: Test KV put (without /data/)
echo "Step 7: Testing PUT /v1/secret/test2..."
curl -s -X PUT -H "X-Vault-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"key1":"value1","key2":"value2"}' \
  "$VAULT_ADDR/v1/secret/test2" | head -10
echo ""

# Step 8: Test KV get
echo "Step 8: Testing GET /v1/secret/data/test..."
curl -s -H "X-Vault-Token: $TOKEN" "$VAULT_ADDR/v1/secret/data/test" | head -10
echo ""

echo "=========================================="
echo "All endpoint tests completed!"
echo "=========================================="

