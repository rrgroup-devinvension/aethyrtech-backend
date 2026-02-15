import logging
import os
import json
from datetime import datetime
from django.conf import settings

LOG_NAME = 'jsonbuilder_api'
LOG_FILE = getattr(settings, 'LOG_DIR', None) or os.path.join(getattr(settings, 'BASE_DIR', ''), 'logs')
os.makedirs(LOG_FILE, exist_ok=True)
LOG_PATH = os.path.join(LOG_FILE, 'jsonbuilder_api.log')

logger = logging.getLogger(LOG_NAME)
if not logger.handlers:
    fh = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)


def log_start(task_id=None, info: dict = None):
    try:
        entry = {
            'event': 'jsonbuilder_start',
            'task_id': task_id,
            'info': info or {}
        }
        logger.info(json.dumps(entry))
    except Exception:
        logging.getLogger(__name__).exception('jsonbuilder_api_logger.log_start failed')


def log_success(task_id=None, info: dict = None):
    try:
        entry = {
            'event': 'jsonbuilder_success',
            'task_id': task_id,
            'info': info or {}
        }
        logger.info(json.dumps(entry))
    except Exception:
        logging.getLogger(__name__).exception('jsonbuilder_api_logger.log_success failed')


def log_error(task_id=None, error: str = None, extra: dict = None):
    try:
        entry = {
            'event': 'jsonbuilder_error',
            'task_id': task_id,
            'error': str(error),
            'extra': extra or {}
        }
        logger.error(json.dumps(entry))
    except Exception:
        logging.getLogger(__name__).exception('jsonbuilder_api_logger.log_error failed')
