"""Configuration handling for AutoSort."""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path

# Default mapping between categories and file extensions.
DEFAULT_FILE_TYPES: dict[str, list[str]] = {
    "Docs": [
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".txt",
        ".csv",
        ".dotx",
        ".doc",
        ".ppt",
        ".potx",
        ".text",
    ],
    "Media": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".mp4",
        ".mov",
        ".mp3",
        ".wav",
        ".webm",
        ".svg",
        ".webp",
        ".ico",
        ".m4a",
    ],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Programs": [".exe", ".msi", ".dmg", ".pkg", ".sh", ".iso"],
    "Development": [
        ".py",
        ".js",
        ".html",
        ".css",
        ".cpp",
        ".java",
        ".sh",
        ".ipynb",
        ".json",
        ".md",
        ".m",
        ".drawio",
        ".ts",
        ".log",
        ".apk",
        ".db",
        ".sqlite",
        ".sql",
    ],
}

# Defaults if JSON doesn't define SkipExtensions
DEFAULT_SKIP_EXTENSIONS: list[str] = [
    ".tmp",
    ".crdownload",
    ".part",
    ".download",
    ".!ut",
    ".ini",
]


def _normalize_extensions(items: list[str]) -> list[str]:
    """Standardize a list of file extensions.

    Args:
        items: Raw extension strings that may lack a leading dot or use mixed case.

    Returns:
        list[str]: Normalized extensions in lower case starting with a dot.

    Side Effects:
        None.
    """
    normalized: list[str] = []
    for raw in items:
        ext = str(raw).strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        normalized.append(ext)
    return normalized


def load_config(config_file_path: Path) -> tuple[dict[str, list[str]], set[str]]:
    """Load categories and skip extensions from a JSON configuration file.

    Args:
        config_file_path: Location of the configuration file.

    Returns:
        tuple[dict[str, list[str]], set[str]]: Mapping of categories to extensions and
        a set of extensions that should be ignored.

    Side Effects:
        Reads the configuration from disk and logs warnings on failure.
    """
    try:
        with config_file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Config root must be a JSON object.")

        skip_list = data.get("SkipExtensions", DEFAULT_SKIP_EXTENSIONS)
        skip_extensions = set(_normalize_extensions(skip_list))

        reserved = {"SkipExtensions", "_meta"}
        categories: dict[str, list[str]] = {}
        for key, value in data.items():
            if key in reserved:
                continue
            if isinstance(value, list):
                categories[key] = _normalize_extensions([str(x) for x in value])

        if not categories:
            categories = copy.deepcopy(DEFAULT_FILE_TYPES)

        return categories, skip_extensions
    except Exception as error:  # pragma: no cover
        logging.warning(
            "Could not load configuration %s, using defaults: %s",
            config_file_path,
            error,
        )
        return copy.deepcopy(DEFAULT_FILE_TYPES), set(
            _normalize_extensions(DEFAULT_SKIP_EXTENSIONS)
        )


CONFIG_FILE_PATH = Path(__file__).resolve().parents[1] / "config" / "file_types.json"

# Load categories and skip rules
file_types, SKIP_EXTENSIONS = load_config(CONFIG_FILE_PATH)

# Folder paths used by the sorter
FOLDER_PATHS = {
    "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "Media": os.path.join(os.path.expanduser("~"), "Desktop", "Media"),
    "Memes": os.path.join(os.path.expanduser("~"), "Desktop", "Media", "Memes"),
    "Docs": os.path.join(os.path.expanduser("~"), "Desktop", "Docs"),
    "Archives": os.path.join(os.path.expanduser("~"), "Desktop", "Archives"),
    "Programs": os.path.join(os.path.expanduser("~"), "Desktop", "Programs"),
    "Development": os.path.join(os.path.expanduser("~"), "Desktop", "Development"),
}

# Ensure every category from the configuration has a destination folder
for category_name in file_types:
    FOLDER_PATHS.setdefault(
        category_name,
        os.path.join(os.path.expanduser("~"), "Desktop", category_name),
    )

# Normalize folder paths
PATH_TO_FOLDERS = {key: os.path.normpath(value) for key, value in FOLDER_PATHS.items()}
for path in PATH_TO_FOLDERS.values():
    os.makedirs(path, exist_ok=True)

DOWNLOADS_FOLDER_PATH = PATH_TO_FOLDERS["Downloads"]
