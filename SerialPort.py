#######################################################
# tAutoOpenSerial    - Serial port that automatically opens 
# tAutoOpenSerialStr - Same thing with str I/O instead of QByteArray
#
# Gracefully handles the port not being open or having an error by 
# simply returning nothing.  Attempts to reopen the port if not open.
#
# If AutoRetryTimeout is non-zero, will automatically try to reopen
# the port periodically.
#
# 
# STATE INVARIANT:
#   bIsOpen always reflects the opened/closed state of the port



#################################################
# Modules used
#

from PySide6.QtSerialPort import QSerialPort
from PySide6.QtCore import Signal, QTimer, QByteArray, QThread, Qt



#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerial    - Serial port that automatically opens 
#

class tAutoOpenSerial(QSerialPort):
  PortOpenStateChange = Signal(bool)  # Emitted when the port is successfully opened or closed
  ReaderWakeUp        = Signal()


  #######################################################
  # Constructor 
  #
  
  def __init__(self, portName, baudrate=9600, readBufSize=0, parent=None):
    super().__init__(parent)

    self.bIsOpen = False

    self.setPortName(portName)
    self.setBaudRate(baudrate)
    if readBufSize != 0:
      self.setReadBufferSize(readBufSize)

    self.setDataBits(QSerialPort.Data8)
    self.setParity(QSerialPort.NoParity)
    self.setStopBits(QSerialPort.OneStop)
    self.setFlowControl(QSerialPort.NoFlowControl)

    # Setup timer for auto-reopen
    #self._ReopenTimer = QTimer()
    #self._ReopenTimer.timeout.connect(self.AttemptOpenIfNeeded)
    #self._ReopenTimer.setSingleShot(True)  

    # Initial attempt to open the port
    self.AttemptOpenIfNeeded()


  #######################################################
  # Destructor - Cleans up by closing the port
  # 

  def __del__(self):
    if self.bIsOpen:
      self.close()


  #######################################################
  # IsOpen
  # 

  def IsOpen(self):
    return self.bIsOpen


  #######################################################
  # AttemptOpenIfNeeded - Attempt to open the port and emit a signal if successful
  # 
  # If the open is not successful, will arm the reopen timer

  def AttemptOpenIfNeeded(self):
    # I write this line but don't know why.
    #if self.errorOccurred() == QSerialPort.SerialPortError.TimeoutError:
    #  pass
    if not self.bIsOpen:
      # ReadWrite is actually a member of QIODevice base class, but this works
      if self.open(QSerialPort.ReadWrite) and self.error() == QSerialPort.NoError:
        self.bIsOpen   = True
        self.bWakingUp = False
        self.PortOpenStateChange.emit(self.bIsOpen)
      else:
        self.close()
        self.bIsOpen = False


  #######################################################
  # _HandleClose - Called when the port should be closed, usually after an error
  # 
  # Also emit a signal
 
  def _HandleClose(self):
    if self.bIsOpen:
      self.bIsOpen = False
      self.PortOpenStateChange.emit(self.bIsOpen)
      #self._ArmReopenTimerIfNotRunning()


  #######################################################
  # read - Read bytes, reopening port if needed
  # 
  # RETURNS:
  #   Retrieved data as a QByteArray

  def read(self):
    self.AttemptOpenIfNeeded()
    if not self.bIsOpen:
      return QByteArray()

    data = self.readAll()
    self.flush()

    if self.error() != QSerialPort.NoError:
      self.close()
      return QByteArray()   # Return empty string on read error

    return data
  

  #######################################################
  # readString - Reads bytes and returns them as a string
  # 
  # RETURNS:
  #   Retrieved data as a string

  def readString(self):
    data = self.read()     # Read in a QByteArray
    return str(data.data(), "utf-8") if not data.isEmpty() else ""  # Convert to string


  #######################################################
  # Write - Writea a either a QByteArray or a string to the port
  # 
  # RETURNS:
  #   Number of characters written, or -1 if not successful

  def write(self, data):
    self.AttemptOpenIfNeeded()
    if not self.bIsOpen:
      return -1  # Return -1 if the port couldn't be opened

    # Convert the data to QByteArray if not already one
    if isinstance(data, str):
      data = data.encode("utf-8")  # Convert string to bytes

    bytes_written = super().write(data)
    if bytes_written == -1 or self.error() != QSerialPort.NoError:
      self.close()
      return -1  # Return -1 on write error
    
    return bytes_written  # Return number of bytes written


  #######################################################
  # Reopen - Close and reopen the port
  # 

  def Reopen(self):
    self.close()
    self.AttemptOpenIfNeeded()


  #######################################################
  # close - Overrides close to calls close but also send signals, restarts the auto-reopen timer
  # 

  def close(self):
    # No need to wrap this in try/except.  Qt will simply close the port gracefully or log 
    # an error.  It won't raise an exception.
    if self.isOpen():
      super().close()
    self._HandleClose()
    

#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerialWholeLine    - Serial port that automatically opens and emits a signal whenever a full line arrives
#

class tAutoOpenSerialWholeLine(tAutoOpenSerial):
  readyLine = Signal(str)  # Signal emitted when a full line is available


  #######################################################
  # Constructor
  # 

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self._lineBuffer = ""  # Buffer for assembling lines

    # Connect the readyRead signal to the line assembly method
    self.readyRead   .connect(self._AssembleLine, Qt.QueuedConnection)
    self.ReaderWakeUp.connect(self.WakeUp, Qt.QueuedConnection)


  #######################################################
  # WakeUp - called whenever characters arrive on the port
  #
  # Emits the readyLine signal whenever a full line has arrived on the port
  # 

  def WakeUp(self):
    self.bWakingUp = True
    #print('wakeup attempt')
    self._AssembleLine()
    

  #######################################################
  # _AssembleLine - called whenever characters arrive on the port
  #
  # Emits the readyLine signal whenever a full line has arrived on the port
  # 

  def _AssembleLine(self):
    if self.bytesAvailable() == 0:
      # This can happen routinely since we're using QueuedConnection - our while loop can pick up bytes before the
      # second signal arrives.
      #print(f"No data available on port {self.portName()}")
      self.bWakingUp = False
      return
    
    while self.bytesAvailable() > 0:
      if self.bWakingUp:
        print(f'*****{self.portName()}: Waking up worked*****')
      self.bWakingUp = False
      data = self.read()  # Read available bytes as a QByteArray

      if self.error() != QSerialPort.NoError:
        print(f"Serial port error on port {self.portName()}: {self.error()}, closing")
        self.close()
        return

      if data.isEmpty():
        print(f"Empty data read on port {self.portName()}")
        break  # No more data available to read

      # Convert QByteArray to string and append to the buffer
      #self._lineBuffer += str(data.data(), "utf-8")

      # Print the raw data in hex format
      #print(f"Raw data: {data.toHex().data().decode('ascii')}")
      if self.bPrintDiag:
        print(str(data.data(), "utf-8", errors="ignore"), end="")

      #try:
      # Convert QByteArray to string and append to the buffer. 
      # The reason for the ignore flag is to skip all tha cruft that appears when you
      # first connect.  Without the flag, it barfs on those characters.
      self._lineBuffer += str(data.data(), "utf-8", errors="ignore")
      #except UnicodeDecodeError as e:
      #  print(f"Decoding error on port {self.portName()}: {e}. Raw bytes: {data}")
      #  break

      # Check for complete lines.  This handles the case where there is more than a full line in the buffer
      while "\n" in self._lineBuffer:
        line, self._lineBuffer = self._lineBuffer.split("\n", 1)
        self.readyLine.emit(line + "\n")  # Emit the line including the newline
        #if self.bPrintDiag:
          #print(f"Current thread: {QThread.currentThread()}", f"Serial port thread: {self.thread()}")
          #print('Emitted: ',line)

