import os
import sys

# Setup Django environment so we can use its database connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection
from datetime import datetime

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

def generate_sql_dump():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"custom_backup_{timestamp}.sql"
    output_path = os.path.join(os.getcwd(), filename)
    
    print("Starting native Python SQL dump (No mysqldump required)...")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
        
        for table in tables:
            print(f"Exporting table: {table}")
            with connection.cursor() as cursor:
                # Write table schema
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_stmt = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_stmt};\n\n")

                # Get total rows for pagination
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                total_rows = cursor.fetchone()[0]
                
                if total_rows > 0:
                    batch_size = 2000
                    offset = 0
                    
                    while offset < total_rows:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT {batch_size} OFFSET {offset}")
                        rows = cursor.fetchall()
                        
                        if not rows:
                            break
                        
                        # Write bulk insert statement to save space and speed up import
                        f.write(f"INSERT INTO `{table}` VALUES \n")
                        row_strings = []
                        for row in rows:
                            values = [escape_val(v) for v in row]
                            row_strings.append(f"({', '.join(values)})")
                        
                        f.write(",\n".join(row_strings) + ";\n")
                        offset += batch_size
                        print(f"  - Progress: {min(offset, total_rows)} / {total_rows} rows")
                        
            f.write("\n")
            
        f.write("SET FOREIGN_KEY_CHECKS=1;\n")
        
    print(f"\nSuccess! Full SQL dump saved to: {output_path}")

if __name__ == "__main__":
    try:
        generate_sql_dump()
    except KeyboardInterrupt:
        print("\nDump cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
