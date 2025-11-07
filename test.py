from database import get_db
from crud import get_user_by_email
   
db = next(get_db())
   
# Check demo user
demo = get_user_by_email(db, "demo@secretvault.com")
if demo:
    print(f"Demo user found:")
    print(f"  Email: {demo.email}")
    print(f"  Active: {demo.is_active}")
    print(f"  Verified: {demo.is_verified}")
       
    # Fix verification if needed
    if not demo.is_verified or not demo.is_active:
        print("Fixing user verification...")
        demo.is_verified = True
        demo.is_active = True
        db.commit()
        print("User verification fixed!")
    else:
        print("User is already verified and active")
else:
    print("Demo user not found")