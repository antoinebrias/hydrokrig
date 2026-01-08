# HydroKrig - QGIS Plugin for Hydrological Interpolation

**HydroKrig** is a custom QGIS plugin developed in Python to streamline the process of spatial interpolation for meteorological data. It is specifically designed to handle datasets where multiple observations (dates) exist for the same set of coordinates, such as daily rainfall records.

---

## 🌟 Key Features

* **Smart Time-Series Filtering**: Automatically detects unique dates in your attribute table to avoid "singular matrix" errors during kriging.
* **PyKrige Integration**: Leverages the power of the `PyKrige` library for professional-grade Ordinary Kriging.
* **Automated Raster Generation**: Uses GDAL to create georeferenced GeoTIFFs directly on your desktop.
* **Clean Visualization**: Optimized for the Drôme watershed with automated masking and duplicate label removal for a professional map output.

---

## 🛠️ The Development Workflow

This plugin was built using a modern QGIS development stack:
* **Plugin Builder 3**: To initialize the project structure.
* **Plugin Reloader**: For real-time code updates without restarting QGIS.
* **Qt Designer**: For building the user interface (`.ui`).


---

## 🚀 Installation & Setup

### 1. Requirements
You must have the following Python libraries installed in your QGIS environment:
```bash
pip install pykrige numpy
```

## 2. Manual Installation

1.  **Download** this repository as a `.zip` file from GitHub.
2.  **Extract** the folder into your QGIS plugins directory:
    * **Windows**: `C:\Users\YourUser\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
    * **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
    * **macOS**: `/Users/YourUser/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`
3.  **Restart QGIS**, go to **Plugins > Manage and Install Plugins**, and check the box next to **HydroKrig**.

---

## 📖 How to Use

1.  **Launch**: Click the **HydroKrig** icon in your QGIS toolbar.
2.  **Select Layer**: Choose your point layer containing the station data.
3.  **Choose Field**: Select the numerical field to interpolate (e.g., `RR` for rainfall or `ALTI` for elevation).
4.  **Pick a Date**: Select the specific date you wish to map from the dynamic dropdown.
5.  **Run**: The plugin calculates the Kriging surface, saves it as a `.tif` file on your desktop, and adds it to your project.
6.  **Masking**: For a clean result, I used a mask layer of the **Drôme watershed** to clip the final output to the study area.


---

## 🎓 Final Thoughts

Building **HydroKrig** was a great learning experience in combining different Python ecosystems within QGIS. It serves as a personal proof of concept for automating geostatistical workflows.

It is a work in progress, and I am continuously looking for ways to refine the logic and improve the user experience.

---

## 📂 Repository Structure

* `hydro_krig.py`: Main logic and PyKrige integration. 
* `hydro_krig_dialog.py`: UI event handling and signals.
* `hydro_krig_dialog_base.ui`: Layout designed in Qt Designer.
* `metadata.txt`: Plugin information for QGIS.
