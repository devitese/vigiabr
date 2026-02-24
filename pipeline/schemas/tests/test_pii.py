"""Tests for PII hashing utilities."""

from __future__ import annotations

import pytest

from pii import hash_cpf, hash_cpf_or_cnpj


class TestHashCpf:
    def test_basic_hash(self):
        result = hash_cpf("12345678901", salt="test-salt")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_formatted_cpf(self):
        """Formatted CPF (XXX.XXX.XXX-XX) should produce same hash as raw digits."""
        raw = hash_cpf("12345678901", salt="test-salt")
        formatted = hash_cpf("123.456.789-01", salt="test-salt")
        assert raw == formatted

    def test_deterministic(self):
        """Same input + salt should always produce same hash."""
        h1 = hash_cpf("12345678901", salt="fixed")
        h2 = hash_cpf("12345678901", salt="fixed")
        assert h1 == h2

    def test_different_salt_different_hash(self):
        """Different salts produce different hashes."""
        h1 = hash_cpf("12345678901", salt="salt-a")
        h2 = hash_cpf("12345678901", salt="salt-b")
        assert h1 != h2

    def test_different_cpf_different_hash(self):
        h1 = hash_cpf("12345678901", salt="same")
        h2 = hash_cpf("98765432100", salt="same")
        assert h1 != h2

    def test_invalid_cpf_too_short(self):
        with pytest.raises(ValueError, match="11 digits"):
            hash_cpf("1234567890", salt="test")

    def test_invalid_cpf_too_long(self):
        with pytest.raises(ValueError, match="11 digits"):
            hash_cpf("123456789012", salt="test")

    def test_irreversible(self):
        """Hash should not contain the original CPF digits."""
        cpf = "12345678901"
        result = hash_cpf(cpf, salt="test")
        assert cpf not in result


class TestHashCpfOrCnpj:
    def test_cpf(self):
        result = hash_cpf_or_cnpj("12345678901", salt="test")
        assert len(result) == 64

    def test_cnpj(self):
        result = hash_cpf_or_cnpj("12345678000195", salt="test")
        assert len(result) == 64

    def test_formatted_cnpj(self):
        raw = hash_cpf_or_cnpj("12345678000195", salt="test")
        formatted = hash_cpf_or_cnpj("12.345.678/0001-95", salt="test")
        assert raw == formatted

    def test_invalid_length(self):
        with pytest.raises(ValueError, match="11.*14"):
            hash_cpf_or_cnpj("123456", salt="test")
