#!/bin/bash
# Demo script for Vault CLI with Secret Vault
# This script demonstrates the full Vault functionality

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8000}"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-admin123}"

# Ensure VAULT_ADDR is exported
export VAULT_ADDR="$VAULT_ADDR"

echo "=========================================="
echo "Secret Vault - Vault CLI Demo"
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
echo "Token: ${TOKEN:0:20}..."
echo ""

# Step 2: Check token
echo "Step 2: Checking token..."
vault token lookup
echo ""

# Step 3: Check health
echo "Step 3: Checking Vault health..."
vault status
echo ""

# Step 4: List mounts
echo "Step 4: Listing secret engine mounts..."
vault secrets list
echo ""

# Step 5: Write a secret
echo "Step 5: Writing a secret..."
vault kv put secret/myapp/database \
  username=admin \
  password=secret123 \
  host=db.example.com
echo ""

# Step 6: Read the secret
echo "Step 6: Reading the secret..."
vault kv get secret/myapp/database
echo ""

# Step 7: List secrets
echo "Step 7: Listing secrets..."
vault kv list secret/
echo ""

# Step 8: Write another secret
echo "Step 8: Writing another secret..."
vault kv put secret/api/keys \
  api_key=abc123xyz \
  api_secret=super-secret-key
echo ""

# Step 9: List all secrets
echo "Step 9: Listing all secrets..."
vault kv list secret/
echo ""

# Step 10: Get secret metadata
echo "Step 10: Getting secret metadata..."
vault kv metadata get secret/myapp/database
echo ""

# Step 11: Update secret (creates new version)
echo "Step 11: Updating secret (creates new version)..."
vault kv put secret/myapp/database \
  username=admin \
  password=newpassword456 \
  host=db.example.com \
  port=5432
echo ""

# Step 12: Get specific version
echo "Step 12: Getting specific version..."
vault kv get -version=1 secret/myapp/database
echo ""

# Step 13: List policies
echo "Step 13: Listing policies..."
vault policy list
echo ""

# Step 14: Create a new token
echo "Step 14: Creating a new token..."
NEW_TOKEN_RESPONSE=$(vault token create -format=json)
NEW_TOKEN=$(echo "$NEW_TOKEN_RESPONSE" | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)
echo "New token created: ${NEW_TOKEN:0:20}..."
echo ""

# Step 15: Renew token
echo "Step 15: Renewing token..."
vault token renew
echo ""

echo "=========================================="
echo "Demo completed successfully! ✅"
echo "=========================================="
echo ""
echo "You can now use the Vault CLI with:"
echo "  export VAULT_ADDR=$VAULT_ADDR"
echo "  export VAULT_TOKEN=$TOKEN"
echo ""
echo "Try these commands:"
echo "  vault kv list secret/"
echo "  vault kv get secret/myapp/database"
echo "  vault token lookup"

