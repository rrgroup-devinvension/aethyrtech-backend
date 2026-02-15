from decimal import Decimal
from datetime import datetime


def normalize_reviews(value):
    """
    Converts:
    "970" -> 970
    "1.4k" -> 1400
    None -> None
    """
    try:
        if not value:
            return None
        value = str(value).lower().strip()
        if "k" in value:
            return int(float(value.replace("k", "")) * 1000)
        return int(value)
    except Exception:
        return None


def normalize_rating(value):
    """
    Converts:
    "4.6" -> 4.6
    4.6 -> 4.6
    None -> None
    """
    try:
        return float(value)
    except Exception:
        return None


def normalize_price(value):
    """
    Converts:
    77 -> 77
    "77" -> 77
    None -> None
    """
    try:
        return Decimal(str(value))
    except Exception:
        return None


def split_images(images_str):
    """
    Converts:
    "url1, url2, url3"
    to:
    ["url1","url2","url3"]
    """
    if not images_str:
        return []
    return [img.strip() for img in images_str.split(",") if img.strip()]

def parse_datetime(value):
    """
    Converts:
    "2026-01-12 16:00:42" -> datetime
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None
