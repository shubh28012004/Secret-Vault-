import sqlite3

try:
    conn = sqlite3.connect('secret_vault.db')
    cursor = conn.cursor()
    
    # Check audit_logs table structure
    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = cursor.fetchall()
    print("Audit logs table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Check if user_id column exists
    user_id_exists = any(col[1] == 'user_id' for col in columns)
    print(f"\nuser_id column exists: {user_id_exists}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
