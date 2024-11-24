#######################################################
# tCollector - class for interacting with the Collector's serial port
#
# Can send commands and receive telemetry
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
from PySide6.QtCore    import QFile, Qt, QMutex, Signal, QDateTime, QTimeZone

from SerialPort        import tAutoOpenSerialWholeLine
from Utilities         import tActiveObject
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

class tCollector(tActiveObject):
  
  CollectorOnlineStateUpdate = Signal(bool)
  CollectorStateUpdate       = Signal(str, int)  # New collector state as an int.  First arg is the collector name ('1A', '1B', etc.)
  
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
      
    #try:
    # Mutex for controlling access to the device
    self._lock = QMutex()

    # We set rtscts and dsrdtr even though this is a virtual COM Port.  This provides a way for 
    # the virtual port driver to inform when it isn't yet initialized or otherwise ready for
    # data, which can happen.
    self.SerialPort  = tAutoOpenSerialWholeLine(portName, baudrate=baud, readBufSize=COLLECTOR_RX_BUFFER_SIZE,
                                                AutoReopenTimeoutSecs=COLLECTOR_RETRY_TIMEOUT_SECS, parent=self)
    # Monitor the port for open/close state changes
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)

    #except:
    #  print('tCollector: Could not open collector',collectorName,'on port', portName)


  ###############################################
  # Destructor
  # 
  # This will be called when the thread exits
  #     

  def __del__(self):
    pass



  ###############################################
  # Start 
  # 
  # Call this after construction to start the collector's active objects running.
  #     

  def Start(self):
    if self.SerialPort.IsOpen():
      self.InitializeConnection()
      self.bInit = True
    else:
      print('tCollector: Could not open collector',self.CollectorName,'on port', self.PortName, flush=True)

    # Monitor the port for open/close state changes
    self.SerialPort.PortOpenStateChange.connect(self.OnlineStatusUpdate)

    # Start our event loop going, also with a timer that will try to reconnect if not connected
    # self.StartThread(COLLECTOR_RETRY_TIMEOUT_SECS * 1000)
    # Start our event loop going.  We do NOT need a reconnect timer because this is handled by the AutoOpenSerial class if a timeout is specified
    self.StartThread()



  ###############################################
  # InitializeConnection - Configures a newly connected collector for I/O
  # 
  # This method simply sends the "Telemetry on" command
  #

  def InitializeConnection(self):
    if not self.SerialPort.IsOpen():
      print('tCollector: ERROR: Collector', self.CollectorName, 'offline in InitializeConnection', flush=True)
    
    self.CollectorState = CollectorNativeStates.UNKNOWN
    self.FlushCommandInput()
    self.SetTimeToNow(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
    self.SetTelemetryOnOff(True)


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
  # This method just attempts to periodically reopen the port if needed
  #

  def PeriodicMethod(self):
    self.SerialPort.AttemptOpenIfNeeded()
    if not self.SerialPort.IsOpen():
      print('tCollector: Collector ' + self.CollectorName + ' on port ' + self.PortName + ' offline', flush=True)


  
  
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
  # GetTelemLine
  # 
  # Returns a telemetry string from the controller
  #     

  def GetTelemLine(self):
    return ' '
  

  ###############################################
  # FlushInput
  # 
  # Write extras characters just to flush any pending "/" command and get back in sync
  # The longest command is 10 characters, so send 11 blanks.
  #     

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

  def Off(self):
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send ten blanks.
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

  def SetTimeToNow(self, timezone : QTimeZone):
    if not isinstance(timezone, QTimeZone):
      raise TypeError("timezone must be of type QTimeZone")

    current_time = QDateTime.currentDateTime(timezone)
    
    # Format to HHMMSS.s (with 0.1 second resolution)
    SetTimeCmd = '/K' + current_time.toString('hhmmss') + f"{int(current_time.time().msec() / 100)}"
    print('Set time (',self.CollectorName,'): ', SetTimeCmd)

    result = self.SerialPort.write(SetTimeCmd)

    if result != 9:
      print ('Could not set time for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0
    

  ###############################################
  # SetTelemetryOnOff()
  # 
  # Turns telemetry on or off
  #
  # INPUTS:
  #   bTelemetryOn - desired state
  #     

  def SetTelemetryOnOff(self, bTelemetryOn : bool):
    cmd = '/L' if bTelemetryOn else 'l'

    result = self.SerialPort.write(cmd)

    if result != 2:
      print ('Could not set telemetry on state for ', self.CollectorName)
      self.bResponded = True
      return -1
    else:
      return 0
