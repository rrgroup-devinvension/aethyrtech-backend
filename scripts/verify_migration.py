import os
import argparse
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine, inspect, text

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def verify_migration(mysql_uri, pg_uri):
    logger.info("Connecting to databases for verification...")
    mysql_engine = create_engine(mysql_uri)
    pg_engine = create_engine(pg_uri)
    
    mysql_insp = inspect(mysql_engine)
    pg_insp = inspect(pg_engine)
    
    mysql_tables = set(mysql_insp.get_table_names())
    pg_tables = set(pg_insp.get_table_names())
    
    common_tables = mysql_tables.intersection(pg_tables)
    
    # Ignore django-specific tables we explicitly skipped during migration
    ignore_tables = {'django_migrations', 'django_content_type'}
    common_tables = sorted([t for t in common_tables if t not in ignore_tables])
    
    print("\n" + "="*85)
    print(f"{'TABLE NAME':<40} | {'MYSQL ROWS':<12} | {'POSTGRES ROWS':<13} | {'STATUS'}")
    print("="*85)
    
    all_match = True
    with mysql_engine.connect() as m_conn, pg_engine.connect() as p_conn:
        for table in common_tables:
            # Get MySQL count
            m_count = m_conn.execute(text(f'SELECT COUNT(*) FROM `{table}`')).scalar()
            
            # Get PG count
            p_count = p_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            
            status = "✅ MATCH" if m_count == p_count else "❌ MISMATCH"
            if m_count != p_count:
                all_match = False
                
            print(f"{table:<40} | {m_count:<12} | {p_count:<13} | {status}")

    print("="*85 + "\n")
    if all_match:
        logger.info("SUCCESS: All migrated tables have perfectly matching row counts!")
    else:
        logger.warning("WARNING: Some tables have mismatched row counts.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mysql-db', required=True, help="MySQL Database Name")
    parser.add_argument('--pg-db', required=True, help="PostgreSQL Database Name")
    args = parser.parse_args()
    
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
    
    verify_migration(mysql_uri, pg_uri)
