"""Tests for configuration utilities."""

import json
from pathlib import Path
import os
import pytest
from autofile import sorter

from autofile.config import (
    DEFAULT_FILE_TYPES,
    DEFAULT_SKIP_EXTENSIONS,
    _normalize_extensions,
    load_config,
)


def test_normalize_extensions_cleans_input() -> None:
    """``_normalize_extensions`` strips whitespace, adds dots, and lowercases.

    Ensures config-driven extension lists are standardized to reliably match
    files regardless of user input format.
    """
    raw = ["TXT", "  .Pdf", "csv", "", " "]
    assert _normalize_extensions(raw) == [".txt", ".pdf", ".csv"]


def test_load_config_valid_file(tmp_path: Path) -> None:
    """Valid JSON config should produce normalized categories and skip list.

    Demonstrates that ``load_config`` converts extensions to lowercase with a
    leading dot and properly separates categories from the skip list.
    """
    cfg = {
        "Docs": ["TXT"],
        "SkipExtensions": [".TMP", "log"],
    }
    config_path = tmp_path / "file_types.json"
    config_path.write_text(json.dumps(cfg))

    categories, skip_exts = load_config(config_path)

    assert categories == {"Docs": [".txt"]}
    assert skip_exts == {".tmp", ".log"}


def test_load_config_malformed_json_falls_back(tmp_path: Path) -> None:
    """Malformed JSON causes a fallback to defaults.

    The loader should guard against corrupt user config by returning the
    built-in defaults when parsing fails.
    """
    config_path = tmp_path / "bad.json"
    config_path.write_text("{ not: valid json }")

    categories, skip_exts = load_config(config_path)

    assert categories == DEFAULT_FILE_TYPES
    assert skip_exts == set(_normalize_extensions(DEFAULT_SKIP_EXTENSIONS))


def test_load_config_no_categories_uses_defaults(tmp_path: Path) -> None:
    """Config without categories falls back to ``DEFAULT_FILE_TYPES``.

    Even if the user supplies a skip list, missing category data should not
    break sorting, so defaults are applied.
    """
    cfg = {"SkipExtensions": ["bak"]}
    config_path = tmp_path / "only_skip.json"
    config_path.write_text(json.dumps(cfg))

    categories, skip_exts = load_config(config_path)

    assert categories == DEFAULT_FILE_TYPES
    assert skip_exts == {".bak"}