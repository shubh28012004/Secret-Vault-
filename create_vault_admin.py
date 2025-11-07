#!/usr/bin/env python3
"""
Create admin user for Vault CLI demo
Creates admin@example.com with password admin123
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from database import engine, get_db
from models import Base, User
from crud import get_user_by_email
from auth import get_password_hash
from logger import get_logger

logger = get_logger("create_vault_admin")

def create_vault_admin():
    """Create admin@example.com user for Vault demo"""
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        
        db = next(get_db())
        
        # Check if user already exists by email
        existing_user = get_user_by_email(db, "admin@example.com")
        if existing_user:
            print("✅ User admin@example.com already exists")
            # Update to ensure it's active, verified, and admin
            existing_user.is_active = True
            existing_user.is_verified = True
            existing_user.is_admin = True
            existing_user.hashed_password = get_password_hash("admin123")
            db.commit()
            print("✅ User updated: active, verified, and admin privileges set")
            print(f"   Email: admin@example.com")
            print(f"   Password: admin123")
            return existing_user
        
        # Check if username "admin" is taken by another user
        from sqlalchemy.orm import Session
        from sqlalchemy import and_
        existing_admin_username = db.query(User).filter(
            and_(User.username == "admin", User.email != "admin@example.com")
        ).first()
        
        username = "admin"
        if existing_admin_username:
            # Use a different username
            username = "vaultadmin"
            print(f"⚠️  Username 'admin' is taken, using '{username}' instead")
        
        # Create admin user
        admin_user = User(
            email="admin@example.com",
            username=username,
            hashed_password=get_password_hash("admin123"),
            full_name="Vault Admin",
            is_active=True,
            is_verified=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   Email: admin@example.com")
        print(f"   Password: admin123")
        print(f"   Role: Administrator")
        
        return admin_user
        
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔐 Creating Vault Admin User")
    print("=" * 50)
    user = create_vault_admin()
    if user:
        print("\n✅ Ready to use Vault CLI!")
        print("   Run: ./vault_login_helper.sh admin@example.com admin123")
    else:
        print("\n❌ Failed to create admin user")
        sys.exit(1)

