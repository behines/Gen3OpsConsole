#######################################################
# Script that runs on the Stanley mini pc in the Jobsite box
# 
# Application requires that you "pip install":
#   pyside6
#   pyvisa
#   pyvisa-py
#   zeroconf (needed for visa device discovery)
#   psutil   (needed for visa interface discovery)
#   transitions
#   astral   # used by Sun.py, pulls in tzdata
#
# I don't think these are needed anymore but were in the original list that I copied in
#   pytz   # Now using QTimeZone
#   tzlocal (installed along with pytz, I believe)
#
# HARDWARE ASSUMPTIONS
# Requires:
#   ESP32 for the marquee display
#   Dome and Outside Temp/Humidity sensors
#
#

#################################################
#
# Modules used
#

# module used to get the current date and time
from datetime import datetime, timedelta
from collections import namedtuple

# module used to control delays
import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore    import QFile, Qt, QElapsedTimer

# Globals, used for communicating between threads
# import globals 

# Import configuration of the system
from ConfigInfo       import *
from CollectorControl import tCollectorControlWindow
from Marquee          import tMarquee
from TempHumSensor    import tTempHumSensor
from Agilent          import tAgilent
from PeriodicLogger   import tPeriodicLogger






##########################################################################################
##########################################################################################
##########################################################################################
#
# MasterControl - class for the main "master control" window of the app
#
# Also includes all top-level sequencing and logic
#

class MasterControl(QMainWindow):

  #######################################################
  # Constructor - Builds the main window and creates the collector control window that contains all the collectors
  #

  def __init__(self, parent=None):
    super().__init__(parent)



    # Load MasterControl UI dynamically
    loader = QUiLoader()
    ui_file = QFile("Gen2OpsConsole.ui")
    
    if not ui_file.exists():
      QMessageBox.critical(self, "Error", "UI file not found: Gen2OpsConsole.ui")
      sys.exit(1)
    
    ui_file.open(QFile.ReadOnly)
    ui = loader.load(ui_file, self)
    ui_file.close()
    
    # Auto-bind widgets as attributes of self.  Not needed if we compile the UI with pyside6-uic,
    # but QUiLoader does not do this automatically.
    for widget in ui.findChildren(QWidget):
      setattr(self, widget.objectName(), widget)

    # Integrate the loaded UI
    self.setCentralWidget(ui.centralWidget())  # Use the central widget from the loaded UI
    self.setWindowTitle('Windsor Master Control Console')


    # Construct the Agilent objects.  The '*' splats the descriptor onto the constructor arguments
    #self.Agilents   = [ tAgilent(*descriptor, parent=self) for descriptor in AGILENTS ]


    # Marquee display and standalone sensors
    #Marquee       = tMarquee      (MARQUEE_COM_PORT)
    #OutsideSensor = tTempHumSensor(OUTSIDE_SENSOR_PORT)
    #DomeSensor    = tTempHumSensor(DOME_SENSOR_PORT)
    #ElecSensor    = tTempHumSensor(ELEC_SENSOR_PORT)


    # Create Collector Control Window
    self.CollectorControlWindow = tCollectorControlWindow()
    self.CollectorControlWindow.show()
    getattr(self.CollectorControlWindow, "raise")()
    self.CollectorControlWindow.activateWindow()


  #######################################################
  # StartApplication - Constructs and initializes objects
  #
  # We wait to do this until after the window is constructed, so that information about 
  # initialization can be reported to the log and to relevant widgets

  def StartApplication(self):

    # Construct the Agilent objects.  The '*' splats the descriptor onto the constructor arguments
    # This includes opening the devices
    # Create the objects with no parant for now, because later the PeriodicLogger will take ownership.
    self.Agilents   = [ tAgilent(*descriptor, parent=None) for descriptor in AGILENTS ]

    # Get the complete channel list, adding the mainframe number as a prefix 1000, 2000, 3000, to each channel
    CompleteChannelList = [channel + 1000*(index+1) for index, agilent in enumerate(self.Agilents) for channel in agilent.ChannelList]

    # Get the indices of channels that we will want to pick out of the data for reporting to 
    # the marquee display
    try:
      BoxMeasurementIndex = CompleteChannelList.index(BOX_CHANNEL_FOR_MARQUEE_DISPLAY)
    except ValueError:
      BoxMeasurementIndex = None
    # Determine which channels to use for reporting DNI and GHI to marquee
    DniChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'DNI channels') 
    GhiChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'GHI channels') 

    self.Collectors = None

    self.PeriodicLogger = tPeriodicLogger(self.Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex, 
                                          DOME_TEMP_SENSOR_PORT, OUTSIDE_TEMP_SENSOR_PORT, ELECTRONICS_TEMP_SENSOR_PORT,
                                          self.Collectors, parent=self)


  #######################################################
  # closeEvent handler - causes Collector window to close along with main window
  #
  # contains all the collectors
  #

  def closeEvent(self, event):
    # Ensure the CollectorControlWindow is closed when the main window is closed
    if self.CollectorControlWindow:
      self.CollectorControlWindow.ForceClose()
    event.accept()  # Proceed with closing MainWin


##########################################################################################
##########################################################################################
##########################################################################################
# Standalone functions
#
# These are not in any class

#################################################
# ValidateAGILENTSEntries
#
# Makes sure the AGILENTA array is properly structure.

def ValidateAGILENTSEntries():
  # Verify all AGILENT entries have the correct number of fields
  for index, agilent in enumerate(AGILENTS):
    if len(agilent) != len(AGILENT_DESCRIPTOR_FIELDS):
      print(f"AGILENT #{index} does not match the expected number of fields, exiting.")
      sys.exit()


#################################################
# FindFirstNonNoneValueForField
#
# For items like the GHI and DNI sensors, most of the Agilents will list the
# sensor ID for the sensor as "None", but the Aglient that actually has these 
# sensors will list a channel value.
#
# This routine helps to find the Agilent that has the specified sensor by finding
# the lowest-numbered device that does not list the channel as "None".  It then
# returns the index of that channel in the complete channel list.  
# 
# This index can then be used to pick it out of a set of channel readings.
#
# INPUTS:
#   CompleteChannelList - the list of all agilent channels, a list of integers like 1101, 1102,... 2101, ... 2320
#   FieldName           - the name of the field you're looking for, from AGILENT_DESCRIPTOR_FIELDS
# 
# RETURNS:
#   The index of the non-None entry in the complete channel list, or None if
#   there are no non-None entries for the field
# 

def FindFirstNonNoneValueForField(CompleteChannelList, FieldName):
  # Determine which channel to use for reporting DNI to marquee
  ChannelIndex = AGILENT_DESCRIPTOR_FIELDS.index(FieldName)         # index of the DNI channel number in the AGILENT list
  Channels = [agilent[ChannelIndex] for agilent in AGILENTS]  # Extracting all the DNI channel entries for all AGILENT's into a list
  ChannelIndex = None          
  DNI             = 0                                          
  # Loop to find the first non-None, and add 1000*(AGILENT #) to get the overall channel number
  for index, ChannelNum in enumerate(Channels):
    if ChannelNum is not None:
      OverallChannelNum = ChannelNum + (1000 * (index+1))                 # Overall channel number
      ChannelIndex = CompleteChannelList.index(OverallChannelNum)  # Its index in the returned list
      break
  return ChannelIndex



if __name__ == "__main__":

  # Get some basic stuff out of the way before even trying to create a window
  ValidateAGILENTSEntries()

  # Create the application and main window
  app = QApplication(sys.argv)

  MainWin = MasterControl()
  MainWin.show()
  getattr(MainWin, "raise")()
  MainWin.activateWindow()
  
  MainWin.StartApplication()


  # Run the event loop, and propagate any exit error code back to the OS.
  sys.exit(app.exec())
