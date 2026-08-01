import base64
import binascii
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    # Create a 32-byte url-safe base64-encoded key based on Django's SECRET_KEY
    # In production, this should be a dedicated ENCRYPTION_KEY environment variable.
    import hashlib

    from cryptography.fernet import Fernet, InvalidToken
    _key = hashlib.sha256(str(settings.SECRET_KEY).encode()).digest()
    _fernet = Fernet(base64.urlsafe_b64encode(_key))
    HAS_CRYPTOGRAPHY = True
except ImportError:
    class InvalidToken(Exception):  # type: ignore[no-redef]
        """Raised when a Fernet token is fundamentally invalid or cannot be decrypted."""
    HAS_CRYPTOGRAPHY = False
    logger.warning(
        "The 'cryptography' package is not installed. ApiProvider credentials "
        "will not be securely encrypted at rest. Please run 'pip install cryptography'."
    )

def encrypt_string(data: str) -> str:
    """Securely encrypt a plain text string using Fernet symmetric encryption."""
    if not data:
        return ""

    if HAS_CRYPTOGRAPHY:
        return _fernet.encrypt(data.encode()).decode()
    else:
        return f"b64:{base64.b64encode(data.encode()).decode()}"

def decrypt_string(encrypted_str: str) -> str:
    """Securely decrypt a previously encrypted string or handle legacy base64-encoded strings."""
    if not encrypted_str:
        return ""

    try:
        if HAS_CRYPTOGRAPHY and not encrypted_str.startswith("b64:"):
            return _fernet.decrypt(encrypted_str.encode()).decode()
        elif encrypted_str.startswith("b64:"):
            return base64.b64decode(encrypted_str[4:]).decode()
        else:
            return encrypted_str
    except (ValueError, TypeError, binascii.Error, InvalidToken, UnicodeDecodeError) as e:
        logger.error(f"Failed to decrypt string: {e}")
        return ""

def encrypt_dict(data: dict) -> str:
    """Serialize a dictionary to JSON and securely encrypt the resulting string."""
    if not data:
        return ""

    json_str = json.dumps(data)
    return encrypt_string(json_str)

def decrypt_dict(encrypted_str: str) -> dict:
    """Securely decrypt an encrypted string back into a Python dictionary."""
    if not encrypted_str:
        return {}

    if isinstance(encrypted_str, dict):
        return encrypted_str

    try:
        decrypted_str = decrypt_string(encrypted_str)
        return json.loads(decrypted_str) if decrypted_str else {}
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to decrypt credentials dict: {e}")
        return {}
