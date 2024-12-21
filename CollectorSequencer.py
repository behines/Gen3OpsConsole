#######################################################
# CollectorSequencer
#
# Makes decisions about when to start up and stow collectors each day.
#
# For details on the 
#
# This class is mostly about the NIP tracker state.  It also controls pyranometer power,
# but that is exceptionally simple inasmuch as all it does is track sunrise/sunset
#
#
# The sequencer runs in a timer callback that checks on things once a minute.
#
# We use the "transitions" state machine library at
# https://github.com/pytransitions/transitions?tab=readme-ov-file#hsm
#
# See the comments at the top of NipSequencer.py for some explanation on how
# the package works.  There is also a document Gen2 Ops Console.docx that includes
# information on sequencing.
#

#################################################

# Modules used
#

# module used to get the current date and time
from datetime       import datetime

import time

from transitions    import Machine
from transitions.extensions.states import add_state_features, Timeout

# module used to get the current date and time for the sun calcs
from datetime import datetime, timedelta
import pytz

from PySide6.QtCore import QObject, QTimer, Signal, QDateTime, QTimeZone, QCoreApplication

from Collector      import tCollector
from PowerControl   import tPowerControl

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
# tCollectorSequencer
#

class tCollectorSequencer(QObject):   # Classes that Define or Emit Signals must derive from QObject

  NipStateUpdate      = Signal(str)
  SunriseSunsetUpdate = Signal(QDateTime,QDateTime)
  ClearSkyGhiUpdate   = Signal(float)

  states = [
    { 'name': 'off',        'on_enter': ['StowAll']      },
            
    { 'name': 'daytime'                            }, 
    { 'name': 'PoweredOff',   'on_enter': ['UsbPowerOff'],  'timeout': COLL_POWEROFF_TIMEOUT,  'on_timeout': 'PowerOn'   }, 
    { 'name': 'PoweringUp',   'on_enter': ['UsbPowerOn'],   'timeout': COLL_POWERON_TIMEOUT,   'on_timeout': 'Unstick' }, 
    { 'name': 'Unstick-stow', 'on_enter': ['UnstickAll'],   'timeout': COLL_UNSTICK_TIMEOUT,   'on_timeout': 'DoOff' }, 
  ]

  # Transitions
  transitions = [ 
    # Argslist below are the args to add_transition, in order:
    #   trigger, source, dest, conditions, unless, before, after, prepare, **kwargs)

    # DNI appearing when we're in Off tells us to start our day
    [ 'YesDNI',       'off',         'daytime'                ],

    # If we decide the day is done, it's time to power everyone off
    [ 'DayIsDone',    'daytime',     'PoweredOff'             ],

    # A PowerOn transition takes us into PoweringUp
    [ 'PowerOn',      'PoweredOff',  'PoweringUp'             ], 

    # Unstick transition causes us to enter Unstick-stow, where we wait for them all to finish unsticking
    [ 'Unstick',      'PoweringUp',  'Unstick-stow'           ], 

    # DoOff transition causes us to enter off
    [ 'DoOff',        'Unstick-stow', 'off'                   ]

  ]

  '''
  # Class methods that are dynamically created by the transitions library.  This eliminates Pylance warnings.
  # Duplicative of .pyi file, because there's no way to include a .pyi file.
  def YesDNI    (self) -> bool: ...
  def DayIsDone (self) -> bool: ...
  def PowerOn   (self) -> bool: ...
  def Unstick   (self) -> bool: ...
  def DoOff     (self) -> bool: ...
  '''

  ###############################################
  # Constructor 
  # 
  # INPUTS:
  #   agilent - the Agilent unit with the 34903A Actuator card in it
  #   SystemState - a state dictionary (will be passed by reference)

  def __init__(self, Collectors : list[tCollector], UsbHubPower : tPowerControl, SunriseSunsetSignal : Signal, NipHasDniSignal : Signal, parent):
    super().__init__(parent)

    # Class member that is added dynamically by the transitions library.  This eliminates the Pylance warning further below.
    self.state: str

    # Initialize the state machine.  We ignore invalid triggers, since our approach with
    # this machine is to simply inform the machine of stimuli and have it decide whether
    # it cares about them.
    self.StateMachine   = StateMachineWithTimeouts(model       = self,
                                  states      = tCollectorSequencer.states, 
                                  transitions = tCollectorSequencer.transitions,
                                  initial     = 'off',
                                  ignore_invalid_triggers = True)
    
    self.LastState      = self.state

    # Set sunrise and sunset to be in the future.  We will get actual values soon
    ThisTimeInTwoDays = QDateTime.currentDateTime().addDays(2)
    self.Sunrise = ThisTimeInTwoDays
    self.Sunset  = ThisTimeInTwoDays

    self.Collectors  = Collectors
    self.UsbHubPower = UsbHubPower

    self.CollectorStatus = {
       key: {
          'HoursAfterSunrise' : values[0],
          'HoursBeforeSunset' : values[1],
          'IsDoneForTheDay'   : False,
       }
       for key, values in COLLECTOR_START_AND_END_TIMES.items()
    }

    # Connect signals
    SunriseSunsetSignal.connect(self.UpdateSunriseSunset)
    NipHasDniSignal    .connect(self.YesDNI)             # Just directly connect this to the state machine transition method

    # Create a timer to run the state machine periodically
    self.StateMachineTimer = QTimer(self)
    self.StateMachineTimer.setSingleShot(False)
    self.StateMachineTimer.timeout.connect(self.RunStateMachine)
    print("Collector Sequencer starting up...")
    self.StateMachineTimer.start(1000 * COLLECTOR_STATE_MACHINE_PERIOD)


  ###############################################
  # Destructor 
  # 
  # Turns off the NIP and pyranometer
  #     

  def __del__(self):
    # self.PowerDown()    # This is now done in the CleanUp method of MasterControl, which calls DoShutdown
    pass


  #######################################################
  # UpdateSunriseSunset

  def UpdateSunriseSunset(self, Sunrise: QDateTime, Sunset: QDateTime):
    self.Sunrise = Sunrise
    self.Sunset  = Sunset


  ###############################################
  # StowAll 
  # 
  # Comamnd all collectors to Stow
  #     

  def StowAll(self): 
    for Collector in self.Collectors:
      Collector.DoStow.emit() 


  ###############################################
  # UnstickAll 
  # 
  # Comamnd all collectors to Unstick then stow
  #     

  def UnstickAll(self): 
    for Collector in self.Collectors:
      Collector.DoUnstick.emit() 



  ###############################################
  # UsbPowerOff 
  # 
  # Turn off USB Power
  #     

  def UsbPowerOff(self): 
    self.UsbHubPower.SetPowerState(False)

  
  ###############################################
  # UsbPowerOn 
  # 
  # Turn on USB Power
  #     

  def UsbPowerOn(self): 
    self.UsbHubPower.SetPowerState(True)

  


  ###############################################
  # RunStateMachine - Execute one iteration of the state machine
  # 
  # Look at the state of the world and emit triggers as appropriate.
  #     

  def RunStateMachine(self):
    # Get current time
    current_time = QDateTime.currentDateTime()
    # Convert current time to SITE_TIMEZONE just in case it's not set the same on this computer
    time_zone    = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    current_time = current_time.toTimeZone(time_zone)

    # A state transition may have occurred while we were asleep, as a result of a timeout
    if self.LastState != self.state:
      print('Collector sequencer timeout transition: ' + self.LastState + ' -> ' + self.state)
      self.LastState = self.state

    # Really the only work we have to do is if our state is 'daytime'.  All other state transitions
    # are handled automatically by timeouts.
    if self.state != 'daytime':
      return
    
    bAllAreDone = True

    for Collector in self.Collectors:
      # We're in no rush here, make sure everything else stays responsive
      QCoreApplication.processEvents()

      status = self.CollectorStatus[Collector.CollectorName]

      StartTime = self.Sunrise.addSecs( 3600 * status['HoursAfterSunrise'])
      EndTime   = self.Sunset .addSecs(-3600 * status['HoursBeforeSunset'])

      bDontStartYet     = (current_time <  StartTime)
      bShouldBeTracking = (current_time >= StartTime) and (current_time <= EndTime)
      bShouldBeDone     =                                 (current_time >  EndTime)

      bIsTracking = Collector.IsTrackingOrAttemptingToTrack()
      if (bDontStartYet):
        status['IsDoneForTheDay']  = False
        bAllAreDone                = False

      if bShouldBeTracking and (not bIsTracking) and Collector.CanTrackIfRequested():
        print(f'Sequencer: Requesting {Collector.CollectorName} to Track')
        Collector.DoTrack.emit()

      elif (bShouldBeDone and not status['IsDoneForTheDay']):
        print(f'Sequencer: Requesting {Collector.CollectorName} to Stow')
        Collector.DoStow.emit()
        status['IsDoneForTheDay']  = True

      # If any are not done, then all are not done
      if not status['IsDoneForTheDay']:
        bAllAreDone = False

    # We've completed our loop over all 15 collectors
    # If all are done for the day, begin wrapping up the day
    if bAllAreDone:
      self.DayIsDone()
