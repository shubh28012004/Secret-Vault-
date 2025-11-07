#!/bin/bash
# Helper script to authenticate with Secret Vault using Vault CLI
# Usage: ./vault_login_helper.sh <email> <password>

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8000}"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-admin123}"

# Ensure VAULT_ADDR is exported
export VAULT_ADDR="$VAULT_ADDR"

echo "Authenticating with Secret Vault at $VAULT_ADDR..."
echo "Email: $EMAIL"

# Login via the JWT endpoint
RESPONSE=$(curl -s -X POST "$VAULT_ADDR/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

# Extract token from response
TOKEN=$(echo "$RESPONSE" | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Error: Failed to authenticate"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "Authentication successful!"
echo "Token: $TOKEN"
echo ""
echo "Setting VAULT_TOKEN environment variable..."
export VAULT_TOKEN="$TOKEN"

echo "Testing token lookup..."
vault token lookup

echo ""
echo "You can now use the Vault CLI with:"
echo "  export VAULT_ADDR=$VAULT_ADDR"
echo "  export VAULT_TOKEN=$TOKEN"
echo "  vault token lookup"

