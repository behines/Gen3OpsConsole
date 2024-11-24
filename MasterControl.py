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
# ************* COMPILING THE UI ***************
# It is nececcsary to convert the .ui files from Qt Creator into _ui.py files that the app will
# load at runtime.  To do this:
#   pyside6-uic Gen2OpsConsole.ui -o Gen2OpsConsole_ui.py
#   pyside6-uic  CollectorPane.ui -o  CollectorPane_ui.py  
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
from PySide6.QtCore    import QFile, QThread, QDateTime, QTimeZone, QTimer

# Globals, used for communicating between threads
# import globals 

# Import configuration of the system
from Gen2OpsConsole_ui import Ui_MasterControl
from ConfigInfo        import *
from CollectorControl  import tCollectorControlWindow
from TempHumSensor     import tTempHumSensor
from Agilent           import tAgilent
from PeriodicLogger    import tPeriodicLogger
from Utilities         import WaitForSignal





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
    #loader = QUiLoader()
    #ui_file = QFile("Gen2OpsConsole.ui")
    
    #if not ui_file.exists():
    #  QMessageBox.critical(self, "Error", "UI file not found: Gen2OpsConsole.ui")
    #  sys.exit(1)
    
    #ui_file.open(QFile.ReadOnly)
    #self.ui = loader.load(ui_file, self)   # Have to assign to self so that ui and all its children persist after the constructor exits
    #ui_file.close()

    #self.ui.centralWidget().setParent(self)

    # Auto-bind widgets as attributes of self.  Not needed if we compile the UI with pyside6-uic,
    # but QUiLoader does not do this automatically.
    #for widget in self.ui.findChildren(QWidget):
    #  setattr(self, widget.objectName(), widget)

    # Integrate the loaded UI
    #self.setCentralWidget(self.ui.centralWidget())  # Use the central widget from the loaded UI
    #self.setCentralWidget(self.ui)  # Use the central widget from the loaded UI

    # Instantiate the UI class and set it up
    self.ui = Ui_MasterControl()
    self.ui.setupUi(self)
    
    self.setWindowTitle('Windsor Master Control Console')




    print('TimeLabel = ', self.ui.SystemTimeLabel)  # Should not be None


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

    self.DomeTempSensor        = tTempHumSensor(DOME_TEMP_SENSOR_PORT,        parent=None)
    self.OutsideTempSensor     = tTempHumSensor(OUTSIDE_TEMP_SENSOR_PORT,     parent=None)
    self.ElectronicsTempSensor = tTempHumSensor(ELECTRONICS_TEMP_SENSOR_PORT, parent=None)

    # Get the indices of channels that we will want to pick out of the data for reporting to 
    # the marquee display
    try:
      BoxMeasurementIndex = CompleteChannelList.index(BOX_CHANNEL_FOR_MARQUEE_DISPLAY)
    except ValueError:
      BoxMeasurementIndex = None
    # Determine which channels to use for reporting DNI and GHI to marquee
    DniChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'DNI channels') 
    GhiChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'GHI channels') 


    # The parent of the object has to be None or it can't be moved to a thread.  The Logger needs to be passed the
    # collector list just so that it can pass it on to the Marquee object, which it creates.
    self.Collectors = self.CollectorControlWindow.CollectorList()
    self.PeriodicLogger = tPeriodicLogger(self.Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex, 
                                          self.DomeTempSensor, self.OutsideTempSensor, self.ElectronicsTempSensor,
                                          self.Collectors) #, parent=None)
    
    # Now that everything is going, we can start the collector monitoring threads.  At this point, the 
    # Collectors are still in this thread that created them, but they will now move to their own threads
    for Collector in self.Collectors:
      Collector.Start()

    # Set up a 1-second timer
    self.OneSecondTimer = QTimer(self)
    self.OneSecondTimer.setSingleShot(False)
    self.OneSecondTimer.timeout.connect(self.OneSecondTick)

    # Get the current time in the specified timezone
    current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
    # Pause a fraction of a second to get perfect sync
    milliseconds_until_next_interval = current_time.time().msecsSinceStartOfDay() % 1000
    QThread.msleep(milliseconds_until_next_interval)

    self.OneSecondTimer.start(1000)


  #######################################################
  # CleanUp - Destroys objects and/or sends signals to objects to destroy themselves
  #
  # We wait to do this until after the window is constructed, so that information about 
  # initialization can be reported to the log and to relevant widgets

  def CleanUp(self):
    # Tell the periodic logger thread to shut down, and wait for confirmation
    WaitForSignal(SignalToWaitFor = self.PeriodicLogger.TheThread.finished, SignalToEmit = self.PeriodicLogger.RequestExit)
    # Now that the thread has exited, schedule it for deletion
    self.PeriodicLogger.deleteLater()
    self.OneSecondTimer.stop()


  #######################################################
  # OneSecondTick handler 
  #
  # contains all the collectors
  #

  def OneSecondTick(self):
   current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
   TimeString = current_time.toString('HH:mm:ss')
   self.ui.SystemTimeLabel.setText(TimeString)
  


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

  app.aboutToQuit.connect(MainWin.CleanUp)


  # Run the event loop, and propagate any exit error code back to the OS.
  sys.exit(app.exec())
