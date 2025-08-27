"""Notification utilities for AutoSorter."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

APP_ID = "AutoFileSort"

try:  # pragma: no cover
    from win11toast import (
        notify as win_notify,
        toast as win_toast,
        update_progress as win_update_progress,
    )
except Exception:  # pragma: no cover
    win_notify = None
    win_toast = None
    win_update_progress = None


def open_file_location(file_path: str) -> None:
    """Open the system file explorer showing the given file."""
    normalized_path = os.path.normpath(os.path.abspath(file_path))
    try:
        if sys.platform.startswith("win"):
            cmd = f'explorer /select,"{normalized_path}"'
            subprocess.run(cmd, shell=True, check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", normalized_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(normalized_path)], check=False)
    except Exception as err:  # pragma: no cover
        logging.error(
            "Failed to open file location for %s: %s", file_path, err, exc_info=True
        )


def show_notification(
    message: str,
    title: str = "",
    select_file: Optional[str] = None,
    open_folder: Optional[str] = None,
    **toast_kwargs: Any,
) -> None:
    """Show a Windows toast or print to console on other platforms."""
    if not sys.platform.startswith("win") or win_toast is None:
        logging.info("%s %s", title, message)
        print(title, message)
        return

    def callback(_: Any) -> None:
        if select_file:
            open_file_location(select_file)
        elif open_folder:
            open_file_location(open_folder)

    try:
        win_toast(
            APP_ID,
            message,
            icon=str(Path(__file__).resolve().parents[1] / "exe_icon.ico"),
            on_click=callback if select_file or open_folder else None,
            app_id=APP_ID,
            title=title,
            **toast_kwargs,
        )
    except Exception as err:  # pragma: no cover
        logging.error("show_notification failed: %s", err, exc_info=True)


def progress_begin(initial_status: str, total: int) -> None:
    """Start a progress notification."""
    if not sys.platform.startswith("win") or win_notify is None:
        logging.info("[Progress] %s 0/%d", initial_status, total)
        print(f"[Progress] {initial_status} 0/{total}")
        return
    try:
        win_notify(
            APP_ID,
            "Batch sorting ...",
            app_id=APP_ID,
            progress={
                "title": "Progress",
                "status": initial_status,
                "value": "0",
                "valueStringOverride": f"0/{total}",
            },
            icon=str(Path(__file__).resolve().parents[1] / "exe_icon.ico"),
        )
        time.sleep(0.2)
    except Exception as err:  # pragma: no cover
        logging.error("progress_begin failed: %s", err, exc_info=True)


def progress_update(done: int, total: int, status: str | None = None) -> None:
    """Update the active progress notification."""
    ratio = 0.0 if total <= 0 else max(0.0, min(1.0, done / total))
    if not sys.platform.startswith("win") or win_update_progress is None:
        msg = f"[Progress] {status or 'Working...'} {done}/{total} ({int(ratio*100)}%)"
        logging.info(msg)
        print(msg)
        return
    payload: dict[str, Any] = {
        "value": ratio,
        "valueStringOverride": f"{done}/{total}",
    }
    if status is not None:
        payload["status"] = status
    try:
        win_update_progress(payload, app_id=APP_ID)
    except TypeError:  # pragma: no cover
        try:
            win_update_progress(payload)
        except Exception as e2:
            logging.error(
                "progress_update failed (no-app_id retry): %s", e2, exc_info=True
            )
    except Exception as e:  # pragma: no cover
        logging.error("progress_update failed: %s", e, exc_info=True)


def progress_complete(message: str = "Completed!") -> None:
    """Mark the progress toast as completed."""
    if not sys.platform.startswith("win") or win_update_progress is None:
        logging.info("[Progress] %s", message)
        print(f"[Progress] {message}")
        return
    try:
        win_update_progress({"status": message}, app_id=APP_ID)
    except TypeError:  # pragma: no cover
        try:
            win_update_progress({"status": message})
        except Exception as e2:
            logging.error(
                "progress_complete failed (no-app_id retry): %s", e2, exc_info=True
            )
    except Exception as e:  # pragma: no cover
        logging.error("progress_complete failed: %s", e, exc_info=True)
