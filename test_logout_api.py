#!/usr/bin/env python3
"""
Test script to check logout API functionality
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "demo@secretvault.com"
TEST_PASSWORD = "DemoPass123!"

def test_login_and_logout():
    """Test login and logout functionality"""
    print("Testing login and logout API...")
    
    # Step 1: Login
    print("1. Logging in...")
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    login_result = login_response.json()
    access_token = login_result.get("access_token")
    
    if not access_token:
        print("❌ No access token received")
        return False
    
    print(f"✅ Login successful, token: {access_token[:20]}...")
    
    # Step 2: Test logout
    print("2. Testing logout...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    logout_response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    
    if logout_response.status_code == 200:
        print("✅ Logout API call successful")
        print(f"Response: {logout_response.json()}")
        return True
    else:
        print(f"❌ Logout failed: {logout_response.status_code}")
        print(f"Response: {logout_response.text}")
        return False

def test_credentials_after_logout():
    """Test if credentials endpoint still works after logout"""
    print("\n3. Testing credentials access after logout...")
    
    # First login to get token
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_response.status_code != 200:
        print("❌ Login failed for credentials test")
        return False
    
    access_token = login_response.json().get("access_token")
    
    # Test credentials access
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    creds_response = requests.get(f"{BASE_URL}/credentials", headers=headers)
    if creds_response.status_code == 200:
        print("✅ Credentials access successful")
    else:
        print(f"❌ Credentials access failed: {creds_response.status_code}")
    
    # Now logout
    logout_response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    if logout_response.status_code == 200:
        print("✅ Logout successful")
    else:
        print(f"❌ Logout failed: {logout_response.status_code}")
    
    # Try to access credentials again (should fail)
    creds_response_after = requests.get(f"{BASE_URL}/credentials", headers=headers)
    if creds_response_after.status_code == 401:
        print("✅ Credentials access properly blocked after logout")
        return True
    else:
        print(f"❌ Credentials still accessible after logout: {creds_response_after.status_code}")
        return False

if __name__ == "__main__":
    print("=== Logout API Test ===\n")
    
    # Test basic login/logout
    success1 = test_login_and_logout()
    
    # Test credentials access after logout
    success2 = test_credentials_after_logout()
    
    print(f"\n=== Test Results ===")
    print(f"Login/Logout: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Credentials after logout: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Logout API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the API implementation.")
