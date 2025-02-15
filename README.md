# 📂 AutoSort

## 🔍 Overview
AutoSort is a desktop automation tool that monitors a selected folder (default: **Downloads**) and automatically moves files to categorized destination folders based on their file extensions. It runs in the **system tray**, allowing users to control sorting operations easily.

---

## 🎥 Demo
![AutoSort in Action](path/to/demo.gif)  
*(Replace with an actual GIF or video link showcasing the script in action.)*

---

## 🛠 File Sorting Flow Diagram
![File Sorting Flow](path/to/flow_diagram.png)  
*(Insert a visual representation of how files are moved based on extensions.)*

---

## 🚀 Performance Monitoring
*(Add benchmarks, performance tests, or insights into CPU/memory usage if relevant.)*
(C:\Users\Marcu\workspace\github.com\Desktop_Automation\plotting\image.png)

---

## ⚡ Installation

### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/yourusername/AutoSort.git
cd AutoSort
```

### **2️⃣ Install Dependencies**
```sh
pip install -r requirements.txt
```

### **3️⃣ Run the Script**
```sh
python main.py
```

---

## 🔧 Convert to an Executable (.exe)

To create a standalone **.exe** file using PyInstaller:

```sh
pyinstaller --onefile --windowed --icon=icon.ico main.py
```
- `--onefile`: Bundles everything into a single executable.
- `--windowed`: Hides the console window.
- `--icon=icon.ico`: Adds a custom icon (replace with your icon file).

The **executable** will be found in the `dist/` folder.

---

## 🖥️ Auto-Start on Windows (Startup Folder)
1. **Generate the .exe file** (see above).
2. **Open Run Dialog** (`Win + R`), type:
   ```
   shell:startup
   ```
   and press **Enter**.
3. **Copy the .exe** from the `dist/` folder and paste it into the **Startup** folder.

Your script will now start automatically when Windows boots.

---

## 🌟 Inspiration
This project was inspired by a **YouTube video** on automating file sorting with Python.  
*(Replace with the actual video link or reference.)*

---

## 📜 License
*(Specify your project's license, e.g., MIT, GPL, etc.)*

---

## ✨ Contributions
Feel free to **fork** this repository and submit **pull requests** if you’d like to improve the project!

