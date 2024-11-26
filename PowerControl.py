#######################################################
# PowerControl
#
# Controls one or several power relays on an Agilent 34903A Actuator module
#




#################################################

# Modules used
#

from Agilent        import tAgilent
from Utilities      import SignalThenWaitFor, SignalEmitter
from PySide6.QtCore import Signal 


class tPowerControl:

  ###############################################
  # Constants 
  # 

  NORMALLY_OPEN   = 1
  NORMALLY_CLOSED = 2

  #################################################
  #
  # Signals
  #

  # Outbound
  PowerRelayStateUpdate = Signal(bool)


  ###############################################
  # Constructor 
  # 
  # INPUTS:
  #   agilent   - the Agilent unit with the 34903A Actuator card in it
  #   Name      - a name for display
  #   PowerRelayChannels - an Agilent-spec list of channels to switch, e.g. '201:202,205'
  #   RelayType - NORMALLY_OPEN or NORMALLY_CLOSED 

  def __init__(self, Agilent: tAgilent, Name, PowerRelayChannels, RelayType):
    self.agilent       = Agilent
    self.Name          = Name
    self.RelayType     = RelayType
    self.RelayChannels = PowerRelayChannels

    
  ###############################################
  # PowerOn
  # 
  
  def PowerOn(self):
    print('Powering on', self.Name)

    NewRelayState = tAgilent.ON if self.RelayType == self.NORMALLY_OPEN else tAgilent.OFF
    #with self.agilent as agilent:
    #  agilent.SetRelayState(self.RelayChannels, NewRelayState)
    self.agilent.DoSetRelayState.emit(self.RelayChannels, NewRelayState)


  ###############################################
  # PowerOff
  # 
  
  def PowerOff(self):
    print('Powering off', self.Name)

    NewRelayState = tAgilent.OFF if self.RelayType == self.NORMALLY_OPEN else tAgilent.ON
    #with self.agilent as agilent:
    #  agilent.SetRelayState(self.RelayChannels, NewRelayState)      
    self.agilent.DoSetRelayState.emit(self.RelayChannels, NewRelayState)



  ###############################################
  # SetPowerState
  # 
  # bState - false to turn off, true to turn on
  
  def SetPowerState(self, bState):

    if bState:
      self.PowerOn()
    else:
      self.PowerOff()

    self.PowerRelayStateUpdate.emit(bState)


  ###############################################
  # GetPowerState
  #
  # If you provide a list of relays, this assumes they all have the same state and just
  # returns the first one.
  # 
  # RETURNS:
  #   True if power is on

  def GetPowerState(self):
    #with self.agilent as agilent:
    #  agilent.GetRelayState(self.RelayChannels)
    RelayStateInfo = SignalThenWaitFor(self.agilent.RelayStateInfo, SignalEmitter(self.agilent.DoGetRelayState,self.RelayChannels))

    # RelayStateInfo is dict.  Let's just return the value of the first entry in the dict and assume they're 
    # all the same
    FirstRelayValue = RelayStateInfo[next(iter(RelayStateInfo))]

    bRelayIsClosed = (self.RelayType == self.NORMALLY_OPEN   and FirstRelayValue == tAgilent.ON or
                      self.RelayType == self.NORMALLY_CLOSED and FirstRelayValue == tAgilent.OFF)
    return bRelayIsClosed
  