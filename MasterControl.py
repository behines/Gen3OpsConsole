#######################################################
# Script that runs on the Stanley mini pc in the Jobsite box
#
# USAGE:
#   python MasterControl.py --site <sitename>
#   where sitename is either windsor or sandia.
#   
#   Note that the app may be installed in a venv, in which case you should follow
#   the instructions in the USING A VENV section below to activate the venv before
#   running the app.
# 
# Application requires that you "pip install":
#   pyside6
#   pyvisa
#   pyvisa-py (*) Not needed if NI-VISA is installed
#   zeroconf (needed for visa device discovery)
#   psutil   (needed for visa interface discovery)
#   transitions
#   astral   # used by Sun.py, pulls in tzdata
#   pytz     # Used by Sun.py, needed even though we are using QTimeZone in most places
#   tzlocal (installed along with pytz, I believe)
#   pyserial
#   debugpy
#   requests
#
# Thus, do
#   python -m pip install --upgrade pip
#   python -m pip install pyside6 pyvisa pyvisa-py zeroconf psutil transitions astral pytz tzlocal pyserial debugpy requests
#
# PRO TIP!!  IMPORTANT
#   Be sure to install 'pyserial' not 'serial'.  'serial' is for serializing JSON objects, 'pyserial' is
#   for doing serial port I/O.
#
# DO NOT INSTALL:
#   NI-VISA from National Instruments: https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html?srsltid=AfmBOopFMv3hfOdLMdHyYRWHIyUSGZ2AWTgoTWsv2cLzflK4pR8Z13Q_#548367
#   It supposedly works better than pyvisa-py, allows parallel access to instruments. 
#   But it is a mess.
#
# HARDWARE ASSUMPTIONS
# Requires:
#   ESP32 for the marquee display
#   Dome and Outside Temp/Humidity sensors
#
# ************* COMPILING THE UI ***************
# It is nececcsary to convert the .ui files from Qt Creator into _ui.py files that the app will
# load at runtime.  To do this:
#   pyside6-uic Gen3OpsConsole.ui -o Gen3OpsConsole_ui.py
#   pyside6-uic  CollectorPane.ui -o  CollectorPane_ui.py  
#

#######################################################
# USING A VENV
#
# It is recommended to install the Python packages into a project-local venv
# rather than into the system Python installation.  This is not mainly because
# this machine runs other Python apps, but because it makes the app setup more
# repeatable and less vulnerable to future package changes.
#
# To create the venv:
#   py -m venv .venv
#
# To activate the venv in PowerShell:
#   .\.venv\Scripts\Activate.ps1
#
# Then install the required packages into the venv:
#   python -m pip install --upgrade pip
#   python -m pip install pyside6 pyvisa pyvisa-py zeroconf psutil transitions astral pytz tzlocal pyserial debugpy requests
#
# Once the venv is activated, "python" and "pip" refer to the copies inside
# .venv, not the system-wide Python installation.
#
# To run the program with the venv activated:
#   python YourApp.py
#
# To run the program without activating the venv first:
#   .\.venv\Scripts\python.exe YourApp.py
#
# For shortcuts, startup scripts, or scheduled tasks, prefer the explicit form:
#   .\.venv\Scripts\python.exe YourApp.py
#
# pyside6-uic is also installed inside the venv when pyside6 is installed.
# With the venv activated, this should work:
#   pyside6-uic Gen3OpsConsole.ui -o Gen3OpsConsole_ui.py
#   pyside6-uic CollectorPane.ui    -o CollectorPane_ui.py
#
# Without activating the venv first, use:
#   .\.venv\Scripts\pyside6-uic.exe Gen3OpsConsole.ui -o Gen3OpsConsole_ui.py
#   .\.venv\Scripts\pyside6-uic.exe CollectorPane.ui    -o CollectorPane_ui.py
#
# If the Python environment ever gets corrupted or confused, the .venv
# directory can be deleted and recreated using the commands above.
#

#######################################################
# SAVING AND RECREATING THE PYTHON ENVIRONMENT
#
# The .venv directory should NOT be committed to GitHub.  It is a local,
# machine-specific directory containing the installed Python interpreter,
# packages, scripts, caches, and generated files.
#
# Instead, after the app is working correctly, save the installed package
# versions to requirements.txt:
#   python -m pip freeze > requirements.txt
#
# Commit requirements.txt to GitHub.
#
# Later, on a new machine, recreate the venv and reinstall the same packages:
#   py -m venv .venv
#   .\.venv\Scripts\Activate.ps1
#   python -m pip install --upgrade pip
#   python -m pip install -r requirements.txt
#
# This does not save the venv itself.  It saves the list of installed packages
# and versions so pip can rebuild an equivalent environment.
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
import re

from PySide6.QtWidgets  import QApplication, QMainWindow, QLabel, QButtonGroup, QMessageBox
from PySide6.QtCore     import Qt, QThread, QDateTime, QTimeZone, QTimer, QSignalBlocker

# Import configuration of the system
from Gen3OpsConsole_ui  import Ui_MasterControl
from ConfigInfo         import *
from CollectorControl   import tCollectorControlWindow
from CollectorLogFiles  import tCollectorLogFiles
from TempHumSensor      import tTempHumSensor
from Agilent            import tAgilent
from PeriodicLogger     import tPeriodicLogger
from PowerControl       import tPowerControl
from Sun                import tSun
from NipSequencer       import tNipSequencer, tSunClockSequencer
from CollectorSequencer import tCollectorSequencer
from LogFile            import tLogFile



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
    #ui_file = QFile("Gen3OpsConsole.ui")
    
    #if not ui_file.exists():
    #  QMessageBox.critical(self, "Error", "UI file not found: Gen3OpsConsole.ui")
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
    
    self.setWindowTitle(PROJECT_CONFIG.WindowTitle)
    self.ui.label.setText(PROJECT_CONFIG.DisplayName + ' Master Control Panel')
    self.ui.menuWindsorOps.setTitle(PROJECT_CONFIG.MenuTitle)

    # Create Collector Control Window
    self.CollectorControlWindow = tCollectorControlWindow()  #self)
    self.CollectorControlWindow.show()

    # Adjust the positions of the windows
    screen          = QApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()

    # Calculate the desired mainwindow y coordinate as 10% of the screen height
    y_coord = int(screen_geometry.height() * 0.1)
    # Keep the current x position and set the new y position
    self.move(self.x(), y_coord)

    # Get the main window and secondary window sizes
    main_geometry      = self                       .geometry()
    secondary_geometry = self.CollectorControlWindow.geometry()

    # Compute aggregate width including a 50-pixel gap
    total_width = main_geometry.width() + 50 + secondary_geometry.width()

    # Compute the horizontal starting point to center both windows
    center_x = (screen_geometry.width() - total_width) // 2

    # Compute the vertical alignment (align vertical centerlines)
    main_center_y     = main_geometry.y() + (main_geometry.height()      // 2)
    secondary_start_y = main_center_y     - (secondary_geometry.height() // 2)
    if secondary_start_y < 30:
      secondary_start_y = 30

    # Set the new positions
    self.move(center_x, 30) #main_geometry.y())
    self.CollectorControlWindow.move(center_x + main_geometry.width() + 100, 30)
                                     #secondary_start_y)

    self.CollectorControlWindow.raise_()
    self.CollectorControlWindow.activateWindow()


  #######################################################
  # StartApplication - Constructs and initializes objects
  #
  # We wait to do this until after the window is constructed, so that information about 
  # initialization can be reported to the log and to relevant widgets

  def StartApplication(self):

    # Verify picotool is available - needed for the Reboot fallback when the embedded reboot
    # command doesn't respond.  Better to fail fast at startup than to discover it's missing
    # at the moment we need to reboot a wedged board.
    if not os.path.isfile(PROJECT_CONFIG.PicotoolPath):
      msg = (f"picotool not found at:\n  {PROJECT_CONFIG.PicotoolPath}\n\n"
             f"Install picotool or update PICOTOOL_PATH in ProjectConfig.py.")
      print(msg, flush=True)
      QMessageBox.critical(self, "picotool not found", msg)
      raise FileNotFoundError(PROJECT_CONFIG.PicotoolPath)

    # Construct the Agilent objects.  The '*' splats the descriptor onto the constructor arguments
    # This includes opening the devices
    # Create the objects with no parant for now, because later the PeriodicLogger will take ownership.
    self.Agilents   = [ tAgilent(*descriptor, parent=None) for descriptor in PROJECT_CONFIG.Agilents ]

    # Get the complete channel list, adding the mainframe number as a prefix 1000, 2000, 3000, to each channel
    CompleteChannelList = [channel + 1000*(index+1) for index, agilent in enumerate(self.Agilents) for channel in agilent.ChannelList]

    self.DomeTempSensor        = tTempHumSensor(PROJECT_CONFIG.DomeTempSensorPort,        parent=None) if PROJECT_CONFIG.bHasDomeTempSensor        else None
    self.OutsideTempSensor     = tTempHumSensor(PROJECT_CONFIG.OutsideTempSensorPort,     parent=None) if PROJECT_CONFIG.bHasOutsideTempSensor     else None
    self.ElectronicsTempSensor = tTempHumSensor(PROJECT_CONFIG.ElectronicsTempSensorPort, parent=None) if PROJECT_CONFIG.bHasElectronicsTempSensor else None

    # Get the indices of channels that we will want to pick out of the data for reporting to 
    # the marquee display
    BoxMeasurementIndex     = CompleteChannelList.index(BOX_CHANNEL_FOR_MARQUEE_DISPLAY) if BOX_CHANNEL_FOR_MARQUEE_DISPLAY in CompleteChannelList else None
    SandTopMeasurementIndex = CompleteChannelList.index(SAND_TOP_CHANNEL)                 if SAND_TOP_CHANNEL                 in CompleteChannelList else None
    SandMidMeasurementIndex = CompleteChannelList.index(SAND_MID_CHANNEL)                 if SAND_MID_CHANNEL                 in CompleteChannelList else None
    SandBotMeasurementIndex = CompleteChannelList.index(SAND_BOT_CHANNEL)                 if SAND_BOT_CHANNEL                 in CompleteChannelList else None

    # Determine which channels to use for reporting DNI and GHI to marquee
    DniChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'DNI channels') 
    GhiChannelIndex = FindFirstNonNoneValueForField(CompleteChannelList, 'GHI channels') 

    # Motor and USB hub power relay objects.  Set the checkboxes based on the current relay state
    self.MotorPower  = None
    self.UsbHubPower = None
    bUsbPowerState   = True
    if PROJECT_CONFIG.bHasMotorPowerRelay:
      self.MotorPower = tPowerControl(self.Agilents[PROJECT_CONFIG.PowerRelayAgilentIndex], 'Motors', PROJECT_CONFIG.MotorPowerChannels, tAgilent.RELAY_NORMALLY_CLOSED, self)
      try:
        self.MotorPowerCheckboxUpdate(self.MotorPower.GetPowerState())
      except TimeoutError:
        print('Motor power relay not responding')
    else:
      self.MotorPowerCheckboxUpdate(False)
      self.ui.MotorPowerCheckBox.setEnabled(False)
    if PROJECT_CONFIG.bHasUsbPowerRelay:
      self.UsbHubPower = tPowerControl(self.Agilents[PROJECT_CONFIG.PowerRelayAgilentIndex], 'USB Hub', PROJECT_CONFIG.UsbHubPowerChannel, tAgilent.RELAY_NORMALLY_CLOSED, self)
      try:
        bUsbPowerState = self.UsbHubPower.GetPowerState()
        self.UsbPowerCheckboxUpdate(bUsbPowerState)
      except TimeoutError:
        print('USB power relay not responding')
    else:
      self.UsbPowerCheckboxUpdate(True)
      self.ui.UsbPowerCheckBox.setEnabled(False)


    ##### Prepare the log file
    # Write comma-separated headers  
    # Header line 1 will capture the version info and raw configuration of the Agilent units
    # Header line 2 is  field/channel names
    DailyFolder   = os.path.join(os.path.expanduser("~"), "Documents", DAILY_FOLDER)
    ArchiveFolder = os.path.join(os.path.expanduser("~"), ARCHIVE_FOLDER)
    Header1Parts = [HEADER1]
    if len(PROJECT_CONFIG.Agilents) > 0:
      Header1Parts.append(','.join([f'"{element}"' if element is not None else '""' for sublist in PROJECT_CONFIG.Agilents for element in sublist]))
    Header1 = ','.join(Header1Parts)

    Header2Fields = ['"Date"', '"Time"']
    Header2Fields.extend([str(num) for num in CompleteChannelList])
    if PROJECT_CONFIG.bHasOutsideTempSensor:
      Header2Fields.extend(['"Outside T"', '"Outside H"'])
    if PROJECT_CONFIG.bHasDomeTempSensor:
      Header2Fields.extend(['"Dome T"', '"Dome H"'])
    if PROJECT_CONFIG.bHasElectronicsTempSensor:
      Header2Fields.extend(['"Elec T"', '"Elec H"'])
    for CollectorInfo in PROJECT_CONFIG.CollectorPorts:
      Header2Fields.append(f'"{CollectorInfo.Name} CPU Temp"')
    for CollectorInfo in PROJECT_CONFIG.CollectorPorts:
      Header2Fields.append(f'"{CollectorInfo.Name} ModeNum"')
      Header2Fields.append(f'"{CollectorInfo.Name} ModeString"')
    Header2 = ','.join(Header2Fields)

    self.LogFile = tLogFile(DailyFolder, ArchiveFolder, Header1, Header2, SITE_TIMEZONE, PROJECT_CONFIG.LogFilePrefix)

    # The parent of the object has to be None or it can't be moved to a thread.  The Logger needs to be passed the
    # collector list just so that it can pass it on to the Marquee object, which it creates.
    self.Collectors = self.CollectorControlWindow.CollectorList()
    self.CollectorLogFiles = tCollectorLogFiles(self.LogFile.DailyFolder, self.Collectors, self)
    self.PeriodicLogger = tPeriodicLogger(self.Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex, 
                                          SandTopMeasurementIndex, SandMidMeasurementIndex, SandBotMeasurementIndex,
                                          self.DomeTempSensor, self.OutsideTempSensor, self.ElectronicsTempSensor,
                                          self.Collectors, self.LogFile, self.CollectorLogFiles, self)



    # Start the NIP sequencer
    # The third Agilent is the one with the Actuator card in it for sequencing
    self.Sun          = tSun(SITE_LATITUDE, SITE_LONGITUDE, SITE_ELEVATION, SITE_TIMEZONE)
    if PROJECT_CONFIG.bHasNip and PROJECT_CONFIG.bHasPowerRelays:
      self.NipSequencer = tNipSequencer(self.Agilents[PROJECT_CONFIG.PowerRelayAgilentIndex], PROJECT_CONFIG.NipPowerChannels,
                                        PROJECT_CONFIG.NipOnOffButtonChannel, PROJECT_CONFIG.PyranometerPowerChannel,
                                        self.Sun, self.PeriodicLogger, self)
    else:
      self.NipSequencer = tSunClockSequencer(self.Sun, self)
      

    # Now that everything is going, we can start the collector monitoring threads.  At this point, the 
    # Collectors are still in this thread that created them, but they will now move to their own threads
    for Collector in self.Collectors:
      # Connect the collector to the USB Hub Power signal
      # Also tell it the current USB hub power state
      Collector.SetUsbPowerDevice(self.UsbHubPower, bUsbPowerState)
      Collector.Start(self.NipSequencer.SunriseSunsetUpdate)   # Collector listens to NipSequencer sunrise/sunset signals

    self.CollectorSequencer = tCollectorSequencer(self.Collectors, self.UsbHubPower, self.MotorPower, self.NipSequencer.SunriseSunsetUpdate, self.NipSequencer.NipHasDni, self)

    # Connect to signals
    self.ConnectToSignals()

    # Since the NIP sequencer won't run for a full minute, go ahead and run it once right now.
    # One might want to do this inside the NipSequencer constructor instead.  But that first 
    # run emits Sunrise and Sunset signals that we, and the collector sequencer, would like to
    # catch, so we want to wait until after we've connected to the signals
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
    if PROJECT_CONFIG.bHasDniSensor:
      self.PeriodicLogger.DniUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.DniLabel, floatVal))
    else:
      self.ui.DniLabel.setText("---")
    if PROJECT_CONFIG.bHasGhiSensor:
      self.PeriodicLogger.GhiUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.GhiLabel, floatVal))
    else:
      self.ui.GhiLabel.setText("---")
    if PROJECT_CONFIG.bHasThermocouples:
      self.PeriodicLogger.BoxTempUpdate    .connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.BoxTempLabel    , floatVal))
      self.PeriodicLogger.SandTopTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandTopTempLabel, floatVal))
      self.PeriodicLogger.SandMidTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandMidTempLabel, floatVal))
      self.PeriodicLogger.SandBotTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.SandBotTempLabel, floatVal))
    else:
      self.ui.BoxTempLabel    .setText("---")
      self.ui.SandTopTempLabel.setText("---")
      self.ui.SandMidTempLabel.setText("---")
      self.ui.SandBotTempLabel.setText("---")
    if PROJECT_CONFIG.bHasDomeTempSensor:
      self.PeriodicLogger.DomeTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.DomeTempLabel, floatVal))
    else:
      self.ui.DomeTempLabel.setText("---")
    if PROJECT_CONFIG.bHasElectronicsTempSensor:
      self.PeriodicLogger.ElecTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.ElecTempLabel, floatVal))
    else:
      self.ui.ElecTempLabel.setText("---")
    if PROJECT_CONFIG.bHasOutsideTempSensor:
      self.PeriodicLogger.StanTempUpdate.connect(lambda floatVal: self.Update4DigitIntLabel(self.ui.StanleyTempLabel, floatVal))
    else:
      self.ui.StanleyTempLabel.setText("---")

    # These are for messages about the power relays from the relay class
    #self.MotorPower.PowerRelayStateUpdate.connect(self.MotorPowerCheckboxUpdate)
    #self.UsbPower  .PowerRelayStateUpdate.connect(self.UsbPowerCheckboxUpdate  )
    # These are for when the user actually checks the box
    self.ui.MotorPowerCheckBox.checkStateChanged.connect(self.UserCheckedMotorPower)
    self.ui.UsbPowerCheckBox  .checkStateChanged.connect(self.UserCheckedUsbPower  )

    self.NipSequencer.NipStateUpdate     .connect(self.UpdateNipStateMessage)
    self.NipSequencer.SunriseSunsetUpdate.connect(self.UpdateSunriseSunset)

    self.CollectorSequencer.StateUpdate  .connect(self.UpdateMasterStateLabel)
    # The signal has already been emitted by the sequencer, so we need to do this to init the GUI properly
    self.UpdateMasterStateLabel(self.CollectorSequencer.state)

    # Access the radio buttons by their object names
    self.SequencerModeRadioGroup = QButtonGroup(self)
    self.SequencerModeRadioGroup.addButton(self.ui.FullAutoRadioButton)
    self.SequencerModeRadioGroup.addButton(self.ui.SemiAutoRadioButton)
    self.SequencerModeRadioGroup.addButton(self.ui.SequencerOffRadioButton)
    self.ui.SequencerOffRadioButton.setChecked(True)

    # Connect the group signal
    self.SequencerModeRadioGroup.buttonClicked.connect(self.SequencerModeChangeRequest)

    # Connect command buttons
    self.ui.OffPushButton           .clicked.connect(lambda: [Collector.DoOff          .emit() for Collector in self.Collectors])
    self.ui.HomePushButton          .clicked.connect(lambda: [Collector.DoHome         .emit() for Collector in self.Collectors])
    self.ui.SetTimePushButton       .clicked.connect(lambda: [Collector.DoSetTime      .emit() for Collector in self.Collectors])
    self.ui.StowPushButton          .clicked.connect(lambda: [Collector.DoStow         .emit() for Collector in self.Collectors])
    self.ui.FlatPushButton          .clicked.connect(lambda: [Collector.DoFlat         .emit() for Collector in self.Collectors])
    self.ui.TrackPushButton         .clicked.connect(lambda: [Collector.DoTrack        .emit() for Collector in self.Collectors])
    self.ui.SaveNvSettingsPushButton.clicked.connect(self.DoSaveNvSettings)



  #######################################################
  # SequencerModeChangeRequest - When the user clicks the sequencer mode button
  #
  
  def SequencerModeChangeRequest(self, NewState : str):
    if self.ui.SequencerOffRadioButton.isChecked():
      self.CollectorSequencer.DisableSeq.emit()
    else:
      # Not off, either full or semi auto
      self.CollectorSequencer.EnableSeq.emit()
      self.CollectorSequencer.SetFullAutomation.emit(self.ui.FullAutoRadioButton.isChecked())


  #######################################################
  # UpdateMasterStateLabel - Updates the master state shown in the main panel
  #
  
  def UpdateMasterStateLabel(self, NewState : str):
    self.ui.MasterStateLabel.setText(NewState)


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
    if self.MotorPower is None:
      return
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
    if self.UsbHubPower is None:
      return
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
  # UpdateSunriseSunset

  def UpdateSunriseSunset(self, Sunrise: QDateTime, Sunset: QDateTime):
    SunriseString = Sunrise.toString("HH:mm:ss")
    SunsetString  = Sunset .toString("HH:mm:ss")
    self.ui.SunriseLabel.setText(SunriseString)
    self.ui.SunsetLabel .setText(SunsetString )


  #######################################################
  # DoOff

  def DoOff(self):
    for Collector in self.Collectors:
      Collector.DoOff.emit()


  #######################################################
  # DoSaveNvSettings - Sends DumpNvSettings to every board and writes captured output to files

  def DoSaveNvSettings(self):
    if hasattr(self, '_nv_capture_active') and self._nv_capture_active:
      print('SaveNvSettings: capture already in progress, ignoring', flush=True)
      return

    timestamp     = datetime.now().strftime("%y%m%d_%H%M")
    output_dir    = os.path.join("NvSettings", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    print(f'SaveNvSettings: capturing to {output_dir}', flush=True)

    self._nv_capture_active = True
    self._nv_output_dir     = output_dir
    self._nv_captures       = {}

    for Collector in self.Collectors:
      name  = Collector.CollectorName
      lines = []

      def make_slot(coll, line_list, board_name):
        started = [False]
        def slot(line):
          if line.strip() == '---':
            if not started[0]:
              started[0] = True
            else:
              coll.TextLineReceived.disconnect(slot)
              self._nv_captures[board_name]['done'] = True
              self._WriteNvFile(board_name, line_list)
          elif started[0]:
            line_list.append(line)
        return slot

      if not Collector.IsInit():
        continue

      slot_fn = make_slot(Collector, lines, name)
      self._nv_captures[name] = {'lines': lines, 'slot': slot_fn, 'done': False}
      Collector.TextLineReceived.connect(slot_fn)
      Collector.DoDumpNvSettings.emit()

    QTimer.singleShot(5000, self._FinishSaveNvSettings)


  #######################################################
  # _WriteNvFile - Writes one board's captured lines to its settings file

  def _WriteNvFile(self, collector_name, lines):
    board_id = None
    for line in lines:
      m = re.search(r'\bG3V2-\S+', line)
      if m:
        board_id = m.group(0)
        break

    if board_id:
      filename = f"{board_id}_{collector_name}_Settings.txt"
    else:
      filename = f"{collector_name}_Settings.txt"

    output_path = os.path.join(self._nv_output_dir, filename)
    with open(output_path, 'w') as f:
      f.write('\n'.join(lines))
    print(f'SaveNvSettings: wrote {output_path} ({len(lines)} lines)', flush=True)


  #######################################################
  # _FinishSaveNvSettings - Fallback timeout: writes files for any board that did not send ---

  def _FinishSaveNvSettings(self):
    for Collector in self.Collectors:
      name    = Collector.CollectorName
      capture = self._nv_captures.get(name)
      if capture is None:
        continue
      if not capture['done']:
        Collector.TextLineReceived.disconnect(capture['slot'])
        self._WriteNvFile(name, capture['lines'])

    self._nv_captures       = {}
    self._nv_capture_active = False
    print('SaveNvSettings: done', flush=True)


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
      pass
      #Collector.RequestExit()

    # Tell the periodic logger thread to shut down, and wait for confirmation
    #self.PeriodicLogger.RequestExit()

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
  for index, agilent in enumerate(PROJECT_CONFIG.Agilents):
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
  Channels = [agilent[ChannelIndex] for agilent in PROJECT_CONFIG.Agilents]  # Extracting all the DNI channel entries for all AGILENT's into a list
  ChannelIndex = None          
  DNI             = 0                                          
  # Loop to find the first non-None, and add 1000*(AGILENT #) to get the overall channel number
  for index, ChannelNum in enumerate(Channels):
    if ChannelNum is not None:
      OverallChannelNum = ChannelNum + (1000 * (index+1))                 # Overall channel number
      ChannelIndex = CompleteChannelList.index(OverallChannelNum)  # Its index in the returned list
      break
  return ChannelIndex


#################################################
# RemoveSiteCommandLineArgs
#
# Removes our app-specific --site argument before Qt parses argv.

def RemoveSiteCommandLineArgs():
  i = 0
  while i < len(sys.argv):
    if sys.argv[i] == "--site" and i + 1 < len(sys.argv):
      del sys.argv[i:i + 2]
    elif sys.argv[i].startswith("--site="):
      del sys.argv[i]
    else:
      i += 1



if __name__ == "__main__":
  global app
  # Get some basic stuff out of the way before even trying to create a window
  ValidateAGILENTSEntries()
  RemoveSiteCommandLineArgs()

  # Create the application and main window
  app = QApplication(sys.argv)

  MainWin = MasterControl()
  MainWin.show()
  MainWin.raise_()
  MainWin.activateWindow()

  #app.aboutToQuit.connect(lambda: print("aboutToQuit signal emitted"))
  #app.aboutToQuit.connect(MainWin.CleanUp)
  
  MainWin.StartApplication()

  # Run the event loop, and propagate any exit error code back to the OS.
  exitCode = app.exec()
  sys.exit(exitCode)
