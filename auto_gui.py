"""
GUI utilities for the desktop automation script.

- Generating a custom folder icon with an arrow.
- Displaying a pop-up prompt asking if a file is a meme.

"""

import math, tkinter as tk
from PIL import Image, ImageDraw

def create_icon(width=64, height=64):
    """
    The icon consists of:
      - A folder: drawn as a rectangle (folder body) and a polygon (folder tab).
      - A U-turn arrow: drawn as an arc with a small arrow head at its end.
    
    Args:
        width (int): The width of the icon image.
        height (int): The height of the icon image.
    
    Returns:
        PIL.Image: Generated icon image.
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


def meme_yes_no():
    """
    Pop-up window asking "Meme?" with Yes and No buttons.
    
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

     # Bring the window to the front and force focus.
    root.lift()                          # Raise the window to the top
    root.attributes('-topmost', True)    # Keep it above other windows
    root.focus_force()                   # Force the window to take focus
    root.grab_set()                      # Make the window modal so all events are directed to it
    
    root.mainloop()

    # Return the result of the user's choice
    return is_meme

