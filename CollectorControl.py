##########################################################################################
# tCollectorControlWindow - class for the window that contains the 15 individual collectors
#

#################################################
#
# Modules used
#

from collections import namedtuple

from PySide6.QtGui     import QTextCursor
from PySide6.QtWidgets import QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtCore    import Qt

# Import configuration of the system
from CollectorPane_ui  import Ui_Form
from ConfigInfo        import *
from Collector         import tCollector
from Utilities         import SignalThenWaitFor



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
      
    self.bInit       = False
    self.bResponded  = False
    self.name        = 'Foo' #collectorName
    self.port        = None
    self.bConnected  = False

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



    # Create the Collector object that interfaces to the hardware
    self.Collector = tCollector(collectorName, portName, baud)
    self.Collector.PortOpenStateChange.connect(self.ConnectionEvent)

    self.Collector.ReleaseStringReceived.connect(self.UpdateReleaseString)
    self.Collector.TextLineReceived.connect(self.AddToLog)   # a non-telemetry line, should just be sent to the console
    self.Collector.TelemetryUpdate.connect(self.UpdateTelemetry)

    # Set the initial state of the display to match whether the port is open
    self.ConnectionEvent(False)

    # The threshold fields are things the user can enter.  We will update if we have new values,
    # but not every time.  This allow the user to type new values.
    # Threshold fields, initial values

    # And connect to signals that tell us the user has entered new values
    self.ui.WideIllumPercentLineEdit   .editingFinished.connect(self.NewUserWideIllumPercent)
    self.ui.NarrowSkyBackgroundLineEdit.editingFinished.connect(self.NewUserNarrowSkyBackground)
    self.ui.NarrowIllumPercentLineEdit .editingFinished.connect(self.NewUserNarrowIllumPercent)

    # Command buttons connect directly to signals of the tCollector class
    self.ui.OffPushButton.        clicked.connect(self.Collector.DoOff      )
    self.ui.HomePushButton.       clicked.connect(self.Collector.DoHome     )
    self.ui.TrackPushButton.      clicked.connect(self.Collector.DoTrack    )
    self.ui.StowPushButton.       clicked.connect(self.Collector.DoStow     )
    self.ui.SetTimePushButton.    clicked.connect(self.Collector.DoSetTime  )
    self.ui.MotorStatusPushButton.clicked.connect(self.Collector.DoMotStatus)
    self.ui.UnstickPushButton.    clicked.connect(self.Collector.DoUnstick  )
    self.ui.RebootPushButton.     clicked.connect(self.Collector.DoReboot   )
    self.ui.TimeButton.           clicked.connect(self.Collector.DoReconnect)


  ###############################################
  # closeEvent - Shut down collector thread
  # 

  def closeEvent(self, event):
    print("CollectorPane is closing",flush=True)

    # Tell the periodic logger thread to shut down, and wait for confirmation
    # SignalThenWaitFor(SignalToWaitFor = self.Collector.TheThread.finished, SignalToEmit = self.Collector.RequestExit)
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
    # print('Collector connection event: ', bConnected)
    # Show all the titles and buttons in an enabled or disabled state
    self.ui.OffPushButton.        setEnabled(bConnected)
    self.ui.HomePushButton.       setEnabled(bConnected)
    self.ui.TrackPushButton.      setEnabled(bConnected)
    self.ui.StowPushButton.       setEnabled(bConnected)
    self.ui.SetTimePushButton.    setEnabled(bConnected)
    self.ui.MotorStatusPushButton.setEnabled(bConnected)
    self.ui.UnstickPushButton.    setEnabled(bConnected)
    self.ui.RebootPushButton.     setEnabled(bConnected)

    # Set the box labels and state label to gray if not connected    
    GroupBoxStyleString = "" if bConnected else "QGroupBox { color: gray; }"

    self.ui.CollectorGroup.setStyleSheet(GroupBoxStyleString)
    self.ui.AzGroup.       setStyleSheet(GroupBoxStyleString)
    self.ui.ElGroup.       setStyleSheet(GroupBoxStyleString)
    self.ui.WideGroup.     setStyleSheet(GroupBoxStyleString)
    self.ui.NarrowGroup.   setStyleSheet(GroupBoxStyleString)
    self.ui.ThresholdGroup.setStyleSheet(GroupBoxStyleString)

    LabelStyleString = "" if bConnected else "QLabel { color: gray; }"
    self.ui.State.         setStyleSheet(LabelStyleString)

    self.bConnected  = bConnected


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

    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.SetWideIllumPercentThreshold(new_value)


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

    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.SetNarrowSkyBackgroundPercentThreshold(new_value)

  
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

    # If it's a valid new value, send it to the target
    if new_value != 0:
      self.Collector.SetNarrowIllumPercentThreshold(new_value)


  ###############################################
  # UpdateReleaseString - TUpate the s/w version info in the upper right corner
  # 
  # INPUTS:
  #   ReleaseString - the string from the collector
  #     

  def UpdateReleaseString(self, ReleaseString: str):
    self.ui.ReleaseStringLabel.setText(ReleaseString)


  ###############################################
  # AddToLog - Text messages from the collector that aren't telemetry strings
  # 
  # INPUTS:
  #   Line - the text line from the collector
  #     

  def AddToLog(self, Line: str):
    # Append the new line
    Line = Line.rstrip('\r\n')  # Eliminate newlines, since append adds them
    self.ui.CollectorLog.append(Line)
    
    # Limit the log to the last N lines (example)
    while self.ui.CollectorLog.document().blockCount() > COLLECTOR_LOG_MAXLINES:
      cursor = self.ui.CollectorLog.textCursor()
      cursor.movePosition(QTextCursor.MoveOperation.Start)  # Move to the start
      cursor.select(QTextCursor.SelectionType.BlockUnderCursor)  # Select the first block (line)
      cursor.removeSelectedText()  # Remove the selected text
      cursor.deleteChar()  # Remove any leftover line break


  ###############################################
  # UpdateTelemetry - Update GUI with new info from collector
  # 
  # INPUTS:
  #   Telem - A dictionary with all the new info from the collector
  #     

  def UpdateTelemetry(self, telemetry: dict):
    try:
      # Current time
      if "TimeString" in telemetry:
        self.ui.TimeButton.setText(telemetry["TimeString"])

      # Motor positions
      if "P" in telemetry:
        azPos = f'P:{telemetry["P"][0]:>11,}'
        elPos = f'P:{telemetry["P"][1]:>11,}'
        self.ui.AzPosLabel.setText(azPos)
        self.ui.ElPosLabel.setText(elPos)

      # Motor velocities
      if "V" in telemetry:
        azVel = f'V:{telemetry["V"][0]:11d}'
        elVel = f'V:{telemetry["V"][1]:11d}'
        self.ui.AzVelLabel.setText(azVel)
        self.ui.ElVelLabel.setText(elVel)

      # Narrow-angle readings
      if "N" in telemetry:
        # Update narrow-angle readings
        # R, L, U, D
        right = telemetry["N"][0]
        left  = telemetry["N"][1]
        up    = telemetry["N"][2]
        down  = telemetry["N"][3]
        self.ui.NarrowRight.setText(f'{right:5d}')
        self.ui.NarrowLeft .setText(f'{left:5d}')
        self.ui.NarrowUp   .setText(f'{up:5d}')
        self.ui.NarrowDown .setText(f'{down:5d}')

        total   = right + left + up + down
        percent = int(100*total/65532)
        self.ui.NarrowIntensity.setText(f'{percent:3d}%  {total:5d}')

      # Wide-angle readings
      if "W" in telemetry:
        # Update wide-angle readings
        if QUAD_CELL_HANDEDNESS > 0:
          # UL, UR, LL, LR
          self.ui.WideUL.setText(f'{telemetry["W"][0]:5d}' if telemetry["W"][0] >= 0 else ' ****')
          self.ui.WideUR.setText(f'{telemetry["W"][1]:5d}' if telemetry["W"][1] >= 0 else ' ****')
          self.ui.WideLL.setText(f'{telemetry["W"][2]:5d}' if telemetry["W"][2] >= 0 else ' ****')
          self.ui.WideLR.setText(f'{telemetry["W"][3]:5d}' if telemetry["W"][3] >= 0 else ' ****')
        else:
          # UL, UR, LL, LR
          self.ui.WideUR.setText(f'{telemetry["W"][0]:5d}' if telemetry["W"][0] >= 0 else ' ****')
          self.ui.WideUL.setText(f'{telemetry["W"][1]:5d}' if telemetry["W"][1] >= 0 else ' ****')
          self.ui.WideLR.setText(f'{telemetry["W"][2]:5d}' if telemetry["W"][2] >= 0 else ' ****')
          self.ui.WideLL.setText(f'{telemetry["W"][3]:5d}' if telemetry["W"][3] >= 0 else ' ****')


      # Tuple of thresholds - wide illum, narrow sky BG %, narrow illum %
      # When receiving, poke the new values into the collecor
      if "R" in telemetry:
        if telemetry["R"][0] != self.Collector.WideAngleIllumPercent:
          self.Collector.WideAngleIllumPercent = telemetry["R"][0]
          self.ui.WideIllumPercentLineEdit.setText(str(self.Collector.WideAngleIllumPercent))
        if telemetry["R"][1] != self.Collector.NarrowSkyBackgroundPercent:
          self.Collector.NarrowSkyBackgroundPercent = telemetry["R"][1]
          self.ui.NarrowSkyBackgroundLineEdit.setText(str(self.Collector.NarrowSkyBackgroundPercent))
        if telemetry["R"][2] != self.Collector.NarrowIlluminationPercent:
          self.Collector.NarrowIlluminationPercent = telemetry["R"][2]
          self.ui.NarrowIllumPercentLineEdit.setText(str(self.Collector.NarrowIlluminationPercent))

      # Servo error
      if "E" in telemetry:
        # Update servo error
        pass

      # Narrow sky background
      if "G" in telemetry:
        # Update narrow sky background in counts
        self.ui.ImpliedSkyBGLabel.setText(f'Implied Sky BG: {telemetry["G"]:5d}')

      # Total intensity on wide-angle detector
      if "I" in telemetry:
        self.ui.WideIntensity.setText(f'{telemetry["I"][1]:3d}%  {telemetry["I"][0]:5d}')

      # Narrow mode status
      if "IsNarrowMode" in telemetry:
        GroupBoxStyleStringGray = "QGroupBox { color: gray; }"
        GroupBoxStyleStringBold = ""
        if telemetry["IsNarrowMode"]:
          self.ui.NarrowGroup.setStyleSheet(GroupBoxStyleStringBold)
          self.ui.WideGroup.  setStyleSheet(GroupBoxStyleStringGray)
        else:
          self.ui.NarrowGroup.setStyleSheet(GroupBoxStyleStringGray)
          self.ui.WideGroup.  setStyleSheet(GroupBoxStyleStringBold)

      # Narrow angle threshold
      if "NarrowAngleThreshold" in telemetry:
        msg = f'NarrowThresh:  {telemetry["NarrowAngleThreshold"]:5d}'
        self.ui.NarrowThresholdLabel.setText(msg)

      # Limit states
      if "LimitStates" in telemetry:
        self.ui.AzLimLowButton .setChecked(telemetry["LimitStates"][0])
        self.ui.AzLimHighButton.setChecked(telemetry["LimitStates"][1])
        self.ui.ElLimLowButton .setChecked(telemetry["LimitStates"][2])
        self.ui.ElLimHighButton.setChecked(telemetry["LimitStates"][3])
        # Home is element 4, not shown on GUI

      # Servo mode
      if "PositionMode" in telemetry:
        if telemetry["PositionMode"][0] == "V":
          self.ui.AzGroup.setTitle('Az - VelMode')
        else:
          self.ui.AzGroup.setTitle('Az - PosMode')

        if telemetry["PositionMode"][1] == "V":
          self.ui.ElGroup.setTitle('El - VelMode')
        else:
          self.ui.ElGroup.setTitle('El - PosMode')


      # Spot coordinates
      if "C" in telemetry:
        self.ui.XPos.setText(f'{telemetry["C"][0]:+.2f}')
        self.ui.YPos.setText(f'{telemetry["C"][1]:+.2f}')

      # Collector mode number
      if "ModeNum" in telemetry:
        # This one we don't display. It gets passed to the marquee as a signal by tCollector
        #if self.CollectorState != telemetry["ModeNum"]:
        #  self.CollectorState = telemetry["ModeNum"]:
        pass

      # Collector mode string
      if "ModeString" in telemetry:
        self.ui.State.setText('State: ' + telemetry["ModeString"])

    except Exception as e:
      # Handle unexpected errors
      print(f"Collectorpane::UpdateTelemetry: Error processing telemetry dict: {e}:")



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
    #layout.addWidget(next(Collector_iterator), 0,0)

    PaneGeometry    = self.CollectorPanes[0].geometry()
    CurrentGeometry = self.geometry()

    self.resize(50+3*PaneGeometry.width(), 50+3.2*PaneGeometry.height())

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
    # print("CollectorWindow close event")
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
