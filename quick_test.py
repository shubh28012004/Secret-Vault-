#!/usr/bin/env python3
"""
Quick test script to verify backend is working and create test users
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_backend():
    """Test if backend is working"""
    print("🔍 Testing Backend...")
    
    try:
        # Test health endpoint
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running:")
        print("   python main.py")
        return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False

def create_test_user(email, username, full_name, password):
    """Create a test user"""
    print(f"📝 Creating user: {email}")
    
    user_data = {
        "email": email,
        "username": username,
        "full_name": full_name,
        "password": password
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/signup",
            json=user_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ User created: {email}")
            return True
        else:
            print(f"❌ Failed to create user: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False

def test_login(email, password):
    """Test login"""
    print(f"🔐 Testing login: {email}")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Login successful: {email}")
            return result.get("access_token")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error testing login: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Secret Vault - Quick Backend Test")
    print("=" * 40)
    
    # Test backend
    if not test_backend():
        return
    
    print("\n📋 Creating Test Users...")
    print("-" * 30)
    
    # Test users
    test_users = [
        {
            "email": "testadmin@example.com",
            "username": "testadmin", 
            "full_name": "Test Admin",
            "password": "TestAdmin123!"
        },
        {
            "email": "testuser@example.com",
            "username": "testuser",
            "full_name": "Test User", 
            "password": "TestUser123!"
        }
    ]
    
    created_count = 0
    
    # Create users
    for user in test_users:
        if create_test_user(**user):
            created_count += 1
        time.sleep(0.5)  # Small delay
    
    print(f"\n✅ Created {created_count}/{len(test_users)} users")
    
    # Test logins
    print(f"\n🔐 Testing Logins...")
    print("-" * 20)
    
    successful_logins = 0
    
    for user in test_users:
        token = test_login(user["email"], user["password"])
        if token:
            successful_logins += 1
        time.sleep(0.5)
    
    print(f"\n✅ {successful_logins}/{len(test_users)} logins successful")
    
    # Summary
    print(f"\n🎯 TEST SUMMARY")
    print("=" * 20)
    print(f"Backend Status: {'✅ Working' if test_backend() else '❌ Failed'}")
    print(f"Users Created: {created_count}/{len(test_users)}")
    print(f"Logins Working: {successful_logins}/{len(test_users)}")
    
    if created_count > 0 and successful_logins > 0:
        print(f"\n🚀 Ready for Streamlit testing!")
        print("Run: streamlit run app1.py")
        print("\nTest Credentials:")
        for user in test_users:
            print(f"  {user['email']} / {user['password']}")
    else:
        print(f"\n⚠️ Some issues detected. Check the logs above.")

if __name__ == "__main__":
    main()
