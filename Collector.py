#######################################################
# tCollector - class for interacting with the Collector's serial port
#
# Can send commands and receive telemetry
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
from PySide6.QtCore    import QFile, Qt, QRecursiveMutex, Signal, QDateTime, QTimeZone, QTime

from SerialPort        import tAutoOpenSerialWholeLine
from Utilities         import tActiveObject, with_lock
from ConfigInfo        import *


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
  DoReconnect          = Signal()

  UpdateThresholds           = Signal()
  
  ###############################################
  # Constructor part 1
  #
  # Part 2 of "construction" occurs when our owner calls "Start".  The space between
  # construction and starting gives the owner a chance to connect to signals.
  # 
  # INPUTS:
  #
  #   parent - if provided, will be ignored, activeobject have to have no parent
  #     

  def __init__(self, collectorName, portName, baud, parent=None):
    super().__init__(parent)   # tActiveObject constructor

    self.CollectorName  = collectorName
    self.PortName       = portName
    self.bInit          = False
    self.CollectorState = CollectorNativeStates.UNKNOWN

    # These are cached values.  When they change (via a GUI event), we send a command to the collector
    self.WideAngleIllumPercent      = 0
    self.NarrowSkyBackgroundPercent = 0
    self.NarrowIlluminationPercent  = 0

    #try:
    # Mutex for controlling access to the device
    self._lock = QRecursiveMutex()

    # We set rtscts and dsrdtr even though this is a virtual COM Port.  This provides a way for 
    # the virtual port driver to inform when it isn't yet initialized or otherwise ready for
    # data, which can happen.
    self.SerialPort  = tAutoOpenSerialWholeLine(portName, baudrate=baud, readBufSize=COLLECTOR_RX_BUFFER_SIZE,
                                                AutoReopenTimeoutSecs=COLLECTOR_RETRY_TIMEOUT_SECS, parent=self)
    # Monitor the port for open/close state changes
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)

    # And for text strings
    self.SerialPort.readyLine.connect(self.ProcessLineOfOutput)

    # Connect signals to methods
    self.DoOff      .connect(self.Off      )
    self.DoHome     .connect(self.Home     )
    self.DoTrack    .connect(self.Track    )
    self.DoStow     .connect(self.Stow     )
    self.DoSetTime  .connect(self.SetTimeToNow)
    self.DoMotStatus.connect(self.MotStatus)
    self.DoUnstick  .connect(self.Unstick  )
    self.DoReboot   .connect(self.Reboot   )
    self.DoReconnect.connect(lambda: self.SetTelemetryOnOff(True))

    self.UpdateThresholds.connect(self.SendThresholdPercentages)


  ###############################################
  # Destructor
  # 
  # This will be called when the thread exits
  #     

  def __del__(self):
    if self.SerialPort.IsOpen():
      self.SerialPort.close()



  ###############################################
  # Start 
  # 
  # Call this after construction to start the collector's active objects running.
  #     
  
  @with_lock
  def Start(self):
    if self.SerialPort.IsOpen():
      self.InitializeConnection()
      self.bInit = True
    else:
      print('tCollector: Could not open collector',self.CollectorName,'on port', self.PortName, flush=True)

    # Monitor the port for open/close state changes
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)

    # Start our event loop going, also with a timer that will try to reconnect if not connected
    self.StartThread(COLLECTOR_RETRY_TIMEOUT_SECS * 1000, self.CollectorName)
    # Start our event loop going.  We do NOT need a reconnect timer because this is handled by the AutoOpenSerial class if a timeout is specified
    # self.StartThread()



  ###############################################
  # InitializeConnection - Configures a newly connected collector for I/O
  # 
  # This method simply sends the "Telemetry on" command
  #

  @with_lock
  def InitializeConnection(self):
    if not self.SerialPort.IsOpen():
      print('tCollector: ERROR: Collector', self.CollectorName, 'offline in InitializeConnection', flush=True)
    else:
      print('tCollector: INFO: Collector', self.CollectorName, 'back online')
      self.CollectorState = CollectorNativeStates.UNKNOWN
      self.FlushCommandInput()
      self.SetTimeToNow()
      self.SetTelemetryOnOff(True)


  ###############################################
  # Reconnect - Closes and reopens/reinits a port
  # 
  # 
  #

  @with_lock
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
    bOldState = self.bInit
    self.bInit = self.SerialPort.IsOpen()

    # If the connection is offline, mark the status as unknown
    if not self.bInit:
      self.CollectorState = CollectorNativeStates.UNKNOWN

    # If the connection has just come online, initialize it
    if self.bInit and not bOldState:
      self.InitializeConnection()


  ###############################################
  # PeriodicMethod
  # 
  # This method just attempts to periodically reopen the port if it's not open
  #

  @with_lock
  def PeriodicMethod(self):
    #print('Collector reopen attempt',flush=True)
    self.SerialPort.AttemptOpenIfNeeded()  # Will be a no-op if the port is open
    if not self.SerialPort.IsOpen():
      #print('tCollector: Collector ' + self.CollectorName + ' on port ' + self.PortName + ' offline', flush=True)
      pass


  
  
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
      #self.TextLineReceived.emit(Line)
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
      print(f"Error parsing TEL line: {e}:")
      print(Line)


  ###############################################
  # FlushInput
  # 
  # Write extras characters just to flush any pending "/" command and get back in sync
  # The longest command is 10 characters, so send 11 blanks.
  #     

  @with_lock
  def FlushCommandInput(self):
    nToSend = 11
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send 11 blanks.
    result = self.SerialPort.write(nToSend * ' ')

    if result != nToSend:
      print('Error flushing input for collector ', self.CollectorName, flush=True)
      return -1  
    
    return 0

  
  ###############################################
  # Stow
  # 
  # Comamnds the collector to Stow
  #     

  @with_lock
  def Stow(self):
    result = self.SerialPort.write('/Q')

    if result == 2:
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

  @with_lock
  def Track(self):
    result = self.SerialPort.write('/t')

    if result == 2:
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

  @with_lock
  def Home(self):
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send ten blanks.
    result = self.SerialPort.write('/h')

    if result == 2:
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

  @with_lock
  def Off(self):
    print('Sending Off command')
    result = self.SerialPort.write('/o')

    if result == 2:
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

  @with_lock
  def SetTimeToNow(self):
    timezone = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    #if not isinstance(timezone, QTimeZone):
    #  raise TypeError("timezone must be of type QTimeZone")

    current_time = QDateTime.currentDateTime(timezone)
    
    # Format to HHMMSS.s (with 0.1 second resolution)
    SetTimeCmd = '/K' + current_time.toString('hhmmss') + f"{int(current_time.time().msec() / 100)}"
    # print('Set time (',self.CollectorName,'): ', SetTimeCmd)

    result = self.SerialPort.write(SetTimeCmd)

    if result != 9:
      print ('Could not set time for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0


  ###############################################
  # MotStatus - sends a pair of commands to cause the collector to print motor status info
  # 
  #     

  @with_lock
  def MotStatus(self):
    result = self.SerialPort.write('/s')

    if result != 2:
      return -1    

    result = self.SerialPort.write('/u')

    if result != 2:
      return -1    

    self.bResponded = True
    return 0



  ###############################################
  # Unstick - Sends an Unstick command
  # 
  #     

  @with_lock
  def Unstick(self):
    result = self.SerialPort.write('/G')

    if result != 2:
      return -1    

    self.bResponded = True
    return 0


  ###############################################
  # Reboot - Sends an Unstick command
  # 
  #     

  @with_lock
  def Reboot(self):
    result = self.SerialPort.write('/IREBOOT')

    if result != 8:
      return -1    

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

  @with_lock
  def SetTelemetryOnOff(self, bTelemetryOn : bool):
    cmd = '/L' if bTelemetryOn else '/l'

    result = self.SerialPort.write(cmd)

    if result != 2:
      print ('Could not set telemetry on state for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0



  ###############################################
  # SetThresholdPercentages()
  # 
  # Sends a message Jnnnmmmppp with the three percentages
  #     

  @with_lock
  def SendThresholdPercentages(self):
    SetThresholdsCmd = '/J' + f"{self.WideAngleIllumPercent:03d}{self.NarrowSkyBackgroundPercent:03d}{self.NarrowIlluminationPercent:03d}"

    result = self.SerialPort.write(SetThresholdsCmd)

    if result !=11:
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
