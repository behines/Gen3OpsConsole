#######################################################
# Utility functions
#
# 
#



#################################################
# Modules used
#

from PySide6.QtCore import QObject, QThread, Signal, QElapsedTimer, QDateTime, QTimeZone

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