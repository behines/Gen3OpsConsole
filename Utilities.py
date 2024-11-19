#######################################################
# Utility functions
#
# 
#



#################################################
# Modules used
#

from PySide6.QtCore import QObject, QThread, Signal, QTimer, QDateTime, QTimeZone

from ConfigInfo import *



##########################################################################################
##########################################################################################
##########################################################################################
# Decorators
#

##############################################
# requires_device_open - Decorator that gets added to a function to cause it to 
# return immediately if the class's IsDeviceOpen() method returns Fals

def requires_device_open(method):
  def wrapper(self, *args, **kwargs):
    if not self.IsDeviceOpen():
      return
    return method(self, *args, **kwargs)
  return wrapper




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
  finished = Signal()     # Signal for thread completion
  error    = Signal(str)  # Signal for errors


  ###############################################
  # Constructor and destructor
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def __init__(self):
    super().__init__()
    self.thread = None

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
  
    self.thread = QThread()
    self.moveToThread(self.thread)

    # Start the method in the new thread
    self.thread.started.connect(lambda: self._run(method, *args, **kwargs))
    self.finished.connect(self.thread.quit)
    self.finished.connect(self.deleteLater)
    self.thread.finished.connect(self.thread.deleteLater)

    self.thread.start()


  ###############################################
  # The (private) method that runs the thread 
  # 
  # The thread should clean up properly, but if not the destructor will tidy up
  #   

  def _run(self, method, *args, **kwargs):
    try:
      method(*args, **kwargs)
      self.finished.emit()
    except Exception as e:
      self.error.emit(str(e))


  ###############################################
  # Stops the thread if running
  # 

  def StopThread(self):
    if self.thread and self.thread.isRunning():
      self.thread.quit()
      self.thread.wait()
      self.thread = None


##########################################################################################
##########################################################################################
##########################################################################################
# tPeriodicThread - a class that owns a thread that runs at a specified interval
#
# This class is meant to be inherited by any class whose main purpose is to spawn a persistent
# periodicaly running thread once initialized.
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
    self.PeriodInMs = PeriodInMs / 1000.0  # Convert to seconds for sleep
    self.SpawnMethodAsThreadAndSetAffinityToNewThread(self, method, *args, **kwargs)


  ###############################################
  # Overloaded (private) method that runs the thread, repeating method periodically
  # 
  
  def _run(self, method, *args, **kwargs):
    try:
      # Get the current time in the specified timezone
      current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))

      # Calculate the remaining time until the next interval
      milliseconds_until_next_interval = int(self.PeriodInMs - (current_time.time().msecsSinceStartOfDay() % self.PeriodInMs))
      
      # Calculate the exact datetime for the next run
      self.NextRunTime = current_time.addMSecs(milliseconds_until_next_interval)

      while True:
        if milliseconds_until_next_interval > 0:
          QThread.msleep(milliseconds_until_next_interval)
          
        # Run the method; break out of loop if it returns non-zero
        if method(self.NextRunTime, *args, **kwargs) != 0:
          break

        self.NextRunTime = self.NextRunTime.addMSecs(self.PeriodInMs)

        current_time = QDateTime.currentDateTime().toTimeZone(QTimeZone(SITE_TIMEZONE.encode('utf-8')))
        milliseconds_until_next_interval = current_time.msecsTo(self.NextRunTime)
          
      self.finished.emit()

    except Exception as e:
      self.error.emit(str(e))