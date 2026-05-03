#######################################################
# tCollector - class for interacting with the Collector's serial port
#
# Can send commands and receive telemetry
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
from PySide6.QtCore       import QRecursiveMutex, Signal, QDateTime, QTime, QTimeZone, QThread
from PySide6.QtSerialPort import QSerialPort

from SerialPort        import tAutoOpenSerialWholeLine
from PowerControl      import tPowerControl
from Utilities         import tActiveObject, with_lock
from ConfigInfo        import *
import subprocess


##########################################################################################
##########################################################################################
##########################################################################################
# tCollector  - Class that implements collector I/O
#
# At construction, the AutoOpenSerial device is created but is not yet moved to its own thread,
# and not started.  This is so that other objects can connect to its signals prior to it starting
# up.
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
# LimitStates          boolean[5] - az low, az high, el low, el high, home
# PositionMode         boolean - true if in positoin mode, false if velocity mode
#   C                  Spot coordinate x-y (float)
# ModeNum              Current mode of the collector (integer)
# ModeString           Current mode of the collecor (string)
# Timestring           Current time as a string HH:MM:SS
#

class tCollector(tActiveObject):
  
  # CollectorOnlineStateUpdate = Signal(bool)
  PortOpenStateChange        = Signal(bool)

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
  DoSetTime                  = Signal()
  DoMotStatus                = Signal()
  DoUnstick                  = Signal()
  DoReboot                   = Signal()
  DoReconnect                = Signal()

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

  def __init__(self, collectorName, portName, baud, parent=None):
    super().__init__(COLLECTOR_RETRY_TIMEOUT_SECS * 1000, parent)   # tActiveObject constructor

    # Mutex for controlling access to the device
    self._lock = QRecursiveMutex()

    self.CollectorName  = collectorName
    self.PortName       = portName
    self.baud           = baud
    self.bInit          = False
    self.CollectorState = CollectorNativeStates.UNKNOWN
    self.bUsbPowerState = False

    # These are cached values.  When they change (via a GUI event), we send a command to the collector
    self.WideAngleIllumPercent      = 0
    self.NarrowSkyBackgroundPercent = 0
    self.NarrowIlluminationPercent  = 0

    #try:

    # Connect signals to methods
    self.DoOff      .connect(self.Off      )
    self.DoHome     .connect(self.Home     )
    self.DoTrack    .connect(self.Track    )
    self.DoStow     .connect(self.Stow     )
    self.DoSetTime  .connect(self.SetTimeToNow)
    self.DoMotStatus.connect(self.MotStatus)
    self.DoUnstick  .connect(self.Unstick  )
    self.DoReboot   .connect(self.Reboot   )
    self.DoReconnect.connect(self.Reconnect)

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
  
  #@with_lock
  def Start(self, SunriseSunsetUpdateSignal):

    # Connect to sunrise and sunset updates
    SunriseSunsetUpdateSignal.connect(self.UpdateSunriseSunset)


    # We set rtscts and dsrdtr even though this is a virtual COM Port.  This provides a way for 
    # the virtual port driver to inform when it isn't yet initialized or otherwise ready for
    # data, which can happen.
    self.SerialPort  = tAutoOpenSerialWholeLine(self.PortName, baudrate=self.baud, readBufSize=COLLECTOR_RX_BUFFER_SIZE,
                                                parent=self)
    # Monitor the port for open/close state changes
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)

    # And for text strings
    self.SerialPort.readyLine          .connect(self.ProcessLineOfOutput)
    self.SerialPort.errorOccurred      .connect(self.HandleSerialPortError)

    self.MissingTelemetryCount = 0

    self.SerialPort.bPrintDiag = False # (self.CollectorName == "4B")
   
    # Manually call OnlineStatusUpdate the first time, to intiialize the port and inform CollectorPane, if it is open
    self.OnlineStatusUpdate(self.SerialPort.IsOpen())
    if not self.bInit:
      print('tCollector: Could not open collector',self.CollectorName,'on port', self.PortName, flush=True)

    # And start the periodic task running
    super().Start()


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

  #@with_lock
  def InitializeConnection(self):
    if not self.SerialPort.IsOpen():
      print(f'tCollector: ERROR: Collector {self.CollectorName} offline in InitializeConnection', flush=True)
    else:
      # print(f'tCollector: INFO: Collector {self.CollectorName} back online', flush=True)
      self.CollectorState = CollectorNativeStates.UNKNOWN
      self.FlushCommandInput()
      self.SetTimeToNow()
      self.SetTelemetryOnOff(True)
    QThread.msleep(10)   # Give the output time to flush


  ###############################################
  # Reconnect - Closes and reopens/reinits a port
  # 
  # 
  #

  #@with_lock
  def Reconnect(self):
    if self.SerialPort.IsOpen():
      self.SerialPort.close()
    self.bInit = False
    self.InitializeConnection()


  ###############################################
  # OnlineStatusUpdate - Called when the serial port connection state changes
  # 
  # This method sends the "Telemetry on" command
  #

  def OnlineStatusUpdate(self, bState):
    bOldState  = self.bInit
    self.bInit = self.SerialPort.IsOpen()

    # If the connection is offline, mark the status as unknown
    if not self.bInit:
      self.CollectorState = CollectorNativeStates.UNKNOWN

    # If the connection has just come online, initialize it
    if self.bInit and not bOldState:
      self.InitializeConnection()

    # Inform the CollectorPane
    self.PortOpenStateChange.emit(self.bInit)


  ###############################################
  # PeriodicMethod
  # 
  # This method just attempts to periodically reopen the port if it's not open
  #

  #@with_lock
  def PeriodicMethod(self):
    #if self.SerialPort.bPrintDiag: 
    #  #print(f"Periodic task Current thread: {QThread.currentThread()}", f"Collector thread: {self.thread()}")
    #  nBytesAvailable = self.SerialPort.bytesAvailable()
    #  if nBytesAvailable > 0:
    #    print(f'Periodic taks ***FOUND {nBytesAvailable} bytes***')
    #    self.SerialPort.readyRead.emit()
    #  else:
    #    print('Periodic task')

    # If USB power is not on, we the port won't even exist and we should not attempt to do anything
    if not self.bUsbPowerState:
      return
    
    # If the port appears open but has become unresponsive for too long, re-open
    if self.SerialPort.IsOpen() and self.MissingTelemetryCount >= COLLECTOR_MISSING_TELEM_REOPEN_THRESHOLD:
      #print(f'Forcing reopen attempt for collector {self.CollectorName}',flush=True)
      self.SerialPort.Reopen()
      self.MissingTelemetryCount = 0  # Just so we don't introduce a reopen loop
    # If it's been unresponsive at all, try to goose the receiver thread with a signal
    elif self.SerialPort.IsOpen() and self.MissingTelemetryCount > 0:
      #print(f'Attempting wakeup for collector {self.CollectorName}',flush=True)
      self.SerialPort.ReaderWakeUp.emit()
    else:
      self.SerialPort.AttemptOpenIfNeeded()  # Will be a no-op if the port is open
    if not self.SerialPort.IsOpen():
      #print('tCollector: Collector ' + self.CollectorName + ' on port ' + self.PortName + ' offline', flush=True)
      pass

    # Increment the missing telemetry counter.  ProcessOutputLine will re-zero it 
    self.MissingTelemetryCount = self.MissingTelemetryCount + 1
  
  
  ###############################################
  # __enter__ and __exit__ for use with "with"
  # 
  # Acquire and release the lock
  #     
     
  def __enter__(self):
    self._lock.lock()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self._lock.unlock()


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

    if Line.startswith("***COLLECTOR ONLINE***"):
      self.InitializeConnection()
      return
    
    if Line.startswith("TRACKER4 RELEASE "):
      self.ReleaseString = Line[17:]
      self.ReleaseStringReceived.emit(self.ReleaseString)
      return
    
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

        elif FieldTag in "G":
          # Single number fields (integer)
          parsed_data[FieldTag] = int(FieldValue)

        elif FieldTag == "H":
          # First character is 'N' or 'W', followed by a 5-digit integer
          IsNarrowMode = (FieldValue[0] == "N")
          NarrowAngleThreshold = int(FieldValue[1:])  # Remaining characters are the threshold
          parsed_data["IsNarrowMode"        ] = IsNarrowMode
          parsed_data["NarrowAngleThreshold"] = NarrowAngleThreshold

        elif FieldTag == "L":
          # Five characters are '0' or '1', converted to a boolean array
          LimitStates = [char == "1" for char in FieldValue]
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

  #@with_lock
  def FlushCommandInput(self):
    # Ctrl-C clears any partial command without executing it; CR then submits a blank line.
    FlushString = "\x03\r"
    result = self.SerialPort.write(FlushString)

    if result != len(FlushString):
      print('Error flushing input for collector ', self.CollectorName, flush=True)
      return -1  
    
    return 0

  
  ###############################################
  # Stow
  # 
  # Comamnds the collector to Stow
  #     

  #@with_lock
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
  # Track
  # 
  # Comamnds the collector to Track
  #     

  #@with_lock
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

  #@with_lock
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

  #@with_lock
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

  #@with_lock
  def SetTimeToNow(self):
    timezone = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    #if not isinstance(timezone, QTimeZone):
    #  raise TypeError("timezone must be of type QTimeZone")

    current_time = QDateTime.currentDateTime(timezone)
    
    # Format to HHMMSSt (with 0.1 second resolution)
    CurrentTimeString = current_time.toString('hhmmss') + f"{int(current_time.time().msec() / 100)}"

    result = self._SendCommand("SetTime", CurrentTimeString, self.sunrise.toString('hhmm'), self.sunset.toString('hhmm'))

    if result < 0:
      print ('Could not set time for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0


  ###############################################
  # MotStatus - sends a pair of commands to cause the collector to print motor status info
  # 
  #     

  #@with_lock
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
  # Unstick - Sends an Unstick command
  # 
  #     

  #@with_lock
  def Unstick(self):
    print('Unstick is not currently implemented for Gen3', flush=True)
    self.bResponded = True
    return -1


  ###############################################
  # Reboot - causes a reboot by using DsLite to reset the board
  # 
  #     

  #@with_lock
  def Reboot(self):
    shell_command = (
      r'"C:\Users\PlanetA\Nextcloud\Engineering\Calseed Prototype\Software\TI_Tools\dslite\dslite" '
      r'--reset 1 --config '
      rf'"C:\Users\PlanetA\Nextcloud\Engineering\Calseed Prototype\Software\TI_Tools\dslite\{self.CollectorName}.ccxml"'
    )

    print(f'Hard resetting {self.CollectorName}')
    #print(shell_command)
    subprocess.run(f'cmd /c "{shell_command} > nul 2>&1"', shell=True)

    self.bResponded = True
    return 0


  ###############################################
  # SetTelemetryOnOff()
  # 
  # Turns telemetry on or off
  #
  # INPUTS:
  #   bTelemetryOn - desired state
  #     

  #@with_lock
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

  #@with_lock
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
    bIsTrackingState = self.CollectorState in [
      CollectorNativeStates.HOME_ELEVATION_LOW    ,
      CollectorNativeStates.HOME_ELEVATION_HIGH   ,
      CollectorNativeStates.HOME_AZIMUTH_NEG      ,
      CollectorNativeStates.HOME_AZIMUTH_POS      ,
      CollectorNativeStates.HOME_AZIMUTH_NEG_RETRY,
      CollectorNativeStates.ACQ_BEGIN             ,
      CollectorNativeStates.ACQ_ELEVATION_WAIT    ,
      CollectorNativeStates.ACQ_AZ                ,
      CollectorNativeStates.ACQ_ERROR             ,
      CollectorNativeStates.ACQUIRE               ,
      CollectorNativeStates.WAITING_FOR_SUN       ,
      CollectorNativeStates.TRACK                 ,
      CollectorNativeStates.CLOUD_PAUSE ]
    
    return bIsTrackingState
    

  ###############################################
  # CanTrackIfRequested
  # 
  # True if the collector will try to track if conditions are right
  #     

  def CanTrackIfRequested(self):
    bCanTrackIfRequested = self.CollectorState in [
      CollectorNativeStates.OFF                    ,
      CollectorNativeStates.HOME_COMPLETE          ,
      CollectorNativeStates.STOW_AZ_HOME           ,
      CollectorNativeStates.STOW_EL_HOME           ,
      CollectorNativeStates.STOWED                 ,
      CollectorNativeStates.STOW_ERROR ]

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
  
