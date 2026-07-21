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
    sChannelAction = 'opening' if self.RelayType == tAgilent.RELAY_NORMALLY_CLOSED else 'closing'
    print(f'Powering on {self.Name} ({sChannelAction} Agilent channels {self.RelayChannels})', flush=True)
    self.agilent.SetRelayState(self.RelayChannels, self.RelayType, True)


  ###############################################
  # PowerOff
  #

  def PowerOff(self):
    sChannelAction = 'closing' if self.RelayType == tAgilent.RELAY_NORMALLY_CLOSED else 'opening'
    print(f'Powering off {self.Name} ({sChannelAction} Agilent channels {self.RelayChannels})', flush=True)
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
    bPowerIsOn = self.agilent.GetRelayState(self.RelayChannels, self.RelayType)
    print(f'{self.Name} power readback: {"ON" if bPowerIsOn else "OFF"} (Agilent channels {self.RelayChannels})', flush=True)
    return bPowerIsOn


  ###############################################
  # LogInstrumentError - Surfaces any instrument error queued by the last relay command
  #
  # For the user-initiated (checkbox) path only - see tAgilent.LogInstrumentError.  Must NOT be
  # called from the automatic sequencer paths.

  def LogInstrumentError(self):
    self.agilent.LogInstrumentError(self.Name)
