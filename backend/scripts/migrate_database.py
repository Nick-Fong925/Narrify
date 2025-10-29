#!/usr/bin/env python3
"""
Database migration script for Narrify automation fields.
Adds new columns to existing posts table while preserving all data.
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import sys


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    
    print(f"📦 Creating backup: {backup_path.name}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created successfully")
    
    return backup_path


def check_existing_columns(cursor) -> set:
    """Check which columns already exist"""
    cursor.execute("PRAGMA table_info(posts)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    return existing_columns


def migrate_database(db_path: Path):
    """Perform database migration"""
    
    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print(f"ℹ️  Run the app first to create the database")
        return False
    
    # Connect to database
    print(f"\n🔌 Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get record count
        cursor.execute("SELECT COUNT(*) FROM posts")
        record_count = cursor.fetchone()[0]
        print(f"📊 Found {record_count} existing records")
        
        # Check existing columns
        existing_columns = check_existing_columns(cursor)
        print(f"📋 Current columns: {len(existing_columns)}")
        
        # Define new columns to add
        new_columns = {
            'generation_status': "VARCHAR DEFAULT 'pending'",
            'generation_error': "TEXT",
            'generated_at': "TIMESTAMP",
            'posted': "BOOLEAN DEFAULT 0",
            'posted_at': "TIMESTAMP",
            'youtube_video_id': "VARCHAR",
            'upload_error': "TEXT",
            'created_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            'updated_at': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        }
        
        # Add missing columns
        columns_added = 0
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                print(f"➕ Adding column: {column_name}")
                try:
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}")
                    columns_added += 1
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Warning: {e}")
        
        # Create indexes if they don't exist
        indexes = [
            ("ix_posts_posted", "posted"),
            ("ix_posts_score", "score"),
            ("ix_posts_generation_status", "generation_status")
        ]
        
        indexes_created = 0
        for index_name, column_name in indexes:
            try:
                print(f"📑 Creating index: {index_name}")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON posts ({column_name})")
                indexes_created += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️  Warning: {e}")
        
        # Commit changes
        conn.commit()
        
        # Verify migration
        print(f"\n🔍 Verifying migration...")
        new_existing_columns = check_existing_columns(cursor)
        print(f"✅ Final column count: {len(new_existing_columns)}")
        
        # Show summary
        print(f"\n📈 Migration Summary:")
        print(f"   • Records preserved: {record_count}")
        print(f"   • Columns added: {columns_added}")
        print(f"   • Indexes created: {indexes_created}")
        print(f"   • Total columns: {len(new_existing_columns)}")
        
        # Show sample record
        cursor.execute("SELECT id, reddit_id, title, posted, generation_status FROM posts LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"\n📝 Sample record verification:")
            print(f"   • ID: {sample[0]}")
            print(f"   • Reddit ID: {sample[1]}")
            print(f"   • Title: {sample[2][:50]}...")
            print(f"   • Posted: {sample[3]}")
            print(f"   • Status: {sample[4]}")
        
        print(f"\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def main():
    """Main migration function"""
    print("=" * 60)
    print("🗄️  Narrify Database Migration Tool")
    print("=" * 60)
    
    # Get database path
    db_path = Path(__file__).parent.parent / "stories.db"
    
    print(f"\nDatabase: {db_path}")
    
    # Confirm migration
    print(f"\n⚠️  This will modify your database!")
    print(f"   A backup will be created first.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        proceed = True
    else:
        response = input(f"\nProceed with migration? (yes/no): ").strip().lower()
        proceed = response in ['yes', 'y']
    
    if not proceed:
        print("❌ Migration cancelled")
        return
    
    # Create backup
    backup_path = backup_database(db_path)
    
    # Run migration
    success = migrate_database(db_path)
    
    if success:
        print(f"\n" + "=" * 60)
        print(f"✅ MIGRATION COMPLETE")
        print(f"=" * 60)
        print(f"\nBackup saved to: {backup_path.name}")
        print(f"\nNext steps:")
        print(f"   1. Install dependencies: pip install -r requirements.txt")
        print(f"   2. Create .env file: cp .env.example .env")
        print(f"   3. Start app: python -m uvicorn app.main:app --reload")
    else:
        print(f"\n" + "=" * 60)
        print(f"❌ MIGRATION FAILED")
        print(f"=" * 60)
        print(f"\nYour backup is safe at: {backup_path.name}")
        print(f"Database unchanged.")


if __name__ == "__main__":
    main()
