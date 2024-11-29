#######################################################
# tTempHumSensor - class for reading and relaying inputs from our temp and humidity sensors
#
# This class only writes to the display, never reads
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
import serial
from PySide6.QtCore import QObject
from ConfigInfo     import *


##########################################################################################
##########################################################################################
##########################################################################################
# tMarquee 
#
# 
#

class tTempHumSensor(QObject):

  #################################################
  #
  # CONFIGURATION
  #

#  BAUD_RATE      = 115200
  # Make the buffer big enough to hold 15 minutes of readings, in case we only read every 10 minutes.  
  # There are 30 readings per minute of 11 characters each (if there is a CR/LF after each)
#  RX_BUFFER_SIZE = 15 * 30 * 11
  # We use default 8N1 and no flow control


  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, portName, parent=None):
    super().__init__(parent)

    self.port     = None
    self.portName = portName

    self.OpenPort(False)


  def __del__(self):
    self.ClosePort()

  
  ###############################################
  # ClosePort
  # 
  # INPUTS:
  #     

  def ClosePort(self):
    if (self.port):
      try:
        self.port.close()
      finally:
        self.port = None


  ###############################################
  # OpenPort
  # 
  # INPUTS:
  #     

  def OpenPort(self, bReopenAttempt):
    if self.port:
      print('tTempHumSensor: Port ', self.portName, ' already open')
      return

    try:
      self.port  = serial.Serial(self.portName, TEMP_HUM_BAUD_RATE, timeout=1)
    except:
      if not bReopenAttempt:
        print('tTempHumSensor: Could not open port ', self.portName)
        #sys.exit()

    try:
      self.port.set_buffer_size(rx_size = TEMP_HUM_RX_BUFFER_SIZE)
    except AttributeError as err:
      #print('PySerial::set_buffer_size not supported on this platform, continuing')
      pass

    if bReopenAttempt and self.port:
      print('tTempHumSensor: Successfullly reopened port ', self.portName)





  ###############################################
  # GetReading
  # 
  # Returns the latest reading from the device.  
  # It's intended that you not call it any faster than its 2-second output rate
  #
  # It will flush all stale readings and only return the last
  #
  # If there is no data available, it will return None
  #     
  
  def GetReading(self):
    # If the port is not open try to reopen it.
    if self.port is None:
      self.OpenPort(True)

    try:
      if self.port is None or self.port.in_waiting == 0:
        return None
    except serial.SerialException as err:
      print('tTempHumSensor: Port ', self.portName,' has gone offline')
      self.ClosePort()

    # If the port is not open try to reopen it.
    if self.port is None:
      self.OpenPort(True)
    
    if self.port is None or self.port.in_waiting == 0:
      return None
    
    
    # Read lines from the port until there are no more
    while self.port.in_waiting > 0:
      line = self.port.readline().decode('utf-8').strip()

      # At the beginning the Adafruit device returns some comment lines
      if line[0] == "#":
        return None

      try:
        # Split the comma-separated values.  Our custom device emits Temp, Humidity
        # The Adafruit Trinkey emits Sernum, temp, humidity, touch
        values = line.split(',')
        if len(values) == 2:
          TempInC, Humidity = values
        elif len(values) == 4:
          # Convert to float and handle exceptions
          SerNum, TempInC, Humidity, Touch = values
        else:
          raise ValueError("Unexpected number of values in line from temp/hum sensor")
        
        TempInC = float(TempInC)
        Humidity = float(Humidity)
        
      except ValueError:
        print('Invalid data received on temp/humidity sensor on port ', self.portName)
        return None

    return [ TempInC, Humidity ]   
 