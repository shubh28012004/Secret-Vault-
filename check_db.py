import sqlite3

try:
    conn = sqlite3.connect('secret_vault.db')
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Check users table
    if ('users',) in tables:
        cursor.execute("SELECT id, email, username, is_verified, is_active FROM users LIMIT 5")
        users = cursor.fetchall()
        print("Users:", users)
        
        # Check table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("Users table columns:", columns)
    
    conn.close()
    print("Database check completed successfully")
    
except Exception as e:
    print(f"Error: {e}")


