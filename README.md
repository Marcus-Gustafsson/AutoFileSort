# 📂 AutoSort

## Overview
AutoSort monitors a folder (Downloads by default) and moves new files into category folders based on their extensions. A system tray icon provides Start, Stop, and Quit controls, and an optional mene pop-up lets you decide where to file images.

### Categories
Docs, Media, Archives, Programs, and Development. Edit or add extensions in [`config/file_types.json`](config/file_types.json).

## Installation
```sh
git clone https://github.com/Marcus-Gustafsson/AutoSort.git
cd AutoSort
uv sync --dev
uv run python main.py
```
`uv` automatically creates and uses a `.venv`.

### Updating dependencies
```sh
uv add <package>  # add a dependency
uv lock           # update uv.lock after editing pyproject.toml
```

## Auto-start on Windows
Create `Run_AutoSort.bat`:
```batch
@echo off
cd /d "C:\path\to\AutoSort"
uv run pythonw main.py
exit
```
Place the batch file in the Startup folder (`Win + R` → `shell:startup`) to launch AutoSort on login.

## System Tray & Notifications
The tray menu provides Start, Stop, and Quit actions. Windows users receive toast notifications via win11toast.
