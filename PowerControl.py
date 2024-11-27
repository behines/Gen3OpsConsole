#######################################################
# PowerControl
#
# Controls one or several power relays on an Agilent 34903A Actuator module
#




#################################################

# Modules used
#

from Agilent        import tAgilent
from PySide6.QtCore import QObject, Signal 


class tPowerControl(QObject):

  ###############################################
  # Constants 
  # 



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
  #   RelayType - tAgilent.RELAY_NORMALLY_OPEN or tAgilent.RELAY_NORMALLY_CLOSED 

  def __init__(self, Agilent: tAgilent, Name, PowerRelayChannels, RelayType, parent=None):
    super().__init__(parent)   

    self.agilent       = Agilent
    self.Name          = Name
    self.RelayType     = RelayType
    self.RelayChannels = PowerRelayChannels

    
  ###############################################
  # PowerOn
  # 
  
  def PowerOn(self):
    print('Powering on', self.Name)
    self.agilent.SetRelayState(self.RelayChannels, self.RelayType, True)


  ###############################################
  # PowerOff
  # 
  
  def PowerOff(self):
    print('Powering off', self.Name)
    self.agilent.SetRelayState(self.RelayChannels, self.RelayType, False)


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
  # RAISES:
  #   TimeoutError if the operation times out

  def GetPowerState(self) -> bool:
    bRelayIsClosed = self.agilent.GetRelayState(self.RelayChannels, self.RelayType)
    return bRelayIsClosed
  