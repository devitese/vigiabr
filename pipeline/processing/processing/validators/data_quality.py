"""Data quality validation for transformed records before loading."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Known range constraints (field_name -> (min, max))
_RANGE_RULES: dict[str, tuple[int, int]] = {
    "sci_score": (0, 1000),
    "score_impacto": (0, 250),
}

# Known fixed-length constraints (field_name -> exact_length)
_LENGTH_RULES: dict[str, int] = {
    "uf": 2,
}


@dataclass
class RejectedRecord:
    """A record that failed validation, with the reason for rejection."""

    record: BaseModel
    reason: str


@dataclass
class ValidationStats:
    """Summary statistics from a validation pass."""

    total_input: int = 0
    valid_count: int = 0
    duplicate_count: int = 0
    invalid_count: int = 0


@dataclass
class ValidationResult:
    """Result of validating a batch of records."""

    valid: list[BaseModel] = field(default_factory=list)
    rejected: list[RejectedRecord] = field(default_factory=list)
    stats: ValidationStats = field(default_factory=ValidationStats)


class DataQualityValidator:
    """Validates and deduplicates transformed records before loading.

    This sits between transformers and loaders as a safety net.
    Pydantic already enforces type constraints, but this layer adds:
    - Deduplication (by key field or full model hash)
    - Range validation for domain-specific fields
    - Fixed-length validation for coded fields
    """

    def validate_batch(
        self,
        records: list[BaseModel],
        dedup_key: str | None = None,
    ) -> ValidationResult:
        """Validate a batch of Pydantic models.

        Args:
            records: List of Pydantic model instances to validate.
            dedup_key: Optional field name to use for deduplication.
                       If None, deduplicates by full model JSON hash.

        Returns:
            ValidationResult with valid records, rejected records, and stats.
        """
        stats = ValidationStats(total_input=len(records))
        valid: list[BaseModel] = []
        rejected: list[RejectedRecord] = []
        seen: set[str] = set()

        for record in records:
            # --- Deduplication ---
            dup_fingerprint = self._dedup_fingerprint(record, dedup_key)
            if dup_fingerprint in seen:
                stats.duplicate_count += 1
                rejected.append(RejectedRecord(record=record, reason="duplicate"))
                continue
            seen.add(dup_fingerprint)

            # --- Field-level validation ---
            violations = self._validate_fields(record)
            if violations:
                stats.invalid_count += 1
                reason = "; ".join(violations)
                rejected.append(RejectedRecord(record=record, reason=reason))
                logger.warning("Record rejected: %s", reason)
                continue

            valid.append(record)

        stats.valid_count = len(valid)

        logger.info(
            "Validation complete: %d input, %d valid, %d duplicates, %d invalid",
            stats.total_input,
            stats.valid_count,
            stats.duplicate_count,
            stats.invalid_count,
        )

        return ValidationResult(valid=valid, rejected=rejected, stats=stats)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup_fingerprint(record: BaseModel, dedup_key: str | None) -> str:
        """Compute a deduplication fingerprint for a record.

        If *dedup_key* is provided and the field exists on the record, the
        fingerprint is ``<model_class>:<field_value>``.  Otherwise we fall
        back to a SHA-256 of the full model JSON (deterministic because
        Pydantic serialises in field-declaration order).
        """
        if dedup_key is not None:
            value = getattr(record, dedup_key, None)
            if value is not None:
                return f"{record.__class__.__name__}:{value}"

        # Full-model hash as fallback
        json_bytes = record.model_dump_json().encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()

    @staticmethod
    def _validate_fields(record: BaseModel) -> list[str]:
        """Run domain-specific range and length checks on a record.

        Returns a list of human-readable violation descriptions (empty if OK).
        """
        violations: list[str] = []
        data = record.model_dump()

        for field_name, (lo, hi) in _RANGE_RULES.items():
            if field_name not in data:
                continue
            value = data[field_name]
            if value is None:
                continue
            if not (lo <= value <= hi):
                violations.append(
                    f"{field_name}={value} out of range [{lo}, {hi}]"
                )

        for field_name, expected_len in _LENGTH_RULES.items():
            if field_name not in data:
                continue
            value = data[field_name]
            if value is None:
                continue
            if len(str(value)) != expected_len:
                violations.append(
                    f"{field_name}={value!r} expected length {expected_len}, "
                    f"got {len(str(value))}"
                )

        return violations
