from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
import os
import json
import logging
from contextlib import contextmanager
from apps.scheduler.exceptions import FileWriteException, DatabaseException

logger = logging.getLogger(__name__)

def save_json_to_file(json_data, brand_name, template):
    try:
        media_sub = getattr(settings, 'SCHEDULER_JSON_MEDIA_SUBPATH', 'jsons')
        brand_slug = slugify(brand_name)
        folder = os.path.join(settings.MEDIA_ROOT, media_sub, brand_slug)
        os.makedirs(folder, exist_ok=True)
        filename = f"{template}-{timezone.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = os.path.join(folder, filename)
        relative_path = f"{media_sub}/{brand_slug}/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Saved JSON file → {filepath}")
        return filename, relative_path
    except Exception as exc:
        logger.exception("JSON file save failed")
        raise FileWriteException(
            message="JSON file save failed",
            extra=str(exc)
        )

def get_mysql_connection():

    try:
        import MySQLdb
        from MySQLdb.cursors import DictCursor
    except Exception:
        raise RuntimeError("mysqlclient required (pip install mysqlclient)")

    db_conf = settings.JSON_BUILDER_DB

    try:

        conn = MySQLdb.connect(
            host=db_conf["host"],
            port=int(db_conf.get("port", 3306)),
            user=db_conf["user"],
            passwd=db_conf["password"],
            db=db_conf["database"],
            charset="utf8mb4",
            cursorclass=DictCursor
        )

        conn.autocommit(True)

        return conn
    except Exception as exc:
        logger.exception("MySQL connection failed")

        raise DatabaseException(
            message="MySQL connection failed",
            extra=str(exc)
        )


@contextmanager
def mysql_connection():

    conn = None
    try:
        conn = get_mysql_connection()
        yield conn
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
