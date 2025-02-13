# Desktop Automation Script: Sorting Files in the Downloads Folder

import os, platform, shutil, logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

import tkinter as tk


def Meme_yes_no():
    """
    Displays a nicely formatted, borderless pop-up asking "Meme?" with Yes and No buttons.
    The window appears in the center of the screen with a dark grey background.
    
    Returns:
        bool: True if "Yes" is clicked, False if "No" is clicked.
    """
    is_meme = False  # Default value

    # Create the main window
    root = tk.Tk()
    root.overrideredirect(True)  # Remove the title bar and window borders
    root.configure(bg="#2e2e2e")  # Set a dark grey background for a modern look

    # Set window size
    window_width, window_height = 250, 100

    # Calculate the center position of the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    # Set the geometry of the window to center it on the screen
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Create a label for the question "Meme?" in white text
    question_label = tk.Label(root, text="Meme?", font=("Helvetica", 16, "bold"), bg="#2e2e2e", fg="white")
    question_label.pack(pady=10)

    # Create a frame to hold the buttons side by side, with the same dark background
    button_frame = tk.Frame(root, bg="#2e2e2e")
    button_frame.pack(pady=10)

    # Callback for "Yes" button: set is_meme to True and close the window.
    def on_yes():
        nonlocal is_meme
        is_meme = True
        root.destroy()

    # Callback for "No" button: set is_meme to False and close the window.
    def on_no():
        nonlocal is_meme
        is_meme = False
        root.destroy()

    # Create the "Yes" button with a modern color scheme.
    yes_button = tk.Button(
        button_frame, text="Yes", command=on_yes, width=10,
        bg="#4CAF50", fg="white", activebackground="#45a049", relief="flat", font=("Helvetica", 12)
    )
    yes_button.pack(side="left", padx=10)

    # Create the "No" button with a modern color scheme.
    no_button = tk.Button(
        button_frame, text="No", command=on_no, width=10,
        bg="#f44336", fg="white", activebackground="#e53935", relief="flat", font=("Helvetica", 12)
    )
    no_button.pack(side="left", padx=10)

    # Start the Tkinter event loop
    root.attributes('-topmost', True)
    root.mainloop()

    # Return the result of the user's choice
    return is_meme


# Print the operating system for debugging purposes.
# This helps you determine if any OS-specific behavior is needed.
print("DBG: Operative system =", platform.uname()[0])  # e.g., "Windows", "Linux", or "Darwin" (for macOS)

# Logging to record file movements.
logging.basicConfig(filename="file_sorter.log", level=logging.INFO, format="%(asctime)s - %(message)s")



# Each key is a category name and its value is a list of extensions that belong to that category.
file_types = {
    "Docs": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".dotx", ".doc", ".ppt", ".potx"],
    "Media": [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".webm", ".svg", ".webp"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Programs": [".exe", ".msi", ".dmg", ".pkg", ".sh", ".iso"],
    "Development": [".py", ".js", ".html", ".css", ".cpp", ".java", ".sh", ".ipynb", ".json", ".md", ".m", ".drawio", ".ts"]
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
    
    Raises:
        OSError: If the Downloads folder is not found.
    """
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
                            if category == "Media" and Meme_yes_no():
                                    dest_folder = path_to_folders["Memes"]
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
    else:
        raise OSError("Downloads folder was not found...")


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


if __name__ == "__main__":
    # Perform an initial sorting of the Downloads folder.
    sorter()
    
    # Set up the observer to monitor selected folder for changes.
    path = downloads_folder_path  # The folder to be monitored.
    event_handler = MyEventHandler() 
    observer = Observer()  
    observer.schedule(event_handler, path, recursive=True)

    # Start the observer to continuously monitor the folder.
    observer.start()
    print(f"DBG: Monitoring directory: {path}")

    try:
        # Keep the script running indefinitely.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # If the user presses Ctrl+C, stop the observer.
        observer.stop()
    observer.join()  # Wait for the observer to finish.



# Step 4: Auto-start and Background Execution
# -------------------------------------------
# What: Ensure that the script starts automatically and runs in the background.
# Why: This way, your file sorting is always active without needing to start the script manually.
# Tips:
# - On Windows, explore options like adding a shortcut to the Startup folder, using Task Scheduler, or creating a Windows service.
# - Implement logging to keep track of what the script is doing and to help with troubleshooting any issues.
# - Ensure your script can shut down gracefully, especially if it's running in the background.
# - Optionally, you could add a simple interface (like a system tray icon) to indicate that the script is running.

# Additional Considerations
# -------------------------
# What: Think about potential problems and how to handle them.
# Why: Being prepared for issues helps prevent errors and makes the script more robust.
# Tips:
# - Use try-except blocks to catch errors like permission problems or files that are being used by other programs.
# - Write clear comments and documentation within your code so you remember why each part is important.
# - Consider writing tests or using manual testing to simulate scenarios like duplicate file names or interrupted downloads.
