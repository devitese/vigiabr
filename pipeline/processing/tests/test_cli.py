"""Tests for the processing CLI argument parser."""

from __future__ import annotations

import pytest

from processing.__main__ import _build_parser


class TestCLIParser:
    """Test CLI argument parsing without invoking any real pipeline logic."""

    def test_parser_valid_source(self):
        """Parser accepts 'camara' as a valid source."""
        parser = _build_parser()
        args = parser.parse_args(["camara"])

        assert args.source == "camara"

    def test_parser_all_valid_sources(self):
        """Parser accepts all registered sources."""
        parser = _build_parser()
        for source in ("camara", "senado", "tse", "transparencia", "cnpj", "querido_diario", "cnj"):
            args = parser.parse_args([source])
            assert args.source == source

    def test_parser_invalid_source(self):
        """Parser rejects an unrecognized source with SystemExit."""
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_source"])

    def test_dry_run_flag(self):
        """--dry-run flag sets dry_run=True."""
        parser = _build_parser()
        args = parser.parse_args(["camara", "--dry-run"])

        assert args.dry_run is True

    def test_dry_run_default_false(self):
        """dry_run defaults to False when not specified."""
        parser = _build_parser()
        args = parser.parse_args(["camara"])

        assert args.dry_run is False

    def test_verbose_flag(self):
        """-v flag sets verbose=True."""
        parser = _build_parser()
        args = parser.parse_args(["camara", "-v"])

        assert args.verbose is True

    def test_data_dir_default(self):
        """--data-dir defaults to pipeline/data."""
        parser = _build_parser()
        args = parser.parse_args(["camara"])

        assert str(args.data_dir) == "pipeline/data"

    def test_data_dir_custom(self):
        """--data-dir accepts a custom path."""
        parser = _build_parser()
        args = parser.parse_args(["camara", "--data-dir", "/tmp/custom"])

        assert str(args.data_dir) == "/tmp/custom"
