"""API key encryption and decryption using Fernet symmetric encryption.

Fernet guarantees that data encrypted with it cannot be read or tampered
with without the key. Keys are encrypted at rest in the database and
decrypted only when needed to make LLM API calls.
"""

from cryptography.fernet import Fernet, InvalidToken

from api.exceptions import EncryptionError
from config import settings


def _get_fernet() -> Fernet:
    """Create a Fernet instance from the configured encryption key.

    Raises:
        EncryptionError: If the encryption key is not configured or invalid.
    """
    key = settings.encryption_key
    if not key or key == "change-me-in-production":
        raise EncryptionError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise EncryptionError(f"Invalid ENCRYPTION_KEY: {exc}") from exc


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key for secure storage.

    Args:
        plain_key: The plaintext API key.

    Returns:
        Base64-encoded encrypted string, safe for database storage.

    Raises:
        EncryptionError: If encryption fails.
    """
    try:
        f = _get_fernet()
        return f.encrypt(plain_key.encode()).decode()
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(f"Failed to encrypt API key: {exc}") from exc


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key for use in LLM API calls.

    Args:
        encrypted_key: Base64-encoded encrypted string from the database.

    Returns:
        The plaintext API key.

    Raises:
        EncryptionError: If decryption fails (wrong key, corrupted data, etc.).
    """
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_key.encode()).decode()
    except EncryptionError:
        raise
    except InvalidToken:
        raise EncryptionError(
            "Failed to decrypt API key. The encryption key may have changed."
        )
    except Exception as exc:
        raise EncryptionError(f"Failed to decrypt API key: {exc}") from exc
