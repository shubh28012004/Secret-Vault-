#!/usr/bin/env python3
"""
Helper script to authenticate with Secret Vault using Vault CLI
Usage: python vault_login_helper.py <email> <password>
"""
import sys
import os
import json
import requests

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8000")
EMAIL = sys.argv[1] if len(sys.argv) > 1 else "admin@example.com"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "admin123"

def main():
    print(f"Authenticating with Secret Vault at {VAULT_ADDR}...")
    print(f"Email: {EMAIL}")
    
    try:
        # Login via the JWT endpoint
        response = requests.post(
            f"{VAULT_ADDR}/v1/auth/jwt/login",
            json={"email": EMAIL, "password": PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        token = data.get("auth", {}).get("client_token")
        
        if not token:
            print("Error: Failed to authenticate")
            print(f"Response: {json.dumps(data, indent=2)}")
            sys.exit(1)
        
        print("Authentication successful!")
        print(f"Token: {token}")
        print()
        print("Set these environment variables:")
        print(f"  export VAULT_ADDR={VAULT_ADDR}")
        print(f"  export VAULT_TOKEN={token}")
        print()
        print("Then you can use the Vault CLI:")
        print("  vault token lookup")
        
        # Optionally set environment variable for current shell
        os.environ["VAULT_TOKEN"] = token
        os.environ["VAULT_ADDR"] = VAULT_ADDR
        
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to connect to {VAULT_ADDR}")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

