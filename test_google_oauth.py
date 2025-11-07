#!/usr/bin/env python3
"""
Test script for Google OAuth integration with Secret Vault
"""

import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_google_oauth_endpoint():
    """Test the Google OAuth endpoint"""
    print("🧪 Testing Google OAuth Integration")
    print("=" * 50)
    
    # Test data (simulated Google OAuth response)
    test_oauth_data = {
        "google_token": "test_google_token_123",
        "email": "testuser@gmail.com",
        "name": "Test User",
        "google_id": "1234567890",
        "profile_picture": "https://example.com/profile.jpg",
        "username": "testuser"
    }
    
    try:
        # Test the Google OAuth endpoint
        print("📡 Testing /auth/google endpoint...")
        response = requests.post(
            f"{API_BASE_URL}/auth/google",
            json=test_oauth_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Google OAuth endpoint working!")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Check if user was created/logged in
            if "access_token" in result:
                print("✅ JWT tokens generated successfully")
                print(f"Access Token: {result['access_token'][:50]}...")
                
                # Test token validity
                headers = {"Authorization": f"Bearer {result['access_token']}"}
                test_response = requests.get(f"{API_BASE_URL}/credentials", headers=headers)
                
                if test_response.status_code == 200:
                    print("✅ JWT token is valid and working")
                else:
                    print(f"⚠️ JWT token test failed: {test_response.status_code}")
            else:
                print("❌ No access token in response")
                
        else:
            print(f"❌ Google OAuth endpoint failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the backend is running:")
        print("   python main.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

def test_api_health():
    """Test if the API is healthy"""
    print("\n🏥 Testing API Health")
    print("-" * 30)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy and running")
            return True
        else:
            print(f"⚠️ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API is not running. Start it with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔐 Secret Vault Google OAuth Integration Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_BASE_URL}")
    print()
    
    # Test API health first
    if test_api_health():
        # Test Google OAuth endpoint
        test_google_oauth_endpoint()
    else:
        print("\n❌ Cannot proceed with OAuth tests - API is not running")
        print("\n📋 To start the API:")
        print("   1. Make sure you're in the project directory")
        print("   2. Run: python main.py")
        print("   3. Wait for 'Uvicorn running on http://127.0.0.1:8000' message")
        print("   4. Run this test again")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()
