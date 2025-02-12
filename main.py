# Desktop Automation Script: Sorting Files in the Downloads Folder


# Step 1: Access the Downloads Folder
# -----------------------------------
# What: Find and open the Downloads folder on your computer.
# Why: The script needs to know where to look for the files that need to be sorted.
# Tips:
# - Use os.path.expanduser("~") to get your home directory, then add "Downloads" to that path.
# - Check if the folder exists and handle any errors if it doesn't or if you don't have permission.
# - Use functions like os.listdir() or pathlib.Path.iterdir() to list all files in the folder.

import os, platform, shutil, logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

print("DBG: Operative system =", platform.uname()[0]) #if we want to switch between windows and linux/mac


# Configure logging to track file movements
logging.basicConfig(filename="file_sorter.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# file extensions mapping to categories
file_types = {
    "Docs": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".dotx",".doc"],
    "Media": [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".webm", ".svg", ".webp"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Programs": [".exe", ".msi", ".dmg", ".pkg", ".sh"],
    "Development": [".py", ".js", ".html", ".css", ".cpp", ".java", ".sh", ".ipynb", ".json", ".md", ".m", ".drawio", ".ts"]
}

# Define folder locations (normalized for cross-platform compatibility)
folder_paths = {
    "Downloads": "Downloads",
    "Media": "Desktop/Media",
    "Docs": "Desktop/Docs",
    "Archives": "Desktop/Archives",
    "Programs": "Desktop/Programs",
    "Development": "Desktop/Development"
}

path_to_folders = {
    key: os.path.normpath(os.path.join(os.path.expanduser("~"), value))
    for key, value in folder_paths.items()
}

# make sure folders exist
for path in path_to_folders.values():
    os.makedirs(path, exist_ok=True)


# Init path to "Downloads" (the folder that files are directly downloaded into)
downloads_folder = path_to_folders["Downloads"]

def sorter():
    if os.path.exists(downloads_folder):
            with os.scandir(downloads_folder) as entries:
                for entry in entries:
                    if entry.is_file():
                        file_extension = os.path.splitext(entry.name)[1].lower()  # Ensure extension matching
                        dest_folder = None

                        for category, extensions in file_types.items():
                            if file_extension in extensions:
                                dest_folder = path_to_folders[category]
                                break
                        
                        # If no category was found for the extension, continue (leaves current file in "Downloads" folder for now)
                        if not dest_folder:
                            continue

                        # Double check that folders exist
                        os.makedirs(dest_folder, exist_ok=True)

                        dest_path = os.path.join(dest_folder, entry.name)
                        if os.path.exists(dest_path):
                            file_name, extension = os.path.splitext(entry.name)
                            counter = 1
                            while os.path.exists(os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")):
                                counter += 1
                            dest_path = os.path.join(dest_folder, f"{file_name}_{'('+str(counter)+')'}{extension}")
                        
                        #Move the file
                        print("DBG: Moving it to", dest_path)
                        shutil.move(entry.path, dest_path)

                        # Log the move
                        logging.info(f"Moved {entry.name} to {dest_folder}")
                                        


    else:
        raise OSError("Downloads folder was not found...")



class MyEventHandler(FileSystemEventHandler):

    def on_modified(self, event):
        print(f"Found this new file in Downloads folder: {event.src_path}")
        sorter()

    
if __name__ == "__main__":
    sorter() #Initial sorting
    path = downloads_folder  # Directory/folder to monitor
    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)

    # Start the observer
    observer.start()
    print(f"Monitoring directory: {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Step 2: Sort Files by Format 
# ----------------------------
# What: Move files into different folders based on their file type (for example, .pdf, .jpg, etc.).
# Why: Sorting by file type makes it easier to organize and find your files later.
# Tips:
# - Create a dictionary or configuration (like a JSON file) that maps file extensions to specific folders.
# - Convert file extensions to lower case to avoid issues with case sensitivity.
# - Decide what to do with files that don’t have an extension or have an unknown extension.
# - Handle cases where a file with the same name already exists in the destination by renaming it (for example, adding a timestamp).




# Step 3: Monitor the Downloads Folder for New Files (Watchdog library)
# --------------------------------------------------
# What: Watch the Downloads folder for any new files that get added.
# Why: Automatically sorting new files means you don't have to run the script manually every time.
# Tips:
# - Use a library like 'watchdog' to detect when new files are added to the folder.
# - Make sure the file is completely downloaded (i.e., not still in progress) before trying to move it.
# - Consider that sometimes multiple events may trigger for a single file; a short delay or a check for file stability can help.





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
