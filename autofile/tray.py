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
    """Set Windows App User Model ID for toast notifications."""
    if not sys.platform.startswith("win"):
        return
    try:  # pragma: no cover
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:  # pragma: no cover
        logging.warning("Failed to set AppUserModelID: %s", e)


def start_action(icon: Any) -> None:
    """Callback for the 'Start' menu item."""
    start_watching()
    update_menu(icon)


def stop_action(icon: Any) -> None:
    """Callback for the 'Stop' menu item."""
    stop_watching()
    update_menu(icon)


def quit_action(icon: Any) -> None:
    """Quit the application."""
    icon.stop()


def update_menu(icon: Any) -> None:
    """Rebuild the tray menu based on current state."""
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
    """Custom event handler that monitors changes in the Downloads folder."""

    def on_modified(self, event: FileSystemEvent) -> None:
        time.sleep(1)
        src = event.src_path if isinstance(event.src_path, str) else str(event.src_path)
        if event.is_directory:
            return
        base = os.path.basename(src)
        if should_skip_by_extension(base):
            return
        sort_file(src)


def start_watching() -> None:
    """Start the watchdog observer to monitor the Downloads folder."""
    global observer
    if observer is None:
        event_handler = MyEventHandler()
        observer = Observer()
        observer.schedule(event_handler, DOWNLOADS_FOLDER_PATH, recursive=True)
        observer.start()
        sort_files()


def stop_watching() -> None:
    """Stop the watchdog observer if it's running."""
    global observer
    if observer is not None:
        observer.stop()
        observer.join()
        observer = None


def main() -> None:
    """Main entry point for the AutoSort tray application."""
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
