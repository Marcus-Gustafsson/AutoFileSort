"""
AutoFileSort Script for Sorting Files from one folder to other folders (one to many).

This script monitors the selected foler ("Downloads"-folder is the default selection)
and automatically moves files to their corresponding destination folders based on file extensions.
Also uses a system tray icon for user control.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import logging
import sys
import subprocess
import time
import threading
from pathlib import Path
from typing import Any, Optional

import pystray
from pystray import MenuItem as item

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

import auto_gui


# Global state (give them explicit types):
observer: Optional[Any] = None
meme_enabled: bool = True
pytray_icon: Optional[Any] = None  # <- quick/pragmatic: treat pystray.Icon as Any

# Prefer native Windows 11 toasts if available
try:  # pragma: no cover
    from win11toast import (
        notify as win_notify,
        toast as win_toast,
        update_progress as win_update_progress,
    )
except Exception:
    win_notify = None
    win_toast = None
    win_update_progress = None

APP_ID = "AutoFileSort"


def set_windows_app_id(app_id: str = "AutoFileSort") -> None:
    """
    On Windows, set the process App User Model ID so toast headers
    show a friendly app name instead of 'Python'.

    Safe no-op on non-Windows platforms.
    """
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes  # local import to avoid platform issues

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        logging.warning("Failed to set AppUserModelID: %s", e)


def start_action(pytray_icon: Any) -> None:
    """
    Callback for the "Start" menu item.
    Sets the global flag to True and (re)starts the observer.

    Args:
        pytray_icon (pystray.Icon): The system tray icon instance to update.

    Returns:
        None
    """
    start_watching()
    update_menu(pytray_icon)


def stop_action(pytray_icon: Any) -> None:
    """
    Callback for the "Stop" menu item.
    Sets the global flag to False and stops the observer.

    Args:
        pytray_icon (pystray.Icon): The system tray icon instance to update.

    Returns:
        None
    """
    stop_watching()
    update_menu(pytray_icon)


def quit_action(pytray_icon: Any) -> None:
    """
    Callback for the "Quit" menu item. Stops the tray icon event loop.

    Args:
        pytray_icon (pystray.Icon): The system tray icon instance.

    Returns:
        None
    """
    print("DEBUG: Quit action triggered. Exiting application...")
    pytray_icon.stop()


def update_menu(pytray_icon: Any) -> None:
    """
    Rebuild and apply the tray icon menu based on current state (running/stopped).

    Args:
        pytray_icon (pystray.Icon): The system tray icon whose menu should be updated.

    Returns:
        None
    """
    print("DEBUG: Updating menu. Current observer state =", observer)
    menu = pystray.Menu(
        item(
            "Start" + (" (active)" if observer is not None else ""),
            start_action,
            enabled=observer is None,
        ),
        item(
            "Stop" + (" (active)" if observer is None else ""),
            stop_action,
            enabled=observer is not None,
        ),
        item("Quit", quit_action),
    )
    pytray_icon.menu = menu
    print("DEBUG: Menu updated.")


# Default mapping between categories and file extensions.
# The configuration file can override these values.
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

# --- Defaults if JSON doesn't define SkipExtensions ---
DEFAULT_SKIP_EXTENSIONS: list[str] = [
    ".tmp",
    ".crdownload",
    ".part",
    ".download",
    ".!ut",
    ".ini",
]


def _normalize_extensions(items: list[str]) -> list[str]:
    """
    Normalize a list of extensions:
    - lowercases
    - ensures a leading dot is present ('.pdf', '.TXT' -> '.pdf', '.txt')
    - filters out empty/invalid entries
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
    """
    Load sorting categories and skip-extensions from JSON config.

    Expected JSON structure:
    {
      "SkipExtensions": [".tmp", ".crdownload", ".ini"],
      "Docs": [".pdf", ".docx", ...],
      "Media": [".jpg", ".png", ...],
      ...
    }

    Returns:
        (file_types, skip_extensions)
        file_types: mapping of category -> list of extensions (normalized)
        skip_extensions: set of extensions that should never be processed
    """
    try:
        with config_file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Config root must be a JSON object.")

        # Extract optional skip list from JSON (fallback to defaults)
        skip_extensions_list = data.get("SkipExtensions", DEFAULT_SKIP_EXTENSIONS)
        skip_extensions = set(_normalize_extensions(skip_extensions_list))

        # Everything else is treated as a category list (ignore the skip key and any metadata keys you might add later)
        reserved = {"SkipExtensions", "_meta"}
        categories: dict[str, list[str]] = {}
        for key, value in data.items():
            if key in reserved:
                continue
            if isinstance(value, list):
                categories[key] = _normalize_extensions([str(x) for x in value])

        # Fallback to DEFAULT_FILE_TYPES if no categories were defined
        if not categories:
            categories = copy.deepcopy(DEFAULT_FILE_TYPES)

        return categories, skip_extensions

    except Exception as error:  # pragma: no cover - rely on logging for visibility
        logging.warning(
            "Could not load configuration %s, using defaults: %s",
            config_file_path,
            error,
        )
        return copy.deepcopy(DEFAULT_FILE_TYPES), set(
            _normalize_extensions(DEFAULT_SKIP_EXTENSIONS)
        )


CONFIG_FILE_PATH = Path(__file__).resolve().parent / "config" / "file_types.json"

# Load categories and skip rules.
file_types, SKIP_EXTENSIONS = load_config(CONFIG_FILE_PATH)


# os.path.expanduser("~") so that the paths work across different operating systems.
# On Windows, for example, os.path.expanduser("~") might be "C:\Users\name", while on macOS/Linux it would be "/Users/name" or "/home/name".
folder_paths = {
    "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "Media": os.path.join(os.path.expanduser("~"), "Desktop", "Media"),
    "Memes": os.path.join(os.path.expanduser("~"), "Desktop", "Media", "Memes"),
    "Docs": os.path.join(os.path.expanduser("~"), "Desktop", "Docs"),
    "Archives": os.path.join(os.path.expanduser("~"), "Desktop", "Archives"),
    "Programs": os.path.join(os.path.expanduser("~"), "Desktop", "Programs"),
    "Development": os.path.join(os.path.expanduser("~"), "Desktop", "Development"),
}

# Ensure every category from the configuration has a destination folder.
for category_name in file_types:
    folder_paths.setdefault(
        category_name, os.path.join(os.path.expanduser("~"), "Desktop", category_name)
    )

# Normalize the folder paths to ensure they are formatted correctly for the current operating system.
path_to_folders = {key: os.path.normpath(value) for key, value in folder_paths.items()}

# Create the folders if they do not already exist.
for path in path_to_folders.values():
    os.makedirs(path, exist_ok=True)

# Initialize the Downloads folder path, where new files are typically saved.
downloads_folder_path = path_to_folders["Downloads"]

# Logging to record file movements.
logging.basicConfig(
    filename=path_to_folders["Development"] + "\\AutoFileSort.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


def check_name(dest_folder: str, entry_name: str) -> str:
    """
    Checks if a file with the same name already exists in the destination folder.
    If it exists, append a counter to the file name to avoid overwriting.

    Args:
        dest_folder (str): The path to the destination folder.
        entry_name (str): The name of the file (including extension).

    Returns:
        str: A unique file path in the destination folder.
    """
    # Split the file name into the base name and extension.
    file_name, extension = os.path.splitext(entry_name)
    destination_path_name = os.path.join(dest_folder, entry_name)

    # If a file with the same name exists, find a new name with a counter.
    if os.path.exists(destination_path_name):
        counter = 1
        while os.path.exists(
            os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")
        ):
            counter += 1
        return os.path.join(
            dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}"
        )

    # If the file does not exist, return the original path/name.
    return destination_path_name


def should_skip_by_extension(filename: str) -> bool:
    """
    Decide if a file should be skipped purely by its extension.

    Args:
        filename: The file's base name (e.g., 'desktop.ini' or 'movie.mp4').

    Returns:
        True if the file's extension is in the configured SKIP_EXTENSIONS; otherwise False.
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in SKIP_EXTENSIONS


def is_file_fully_downloaded(
    file_path: str, wait_time: int = 1, check_interval: int = 1
) -> bool:
    """
    Waits until the file size stops changing, indicating that the file is fully downloaded.
    This prevents moving a file that is still being written/modified.

    Args:
        file_path (str): The full path of the file to check.
        wait_time (int, optional): The total time (in seconds) the file size should remain unchanged.
                                   Defaults to 2 seconds.
        check_interval (int, optional): The interval (in seconds) between size checks.
                                        Defaults to 1 second.

    Returns:
        bool: True if the file is stable (i.e., fully downloaded), False otherwise.
    """
    prev_size = -1
    stable_count = 0

    # Loop until the file size remains the same for 'wait_time' seconds.
    while stable_count < wait_time:
        current_size = os.path.getsize(file_path)
        if current_size == prev_size:
            print(f"DBG: current size = {current_size} and prev size = {prev_size}")
            stable_count += (
                check_interval  # Increase the stable count if size doesn't change.
            )
        else:
            stable_count = 0  # Reset if the file size changes.
        prev_size = current_size
        time.sleep(check_interval)

    return True  # file is considered stable.


def open_file_location(file_path: str) -> None:
    """
    Open the system file explorer showing (and selecting) the given file.

    On Windows, this uses `explorer /select,"<absolute_path>"` to highlight the file.
    On macOS it reveals the file in Finder, and on Linux it opens the parent folder.

    Args:
        file_path (str): Full path to the file that should be revealed/selected.

    Returns:
        None
    """
    normalized_path = os.path.normpath(os.path.abspath(file_path))
    print(f"DBG: open_file_location() -> {normalized_path}")

    try:
        if sys.platform.startswith("win"):
            # Quote the path; keep the comma after /select,
            cmd = f'explorer /select,"{normalized_path}"'
            print(f"DBG: Running: {cmd}")
            subprocess.run(cmd, shell=True, check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", normalized_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(normalized_path)], check=False)
    except Exception as err:
        logging.error(
            f"Failed to open file location for {file_path}: {err}", exc_info=True
        )


def show_notification(
    message: str,
    title: str = "",
    select_file: Optional[str] = None,
    open_folder: Optional[str] = None,
    **toast_kwargs: Any,
) -> None:
    """
    Show a Windows toast. Click behavior:
      - If `select_file` is provided: clicking selects that file in Explorer (uses `toast` with callback).
      - Else if `open_folder` is provided: clicking opens that folder via file URI (uses `notify`).
      - Else: shows a toast with no click action.

    Falls back to logging/print if win11toast is unavailable or not on Windows.

    Args:
        message (str): Text content of the notification.
        title (str, optional): Title for the toast window. Defaults to "".
        select_file (str | None, optional): Path to a file to highlight in Explorer on click.
        open_folder (str | None, optional): Path to a folder to open on click (no highlight).
        **toast_kwargs: Extra win11toast options (e.g., icon, image, duration, audio).

    Returns:
        None
    """
    try:
        if not sys.platform.startswith("win") or (
            win_notify is None and win_toast is None
        ):
            logging.info(f"[Notification] {title}: {message}")
            print(f"[Notification] {title}: {message}")
            return

        # Case 1: highlight a specific file → need Python callback → use toast (blocking) in a thread
        if select_file and win_toast is not None:
            abs_file = os.path.abspath(select_file)

            def _run_toast() -> None:
                try:
                    win_toast(
                        title or "Notification",
                        message,
                        on_click=lambda args=None: open_file_location(abs_file),
                        **toast_kwargs,
                    )
                except Exception as err:
                    logging.error(f"Toast (select_file) failed: {err}", exc_info=True)

            threading.Thread(target=_run_toast, daemon=True).start()
            return

        # Case 2: open a folder (no highlight) → URL works with notify (non-blocking)
        if open_folder and win_notify is not None:
            folder_uri = Path(open_folder).resolve().as_uri()
            win_notify(
                title or "Notification",
                message,
                on_click=folder_uri,
                **toast_kwargs,
                icon=str(Path(__file__).with_name("exe_icon.ico")),
            )
            return

        # Default: plain notify without click
        if win_notify is not None:
            win_notify(title or "Notification", message, **toast_kwargs)
        else:
            # If only toast exists, show it in background thread without on_click
            threading.Thread(
                target=lambda: win_toast(
                    title or "Notification", message, **toast_kwargs
                ),
                daemon=True,
            ).start()

    except Exception as err:
        logging.error(f"Toast failed: {err}", exc_info=True)
        print(f"[Notification error] {title}: {message}")


def progress_begin(initial_status: str, total: int) -> None:
    """
    Create a determinate progress toast at 0/total, bound to our APP_ID.
    Keep initial value as STRING '0' (safer across Windows builds).
    """
    if not sys.platform.startswith("win") or win_notify is None:
        logging.info(f"[Progress] {APP_ID}: {initial_status} 0/{total}")
        print(f"[Progress] {APP_ID}: {initial_status} 0/{total}")
        return

    try:
        # Classic (title, message) positional args + progress + *same* app_id.
        win_notify(
            APP_ID,  # title/header line
            "Batch sorting ...",  # message/subheader
            app_id=APP_ID,
            progress={
                "title": "Progress",
                "status": initial_status,
                "value": "0",  # NOTE: string "0"
                "valueStringOverride": f"0/{total}",
            },
            icon=str(Path(__file__).with_name("exe_icon.ico")),
        )

        # Give Windows a beat to register the progress toast before first update.
        time.sleep(0.2)

    except Exception as err:
        logging.error(f"progress_begin failed: {err}", exc_info=True)


def progress_update(done: int, total: int, status: str | None = None) -> None:
    """
    Update the active progress toast. Status can be 'filename → Folder'.
    Pass the same APP_ID so the library updates the correct toast.
    """
    ratio = 0.0 if total <= 0 else max(0.0, min(1.0, done / total))

    if not sys.platform.startswith("win") or win_update_progress is None:
        msg = f"[Progress] {status or 'Working...'} {done}/{total} ({int(ratio*100)}%)"
        logging.info(msg)
        print(msg)
        return

    try:
        payload: dict[str, Any] = {
            "value": ratio,  # float 0..1 for updates
            "valueStringOverride": f"{done}/{total}",
        }
        if status is not None:
            payload["status"] = status

        # IMPORTANT: target the same app_id as progress_begin
        win_update_progress(payload, app_id=APP_ID)

    except TypeError:
        # Some older builds don’t accept app_id kwarg; retry without it.
        try:
            win_update_progress(payload)
        except Exception as e2:
            logging.error(
                f"progress_update failed (no-app_id retry): {e2}", exc_info=True
            )
    except Exception as e:
        logging.error(f"progress_update failed: {e}", exc_info=True)


def progress_complete(message: str = "Completed!") -> None:
    """
    Mark progress as completed by updating the status text on the same toast.
    """
    if not sys.platform.startswith("win") or win_update_progress is None:
        logging.info(f"[Progress] {message}")
        print(f"[Progress] {message}")
        return

    try:
        win_update_progress({"status": message}, app_id=APP_ID)
    except TypeError:
        # Fallback if app_id param not supported
        try:
            win_update_progress({"status": message})
        except Exception as e2:
            logging.error(
                f"progress_complete failed (no-app_id retry): {e2}", exc_info=True
            )
    except Exception as e:
        logging.error(f"progress_complete failed: {e}", exc_info=True)


def resolve_destination(path: str, ask_meme: bool = False) -> Optional[str]:
    """
    Compute the destination folder for a file given its extension/category.
    Optionally asks the 'meme?' question for Media (when ask_meme=True).

    Skips files whose extension appears in SKIP_EXTENSIONS.

    Args:
        path: Absolute or relative file path to evaluate.
        ask_meme: If True and the file is in 'Media', prompt the user to redirect to 'Memes'.

    Returns:
        The destination folder path (string) or None if unknown/should skip.
    """
    entry_name = os.path.basename(path)

    # Skip by extension only
    if should_skip_by_extension(entry_name):
        return None

    if not os.path.isfile(path):
        return None

    ext = os.path.splitext(entry_name)[1].lower()
    for category, extensions in file_types.items():
        if ext in extensions:
            if category == "Media" and meme_enabled and ask_meme:
                return (
                    path_to_folders["Memes"]
                    if auto_gui.meme_yes_no()
                    else path_to_folders["Media"]
                )
            return path_to_folders[category]
    return None


def sort_file(
    path: str, notify: bool = True, planned_dest: Optional[str] = None
) -> Optional[str]:
    """
    Move a single file to its computed destination (based on extension category).

    Behavior:
      - Skips files whose extension is in SKIP_EXTENSIONS.
      - If 'planned_dest' is provided, uses it; otherwise computes via resolve_destination().
      - Ensures a non-conflicting filename in the destination.
      - Waits until the file size is stable before moving.
      - Optionally shows a toast on success.

    Args:
        path: Full path to the file to move.
        notify: If True, show a desktop notification after moving.
        planned_dest: If provided, use this folder instead of recomputing.

    Returns:
        The destination filepath if moved; otherwise None.
    """
    entry_name = os.path.basename(path)

    # Skip by extension only
    if should_skip_by_extension(entry_name):
        return None
    if not os.path.isfile(path):
        return None

    # Determine destination
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
        logging.info(f'Moved file: "{entry_name}" to folder: {dest_folder}')

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
    """
    Batch-scan the Downloads folder, move eligible files, and show a progress bar.

    Progress counting:
      - Only includes files that are *eligible to move*:
        - regular files (not directories)
        - not skipped by extension
        - resolvable to a valid destination (based on configured categories)
      - This ensures totals like 0/3 rather than counting skipped files.

    UI:
      - Shows a determinate toast progress bar.
      - Status line includes the current file (truncated) and destination category.
      - Suppresses per-file toasts; a single summary is shown at the end.
    """
    global pytray_icon

    print(f"DBG: pytray_icon at start of sort_files = {pytray_icon}")
    if pytray_icon is None:
        print("DBG: returning due to pytray_icon not yet init")
        return

    moved_files: list[str] = []

    try:
        if not os.path.exists(downloads_folder_path):
            return

        # Build a stable list of candidate files we *intend* to move
        with os.scandir(downloads_folder_path) as entries:
            raw_files = [e.path for e in entries if e.is_file()]

        # Filter to only files that are not skipped AND have a known destination
        candidates: list[tuple[str, str]] = []  # (path, dest_folder)
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

            # Show which file we're on (before moving)
            progress_update(done, total, status=f"{short_name} → {dest_label}")

            # Move (no per-file popup; we reuse the planned destination)
            result = sort_file(file_path, notify=False, planned_dest=dest_folder)
            if result:
                moved_files.append(os.path.basename(result))

            done += 1
            # Keep the status line in sync with the counter
            progress_update(done, total, status=f"{short_name} → {dest_label}")

        progress_complete("Completed!")

        # End-of-batch summary (as before)
        if moved_files:
            max_list = 3
            name = os.path.basename(file_path)
            listed = "\n".join(f"- {name[:45]}..." for name in moved_files[:max_list])
            if len(moved_files) > max_list:
                listed += f"\n...and {len(moved_files) - max_list} more"
            show_notification(message=listed, title="Files moved:", duration="long")

    except Exception as error:
        logging.error(f"ERROR: {error}", exc_info=True)
        sys.exit(1)


class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that monitors changes in the Downloads folder.
    """

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle filesystem modification events from watchdog.

        Debounces duplicate bursts, then processes only the concrete file that changed.
        Ignores files whose extension is configured to be skipped.
        """
        time.sleep(1)  # reduce duplicate triggers

        src = event.src_path
        src_text = (
            src.decode("utf-8", errors="surrogateescape")
            if isinstance(src, bytes)
            else str(src)
        )

        print(f"DBG: Found this new file in Downloads folder: {src_text}")
        if event.is_directory:
            return

        base = os.path.basename(src_text)
        if should_skip_by_extension(base):
            return

        sort_file(src_text)


def start_watching() -> None:
    """
    Starts the watchdog observer to monitor the Downloads folder.

    Returns:
        None
    """
    global observer
    if observer is None:  # Only start if not already running.
        event_handler = MyEventHandler()
        observer = Observer()
        observer.schedule(event_handler, downloads_folder_path, recursive=True)
        observer.start()
        print("DBG: Observer started and monitoring directory:", downloads_folder_path)
        print(f"DBG: observer.is_alive() = {observer.is_alive()}")
        sort_files()


def stop_watching() -> None:
    """
    Stops the watchdog observer if it's running.

    Returns:
        None
    """
    global observer
    if observer is not None:
        observer.stop()
        observer.join()  # Wait until the thread terminates.
        print("DBG: Observer stopped after joining.")
        print(f"DBG: observer.is_alive() = {observer.is_alive()}")
        observer = None


def main() -> None:
    """
    Main entry point for the file sorting automation script.

    Initializes file watching, sets up the system tray icon,
    and ensures proper error handling.

    Returns:
        None
    """
    global pytray_icon

    try:
        set_windows_app_id(APP_ID)  # use the same constant everywhere
        print(f"DBG: has_notificaiton = {pystray.Icon.HAS_NOTIFICATION}")

        # Create the tray icon with menus.
        pytray_icon = pystray.Icon(
            "my_pytray_icon",
            icon=auto_gui.create_icon(64, 64),
            title="AutoFileSort",
            menu=pystray.Menu(
                item(
                    "Start (active)", start_action, enabled=False
                ),  # Starts in active state.
                item("Stop", stop_action),
                item("Quit", quit_action),
            ),
        )

        # Start tray icon
        pytray_icon.run_detached()

        # Starts in watching/running state.
        start_watching()

    except Exception as error:
        logging.error(f"ERROR in main setup: {error}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
