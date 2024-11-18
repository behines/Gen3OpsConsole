###############################################
# tSerial - Manages serial ports
#
# Opens and closes ports, and particularly, helps to deal with ports that
# are offline at startup or that go offline later
#


import serial

class tSerial:

  ###############################################
  # tSerial constructor
  #  

  def __init__(self, port, baud, timeout = 0):
    self.Port             = port
    self.Baud             = baud
    self.TimeoutSecs      = timeout
    self.SerialPort       = None
  

  ###############################################
  # tSerial::Open
  # 
  # Opens the serial port specified in the constructor
  #
  # Takes the long-name of the port as an argument
  #
  # RETURNS:
  #   0 if successful, 1 if already open, -1 if failed
  #
 
  def Open(self, LongName = None):
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
  # Closes the serial port, if it was open
  #
 
  def Close(self):
    if (self.IsOpen()) : 
      print("Closing ", self.SerialPort.name)
      self.SerialPort.close()
      self.SerialPort = None


  ###############################################
  # tUart::IsOpen
  # 
  # Uses the state invariant that self.SerialPort is the port object if 
  # successfully opened, or is None if not open.
  #
 
  def IsOpen(self):
    return (not (self.SerialPort is None))
  

  ###############################################
  # tUart::SetTimeout
  # 
  # Sets the timeout for operations to the specified number of seconds.  Can be a float.
  #
 
  def SetTimeout(self, timeout):
    self.SerialPort.timeout = timeout


  ###############################################
  # tUart::__enter__ and __exit
  # 
  # These methods are called automatically at the beginning and end of "with" blocks.
  # This allows automatic closing of the port when used in a with block.
  #

  def __enter__(self):   # Called when a with statement is used
    if (not self.IsOpen()):    
      self.Open() 
      
  def __exit__(self, exception_type, exception_value, traceback):
    self.Close()
    

  ###############################################
  # tUart::EnumeratePorts - Static method to get list of ports
  #
  # You can call this prior to constructing a UART to get a list of candidate ports
  #  
  # It returns a vector of tuples of (Device, Description)
  
  @staticmethod
  def EnumeratePorts():
    
    PortObjects = serial.tools.list_ports.comports()
    DeviceList = [ (PortObjects[i].device,PortObjects[i].description) for i in range(len(PortObjects)) ]

    return DeviceList

