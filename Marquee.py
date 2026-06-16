#######################################################
# tMarquee - class for talking to the marquee display
#
# This class only writes to the display, never reads
#



#################################################

# Modules used
#

import sys
from ConfigInfo     import *

# module used to talk over serial with the esp32
try:
  import serial
except ModuleNotFoundError:
  if PROJECT_CONFIG.bHasMarquee:
    raise
  serial = None

# For implementing object locking and retry timer
from PySide6.QtCore import QElapsedTimer, QObject
from Utilities      import requires_device_open
from Collector      import tCollector
from typing         import List              # For pylance


##########################################################################################
##########################################################################################
##########################################################################################
# tMarquee 
#
# The Marquee object is owned by the PeriodicLogger, and the whole app is single-threaded, so
# callers invoke tMarquee methods directly - there is no need for signals to update GHI, DNI, or
# temperatures.  Collector state still arrives via the CollectorStateUpdate signal, but on the
# same thread.
#

class tMarquee(QObject):

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

  def __init__(self, portName, CollectorList: List[tCollector], parent=None):
    super().__init__(parent)

    # NOTE: single-threaded app - the recursive mutex that used to guard this device was
    # scaffolding for an abandoned per-instrument-thread design, and is removed (see the
    # fuller note in tAgilent.__init__).
    self.port     = None
    self.portName = portName

    self.RetryTimer     = QElapsedTimer()
    self.RetryTimeoutMs = MARQUEE_RETRY_TIMEOUT_SECS * 1000  # Convert minutes to milliseconds
    self.OpenPort()

    # Connect to the collector signals that indicate state updates
    for Collector in CollectorList:
      Collector.CollectorStateUpdate.connect(self.SendCollectorState)

  def __del__(self):
    if not self.port is None:
      self.port.close()


  ###############################################
  # (Removed __enter__/__exit__ context-manager locking - single-threaded app, see __init__.)


  ###############################################
  # OpenPort
  # 
    
  def OpenPort(self):
    try:
      self.port = serial.Serial(self.portName, MARQUEE_BAUD_RATE, timeout=1)
      print('tMarquee: Successfully opened port ', self.portName)
    except:
      self.port = None
      self.RetryTimer.start()
      print('tMarquee: Could not open port ', self.portName)


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
    if not self.RetryTimer.isValid() or self.RetryTimer.elapsed() >= self.RetryTimeoutMs:
      self.OpenPort()
    return not (self.port is None)
    

  ###############################################
  # SendMessage
  # 
  #     
  
  @requires_device_open()
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
      self.RetryTimer.start()
      print('Error writing to the marquee serial port ', self.portName, ', will attempt to reopen next time.')
   


  ###############################################
  # SendOutsideData
  #     
  
  @requires_device_open()
  def SendOutsideData(self, TempInC, Humidity):
    TempInF = TempInC * 9/5 + 32
    self.SendMessage(f"T{TempInF}\n")
    self.SendMessage(f"H{Humidity}\n")

    
  ###############################################
  # SendDomeData
  #     
  
  @requires_device_open()
  def SendDomeData(self, TempInC, Humidity):
    TempInF = TempInC * 9/5 + 32
    self.SendMessage(f"t{TempInF}\n")
    self.SendMessage(f"h{Humidity}\n")


  ###############################################
  # SendBoxData
  #     
  
  @requires_device_open()
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
  
  @requires_device_open()
  def SendDNI(self, DNI):
    self.SendMessage(f"D{int(DNI)}\n")





  ###############################################
  # SendAll
  #     

  @requires_device_open()
  def SendAll(self, DomeTempInC, DomeHumidity, OutsideTempInC, OutsideHumidity, BoxTempInC, GHI, DNI): #, CollectorStates):
    self.SendDomeData(DomeTempInC, DomeHumidity)
    self.SendOutsideData(OutsideTempInC, OutsideHumidity)
    self.SendBoxData(BoxTempInC)
    self.SendGHI(GHI)
    self.SendDNI(DNI)
    #self.SendCollectorStates(CollectorStates)


  ###############################################
  # SendTemps
  #     

  @requires_device_open()
  def SendTemps(self, DomeTempInC, DomeHumidity, OutsideTempInC, OutsideHumidity, BoxTempInC):
    self.SendDomeData(DomeTempInC, DomeHumidity)
    self.SendOutsideData(OutsideTempInC, OutsideHumidity)
    self.SendBoxData(BoxTempInC)


  ###############################################
  # SendSun
  #     

  @requires_device_open()
  def SendSun(self, GHI, DNI):
    self.SendGHI(GHI)
    self.SendDNI(DNI)


  ###############################################
  # SendCollectorState
  # 
  # Called when 

  @requires_device_open()
  def SendCollectorState(self, CollectorName: str, NewState: CollectorNativeStates):

    CollectorNum = -1
    if PROJECT_CONFIG.MarqueeDisplayOrder is not None:
      try:
        CollectorNum = PROJECT_CONFIG.MarqueeDisplayOrder.index(CollectorName)
      except ValueError:
        print('WARNING: SendCollectorState: Could not find Collector Name ', CollectorName, ' in MARQUEE_DISPLAY_ORDER list')

    # Look up the collector number from the array, if still needed
    if CollectorNum < 0:
      try:
        CollectorNum = [CollectorPort.Name for CollectorPort in PROJECT_CONFIG.CollectorPorts].index(CollectorName)
      except ValueError:
        print('SendCollectorState: Unrecognized Collector Name ', CollectorName)
        return

    try:
      MarqueeStateNum = CollectorNativeStateToMarqueeState[NewState].value
    except KeyError:
      print('Could not find state ', NewState.name, ' in CollectorNativeStates enum')
      return

    # Encode the CollectorNum and the state as ASCII characters, starting from 64
    # So the encoding ia @=0, A=1, etc.
    msg = 'C' + chr(ord('@') + CollectorNum) + chr(ord('@') + MarqueeStateNum)
    # print(f'Sending marquee msg {msg}')
    self.SendMessage(msg + '\n')
