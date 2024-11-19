#######################################################
# tCollector - class for interacting with the Collector's serial port
#
# Can send commands and receive telemetry
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
import serial
from datetime import datetime

from PySide6.QtWidgets import  QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore    import QFile, Qt, QElapsedTimer, QMutex

##########################################################################################
##########################################################################################
##########################################################################################
# tCollector  - Class that implements the collector pane and all collector activities
#
# 
#

class tCollector(QWidget):
  
  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, collectorName, portName, baudRate, parent=None):
    super().__init__(parent)   # QWidget constructor
      
    self.bInit    = False
    self.bResponded  = False
    self.name     = 'Foo' #collectorName
    self.port     = None

    # Load CollectorPane UI dynamically
    loader = QUiLoader()
    ui_file = QFile("CollectorPane.ui")
    ui_file.open(QFile.ReadOnly)
    ui = loader.load(ui_file, self)
    ui_file.close()

    # Auto-bind widgets as attributes of self.  Not needed if we compile the UI with pyside6-uic,
    # but QUiLoader does not do this automatically.
    for widget in ui.findChildren(QWidget):
      setattr(self, widget.objectName(), widget)

    self.setFixedSize(ui.size())

    collectorName = 'Collector ' + collectorName
    self.CollectorGroup.setTitle(collectorName)

    try:
      # Mutex for controlling access to the device
      self._lock = QMutex()

      # We set rtscts and dsrdtr even though this is a virtual COM Port.  This provides a way for 
      # the virtual port driver to inform when it isn't yet initialized or otherwise ready for
      # data, which can happen.
      self.port  = serial.Serial(portName, baudRate, timeout=5)
      self.dtr = True
      self.rts = True

      #try:
        # Undocumented func on windows.  Needed to keep it from buffering output and losing characters
        # at the end
      #  self.port.set_buffer_size(tx_size = 0)
      #except AttributeError as err:
      #  print('PySerial::set_buffer_size not supported on this platform, continuing')
      #time.sleep(0.5)

      self.bInit = True
    except:
      print('tCollector: Could not open collector ',collectorName,'on port ', portName)


  def __del__(self):
    if self.port:
      self.port.flush()
      self.port.close()


  ###############################################
  # Open the port
  # 
  #     
     
  def Open(self):
    if (self.SerialPort is None) :
      try:
        if (LongName == None):
          if (self.LongName == None):
            print("tUart::Open: must supply a LongName either as argument to Open() or via SetLongName()"  )
            return -1
          else:
            LongName = self.LongName
        print("Attempting to open ", self.Port, ": ", LongName)
        if ((not (self.Port is None)) and (CAN_OVER_SERIAL_PORT_NAME in LongName)):
          # This appears to be our Arduino Due relaying CAN bus over serial - set the baud rate to match it
          self.Baud = CAN_OVER_SERIAL_BAUD_RATE
          self.bIsCanOverSerial = True
          print("Adjusted to use CAN baud rate of ", CAN_OVER_SERIAL_BAUD_RATE)
        else:
          self.bIsCanOverSerial = False
        self.SerialPort = serial.Serial(self.Port, self.Baud, timeout = self.TimeoutSecs)  # , rtscts = True)
        print("Serial port is ", self.SerialPort.name)         # check which port was really used
        try:
          self.SerialPort.set_buffer_size(rx_size = RX_BUFFER_SIZE, tx_size = TX_BUFFER_SIZE)
        except AttributeError as err:
          print("PySerial::set_buffer_size not supported on this platform, continuing"  )
        return 0
      except OSError as err:
        print("Error opening serial port:", err)
        self.SerialPort = None
        return -1
    else:
      print("Serial port ", self.SerialPort.name, " already open")  
      return 1


  ###############################################
  # tUart::Close
  # 
  #
 
  def Close(self):
    if (self.IsOpen()) : 
      self.port.close()
      self.port = None


  ###############################################
  # tUart::IsOpen
  #
 
  def IsOpen(self):
    return (not (self.port is None))



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
  # WaitForLineReady
  # 
  # Waits for DSR and CTS to be ready, with timeout
  #
  # RETURNS:
  #   True if ready, False if timed out
  #     

  def WaitForLineReady(self, TimeoutInSeconds):
    return True
    #bDidPrint = False
    #bRetVal   = False
#
    #while TimeoutInSeconds >= 0:
    #  if self.port.dsr and self.port.cts:
    #    bRetVal = True
    #    break
    #  else:
    #    TimeoutInSeconds = TimeoutInSeconds - 0.2
    #    bDidPrint = True
    #    if self.port.dsr:
    #      print('D.', end='')
    #    else:
    #      print('d', end='')
    #    if self.port.cts:
    #      print('C.', end='')
    #    else:
    #      print('c', end='')
#
    #    time.sleep(0.2)
#
    #if bDidPrint:
    #  if bRetVal:
    #    print('>')
    #  else:
    #    print('X')
  #
    #return bRetVal


   
  ###############################################
  # ReadLine
  # 
  # Returns a line of text from the controller, if available
  #     

  def ReadLine(self):
    if self.port.in_waiting == 0:
      return None
    
    # Read lines from the port until there are no more
    if self.port.in_waiting > 0:
      line = self.port.readline().decode('utf-8').strip()

    return line
  

  ###############################################
  # WriteChars
  # 
  # Writes characters to the controller.  Pass the message in as a string. Does NOT 
  # append a newline or carriage return
  #
  # Returns the number of bytes written.
  #     

  def WriteChars(self, Msg):
    if not self.WaitForLineReady(5):
      print('Collector ', self.name,': Failed to write ', Msg)
      
    try:
      nWritten = self.port.write(Msg.encode('utf-8'))
      #self.port.flush()
      return nWritten
    except:
      return -1
    


  ###############################################
  # FlushInput
  # 
  # Write extras characters just to flush any pending "/" command and get back in sync
  # The longest command is 10 characters, so send ten blanks.
  #     

  def FlushInput(self):
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send 11 blanks.
    result = self.WriteChars('           ')

    if result != 11:
      print('Error flushing input for collector ', self.name)
      return -1  
    
    return 0

  
  ###############################################
  # Stow
  # 
  # Comamnds the collector to Stow
  #     

  def Stow(self):
    result = self.WriteChars('/Q')

    if result == 2:
      print ('Stowing collector ', self.name)
      self.bResponded = True
      return 0
    else:
      print('Could not stow ', self.name)
      return -1  


  ###############################################
  # Track
  # 
  # Comamnds the collector to Track
  #     

  def Track(self):
    result = self.WriteChars('/t')

    if result == 2:
      print ('Tracking collector ', self.name)
      self.bResponded = True
      return 0
    else:
      print('Could not track ', self.name)
      return -1
    

  ###############################################
  # Home
  # 
  # Comamnds the collector to Home
  #     

  def Home(self):
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send ten blanks.
    result = self.WriteChars('/h')

    if result == 2:
      print ('Homing collector ', self.name)
      self.bResponded = True
      return 0
    else:
      print('Could not home ', self.name)
      return -1
    

  ###############################################
  # Off
  # 
  # Comamnds the collector to turn off
  #     

  def Off(self):
    # Write extras characters just to flush any pending "/" command and get back in sync
    # The longest command is 10 characters, so send ten blanks.
    result = self.WriteChars('/o')

    if result == 2:
      print ('Turning off collector ', self.name)
      self.bResponded = True
      return 0
    else:
      print('Could not turn off ', self.name)
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
  # Comamnds the collector to Home
  #     

  def SetTimeToNow(self, timezone):

    current_time = datetime.now(pytz.timezone(timezone))
    
    # Format to HHMMSS.s (with 0.1 second resolution)
    SetTimeCmd = '/K' + current_time.strftime('%H%M%S') + f"{int(current_time.microsecond / 100000)}"
    print('Set time (',self.name,'): ', SetTimeCmd)

    result = self.WriteChars(SetTimeCmd)

    if result != 9:
      print ('Could not set time for ', self.name)
      self.bResponded = True
      return -1
    else:
      return 0
