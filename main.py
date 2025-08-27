"""
AutoFileSort Script for Sorting Files from one folder to other folders (one to many).

This script monitors the selected foler ("Downloads"-folder is the default selection)
and automatically moves files to their corresponding destination folders based on file extensions.
Also uses a system tray icon for user control.
"""

import os
import shutil
import logging
import sys
import subprocess
import pystray
import time
import auto_gui
import threading
from pathlib import Path
from typing import Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import MenuItem as item


# Prefer native Windows 11 toasts if available
try:  # pragma: no cover
    from win11toast import notify as win_notify, toast as win_toast  # type: ignore
except Exception:
    win_notify = None
    win_toast = None

# Cross-platform fallback notifications (simple, no click callback)
try:  # pragma: no cover
    from plyer import notification as plyer_notification  # type: ignore
except Exception:
    plyer_notification = None


# Global variable to keep track of state.
observer = None  # to store the observer thread from WatchDog
meme_enabled: bool = True  # Set to false to disable meme-button pop-up
tray_icon = None


def start_action(tray_icon) -> None:
    """
    Callback for the "Start" menu item.
    Sets the global flag to True and (re)starts the observer.

    Args:
        tray_icon (pystray.Icon): The system tray icon instance to update.

    Returns:
        None
    """
    start_watching()
    update_menu(tray_icon)


def stop_action(tray_icon) -> None:
    """
    Callback for the "Stop" menu item.
    Sets the global flag to False and stops the observer.

    Args:
        tray_icon (pystray.Icon): The system tray icon instance to update.

    Returns:
        None
    """
    stop_watching()
    update_menu(tray_icon)


def quit_action(tray_icon) -> None:
    """
    Callback for the "Quit" menu item. Stops the tray icon event loop.

    Args:
        tray_icon (pystray.Icon): The system tray icon instance.

    Returns:
        None
    """
    print("DEBUG: Quit action triggered. Exiting application...")
    tray_icon.stop()


def update_menu(tray_icon) -> None:
    """
    Rebuild and apply the tray icon menu based on current state (running/stopped).

    Args:
        tray_icon (pystray.Icon): The system tray icon whose menu should be updated.

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
    tray_icon.menu = menu
    print("DEBUG: Menu updated.")


# Each key is a category name and its value is a list of extensions that belong to that category.
file_types = {
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


def is_file_fully_downloaded(file_path: str, wait_time=2, check_interval=1) -> bool:
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
    except Exception as error:
        logging.error(
            f"Failed to open file location for {file_path}: {error}", exc_info=True
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

            def _run_toast():
                try:
                    win_toast(
                        title or "Notification",
                        message,
                        on_click=lambda args=None: open_file_location(abs_file),
                        **toast_kwargs,
                    )
                except Exception as e:
                    logging.error(f"Toast (select_file) failed: {e}", exc_info=True)

            threading.Thread(target=_run_toast, daemon=True).start()
            return

        # Case 2: open a folder (no highlight) → URL works with notify (non-blocking)
        if open_folder and win_notify is not None:
            folder_uri = Path(open_folder).resolve().as_uri()
            win_notify(
                title or "Notification", message, on_click=folder_uri, **toast_kwargs
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

    except Exception as e:
        logging.error(f"Toast failed: {e}", exc_info=True)
        print(f"[Notification error] {title}: {message}")


def sort_files():

    global tray_icon

    """
    Scans the Downloads folder and moves files to their corresponding destination folders
    based on their file extension. 
    Files that are still being downloaded or are temporary (e.g., .crdownload, .part) are skipped.
    
    Catches:
        Error: If any exception occurs and store in logfile.
    """
    print(f"DBG: tray_icon at start of sort_files = {tray_icon}")
    if tray_icon is None:
        print("DBG: reutrning due to Tray_icon not yet init")
        return

    try:
        if os.path.exists(downloads_folder_path):
            # Iterate over all entries (files and folders) in the Downloads directory.
            with os.scandir(downloads_folder_path) as entries:

                for entry in entries:

                    # Skip temporary files that indicate an ongoing download.
                    if entry.name.endswith(
                        (".crdownload", ".part", ".download", ".!ut", ".tmp")
                    ):
                        print(f"DBG: Skipping temporary file: {entry.name}")
                        continue  # Do not process these files.
                    elif (
                        entry.name.lower().__contains__("outlier")
                        or entry.name.lower().__contains__("handelsbanken")
                        or entry.name.lower().__contains__("allkort")
                    ):
                        print("Skipping current downloaded filefiles....")
                        logging.info(f'Skipped moving: "{entry.name}"')
                        continue

                    elif entry.is_file():
                        # Get the file extension in lowercase for case-insensitive matching.
                        file_extension = os.path.splitext(entry.name)[1].lower()
                        dest_folder = None

                        # Determine the destination folder by checking the file extension.
                        for category, extensions in file_types.items():
                            if file_extension in extensions:
                                if category == "Media" and meme_enabled:
                                    if auto_gui.meme_yes_no():
                                        dest_folder = path_to_folders["Memes"]
                                    else:
                                        dest_folder = path_to_folders[category]
                                else:
                                    dest_folder = path_to_folders[category]
                                    break

                        # If the file's extension does not match any category, leave it in Downloads/starting folder.
                        if not dest_folder:
                            continue

                        # Ensure the destination folder exists.
                        os.makedirs(dest_folder, exist_ok=True)

                        # Check and adjust the file name if there is a duplicate in the destination folder.
                        filename_dest_path = check_name(dest_folder, entry.name)

                        # Check if the file is fully downloaded before moving.
                        if is_file_fully_downloaded(entry.path):
                            print("DBG: File stable, Moving it to", filename_dest_path)
                            shutil.move(entry.path, filename_dest_path)

                        # Log the file movement.
                        logging.info(
                            f'Moved file: "{entry.name}" to folder: {dest_folder}'
                        )

                        print(f"DBG: tray_icon = {tray_icon}")

                        # Show a desktop notification. On Windows the user can
                        # click the notification to open the moved file's
                        # location in the file explorer.
                        show_notification(
                            message=f'- "{entry.name}" \n Moved to \n - {dest_folder}',
                            title="File moved",
                            select_file=filename_dest_path,  # <-- open Explorer and highlight this file
                            duration="short",
                            audio={"silent": "true"},
                        )

    except Exception as error:
        logging.error(f"ERROR: {error}", exc_info=True)
        sys.exit(1)


class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that monitors changes in the Downloads folder.
    """

    def on_modified(self, event) -> None:
        """
        Handle filesystem modification events from watchdog.

        Debounces rapid successive events by sleeping briefly, then triggers sorting.

        Args:
            event (watchdog.events.FileSystemEvent): The filesystem event supplied by watchdog.

        Returns:
            None
        """
        time.sleep(1)  # reduce duplicate triggers
        print(f"DBG: Found this new file in Downloads folder: {event.src_path}")
        sort_files()


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
    global tray_icon

    try:
        print(f"DBG: has_notificaiton = {pystray.Icon.HAS_NOTIFICATION}")

        # Create the tray icon with menus.
        tray_icon = pystray.Icon(
            "my_tray_icon",
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
        tray_icon.run_detached()

        # Starts in watching/running state.
        start_watching()

    except Exception as error:
        logging.error(f"ERROR in main setup: {error}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
