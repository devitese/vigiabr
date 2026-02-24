"""PII utilities for LGPD compliance — CPF hashing."""

from __future__ import annotations

import hashlib
import os
import re

# Salt is loaded from environment or generated once at startup.
# In production, set VIGIABR_PII_SALT as an environment variable.
_PII_SALT: str = os.environ.get("VIGIABR_PII_SALT", "vigiabr-default-dev-salt-change-in-prod")

# Regex for CPF: 11 digits, optionally formatted as XXX.XXX.XXX-XX
_CPF_RE = re.compile(r"[\d.\-/]+")


def _normalize_cpf(cpf: str) -> str:
    """Strip formatting characters, keep only digits."""
    return re.sub(r"[^\d]", "", cpf)


def hash_cpf(cpf: str, *, salt: str | None = None) -> str:
    """Hash a CPF using SHA-256 with salt. Returns 64-char hex string.

    Args:
        cpf: Brazilian CPF number (11 digits, may include formatting).
        salt: Optional override salt. Uses VIGIABR_PII_SALT env var by default.

    Returns:
        64-character lowercase hex SHA-256 hash.

    Raises:
        ValueError: If CPF doesn't contain exactly 11 digits after normalization.
    """
    digits = _normalize_cpf(cpf)
    if len(digits) != 11:
        raise ValueError(f"CPF must have exactly 11 digits, got {len(digits)}: {cpf!r}")

    effective_salt = salt if salt is not None else _PII_SALT
    payload = f"{effective_salt}:{digits}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_cpf_or_cnpj(value: str, *, salt: str | None = None) -> str:
    """Hash a CPF (11 digits) or CNPJ (14 digits) using SHA-256 with salt.

    Args:
        value: CPF or CNPJ, may include formatting.
        salt: Optional override salt.

    Returns:
        64-character lowercase hex SHA-256 hash.

    Raises:
        ValueError: If value doesn't contain exactly 11 or 14 digits.
    """
    digits = _normalize_cpf(value)
    if len(digits) not in (11, 14):
        raise ValueError(
            f"Expected 11 (CPF) or 14 (CNPJ) digits, got {len(digits)}: {value!r}"
        )

    effective_salt = salt if salt is not None else _PII_SALT
    payload = f"{effective_salt}:{digits}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
