import argparse
import logging
import os
import sys
import time
from datetime import datetime

# Compute project root and add it to sys.path so it can find the 'config' module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Setup Django environment so we can use its database connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402

django.setup()


from django.db import connections, transaction  # noqa: E402


def escape_val(val, engine):
    """Safely escape values for raw SQL."""
    if val is None:
        return "NULL"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, bool):
        if engine == 'postgresql':
            return "true" if val else "false"
        return "1" if val else "0"
    elif isinstance(val, bytes):
        if engine == 'postgresql':
            return f"E'\\\\x{val.hex()}'"
        return "0x" + val.hex()
    else:
        if engine == 'postgresql':
            val_str = str(val).replace("'", "''")
            return f"'{val_str}'"
        else:
            # String escaping for MySQL
            val_str = str(val).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            return f"'{val_str}'"

def generate_sql_dump(db_name='default', target_dialect=None):
    """Generate a full native Python SQL dump without requiring mysqldump/pg_dump."""
    if db_name not in connections:
        logger.error(f"Error: Database '{db_name}' is not configured in settings.DATABASES")
        return

    connection = connections[db_name]
    engine_full = connection.settings_dict.get('ENGINE', '')
    source_engine = 'postgresql' if 'postgresql' in engine_full else 'mysql'
    engine = target_dialect if target_dialect else source_engine

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_folder = datetime.now().strftime("%Y-%m-%d")
    filename = f"{db_name}_{engine}_{timestamp}.sql"

    # Create the backups directory and the database-specific subdirectory
    backup_dir = os.path.join(PROJECT_ROOT, "backups", db_name, date_folder)
    os.makedirs(backup_dir, exist_ok=True)

    output_path = os.path.join(backup_dir, filename)

    logger.info(f"Starting native Python SQL dump for database '{db_name}' ({engine})...")

    start_time = time.time()

    with connection.cursor() as cursor:
        if source_engine == 'postgresql':
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        else:
            cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

    with open(output_path, 'w', encoding='utf-8') as f:
        if engine == 'postgresql':
            f.write("SET session_replication_role = 'replica';\n\n")
        else:
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

        for table in tables:
            logger.info(f"Exporting table: {table}")
            with connection.cursor() as cursor:
                if engine == 'postgresql':
                    # We assume schema exists for PG, just TRUNCATE data safely
                    f.write(f'TRUNCATE TABLE "{table}" CASCADE;\n\n')
                else:
                    # Write table schema for MySQL
                    if source_engine == 'mysql':
                        cursor.execute(f"SHOW CREATE TABLE `{table}`")
                        create_stmt = cursor.fetchone()[1]
                        f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                        f.write(f"{create_stmt};\n\n")

                # Get total rows for pagination
                if source_engine == 'postgresql':
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')  # noqa: S608
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")  # noqa: S608
                total_rows = cursor.fetchone()[0]

                if total_rows > 0:
                    batch_size = 2000
                    rows_processed = 0

                    if source_engine == 'postgresql':
                        # PostgreSQL named cursor for server-side streaming
                        import uuid
                        cursor_name = f'stream_{uuid.uuid4().hex}'
                        # Named cursors in psycopg2 require a transaction block
                        with transaction.atomic(using=db_name):
                            raw_cursor = connection.connection.cursor(name=cursor_name)
                            raw_cursor.itersize = batch_size
                            raw_cursor.execute(f'SELECT * FROM "{table}"')  # noqa: S608

                            while True:
                                rows = raw_cursor.fetchmany(batch_size)
                                if not rows:
                                    break
                                
                                columns = [col[0] for col in raw_cursor.description]

                                if engine == 'postgresql':
                                    col_names = ", ".join([f'"{c}"' for c in columns])
                                    f.write(f'INSERT INTO "{table}" ({col_names}) VALUES \n')  # noqa: S608
                                else:
                                    col_names = ", ".join([f'`{c}`' for c in columns])
                                    f.write(f"INSERT INTO `{table}` ({col_names}) VALUES \n")  # noqa: S608
                                
                                row_strings = [f"({', '.join([escape_val(v, engine) for v in row])})" for row in rows]
                                f.write(",\n".join(row_strings) + ";\n")

                                rows_processed += len(rows)
                                logger.info(f"  - Progress: {min(rows_processed, total_rows)} / {total_rows} rows")
                            raw_cursor.close()
                    else:
                        # MySQL SSCursor (Server Side Cursor) prevents OOM and removes OFFSET penalty
                        try:
                            import MySQLdb.cursors
                            cursor_class = MySQLdb.cursors.SSCursor
                        except ImportError:
                            cursor_class = None

                        raw_cursor = connection.connection.cursor(cursor_class) if cursor_class else connection.cursor()
                        raw_cursor.execute(f"SELECT * FROM `{table}`")  # noqa: S608

                        while True:
                            rows = raw_cursor.fetchmany(batch_size)
                            if not rows:
                                break
                            
                            columns = [col[0] for col in raw_cursor.description]

                            if engine == 'postgresql':
                                col_names = ", ".join([f'"{c}"' for c in columns])
                                f.write(f'INSERT INTO "{table}" ({col_names}) VALUES \n')  # noqa: S608
                            else:
                                col_names = ", ".join([f'`{c}`' for c in columns])
                                f.write(f"INSERT INTO `{table}` ({col_names}) VALUES \n")  # noqa: S608
                                
                            row_strings = [f"({', '.join([escape_val(v, engine) for v in row])})" for row in rows]
                            f.write(",\n".join(row_strings) + ";\n")

                            rows_processed += len(rows)
                            logger.info(f"  - Progress: {min(rows_processed, total_rows)} / {total_rows} rows")
                        raw_cursor.close()

            f.write("\n")

        if engine == 'postgresql':
            f.write("SET session_replication_role = 'origin';\n")
        else:
            f.write("SET FOREIGN_KEY_CHECKS=1;\n")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    mins, secs = divmod(elapsed_time, 60)
    time_str = f"{int(mins)} minutes and {secs:.2f} seconds" if mins > 0 else f"{secs:.2f} seconds"

    logger.info(f"\nSuccess! Full SQL dump saved to: {output_path}")
    logger.info(f"Total time taken: {time_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup a specific Django database or all if omitted.")
    parser.add_argument(
        "--db", default=None,
        help="Name of the database to backup (e.g., default, xbytes_db, karmatech_db). Omit to backup all."
    )
    parser.add_argument(
        "--dialect", default=None,
        help="Target SQL dialect for the dump (mysql or postgresql). Defaults to the active engine."
    )
    args = parser.parse_args()

    try:
        from django.conf import settings
        dbs_to_backup = [args.db] if args.db else list(settings.DATABASES.keys())
        for db in dbs_to_backup:
            generate_sql_dump(db_name=db, target_dialect=args.dialect)
            logger.info("-" * 40)
    except KeyboardInterrupt:
        logger.info("\nDump cancelled by user.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"\nAn error occurred: {e}")
