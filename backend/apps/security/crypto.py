"""Encryption-at-rest for genuinely sensitive fields.

LIFEOS currently has no field that needs this (Cards deliberately stores
only nickname/last-4/expiry — see apps.finance.models.Card and
docs/SECURITY.md "Cards"). This module exists so that IF a future field
truly needs it, the correct pattern is already in place: a key that never
touches source control or the database, held in the macOS Keychain.

The key is never hardcoded and never logged. If the Keychain is unavailable
(non-macOS dev environment), a local key file under a gitignored path is
used instead so development still works — production (the shipped Mac app)
always uses the Keychain.
"""

import subprocess
import sys

from cryptography.fernet import Fernet
from django.conf import settings


def _keychain_get(service: str, account: str) -> str | None:
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _keychain_set(service: str, account: str, value: str) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(
            ["security", "add-generic-password", "-U", "-s", service, "-a", account, "-w", value],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return True
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def _local_fallback_key_path():
    return settings.LIFEOS_SECRETS_DIR / ".field_encryption_key"


def get_or_create_field_encryption_key() -> bytes:
    service = settings.LIFEOS_KEYCHAIN_SERVICE
    account = settings.LIFEOS_KEYCHAIN_ACCOUNT

    existing = _keychain_get(service, account)
    if existing:
        return existing.encode()

    new_key = Fernet.generate_key()
    if _keychain_set(service, account, new_key.decode()):
        return new_key

    # Non-macOS dev fallback — gitignored, file-permission-restricted.
    path = _local_fallback_key_path()
    if path.exists():
        return path.read_bytes()
    path.write_bytes(new_key)
    path.chmod(0o600)
    return new_key


def encrypt_field(plaintext: str) -> str:
    key = get_or_create_field_encryption_key()
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    key = get_or_create_field_encryption_key()
    return Fernet(key).decrypt(ciphertext.encode()).decode()
