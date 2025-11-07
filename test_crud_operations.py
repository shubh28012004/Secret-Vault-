#!/usr/bin/env python3
"""
Test script to verify CRUD operations are working correctly
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "demo@secretvault.com"
TEST_PASSWORD = "DemoPass123!"

def test_login():
    """Test login functionality"""
    print("Testing login...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login successful for {TEST_EMAIL}")
        return data.get("access_token")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_get_credentials(token):
    """Test getting credentials"""
    print("\nTesting get credentials...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/credentials", headers=headers)
    
    if response.status_code == 200:
        credentials = response.json()
        print(f"✅ Retrieved {len(credentials)} credentials")
        return credentials
    else:
        print(f"❌ Get credentials failed: {response.status_code} - {response.text}")
        return []

def test_create_credential(token):
    """Test creating a new credential"""
    print("\nTesting create credential...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    credential_data = {
        "title": "Test Credential",
        "username": "testuser",
        "password": "TestPass123!",
        "category": "Testing",
        "url": "https://test.example.com",
        "notes": "This is a test credential"
    }
    
    response = requests.post(f"{BASE_URL}/credentials", json=credential_data, headers=headers)
    
    if response.status_code == 200:
        credential = response.json()
        print(f"✅ Created credential: {credential['title']} (ID: {credential['id']})")
        return credential
    else:
        print(f"❌ Create credential failed: {response.status_code} - {response.text}")
        return None

def test_get_single_credential(token, credential_id):
    """Test getting a single credential"""
    print(f"\nTesting get single credential (ID: {credential_id})...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/credentials/{credential_id}", headers=headers)
    
    if response.status_code == 200:
        credential = response.json()
        print(f"✅ Retrieved credential: {credential['title']}")
        return credential
    else:
        print(f"❌ Get single credential failed: {response.status_code} - {response.text}")
        return None

def test_update_credential(token, credential_id):
    """Test updating a credential"""
    print(f"\nTesting update credential (ID: {credential_id})...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    update_data = {
        "title": "Updated Test Credential",
        "notes": "This credential has been updated"
    }
    
    response = requests.put(f"{BASE_URL}/credentials/{credential_id}", json=update_data, headers=headers)
    
    if response.status_code == 200:
        credential = response.json()
        print(f"✅ Updated credential: {credential['title']}")
        return credential
    else:
        print(f"❌ Update credential failed: {response.status_code} - {response.text}")
        return None

def test_delete_credential(token, credential_id):
    """Test deleting a credential"""
    print(f"\nTesting delete credential (ID: {credential_id})...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(f"{BASE_URL}/credentials/{credential_id}", headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Deleted credential (ID: {credential_id})")
        return True
    else:
        print(f"❌ Delete credential failed: {response.status_code} - {response.text}")
        return False

def test_search_credentials(token):
    """Test searching credentials"""
    print("\nTesting search credentials...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/credentials/search/test", headers=headers)
    
    if response.status_code == 200:
        credentials = response.json()
        print(f"✅ Search returned {len(credentials)} results")
        return credentials
    else:
        print(f"❌ Search credentials failed: {response.status_code} - {response.text}")
        return []

def test_get_audit_logs(token):
    """Test getting audit logs"""
    print("\nTesting get audit logs...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/audit", headers=headers)
    
    if response.status_code == 200:
        logs = response.json()
        print(f"✅ Retrieved {len(logs)} audit logs")
        return logs
    else:
        print(f"❌ Get audit logs failed: {response.status_code} - {response.text}")
        return []

def main():
    """Run all CRUD tests"""
    print("🧪 Testing Secret Vault CRUD Operations")
    print("=" * 50)
    
    # Test login
    token = test_login()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return
    
    # Test get credentials (should be empty initially)
    initial_credentials = test_get_credentials(token)
    
    # Test create credential
    new_credential = test_create_credential(token)
    if not new_credential:
        print("❌ Cannot proceed without creating a test credential")
        return
    
    credential_id = new_credential['id']
    
    # Test get single credential
    test_get_single_credential(token, credential_id)
    
    # Test update credential
    test_update_credential(token, credential_id)
    
    # Test search credentials
    test_search_credentials(token)
    
    # Test get audit logs
    test_get_audit_logs(token)
    
    # Verify credential was created by getting all credentials again
    updated_credentials = test_get_credentials(token)
    if len(updated_credentials) > len(initial_credentials):
        print(f"✅ Credential count increased from {len(initial_credentials)} to {len(updated_credentials)}")
    
    # Test delete credential
    test_delete_credential(token, credential_id)
    
    # Verify credential was deleted
    final_credentials = test_get_credentials(token)
    if len(final_credentials) == len(initial_credentials):
        print(f"✅ Credential count returned to {len(final_credentials)} (cleanup successful)")
    
    print("\n" + "=" * 50)
    print("🎉 CRUD Operations Test Complete!")

if __name__ == "__main__":
    main()
