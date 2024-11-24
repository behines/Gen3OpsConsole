#######################################################
# Utility functions
#
# 
#



#################################################
# Modules used
#

from PySide6.QtCore import QObject, QThread, Signal, QDateTime, QTimeZone, QTimer, QEventLoop
import debugpy

from ConfigInfo import *



##########################################################################################
##########################################################################################
##########################################################################################
# Decorators
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
# WaitForSignal - Blocks until the specified signal is received
#
# INPUTS:
#   SignalToEmit - If provided, Qt will emit this signal for you in order to provoke the signal you're waiting on
#   TimeoutInMs  - how long to wait before giving up

def WaitForSignal(SignalToWaitFor:Signal, SignalToEmit:Signal=None, TimeoutInMs=0, parent=None):
    
  # This is Qt's funny way of blocking to wait for a signal
  loop = QEventLoop(parent)
  SignalToWaitFor.connect(loop.quit)

  # We will also exit the event loop if the timer times out
  if TimeoutInMs != 0:
    Timer = QTimer(parent)
    Timer.setSingleShot(True)
    Timer.timeout.connect(loop.quit)
    print('WaitForSignal timer start')
    Timer.start(TimeoutInMs)

  if not SignalToEmit is None:
    SignalToEmit.emit()

  # Block until the signal is emitted
  loop.exec()


##########################################################################################
##########################################################################################
##########################################################################################
# tActiveObject - Class that implements a thread that starts an event loop, so that the
#                 object can respond to signals.
#
# This class is meant to be inherited by any class whose main purpose is to be an "active
# object" that can respond to signals and emit responses.
#
# This class will not actually start the thread.  The derivce class constructor should call
# self.StartThread() as its last act
#
# Your derived class's destructor should call self.ShutDownComplete.emit() as its last act
#

class tActiveObject(QThread):

  RequestExit      = Signal()
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
  #  

  def StartThread(self, TimerPeriodInMs=0):
    # Now move ourself and all our new children to the thread we will start
    #self.TheThread = QThread()
    self.moveToThread(self)

    # Now start the thread.  
    # self.TheThread.started .connect(self.OnThreadStart)
    # self.finished   .connect(self.deleteLater)     # Causes the our destructor to be called when the thread exits
    self.RequestExit.connect(self.OnExitRequest)

    self.TimerPeriodInMs = TimerPeriodInMs

    self.start()



  ###############################################
  # OnExitRequest
  # 
  # Called when we receive a RequestExit signal
  #
  # Stops the periodic timer if running
  #
  # Tells the thread's event loop to exit, which will cause run() to return, which will 
  # fire the finished signal, which will call deleteLater, which will run our destructor.
  #  

  def OnExitRequest(self):
    print('ActiveObject exiting')
    if self.TimerPeriodInMs != 0:
      self.Timer.stop()
    self.quit()        # Tell the thread's event loop to exit.  


  ###############################################
  # run - Starts the active object's event loop
  #  

  def run(self):
    # Enable breakpoints within code in this thread
    debugpy.debug_this_thread()
    
    # Set up timer if requested
    if self.TimerPeriodInMs != 0:
      self.Timer = QTimer(self)
      self.Timer.setSingleShot(True)
      self.Timer.timeout.connect(self.OnTimerTimeout)

      # Get the current time in the specified timezone
      current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
      # Calculate the remaining time until the next interval
      milliseconds_until_next_interval = int(self.TimerPeriodInMs - (current_time.time().msecsSinceStartOfDay() % self.TimerPeriodInMs))
      # Calculate the exact datetime for the next run
      self.ScheduledTime = current_time.addMSecs(milliseconds_until_next_interval)
      print('Starting ActiveObject Timer at init, object id = ' + str(id(self)), flush=True)
      self.Timer.start(milliseconds_until_next_interval)

    # Start the thread's event loop by calling the base class run().  The default
    # implementation simply calls exec()
    super().run()       # i.e., self.exec()


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

    # If we've missed one or more intervals, just skip, and advance to the next scheduled time that is in the future
    while milliseconds_until_next_interval <= 0:
      milliseconds_until_next_interval = milliseconds_until_next_interval + self.TimerPeriodInMs
    
    print('Starting ActiveObject Timer on Timeout, object id = ' + str(id(self)), flush=True)
    self.Timer.start(milliseconds_until_next_interval)


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
