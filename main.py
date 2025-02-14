# Desktop Automation Script: Sorting Files in the Downloads Folder

import os, shutil, logging, sys, pystray, time, auto_gui
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import MenuItem as item

# Global variable to keep track of state.
observer = None  # to store the observer thread from WatchDog
meme_enabled = True # Set to false to disable meme-button pop-up


def start_action(icon):
    """
    Callback for the "Start" menu item.
    Sets the global flag to True and (re)starts the observer.
    """
    start_watching()  # Restart the observer if it was stopped.
    update_menu(icon)

def stop_action(icon):
    """
    Callback for the "Stop" menu item.
    Sets the global flag to False and stops the observer.
    """
    stop_watching()  # Stop the observer completely.
    update_menu(icon)

def quit_action(icon):
    """
    Callback for the "Quit" menu item.
    """
    print("DEBUG: Quit action triggered. Exiting application...")
    icon.stop()

def update_menu(icon):
    """
    Updates the tray icon's menu based on the current state.
    """
    print("DEBUG: Updating menu. Current observer state =", observer)
    menu = pystray.Menu(
        item("Start" + (" (active)" if observer is not None else ""), start_action, enabled= observer is None),
        item("Stop" + (" (active)" if observer is None else ""), stop_action, enabled= observer is not None),
        item("Quit", quit_action)
    )
    icon.menu = menu
    icon.update_menu()
    print("DEBUG: Menu updated.")



#print("DBG: Operative system =", platform.uname()[0])  # e.g., "Windows", "Linux", or "Darwin" (for macOS)





# Each key is a category name and its value is a list of extensions that belong to that category.
file_types = {
    "Docs": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".dotx", ".doc", ".ppt", ".potx"],
    "Media": [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".webm", ".svg", ".webp", ".ico"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Programs": [".exe", ".msi", ".dmg", ".pkg", ".sh", ".iso"],
    "Development": [".py", ".js", ".html", ".css", ".cpp", ".java", ".sh", ".ipynb", ".json", ".md", ".m", ".drawio", ".ts", ".log"]
}

# os.path.expanduser("~") so that the paths work across different operating systems.
# On Windows, for example, os.path.expanduser("~") might be "C:\Users\name", while on macOS/Linux it would be "/Users/name" or "/home/name".
folder_paths = {
    "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "Media": os.path.join(os.path.expanduser("~"), "Desktop", "Media"),
    "Memes": os.path.join(os.path.expanduser("~"), "Desktop/Media", "Memes"),
    "Docs": os.path.join(os.path.expanduser("~"), "Desktop", "Docs"),
    "Archives": os.path.join(os.path.expanduser("~"), "Desktop", "Archives"),
    "Programs": os.path.join(os.path.expanduser("~"), "Desktop", "Programs"),
    "Development": os.path.join(os.path.expanduser("~"), "Desktop", "Development")
}

# Normalize the folder paths to ensure they are formatted correctly for the current operating system.
path_to_folders = {key: os.path.normpath(value) for key, value in folder_paths.items()}

# Create the folders if they do not already exist.
for path in path_to_folders.values():
    os.makedirs(path, exist_ok=True)

# Initialize the Downloads folder path, where new files are typically saved.
downloads_folder_path = path_to_folders["Downloads"]

# Logging to record file movements.
logging.basicConfig(filename= path_to_folders["Development"] + "\\file_auto-sorter.log", level=logging.INFO, format="%(asctime)s - %(message)s")

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
        while os.path.exists(os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")):
            counter += 1
        return os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")
    
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
            stable_count += check_interval  # Increase the stable count if size doesn't change.
        else:
            stable_count = 0  # Reset if the file size changes.
        prev_size = current_size
        time.sleep(check_interval)
    
    return True  # file is considered stable.

def sorter():
    """
    Scans the Downloads folder and moves files to their corresponding destination folders
    based on their file extension. Files that are still being downloaded or are temporary
    (e.g., .crdownload, .part) are skipped.
    
    Catches:
        Error: If any exception occurs and store in logfile.
    """
    try: 
        if os.path.exists(downloads_folder_path):
            # Iterate over all entries (files and folders) in the Downloads directory.
            with os.scandir(downloads_folder_path) as entries:
        
                for entry in entries:

                    # Skip temporary files that indicate an ongoing download.
                    if entry.name.endswith((".crdownload", ".part", ".download", ".!ut", ".tmp")):
                        print(f"DBG: Skipping temporary file: {entry.name}")
                        continue  # Do not process these files.

                    elif entry.is_file():
                        # Get the file extension in lowercase for case-insensitive matching.
                        file_extension = os.path.splitext(entry.name)[1].lower()
                        dest_folder = None

                        # Determine the destination folder by checking the file extension.
                        for category, extensions in file_types.items():
                            if file_extension in extensions:
                                if category == "Media" and meme_enabled:
                                    if auto_gui.Meme_yes_no():
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
                        logging.info(f"Moved {entry.name} to {dest_folder}")

    except Exception as error:
        logging.error(f"ERROR: {error}", exc_info=True)
        sys.exit(1)


class MyEventHandler(FileSystemEventHandler):
    """
    Custom event handler that monitors changes in the Downloads folder.
    When a modification is detected in selected folder, it triggers the sorter() function.
    """
    def on_modified(self, event):
        # Wait a moment to reduce duplicate triggers of sorting function.
        time.sleep(1)
        print(f"DBG: Found this new file in Downloads folder: {event.src_path}")
        sorter()


def start_watching():
    """
    Starts the watchdog observer to monitor the Downloads folder.
    Creates a new Observer instance and starts it.
    """
    global observer
    if observer is None:  # Only start if not already running.
        event_handler = MyEventHandler()
        observer = Observer()
        observer.schedule(event_handler, downloads_folder_path, recursive=True)
        observer.start()
        print("DBG: Observer started and monitoring directory:", downloads_folder_path)
        print(f"DBG: observer.is_alive() = {observer.is_alive()}")
        sorter()

def stop_watching():
    """
    Stops the watchdog observer if it's running.
    Calls stop() and join() to cleanly terminate the observer's thread.
    """
    global observer
    if observer is not None:
        observer.stop()
        observer.join()  # Wait until the thread terminates.
        print("DBG: Observer stopped after joining.")
        print(f"DBG: observer.is_alive() = {observer.is_alive()}")
        observer = None



if __name__ == "__main__":
    try:
        # Starts in watching/running state.
        start_watching()

        # Create the tray icon with menus.
        icon = pystray.Icon(
            "my_tray_icon",
            icon=auto_gui.create_icon(64, 64),
            title="My Tray Icon",
            menu=pystray.Menu(
                item("Start" + (" (active)" if observer is not None else ""), start_action, enabled= observer is None), # Starts in active state.
                item("Stop", stop_action),
                item("Quit", quit_action)
            )
        )

    except Exception as error:
        logging.error(f"ERROR in main setup: {error}", exc_info=True)
        sys.exit(1)

    # Run the tray icon on the main thread (required for macOS)
    try:
        icon.run()
    except Exception as error:
        logging.error(f"ERROR in tray icon: {error}", exc_info=True)
        sys.exit(1)
