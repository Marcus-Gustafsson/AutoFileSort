"""File sorting routines for AutoSort."""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Optional

import auto_gui

from .config import (
    DOWNLOADS_FOLDER_PATH,
    PATH_TO_FOLDERS,
    SKIP_EXTENSIONS,
    file_types,
)
from .notifications import (
    progress_begin,
    progress_complete,
    progress_update,
    show_notification,
)

meme_enabled: bool = True


def check_name(dest_folder: str, entry_name: str) -> str:
    """Return a non-conflicting destination path for a file."""
    file_name, extension = os.path.splitext(entry_name)
    destination_path_name = os.path.join(dest_folder, entry_name)
    if os.path.exists(destination_path_name):
        counter = 1
        while os.path.exists(
            os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")
        ):
            counter += 1
        return os.path.join(
            dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}"
        )
    return destination_path_name


def should_skip_by_extension(filename: str) -> bool:
    """Return True if the file's extension is configured to be skipped."""
    _, ext = os.path.splitext(filename.lower())
    return ext in SKIP_EXTENSIONS


def is_file_fully_downloaded(
    file_path: str, wait_time: int = 1, check_interval: int = 1
) -> bool:
    """Wait until the file size stops changing."""
    prev_size = -1
    stable_count = 0
    while stable_count < wait_time:
        current_size = os.path.getsize(file_path)
        if current_size == prev_size:
            stable_count += check_interval
        else:
            stable_count = 0
        prev_size = current_size
        time.sleep(check_interval)
    return True


def resolve_destination(path: str, ask_meme: bool = False) -> Optional[str]:
    """Compute the destination folder for a file based on extension."""
    entry_name = os.path.basename(path)
    if should_skip_by_extension(entry_name) or not os.path.isfile(path):
        return None
    ext = os.path.splitext(entry_name)[1].lower()
    for category, extensions in file_types.items():
        if ext in extensions:
            if category == "Media" and meme_enabled and ask_meme:
                return (
                    PATH_TO_FOLDERS["Memes"]
                    if auto_gui.meme_yes_no()
                    else PATH_TO_FOLDERS["Media"]
                )
            return PATH_TO_FOLDERS[category]
    return None


def sort_file(
    path: str, notify: bool = True, planned_dest: Optional[str] = None
) -> Optional[str]:
    """Move a single file to its destination folder."""
    entry_name = os.path.basename(path)
    if should_skip_by_extension(entry_name) or not os.path.isfile(path):
        return None
    dest_folder = (
        planned_dest
        if planned_dest is not None
        else resolve_destination(path, ask_meme=True)
    )
    if not dest_folder:
        return None
    os.makedirs(dest_folder, exist_ok=True)
    destination_path = check_name(dest_folder, entry_name)
    if is_file_fully_downloaded(path):
        shutil.move(path, destination_path)
        logging.info('Moved file: "%s" to folder: %s', entry_name, dest_folder)
        if notify:
            show_notification(
                message=f'- "{entry_name}" \n Moved to \n - {dest_folder}',
                title="File moved:",
                select_file=destination_path,
                duration="long",
            )
        return destination_path
    return None


def sort_files() -> None:
    """Batch-scan the Downloads folder and move eligible files."""
    moved_files: list[str] = []
    try:
        if not os.path.exists(DOWNLOADS_FOLDER_PATH):
            return
        with os.scandir(DOWNLOADS_FOLDER_PATH) as entries:
            raw_files = [e.path for e in entries if e.is_file()]
        candidates: list[tuple[str, str]] = []
        for p in raw_files:
            base = os.path.basename(p)
            if should_skip_by_extension(base):
                continue
            dest = resolve_destination(p, ask_meme=False)
            if dest is not None:
                candidates.append((p, dest))
        total = len(candidates)
        if total == 0:
            return
        progress_begin(initial_status="Scanning & sorting…", total=total)
        progress_update(0, total, status="Starting…")
        done = 0
        for file_path, dest_folder in candidates:
            name = os.path.basename(file_path)
            short_name = (name[:25] + "…") if len(name) > 25 else name
            dest_label = os.path.basename(dest_folder)
            result = sort_file(file_path, notify=False, planned_dest=dest_folder)
            if result:
                moved_files.append(os.path.basename(result))
            done += 1
            progress_update(done, total, status=f"{short_name} → {dest_label}")
        progress_complete("Batch complete")
        if moved_files:
            max_list = 3
            listed = "\n".join(f"- {name[:45]}..." for name in moved_files[:max_list])
            if len(moved_files) > max_list:
                listed += f"\n...and {len(moved_files) - max_list} more"
            show_notification(message=listed, title="Files moved:", duration="long")
    except Exception as error:  # pragma: no cover
        logging.error("ERROR: %s", error, exc_info=True)
