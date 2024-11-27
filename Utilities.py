#######################################################
# Utility functions
#
# 
#



#################################################
# Modules used
#

from PySide6.QtCore import QObject, QThread, Signal, QDateTime, QTimeZone, QTimer, QEventLoop, QMutexLocker
import debugpy
import threading

from ConfigInfo import *



##########################################################################################
##########################################################################################
##########################################################################################
# Decorators
#
# Note, these can be nested.  Recommended is to put them in this order:
#   @requires_device_open()
#   @with_lock()
#   def Method(self)
#
# The inner decorator with_lock will be called first, ensuring the lock is in place during the open attempt
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


##############################################
# with_lock - Decorator that grabs a lock on the class's mutex _lock
#             for the duration of the method

def with_lock(method):
  def wrapper(self, *args, **kwargs):
    with QMutexLocker(self._lock):  # Ensure the mutex is locked during the method call
      return method(self, *args, **kwargs)
  return wrapper



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

  if not StimulusFuncToCall is None:
    StimulusFuncToCall()

  #print('Exit request emitted',flush=True)
  # Block until the signal is emitted
  loop.exec()
  #print('Event loop exited',flush=True)
  if bTimedOut:
    raise TimeoutError

  return payload


############
# SignalEmitter helper function
def SignalEmitter(TheSignal, *args, **kwargs):
  def emitter():
      TheSignal.emit(*args, **kwargs)
  return emitter



##########################################################################################
##########################################################################################
##########################################################################################
# tActiveThread - Class that implements the thread for a tActiveObject.  
#
# The main job of the thread is to start an event loop, by calleing the base class run() method
#

class tActiveThread(QThread):


  ###############################################
  # Constructor and destructor
  # 
  # We make use of parent in the class.  We know that the parent is a tActiveObject,
  # so we can reach into the ActiveObject and start its timer for it if need be.
  #   

  def __init__(self, ActiveObject, parent=None):
    super().__init__(parent)
    self.ActiveObject = ActiveObject

  def __del__(self):
    pass

  ###############################################
  # run - Starts the active object's event loop
  #  

  def run(self):
    threading.currentThread().name = self.objectName()  # Set Python thread name
    # Enable breakpoints within code in this thread
    debugpy.debug_this_thread()
    
    #print('ActiveObject thread started')

    # Set up timer if requested
    if self.ActiveObject.TimerPeriodInMs != 0:
      self.ActiveObject.Timer = QTimer(self)
      self.ActiveObject.Timer.setSingleShot(True)
      self.ActiveObject.Timer.timeout.connect(self.ActiveObject.OnTimerTimeout)

      # Get the current time in the specified timezone
      current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
      # Calculate the remaining time until the next interval
      milliseconds_until_next_interval = int(self.ActiveObject.TimerPeriodInMs - (current_time.time().msecsSinceStartOfDay() % self.ActiveObject.TimerPeriodInMs))
      # Calculate the exact datetime for the next run
      self.ActiveObject.ScheduledTime = current_time.addMSecs(milliseconds_until_next_interval)
      #print('Starting ActiveObject Timer, period = ' + str(self.ActiveObject.TimerPeriodInMs) + ' in init, object id = ' + str(id(self)), flush=True)
      #print(f"Timer creation thread: {QThread.currentThread()}")

      self.ActiveObject.Timer.start(milliseconds_until_next_interval)

    # Start the thread's event loop by calling the base class run().  The default
    # implementation simply calls exec()
    super().run()       # i.e., self.exec()

    if self.ActiveObject.TimerPeriodInMs != 0:
      self.ActiveObject.Timer.stop()

    #print('ActiveThread exiting')


##########################################################################################
##########################################################################################
##########################################################################################
# tActiveObject - Class that implements a thread that starts an event loop, so that the
#                 object can respond to signals.
#
# This class is meant to be inherited by any class whose main purpose is to be an "active
# object" that can respond to signals and emit responses.
#
# This class will not actually start the thread.  The derived class constructor should call
# self.StartThread() as its last act
#
# Your derived class's destructor should call self.ShutDownComplete.emit() as its last act
#

class tActiveObject(QObject):

  RequestExitSignal = Signal()
  #ShutDownComplete = Signal()


  ###############################################
  # Constructor and destructor
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def __init__(self,parent=None):
    parent = None  # ActiveObjects have to have no parent, in order to be able to move them to a thread
    super().__init__(parent)
    

  def __del__(self):
    if self.TimerPeriodInMs != 0:
      self.Timer.stop()


  ###############################################
  # StartThread
  # 
  # Causes the object's run method to start.  Also moves the affinity of the caller (and all
  # its children) to the thread.
  # 
  # INPUTS:
  #   TimerPeriodInMs - if nonzero, will call self.PeriodicMethod at this interval
  #   name            - a descriptive name for the thread that will show up in the debugger
  #  

  def StartThread(self, TimerPeriodInMs=0, name=None):
    # Now move ourself and all our new children to the thread we will start
    self.TheThread = tActiveThread(self, self)
    if not name is None:
      # print('Setting thread name to ',name)
      self.TheThread.setObjectName(name)
    self.moveToThread(self.TheThread)

    # Now start the thread.  
    # self.TheThread.started .connect(self.OnThreadStart)
    # self.finished   .connect(self.deleteLater)     # Causes the our destructor to be called when the thread exits
    self.RequestExitSignal.connect(self.OnExitRequest)

    self.TimerPeriodInMs = TimerPeriodInMs

    # Now start the thread.  
    #self.TheThread.started .connect(self.OnThreadStart)
    #self.TheThread.finished.connect(self.deleteLater)     # Causes our destructor to be called when the thread exits

    self.TheThread.start()


  ###############################################
  # RequestExit - Ask the ActiveObject to exit
  # 
  # Sends itself the RequestExitSignal signal
  #  

  def RequestExit(self):
    self.RequestExitSignal.emit()
    self.TheThread.quit()        # Tell the thread's event loop to exit.  
    self.TheThread.wait()
    self.TheThread.deleteLater()


  ###############################################
  # OnExitRequest
  # 
  # Called when we receive a RequestExitSignal signal
  #
  # Stops the periodic timer if running
  #
  # Tells the thread's event loop to exit, which will cause run() to return, which will 
  # fire the finished signal, which will call deleteLater, which will run our destructor.
  #  

  def OnExitRequest(self):
    #print('ActiveObject exiting')
    #if self.TimerPeriodInMs != 0:
    #  self.Timer.stop()
      
    # Schedule the thread for deletion, so that it doesn't get killed while it's still running
    #self.TheThread.deleteLater()

    # This method is being processed by the thread we are trying to shut down.
    #QCoreApplication.exit(0)     # Safely exit the event loop
    #self.TheThread.quit()        # Tell the thread's event loop to exit.  
    #self.TheThread.wait()
    #self.TheThread.deleteLater()
    #print('ActiveObject exited')
    pass


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


''' This code not used a present

##########################################################################################
##########################################################################################
##########################################################################################
# tThreadRunner - class that implements the ability to spawn a thread and assign the 
#                 owner to the thread.
#
# This class is meant to be inherited by any class whose main purpose is to spawn a persistent
# thread once initialized.
#

class tThreadRunner(QObject):
  Finished = Signal()     # Signal for thread completion
  error    = Signal(str)  # Signal for errors


  ###############################################
  # Constructor and destructor
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def __init__(self):
    super().__init__()
    self.TheThread = None

  def __del__(self):
    try:
      self.StopThread()
    except Exception as e:
      print(f"Warning: Exception during tThreadRunner cleanup: {e}")


  ###############################################
  # SpawnMethodAsThreadAndSetAffinityToNewThread
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  # The object that calls this method will have its affinity moved to the new thread
  #   
  # The method you spawn should never return, unless you want the thread to exit
  #

  def SpawnMethodAsThreadAndSetAffinityToNewThread(self, method, *args, **kwargs):
  
    self.TheThread = QThread()
    self.moveToThread(self.TheThread)

    # Start the method in the new thread
    
    self.methodToRun = lambda: method(*args, **kwargs)  # Store the method and its arguments
    self.TheThread.started .connect(self._run)
    self.Finished          .connect(self.TheThread.quit)
    self.Finished          .connect(self.deleteLater)
    self.TheThread.finished.connect(self.TheThread.deleteLater)

    self.TheThread.start()


  ###############################################
  # The (private) method that runs the thread 
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def _run(self):
    try:
      self.methodToRun()
      self.Finished.emit()
    except Exception as e:
      self.error.emit(str(e))


  ###############################################
  # Stops the thread if running
  # 

  def StopThread(self):
    if self.TheThread and self.TheThread.isRunning():
      self.TheThread.quit()
      self.TheThread.wait()
      self.TheThread = None


##########################################################################################
##########################################################################################
##########################################################################################
# tPeriodicThread - a class that owns a thread that runs at a specified interval
#
# This class is meant to be inherited by any class whose main purpose is to spawn a persistent
# periodically running thread once initialized.
#
# The derived class should provide a method tPeriodicMethod(self, args), and then you spawn
# the periodic method using
#    self.SpawnPeriodicMethodAsThreadAndSetAffinityToNewThread(PeriodInMs, self.PeriodicMethod, arg1, arg2 [etc])
# If your PeriodicMethod wants to know the time at which is was scheduled to run, that is stored in 
# self.ScheduledTime
#

class tPeriodicThread(tThreadRunner):

  ###############################################
  # Constructor
  # 

  def __init__(self, interval_ms):
    super().__init__()


  ###############################################
  # SpawnPeriodicMethodAsThreadAndSetAffinityToNewThread
  # 
  # Will run the method you provide with the specified period, synced to the clock.  So a 1-minute period
  # will run at 1:01:00, 1:02:00, etc.
  #
  # Your method should normally return 0.  If it returns non-zero, the thread will exit and scheduling will
  # cease.  If it raises an exception, the thread will also exit with an exception.

  def SpawnPeriodicMethodAsThreadAndSetAffinityToNewThread(self, PeriodInMs, method, *args, **kwargs):
    self.PeriodInMs = PeriodInMs
    self.SpawnMethodAsThreadAndSetAffinityToNewThread(method, *args, **kwargs)


  ###############################################
  # Overloaded (private) method that runs the thread, repeating method periodically
  # 
  
  def _run(self):
    try:
      # Get the current time in the specified timezone
      current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))

      # Calculate the remaining time until the next interval
      milliseconds_until_next_interval = int(self.PeriodInMs - (current_time.time().msecsSinceStartOfDay() % self.PeriodInMs))
      
      # Calculate the exact datetime for the next run
      self.ScheduledTime = current_time.addMSecs(milliseconds_until_next_interval)

      while True:
        if milliseconds_until_next_interval > 0:
          QThread.msleep(milliseconds_until_next_interval)
          
        # Run the method; break out of loop if it returns non-zero
        if self.methodToRun() != 0:
          break

        self.ScheduledTime = self.ScheduledTime.addMSecs(self.PeriodInMs)

        current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
        milliseconds_until_next_interval = current_time.msecsTo(self.ScheduledTime)
          
      self.Finished.emit()

    except Exception as e:
      print('Error in tPeriodicThread::_run: ', str(e))
      self.error.emit(str(e))

'''
