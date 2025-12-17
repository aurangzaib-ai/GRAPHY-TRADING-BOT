#!/usr/bin/env python3
"""
Migration script to add the 'programming' column to existing user_access tables.
This script should be run once to update existing databases after the Programming page is added.

Usage: python migrate_programming_permission.py
"""

import sqlite3
import os
import sys

DB_FILE = "users.db"

def migrate_database():
    """Add programming column to user_access table if it doesn't exist"""
    
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' not found. No migration needed.")
        return True
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if programming column already exists
        cursor.execute("PRAGMA table_info(user_access)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'programming' in columns:
            print("✅ Programming column already exists. No migration needed.")
            conn.close()
            return True
        
        # Add the programming column
        print("🔄 Adding 'programming' column to user_access table...")
        cursor.execute("ALTER TABLE user_access ADD COLUMN programming BOOLEAN DEFAULT FALSE")
        
        # Update all existing users to have programming = FALSE by default
        cursor.execute("UPDATE user_access SET programming = FALSE WHERE programming IS NULL")
        
        conn.commit()
        conn.close()
        
        print("✅ Successfully added 'programming' column to user_access table.")
        print("📝 All existing users have been set to programming = FALSE by default.")
        print("💡 Use the Admin panel to grant Programming access to specific users.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting Programming Permission Migration")
    print("=" * 50)
    
    success = migrate_database()
    
    print("=" * 50)
    if success:
        print("✅ Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your Streamlit application")
        print("2. Log in as admin and go to the Admin panel")
        print("3. Grant 'Programming' access to users who need it")
        print("4. The new Programming page should now be accessible")
    else:
        print("❌ Migration failed! Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 