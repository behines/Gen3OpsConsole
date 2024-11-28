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
#   pytz     # Used by Sun.py, needed even though we are using QTimeZone in most places
#   tzlocal (installed along with pytz, I believe)
#   serial
#
# Thus, do
#
# python -m pip install pyside6 pyvisa pyvisa-py zeroconf psutil transitions astral pytz tzlocal serial
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
import sys
import os

from PySide6.QtWidgets import QApplication, QMainWindow, QCheckBox, QLabel, QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtCore    import Qt, QFile, QThread, QDateTime, QTimeZone, QTimer, QSignalBlocker

# Import configuration of the system
from Gen2OpsConsole_ui import Ui_MasterControl
from ConfigInfo        import *
from CollectorControl  import tCollectorControlWindow
from TempHumSensor     import tTempHumSensor
from Agilent           import tAgilent
from PeriodicLogger    import tPeriodicLogger
from PowerControl      import tPowerControl
from Sun               import tSun
from NipSequencer      import tNipSequencer
from LogFile           import tLogFile



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
    BoxMeasurementIndex     = CompleteChannelList.index(BOX_CHANNEL_FOR_MARQUEE_DISPLAY)
    SandTopMeasurementIndex = CompleteChannelList.index(SAND_TOP_CHANNEL)
    SandMidMeasurementIndex = CompleteChannelList.index(SAND_MID_CHANNEL)
    SandBotMeasurementIndex = CompleteChannelList.index(SAND_BOT_CHANNEL)

    # Determine which channels to use for reporting DNI and GHI to marquee
    DniChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'DNI channels') 
    GhiChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'GHI channels') 

    # Motor and USB hub power relay objects.  Set the checkboxes based on the current relay state
    self.MotorPower  = tPowerControl(self.Agilents[AGILENT_WITH_POWER_RELAYS], 'Motors',  MOTOR_POWER_CHANNELS,  tAgilent.RELAY_NORMALLY_CLOSED, self)
    self.UsbHubPower = tPowerControl(self.Agilents[AGILENT_WITH_POWER_RELAYS], 'USB Hub', USB_HUB_POWER_CHANNEL, tAgilent.RELAY_NORMALLY_CLOSED, self)
    try:
      self.MotorPowerCheckboxUpdate(self.MotorPower .GetPowerState())
    except TimeoutError:
      print('Motor power relay not responding')
    try:
      self.UsbPowerCheckboxUpdate  (self.UsbHubPower.GetPowerState())
    except TimeoutError:
      print('USB power relay not responding')


    ##### Prepare the log file
    # Write comma-separated headers  
    # Header line 1 will capture the version info and raw configuration of the Agilent units
    # Header line 2 is  field/channel names
    DailyFolder   = os.path.join(os.path.expanduser("~"), "Documents", DAILY_FOLDER)
    ArchiveFolder = os.path.join(os.path.expanduser("~"), ARCHIVE_FOLDER)
    Header1 = HEADER1 + ',' + ','.join([f'"{element}"' if element is not None else '""' for sublist in AGILENTS for element in sublist])
    Header2 = '"Date","Time",' + ','.join(str(num) for num in CompleteChannelList) + ',"Outside T","Outside H","Dome T","Dome H","Elec T","Elec H"'

    self.LogFile = tLogFile(DailyFolder, ArchiveFolder, Header1, Header2, SITE_TIMEZONE)

    # The parent of the object has to be None or it can't be moved to a thread.  The Logger needs to be passed the
    # collector list just so that it can pass it on to the Marquee object, which it creates.
    self.Collectors = self.CollectorControlWindow.CollectorList()
    self.PeriodicLogger = tPeriodicLogger(self.Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex, 
                                          SandTopMeasurementIndex, SandMidMeasurementIndex, SandBotMeasurementIndex,
                                          self.DomeTempSensor, self.OutsideTempSensor, self.ElectronicsTempSensor,
                                          self.Collectors, self.LogFile) #, parent=None)

    # Now that everything is going, we can start the collector monitoring threads.  At this point, the 
    # Collectors are still in this thread that created them, but they will now move to their own threads
    for Collector in self.Collectors:
      Collector.Start()

    # Start the NIP sequencer
    # The third Agilent is the one with the Actuator card in it for sequencing
    self.Sun          = tSun(SITE_LATITUDE, SITE_LONGITUDE, SITE_ELEVATION, SITE_TIMEZONE)
    self.NipSequencer = tNipSequencer(self.Agilents[AGILENT_WITH_POWER_RELAYS], NIP_POWER_CHANNELS, 
                                      NIP_ON_OFF_BUTTON_CHANNEL, PYRANOMETER_POWER_CHANNEL,
                                      self.Sun, self.PeriodicLogger, self)
      


    # Connect to signals
    self.ConnectToSignals()

    # Since the NIP sequencer won't run for a full minute, go ahead and run it once right now.
    # One might want to do this inside the NipSequencer constructor instead.  But that first 
    # run emits Sunrise and Sunset signals that we'd like to catch, so we want to wait until 
    # after we've connected to the signals
    self.NipSequencer.RunStateMachine()


    # Set up a 1-second timer to tick the on-screen clock
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
  # ConnectToSignals - Sign up for all the signals that MasterControl wants to receive
  #
  
  def ConnectToSignals(self):
    self.PeriodicLogger.DniUpdate        .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.DniLabel        , floatVal))
    self.PeriodicLogger.GhiUpdate        .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.GhiLabel        , floatVal))
    self.PeriodicLogger.BoxTempUpdate    .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.BoxTempLabel    , floatVal))
    self.PeriodicLogger.DomeTempUpdate   .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.DomeTempLabel   , floatVal))
    self.PeriodicLogger.ElecTempUpdate   .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.ElecTempLabel   , floatVal))
    self.PeriodicLogger.StanTempUpdate   .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.StanleyTempLabel, floatVal))
    self.PeriodicLogger.SandTopTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandTopTempLabel, floatVal))
    self.PeriodicLogger.SandMidTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandMidTempLabel, floatVal))
    self.PeriodicLogger.SandBotTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandBotTempLabel, floatVal))

    # These are for messages about the power relays from the relay class
    #self.MotorPower.PowerRelayStateUpdate.connect(self.MotorPowerCheckboxUpdate)
    #self.UsbPower  .PowerRelayStateUpdate.connect(self.UsbPowerCheckboxUpdate  )
    # These are for when the user actually checks the box
    self.ui.MotorPowerCheckBox.checkStateChanged.connect(self.UserCheckedMotorPower)
    self.ui.UsbPowerCheckBox  .checkStateChanged.connect(self.UserCheckedUsbPower  )

    self.NipSequencer.NipStateUpdate     .connect(self.UpdateNipStateMessage)
    self.NipSequencer.SunriseSunsetUpdate.connect(self.UpdateSunriseSunset)



  #######################################################
  # Update4DigitIntLabel - Updates values that are 4-digit integer label fields
  #
  
  def Update4DigitIntLabel(self, field: QLabel, value: float):
    field.setText(str(int(value)))


  #######################################################
  # MotorPowerCheckboxUpdate - Updates the checkbox based on signals from the class

  def MotorPowerCheckboxUpdate(self, value: bool):
    # Don't self-stimulate - turn off signals before updating the checkbox
    _ = QSignalBlocker(self.ui.MotorPowerCheckBox)     
    self.ui.MotorPowerCheckBox.setChecked(value)

  #######################################################
  # UsbPowerCheckboxUpdate - Updates values that are 4-digit integer label fields
 
  def UsbPowerCheckboxUpdate(self, value: bool):
    # Don't self-stimulate - turn off signals before updating the checkbox
    _ = QSignalBlocker(self.ui.UsbPowerCheckBox) 
    self.ui.UsbPowerCheckBox.setChecked(value)


  #######################################################
  # UserCheckedMotorPower - Updates the checkbox based on signals from the class

  def UserCheckedMotorPower(self, checkstate: Qt.CheckState):
    bValue = (checkstate == Qt.Checked)
    self.MotorPower.SetPowerState(bValue)
    print('Turning Motor power', 'ON' if bValue else 'OFF')
    try:
      bSuccess = (self.MotorPower.GetPowerState() == bValue)
    except TimeoutError:
      bSuccess = False
    if not bSuccess:
      QMessageBox.critical(self, "Error", "Motor Power Relay did not respond", QMessageBox.Ok)


  #######################################################
  # UserCheckedUsbPower - Updates the checkbox based on signals from the class

  def UserCheckedUsbPower(self, checkstate: Qt.CheckState):
    bValue = (checkstate == Qt.Checked)
    self.UsbHubPower.SetPowerState(bValue)
    print('Turning USB power', 'ON' if bValue else 'OFF')
    try:
      bSuccess = (self.UsbHubPower.GetPowerState() == bValue)
    except TimeoutError:
      bSuccess = False
    if not bSuccess:
      QMessageBox.critical(self, "Error", "USB Power Relay did not respond", QMessageBox.Ok)
   

  #######################################################
  # UpdateNipStateMessage

  def UpdateNipStateMessage(self, NipStateString: str):
    NipStateString = NipStateString[0].upper() + NipStateString[1:]
    self.ui.NipStateLabel.setText(NipStateString)

  #######################################################
  # UpdateNipStateMessage

  def UpdateSunriseSunset(self, Sunrise: QDateTime, Sunset: QDateTime):
    SunriseString = Sunrise.toString("HH:mm:ss")
    SunsetString  = Sunset .toString("HH:mm:ss")
    self.ui.SunriseLabel.setText(SunriseString)
    self.ui.SunsetLabel .setText(SunsetString )


  #######################################################
  # closeEvent - Fires when MainWin is closed by the user - our signal to tidy up and exit
  #
  # We do this rather than connect to app.aboutToQuit, because there is a chicken-and-egg problem.
  # The app will not try to quit until the MainWin event loop exits, which won't happen until 
  # the various threads stop.  So we have to trap earlier in the process to initiate shutdown.
  #

  def closeEvent(self, event):
    # print("MainWin is closing")
    self.CleanUp()  # Call your cleanup method here
    super().closeEvent(event)


  #######################################################
  # CleanUp - Destroys objects and/or sends signals to objects to destroy themselves
  #
  # We wait to do this until after the window is constructed, so that information about 
  # initialization can be reported to the log and to relevant widgets

  def CleanUp(self):
    # Stop the 1-second tick
    self.OneSecondTimer.stop()

    # Shut down the NIP.  
    # We can call directly because the NIP sequencer is in the master GUI thread
    self.NipSequencer.DoShutdown() 

    # Shut down all the collectors
    for Collector in self.Collectors:
      Collector.RequestExit()

    # Tell the periodic logger thread to shut down, and wait for confirmation
    self.PeriodicLogger.RequestExit()

    # Shut down the collector window
    self.CollectorControlWindow.ForceClose()

    # Allows for any dummy threads to finish cleanup
    #app.processEvents()



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
  global app
  # Get some basic stuff out of the way before even trying to create a window
  ValidateAGILENTSEntries()

  # Create the application and main window
  app = QApplication(sys.argv)

  MainWin = MasterControl()
  MainWin.show()
  getattr(MainWin, "raise")()
  MainWin.activateWindow()

  #app.aboutToQuit.connect(lambda: print("aboutToQuit signal emitted"))
  #app.aboutToQuit.connect(MainWin.CleanUp)
  
  MainWin.StartApplication()

  # Run the event loop, and propagate any exit error code back to the OS.
  exitCode = app.exec()
  sys.exit(exitCode)
