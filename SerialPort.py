###############################################
# tSerialPort - Manages serial ports
#
# Opens and closes ports, and particularly, helps to deal with ports that
# are offline at startup or that go offline later
#

# For implementing object locking and retry timer
from PySide6.QtCore import QMutex, QTimer, QObject
from Utilities      import requires_device_open
import serial

from ConfigInfo       import *


class tSerialPort(QObject):

  ###############################################
  # tSerialPort constructor
  #  
  # bAutoRetry - if True, the class will automatically try to reconnect periodically

  def __init__(self, portName, baud, bAutoRetry=True, rx_size = DEFAULT_SERIAL_PORT_RX_BUFFER_SIZE,
               tx_size= DEFAULT_SERIAL_PORT_TX_BUFFER_SIZE, timeout = 0, parent=None):
    super().__init__(parent)   # QObject constructor

    self.PortName    = portName
    self.Baud        = baud
    self.TimeoutSecs = timeout
    self.bAutoRetry  = bAutoRetry
    self.rx_size     = rx_size
    self.tx_size     = tx_size
    self.port        = None

    # Retry timer.  Used if we need to try to reopen the port at a time other
    # than when the program tries to read it.  So things like the temp/humidity
    # sensors don't need this since we actively read them. 
    if bAutoRetry:
      self.RetryTimer = QTimer()
      self.RetryTimer.setSingleShot(True)  # Optional: Make it fire only once
  
  def __del__(self):
    self.Close()
    if not self.RetryTimer is None and self.RetryTimer.isActive():
      self.RetryTimer.stop()
      

  ###############################################
  # tSerialPort::Open
  # 
  # Opens the serial port specified in the constructor
  #
  # RETURNS:
  #   0 if successful, 1 if already open, -1 if failed
  #
 
  def Open(self):
    if (self.SerialPort is None) :
      try:
        print("Attempting to open ", self.PortName)
        self.SerialPort = serial.Serial(self.Portname, self.Baud, timeout = self.TimeoutSecs)  # , rtscts = True)

        try:
          self.SerialPort.set_buffer_size(rx_size = self.rx_size, tx_size = self.tx_size)
        except AttributeError as err:
          print("PySerial::set_buffer_size not supported on this platform, continuing"  )
        return 0
      except OSError as err:
        print("Error opening serial port:", err, ', will retry in ', SERIAL_PORT_RETRY_TIMEOUT_SECS, ' seconds')
        self.SerialPort = None


  ###############################################
  # tSerialPort::Close
  # 
  # Closes the serial port, if it was open
  #
 
  def Close(self):
    if (self.IsOpen()) : 
      print("Closing ", self.SerialPort.name)
      self.SerialPort.close()
      self.SerialPort = None


  ###############################################
  # tSerialPort::StartOpenRetryTimer
  # 
  # Kicks off a timer that we can check
  #   
 
  def StartOpenRetryTimer(self):
    timeout_ms = SERIAL_PORT_RETRY_TIMEOUT_SECS * 60 * 1000  # Convert minutes to milliseconds
    self.RetryTimer.start(timeout_ms)


  ###############################################
  # tSerialPort::IsDeviceOpen
  # 
  # Returns true if the device is open.  If it is not open, it will check the retry timer.
  # If the retry timer has expired, it will try again to open the device.
  #   
 
  def IsDeviceOpen(self):
    if self._IsOpen():
      return True
    # If the device is not open, see if the retry timer has timed out
    if self.RetryTimer.remainingTime() <= 0:
      self.Open()
      return not (self.SerialPort is None)
    

  ###############################################
  # tSerialPort::_IsOpen
  # 
  #
 
  def _IsOpen(self):
    return (not (self.SerialPort is None))
  

  ###############################################
  # tSerialPort:::SetTimeout
  # 
  # Sets the timeout for operations to the specified number of seconds.  Can be a float.
  #
 
  def SetTimeout(self, timeout):
    self.SerialPort.timeout = timeout


  ###############################################
  # tSerialPort::__enter__ and __exit
  # 
  # These methods are called automatically at the beginning and end of "with" blocks.
  # This allows automatic closing of the port when used in a with block.
  #

  def __enter__(self):   # Called when a with statement is used
    if (not self.IsOpen()):    
      self.Open() 
      
  def __exit__(self, exception_type, exception_value, traceback):
    self.Close()
    