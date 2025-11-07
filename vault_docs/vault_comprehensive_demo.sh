#!/bin/bash
# Comprehensive Vault Demo Script
# Demonstrates all Vault features and use cases

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8000}"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-admin123}"

# Ensure VAULT_ADDR is set
export VAULT_ADDR="$VAULT_ADDR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     HashiCorp Vault - Comprehensive Demo                    ║"
echo "║     Secret Vault Integration                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Authentication
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 1: Authentication${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Authenticating with Secret Vault..."
RESPONSE=$(curl -s -X POST "$VAULT_ADDR/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$RESPONSE" | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Authentication failed!${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

export VAULT_TOKEN="$TOKEN"
export VAULT_ADDR="$VAULT_ADDR"

echo -e "${GREEN}✅ Authenticated successfully!${NC}"
echo "Token: ${TOKEN:0:20}..."
vault token lookup | head -5
echo ""

# Step 2: System Status
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 2: System Status & Health Check${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
vault status
echo ""

# Step 3: Secret Engine Mounts
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 3: Secret Engine Mounts${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Available secret engines:"
vault secrets list
echo ""

# Step 4: Use Case 1 - Storing Application Secrets
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 1: Storing Application Secrets${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Storing production database credentials..."
vault kv put secret/production/database \
  host=prod-db.example.com \
  port=5432 \
  username=app_user \
  password=SuperSecurePassword123! \
  database=production_db

echo ""
echo "Storing API keys for third-party services..."
vault kv put secret/production/api-keys \
  stripe_key=sk_live_abc123xyz \
  aws_access_key=AKIAIOSFODNN7EXAMPLE \
  github_token=ghp_1234567890abcdef

echo ""
echo "Storing encryption keys..."
vault kv put secret/production/encryption \
  fernet_key=base64_encoded_key_here \
  aes_key=another_encryption_key

echo -e "${GREEN}✅ Application secrets stored securely${NC}"
echo ""

# Step 5: Use Case 2 - Secret Versioning
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 2: Secret Versioning & History${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Reading current version of database secret:"
vault kv get secret/production/database
echo ""

echo "Updating password (creates new version)..."
vault kv put secret/production/database \
  host=prod-db.example.com \
  port=5432 \
  username=app_user \
  password=NewSecurePassword456! \
  database=production_db

echo ""
echo "Viewing secret metadata (version history):"
vault kv metadata get secret/production/database
echo ""

echo "Reading previous version:"
vault kv get -version=1 secret/production/database
echo -e "${GREEN}✅ Secret versioning demonstrated${NC}"
echo ""

# Step 6: Use Case 3 - Organizing Secrets
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 3: Organizing Secrets by Environment${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Storing development environment secrets..."
vault kv put secret/development/database \
  host=dev-db.example.com \
  username=dev_user \
  password=dev_password

vault kv put secret/development/api-keys \
  stripe_key=sk_test_abc123 \
  aws_access_key=AKIADEVEXAMPLE

echo ""
echo "Storing staging environment secrets..."
vault kv put secret/staging/database \
  host=staging-db.example.com \
  username=staging_user \
  password=staging_password

echo ""
echo "Listing all secrets:"
vault kv list secret/
echo ""
echo "Listing production secrets:"
vault kv list secret/production/
echo -e "${GREEN}✅ Secrets organized by environment${NC}"
echo ""

# Step 7: Use Case 4 - Access Control & Policies
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 4: Access Control & Policies${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Current policies:"
vault policy list
echo ""

echo "Viewing default policy:"
vault policy read default
echo ""

echo "Creating a developer policy (read-only access to development secrets)..."
vault policy write developer-policy - <<EOF
path "secret/data/development/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/development/*" {
  capabilities = ["list", "read"]
}
EOF

echo ""
echo "Creating a token with developer policy:"
DEV_TOKEN=$(vault token create -policy=developer-policy -format=json | grep -o '"client_token":"[^"]*' | cut -d'"' -f4)
echo "Developer token created: ${DEV_TOKEN:0:20}..."
echo -e "${GREEN}✅ Access control policies demonstrated${NC}"
echo ""

# Step 8: Use Case 5 - Token Management
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 5: Token Management${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Creating a new token with specific TTL:"
vault token create -ttl=1h -display-name="demo-token"
echo ""

echo "Renewing current token:"
vault token renew
echo ""

echo "Looking up token information:"
vault token lookup
echo -e "${GREEN}✅ Token management demonstrated${NC}"
echo ""

# Step 9: Use Case 6 - Secret Rotation
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 6: Secret Rotation${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Current database password:"
vault kv get -field=password secret/production/database
echo ""

echo "Rotating password (creating new version)..."
vault kv put secret/production/database \
  host=prod-db.example.com \
  port=5432 \
  username=app_user \
  password=RotatedPassword789! \
  database=production_db

echo ""
echo "New password:"
vault kv get -field=password secret/production/database
echo ""

echo "Version history:"
vault kv metadata get secret/production/database | grep -A 5 versions
echo -e "${GREEN}✅ Secret rotation demonstrated${NC}"
echo ""

# Step 10: Use Case 7 - Secret Deletion & Recovery
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}USE CASE 7: Secret Deletion & Recovery${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo "Creating a temporary secret:"
vault kv put secret/temp/test \
  key1=value1 \
  key2=value2
echo ""

echo "Deleting the secret:"
vault kv delete secret/temp/test
echo ""

echo "Attempting to read deleted secret (should fail):"
vault kv get secret/temp/test 2>&1 || echo "Secret not found (as expected)"
echo ""

echo "Note: In production, deleted secrets can be recovered from previous versions"
echo -e "${GREEN}✅ Secret deletion demonstrated${NC}"
echo ""

# Step 11: Summary
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}DEMO SUMMARY${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "✅ Demonstrated Features:"
echo "   1. Authentication & Token Management"
echo "   2. Secret Storage (KV v2 Engine)"
echo "   3. Secret Versioning & History"
echo "   4. Secret Organization by Environment"
echo "   5. Access Control & Policies"
echo "   6. Token Lifecycle Management"
echo "   7. Secret Rotation"
echo "   8. Secret Deletion"
echo ""
echo "📊 Current Secret Count:"
vault kv list secret/ 2>/dev/null | wc -l | xargs echo "   Total paths:"
echo ""
echo "🔐 Security Features:"
echo "   • All secrets encrypted at rest"
echo "   • Policy-based access control"
echo "   • Complete audit trail"
echo "   • Token-based authentication"
echo "   • Version history for all secrets"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Demo Completed Successfully! ✅                            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next Steps:"
echo "  • Review audit logs: vault audit list"
echo "  • Create custom policies: vault policy write <name> <policy.hcl>"
echo "  • Integrate with applications using Vault API"
echo "  • Set up secret rotation schedules"
echo ""

