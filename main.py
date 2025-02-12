# Desktop Automation Script: Sorting Files in the Downloads Folder


# Step 1: Access the Downloads Folder
# -----------------------------------
# What: Find and open the Downloads folder on your computer.
# Why: The script needs to know where to look for the files that need to be sorted.
# Tips:
# - Use os.path.expanduser("~") to get your home directory, then add "Downloads" to that path.
# - Check if the folder exists and handle any errors if it doesn't or if you don't have permission.
# - Use functions like os.listdir() or pathlib.Path.iterdir() to list all files in the folder.

import os, platform, shutil

print(platform.uname()[0]) #if we want to switch between windows and linux/mac


audio_format = [".mp3", ".mp4", ".wav"]
video_format = [".mp4", ".mov", ".wav"]

folder_paths = {
    "Download": "Downloads",
    "Audio": "Desktop\Audio Files",
    "Video": "Desktop\Video Files",
    "Images": "Desktop\Image Files",
    "Documents": "Desktop\Documents",

}

path_to_folders = {
    key: os.path.normpath(os.path.join(os.path.expanduser("~"), value))
    for key, value in folder_paths.items()
}

# Create folders if they don’t exist
for path in path_to_folders.values():
    os.makedirs(path, exist_ok=True)


print(path_to_folders)

# Dynamic path to the folders:
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
audio_folder = os.path.join(os.path.expanduser("~"), "Desktop\Audio Files")
print("DBG: downloads path = ", downloads_folder)
print("DBG: audio path = ", audio_folder)


# Check if the folder exists before trying to access it:
if os.path.exists(downloads_folder):
    with os.scandir(downloads_folder) as entries:
        print("entries.next() = ", entries.__next__())
        for entry in entries:
            if os.path.splitext(entry.name)[1] in audio_format:
                shutil.move(entry.path, audio_folder)
            elif os.path.splitext(entry.name)[1] in video_format:
                pass


else:
    print("Downloads folder not found at:", downloads_folder)



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
