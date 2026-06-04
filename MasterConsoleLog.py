#######################################################
# tMasterConsoleLog - Tee stdout and stderr to MasterConsole.log
#
# Keeps normal terminal output while also appending Python-level console output
# to a daily text log file.
#

import atexit
import sys

from DailyTextLogFile import tDailyTextLogFile


##########################################################################################
##########################################################################################
##########################################################################################
# tTeeStream
#
#

class tTeeStream:

  ###############################################
  # Constructor
  #

  def __init__(self, OriginalStream, LogFile):
    self.OriginalStream = OriginalStream
    self.LogFile        = LogFile


  ###############################################
  # write - Write text to the terminal stream and the log file
  #

  def write(self, Text):
    self.OriginalStream.write(Text)
    self.LogFile.WriteText(Text)
    return len(Text)


  ###############################################
  # flush - Flush the terminal stream
  #

  def flush(self):
    self.OriginalStream.flush()


  ###############################################
  # __getattr__ - Delegate stream attributes to the original stream
  #

  def __getattr__(self, Name):
    return getattr(self.OriginalStream, Name)


##########################################################################################
##########################################################################################
##########################################################################################
# tMasterConsoleLog
#
#

class tMasterConsoleLog:

  ###############################################
  # Constructor
  #

  def __init__(self, DailyFolder):
    self.SysModule      = sys
    self.LogFile        = tDailyTextLogFile(DailyFolder, "MasterConsole.log")
    self.OriginalStdout = self.SysModule.stdout
    self.OriginalStderr = self.SysModule.stderr
    self.bInstalled     = False

    self.Install()
    atexit.register(self.Restore)


  ###############################################
  # Install - Replace stdout and stderr with tee streams
  #

  def Install(self):
    if self.bInstalled:
      return

    self.SysModule.stdout = tTeeStream(self.OriginalStdout, self.LogFile)
    self.SysModule.stderr = tTeeStream(self.OriginalStderr, self.LogFile)
    self.bInstalled = True


  ###############################################
  # Restore - Restore stdout and stderr to their original streams
  #

  def Restore(self):
    if not self.bInstalled:
      return

    CurrentStdout = self.SysModule.stdout
    CurrentStderr = self.SysModule.stderr

    for Stream in (CurrentStdout, CurrentStderr):
      try:
        if Stream is not None:
          Stream.flush()
      except Exception:
        pass

    self.SysModule.stdout = self.OriginalStdout
    self.SysModule.stderr = self.OriginalStderr
    self.bInstalled = False


  ###############################################
  # StartNewFile - Rotate MasterConsole.log
  #

  def StartNewFile(self):
    return self.LogFile.StartNewFile()
