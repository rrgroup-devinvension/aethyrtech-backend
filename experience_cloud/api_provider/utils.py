import json
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    # Create a 32-byte url-safe base64-encoded key based on Django's SECRET_KEY
    # In production, this should be a dedicated ENCRYPTION_KEY environment variable.
    import hashlib
    _key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    _fernet = Fernet(base64.urlsafe_b64encode(_key))
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("The 'cryptography' package is not installed. ApiProvider credentials will not be securely encrypted at rest. Please run 'pip install cryptography'.")

def encrypt_string(data: str) -> str:
    """Encrypt a plain string."""
    if not data:
        return ""
        
    if HAS_CRYPTOGRAPHY:
        return _fernet.encrypt(data.encode()).decode()
    else:
        return f"b64:{base64.b64encode(data.encode()).decode()}"

def decrypt_string(encrypted_str: str) -> str:
    """Decrypt a string."""
    if not encrypted_str:
        return ""
        
    try:
        if HAS_CRYPTOGRAPHY and not encrypted_str.startswith("b64:"):
            return _fernet.decrypt(encrypted_str.encode()).decode()
        elif encrypted_str.startswith("b64:"):
            return base64.b64decode(encrypted_str[4:]).decode()
        else:
            return encrypted_str
    except Exception as e:
        logger.error(f"Failed to decrypt string: {e}")
        return ""

def encrypt_dict(data: dict) -> str:
    """Encrypt a dictionary into a string."""
    if not data:
        return ""
        
    json_str = json.dumps(data)
    return encrypt_string(json_str)

def decrypt_dict(encrypted_str: str) -> dict:
    """Decrypt a string back into a dictionary."""
    if not encrypted_str:
        return {}
        
    if isinstance(encrypted_str, dict):
        return encrypted_str
        
    try:
        decrypted_str = decrypt_string(encrypted_str)
        return json.loads(decrypted_str) if decrypted_str else {}
    except Exception as e:
        logger.error(f"Failed to decrypt credentials dict: {e}")
        return {}
