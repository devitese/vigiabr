"""Tests for processing validators — data quality and PII safety net."""

from __future__ import annotations

from pydantic import BaseModel

from processing.validators.data_quality import DataQualityValidator
from processing.validators.pii_hasher import PIIHasher


# -------------------------------------------------------------------- #
# Fake Pydantic models for testing (no real DB schemas needed)           #
# -------------------------------------------------------------------- #


class FakeRecord(BaseModel):
    """Minimal test record with common domain fields."""

    uf: str = "SP"
    cpf_hash: str | None = None
    sci_score: int | None = None


class FakeRecordWithKey(BaseModel):
    """Record with a dedup key field."""

    id_tse: str
    nome: str = "Test"
    uf: str = "SP"


class FakeRecordWithCpf(BaseModel):
    """Record that carries a raw cpf field (simulates un-hashed data)."""

    nome: str = "Test"
    cpf: str | None = None
    cpf_hash: str | None = None


# -------------------------------------------------------------------- #
# DataQualityValidator tests                                             #
# -------------------------------------------------------------------- #


class TestDataQualityValidatorDedup:
    """Test deduplication logic."""

    def test_dedup_by_key(self):
        """Two records with the same dedup key: one accepted, one rejected."""
        records = [
            FakeRecordWithKey(id_tse="100", nome="Alice"),
            FakeRecordWithKey(id_tse="200", nome="Bob"),
            FakeRecordWithKey(id_tse="100", nome="Alice Copy"),
        ]

        dq = DataQualityValidator()
        result = dq.validate_batch(records, dedup_key="id_tse")

        assert result.stats.total_input == 3
        assert result.stats.valid_count == 2
        assert result.stats.duplicate_count == 1
        assert len(result.valid) == 2
        assert len(result.rejected) == 1
        assert result.rejected[0].reason == "duplicate"

    def test_dedup_by_hash(self):
        """Two identical records (no dedup_key): one rejected as duplicate via model hash."""
        records = [
            FakeRecord(uf="SP", sci_score=500),
            FakeRecord(uf="SP", sci_score=500),  # exact duplicate
        ]

        dq = DataQualityValidator()
        result = dq.validate_batch(records, dedup_key=None)

        assert result.stats.total_input == 2
        assert result.stats.valid_count == 1
        assert result.stats.duplicate_count == 1


class TestDataQualityValidatorRangeAndLength:
    """Test range and length validation rules."""

    def test_range_validation_uf(self):
        """A record with uf='ABC' (3 chars) is rejected (expected length 2)."""
        records = [
            FakeRecord(uf="ABC", sci_score=500),
        ]

        dq = DataQualityValidator()
        result = dq.validate_batch(records)

        assert result.stats.total_input == 1
        assert result.stats.invalid_count == 1
        assert len(result.rejected) == 1
        assert "uf" in result.rejected[0].reason
        assert "expected length 2" in result.rejected[0].reason

    def test_valid_batch(self):
        """All valid records pass without rejection."""
        records = [
            FakeRecord(uf="SP", sci_score=500),
            FakeRecord(uf="RJ", sci_score=0),
            FakeRecord(uf="MG", sci_score=1000),
        ]

        dq = DataQualityValidator()
        result = dq.validate_batch(records)

        assert result.stats.total_input == 3
        assert result.stats.valid_count == 3
        assert result.stats.duplicate_count == 0
        assert result.stats.invalid_count == 0
        assert len(result.rejected) == 0

    def test_empty_batch(self):
        """An empty list produces an empty result."""
        dq = DataQualityValidator()
        result = dq.validate_batch([])

        assert result.stats.total_input == 0
        assert result.stats.valid_count == 0
        assert len(result.valid) == 0
        assert len(result.rejected) == 0

    def test_sci_score_out_of_range(self):
        """sci_score outside [0, 1000] is rejected."""
        records = [
            FakeRecord(uf="SP", sci_score=1500),
        ]

        dq = DataQualityValidator()
        result = dq.validate_batch(records)

        assert result.stats.invalid_count == 1
        assert "sci_score" in result.rejected[0].reason


# -------------------------------------------------------------------- #
# PIIHasher tests                                                        #
# -------------------------------------------------------------------- #


class TestPIIHasherNoRawPII:
    """Test validate_no_raw_pii — checks for raw CPF/CNPJ in records."""

    def test_no_raw_pii_clean(self):
        """Records with a valid 64-char hex cpf_hash produce no violations."""
        valid_hash = "a" * 64  # 64-char hex string
        records = [
            FakeRecord(cpf_hash=valid_hash),
            FakeRecord(cpf_hash=None),  # None is acceptable
        ]

        hasher = PIIHasher()
        violations = hasher.validate_no_raw_pii(records)

        assert len(violations) == 0

    def test_raw_pii_detected(self):
        """A field named 'cpf' with an 11-digit value is flagged as raw PII."""
        records = [
            FakeRecordWithCpf(cpf="12345678901"),
        ]

        hasher = PIIHasher()
        violations = hasher.validate_no_raw_pii(records)

        assert len(violations) == 1
        assert violations[0].violation_type == "raw_pii_detected"
        assert violations[0].field_name == "cpf"
        assert violations[0].record_index == 0


class TestPIIHasherVerifyHashedFields:
    """Test verify_hashed_fields — checks _hash fields have valid format."""

    def test_invalid_hash_format(self):
        """A record with cpf_hash='not-a-hash' is flagged as invalid."""
        records = [
            FakeRecord(cpf_hash="not-a-hash"),
        ]

        hasher = PIIHasher()
        violations = hasher.verify_hashed_fields(records)

        assert len(violations) == 1
        assert violations[0].violation_type == "invalid_hash_format"
        assert violations[0].field_name == "cpf_hash"

    def test_valid_hash_passes(self):
        """A proper 64-char hex hash produces no violations."""
        records = [
            FakeRecord(cpf_hash="ab" * 32),  # 64-char hex
        ]

        hasher = PIIHasher()
        violations = hasher.verify_hashed_fields(records)

        assert len(violations) == 0

    def test_none_hash_is_ok(self):
        """None cpf_hash is acceptable (optional field)."""
        records = [
            FakeRecord(cpf_hash=None),
        ]

        hasher = PIIHasher()
        violations = hasher.verify_hashed_fields(records)

        assert len(violations) == 0


class TestPIIHasherValidateCombined:
    """Test PIIHasher.validate() — runs both checks together."""

    def test_validate_combined(self):
        """validate() catches both raw PII and invalid hash format in one pass."""
        records = [
            FakeRecordWithCpf(cpf="12345678901", cpf_hash="ab" * 32),  # raw PII in cpf
            FakeRecordWithCpf(cpf=None, cpf_hash="not-a-hash"),  # bad hash format
            FakeRecordWithCpf(cpf=None, cpf_hash="cd" * 32),  # clean
        ]

        hasher = PIIHasher()
        violations = hasher.validate(records)

        # Record 0: raw_pii_detected on "cpf" field
        # Record 1: invalid_hash_format on "cpf_hash" field
        # Record 2: clean
        assert len(violations) == 2

        violation_types = {v.violation_type for v in violations}
        assert "raw_pii_detected" in violation_types
        assert "invalid_hash_format" in violation_types

    def test_validate_all_clean(self):
        """validate() returns empty list when all records are clean."""
        records = [
            FakeRecord(cpf_hash="ab" * 32),
            FakeRecord(cpf_hash="cd" * 32),
        ]

        hasher = PIIHasher()
        violations = hasher.validate(records)

        assert len(violations) == 0
