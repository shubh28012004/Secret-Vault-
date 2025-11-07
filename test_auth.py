import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from auth import get_password_hash, verify_password
from database import get_db
from models import User

def test_password_hashing():
    """Test password hashing and verification"""
    password = "DemoPass123!"
    
    # Hash the password
    hashed = get_password_hash(password)
    print(f"Original password: {password}")
    print(f"Hashed password: {hashed}")
    
    # Verify the password
    is_valid = verify_password(password, hashed)
    print(f"Password verification: {is_valid}")
    
    # Test wrong password
    is_valid_wrong = verify_password("WrongPassword", hashed)
    print(f"Wrong password verification: {is_valid_wrong}")
    
    return is_valid

def test_demo_user_auth():
    """Test demo user authentication"""
    try:
        db = next(get_db())
        
        # Get demo user
        demo_user = db.query(User).filter(User.email == "demo@secretvault.com").first()
        if not demo_user:
            print("❌ Demo user not found")
            return False
        
        print(f"Demo user found: {demo_user.email}")
        print(f"Stored hash: {demo_user.hashed_password}")
        print(f"Is verified: {demo_user.is_verified}")
        print(f"Is active: {demo_user.is_active}")
        
        # Test password verification
        test_password = "DemoPass123!"
        is_valid = verify_password(test_password, demo_user.hashed_password)
        print(f"Demo password verification: {is_valid}")
        
        return is_valid
        
    except Exception as e:
        print(f"Error testing demo user: {e}")
        return False

if __name__ == "__main__":
    print("Testing password authentication...")
    print("=" * 40)
    
    # Test password hashing
    print("1. Testing password hashing:")
    hash_test = test_password_hashing()
    print()
    
    # Test demo user
    print("2. Testing demo user authentication:")
    demo_test = test_demo_user_auth()
    print()
    
    print("=" * 40)
    if hash_test and demo_test:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
