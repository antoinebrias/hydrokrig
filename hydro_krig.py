# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HydroKrig - A QGIS plugin
 Rainfall interpolation tool using Ordinary Kriging.
 ***************************************************************************/
"""
import os
import os.path
import numpy as np
from pykrige.ok import OrdinaryKriging
from osgeo import gdal, osr

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import Qgis, QgsProject, QgsMapLayerProxyModel

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .hydro_krig_dialog import HydroKrigDialog

class HydroKrig:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize locale/translations
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HydroKrig_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&HydroKrig')

        # This will be initialized in run()
        self.dlg = None
        self.first_start = True

    def tr(self, message):
        """Get the translation for a string."""
        return QCoreApplication.translate('HydroKrig', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, 
                   add_to_menu=True, add_to_toolbar=True, status_tip=None, 
                   whats_this=None, parent=None):
        """Add a toolbar icon and menu item."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip: action.setStatusTip(status_tip)
        if whats_this: action.setWhatsThis(whats_this)
        if add_to_toolbar: self.iface.addToolBarIcon(action)
        if add_to_menu: self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons."""
        icon_path = ':/plugins/hydro_krig/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'HydroKrig'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&HydroKrig'), action)
            self.iface.removeToolBarIcon(action)

    def run_kriging_logic(self):
        """Core interpolation logic using PyKrige with date filtering."""
        # 1. Fetch layer, field, and date from UI
        layer = self.dlg.comboBoxLayer.currentLayer()
        field = self.dlg.comboBoxField.currentField()
        selected_date = self.dlg.comboBoxDate.currentText()

        if not layer or field == "" or selected_date == "":
            self.iface.messageBar().pushMessage("Error", "Please select a valid layer, field, and date", level=Qgis.Critical)
            return

        # 2. Extract X, Y (coordinates) and Z (values) filtered by date
        x, y, z = [], [], []
        for feature in layer.getFeatures():
            # Check if the feature matches the selected date (converted to string for safety)
            if str(feature['AAAAMMJJ']) == selected_date:
                if feature.geometry():
                    pt = feature.geometry().asPoint()
                    val = feature[field]
                    
                    # Only add if the value is not NULL
                    if val is not None:
                        x.append(pt.x())
                        y.append(pt.y())
                        z.append(float(val))

        # Check if we have enough points for the specific date
        if len(x) < 3:
            self.iface.messageBar().pushMessage("Error", f"Need at least 3 points for {selected_date}. Found: {len(x)}", level=Qgis.Warning)
            return

        # Convert to numpy arrays
        x, y, z = np.array(x), np.array(y), np.array(z)

        # 3. Create the interpolation grid (100x100 resolution)
        grid_x = np.linspace(x.min(), x.max(), num=100)
        grid_y = np.linspace(y.min(), y.max(), num=100)

        # 4. Execute Ordinary Kriging
        try:
            # Using 'linear' variogram model
            OK = OrdinaryKriging(x, y, z, variogram_model='linear', verbose=False)
            z_interp, sigmasq = OK.execute('grid', grid_x, grid_y)
            
            # Generate a dynamic filename using the selected date to avoid "Permission Denied" errors
            selected_date = self.dlg.comboBoxDate.currentText()
            output_filename = f"rainfall_{selected_date}.tif"

            # Export the resulting matrix to a GeoTIFF using the layer's CRS
            self.create_raster(z_interp, grid_x, grid_y, layer.crs(), output_filename)
            self.iface.messageBar().pushMessage("Success", f"Rainfall map for {selected_date} generated on Desktop", level=Qgis.Info)
            
        except Exception as e:
            self.iface.messageBar().pushMessage("Kriging Error", str(e), level=Qgis.Critical)


    def create_raster(self, data, x_grid, y_grid, crs, filename):
        """Converts the Kriging result into a physical GeoTIFF file."""
        import os
        from osgeo import gdal, osr
        import numpy as np

        # Define the full path to the Desktop
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        output_path = os.path.join(desktop, filename)
        
        driver = gdal.GetDriverByName('GTiff')
        
        # IMPORTANT: If the file already exists, we must try to delete it.
        # If it's open in QGIS, this will fail and we need to handle it.
        if os.path.exists(output_path):
            try:
                # Close the file if it's already in the driver's memory
                driver.Delete(output_path)
            except Exception:
                # If deletion fails (Permission Denied), we append a small timestamp
                import time
                unique_suffix = time.strftime("%H%M%S")
                filename = filename.replace(".tif", f"_{unique_suffix}.tif")
                output_path = os.path.join(desktop, filename)

        rows, cols = data.shape
        dataset = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)

        # Set Geotransform [LeftX, PixelWidth, 0, TopY, 0, PixelHeight]
        px_w = (x_grid.max() - x_grid.min()) / (cols - 1)
        px_h = (y_grid.max() - y_grid.min()) / (rows - 1)
        dataset.SetGeoTransform([x_grid.min(), px_w, 0, y_grid.max(), 0, -px_h])

        # Set Coordinate System
        srs = osr.SpatialReference()
        srs.ImportFromWkt(crs.toWkt())
        dataset.SetProjection(srs.ExportToWkt())

        # Write data (Flipped for GDAL standard)
        band = dataset.GetRasterBand(1)
        band.WriteArray(np.flipud(data))
        
        # Set NoData value to avoid black borders
        band.SetNoDataValue(-9999)
        
        band.FlushCache()
        dataset = None # Properly close the file to release the lock

        # Load the layer into QGIS with a specific name based on the filename
        layer_name = filename.replace(".tif", "")
        self.iface.addRasterLayer(output_path, layer_name)

    def run(self):
        """Main method called when the plugin icon is clicked."""
        if self.first_start:
            self.first_start = False
            self.dlg = HydroKrigDialog()

        # UI Setup: Only show point layers
        from qgis.core import QgsMapLayerProxyModel
        self.dlg.comboBoxLayer.setFilters(QgsMapLayerProxyModel.PointLayer)

        # Link field selector to the initial layer
        self.dlg.comboBoxField.setLayer(self.dlg.comboBoxLayer.currentLayer())
        
        # Initial update of the date list
        self.update_dates()

        # Connect signals
        try:
            # Disconnect previous signals to avoid multiple triggers
            self.dlg.comboBoxLayer.layerChanged.disconnect()
        except:
            pass
            
        # Connect layer change to update both fields and available dates
        self.dlg.comboBoxLayer.layerChanged.connect(self.dlg.comboBoxField.setLayer)
        self.dlg.comboBoxLayer.layerChanged.connect(self.update_dates)

        self.dlg.show()
        result = self.dlg.exec_()
        
        if result:
            self.run_kriging_logic()

    def update_dates(self):
        """Populate comboBoxDate with unique values from the 'AAAAMMJJ' field."""
        layer = self.dlg.comboBoxLayer.currentLayer()
        self.dlg.comboBoxDate.clear()
        
        if layer:
            # Find the index of the date column
            idx = layer.fields().indexOf('AAAAMMJJ')
            if idx != -1:
                # Retrieve unique date values and sort them (newest first)
                dates = layer.uniqueValues(idx)
                str_dates = sorted([str(d) for d in dates if d], reverse=True)
                self.dlg.comboBoxDate.addItems(str_dates)
            else:
                # Inform the user if the specific date field is missing
                self.dlg.comboBoxDate.addItem("Field 'AAAAMMJJ' missing")