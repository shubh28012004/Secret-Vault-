import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def get_user(cursor: sqlite3.Cursor, email: str):
    cursor.execute(
        "SELECT id, email, is_verified, is_active FROM users WHERE lower(email)=lower(?)",
        (email,),
    )
    return cursor.fetchone()


def update_verification(db_path: Path, email: str, verify: bool = True, activate: bool = True) -> str:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()

        # Ensure user exists
        user = get_user(cur, email)
        if not user:
            return f"User not found for email: {email}"

        # Build update
        set_clauses = ["is_verified=?"]
        params = [1 if verify else 0]
        if activate:
            set_clauses.append("is_active=?")
            params.append(1 if verify else 0)

        # Optionally set verified_at if column exists
        if column_exists(cur, "users", "verified_at"):
            set_clauses.append("verified_at=?")
            params.append(datetime.utcnow().isoformat())

        params.append(email)

        sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE lower(email)=lower(?)"
        cur.execute(sql, params)
        conn.commit()

        if cur.rowcount == 0:
            return "No rows updated (unexpected)."

        # Fetch and show new state
        updated = get_user(cur, email)
        return (
            f"Updated {cur.rowcount} row(s). Now: is_verified={updated[2]}, is_active={updated[3]}"
        )
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Mark a user's email as verified in secret_vault.db"
    )
    parser.add_argument("email", help="Email address to verify")
    parser.add_argument(
        "--db",
        default="secret_vault.db",
        help="Path to SQLite database (default: secret_vault.db)",
    )
    parser.add_argument(
        "--unverify",
        action="store_true",
        help="Set email as unverified instead of verified",
    )
    parser.add_argument(
        "--keep-active",
        action="store_true",
        help="Do not change is_active status (by default activates when verifying)",
    )

    args = parser.parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    message = update_verification(
        db_path=db_path,
        email=args.email,
        verify=not args.unverify,
        activate=not args.keep_active,
    )
    print(message)


if __name__ == "__main__":
    main()


