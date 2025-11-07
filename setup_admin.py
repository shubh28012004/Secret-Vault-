#!/usr/bin/env python3
"""
Setup script for Secret Vault - Creates initial admin user and demo account
"""
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from database import engine, get_db
from models import Base, User
from crud import create_user, get_user_by_email
from auth import get_password_hash
from logger import get_logger

logger = get_logger("setup_admin")

def create_admin_user():
    """Create the initial admin user"""
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        
        db = next(get_db())
        
        # Check if admin user already exists
        admin_user = get_user_by_email(db, "admin@secretvault.com")
        if admin_user:
            print("✅ Admin user already exists")
            return admin_user
        
        # Create admin user
        admin_data = {
            "email": "admin@secretvault.com",
            "username": "admin",
            "full_name": "System Administrator",
            "password": "AdminPass123!"
        }
        
        # Create user with admin privileges
        hashed_password = get_password_hash(admin_data["password"])
        admin_user = User(
            email=admin_data["email"].lower(),
            username=admin_data["username"].lower(),
            hashed_password=hashed_password,
            full_name=admin_data["full_name"],
            is_active=True,
            is_verified=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully")
        print(f"   Email: {admin_data['email']}")
        print(f"   Username: {admin_data['username']}")
        print(f"   Password: {admin_data['password']}")
        
        return admin_user
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        print(f"❌ Failed to create admin user: {e}")
        return None

def create_demo_user():
    """Create a demo user for testing"""
    try:
        db = next(get_db())
        
        # Check if demo user already exists
        demo_user = get_user_by_email(db, "demo@secretvault.com")
        if demo_user:
            print("✅ Demo user already exists")
            return demo_user
        
        # Create demo user
        demo_data = {
            "email": "demo@secretvault.com",
            "username": "demo",
            "full_name": "Demo User",
            "password": "DemoPass123!"
        }
        
        # Create user
        hashed_password = get_password_hash(demo_data["password"])
        demo_user = User(
            email=demo_data["email"].lower(),
            username=demo_data["username"].lower(),
            hashed_password=hashed_password,
            full_name=demo_data["full_name"],
            is_active=True,
            is_verified=True,
            is_admin=False
        )
        
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        
        print("✅ Demo user created successfully")
        print(f"   Email: {demo_data['email']}")
        print(f"   Username: {demo_data['username']}")
        print(f"   Password: {demo_data['password']}")
        
        return demo_user
        
    except Exception as e:
        logger.error(f"Failed to create demo user: {e}")
        print(f"❌ Failed to create demo user: {e}")
        return None

def verify_database():
    """Verify database connection and tables"""
    try:
        db = next(get_db())
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        print("✅ Database connection verified")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🔐 Secret Vault Setup")
    print("=" * 50)
    
    # Verify database
    if not verify_database():
        print("❌ Setup failed: Database connection error")
        return False
    
    # Create admin user
    admin_user = create_admin_user()
    if not admin_user:
        print("❌ Setup failed: Could not create admin user")
        return False
    
    # Create demo user
    demo_user = create_demo_user()
    if not demo_user:
        print("❌ Setup failed: Could not create demo user")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Account Information:")
    print("   Admin Account:")
    print("     Email: admin@secretvault.com")
    print("     Password: AdminPass123!")
    print("     Role: Administrator")
    print("\n   Demo Account:")
    print("     Email: demo@secretvault.com")
    print("     Password: DemoPass123!")
    print("     Role: Regular User")
    print("\n🚀 You can now start the application with:")
    print("   python main.py")
    print("\n🌐 Access the application at:")
    print("   http://localhost:8000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
