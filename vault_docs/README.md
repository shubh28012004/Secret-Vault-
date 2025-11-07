# Vault Documentation

This folder contains all HashiCorp Vault integration documentation and demo scripts.

## Files

- **VAULT_COMPREHENSIVE_REPORT.md** - Complete documentation covering:
  - Why we used Vault
  - What we used it for
  - Implementation details
  - Quick start guide
  - Usage & commands
  - Demo guide
  - Architecture
  - Security & compliance
  - Troubleshooting

## Demo Scripts

- **vault_demo.sh** - Quick demo (5 minutes)
- **vault_comprehensive_demo.sh** - Full demo (10 minutes)
- **vault_login_helper.sh** - Authentication helper (Bash)
- **vault_login_helper.py** - Authentication helper (Python)

## Quick Start

1. **Set environment variable** (REQUIRED):
   ```bash
   export VAULT_ADDR=http://127.0.0.1:8000
   ```

2. **Start the application** (if not running):
   ```bash
   cd /Users/shubh/Desktop/CYBERSECURITY/secret-vault-7.0
   source venv/bin/activate
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Authenticate**:
   ```bash
   ./vault_docs/vault_login_helper.sh admin@example.com admin123
   ```

4. **Run demo**:
   ```bash
   ./vault_docs/vault_comprehensive_demo.sh admin@example.com admin123
   ```

**Note**: After adding new endpoints, restart the server for changes to take effect.

For complete documentation, see **VAULT_COMPREHENSIVE_REPORT.md**.

