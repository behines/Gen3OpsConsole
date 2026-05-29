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
# the package works.  There is also a document Gen3 Ops Console.docx that includes
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

  StateUpdate       = Signal(str)
  DisableSeq        = Signal()
  EnableSeq         = Signal()
  SetFullAutomation = Signal(bool)

  states = [
    { 'name': 'Disabled',                                  },
    { 'name': 'Night',        'on_enter': ['StowAll']      },
    { 'name': 'Daytime'                                    }, 
    { 'name': 'PoweredOff',   'on_enter': ['MotorPowerOff', 'UsbPowerOff'],  'timeout': COLL_POWEROFF_TIMEOUT,  'on_timeout': 'PowerOn'   },
    { 'name': 'PoweringUp',   'on_enter': ['UsbPowerOn',   'MotorPowerOn'], 'timeout': COLL_POWERON_TIMEOUT,   'on_timeout': 'StartStow' },
    { 'name': 'Stow',         'on_enter': ['StowAll'],      'timeout': COLL_UNSTICK_TIMEOUT,   'on_timeout': 'DoOff' }, 
  ]

  # Transitions
  transitions = [ 
    # Argslist below are the args to add_transition, in order:
    #   trigger, source, dest, conditions, unless, before, after, prepare, **kwargs)

    # DNI appearing when we're in Off tells us to start our day
    [ 'YesDNI',       'Night',       'Daytime'     , 'IsBeforeBedtime' ],  # Only switch to daytime if it's not after bedtime

    # If we decide the day is done, it's time to power everyone off
    [ 'DayIsDone',    'Daytime',     'PoweredOff'             ],

    # A PowerOn transition takes us into PoweringUp
    [ 'PowerOn',      'PoweredOff',  'PoweringUp'             ], 

    # StartStow transition causes us to enter Stow, where we wait for them all to finish stowing
    [ 'StartStow',    'PoweringUp',  'Stow'                   ], 

    # DoOff transition causes us to enter off
    [ 'DoOff',        'Stow',        'Night'                  ],

    [ 'Disable',      'Night',        'Disabled'              ],
    [ 'Disable',      'Daytime',      'Disabled'              ],
    [ 'Disable',      'PoweredOff',   'Disabled'              ],
    [ 'Disable',      'PoweringUp',   'Disabled'              ],
    [ 'Disable',      'Stow',        'Disabled'               ],

    [ 'Enable',       'Disabled',     'Daytime'               ]   # When re-enabled we'll jump right into Daytime mode
  ]

  '''
  # Class methods that are dynamically created by the transitions library.  This eliminates Pylance warnings.
  # Duplicative of .pyi file, because there's no way to include a .pyi file.
  def YesDNI    (self) -> bool: ...
  def DayIsDone (self) -> bool: ...
  def PowerOn   (self) -> bool: ...
  def StartStow (self) -> bool: ...
  def DoOff     (self) -> bool: ...
  '''

  ###############################################
  # Constructor 
  # 
  # INPUTS:
  #   agilent - the Agilent unit with the 34903A Actuator card in it
  #   SystemState - a state dictionary (will be passed by reference)

  def __init__(self, Collectors : list[tCollector], UsbHubPower : tPowerControl, MotorPower : tPowerControl, SunriseSunsetSignal : Signal, NipHasDniSignal : Signal, parent):
    super().__init__(parent)

    # Class member that is added dynamically by the transitions library.  This eliminates the Pylance warning further below.
    self.state: str

    # Initialize the state machine.  We ignore invalid triggers, since our approach with
    # this machine is to simply inform the machine of stimuli and have it decide whether
    # it cares about them.
    self.StateMachine   = StateMachineWithTimeouts(model       = self,
                                  states      = tCollectorSequencer.states, 
                                  transitions = tCollectorSequencer.transitions,
                                  initial     = 'Night',
                                  ignore_invalid_triggers = True,
                                  after_state_change = 'NotifyStateChange')
    
    self.LastState      = 'Night'

    # Set sunrise and sunset to be in the future.  We will get actual values soon
    ThisTimeInTwoDays  = QDateTime.currentDateTime().addDays(2)
    self.Sunrise       = ThisTimeInTwoDays
    self.Sunset        = ThisTimeInTwoDays
    self.LatestEndTime = ThisTimeInTwoDays

    self.Collectors  = Collectors
    self.UsbHubPower = UsbHubPower
    self.MotorPower  = MotorPower

    self.CollectorStatus = {
       Collector.CollectorName: {
          'HasRebootedYet'    : False,
          'IsDoneForTheDay'   : False,
       }
       for Collector in Collectors
    }

    # Connect signals
    SunriseSunsetSignal   .connect(self.UpdateSunriseSunset)
    if USE_DNI_TO_START_DAY and PROJECT_CONFIG.bHasDniSensor:
      NipHasDniSignal.connect(self.YesDNI)             # Just directly connect this to the state machine transition method

    self.bFullAutomation = True
    self.SetFullAutomation.connect(self.SetAutomationLevel)
    self.EnableSeq        .connect(self.EnableSequencer)
    self.DisableSeq       .connect(self.DisableSequencer)

    # Create a timer to run the state machine periodically
    self.StateMachineTimer = QTimer(self)
    self.StateMachineTimer.setSingleShot(False)
    self.StateMachineTimer.timeout.connect(self.RunStateMachine)
    print("Collector Sequencer starting up...", flush=True)
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
  # EnableSequencer

  def EnableSequencer(self):
    self.Enable()      # Call the state machine transition.  Only makes sense if we're in Disabled, else ignored


  #######################################################
  # DisableSequencer

  def DisableSequencer(self):
    self.Disable()     # Call the state machine transition. 


  #######################################################
  # SetAutomationLevel - Callback for signal
  #

  def SetAutomationLevel(self, bFullAuto):
    self.bFullAutomation = bFullAuto
    

  #######################################################
  # UpdateSunriseSunset

  def UpdateSunriseSunset(self, Sunrise: QDateTime, Sunset: QDateTime):
    self.Sunrise = Sunrise
    self.Sunset  = Sunset

    self.LatestEndTime = self.Sunset.addSecs(-60 * COLLECTOR_STOP_BEFORE_SUNSET_MINUTES)


  #######################################################
  # IsBeforeBedtime - True only if it's not before everyone's bedtime
  #

  def IsBeforeBedtime(self) -> bool:
    # Get current time
    current_time = QDateTime.currentDateTime()
    # Convert current time to SITE_TIMEZONE just in case it's not set the same on this computer
    time_zone    = QTimeZone(SITE_TIMEZONE.encode('utf-8'))
    current_time = current_time.toTimeZone(time_zone)

    
    # Compare to the "latest end time" computed during UpdateSunriseSunset
    bIsBeforeBedtime = self.LatestEndTime > current_time
    # print(f'IsBeforeBedtime: {bIsBeforeBedtime}', flush=True)
          
    return bIsBeforeBedtime
  

  ###############################################
  # StowAll 
  # 
  # Comamnd all collectors to Stow
  #     

  def StowAll(self): 
    print('Sending Stow to all', flush=True)
    for Collector in self.Collectors:
      Collector.DoStow.emit() 


  ###############################################
  ###############################################
  # UsbPowerOff 
  # 
  # Turn off USB Power
  #     

  def UsbPowerOff(self): 
    if self.UsbHubPower is not None:
      self.UsbHubPower.SetPowerState(False)

  
  ###############################################
  # UsbPowerOn 
  # 
  # Turn on USB Power
  #     

  def UsbPowerOn(self):
    if self.UsbHubPower is not None:
      self.UsbHubPower.SetPowerState(True)


  ###############################################
  # MotorPowerOff

  def MotorPowerOff(self):
    if self.MotorPower is not None:
      self.MotorPower.SetPowerState(False)


  ###############################################
  # MotorPowerOn

  def MotorPowerOn(self):
    if self.MotorPower is not None:
      self.MotorPower.SetPowerState(True)



  ###############################################
  # NotifyStateChange - Callback for state change events
  # 
  # Called by the transitions library after a state change
  #     

  def NotifyStateChange(self):
    print('Collector sequencer transition: ' + self.LastState + ' -> ' + self.state, flush=True)
    self.LastState = self.state
    self.StateUpdate.emit(self.state)


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



    StartTime = self.Sunrise.addSecs( 60 * COLLECTOR_START_AFTER_SUNRISE_MINUTES)
    EndTime   = self.Sunset .addSecs(-60 * COLLECTOR_STOP_BEFORE_SUNSET_MINUTES)

    if self.state == 'Night' and (not USE_DNI_TO_START_DAY or not PROJECT_CONFIG.bHasDniSensor) and current_time >= StartTime and current_time < EndTime:
      self.YesDNI()

    # Really the only work we have to do is if our state is 'Daytime'.  All other state transitions
    # are handled automatically by timeouts.
    if self.state != 'Daytime':
      return
    
    bAllAreDone = True

    for Collector in self.Collectors:
      # We're in no rush here, make sure everything else stays responsive
      QCoreApplication.processEvents()

      status = self.CollectorStatus[Collector.CollectorName]

      bDontStartYet     = (current_time <  StartTime)
      bShouldBeTracking = (current_time >= StartTime) and (current_time <= EndTime)
      bShouldBeDone     =                                 (current_time >  EndTime)

      if (bDontStartYet):
        status['HasRebootedYet']   = False
        status['IsDoneForTheDay']  = False
        bAllAreDone                = False

      bIsTracking = Collector.IsTrackingOrAttemptingToTrack()

      if bShouldBeTracking:
        status['IsDoneForTheDay']  = False  # This is important for cases where the sun comes out midday
        if bIsTracking:
          status['HasRebootedYet'] = True   # Don't reboot a collector that is already successfully tracking
        elif not status['HasRebootedYet']:
          print(f'Sequencer: Requesting {Collector.CollectorName} to Reboot', flush=True)
          Collector.DoReboot.emit()
          status['HasRebootedYet'] = True
        # Next.  If in full automation, we start to track from states including STOW states and HOME_COMPLETE.  In Semi Automation, we only start from Off.
        elif Collector.IsOff() or (self.bFullAutomation and Collector.CanTrackIfRequested()):
          print(f'Sequencer: Requesting {Collector.CollectorName} to Track', flush=True)
          Collector.DoTrack.emit()

      elif (bShouldBeDone and not status['IsDoneForTheDay']):
        print(f'Sequencer: Requesting {Collector.CollectorName} to Stow', flush=True)
        Collector.DoStow.emit()
        status['IsDoneForTheDay']  = True

      # If any are not done, then all are not done
      if not status['IsDoneForTheDay']:
        bAllAreDone = False

    # We've completed our loop over all 15 collectors
    # If all are done for the day, begin wrapping up the day
    if bAllAreDone:
      self.DayIsDone()
