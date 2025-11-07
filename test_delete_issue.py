#!/usr/bin/env python3
"""
Test script to specifically test the delete operation
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
        "title": "Delete Test Credential",
        "username": "deletetest",
        "password": "DeleteTest123!",
        "category": "Testing",
        "url": "https://delete-test.example.com",
        "notes": "This credential will be deleted"
    }
    
    response = requests.post(f"{BASE_URL}/credentials", json=credential_data, headers=headers)
    
    if response.status_code == 200:
        credential = response.json()
        print(f"✅ Created credential: {credential['title']} (ID: {credential['id']})")
        return credential
    else:
        print(f"❌ Create credential failed: {response.status_code} - {response.text}")
        return None

def test_delete_credential(token, credential_id):
    """Test deleting a credential"""
    print(f"\nTesting delete credential (ID: {credential_id})...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(f"{BASE_URL}/credentials/{credential_id}", headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Delete request successful for credential (ID: {credential_id})")
        return True
    else:
        print(f"❌ Delete credential failed: {response.status_code} - {response.text}")
        return False

def test_credential_exists(token, credential_id):
    """Test if a credential still exists"""
    print(f"\nTesting if credential (ID: {credential_id}) still exists...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/credentials/{credential_id}", headers=headers)
    
    if response.status_code == 404:
        print(f"✅ Credential (ID: {credential_id}) no longer exists (404)")
        return False
    elif response.status_code == 200:
        print(f"❌ Credential (ID: {credential_id}) still exists (200)")
        return True
    else:
        print(f"❓ Unexpected response: {response.status_code} - {response.text}")
        return None

def main():
    """Run delete test"""
    print("🧪 Testing Delete Operation")
    print("=" * 50)
    
    # Test login
    token = test_login()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return
    
    # Get initial credentials
    initial_credentials = test_get_credentials(token)
    initial_count = len(initial_credentials)
    print(f"Initial credential count: {initial_count}")
    
    # Create a test credential
    new_credential = test_create_credential(token)
    if not new_credential:
        print("❌ Cannot proceed without creating a test credential")
        return
    
    credential_id = new_credential['id']
    
    # Verify credential was created
    after_create_credentials = test_get_credentials(token)
    after_create_count = len(after_create_credentials)
    print(f"After create credential count: {after_create_count}")
    
    if after_create_count != initial_count + 1:
        print(f"❌ Expected {initial_count + 1} credentials, got {after_create_count}")
        return
    
    # Test delete
    delete_success = test_delete_credential(token, credential_id)
    if not delete_success:
        print("❌ Delete operation failed")
        return
    
    # Wait a moment for the operation to complete
    time.sleep(1)
    
    # Verify credential no longer exists via direct GET
    still_exists = test_credential_exists(token, credential_id)
    if still_exists:
        print("❌ Credential still exists after delete")
        return
    
    # Verify credential count decreased
    after_delete_credentials = test_get_credentials(token)
    after_delete_count = len(after_delete_credentials)
    print(f"After delete credential count: {after_delete_count}")
    
    if after_delete_count != initial_count:
        print(f"❌ Expected {initial_count} credentials after delete, got {after_delete_count}")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Delete Operation Test Complete!")
    print("✅ Delete operation is working correctly on the backend")

if __name__ == "__main__":
    main()
