# Desktop Automation Script: Sorting Files in the Downloads Folder

import os, platform, shutil, logging, sys, threading, math, pystray, time, tkinter as tk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# Global variable to keep track of our "running" state.
running = True
stop_event = threading.Event()
observer_thread = None  # to store the observer thread

def create_icon(width=64, height=64):
    """
    The icon consists of:
      - A folder: drawn as a rectangle (folder body) and a polygon (folder tab).
      - A U-turn arrow: drawn as an arc with a small arrow head at its end.
    
    Args:
        width (int): The width of the icon image.
        height (int): The height of the icon image.
    
    Returns:
        PIL.Image: The generated icon image.
    """
    
    # Create a blank image with a white background.
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Folder body: a rectangle from (4, 24) to (60, 52)
    folder_body = (4, 24, 60, 52)
    draw.rectangle(folder_body, fill='gold', outline='black')
    
    # Folder tab: a polygon on top of the folder body.
    folder_tab = [(4, 24), (20, 12), (36, 12), (36, 24)]
    draw.polygon(folder_tab, fill='goldenrod', outline='black')
    
    center_x, center_y = 32, 39  # (Approximately center of folder_body)
    
    # Choose a radius for the arc. Adjust this value to make the arrow larger or smaller.
    r = 12  # Radius of the arc
    
    # Define a bounding box for the arc (a circle centered at (center_x, center_y) with radius r)
    bbox = (center_x - r, center_y - r, center_x + r, center_y + r)
    
    # Define the start and end angles for the arc
    # Note: In Pillow, 0° is at 3 o'clock and angles increase counterclockwise.
    start_angle = 130  # Start angle of arc (in degrees)
    end_angle = 35     # End angle of arc (equivalent to 380° for a 180° span)
    
    # Draw the arc with the defined bounding box and angles.
    draw.arc(bbox, start=start_angle, end=end_angle, fill='black', width=4)
    
    # Calculate the endpoint
    angle_rad = math.radians(end_angle)
    bottom_right_x = center_x + r * math.cos(angle_rad)
    bottom_right_y = center_y + r * math.sin(angle_rad)
    bottom_right = (bottom_right_x + 3, bottom_right_y + 3)
    
    # Draw the arrow head at the arrow tip.
    #   p1: Bottom right corner
    #   p2: Top left corner
    #   p3: Bottom left corner (arrow tip)
    p1 = bottom_right
    p2 = (bottom_right_x - 4, bottom_right_y - 4)
    p3 = (bottom_right_x - 4, bottom_right_y + 3)
    arrow_head = [p1, p2, p3]
    
    draw.polygon(arrow_head, fill='black')
    return image


def start_action(icon, item):
    """
    Callback for the "Start" menu item.
    """
    global running, observer_thread
    running = True
    print("DEBUG: Start action triggered. Running =", running)
    update_menu(icon)

def stop_action(icon, item):
    """
    Callback for the "Stop" menu item.
    """
    global running, observer_thread
    running = False
    print("DEBUG: Stop action triggered. Running =", running)
    update_menu(icon)

def quit_action(icon, item):
    """
    Callback for the "Quit" menu item.
    """
    print("DEBUG: Quit action triggered. Exiting application...")
    stop_event.set()  # Signal observer thread to stop.
    icon.stop()

def update_menu(icon):
    """
    Updates the tray icon's menu based on the current running state.
    """
    print("DEBUG: Updating menu. Current running state =", running)
    menu = pystray.Menu(
        item("Start" + (" (active)" if running else ""), start_action, enabled=not running),
        item("Stop" + (" (active)" if not running else ""), stop_action, enabled=running),
        item("Quit", quit_action)
    )
    icon.menu = menu
    icon.update_menu()
    print("DEBUG: Menu updated.")

# Create the tray icon with menus.
icon = pystray.Icon(
    "my_tray_icon",
    icon=create_icon(64, 64),
    title="My Tray Icon",
    menu=pystray.Menu(
        item("Start" + (" (active)" if running else ""), start_action, enabled=not running),
        item("Stop", stop_action),
        item("Quit", quit_action)
    )
)



def Meme_yes_no():
    """
    Borderless pop-up asking "Meme?" with Yes and No buttons.
    The window appears in the center of the screen.
    
    Returns:
        bool: True if "Yes" is clicked, False if "No" is clicked.
    """
    is_meme = False  # Default value

    # Create the main window
    root = tk.Tk()
    root.overrideredirect(True)  # Remove the title bar and window borders
    root.configure(bg="#2e2e2e")  # "#2e2e2e" = dark grey background

    # Set window size
    window_width, window_height = 250, 100

    # Calculate the center position of the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)

    # Set the geometry of the window to center it on the screen
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Label/text for the question
    question_label = tk.Label(root, text="Meme?", font=("Helvetica", 16, "bold"), bg="#2e2e2e", fg="white")
    question_label.pack(pady=10)

    # Frame to hold the buttons
    button_frame = tk.Frame(root, bg="#2e2e2e")
    button_frame.pack(pady=10)

    # "Yes" button --> set is_meme to True and close the window.
    def on_yes():
        nonlocal is_meme
        is_meme = True
        root.destroy()

    # "No" button --> set is_meme to False and close the window.
    def on_no():
        nonlocal is_meme
        is_meme = False
        root.destroy()

    # "Yes" button color scheme/formatting
    yes_button = tk.Button(
        button_frame, text="Yes", command=on_yes, width=10,
        bg="#4CAF50", fg="white", activebackground="#45a049", relief="flat", font=("Helvetica", 12)
    )
    yes_button.pack(side="left", padx=10)

    # "No" button color scheme/formatting
    no_button = tk.Button(
        button_frame, text="No", command=on_no, width=10,
        bg="#f44336", fg="white", activebackground="#e53935", relief="flat", font=("Helvetica", 12)
    )
    no_button.pack(side="left", padx=10)

    # Make sure window is on topmost layer and start loop
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
#downloads_folder_path = "wroooooooong"


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


def run_observer():
    """
    Sets up and runs the watchdog observer to monitor the Downloads folder.
    This function runs in a separate thread.
    """
    try:
        path = downloads_folder_path
        event_handler = MyEventHandler()
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        print(f"DBG: Monitoring directory: {path}")
        while not stop_event.is_set()
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        observer.stop()
        icon.stop()
        sys.exit(0)
    except Exception as error:
        logging.error(f"ERROR in observer thread: {error}", exc_info=True)
        sys.exit(1)
    observer.join()

if __name__ == "__main__":
    try:
        # Do an initial sort
        sorter()

        # Start the watchdog observer in a separate daemon thread.
        observer_thread = threading.Thread(target=run_observer, daemon=True)
        observer_thread.start()

    except Exception as error:
        logging.error(f"ERROR in main setup: {error}", exc_info=True)
        sys.exit(1)

    # Run the tray icon on the main thread.
    # On macOS, this is required because the system tray implementation must run in the main thread.
    try:
        icon.run()
    except Exception as error:
        logging.error(f"ERROR in tray icon: {error}", exc_info=True)
        sys.exit(1)

    # Optionally, join the observer thread if needed (it should exit when the icon is closed).
    #observer_thread.join()

