##########################################################################################
# tCollectorControlWindow - class for the window that contains the 15 individual collectors
#

#################################################
#
# Modules used
#

from collections import namedtuple

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtCore    import Qt, QFile

# Import configuration of the system
from CollectorPane_ui  import Ui_Form
from ConfigInfo        import *
from Collector         import tCollector
from Utilities         import WaitForSignal



##########################################################################################
##########################################################################################
##########################################################################################
# tCollectorPane  - Class that implements the collector pane and all collector activities
#
# 
#

class tCollectorPane(QWidget):
  
  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, collectorName, portName, baud, parent=None):
    super().__init__(parent)   # QWidget constructor
      
    self.bInit    = False
    self.bResponded  = False
    self.name     = 'Foo' #collectorName
    self.port     = None

    # Load CollectorPane UI dynamically
    #loader = QUiLoader()
    #ui_file = QFile("CollectorPane.ui")
    #ui_file.open(QFile.ReadOnly)
    #self.ui = loader.load(ui_file, self)    # Have to assign to self so that ui and all its children persist after the constructor exits
    #ui_file.close()

    # Auto-bind widgets as attributes of self.  Not needed if we compile the UI with pyside6-uic,
    # but QUiLoader does not do this automatically.
    #for widget in self.ui.findChildren(QWidget):
    #  setattr(self, widget.objectName(), widget)
    # self.setFixedSize(self.ui.size())


    self.ui = Ui_Form()
    self.ui.setupUi(self)
    
    self.setFixedSize(self.size())

    collectorTitle = 'Collector ' + collectorName
    self.ui.CollectorGroup.setTitle(collectorTitle)

    # Have the displays come up in a disconnected state, until we see a connection event
    self.ConnectionEvent(False)

    # Create the Collector object that interfaces to the hardware
    self.Collector = tCollector(collectorName, portName, baud)
    self.Collector.SerialPort.PortOpenStateChange.connect(self.ConnectionEvent)

    self.Collector.TextLineReceived.connect(self.AddToLog)   # a non-telemetry line, should just be sent to the console
    self.Collector.TelemetryUpdate.connect(self.UpdateTelemetry)

    # The threshold fields are things the user can enter.  We will update if we have new values,
    # but not every time.  This allow the user to type new values.
    # Threshold fields, initial values
    self.WideIllumPercentEntry  = 0
    self.NarrowSkyBgEntry       = 0
    self.NarrowIllumThreshEntry = 0
    # And connect to signals that tell us the user has entered new values
    self.ui.WideIllumPercentLineEdit   .editingFinished.connect(self.NewUserWideIllumPercent)
    self.ui.NarrowSkyBackgroundLineEdit.editingFinished.connect(self.NewUserNarrowSkyBackground)
    self.ui.NarrowIllumPercentLineEdit .editingFinished.connect(self.NewUserNarrowIllumPercent)


  ###############################################
  # closeEvent - Shut down collector thread
  # 


  def closeEvent(self, event):
    print("CollectorPane is closing",flush=True)

    # Tell the periodic logger thread to shut down, and wait for confirmation
    # WaitForSignal(SignalToWaitFor = self.Collector.TheThread.finished, SignalToEmit = self.Collector.RequestExit)
    # Now that the thread has exited, schedule it for deletion
    #self.Collector.deleteLater()
    print("Collector cleaned up",flush=True)


  ###############################################
  # Destructor - Clean up 
  # 

  def __del__(self):
    pass


  ###############################################
  # ConnectionEvent
  # 
  # INPUTS:
  #   bPortOpenState - True or False depending on whether the port is connected
  #     

  def ConnectionEvent(self, bConnected):
    # Show all the titles and buttons in an enabled or disabled state
    self.ui.OffPushButton.        setEnabled(bConnected)
    self.ui.HomePushButton.       setEnabled(bConnected)
    self.ui.TrackPushButton.      setEnabled(bConnected)
    self.ui.StowPushButton.       setEnabled(bConnected)
    self.ui.SetTimePushButton.    setEnabled(bConnected)
    self.ui.MotorStatusPushButton.setEnabled(bConnected)
    self.ui.UnstickPushButton.    setEnabled(bConnected)
    self.ui.RebootPushButton.     setEnabled(bConnected)

    # Set the box lables and state label to gray if not connected    
    GroupBoxStyleString = "" if bConnected else "QGroupBox { color: gray; }"

    self.ui.CollectorGroup.setStyleSheet(GroupBoxStyleString)
    self.ui.AzGroup.       setStyleSheet(GroupBoxStyleString)
    self.ui.ElGroup.       setStyleSheet(GroupBoxStyleString)
    self.ui.WideGroup.     setStyleSheet(GroupBoxStyleString)
    self.ui.NarrowGroup.   setStyleSheet(GroupBoxStyleString)
    self.ui.ThresholdGroup.setStyleSheet(GroupBoxStyleString)

    LabelStyleString = "" if bConnected else "QLabel { color: gray; }"
    self.ui.State.         setStyleSheet(LabelStyleString)


  ###############################################
  ###############################################
  # User entries into the threshold fields
  #
  # If the user enters garbage, just set the value to 0, which will led to it being overwritten
  # by the collector at the next update.
  #

  ###############################################
  # NewUserWideIllumPercent
  def NewUserWideIllumPercent(self):
    try:
      new_value = int(self.ui.WideIllumPercentLineEdit.text())
    except ValueError:
      new_value = 0

    # Invalidate out-of-range inputs
    if new_value < 1 or new_value > 100:
      new_value = 0

    self.WideIllumPercentEntry = new_value
    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.emit(self.WideIllumPercentEntry, self.NarrowSkyBgEntry, self.NarrowIllumThreshEntry)

  ###############################################
  # NewUserNarrowSkyBackground
  def NewUserNarrowSkyBackground(self):
    try:
      new_value = int(self.ui.NarrowSkyBackgroundLineEdit.text())
    except ValueError:
      new_value = 0

    # Invalidate out-of-range inputs
    if new_value < 1 or new_value > 100:
      new_value = 0

    self.NarrowSkyBgEntry = new_value
    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.emit(self.WideIllumPercentEntry, self.NarrowSkyBgEntry, self.NarrowIllumThreshEntry)
  
  ###############################################
  # NewUserNarrowIllumPercent
  def NewUserNarrowIllumPercent(self):
    try:
      new_value = int(self.ui.NarrowIllumPercentLineEdit.text())
    except ValueError:
      new_value = 0

    # Invalidate out-of-range inputs
    if new_value < 1 or new_value > 100:
      new_value = 0

    self.NarrowIllumThreshEntry = new_value
    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.emit(self.WideIllumPercentEntry, self.NarrowSkyBgEntry, self.NarrowIllumThreshEntry)




  ###############################################
  # AddToLog - Text messages from the collector that aren't telemetry strings
  # 
  # INPUTS:
  #   Line - the text line from the collector
  #     

  def AddToLog(self, Line: str):
    # Append the new line
    self.CollectorLog.append(Line)
    
    # Limit the log to the last N lines (example)
    while self.CollectorLog.document().blockCount() > COLLECTOR_LOG_MAXLINES:
      cursor = self.CollectorLog.textCursor()
      cursor.movePosition(cursor.Start)  # Move to the start
      cursor.select(cursor.BlockUnderCursor)  # Select the first block (line)
      cursor.removeSelectedText()  # Remove the selected text
      cursor.deleteChar()  # Remove any leftover line break


  ###############################################
  # UpdateTelemetry - Update GUI with new info from collector
  # 
  # INPUTS:
  #   Telem - A dictionary with all the new info from the collector
  #     

  def UpdateTelemetry(self, telemetry: dict):

    # Current time
    if "TimeString" in telemetry:
      self.ui.TimeLabel.setText(telemetry["TimeString"])

    # Motor positions
    if "P" in telemetry:
      azPos = str(telemetry["P"][0])
      elPos = str(telemetry["P"][1])
      self.ui.AzPosLabel.setText(azPos)
      self.ui.ElPosLabel.setText(elPos)

    # Motor velocities
    if "V" in telemetry:
      azVel = str(telemetry["V"][0])
      elVel = str(telemetry["V"][1])
      self.ui.AzVelLabel.setText(azVel)
      self.ui.ElVelLabel.setText(elVel)

    # Narrow-angle readings
    if "N" in telemetry:
      # Update narrow-angle readings
      # UL, UR, LL, LR
      self.ui.NarrowUL.setText(str(telemetry["N"][0]))
      self.ui.NarrowUR.setText(str(telemetry["N"][1]))
      self.ui.NarrowLL.setText(str(telemetry["N"][2]))
      self.ui.NarrowLR.setText(str(telemetry["N"][3]))


    # Wide-angle readings
    if "W" in telemetry:
      # Update wide-angle readings
      # UL, UR, LL, LR
      self.ui.WideUL.setText(str(telemetry["W"][0]))
      self.ui.WideUR.setText(str(telemetry["W"][1]))
      self.ui.WideLL.setText(str(telemetry["W"][2]))
      self.ui.WideLR.setText(str(telemetry["W"][3]))


    # Tuple of thresholds - wide illum, narrow sky BG %, narrow illum %
    if "R" in telemetry:
      if telemetry["R"][0] != self.WideIllumPercentEntry:
        self.WideIllumPercentEntry = telemetry["R"][0]
        self.ui.WideIllumPercentLineEdit.setText(str(self.WideIllumPercentEntry))
      if telemetry["R"][1] != self.NarrowSkyBgEntry:
        self.NarrowSkyBgEntry = telemetry["R"][1]
        self.ui.NarrowSkyBackgroundLineEdit.setText(str(self.NarrowSkyBgEntry))
      if telemetry["R"][2] != self.NarrowIllumThreshEntry:
        self.NarrowIllumThreshEntry = telemetry["R"][2]
        self.ui.NarrowIllumPercentLineEdit.setText(str(self.NarrowIllumThreshEntry))

    # Servo error
    if "E" in telemetry:
      # Update servo error
      pass

    # Narrow sky background
    if "G" in telemetry:
      # Update narrow sky background in counts
      pass

    # Total intensity on detector
    if "I" in telemetry:
      # Update total intensity on detector in counts and as a percentage
      pass

    # Narrow mode status
    if "IsNarrowMode" in telemetry:
      # Update narrow-angle mode status
      pass

    # Narrow angle threshold
    if "NarrowAngleThreshold" in telemetry:
      # Update narrow-angle threshold
      pass

    # Limit states
    if "LimitStates" in telemetry:
      # Update limit states (boolean array)
      pass

    # Servo mode
    if "PositionMode" in telemetry:
      # Update servo mode (true = position, false = velocity)
      pass

    # Spot coordinates
    if "C" in telemetry:
      # Update spot coordinates (x, y)
      pass

    # Collector mode number
    if "ModeNum" in telemetry:
      # Update current mode of the collector (integer)
      pass

    # Collector mode string
    if "ModeString" in telemetry:
      # Update current mode of the collector (string)
      pass




#   P                  Tuple of az/el motor positions
#   V                  Tuple of az/el motor velocities
#   N                  Tuple of the four narrow-angle readings
#   W                  Tuple of the four wide-angle readings
#   R                  Tuple of thresholds - wide illum, narrow sky BG %, narrow illum %
#   E                  Servo error, either velocity or position error depending on servo mode
#   G                  Narrow sky background in counts
#   I                  Tuple of Total intensity on detector in counts, and as a percentage
# IsNarrowMode         True if in narrow-angle mode, else wide
# NarrowAngleThreshold Threshold for switching to narrow angle
# LimitStates          boolean[5] - az low, az high, el low, el high, home
# PositionMode         boolean - true if in positoin mode, false if velocity mode
#   C                  Spot coordinate x-y (float)
# ModeNum              Current mode of the collector (integer)
# ModeString           Current mode of the collecor (string)
# Timestring           Current time as a string HH:MM:SS



##########################################################################################
##########################################################################################
##########################################################################################
#
# tCollectorControlWindow - class for the main "master control" window of the app
#
# Also includes all top-level sequencing and logic
#

class tCollectorControlWindow(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Collector Control")
    # Create a central widget and grid layout for 5x3 collector panes
    central_widget = QWidget()
    layout = QGridLayout(central_widget)

    # Create the collector array.  We have to do it here, rather than at a higher level,
    # because the tCollector widget needs to be told its parent.  The collector panes will 
    # create and own the collecor objects
    self.CollectorPanes = [ tCollectorPane(*port_info, COLLECTOR_BAUD_RATE, self) for port_info in COLLECTOR_PORTS ]
    Collector_iterator = (CollectorPane for CollectorPane in self.CollectorPanes)  # Compact generator for use in loop below
    for row in range(5):
      for col in range(3):
        layout.addWidget(next(Collector_iterator), row, col)
        
    # Wrap the central widget with a QScrollArea
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(central_widget)

    # Only enable vertical scroll bar
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    # Set the scroll area as the main layout
    main_layout = QVBoxLayout(self)
    main_layout.addWidget(scroll_area)
    self.setLayout(main_layout)

    # Disable the close button in this window
    self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

    self.bAllowClose = False


  ###############################################
  # ForceClose - used by MainWin to shut us down at exit
  #    

  def ForceClose(self):
    self.bAllowClose = True
    self.close()


  ###############################################
  # closeEvent - rejects any attempt to close the window directly - it must follow MainWin
  #    

  def closeEvent(self, event):
    print("CollectorWindow close event")
    if not self.bAllowClose:
      # Ignore any close events
      QMessageBox.warning(self, "Warning", "You cannot close this window directly.")
      event.ignore()


  ###############################################
  # CollectorList - Returns a list of all 15 collectors
  # 

  def CollectorList(self):
    CollectorList = [ CollectorPane.Collector for CollectorPane in self.CollectorPanes ]
    return CollectorList
