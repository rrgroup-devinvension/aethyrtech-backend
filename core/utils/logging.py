import logging

def get_logger(name: str = "app"):
    """
    Consistent logger getter. Configure handlers/formatters in Django LOGGING.
    """
    return logging.getLogger(name)
