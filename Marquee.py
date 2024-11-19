#######################################################
# tMarquee - class for talking to the marquee display
#
# This class only writes to the display, never reads
#



#################################################

# Modules used
#

# module used to talk over serial with the esp32
import serial
import sys
# For implementing object locking and retry timer
from PySide6.QtCore import QMutex, QTimer
from Utilities      import requires_device_open


##########################################################################################
##########################################################################################
##########################################################################################
# tMarquee 
#
# 
#

class tMarquee:

  #################################################
  #
  # CONFIGURATION
  #

  # We use default 8N1 and no flow control

  DEBUG        = True

  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, portName):

    # Mutex for controlling access to the device
    self._lock = QMutex()

    self.port     = None
    self.portName = portName
    self.OpenPort()

    # Retry timer.  Probably won't need it but it's simplest to create it regardless
    self.RetryTimer = QTimer()
    self.RetryTimer.setSingleShot(True)  # Optional: Make it fire only once

    if self.port is None:
      print('tMarquee: Could not open port ', self.portName)

  def __del__(self):
     if not self.port is None:
       self.port.close()


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
  # OpenPort
  # 
  #     
  
  def OpenPort(self):
    try:
      self.port = serial.Serial(self.portName, tMarquee.BAUD_RATE, timeout=1)
    except:
      self.port = None

    return self.port
  

  ###############################################
  # IsDeviceOpen
  # 
  # Returns true if the device is open.  If it is not open, it will check the retry timer.
  # If the retry timer has expired, it will try again to open the device.
  #   
 
  def IsDeviceOpen(self):
    if not self.port is None:
      return True
    # If the device is not open, see if the retry timer has timed out
    if self.RetryTimer.remainingTime() <= 0:
      self.OpenAndConfigureDevice()
      return not (self.device is None)
    


  ###############################################
  # SendMessage
  # 
  #     
  
  def SendMessage(self, line):
    # If the port is closed, try to reopen it
    if self.port is None:
      self.OpenPort()

    # If it failed, just abort
    if self.port is None:
      return

    try:
      # Write the values separately to the other serial port
      self.port.write(line.encode())   # Encode is necessary to convert the string to the bytes that Serial expects
    except serial.SerialException:
      self.port.close()
      self.port = None
      print('Error writing to the marquee serial port ', self.portName, ', will attempt to reopen next time.')
   


  ###############################################
  # SendOutsideData
  #     
  
  def SendOutsideData(self, TempInC, Humidity):
    TempInF = TempInC * 9/5 + 32
    self.SendMessage(f"T{TempInF}\n")
    self.SendMessage(f"H{Humidity}\n")

    
  ###############################################
  # SendDomeData
  #     
  
  def SendDomeData(self, TempInC, Humidity):
    TempInF = TempInC * 9/5 + 32
    self.SendMessage(f"t{TempInF}\n")
    self.SendMessage(f"h{Humidity}\n")


  ###############################################
  # SendBoxData
  #     
  
  def SendBoxData(self, TempInC):
    self.SendMessage(f"B{TempInC}\n")


  ###############################################
  # SendGHI
  #     
  
  def SendGHI(self, GHI):
    self.SendMessage(f"G{int(GHI)}\n")


  ###############################################
  # SendDNI
  #     
  
  def SendDNI(self, DNI):
    self.SendMessage(f"D{int(DNI)}\n")


  ###############################################
  # SendCollectorStates
  #
  # INPUTS:
  #   A list of collector states, 0-N
  #     
  
  def SendCollectorStates(self, StatesList):
    msg = 'C' + ''.join(str(digit) for digit in StatesList)
    self.SendMessage(msg + '\n')


  ###############################################
  # SendAll
  #     
  def SendAll(self, DomeTempInC, DomeHumidity, OutsideTempInC, OutsideHumidity, BoxTempInC, GHI, DNI, CollectorStates):
    self.SendDomeData(DomeTempInC, DomeHumidity)
    self.SendOutsideData(OutsideTempInC, OutsideHumidity)
    self.SendBoxData(BoxTempInC)
    self.SendGHI(GHI)
    self.SendDNI(DNI)
    self.SendCollectorStates(CollectorStates)