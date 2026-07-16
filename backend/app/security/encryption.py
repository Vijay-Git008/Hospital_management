import os
from cryptography.fernet import Fernet

KEY_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "key.enc")

def get_encryption_key() -> bytes:
    """Reads or generates a symmetric key for API key encryption."""
    if os.path.exists(KEY_FILE_PATH):
        with open(KEY_FILE_PATH, "rb") as f:
            return f.read().strip()
    else:
        key = Fernet.generate_key()
        # Save key to local file
        os.makedirs(os.path.dirname(KEY_FILE_PATH), exist_ok=True)
        with open(KEY_FILE_PATH, "wb") as f:
            f.write(key)
        return key

def encrypt_val(val: str) -> str:
    """Encrypts a string value using Fernet symmetric encryption."""
    if not val:
        return ""
    f = Fernet(get_encryption_key())
    return f.encrypt(val.encode("utf-8")).decode("utf-8")

def decrypt_val(encrypted_val: str) -> str:
    """Decrypts a string value using Fernet symmetric encryption."""
    if not encrypted_val:
        return ""
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted_val.encode("utf-8")).decode("utf-8")
    except Exception:
        # Return empty on decryption failure (e.g., key mismatch or tampering)
        return ""
