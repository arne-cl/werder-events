import sqlite3
import argparse

def migrate(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add new columns
    cursor.execute('ALTER TABLE events ADD COLUMN is_reviewed BOOLEAN DEFAULT 0')
    cursor.execute('ALTER TABLE events ADD COLUMN is_visible BOOLEAN DEFAULT 0')

    conn.commit()
    conn.close()

    print(f"Migration completed: Added 'is_reviewed' and 'is_visible' columns to the events table in {db_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add is_reviewed and is_visible columns to the events table.')
    parser.add_argument('db_path', help='Path to the SQLite database file')
    args = parser.parse_args()

    migrate(args.db_path)
