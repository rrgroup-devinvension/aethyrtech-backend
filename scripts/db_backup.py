import logging
import os
import sys
import time

# Compute project root and add it to sys.path so it can find the 'config' module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Setup Django environment so we can use its database connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402

django.setup()

from datetime import datetime  # noqa: E402

from django.db import connections  # noqa: E402
import argparse


def escape_val(val):
    """Safely escape values for raw SQL."""
    if val is None:
        return "NULL"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, bool):
        return "1" if val else "0"
    elif isinstance(val, bytes):
        return "0x" + val.hex()
    else:
        # String escaping for MySQL
        val_str = str(val).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
        return f"'{val_str}'"

def generate_sql_dump(db_name='default'):
    """Generate a full native Python SQL dump without requiring mysqldump."""
    if db_name not in connections:
        logger.error(f"Error: Database '{db_name}' is not configured in settings.DATABASES")
        return
        
    connection = connections[db_name]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_folder = datetime.now().strftime("%Y-%m-%d")
    filename = f"{db_name}_{timestamp}.sql"
    
    # Create the backups directory and the database-specific subdirectory
    backup_dir = os.path.join(PROJECT_ROOT, "backups", db_name, date_folder)
    os.makedirs(backup_dir, exist_ok=True)
    
    output_path = os.path.join(backup_dir, filename)

    logger.info(f"Starting native Python SQL dump for database '{db_name}'...")
    
    start_time = time.time()

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

        for table in tables:
            logger.info(f"Exporting table: {table}")
            with connection.cursor() as cursor:
                # Write table schema
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_stmt = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_stmt};\n\n")

                # Get total rows for pagination
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")  # noqa: S608
                total_rows = cursor.fetchone()[0]

                if total_rows > 0:
                    batch_size = 2000
                    offset = 0

                    while offset < total_rows:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT {batch_size} OFFSET {offset}")  # noqa: S608
                        rows = cursor.fetchall()

                        if not rows:
                            break

                        # Write bulk insert statement to save space and speed up import
                        f.write(f"INSERT INTO `{table}` VALUES \n")  # noqa: S608
                        row_strings = []
                        for row in rows:
                            values = [escape_val(v) for v in row]
                            row_strings.append(f"({', '.join(values)})")

                        f.write(",\n".join(row_strings) + ";\n")
                        offset += batch_size
                        logger.info(f"  - Progress: {min(offset, total_rows)} / {total_rows} rows")

            f.write("\n")

        f.write("SET FOREIGN_KEY_CHECKS=1;\n")
        
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    mins, secs = divmod(elapsed_time, 60)
    time_str = f"{int(mins)} minutes and {secs:.2f} seconds" if mins > 0 else f"{secs:.2f} seconds"

    logger.info(f"\nSuccess! Full SQL dump saved to: {output_path}")
    logger.info(f"Total time taken: {time_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup a specific Django database.")
    parser.add_argument("--db", default="default", help="Name of the database to backup (e.g., default, xbytes_db, karmatech_db)")
    args = parser.parse_args()

    try:
        generate_sql_dump(db_name=args.db)
    except KeyboardInterrupt:
        logger.info("\nDump cancelled by user.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"\nAn error occurred: {e}")
