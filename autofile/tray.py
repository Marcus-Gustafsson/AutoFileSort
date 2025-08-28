"""System tray integration and file watcher for AutoSort."""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Optional

import pystray
from pystray import MenuItem as item
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import auto_gui
from .config import DOWNLOADS_FOLDER_PATH
from .notifications import APP_ID
from .sorter import sort_file, sort_files, should_skip_by_extension

observer: Optional[Any] = None
pytray_icon: Optional[Any] = None


def set_windows_app_id(app_id: str = APP_ID) -> None:
    """Configure the App User Model ID for Windows notifications.

    Args:
        app_id: Identifier used by the notification system.

    Returns:
        None.

    Side Effects:
        Registers the process with Windows; no effect on other platforms.
    """
    if not sys.platform.startswith("win"):
        return
    try:  # pragma: no cover
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:  # pragma: no cover
        logging.warning("Failed to set AppUserModelID: %s", e)


def start_action(icon: Any) -> None:
    """Start watching for file changes and refresh the menu.

    Args:
        icon: Pystray icon instance.

    Returns:
        None.

    Side Effects:
        Begins filesystem monitoring and updates the tray menu.
    """
    start_watching()
    update_menu(icon)


def stop_action(icon: Any) -> None:
    """Stop watching for file changes and refresh the menu.

    Args:
        icon: Pystray icon instance.

    Returns:
        None.

    Side Effects:
        Stops filesystem monitoring and updates the tray menu.
    """
    stop_watching()
    update_menu(icon)


def quit_action(icon: Any) -> None:
    """Exit the tray application.

    Args:
        icon: Pystray icon instance.

    Returns:
        None.

    Side Effects:
        Stops the icon's event loop.
    """
    icon.stop()


def update_menu(icon: Any) -> None:
    """Rebuild the tray menu based on the observer state.

    Args:
        icon: Pystray icon instance.

    Returns:
        None.

    Side Effects:
        Mutates the menu of the provided icon.
    """
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
    icon.menu = menu


class MyEventHandler(FileSystemEventHandler):
    """Monitor changes in the Downloads folder and trigger sorting."""

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: Watchdog event describing the change.

        Returns:
            None.

        Side Effects:
            Sorts the file if eligible.
        """
        time.sleep(1)
        src = event.src_path if isinstance(event.src_path, str) else str(event.src_path)
        if event.is_directory:
            return
        base = os.path.basename(src)
        if should_skip_by_extension(base):
            return
        sort_file(src)


def start_watching() -> None:
    """Begin monitoring the Downloads folder.

    Returns:
        None.

    Side Effects:
        Starts a watchdog observer and may immediately sort existing files.
    """
    global observer
    if observer is None:
        event_handler = MyEventHandler()
        observer = Observer()
        observer.schedule(event_handler, DOWNLOADS_FOLDER_PATH, recursive=True)
        observer.start()
        sort_files()


def stop_watching() -> None:
    """Stop the active watchdog observer.

    Returns:
        None.

    Side Effects:
        Terminates the observer thread.
    """
    global observer
    if observer is not None:
        observer.stop()
        observer.join()
        observer = None


def main() -> None:
    """Launch the system tray application.

    Returns:
        None.

    Side Effects:
        Creates a tray icon, starts a GUI event loop, and begins monitoring the
        Downloads folder.
    """
    global pytray_icon
    try:
        set_windows_app_id(APP_ID)
        pytray_icon = pystray.Icon(
            "my_pytray_icon",
            icon=auto_gui.create_icon(64, 64),
            title="AutoSort",
            menu=pystray.Menu(
                item("Start (active)", start_action, enabled=False),
                item("Stop", stop_action),
                item("Quit", quit_action),
            ),
        )
        pytray_icon.run_detached()
        start_watching()
    except Exception as error:  # pragma: no cover
        logging.error("ERROR in main setup: %s", error, exc_info=True)
        sys.exit(1)
