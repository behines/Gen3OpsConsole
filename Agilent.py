#######################################################
# tAgilent - manages a single 34970A
#



#################################################

# Modules used
#

# module used to get the current date and time
from datetime import datetime
# module used to talk with the agilent devices
import pyvisa  
# module used to talk over serial with the esp32
import serial
# module used to write to csv file
import csv
# module used to navigate directories for csv file
import os

import sys

# For implementing object locking and retry timer
from PySide6.QtCore import QRecursiveMutex, QElapsedTimer, QObject, QThread, Signal, QMutex, QWaitCondition, QMutexLocker
from Utilities      import requires_device_open, with_lock, SignalThenWaitFor, SignalEmitter


from ConfigInfo       import *


##########################################################################################
##########################################################################################
##########################################################################################
# tAgilent 
#
# Manages info about the COM Port connection 
#
# Includes __enter__ and __exit__ methods for use with a "with" statement that provide for
# mutually exclusive access to the serial port.
#

class tAgilent(QObject):

  #################################################
  #
  # CONFIGURATION
  #

  BAUD_RATE    = 9600        # I had it much higher, but I was getting input buffer overruns, even with RTS/CTS configured.  This fixed it, and is plenty fast for us.
  DATA_BITS    = 8
  PARITY       = pyvisa.constants.Parity.none 
  STOP_BITS    = pyvisa.constants.StopBits.one
  FLOW_CONTROL = pyvisa.constants.ControlFlow.rts_cts

  TIMEOUT_SECS = 2           # How long to give the instrument to respond before raising a timeout error

  #################################################
  #
  # Static members
  #

  PyVisaResourceManager = None

  # STATUS_BITS for STATus:OPERation:CONDition?
  STATUS_Calibrating       =     1  # The instrument is calibrating.
  STATUS_SelfTest          =     2  # The instrument is doing a selftest.
  STATUS_Scanning          =    16  # The instrument is scanning.
  STATUS_WaitingForTrigger =    32  # The instrument is waiting for a trigger.
  STATUS_USB_MSD_detected  =   128  # A USB mass storage device (USB drive) has been detected.
  STATUS_ConfigChanged     =   256  # The instrument configuration has changed.
  STATUS_InstrumentLocked  =  1024  # The instrument is locked.
  STATUS_GlobalError       =  8192  # An error is in the global error queue.
  STATUS_Busy              = 16384  # The instrument is busy.

  # For commanding relays
  OPEN                     = 0
  CLOSE                    = 1
  ON                       = CLOSE
  OFF                      = OPEN
  RELAY_NORMALLY_OPEN      = 1
  RELAY_NORMALLY_CLOSED    = 2

  #################################################
  #
  # Signals
  #

  # Incoming
  DoSetRelayState   = Signal(str,int)     # ChannelList e.g. '218:220', and 0 or 1 (tAgilent.ON or OFF)
  DoGetRelayState   = Signal(str, list, QMutex, QWaitCondition)         # ChannelList, ResultList, mutex, and wait condition

  # Outbound
  # RelayStateInfo    = Signal(dict)         # Dictionary of channel, value


  #################################################
  # AgilentChannelListToPythonList
  #
  # Expands an Agilent channel list like "101:103,204:208,309" into a fully
  # elaborated list of channel numbers for Python

  def AgilentChannelListToPythonList(ChannelList):
    result = []
    for part in ChannelList.split(','):
      if ':' in part:
        start, end = map(int, part.split(':'))
        result.extend(range(start, end + 1))
      else:
        result.append(int(part))
    return result


  ###############################################
  # Constructor 
  # 
  # INPUTS:
  #     

  def __init__(self, deviceName, FullScanChannelList, TypeKhermocoupleChannels, GhiChannel, 
                     DniChannel, NipCalibrationFactorInMicrovolts,
                     ChannelForDisplayOnFrontPanel, parent=None):
    super().__init__(parent)   # QObject constructor

                     
    # Create the resource manager if it doesn't exist yet
    if tAgilent.PyVisaResourceManager is None:
      tAgilent.PyVisaResourceManager = pyvisa.ResourceManager()
      print('Created pyvisa resource manager, found:')
      print(tAgilent.PyVisaResourceManager.list_resources())

    # Mutex for controlling access to the device
    self._lock          = QRecursiveMutex()
    self.RetryTimer     = QElapsedTimer()
    self.RetryTimeoutMs = AGILENT_RETRY_TIMEOUT_SECS * 1000  # Convert minutes to milliseconds

    # Remember our arguments for use in the call to OpenDevice
    # We remember rather than call so that we can try open again later if it fails at first
    self.DeviceName                       = deviceName
    self.FullScanChannelList              = FullScanChannelList
    self.TypeKhermocoupleChannels         = TypeKhermocoupleChannels
    self.GhiChannel                       = GhiChannel
    self.DniChannel                       = DniChannel
    self.NipCalibrationFactorInMicrovolts = NipCalibrationFactorInMicrovolts
    self.ChannelForDisplayOnFrontPanel    = ChannelForDisplayOnFrontPanel

    # Explode the channel list as provided into a fully elaborated list
    # We can do this in the constructor becuase it doesn't require the device to be open
    self.ChannelList = tAgilent.AgilentChannelListToPythonList(FullScanChannelList)

    # Connect signals
    self.DoSetRelayState.connect(self._SetRelayState)
    self.DoGetRelayState.connect(self._GetRelayState)

    self.OpenAndConfigureDevice()


  ###############################################
  # Destructor
  # 
  # INPUTS:
  #     
    
  def __del__(self):
    if not self.device is None:
      self.device.close()


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
  # OpenAndConfigureDevice
  # 
  # INPUTS:
  #   Member variables that mirror all the constructor arguments
  #   
    
  def OpenAndConfigureDevice(self):
    self.device = None

    try:
      self.device              = tAgilent.PyVisaResourceManager.open_resource(self.DeviceName) 
      self.device.baud_rate    = tAgilent.BAUD_RATE
      self.device.data_bits    = tAgilent.DATA_BITS
      self.device.parity       = tAgilent.PARITY 
      self.device.stop_bits    = tAgilent.STOP_BITS
      self.device.flow_control = tAgilent.FLOW_CONTROL
      self.device.timeout      = 1000 * tAgilent.TIMEOUT_SECS
    except:
      self.device = None
      print('tAgilent: Could not open device ', self.DeviceName, ', will retry in ', AGILENT_RETRY_TIMEOUT_SECS/60.0, ' minutes')
      self.RetryTimer.start()
      return
    
    # Reset the unit
    self.Reset()
     
    if not self.TypeKhermocoupleChannels is None:
      self.ConfigureChannelsAsThermocouple(self.TypeKhermocoupleChannels, 'K')

    if not self.GhiChannel is None:
      self.ConfigureChannelsforGHI(self.GhiChannel)

    if not self.DniChannel is None:
      self.ConfigureChannelsforDNI(self.DniChannel, self.NipCalibrationFactorInMicrovolts)

    if not self.ChannelForDisplayOnFrontPanel is None:
      self.SelectChannelToDisplayOnFrontPanel(self.ChannelForDisplayOnFrontPanel)

    self.ConfigureScanList(self.FullScanChannelList)
 

  ###############################################
  # IsDeviceOpen
  # 
  # Returns true if the device is open.  If it is not open, it will check the retry timer.
  # If the retry timer has expired, it will try again to open the device.
  #   
 
  def IsDeviceOpen(self):
    if not self.device is None:
      return True
    # If the device is not open, see if the retry timer has timed out
    if self.RetryTimer.elapsed() >= self.RetryTimeoutMs:
      self.OpenAndConfigureDevice()
    return not (self.device is None)


  ###############################################
  # Reset - Resets device to factory reset/power-on state
  # 

  @requires_device_open()
  @with_lock
  def Reset(self):
    # Clear the Agilent of any data stored in memory from previous scans
    self.device.write('*CLS')     

    # Reset the Agilent of any settings already in the device
    ### NOTE: *RST is a factory reset.
    # To restore to state at last power-on, use "*RCL 0" instead.  But *RST is okay.  Per p. 190 of
    # the manual, the remote interface settings are not reset by a factory reset.
    self.device.write('*RST')

    # This is necessary in order to avoid input buffer overruns
    QThread.sleep(1)

    # Configure the unit to not report units or channel numbers or time - just readings
    self.device.write('FORMAT:READING:UNIT OFF')
    self.device.write('FORMAT:READING:CHANNEL OFF')
    self.device.write('FORMAT:READING:TIME OFF')
    self.device.write('FORMAT:READING:ALARM OFF')


  ###############################################
  # ConfigureChannelsforDNI
  #
  # INPUTS:
  #   ChannelList - List of channels, in the form, e.g., '101:105,108,111,112,204:209'
  #   NipCalibrationFactorInMicrovolts - Microvolts per W/m^2 from the nameplate on the NIP 

  @requires_device_open()
  @with_lock
  def ConfigureChannelsforDNI(self,ChannelList,NipCalibrationFactorInMicrovolts):
    scanlist = '(@' + str(ChannelList) + ')'
    # Configure channel list for DC voltage reading, 10 mV range
    # E.g., one of our NIPs has a calibration factor of 8.23 uV per W/m^2
    # So at 1000 W/m^2, it would read 8.23 mV.  So 10 mV is a good range.
    self.device.write('CONF:VOLT:DC  0.010,DEF,' + scanlist)
    
    # Enable scaling from volts to W/m^2.  We want the reciprocal of 0.00000823, times 1.08 (1.19?) to 
    # account for the loss through the dome
    gain = NIP_COVER_GLASS_SCALE_FACTOR / (NipCalibrationFactorInMicrovolts / 1e6)
    print("Setting NIP scale factor to ", f"{gain:.1f}")
    self.device.write('CALC:SCAL:GAIN ' + f"{gain:.1f}" + ',' + scanlist)
    self.device.write('CALC:SCAL:OFFS 0.0,' + scanlist)
    self.device.write('CALC:SCAL:STAT ON,' + scanlist)
    self.device.write('CALC:SCAL:UNIT "Wm2",'+ scanlist)

  
  ###############################################
  # SelectChannelToDisplayOnFrontPanel
  #
  # INPUTS:
  #   Agilent channel number - e.g. 101, 304, etc.

  @requires_device_open()
  @with_lock
  def SelectChannelToDisplayOnFrontPanel(self,Channel):
    # Convert to string in case the channel was passed in as an int
    Channel = str(Channel)

    scanlist = '(@' + Channel + ')'
    # Display GHI on the console
    self.device.write('ROUT:MON ' + scanlist)
    self.device.write('ROUT:MON:STATE ON')


  ###############################################
  # ConfigureChannelsforGHI
  #
  # INPUTS:
  #   ChannelList - List of channels, in the form, e.g., '101:105,108,111,112,204:209'
  # 

  @requires_device_open()
  @with_lock
  def ConfigureChannelsforGHI(self,ChannelList):
    scanlist = '(@' + str(ChannelList) + ')'
    # Configure channel list for DC voltage reading, 0-10V range
    self.device.write("CONF:VOLT:DC 10,DEF, " + scanlist)

    # Enable scaling from volts to W/m^2.  The device is calibrated so that 5V = 1000 W/m^2
    self.device.write("CALC:SCAL:GAIN 200.0," + scanlist)
    self.device.write("CALC:SCAL:OFFS 0.0," + scanlist)
    self.device.write("CALC:SCAL:STAT ON," + scanlist)
    self.device.write('CALC:SCAL:UNIT "Wm2",'+ scanlist)


  ###############################################
  # ConfigureChannelsAsThermocouple 
  #
  # INPUTS:
  #   ChannelList - List of channels, in the form, e.g., '101:105,108,111,112,204:209'
  #   Type        - A single character, like 'K' for type K thermocouples
  # 

  @requires_device_open()
  @with_lock
  def ConfigureChannelsAsThermocouple(self,ChannelList,TCType):
    scanlist = '(@' + ChannelList + ')'

    ChannelConfCommand   = 'CONF:TEMP  TC,' + TCType + ',' + scanlist
    UnitsConfCommand     = 'UNIT:TEMP C,' + scanlist

    # Enable the thermocouple check feature (opens are reported as “+9.90000000E+37”)
    TcCheckEnableCommand = 'SENS:TEMP:TRAN:TC:CHECK ON,' + scanlist

    # Set the reference junction to internal.  By defaulit, a fixed reference junction temp of 0.0 
    # is used.  We want to do better than that.
    TcSetReferemceCommand = 'TEMPerature:TRANsducer:TCouple:RJUNction:TYPE INT,' + scanlist

    self.device.write(ChannelConfCommand)
    self.device.write(UnitsConfCommand)
    self.device.write(TcCheckEnableCommand)
    self.device.write(TcSetReferemceCommand)


  ###############################################
  # ConfigureScanList 
  #
  # Once all channels have been configured, we now prepare the full scan list
  # The scan will then occur when a trigger is sent.
  # 

  @requires_device_open()
  @with_lock    
  def ConfigureScanList(self, FullScanChannelList):
    scanlist = '(@' + FullScanChannelList + ')'
    self.device.write("ROUTE:SCAN " + scanlist) 

    # Set the trigger source to manual, and a single sweep
    # The "BUS" trigger source means software, i.e. from the GPIB bus, even though we
    # use the serial port rather than the bus.
    #self.device.write('TRIG:SOURCE BUS')  

    # We use IMMediate trigger mode, since we are using READ?.  See p. 1508 of the command manual.  READ?
    # puts the device in "Wait-for-trigger" mode, and the IMM means that the trigger occurs immediately.
    # This is simpler than using BUS then INIT then *TRG
    self.device.write('TRIG:SOURCE IMM')  
    self.device.write('TRIG:COUNT 1') 


  ###############################################
  # FlushInputBuffer
  #
  # Clears any characters that have been sent by the instrument.  May be useful in 
  # the event of a timeout from a previous READ? operationn
  #
  # The approach is to read characters with the timeout set to zero, then put the 
  # timeout back

  @requires_device_open()
  @with_lock
  def FlushInputBuffer(self):
    curTimeout          = self.device.timeout 
    self.device.timeout = 0

    while True:
      try:
        data = self.device.read_raw()
        if not data:
          break
      except pyvisa.errors.VisaIOError:
        break

    self.device.timeout = curTimeout


  ###############################################
  # Read
  #
  # Runs a scan of the defined channel list.
  #
  # The instrument scans the list of channels in ascending order from
  # slot 100 through slot 300 (channels are re-ordered as needed)
  # 
  # RETURNS:
  #   A comma-separated list of values.  If the reading times out, it will return -1 for all readings

  @requires_device_open()
  @with_lock
  def Read(self, bTrimCrLf):
    # Flush any characters in the port.  This is defensive, in case the last read timed out and then actually returned something later.
    self.FlushInputBuffer()

    # Arm the scan.  It is now waiting for a trigger, but will go immediately since trigger mode is IMM.
    self.device.write('READ?')
    # self.device.write('*TRG')   # See comment about triggering in previous routine

    # This doesn't seem to work.  It seems that we can't read anything because the read itself
    # is tying up the output buffer
    #if self.WaitForScanToComplete() < 0:
    #  return [-1]*len(self.ChannelList)
    # Instead, simply insert a delay

    try:
      response = self.device.read()
    except pyvisa.errors.VisaIOError:
      print('Agilent timeout, Retrying...')
      try:
        response = self.device.read()
      except pyvisa.errors.VisaIOError:
        print('Agilent 2nd Timeout, bailing out')
        minus_ones = [-1]*len(self.ChannelList)
        return ','.join(str(num) for num in minus_ones)

    if bTrimCrLf:
      response = response.strip()  #[:-2]
      
    return response


  ###############################################
  # WaitForScanToComplete
  #
  # Reads the system status register and waits for not busy / not scanning
  #
  # RETURNS:
  #   0 after a successful wait, -1 if timed out

  @requires_device_open()
  @with_lock
  def _WaitForScanToComplete(self, timeout = 3):
    IsBusyOrScanning = True
    while IsBusyOrScanning:
      StatusReg = self.device.query('STAT:OPER:COND?')
      IsBusyOrScanning = (StatusReg & tAgilent.STATUS_Scanning | StatusReg & tAgilent.STATUS_Busy) != 0
      # Check for timeout, pause it we need to try again
      if IsBusyOrScanning:
        timeout = timeout - 0.1
        if (timeout < 0):
          return -1
        QThread.msleep(100)

    return 0


  ###############################################
  # _SetRelayState 
  #
  # Opens or closes the specified relays
  #
  # INPUTS:
  #   channel list - channel list string
  #   State        - tAgilent.OPEN or tAgilent.CLOSE
  # 

  @requires_device_open()
  @with_lock    
  def _SetRelayState(self, ChannelList, State):
    if State == self.OPEN:
      Command = 'ROUTE:OPEN '
    elif State == self.CLOSE:
      Command = 'ROUTE:CLOS '
    else:
      raise ValueError
    
    scanlist = '(@' + ChannelList + ')'
    self.device.write(Command + scanlist) 


  ###############################################
  # _GetRelayState - Returns the state of the specified relays
  #
  # INPUTS:
  #   channel list - channel list (string) of relays to read
  #   RelayList    - should be an empty list.  It will be modified by this function
  #   mutex, condition - condition variable and mutex to guard and block on the result
  # RETURNS:
  #   RelayStateList - will be modified to be a list of relay readings, as 0's and 1's
  
  @requires_device_open()
  @with_lock    
  def _GetRelayState(self, ChannelList, RelayStateList: list, mutex:QMutex = None, condition:QWaitCondition = None):
    Command = 'ROUTE:CLOS? '
    
    scanlist = '(@' + ChannelList + ')'
    self.device.write(Command + scanlist)

    try:
      response = self.device.read()
      response = response.strip()  #[:-2]
    except pyvisa.errors.VisaIOError:
      #print('Agilent timeout reading relay state, Retrying...')
      return []

    # Remove CrLf:

      
    # PythonChannelList = tAgilent.AgilentChannelListToPythonList(ChannelList)
    # RelayStateList    = list(map(int,response.split(',')))

    # Create a dictionary from the two lists
    # RelayStateDict = {channel: value for channel, value in zip(PythonChannelList, RelayStateList)}

    # Emit the signal
    # self.RelayStateInfo.emit(RelayStateDict)

    # If no mutexes or whatnot, it's a simple function call
    if (mutex is None) or (condition is None):
      RelayStateList.append(list(map(int,response.split(','))))
    else:
      with QMutexLocker(mutex):
        RelayStateList.append(list(map(int,response.split(','))))  # Post the result
        condition.wakeAll()  # Notify the waiting thread


  ###############################################
  # SetRelayState
  #
  # INPUTS:
  #   RelayChannels - a list of relay channels in a string like '218:220'
  #   RelayType     - tAgilent.RELAY_NORMALLY_OPEN or tAgilent.RELAY_NORMALLY_CLOSED
  #   NewRelayState - True for on and False for off
  # RETURNS:
  #   True if power is on on the first realy in the list

  def SetRelayState(self, RelayChannels, RelayType, bState: bool):
    if bState:
      NewRelayState = tAgilent.ON  if RelayType == tAgilent.RELAY_NORMALLY_OPEN else tAgilent.OFF
    else:
      NewRelayState = tAgilent.OFF if RelayType == tAgilent.RELAY_NORMALLY_OPEN else tAgilent.ON

    self.DoSetRelayState.emit(RelayChannels, NewRelayState)


  ###############################################
  # GetRelayState
  #
  # If you provide a list of relays, this assumes they all have the same state and just
  # returns the first one.
  # 
  # INPUTS:
  #   RelayChannels - a relaychannel string like '218:220'
  # RETURNS:
  #   True if power is on on the first realy in the list
  # RAISES:
  #   TimeoutError if the operation times out

  def GetRelayState(self, RelayChannels, RelayType) -> bool:
    #print('Calling signalthenwait')
    #RelayStateInfo = SignalThenWaitFor(self.RelayStateInfo, SignalEmitter(self.DoGetRelayState, RelayChannels), TimeoutInMs=500)
    #print('signalthenwait returned')

    RelayStates = []  # Container for the result (mutable)

    ####
    # We do two different approaches based on whether we are in the same thread as the Agilent object
    # If in the same thread, it's a simple function call.  If in a different thread we use a condition
    # variable
    if QThread.currentThread() == self.thread():
        self._GetRelayState(RelayChannels, RelayStates)
        if RelayStates.isempty():
          raise TimeoutError("Timed out waiting for relay state")

    else:
      mutex     = QMutex()
      condition = QWaitCondition()
      with QMutexLocker(mutex):
        # Emit signal to worker thread
        self.DoGetRelayState.emit(RelayChannels, RelayStates, mutex, condition)
        # Wait for the worker to complete
        if not condition.wait(mutex, 500):  # 0.5-second timeout
          raise TimeoutError("Timed out waiting for relay state")

    # RelayStateInfo is dict.  Let's just return the value of the first entry in the dict and assume they're 
    # all the same
    #FirstRelayValue = RelayStateInfo[next(iter(RelayStateInfo))]
    FirstRelayValue = RelayStates[0]

    bRelayIsClosed  = (RelayType == self.RELAY_NORMALLY_OPEN   and FirstRelayValue == tAgilent.ON or
                       RelayType == self.RELAY_NORMALLY_CLOSED and FirstRelayValue == tAgilent.OFF)
    return bRelayIsClosed
  