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


"""Tests for sorting logic and helpers."""


def test_should_skip_by_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    """``should_skip_by_extension`` respects the configured skip set.

    Validates that extensions are compared case-insensitively and only those in
    the skip list trigger skipping.
    """
    monkeypatch.setattr(sorter, "SKIP_EXTENSIONS", {".tmp", ".skip"})
    assert sorter.should_skip_by_extension("file.tmp") is True
    assert sorter.should_skip_by_extension("FILE.SKIP") is True
    assert sorter.should_skip_by_extension("file.txt") is False


def test_resolve_destination_known_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Known extensions map to their configured folders.

    The file should be sent to the folder associated with its extension.
    """
    docs = tmp_path / "Docs"
    media = tmp_path / "Media"
    memes = tmp_path / "Memes"
    for p in (docs, media, memes):
        p.mkdir()

    monkeypatch.setattr(sorter, "file_types", {"Docs": [".txt"], "Media": [".jpg"]})
    monkeypatch.setattr(
        sorter,
        "PATH_TO_FOLDERS",
        {"Docs": str(docs), "Media": str(media), "Memes": str(memes)},
    )
    monkeypatch.setattr(sorter, "SKIP_EXTENSIONS", set())

    file_path = tmp_path / "note.txt"
    file_path.write_text("data")
    assert sorter.resolve_destination(str(file_path)) == str(docs)


def test_resolve_destination_media_meme_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Media files route to Memes when the user confirms the prompt."""
    docs = tmp_path / "Docs"
    media = tmp_path / "Media"
    memes = tmp_path / "Memes"
    for p in (docs, media, memes):
        p.mkdir()

    monkeypatch.setattr(sorter, "file_types", {"Media": [".jpg"]})
    monkeypatch.setattr(
        sorter,
        "PATH_TO_FOLDERS",
        {"Docs": str(docs), "Media": str(media), "Memes": str(memes)},
    )
    monkeypatch.setattr(sorter, "SKIP_EXTENSIONS", set())
    monkeypatch.setattr(sorter.auto_gui, "meme_yes_no", lambda: True)

    file_path = tmp_path / "funny.jpg"
    file_path.write_text("img")

    assert sorter.resolve_destination(str(file_path), ask_meme=True) == str(memes)


def test_resolve_destination_unknown_extension_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unmapped extensions return ``None``."""
    docs = tmp_path / "Docs"
    docs.mkdir()

    monkeypatch.setattr(sorter, "file_types", {"Docs": [".txt"]})
    monkeypatch.setattr(sorter, "PATH_TO_FOLDERS", {"Docs": str(docs)})
    monkeypatch.setattr(sorter, "SKIP_EXTENSIONS", set())

    file_path = tmp_path / "file.bin"
    file_path.write_text("data")
    assert sorter.resolve_destination(str(file_path)) is None


def test_sort_file_handles_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duplicate filenames gain a numbered suffix to avoid overwriting."""
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()

    # Existing file in destination
    existing = dest / "file.txt"
    existing.write_text("existing")

    # File to move
    new_file = src / "file.txt"
    new_file.write_text("new")

    monkeypatch.setattr(sorter, "is_file_fully_downloaded", lambda p: True)
    result = sorter.sort_file(str(new_file), notify=False, planned_dest=str(dest))

    assert result is not None
    assert os.path.exists(result)
    assert os.path.basename(result) == "file_(1).txt"
    assert not new_file.exists()


def test_sort_file_skips_configured_extensions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files with skip-list extensions remain untouched."""
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()

    to_skip = src / "ignore.tmp"
    to_skip.write_text("temp")

    monkeypatch.setattr(sorter, "SKIP_EXTENSIONS", {".tmp"})
    monkeypatch.setattr(sorter, "is_file_fully_downloaded", lambda p: True)

    result = sorter.sort_file(str(to_skip), notify=False, planned_dest=str(dest))

    assert result is None
    assert to_skip.exists()
    assert not (dest / "ignore.tmp").exists()
