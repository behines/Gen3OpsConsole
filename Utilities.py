#######################################################
# Utility functions
#
# 
#



#################################################
# Modules used
#

from PySide6.QtCore import QObject, Signal, QDateTime, QTimeZone, QTimer, QEventLoop, Qt
from ConfigInfo import *



##########################################################################################
##########################################################################################
##########################################################################################
# Decorators
#
# requires_device_open is the only device decorator now.  The with_lock locking decorator
# was removed along with the abandoned per-instrument worker-thread design - this app is
# single-threaded, so a mutex bought nothing (and a recursive one could not even prevent
# same-thread re-entrancy).
#

##############################################
# requires_device_open - Decorator that gets added to a function to cause it to 
# return immediately if the class's IsDeviceOpen() method returns False.  
# You can specify what it should return if the device is not open - the default is
# an empty string

# Simpler version a decorator - just takes the method as an argument and returns a closure "wrapper"
# that calls mehod.
#def requires_device_open(method):
#  def wrapper(self, *args, **kwargs):
#    if not self.IsDeviceOpen():
#      return
#    return method(self, *args, **kwargs)
#  return wrapper

# Fancier version.  An extra layer of closure.  The outer requires_device_open returns a closure
# "decorator", which returns a closure "wrapper", which gets called.  Note that you can't just
# say "@requires_device_open" when using it - you have to say "@requires_device_open()".  Else it 
# interprets "@requires_device_open" as a no-argument function call rather than as a decorator
# factory.  We *could* check for this by checking if the argument is callable (and thus a method),
# in which case we'd basically branch into the simpler version above.  It's simpler to just require
# the () syntax
def requires_device_open(default_return=''):
  def decorator(method):
    def wrapper(self, *args, **kwargs):
      if not self.IsDeviceOpen():
        return default_return
      return method(self, *args, **kwargs)
    return wrapper
  return decorator



##########################################################################################
##########################################################################################
##########################################################################################
# SignalThenWaitFor - Sends a stimulus then blocks until the specified signal is received
#   and
# SignalEmitter     - Helper function for packaging a signal emitter with arguments
#
# The idea here is that StimulusFuncToCall must take no arguments, but it can be a closure
# with the ability to do whatever complex operation you like.  Most often this will be
# emitting a signal..
#
# So if you want the stimulus to be emitting a signal MySignal(channel,value), then write
#    
#   SignalThenWaitFor(SomeSignalToWaitFor, SignalEmitter(MySignal,channel,value), TimeoutInMs=5000, parent=self)
#
# INPUTS:
#   SignalToWaitFor    - the routine will block until this signal arrives, or until a timeout 
#   StimulusFuncToCall - If provided, Qt will ecall this function in order to stimulate the emission of 
#                        the signal you're waiting on.  It should take no arguments.
#   TimeoutInMs        - how long to wait before giving up, 0 == forever
# RETURNS:
#   The payload that was returned by the waited-for signal, as a list of argument values

def SignalThenWaitFor(SignalToWaitFor:Signal, StimulusFuncToCall=None, TimeoutInMs=0, parent=None, *args, **kwargs):

  # To store the payload of SignalToWaitFor
  payload = []
  def capture_payload(*signal_args):
    print('SignalThenWaitFor: Signal Received, capturing payload')
    payload.extend(signal_args)     # Nonlocal not required since this is not an assignment so it has to look outside
    loop.quit()    

  bTimedOut = False
  def TimedOut():
    nonlocal bTimedOut
    bTimedOut = True
    loop.quit()   

  # This is Qt's funny way of blocking to wait for a signal.  The canonical way it to just have the signal
  # connect to loop.quit, to cause the event loop to exit.  But we also want to capture the payload.
  loop = QEventLoop(parent)
  SignalToWaitFor.connect(capture_payload)

  # We will also exit the event loop if the timer times out
  if TimeoutInMs != 0:
    Timer = QTimer(parent)
    Timer.setSingleShot(True)
    Timer.timeout.connect(TimedOut)
    #print('SignalThenWaitFor timer start')
    Timer.start(TimeoutInMs)

  print('SignalThenWaitFor: Calling StimFunc')
  if not StimulusFuncToCall is None:
    StimulusFuncToCall()
  print('SignalThenWaitFor: Starting event loop')

  #print('Exit request emitted',flush=True)
  # Block until the signal is emitted
  loop.exec()
  #print('Event loop exited',flush=True)
  if bTimedOut:
    print('SignalThenWaitFor: Event loop timeout')
    raise TimeoutError

  print('SignalThenWaitFor: Complete')

  return payload


############
# SignalEmitter helper function
def SignalEmitter(TheSignal, *args, **kwargs):
  def emitter():
      print('SignalEmitter emitting ', TheSignal)
      TheSignal.emit(*args, **kwargs)
  return emitter

############
# Diagnostic monitot that can be installed on an event loop using QThread.currentThread().eventDispatcher().installEventFilter(AnEventMonitor)
class EventMonitor(QObject):
  def eventFilter(self, obj, event):
    print(f"Event: {event.type()} processed for {obj}")
    return super().eventFilter(obj, event)  # Pass the event on



##########################################################################################
##########################################################################################
##########################################################################################
# tActiveObject - Class that implements a timer that causes PeriodicMethod to be called at the specified rate
#
# This class is meant to be inherited by any class whose main purpose is to be an "active
# object" that executes a function periodically.
#
# This class will not actually start the timer.  The derived class or its owner should call Start()
# on the object when ready to kick things off.
#
# Of course any class can just implement its own timer callback, but this adds a little bit of 
# functionality to call the function synchronously - that is, if it's scheduled to run every 0.5
# seconds, it will run at 0.5, 1.0, 1.5, 2.0 exactly.
#

class tActiveObject(QObject):

  ###############################################
  # Constructor and destructor
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def __init__(self, TimerPeriodInMs, parent=None):
    parent = None  # ActiveObjects have to have no parent, in order to be able to move them to a thread
    super().__init__(parent)
    self.TimerPeriodInMs = TimerPeriodInMs

  def __del__(self):
    if self.TimerPeriodInMs != 0:
      self.Timer.stop()


  ###############################################
  # Start - Starts the periodic timer callbacks running
  # 

  def Start(self):
    # Set up timer if requested
    if self.TimerPeriodInMs != 0:
      self.Timer = QTimer(self)
      self.Timer.setSingleShot(True)
      self.Timer.timeout.connect(self.OnTimerTimeout)  #, Qt.QueuedConnection)

      # Get the current time in the specified timezone
      current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
      # Calculate the remaining time until the next interval
      milliseconds_until_next_interval = int(self.TimerPeriodInMs - (current_time.time().msecsSinceStartOfDay() % self.TimerPeriodInMs))
      # Calculate the exact datetime for the next run
      self.ScheduledTime = current_time.addMSecs(milliseconds_until_next_interval)

      self.Timer.start(milliseconds_until_next_interval)


  ###############################################
  # PeriodicMethod - Called whenever the timer fires.  It is intended that you
  #                  override this with your method
  # 

  def PeriodicMethod(self):
    pass
  

  ###############################################
  # OnTimerTimeout - called when the periodic timer fires
  # 

  def OnTimerTimeout(self):
    # Call the user's periodic method
    self.PeriodicMethod()

    # Compute the next time to fire the timer
    self.ScheduledTime = self.ScheduledTime.addMSecs(self.TimerPeriodInMs)

    current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
    milliseconds_until_next_interval = current_time.msecsTo(self.ScheduledTime)
    #print(f"Timeout thread: {self.Timer.thread()}")

    # If we've missed one or more intervals, just skip, and advance to the next scheduled time that is in the future
    while milliseconds_until_next_interval <= 0:
      milliseconds_until_next_interval = milliseconds_until_next_interval + self.TimerPeriodInMs
    
    self.Timer.start(milliseconds_until_next_interval)
    #print(f"After timer start attempt: thread: {self.Timer.thread()}")

