import logging
import os
import json
from datetime import datetime
from django.conf import settings

LOG_NAME = 'datadump_api'
LOG_FILE = getattr(settings, 'LOG_DIR', None) or os.path.join(getattr(settings, 'BASE_DIR', ''), 'logs')
os.makedirs(LOG_FILE, exist_ok=True)
LOG_PATH = os.path.join(LOG_FILE, 'datadump_api.log')

logger = logging.getLogger(LOG_NAME)
if not logger.handlers:
    fh = logging.FileHandler(LOG_PATH)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)


def log_success(pincode: str, keywords: list, response: dict):
    try:
        entry = {
            'event': 'datadump_success',
            'pincode': pincode,
            'keywords_count': len(keywords) if keywords else 0,
            'response_summary': response if isinstance(response, dict) else str(response)
        }
        logger.info(json.dumps(entry))
    except Exception:
        # Swallow logging errors to avoid affecting caller flows
        logging.getLogger(__name__).exception('datadump_api_logger.log_success failed')


def log_error(pincode: str, keywords: list, error: str, extra: dict = None):
    try:
        entry = {
            'event': 'datadump_error',
            'pincode': pincode,
            'keywords_count': len(keywords) if keywords else 0,
            'error': str(error),
            'extra': extra or {}
        }
        logger.error(json.dumps(entry))
    except Exception:
        # Swallow logging errors to avoid affecting caller flows
        logging.getLogger(__name__).exception('datadump_api_logger.log_error failed')
