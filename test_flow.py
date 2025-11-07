#!/usr/bin/env python3
"""
Test script to verify the complete login/logout flow
"""
import requests
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "demo@secretvault.com"
TEST_PASSWORD = "DemoPass123!"

def test_complete_flow():
    """Test the complete login/logout flow"""
    print("=== Testing Complete Login/Logout Flow ===\n")
    
    # Step 1: Test root redirect
    print("1. Testing root redirect...")
    try:
        response = requests.get(f"{BASE_URL}/", allow_redirects=False)
        if response.status_code in [301, 302, 303, 307, 308]:
            print(f"✅ Root redirects to: {response.headers.get('Location', 'unknown')}")
        else:
            print(f"❌ Root doesn't redirect: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing root: {e}")
    
    # Step 2: Test login page
    print("\n2. Testing login page...")
    try:
        response = requests.get(f"{BASE_URL}/login")
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print(f"❌ Login page error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing login page: {e}")
    
    # Step 3: Test dashboard page
    print("\n3. Testing dashboard page...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard")
        if response.status_code == 200:
            print("✅ Dashboard page accessible")
        else:
            print(f"❌ Dashboard page error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing dashboard page: {e}")
    
    # Step 4: Test logout page
    print("\n4. Testing logout page...")
    try:
        response = requests.get(f"{BASE_URL}/logout")
        if response.status_code == 200:
            print("✅ Logout page accessible")
        else:
            print(f"❌ Logout page error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing logout page: {e}")
    
    # Step 5: Test login API
    print("\n5. Testing login API...")
    try:
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            print("✅ Login API working")
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                print("✅ Access token received")
                
                # Step 6: Test logout API
                print("\n6. Testing logout API...")
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                logout_response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
                if logout_response.status_code == 200:
                    print("✅ Logout API working")
                else:
                    print(f"❌ Logout API error: {logout_response.status_code}")
            else:
                print("❌ No access token received")
        else:
            print(f"❌ Login API error: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing login/logout API: {e}")
    
    print("\n=== Flow Test Complete ===")

if __name__ == "__main__":
    test_complete_flow()
