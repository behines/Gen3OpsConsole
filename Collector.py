#######################################################
# tCollector - class for interacting with the Collector's serial port
#
# Can send commands and receive telemetry
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
from PySide6.QtCore       import Signal, QDateTime, QTime, QTimeZone, QThread, QTimer, QProcess
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

from SerialPort        import tAutoOpenSerialWholeLine, tSerialConnectProbe
from PowerControl      import tPowerControl
from Utilities         import tActiveObject
from ConfigInfo        import *
import re


##########################################################################################
##########################################################################################
##########################################################################################
# tCollector  - Class that implements collector I/O
#
# At construction, the AutoOpenSerial device is created but not yet started.  This gives other
# objects a chance to connect to its signals before it starts up.  (The app is single-threaded;
# the device is not moved to a worker thread.)
# 
#
# When telemetry is emitted as a dictionary, it takes on this form
#  Key                 Value
# -----                -----
#   P                  Tuple of az/el motor positions
#   V                  Tuple of az/el motor velocities
#   N                  Tuple of the four narrow-angle readings
#   W                  Tuple of the four wide-angle readings
#   R                  Tuple of thresholds - wide illum, narrow sky BG %, narrow illum %
#   E                  Servo error, either velocity or position error depending on servo mode
#   G                  Narrow sky background in counts
#   I                  Tuple of Total intensity on wide-angle detector in counts, and as a percentage
# IsNarrowMode         True if in narrow-angle mode, else wide
# NarrowAngleThreshold Threshold for switching to narrow angle
# LimitStates          integer[5] - az low, az high, el low, el high, home
#                      0 none, 1 soft, 2 hard, 3 soft+hard
# PositionMode         boolean - true if in positoin mode, false if velocity mode
#   C                  Spot coordinate x-y (float)
#   J                  Processor temperature in degrees C
# ModeNum              Current mode of the collector (integer)
# ModeString           Current mode of the collecor (string)
# Timestring           Current time as a string HH:MM:SS
#

class tCollector(tActiveObject):
  
  # CollectorOnlineStateUpdate = Signal(bool)
  PortOpenStateChange        = Signal(bool)
  # Host-side serial connection state for the pane: 'connected' | 'offline' | 'hung'.
  # 'hung' = the guarded connect-probe timed out, i.e. QSerialPort.open()/close() is blocking on
  # a wedged/half-powered board (recover with a USB power-cycle).
  ConnectionStateUpdate      = Signal(str, str)

  # Telemetry signals
  ReleaseStringReceived      = Signal(str)
  TextLineReceived           = Signal(str)       # a non-telemetry line, should just be sent to the console
  CollectorStateUpdate       = Signal(str, CollectorNativeStates)  # New collector state as an int.  First arg is the collector name ('1A', '1B', etc.)
  # Signal to emit parsed telemetry data as a dictionary
  TelemetryUpdate            = Signal(dict)

  # Commands
  DoOff                      = Signal()
  DoHome                     = Signal()
  DoTrack                    = Signal()
  DoStow                     = Signal()
  DoFlat                     = Signal()
  DoSetTime                  = Signal()
  DoMotStatus                = Signal()
  DoReboot                   = Signal()
  DoReconnect                = Signal()
  DoDumpNvSettings           = Signal()

  UpdateThresholds           = Signal()
  

  ###############################################
  # Constructor part 1
  #
  # Part 2 of "construction" occurs when our owner calls "Start".  The space between
  # construction and starting gives the owner a chance to connect to signals.
  # 
  # INPUTS:
  #
  #   
  #     

  def __init__(self, collectorName, portName, boardSerial, baud, parent=None):
    super().__init__(COLLECTOR_RETRY_TIMEOUT_SECS * 1000, parent)   # tActiveObject constructor

    # NOTE: single-threaded app - the recursive mutex that used to guard this device is
    # removed (see the fuller note in tAgilent.__init__).

    self.CollectorName  = collectorName
    self.PortName       = portName
    self.BoardSerial    = boardSerial
    self.baud           = baud
    self.bInit          = False
    self.CollectorState = CollectorNativeStates.UNKNOWN
    self.CpuTemp        = None
    self.bUsbPowerState = not PROJECT_CONFIG.bHasUsbPowerRelay
    self.LastRebootRequestMsecs  = 0
    self.LastRebootAcceptedMsecs = 0
    self.ReleaseString           = ""

    # In-flight async picotool reboot processes (QProcess).  Tracked so the kill timer can
    # tell a still-running process from one that already finished and was cleaned up.
    self._PicotoolProcesses      = set()

    # ----- Guarded serial-connect state machine (see SerialPort.py header for WHY) -----
    # All serial open/close is guarded by a probe thread so a wedged board can't freeze the GUI.
    self._probe          = None    # in-flight tSerialConnectProbe, or None
    self._portWentBad    = False   # a connected port went offline -> abandon it + reconnect
    self._connHung       = False   # last probe timed out (board wedged) -> red HUNG annunciator
    self._probeFailCount = 0       # consecutive "port present but can't open" probe failures
    self._abandonedPorts = []      # wedged port objects we keep referenced so their (blocking)
                                   # close() never runs; the OS handle frees when the device
                                   # de-enumerates (USB power-cycle / reset)

    # These are cached values.  When they change (via a GUI event), we send a command to the collector
    self.WideAngleIllumPercent      = 0
    self.NarrowSkyBackgroundPercent = 0
    self.NarrowIlluminationPercent  = 0

    #try:

    # Connect signals to methods
    self.DoOff            .connect(self.Off            )
    self.DoHome           .connect(self.Home           )
    self.DoTrack          .connect(self.Track          )
    self.DoStow           .connect(self.Stow           )
    self.DoFlat           .connect(self.Flat           )
    self.DoSetTime        .connect(self.SetTimeToNow   )
    self.DoMotStatus      .connect(self.MotStatus      )
    self.DoReboot         .connect(self.Reboot         )
    self.DoReconnect      .connect(self.Reconnect      )
    self.DoDumpNvSettings .connect(self.DumpNvSettings )

    self.UpdateThresholds.connect(self.SendThresholdPercentages)

    # Initialize sunrise and sunset to just before midnight.  These will get overwritten shortly 
    # when the NIP sequencer actually computes them, but for now this will be "in the future".
    timezone     = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    self.sunrise = QDateTime.currentDateTime(timezone)
    self.sunrise.setTime(QTime(23, 59))  # Set time to 11:59 PM
    self.sunset  = self.sunrise

    # To avoid repeated error messages
    self.LastSerialPortErrorTime = {}

  ###############################################
  # Destructor
  # 
  # This will be called when the thread exits
  #     

  def __del__(self):
    if self.SerialPort.IsOpen():
      self.SerialPort.close()


  ###############################################
  # HandleSerialPortError 
  # 
  # 

  def HandleSerialPortError(self, error):
    if error != QSerialPort.NoError:
      timezone = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
      current_time = QDateTime.currentDateTime(timezone)

      # We keep an associative array of the last known time for each type of serial port error 
      # Check if we have an entry
      secsSinceLastError = 10000000
      if error in self.LastSerialPortErrorTime:
        secsSinceLastError = self.LastSerialPortErrorTime[error].secsTo(current_time)

      self.LastSerialPortErrorTime[error] = current_time

      if secsSinceLastError > 100:
        print(f"Collector {self.CollectorName}: Serial port error: {error}")
        # Handle error (e.g., reconnect, notify user, etc.)


  ###############################################
  # SetUsbPowerDevice - informs the collector of the USB power device so that it can be aware of USB power events
  #

  def SetUsbPowerDevice(self, UsbHubPowerDevice: tPowerControl, bCurrentUsbPowerState):
    if UsbHubPowerDevice is None:
      self.bUsbPowerState = True
    else:
      self.bUsbPowerState = bCurrentUsbPowerState
      UsbHubPowerDevice.PowerRelayStateUpdate.connect(self.UsbPowerStateUpdateEvent)


  ###############################################
  # UsbPowerStateUpdateEvent - Called whenever USB power goes on or off
  #

  def UsbPowerStateUpdateEvent(self, bNewPowerState):
    self.bUsbPowerState = bNewPowerState


  ###############################################
  # Start 
  # 
  # Call this after construction to start the collector's periodic task running.
  # This also includes opening the serial port.
  #     
  
  def Start(self, SunriseSunsetUpdateSignal):

    # Connect to sunrise and sunset updates
    SunriseSunsetUpdateSignal.connect(self.UpdateSunriseSunset)

    self.MissingTelemetryCount = 0

    # Create the (initially closed) serial port and wire its signals.  The port is NOT opened
    # here - opening is driven by the guarded connect-probe (see _BeginConnect) so a wedged board
    # can never block the GUI thread inside QSerialPort.open().
    self._CreateAndWireFreshPort()

    # Inform the CollectorPane of the initial (offline) state.
    self.OnlineStatusUpdate(self.SerialPort.IsOpen())

    # Kick off the guarded connect right away (a no-op in --safe mode).
    self._BeginConnect()

    # And start the periodic task running (drives reconnects / health checks).
    super().Start()


  ###############################################
  # _CreateAndWireFreshPort - Make a brand-new serial-port object and connect its signals
  #
  # Used at startup and whenever we abandon a wedged port and reconnect.  Each fresh object
  # self-wires its own readyRead->line-assembly; here we wire the collector-level signals.
  #

  def _CreateAndWireFreshPort(self):
    self.SerialPort = tAutoOpenSerialWholeLine(self.PortName, baudrate=self.baud,
                                               readBufSize=COLLECTOR_RX_BUFFER_SIZE, parent=self)
    self.SerialPort.bPrintDiag = False
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)
    self.SerialPort.readyLine          .connect(self.ProcessLineOfOutput)
    self.SerialPort.errorOccurred      .connect(self.HandleSerialPortError)


  ###############################################
  # _BeginConnect - Start a guarded (non-blocking) connect via the probe
  #
  # We never open the real port directly from the GUI thread (open() can block on a wedged
  # board).  Instead we probe the port on a worker thread; _OnProbeFinished opens the real port
  # only if the probe proved it opens+closes fast.  No-op in --safe mode, while a probe is
  # already running, or if we're already connected.
  #

  def _BeginConnect(self):
    if SAFE_MODE or self._probe is not None or self.SerialPort.IsOpen():
      return
    self._probe = tSerialConnectProbe(self.PortName, self.baud, SERIAL_CONNECT_PROBE_TIMEOUT_SECS, parent=self)
    self._probe.finished.connect(self._OnProbeFinished)
    self._probe.Start()


  ###############################################
  # _OnProbeFinished - Act on the probe result: 'ok' / 'fail' / 'timeout'
  #

  def _OnProbeFinished(self, result):
    probe = self._probe
    self._probe = None
    if probe is not None:
      probe.deleteLater()

    if result == 'ok':
      # Device opened+closed fast on the probe -> safe to open the real port on the GUI thread
      # (it will be fast too).  AttemptOpenIfNeeded emits PortOpenStateChange(True) on success ->
      # OnlineStatusUpdate -> bInit True + InitializeConnection.
      self._probeFailCount = 0
      self._SetHung(False)
      self.SerialPort.AttemptOpenIfNeeded()

    elif result == 'timeout':
      # open()/close() is BLOCKED on the worker thread -> the board is wedged-but-present.
      # Declare HUNG (red); recovery is a USB power-cycle.  We retry on later cycles, and once the
      # device finally recovers the next probe returns 'ok' and we reconnect.
      self._SetHung(True)

    else:  # 'fail'
      # Couldn't open quickly.  If the COM port isn't even present, the board is rebooting /
      # unplugged - normal, stay quietly offline.  If it IS present but we still can't open it
      # (held by an abandoned wedged handle, or wedged), call it HUNG after a few tries so a brief
      # mid-reboot blip doesn't flash red.
      if self._PortIsPresent():
        self._probeFailCount += 1
        self._SetHung(self._probeFailCount >= SERIAL_HUNG_FAIL_THRESHOLD)
      else:
        self._probeFailCount = 0
        self._SetHung(False)


  ###############################################
  # _PortIsPresent - True if this collector's COM port currently exists in the OS
  #
  # Absent  -> the device is rebooting / unplugged (normal, will reconnect).
  # Present -> the device is enumerated; if we still can't open it, it's wedged.
  #

  def _PortIsPresent(self):
    return self.PortName in [p.portName() for p in QSerialPortInfo.availablePorts()]


  ###############################################
  # _AbandonAndConnectFresh - Drop a stale/wedged port (without closing it) and reconnect fresh
  #
  # The current port object went offline/errored, and its OS handle may still be held by a wedged
  # device.  A native close() to recover it would block the GUI thread - so we do NOT close it.
  # We ABANDON it: stop listening to it, and keep a reference so its destructor (which would call
  # the blocking close()) never runs.  Then we bring up a brand-new port object and probe-connect
  # through it.  The abandoned handle is released for free when the device de-enumerates (USB
  # power-cycle / reset).  Cost: a tiny intentional leak per wedge - it can't hang, which is the
  # whole point.
  #

  def _AbandonAndConnectFresh(self):
    old = self.SerialPort
    if old is not None:
      old.blockSignals(True)
      try:
        old.PortOpenStateChange.disconnect(self.OnlineStatusUpdate)
        old.readyLine          .disconnect(self.ProcessLineOfOutput)
        old.errorOccurred      .disconnect(self.HandleSerialPortError)
      except (RuntimeError, TypeError):
        pass
      self._abandonedPorts.append(old)

    # We're offline now; grey the pane.
    self.bInit = False
    self.PortOpenStateChange.emit(False)

    self._CreateAndWireFreshPort()
    self._BeginConnect()


  ###############################################
  # _SetHung - Set/clear the HUNG (red) connection state, announcing changes to the pane
  #

  def _SetHung(self, bHung):
    if bHung == self._connHung:
      return
    self._connHung = bHung
    if bHung:
      print(f'tCollector: Collector {self.CollectorName} appears HUNG (serial port wedged - '
            f'open/close blocked).  Recover with a USB power-cycle.', flush=True)
      self.ConnectionStateUpdate.emit(self.CollectorName, 'hung')
    else:
      # Clear the HUNG indication; reflect current connectivity.
      self.ConnectionStateUpdate.emit(self.CollectorName, 'connected' if self.bInit else 'offline')


  ###############################################
  # UpdateSunriseSunset - Called whenever a new sunrise and sunset are computed 
  # 
  # Call this after construction to start the collector's periodic task running.
  # This also includes opening the serial port.
  #   

  def UpdateSunriseSunset(self, Sunrise: QDateTime, Sunset: QDateTime):
    self.sunrise = Sunrise
    self.sunset  = Sunset
    self.SetTimeToNow()          # Inform the collector


  ###############################################
  # InitializeConnection - Configures a newly connected collector for I/O
  # 
  # This method simply sends the "Telemetry on" command
  #

  def InitializeConnection(self):
    if not self.SerialPort.IsOpen():
      print(f'tCollector: ERROR: Collector {self.CollectorName} offline in InitializeConnection', flush=True)
    else:
      # print(f'tCollector: INFO: Collector {self.CollectorName} back online', flush=True)
      self.CollectorState = CollectorNativeStates.UNKNOWN
      self.FlushCommandInput()
      self.SetTimeToNow()
      self.SetTelemetryOnOff(True)
      self.About()
    QThread.msleep(10)   # Give the output time to flush


  ###############################################
  # Reconnect - Closes and reopens/reinits a port
  # 
  # 
  #

  def Reconnect(self):
    # User-requested reconnect (Reconnect button).  Abandon the current port and probe-reconnect
    # a fresh one - we never call the blocking close() to recover (it can hang on a wedged board).
    self._AbandonAndConnectFresh()


  ###############################################
  # OnlineStatusUpdate - Called when the serial port connection state changes
  # 
  # This method sends the "Telemetry on" command
  #

  def OnlineStatusUpdate(self, bState):
    bOldState  = self.bInit
    self.bInit = self.SerialPort.IsOpen()

    # If we were connected and just went offline, this port object is now stale: its OS handle
    # may still be held by a wedged device, and a native close() would block the GUI thread.
    # Flag it so PeriodicMethod abandons it and probe-reconnects a fresh port (instead of ever
    # calling the blocking close()).
    if bOldState and not self.bInit:
      self._portWentBad = True

    # If the connection is offline, mark the collector state unknown
    if not self.bInit:
      self.CollectorState = CollectorNativeStates.UNKNOWN
      self.CollectorStateUpdate.emit(self.CollectorName, self.CollectorState)
      if not self._connHung:
        self.ConnectionStateUpdate.emit(self.CollectorName, 'offline')

    # If the connection has just come online, initialize it
    if self.bInit and not bOldState:
      self._SetHung(False)
      self.ConnectionStateUpdate.emit(self.CollectorName, 'connected')
      self.InitializeConnection()

    # Inform the CollectorPane
    self.PortOpenStateChange.emit(self.bInit)


  ###############################################
  # PeriodicMethod
  # 
  # This method just attempts to periodically reopen the port if it's not open
  #

  def PeriodicMethod(self):
    # If USB power is off, the ports don't even exist - do nothing.
    if not self.bUsbPowerState:
      return

    # If we're connected but telemetry has stopped for too long, the board has either rebooted/
    # reset (we must reconnect) or wedged (-> HUNG).  We do NOT pre-judge which: we abandon this
    # port and probe-reconnect a fresh one, and the guarded probe sorts it out.  (Closing the
    # current open port to "reopen" it - the old behaviour - is exactly what hung the app, so we
    # never do that.)
    if self.SerialPort.IsOpen() and self.MissingTelemetryCount >= COLLECTOR_MISSING_TELEM_REOPEN_THRESHOLD:
      self._portWentBad = True

    if self._probe is None:
      # No probe in flight - advance the connection.
      if self._portWentBad:
        self._portWentBad = False
        self._AbandonAndConnectFresh()       # abandon the stale/wedged port, then fresh + probe
      elif not self.SerialPort.IsOpen():
        self._BeginConnect()                 # initial connect, or retry of an absent/wedged port

    # Count the missing-telemetry interval.  ProcessLineOfOutput re-zeros it on any received line.
    self.MissingTelemetryCount = self.MissingTelemetryCount + 1
  
  
  ###############################################
  # (Removed __enter__/__exit__ context-manager locking - single-threaded app, see __init__.)


  ###############################################
  # IsInit - true if class initialized and is connected to the target
  # 
  # INPUTS:
  #     

  def IsInit(self):
    return self.bInit
  

  ###############################################
  # ProcessLineOfOutput
  # 
  # Processes lines of text as they arrive from the collector
  #
  # If the line is not a telemetry burst, it is emitted as a "TextLineReceived"
  # signal.  If it is telemetry, it is parsed into a dictionary and emitted.
  #     

  def ProcessLineOfOutput(self, Line: str):
    self.MissingTelemetryCount = 0

    # Strip a leading "> " prompt if present so the line below still recognizes telemetry
    if Line.startswith("> "):
      Line = Line[2:]

    if Line.startswith("***COLLECTOR ONLINE***"):
      self.InitializeConnection()
      return
    
    match = re.search(r'\b(\d{6}_\d{4})\b', Line)
    if match:
      self.ReleaseString = match.group(1)
      self.ReleaseStringReceived.emit(self.ReleaseString)

    if Line.startswith("Rebooting..."):
      self.LastRebootAcceptedMsecs = QDateTime.currentMSecsSinceEpoch()
    
    if not Line.startswith("TEL:"):
      # Emit signal for non-TEL line
      self.TextLineReceived.emit(Line)
      return

    # Remove "TEL:" and parse the telemetry line
    try:
      #if self.CollectorName == "4B": 
        #self.TextLineReceived.emit(Line)
      #  print(Line)
      Line = Line[4:]  # Remove "TEL:"
      fields = Line.strip().split(":")  # Split into segments FieldTagged by single-character field names

      parsed_data = {}
      for field in fields:
        if len(field) < 2:
          continue  # Skip malformed fields
        
        FieldTag   = field[0]   # First character is the Field Tag
        FieldValue = field[1:]  # Remaining is the value(s)
        
        # Parse fields based on content
        if FieldTag in "PVNWREI":
          # Multiple signed numbers separated by commas.  "map" here simply applies the "int" function to each of the split strings
          parsed_data[FieldTag] = tuple(map(int, FieldValue.split(",")))

        elif FieldTag in "GJ":
          # Single number fields (integer)
          parsed_data[FieldTag] = int(FieldValue)
          if FieldTag == "J":
            self.CpuTemp = int(FieldValue)

        elif FieldTag == "H":
          # First character is 'N' or 'W', followed by a 5-digit integer
          IsNarrowMode = (FieldValue[0] == "N")
          NarrowAngleThreshold = int(FieldValue[1:])  # Remaining characters are the threshold
          parsed_data["IsNarrowMode"        ] = IsNarrowMode
          parsed_data["NarrowAngleThreshold"] = NarrowAngleThreshold

        elif FieldTag == "L":
          # Five characters are 0-3 limit states: 0 none, 1 soft, 2 hard, 3 both
          LimitStates = [int(char) for char in FieldValue]
          parsed_data["LimitStates"] = LimitStates

        elif FieldTag == "S":
          # Characters are 'V' or 'P', converted to a boolean array for motor modes
          bPositionMode = [char == "P" for char in FieldValue]
          parsed_data["PositionMode"] = bPositionMode

        elif FieldTag == "C":
          # Multiple signed numbers separated by commas.  "map" here simply applies the "int" function to each of the split strings
          parsed_data[FieldTag] = tuple(map(float, FieldValue.split(",")))

        elif FieldTag == "M":
          # First two characters are the integer ModeNum
          ModeNum = int(FieldValue[:2])
          # Remaining part after the comma is the ModeString
          ModeString = FieldValue[3:]  # Skip the comma at index 2
          parsed_data["ModeNum"   ] = ModeNum
          parsed_data["ModeString"] = ModeString

          if ModeNum != self.CollectorState.value:   # CollectorState is an enum
            self.CollectorState = CollectorNativeStates(ModeNum)
            self.CollectorStateUpdate.emit(self.CollectorName, self.CollectorState)

        elif FieldTag == "T":
          # Parse Thhmmss and format as "hh:mm:ss"
          hours      = FieldValue[ :2]
          minutes    = FieldValue[2:4]
          seconds    = FieldValue[4:6]
          TimeString = f"{hours}:{minutes}:{seconds}"
          parsed_data["TimeString"] = TimeString

      # Emit signal with parsed telemetry data
      self.TelemetryUpdate.emit(parsed_data)

    except Exception as e:
      # Handle unexpected errors
      #print(f"Error parsing TEL line: {e}:")
      #print(Line)
      pass


  ###############################################
  # _SendCommand
  #
  # Sends a Gen3 collector command.
  #

  def _SendCommand(self, CommandName, *args):
    CommandParts = [CommandName] + [str(arg) for arg in args]
    Command      = " ".join(CommandParts) + "\r"

    result = self.SerialPort.write(Command)

    if result != len(Command):
      return -1

    return result


  ###############################################
  # FlushInput
  # 
  # Cancels any pending line-editor input and submits a blank line to get back in sync.
  #     

  def FlushCommandInput(self):
    # Ctrl-C clears any partial command without executing it; CR then submits a blank line.
    FlushString = "\x03\r"
    result = self.SerialPort.write(FlushString)

    if result != len(FlushString):
      print('Error flushing input for collector ', self.CollectorName, flush=True)
      return -1  
    
    return 0

  
  ###############################################
  # About - requests the collector to report its release string
  #

  def About(self):
    self._SendCommand("About")


  ###############################################
  # Stow
  #
  # Comamnds the collector to Stow
  #

  def Stow(self):
    result = self._SendCommand("Stow")

    if result > 0:
      print ('Stowing collector ', self.CollectorName)
      self.bResponded = True
      return 0
    else:
      print('Could not stow ', self.CollectorName)
      return -1  


  ###############################################
  # Flat
  # 
  # Comamnds the collector to Flat
  #     

  def Flat(self):
    result = self._SendCommand("Flat")

    if result > 0:
      print ('Flattening collector ', self.CollectorName)
      self.bResponded = True
      return 0
    else:
      print('Could not flatten ', self.CollectorName)
      return -1  


  ###############################################
  # Track
  # 
  # Comamnds the collector to Track
  #     

  def Track(self):
    result = self._SendCommand("TrackOn")

    if result > 0:
      print ('Tracking collector ', self.CollectorName)
      self.bResponded = True
      return 0
    else:
      print('Could not track ', self.CollectorName)
      return -1
    

  ###############################################
  # Home
  # 
  # Comamnds the collector to Home
  #     

  def Home(self):
    result = self._SendCommand("Home")

    if result > 0:
      print ('Homing collector ', self.CollectorName)
      self.bResponded = True
      return 0
    else:
      print('Could not home ', self.CollectorName)
      return -1
    

  ###############################################
  # Off
  # 
  # Comamnds the collector to turn off
  #     

  def Off(self):
    print('Sending Off command')
    result = self._SendCommand("TrackOff")

    if result > 0:
      print ('Turning off collector ', self.CollectorName)
      self.bResponded = True
      return 0
    else:
      print('Could not turn off ', self.CollectorName)
      return -1


  ###############################################
  # Responded
  # 
  # 
  #     

  def Responded(self):
    return self.bResponded
  

  ###############################################
  # SetTimeToNow()
  # 
  #  Sets the time on the collector
  #     

  def SetTimeToNow(self):
    timezone = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    #if not isinstance(timezone, QTimeZone):
    #  raise TypeError("timezone must be of type QTimeZone")

    current_time = self._ToStandardTime(QDateTime.currentDateTime(timezone), timezone)
    sunrise      = self._ToStandardTime(self.sunrise, timezone)
    sunset       = self._ToStandardTime(self.sunset,  timezone)

    # Format to HHMMSSt (with 0.1 second resolution) and YYMMDD date
    CurrentTimeString = current_time.toString('HHmmss') + f"{int(current_time.time().msec() / 100)}"
    CurrentDateString = current_time.toString('yyMMdd')

    result = self._SendCommand("SetTime", CurrentTimeString, CurrentDateString, sunrise.toString('hhmm'), sunset.toString('hhmm'))

    if result < 0:
      print ('Could not set time for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0


  ###############################################
  # _ToStandardTime()
  #
  #  Converts a site-local QDateTime to standard clock time by removing any DST offset.
  #

  def _ToStandardTime(self, date_time: QDateTime, timezone: QTimeZone):
    site_time = date_time.toTimeZone(timezone)
    return site_time.addSecs(-timezone.daylightTimeOffset(site_time))


  ###############################################
  # MotStatus - sends a pair of commands to cause the collector to print motor status info
  # 
  #     

  def MotStatus(self):
    result = self._SendCommand("Status")

    if result < 0:
      return -1    

    result = self._SendCommand("Tuning")

    if result < 0:
      return -1    

    self.bResponded = True
    return 0

  ###############################################
  # DumpNvSettings - requests the collector to dump its NV settings
  #

  def DumpNvSettings(self):
    self._SendCommand("DumpNvSettings")


  ###############################################
  # Reboot - asks the collector to reboot, then falls back to picotool
  # 
  #     

  def Reboot(self, bForced=False):
    # Sequencer-driven reboots silently skip absent boards; user-clicked reboots
    # always try (picotool can talk to the board even if the COM port is wedged)
    if not bForced and not self.SerialPort.IsOpen():
      return 0
    print(f'Rebooting {self.CollectorName}')
    self.LastRebootRequestMsecs = QDateTime.currentMSecsSinceEpoch()
    self._SendCommand("Reboot")
    QTimer.singleShot(2000, self._PicotoolRebootIfNeeded)
    self.bResponded = True
    return 0


  ###############################################
  # _PicotoolRebootIfNeeded
  #
  # Uses picotool if the embedded Reboot command did not receive an acknowledgement.
  #

  def _PicotoolRebootIfNeeded(self):
    if self.LastRebootAcceptedMsecs >= self.LastRebootRequestMsecs:
      return

    if self.BoardSerial is None:
      print(f'Could not reboot {self.CollectorName}: reboot serial not configured', flush=True)
      return

    # Don't stack a second picotool on this board if one is still in flight (e.g. the user
    # mashes Reboot) - concurrent picotools would contend for the same USB device.  Each
    # tCollector only ever reboots its own board, so any in-flight process means a reboot is
    # already running.
    if self._PicotoolProcesses:
      print(f'Picotool reboot for {self.CollectorName} skipped: a reboot is already in progress', flush=True)
      return

    print(f'Picotool rebooting {self.CollectorName} ({self.BoardSerial})', flush=True)

    # Launch picotool asynchronously via QProcess.  A blocking subprocess.run() would park
    # this (GUI) thread until picotool exits, and picotool can wait indefinitely on a flaky
    # or half-enumerated board, freezing the entire app with no way to even pause it.
    # QProcess.start() returns immediately and reports completion through a signal, so a
    # wedged picotool just sits harmlessly in the background.  This stays on the GUI event
    # loop - no worker thread - so it does not disturb Qt's single-threaded serial model.
    PicotoolProcess = QProcess(self)
    self._PicotoolProcesses.add(PicotoolProcess)
    PicotoolProcess.finished.connect(
      lambda exitCode, exitStatus, proc=PicotoolProcess: self._PicotoolRebootFinished(proc, exitCode, exitStatus))
    # If picotool can't even launch, finished() never fires - reap it on errorOccurred so
    # the QProcess can't linger in the set forever.
    PicotoolProcess.errorOccurred.connect(
      lambda error, proc=PicotoolProcess: self._PicotoolRebootError(proc, error))
    PicotoolProcess.start(PROJECT_CONFIG.PicotoolPath, ["reboot", "--ser", self.BoardSerial, "-f"])

    # Hygiene backstop (not the freeze fix - QProcess already prevents that): if picotool
    # wedges on a bad board, reap it after a generous timeout so stuck processes don't
    # accumulate holding that board's USB handle.
    QTimer.singleShot(1000 * PICOTOOL_REBOOT_TIMEOUT_SECS,
                      lambda proc=PicotoolProcess: self._PicotoolRebootKillIfRunning(proc))


  ###############################################
  # _PicotoolRebootFinished - Logs the result of an async picotool reboot and cleans up
  #
  # INPUTS:
  #   PicotoolProcess - the QProcess that finished
  #   exitCode        - picotool's exit code (0 on success)
  #   exitStatus      - QProcess.ExitStatus (CrashExit if we killed it or it crashed)
  #

  def _PicotoolRebootFinished(self, PicotoolProcess, exitCode, exitStatus):
    # Idempotent: errorOccurred may have already cleaned this one up.
    if PicotoolProcess not in self._PicotoolProcesses:
      return
    if exitStatus == QProcess.ExitStatus.CrashExit:
      # We killed it (timeout backstop) or it crashed; the exit code is meaningless here.
      print(f'Picotool reboot for {self.CollectorName} did not exit cleanly (killed or crashed)', flush=True)
    elif exitCode != 0:
      errText = bytes(PicotoolProcess.readAllStandardError()).decode('utf-8', errors='ignore').strip()
      outText = bytes(PicotoolProcess.readAllStandardOutput()).decode('utf-8', errors='ignore').strip()
      detail  = ' '.join(t for t in (errText, outText) if t)
      print(f'Picotool reboot failed for {self.CollectorName} (exit {exitCode}): {detail}', flush=True)
    self._PicotoolProcesses.discard(PicotoolProcess)
    PicotoolProcess.deleteLater()


  ###############################################
  # _PicotoolRebootError - Reaps a picotool process that failed to launch
  #
  # finished() does not fire when the process never starts, so we clean up here.  Other
  # errors (e.g. a crash after a normal start) are left to finished().
  #
  # INPUTS:
  #   PicotoolProcess - the QProcess that reported an error
  #   error           - QProcess.ProcessError
  #

  def _PicotoolRebootError(self, PicotoolProcess, error):
    if PicotoolProcess not in self._PicotoolProcesses:
      return
    if error == QProcess.ProcessError.FailedToStart:
      print(f'Picotool could not be launched for {self.CollectorName}', flush=True)
      self._PicotoolProcesses.discard(PicotoolProcess)
      PicotoolProcess.deleteLater()


  ###############################################
  # _PicotoolRebootKillIfRunning - Reaps a picotool process that wedged on a flaky board
  #
  # INPUTS:
  #   PicotoolProcess - the QProcess to check and possibly kill
  #

  def _PicotoolRebootKillIfRunning(self, PicotoolProcess):
    # If it already finished, it has been removed from the set and cleaned up; do not touch
    # the (possibly deleted) object.
    if PicotoolProcess not in self._PicotoolProcesses:
      return

    print(f'Picotool reboot for {self.CollectorName} timed out after '
          f'{PICOTOOL_REBOOT_TIMEOUT_SECS}s, killing', flush=True)
    PicotoolProcess.kill()


  ###############################################
  # SetTelemetryOnOff()
  # 
  # Turns telemetry on or off
  #
  # INPUTS:
  #   bTelemetryOn - desired state
  #     

  def SetTelemetryOnOff(self, bTelemetryOn : bool):
    cmd = "TelOn" if bTelemetryOn else "TelOff"

    result = self._SendCommand(cmd)

    if result < 0:
      print ('Could not set telemetry on state for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0



  ###############################################
  # SetThresholdPercentages()
  # 
  # Sends the three tracking threshold percentages
  #     

  def SendThresholdPercentages(self):
    result = self._SendCommand("Thresh",
                               self.WideAngleIllumPercent,
                               self.NarrowSkyBackgroundPercent,
                               self.NarrowIlluminationPercent)

    if result < 0:
      print ('Could not set threshold percentages for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0
    

  ###############################################
  # SetWideIllumPercentThreshold
  # 
  # Thread-safe method for adjusting threshold
  #     

  def SetWideIllumPercentThreshold(self, WideIllumPercent):
    self.WideAngleIllumPercent = WideIllumPercent
    self.UpdateThresholds.emit()


  ###############################################
  # SetNarrowSkyBackgroundPercentThreshold
  # 
  # Thread-safe method for adjusting threshold
  #     

  def SetNarrowSkyBackgroundPercentThreshold(self, NarrowBgPercent):
    self.NarrowSkyBackgroundPercent = NarrowBgPercent
    self.UpdateThresholds.emit()


  ###############################################
  # SetNarrowIllumPercentThreshold
  # 
  # Thread-safe method for adjusting threshold
  #     

  def SetNarrowIllumPercentThreshold(self, NarrowIllumPercent):
    self.NarrowIlluminationPercent = NarrowIllumPercent
    self.UpdateThresholds.emit()


  ###############################################
  # IsTrackingOrAttemptingToTrack
  # 
  # True if the collector will try to track if conditions are right
  #     

  def IsTrackingOrAttemptingToTrack(self):
    # In-progress homing, in-progress acquire (including the recoverable
    # ACQ_ERROR), and any tracking sub-state.  Homing error states (HOME_*_ERROR)
    # are intentionally excluded — those are dead ends, not active attempts.
    bIsTrackingState = self.CollectorState in [
      CollectorNativeStates.HOME_OFFSET              ,
      CollectorNativeStates.HOME_AZ_NEG              ,
      CollectorNativeStates.HOME_ELEVATION_LOW       ,
      CollectorNativeStates.ACQ_BEGIN                ,
      CollectorNativeStates.ACQ_INITIAL_POSITION_WAIT,
      CollectorNativeStates.ACQ_AZ                   ,
      CollectorNativeStates.ACQ_ERROR                ,
      CollectorNativeStates.ACQUIRE                  ,
      CollectorNativeStates.WAITING_FOR_SUN          ,
      CollectorNativeStates.TRACK                    ,
      CollectorNativeStates.DEAD_RECKON              ,
      CollectorNativeStates.CLOUD_PAUSE              ,
    ]

    return bIsTrackingState
    

  ###############################################
  # CanTrackIfRequested
  # 
  # True if the collector will try to track if conditions are right
  #     

  def CanTrackIfRequested(self):
    # Static, idle resting states from which the auto-sequencer is allowed to
    # issue a Track command.  FLAT/FLAT_ERROR are included symmetrically with
    # STOWED/STOW_ERROR — both represent a parked position the sequencer is
    # free to leave when the tracking window opens.
    bCanTrackIfRequested = self.CollectorState in [
      CollectorNativeStates.OFF          ,
      CollectorNativeStates.HOME_COMPLETE,
      CollectorNativeStates.STOWED       ,
      CollectorNativeStates.STOW_ERROR   ,
      CollectorNativeStates.FLAT         ,
      CollectorNativeStates.FLAT_ERROR   ,
    ]

    return bCanTrackIfRequested


  ###############################################
  # IsOff
  # 
  # True if the collector is in Off state
  #     

  def IsOff(self):
    bIsOff = self.CollectorState in [
      CollectorNativeStates.OFF  ]

    return bIsOff    
  
