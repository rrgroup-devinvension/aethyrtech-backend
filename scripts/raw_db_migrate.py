import os
import sys
import logging
import argparse
from urllib.parse import quote_plus
from sqlalchemy import create_engine, MetaData, Table, Integer, String, inspect
from sqlalchemy.types import TypeEngine
from sqlalchemy.schema import CreateTable

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

def migrate_raw_database(mysql_uri, pg_uri):
    logger.info(f"Connecting to MySQL: {mysql_uri.split('@')[1] if '@' in mysql_uri else 'local'}")
    mysql_engine = create_engine(mysql_uri)
    
    logger.info(f"Connecting to PostgreSQL: {pg_uri.split('@')[1] if '@' in pg_uri else 'local'}")
    pg_engine = create_engine(pg_uri)

    logger.info("Reflecting MySQL schema...")
    mysql_meta = MetaData()
    mysql_meta.reflect(bind=mysql_engine)
    
    logger.info("Reflecting PostgreSQL schema...")
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    # Check if MySQL tables are missing in PostgreSQL and create them dynamically
    logger.info("Ensuring all MySQL tables exist in PostgreSQL...")
    for table in mysql_meta.sorted_tables:
        if table.name in ['django_migrations', 'django_content_type']:
            continue
            
        if table.name not in pg_meta.tables:
            logger.info(f"Table {table.name} missing in PostgreSQL. Creating it...")
            new_columns = []
            for col in table.columns:
                from sqlalchemy import String, Text, Integer, Boolean, Enum
                
                new_type = col.type
                type_str = str(new_type.__class__).upper()
                
                if isinstance(new_type, Enum) or 'ENUM' in type_str:
                    new_type = String(255)
                elif 'TINYINT' in type_str:
                    new_type = Boolean()
                elif isinstance(new_type, String):
                    new_type = String(new_type.length)
                elif isinstance(new_type, Text):
                    new_type = Text()
                    
                from sqlalchemy import Column, Table
                from typing import Any, cast
                new_col = Column(col.name, cast(Any, new_type), primary_key=col.primary_key, nullable=col.nullable, autoincrement=col.autoincrement)
                new_columns.append(new_col)
                
            from sqlalchemy import Table
            new_table = Table(table.name, pg_meta, *new_columns)
            new_table.create(bind=pg_engine)
            logger.info(f"  - Created table schema for {table.name}")

    # Truncate all tables at once before migrating any data
    # This prevents TRUNCATE CASCADE from accidentally wiping out already-migrated tables
    logger.info("Truncating all target tables before migration...")
    tables_to_truncate = [t.name for t in pg_meta.sorted_tables if t.name not in ['django_migrations', 'django_content_type'] and t.name in mysql_meta.tables]
    if tables_to_truncate:
        with pg_engine.connect() as pg_conn:
            with pg_conn.begin():
                try:
                    from sqlalchemy import text
                    table_names_str = ", ".join([f'"{name}"' for name in tables_to_truncate])
                    pg_conn.execute(text(f"TRUNCATE TABLE {table_names_str} CASCADE;"))
                    logger.info("Successfully truncated all tables.")
                except Exception as e:
                    logger.warning(f"Initial truncate failed: {e}")
    
    # Now copy data
    for table in pg_meta.sorted_tables:
        if table.name in ['django_migrations', 'django_content_type']:
            logger.info(f"Skipping core Django table: {table.name}")
            continue

        if table.name not in mysql_meta.tables:
            logger.warning(f"Table {table.name} not found in MySQL, skipping.")
            continue

        logger.info(f"Migrating data for table: {table.name}")
        
        # We read from mysql_engine using the mysql_meta table
        mysql_table = mysql_meta.tables[table.name]
        
        with mysql_engine.connect() as mysql_conn:
            with pg_engine.connect() as pg_conn:
                # Temporarily disable foreign key constraints for this session
                pg_conn.execute(text("SET session_replication_role = 'replica';"))
                pg_conn.commit()
                
                # Precompute valid columns and boolean columns for ultra-fast inner loop
                valid_cols = {col.name for col in table.columns}
                bool_cols = {col.name for col in table.columns if str(col.type) == 'BOOLEAN'}
                
                result = mysql_conn.execute(mysql_table.select())
                batch_size = 20000
                rows = result.fetchmany(batch_size)
                
                total = 0
                while rows:
                    from typing import Any
                    dicts: list[dict[str, Any]] = []
                    for row in rows:
                        d: dict[str, Any] = {}
                        for k, v in row._mapping.items():
                            k_str = str(k)
                            if k_str in valid_cols:
                                if k_str in bool_cols and isinstance(v, int):
                                    d[k_str] = bool(v)
                                else:
                                    d[k_str] = v
                        dicts.append(d)
                        
                    if dicts:
                        with pg_conn.begin():
                            try:
                                pg_conn.execute(table.insert(), dicts)
                            except Exception as e:
                                logger.error(f"  - Error inserting into {table.name}: {e}")
                                # Try one by one to find the bad row if bulk fails
                                for d in dicts:
                                    try:
                                        pg_conn.execute(table.insert(), [d])
                                    except Exception as inner_e:
                                        pass # Log or ignore
                    total += len(rows)
                    logger.info(f"  - Copied {total} rows...")
                    rows = result.fetchmany(batch_size)
                    
                # Re-enable foreign key constraints
                pg_conn.execute(text("SET session_replication_role = 'origin';"))
                pg_conn.commit()
                        
    logger.info("Full database migration complete!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mysql-db', required=True, help="MySQL Database Name")
    parser.add_argument('--pg-db', required=True, help="PostgreSQL Database Name")
    
    args = parser.parse_args()
    
    # Try to load credentials from Django settings/.env if possible
    import os
    from urllib.parse import quote_plus
    
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, val = line.strip().split('=', 1)
                    env_vars[key] = val
                    
    # Hardcode MySQL credentials (assuming default local setup)
    mysql_user = 'root'
    mysql_pwd = 'root'
    mysql_host = '127.0.0.1'
    mysql_port = '3306'
    
    # Load PostgreSQL credentials from .env
    pg_user = env_vars.get('DB_USER', 'postgres')
    pg_pwd = env_vars.get('DB_PASSWORD', '') 
    pg_host = env_vars.get('DB_HOST', '127.0.0.1')
    pg_port = env_vars.get('DB_PORT', '5432')
    
    mysql_pwd_quoted = quote_plus(mysql_pwd) if mysql_pwd else ""
    pg_pwd_quoted = quote_plus(pg_pwd) if pg_pwd else ""
    
    mysql_uri = f"mysql+pymysql://{mysql_user}:{mysql_pwd_quoted}@{mysql_host}:{mysql_port}/{args.mysql_db}"
    pg_uri = f"postgresql+psycopg2://{pg_user}:{pg_pwd_quoted}@{pg_host}:{pg_port}/{args.pg_db}"
    
    migrate_raw_database(mysql_uri, pg_uri)
