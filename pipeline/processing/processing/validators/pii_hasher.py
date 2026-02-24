"""PII safety-net validator — catches unhashed personal identifiers before persistence.

Transformers are responsible for hashing PII during transformation.  This
validator is a **defence-in-depth** layer that scans records right before
loading and flags anything that looks like raw CPF / CNPJ data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Regex: value that is *exactly* 11 or 14 digits (possibly with formatting).
# We strip non-digit chars first, so just check digit-only length.
_RAW_PII_RE = re.compile(r"^\d{11}$|^\d{14}$")

# 64-character lowercase hex string (SHA-256 output)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class PIIViolation:
    """A single PII violation found in a record."""

    record_index: int
    field_name: str
    violation_type: str  # "raw_pii_detected" or "invalid_hash_format"
    detail: str


class PIIHasher:
    """Ensures all PII fields are hashed before persistence.

    This is a SAFETY NET -- transformers should hash PII during transformation,
    but this validator catches any that slip through.
    """

    # Fields that MUST contain hashed values (64-char hex), never raw PII.
    PII_FIELDS: frozenset[str] = frozenset({"cpf_hash", "doador_cpf_cnpj_hash"})

    # Field name substrings that might carry raw PII in source data.
    RAW_PII_PATTERNS: frozenset[str] = frozenset({"cpf", "cnpj", "cpf_cnpj"})

    def validate_no_raw_pii(self, records: list[BaseModel]) -> list[PIIViolation]:
        """Scan records for any field whose value looks like raw PII.

        A value is suspicious if, after stripping formatting characters,
        it is exactly 11 digits (CPF) or 14 digits (CNPJ).

        Args:
            records: List of Pydantic model instances to scan.

        Returns:
            List of PIIViolation objects. Empty means all clear.
        """
        violations: list[PIIViolation] = []

        for idx, record in enumerate(records):
            data = record.model_dump()
            for field_name, value in data.items():
                if value is None or not isinstance(value, str):
                    continue

                # Only inspect fields whose names suggest PII content
                if not self._field_looks_like_pii(field_name):
                    continue

                digits = re.sub(r"[^\d]", "", value)
                if _RAW_PII_RE.match(digits):
                    violation = PIIViolation(
                        record_index=idx,
                        field_name=field_name,
                        violation_type="raw_pii_detected",
                        detail=(
                            f"Field '{field_name}' contains a value that looks "
                            f"like raw PII ({len(digits)} digits). "
                            f"PII must be hashed before persistence."
                        ),
                    )
                    violations.append(violation)
                    logger.error(
                        "RAW PII DETECTED in record %d, field '%s' "
                        "(%d-digit value). This is a LGPD violation risk.",
                        idx,
                        field_name,
                        len(digits),
                    )

        return violations

    def verify_hashed_fields(self, records: list[BaseModel]) -> list[PIIViolation]:
        """Verify that fields ending in ``_hash`` contain valid 64-char hex strings.

        Args:
            records: List of Pydantic model instances to verify.

        Returns:
            List of PIIViolation objects for fields with invalid hash formats.
        """
        violations: list[PIIViolation] = []

        for idx, record in enumerate(records):
            data = record.model_dump()
            for field_name, value in data.items():
                if not field_name.endswith("_hash"):
                    continue
                if value is None:
                    # Optional hash fields (e.g. cpf_hash on Mandatario) may be None
                    continue
                if not isinstance(value, str) or not _HASH_RE.match(value):
                    violation = PIIViolation(
                        record_index=idx,
                        field_name=field_name,
                        violation_type="invalid_hash_format",
                        detail=(
                            f"Field '{field_name}' should contain a 64-char hex "
                            f"SHA-256 hash, but got: {str(value)[:20]!r}..."
                        ),
                    )
                    violations.append(violation)
                    logger.error(
                        "Invalid hash format in record %d, field '%s'. "
                        "Expected 64-char hex SHA-256.",
                        idx,
                        field_name,
                    )

        return violations

    def validate(self, records: list[BaseModel]) -> list[PIIViolation]:
        """Run all PII checks and return combined violations.

        This is a convenience method that runs both ``validate_no_raw_pii``
        and ``verify_hashed_fields``.

        Args:
            records: List of Pydantic model instances to validate.

        Returns:
            Combined list of all PIIViolation objects found.
        """
        violations: list[PIIViolation] = []
        violations.extend(self.validate_no_raw_pii(records))
        violations.extend(self.verify_hashed_fields(records))

        if violations:
            logger.warning(
                "PII validation found %d violation(s) across %d records",
                len(violations),
                len(records),
            )
        else:
            logger.debug(
                "PII validation passed for %d records with no violations",
                len(records),
            )

        return violations

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _field_looks_like_pii(field_name: str) -> bool:
        """Check if a field name suggests it might contain PII.

        Returns True if the field name contains 'cpf' or 'cnpj' (case
        insensitive) AND does NOT end with '_hash' (which indicates the
        value is already hashed).
        """
        lower = field_name.lower()
        if lower.endswith("_hash"):
            return False
        return "cpf" in lower or "cnpj" in lower
