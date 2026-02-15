#!/usr/bin/env python3
"""
Simple MySQL connectivity check for JSON builder.

Reads environment variables:
  JSON_BUILDER_DB_HOST
  JSON_BUILDER_DB_PORT (optional, default 3306)
  JSON_BUILDER_DB_USER
  JSON_BUILDER_DB_PASSWORD
  JSON_BUILDER_DB_NAME

Exit codes:
  0 - success
  1 - connection failed
  2 - missing configuration
  3 - pymysql not installed

Usage:
  python scripts/check_mysql.py
"""
import os
import sys


def get_conf():
    host = os.getenv('JSON_BUILDER_DB_HOST')
    if not host:
        print('Missing environment variable: JSON_BUILDER_DB_HOST')
        sys.exit(2)
    port = int(os.getenv('JSON_BUILDER_DB_PORT', '3306'))
    user = os.getenv('JSON_BUILDER_DB_USER')
    password = os.getenv('JSON_BUILDER_DB_PASSWORD')
    database = os.getenv('JSON_BUILDER_DB_NAME')

    if not (user and password and database):
        print('Missing one of JSON_BUILDER_DB_USER / JSON_BUILDER_DB_PASSWORD / JSON_BUILDER_DB_NAME')
        sys.exit(2)

    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database,
    }


def main():
    conf = get_conf()
    # Try mysqlclient (MySQLdb) first (C driver commonly used by Django)
    try:
        import MySQLdb
        try:
            conn = MySQLdb.connect(
                host=conf['host'],
                port=conf['port'],
                user=conf['user'],
                passwd=conf['password'],
                db=conf['database'],
                connect_timeout=5,
            )
            cur = conn.cursor()
            cur.execute('SELECT VERSION()')
            row = cur.fetchone()
            ver = row[0] if row else 'unknown'
            print(f'OK: connected using mysqlclient (MySQLdb), version: {ver}')
            cur.close()
            conn.close()
            sys.exit(0)
        except Exception as e:
            print('mysqlclient present but connection failed:', str(e))
            # fallthrough to try pymysql
    except Exception:
        # mysqlclient not installed
        pass

    # Try pymysql next
    try:
        import pymysql
        from pymysql.cursors import DictCursor
        try:
            conn = pymysql.connect(
                host=conf['host'],
                port=conf['port'],
                user=conf['user'],
                password=conf['password'],
                db=conf['database'],
                cursorclass=DictCursor,
                connect_timeout=5,
                read_timeout=5,
            )
            with conn.cursor() as cur:
                cur.execute('SELECT VERSION() as v')
                row = cur.fetchone()
                ver = row.get('v') if row else 'unknown'
                print(f'OK: connected using pymysql, version: {ver}')
            conn.close()
            sys.exit(0)
        except Exception as e:
            print('pymysql present but connection failed:', str(e))
            # fallthrough to try Django connection
    except Exception:
        # pymysql not installed
        pass

    # Final fallback: try using Django's configured DB (uses whichever driver Django uses)
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()
        from django.db import connection
        try:
            connection.ensure_connection()
            print('OK: connected via Django DB connection')
            sys.exit(0)
        except Exception as e:
            print('Django DB connection failed:', str(e))
            sys.exit(1)
    except Exception:
        print('No suitable MySQL driver found (mysqlclient or pymysql) and Django not available.')
        print('Install mysqlclient or pymysql, or run the check within the Django environment.')
        sys.exit(3)


if __name__ == '__main__':
    main()
