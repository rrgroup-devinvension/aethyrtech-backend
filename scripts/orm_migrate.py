import os
import sys
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402
django.setup()

from django.apps import apps  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import connections, transaction  # noqa: E402
import argparse  # noqa: E402

def migrate_via_orm(db_alias):
    """
    Reads from MySQL using a temporary source alias and saves to Postgres using the native alias.
    """
    source_alias = f"source_mysql_for_{db_alias}"
    logger.info(f"Starting ORM-based migration from MySQL ({source_alias}) to Postgres ({db_alias})...")

    # 1. We copy it to the temporary source_alias directly from settings to avoid caching
    settings.DATABASES[source_alias] = settings.DATABASES[db_alias].copy()
    
    # 2. We overwrite the native db_alias to point to PostgreSQL
    postgres_config = settings.DATABASES[db_alias].copy()
    postgres_config.update({
        'ENGINE': 'django.db.backends.postgresql',
        'USER': 'postgres',
        'PORT': '5432',
    })
    settings.DATABASES[db_alias] = postgres_config
    
    # Force Django to drop any cached connection for db_alias
    if hasattr(connections, '_connections'):
        if hasattr(connections._connections, db_alias):
            delattr(connections._connections, db_alias)
            
    with connections[db_alias].cursor() as cursor:
        cursor.execute("SET session_replication_role = 'replica';")
    
    from django.db import router
    
    try:
        models = apps.get_models()
        
        for model in models:
            if model._meta.proxy or not model._meta.managed:
                continue
            
            # CRITICAL: Only migrate models that natively belong in this specific target database!
            # The database router will return False for core apps if target_db is an external DB (xbytes/karmatech).
            if not router.allow_migrate(db_alias, model._meta.app_label, model_name=model._meta.model_name):
                continue
            
            table_name = model._meta.db_table
            logger.info(f"Migrating ORM model: {model.__name__} ({table_name})")
            
            # Truncate on target
            with connections[db_alias].cursor() as cursor:
                cursor.execute(f'TRUNCATE TABLE "{table_name}" CASCADE;')
            
            # Fetch all from source
            qs = model.objects.using(source_alias).all()
            total = qs.count()
            
            if total > 0:
                # We use bulk_create in chunks
                batch_size = 2000
                
                objects_to_create = []
                processed = 0
                for obj in qs.iterator(chunk_size=batch_size):
                    objects_to_create.append(obj)
                    if len(objects_to_create) >= batch_size:
                        model.objects.using(db_alias).bulk_create(objects_to_create, batch_size=batch_size, ignore_conflicts=True)
                        processed += len(objects_to_create)
                        logger.info(f"  - Progress: {processed} / {total}")
                        objects_to_create = []
                        
                if objects_to_create:
                    model.objects.using(db_alias).bulk_create(objects_to_create, batch_size=batch_size, ignore_conflicts=True)
                    processed += len(objects_to_create)
                    logger.info(f"  - Progress: {processed} / {total}")
    finally:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("SET session_replication_role = 'origin';")
            
    logger.info("Migration complete!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='default', help="Source DB in settings")
    args = parser.parse_args()
    migrate_via_orm(args.source)
