import sqlite3
import logging

def migrate(db_path):
    logger = logging.getLogger(__name__)
    logger.info("Starting migration: Change boolean columns to integer")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            
            # Get all columns for the current table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            for column in columns:
                column_name = column[1]
                column_type = column[2].lower()

                if column_type == 'boolean':
                    logger.info(f"Converting column {table_name}.{column_name} from BOOLEAN to INTEGER")

                    # Create a new temporary column
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name}_temp INTEGER;")

                    # Copy data from the old column to the new one, converting boolean to integer
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET {column_name}_temp = CASE
                            WHEN {column_name} = 1 OR {column_name} = 'true' THEN 1
                            ELSE 0
                        END;
                    """)

                    # Drop the old column
                    cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name};")

                    # Rename the temporary column to the original name
                    cursor.execute(f"ALTER TABLE {table_name} RENAME COLUMN {column_name}_temp TO {column_name};")

        conn.commit()
        logger.info("Migration completed successfully")

    except sqlite3.Error as e:
        logger.error(f"An error occurred: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python 02_change_boolean_to_integer.py <path_to_database>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    migrate(db_path)
