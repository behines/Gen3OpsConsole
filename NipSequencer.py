#######################################################
# NipSequencer
#
# Makes decisions about operating modes, power states, etc.
#
#
## This class is mostly about the NIP tracker state.  It also controls pyranometer power,
# but that is exceptionally simple inasmuch as all it does is track sunrise/sunset.
#
# The sequencer runs in a timer callback.
#
# The current assumption is that all of the actuators needed by the sequencer are
# on a single Agilent card.  The mainframe unit is passed in to this method.  The
# individual channel assignments are coded in the Configuration below.
#
#
# We use the "transitions" state machine library at
# https://github.com/pytransitions/transitions?tab=readme-ov-file#hsm
#
# A note on how the library works.  It's confusing if you come back to 
# it after a couple of years.  What happens is that for every transition defined
# in the "transitions" array, it dynamically creates methods with those names and
# adds them to the object specified by the "model" parameter that you pass in when
# the machine is created.
#
#
# Also, a bit of info on the transitions library terminology.  It offers a pair of
# features that seem the same at first - before/after callbacks, and on_enter/on_exit
# callbacks.  The subtlety is that one is associated with *states*, while the other
# is associated with transitions.  What's the difference?  
#
# Sometimes there are transitions that just return to the same state.  (Example: 
# imagine a grandfather clock.  The vast majority of the "tick" events just
# return to the "ticking" state with no other state transitions.)  In this case,
# the "tick" event's before and after callbacks would fire, but the "ticking"
# state's on_enter and on_exit callbacks would not fire.
#
# Generally, any before() method is called before enter and exit methods are called, 
# and the after() method is called last.
#
# Then there is the prepare() method, which differs from the others in that it is called
# first and also called before any conditions are checked.  So the trigger will always
# result in a call to prepare(), even if the transition is not consummated.  Finalize
# has behavior similar to prepare, but at the end of a transition, regardless of whether
# it was taken.


#################################################

# Modules used
#

# module used to get the current date and time
from datetime       import datetime

import time

from Agilent        import tAgilent
from PowerControl   import tPowerControl
from PeriodicLogger import tPeriodicLogger
from Sun            import tSun
from transitions    import Machine
from transitions.extensions.states import add_state_features, Timeout

# module used to get the current date and time for the sun calcs
from datetime import datetime, timedelta
import pytz

from PySide6.QtCore import QObject, QTimer, Signal, QDateTime, QTimeZone

# Configuration forthe sequencer
from ConfigInfo import *


##########################################################################################
##########################################################################################
##########################################################################################
# StateMachineWithTimeouts
#
# See the doc for the transitions library to understand this bit.  This extends the base 
# functionality to add timeouts
#

@add_state_features(Timeout)
class StateMachineWithTimeouts(Machine):
    pass


##########################################################################################
##########################################################################################
##########################################################################################
# tNipSequencer
#

class tNipSequencer(QObject):   # Classes that Define or Emit Signals must derive from QObject

  NipStateUpdate      = Signal(str)
  SunriseSunsetUpdate = Signal(QDateTime,QDateTime)
  ClearSkyGhiUpdate   = Signal(float)
  NipHasDni           = Signal()

  states = [
    { 'name': 'off',     'on_enter': ['PowerDown'] },
            
    # Acquire state automatically enters track after timeout, unless another transition 
    # (namely "sun_is_not_out" has already occurred
    { 'name': 'acquire', 'on_enter': ['PowerUp'], 'timeout': NIP_ACQUIRE_TIMEOUT,     'on_timeout': 'acquire_complete' }, 
    { 'name': 'track'                              },

    # When in DNI warning, we time out to 'off' unless DNI appears before the timeout
    { 'name': 'DniWarning',                       'timeout': NIP_DNI_WARNING_TIMEOUT, 'on_timeout': 'Shutdown'         }
  ]

  # Transitions
  transitions = [ 
    # Argslist below are the args to add_transition, in order:
    #   trigger, source, dest, conditions, unless, before, after, prepare, **kwargs)

    # Waking up in the morning, or anytime the sun comes out
    [ 'sun_is_out',       'off',        'acquire'                ],

    # if the sun goes away during an acquire, it must be repeated, so we abort
    [ 'sun_is_not_out',   'acquire',    'off'                    ], 

    # if the sun goes away during an acquire, it must be repeated, so we abort
    [ 'acquire_complete', 'acquire',    'track'                  ], 

    # If we're tracking and the sun is out, we should have DNI.  If we get a NoDNI event
    # while tracking when the sun is out, we should start over and re-acquire
    # However, we don't give up immediately.  We go to "DniWarning" state, and
    # from there go on to off or back track at the next interval.
    #    Note that if the sun is *not* out, the lack of DNI is *not* a DNI warning
    # situation.  The idea behind DNI Warning is to capture the event "The NIP tracker
    # is mispointed, might need a restart."  If the sun *isn't* out and we don't see 
    # DNI, that is actually fine - what we want to do in that case is allow the 
    # tracker to continue to run open-loop.  Then when the sun comes back out it may 
    # be able to lock on again.  This is why DNI Warning is only a warning - it allows
    # time for the tracker to recover when the sun reappears.
    [ 'NoDNI',            'track',      'DniWarning', 'IsSunOut' ],

    [ 'YesDNI',           'DniWarning', 'track'                  ],

    [ 'Shutdown',         'acquire',    'off'                    ],
    [ 'Shutdown',         'DniWarning', 'off'                    ],  # Without this, the DniWarning timeout above does not do anything
    [ 'Shutdown',         'track',      'off'                    ]

  ]

  '''
  # Class methods that are dynamically created by the transitions library.  This eliminates Pylance warnings.
  # Duplicative of .pyi file, because there's no way to include a .pyi file.
  def sun_is_out      (self) -> bool: ...
  def sun_is_not_out  (self) -> bool: ...
  def acquire_complete(self) -> bool: ...
  def NoDNI           (self) -> bool: ...
  def YesDNI          (self) -> bool: ...
  def Shutdown        (self) -> bool: ...
  '''

  ###############################################
  # Constructor 
  # 
  # INPUTS:
  #   agilent - the Agilent unit with the 34903A Actuator card in it
  #   SystemState - a state dictionary (will be passed by reference)

  def __init__(self, Agilent, NipPowerChannels, NipOnOffButtonChannel, 
               PyranometerPowerChannel, Sun: tSun, PeriodicLogger: tPeriodicLogger, parent):
    super().__init__(parent)

    # Class member that is added dynamically by the transitions library.  This eliminates the Pylance warning further below.
    self.state: str

    self.agilent                 = Agilent
    self.sun                     = Sun
    self.SystemState             =   SystemState = {
                                       'GHI'         : 0,
                                       'DNI'         : 0,
                                       'ClearSkyGHI' : 0,
                                       'sunrise'     : datetime.now(pytz.timezone(SITE_TIMEZONE)) + timedelta(days=1),
                                       'sunset'      : datetime.now(pytz.timezone(SITE_TIMEZONE)) - timedelta(days=1)
                                     }

    # Create the power control objects that allow us to turn the NIP and pyranometer on and off,
    # and to press the OnOff button on the NIP
    self.NipPower         = tPowerControl(Agilent, 'NIP',          NipPowerChannels,         tAgilent.RELAY_NORMALLY_OPEN, self)
    self.PyranometerPower = tPowerControl(Agilent, 'Pyranometer',  PyranometerPowerChannel,  tAgilent.RELAY_NORMALLY_OPEN, self)
    self.NipOnOffButton   = tPowerControl(Agilent, 'NIP OnOff  ',  NipOnOffButtonChannel,    tAgilent.RELAY_NORMALLY_OPEN, self)

    # This is a little timer we use when sequencing the powering on of the NIP.  We preallocate it here
    self.NipPowerOnTimer  = QTimer(self)
    self.NipPowerOnTimer.setSingleShot(True)

    # Initialize the state machine.  We ignore invalid triggers, since our approach with
    # this machine is to simply inform the machine of stimuli and have it decide whether
    # it cares about them.
    self.StateMachine   = StateMachineWithTimeouts(model       = self,
                                  states      = tNipSequencer.states, 
                                  transitions = tNipSequencer.transitions,
                                  initial     = 'off',
                                  ignore_invalid_triggers = True)
    
    self.LastState      = self.state

    # The on-enter method is not called for the intial state.  To be sure we know
    # the state of the physical hardware, we power down so as to match the Machine's 
    # state.
    self.PowerDown()
    self.PyranometerPowerState = None

    # Connect to GHI and DNI updates from the logger
    PeriodicLogger.DniUpdate.connect(self.DniUpdate)
    PeriodicLogger.GhiUpdate.connect(self.GhiUpdate)

    # Create a timer to run the state machine periodically
    self.StateMachineTimer = QTimer(self)
    self.StateMachineTimer.setSingleShot(False)
    self.StateMachineTimer.timeout.connect(self.RunStateMachine)
    print("NIP Sequencer starting up...")
    self.StateMachineTimer.start(1000 * NIP_STATE_MACHINE_PERIOD)


  

  ###############################################
  # Destructor 
  # 
  # Turns off the NIP and pyranometer
  #     

  def __del__(self):
    # self.PowerDown()    # This is now done in the CleanUp method of MasterControl, which calls DoShutdown
    pass

  ###############################################
  # SetPyranometerPowerState 
  # 
  # Returns the system to a safe state
  #     

  def SetPyranometerPowerState(self, bOn): 
    if self.PyranometerPowerState != bOn:
      self.PyranometerPower.SetPowerState(bOn)
      print('Pyranometer power switched ' + ('on' if bOn else 'off'))
      self.PyranometerPowerState = bOn


  ###############################################
  # PowerDown 
  # 
  # Returns the system to a safe state
  #     

  def PowerDown(self):
    # Open the 12V power to the device
    # Open the soft power button
    print('NIP Tracker powering down')
    self.NipPower      .SetPowerState(False)
    self.NipOnOffButton.SetPowerState(False)


  ###############################################
  # PowerUp 
  # 
  # Apply the sequence to power up the NIP.  In order to keep the GUI responsive,
  # we do this in three parts.
  #   Turn on the 12V power to the device
  #   Wait a couple of seconds
  #   Short the soft power button for two seconds
  #     

  def PowerUp(self):
    # Turn on power to the NIP
    print('NIP Tracker powering up')
    self.NipPower      .SetPowerState(True)
    # Now set a timer to call PowerUp_part2 after a delay to let the NIP complete its power-up
    self.NipPowerOnTimer.timeout.connect(self._PowerUp_part2)
    self.NipPowerOnTimer.setSingleShot(True)
    self.NipPowerOnTimer.start(1000 * NIP_TRACKER_POWER_ON_DELAY)

  def _PowerUp_part2(self):
    # Press the soft power button, then pause...
    print('Pressing soft power button')
    self.NipOnOffButton.SetPowerState(True)
    self.NipPowerOnTimer.timeout.disconnect(self._PowerUp_part2)
    self.NipPowerOnTimer.timeout.connect(self._PowerUp_part3)
    self.NipPowerOnTimer.setSingleShot(True)
    self.NipPowerOnTimer.start(1000 * NIP_TRACKER_POWER_BUTTON_PRESS_TIME)

  def _PowerUp_part3(self):
    self.NipPowerOnTimer.timeout.disconnect(self._PowerUp_part3)
    # And now release the soft power button
    print('Releasing soft power button')
    self.NipOnOffButton.SetPowerState(False)


  ###############################################
  # IsSunOut 
  # 
  # Uses GHI to decide
  #   
      
  def IsSunOut(self):
    bIsSunOut = (self.SystemState['GHI'] > NIP_GHI_SUN_IS_OUT_THRESHOLD * self.SystemState['ClearSkyGHI'] and
                 self.SystemState['GHI'] > NIP_GHI_SUN_IS_OUT_MIN)
    return bIsSunOut


  ###############################################
  # DniUpdate - called when a DNI update signal is received from the PeriodicLogger
  # 

  def DniUpdate(self, DNI):
    self.SystemState['DNI'] = DNI


  ###############################################
  # GhiUpdate - called when a GHI update signal is received from the PeriodicLogger
  # 

  def GhiUpdate(self, GHI):
    self.SystemState['GHI'] = GHI


  ###############################################
  # DoShutdown - Shuts down the NIP sequencer
  # 

  def DoShutdown(self):
    print("NIP Sequencer exiting")
    # Call the Shutdown method from the transitions library to enter the Shutdown state
    self.Shutdown()
    

  ###############################################
  # RunStateMachine - Execute one iteration of the state machine
  # 
  # Look at the state of the world and emit triggers as appropriate.
  #     

  def RunStateMachine(self):
    sunrise: datetime
    sunset : datetime

    # A state transition may have occurred while we were asleep, as a result of a timeout
    if self.LastState != self.state:
      print('NIP timeout transition: ' + self.LastState + ' -> ' + self.state)
      self.LastState = self.state

    sunrise, sunset, GHI_clear_sky = self.sun.GetValues()
    now                            = datetime.now(self.sun.timezone)

    # Send signals if warranted
    self.ClearSkyGhiUpdate.emit(GHI_clear_sky)
    if (self.SystemState['sunrise'] != sunrise or
        self.SystemState['sunset']  != sunset):
      # Convert the sunrise and sunset to QDateTime
      QSunrise = QDateTime.fromSecsSinceEpoch(int(sunrise.timestamp()), QTimeZone(SITE_TIMEZONE.encode('utf-8')))
      QSunset  = QDateTime.fromSecsSinceEpoch(int(sunset .timestamp()), QTimeZone(SITE_TIMEZONE.encode('utf-8')))
      self.SunriseSunsetUpdate.emit(QSunrise, QSunset)
      
    # Update our own internal values
    self.SystemState['sunrise']     = sunrise
    self.SystemState['sunset']      = sunset
    self.SystemState['ClearSkyGHI'] = GHI_clear_sky

    bDaytime = (now > sunrise) and (now < sunset)
    if not bDaytime:
      # Zero the DNI and GHI, to avoid any stale values or nonsensical values
      self.SystemState['GHI'] = 0
      self.SystemState['DNI'] = 0
      bHaveGHI = False
      bHaveDNI = False
    else:
      bHaveGHI = self.IsSunOut()
      bHaveDNI = self.SystemState['DNI'] > NIP_DNI_THRESHOLD

    self.SetPyranometerPowerState(bDaytime)

    if not bDaytime:
      self.Shutdown()

    ################
    # Things we do if it's daytime
    else:
      # Ensure that the pyranometer is on
      # Turn on 
      if bHaveGHI:
        self.sun_is_out()
      else:
        self.sun_is_not_out()

      if bHaveDNI:
        self.YesDNI()
        self.NipHasDni.emit()
      else:
        self.NoDNI()
    
    if self.LastState != self.state:
      print('NIP state transition: ' + self.LastState + ' -> ' + self.state)
      self.LastState = self.state
      
    self.NipStateUpdate.emit(self.state)