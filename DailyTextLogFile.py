#######################################################
# tDailyTextLogFile - Rotating daily text log file helper
#
# Provides the shared .log file rotation behavior used by collector console
# logs and the master stdout/stderr tee.
#

import os
import sys
from datetime import datetime

from PySide6.QtCore import QFile


##########################################################################################
##########################################################################################
##########################################################################################
# tDailyTextLogFile
#
#

class tDailyTextLogFile:

  ###############################################
  # Constructor
  #

  def __init__(self, DailyFolder, ShortLogFileName):
    self.DailyFolder      = DailyFolder
    self.ShortLogFileName = ShortLogFileName
    self.LogFileName      = os.path.join(self.DailyFolder, self.ShortLogFileName)

    self.StartNewFile()


  ###############################################
  # StartNewFile - Rotate the existing file and create a fresh empty log
  #

  def StartNewFile(self):
    os.makedirs(self.DailyFolder, exist_ok=True)
    self.LogFileName = os.path.join(self.DailyFolder, self.ShortLogFileName)

    if not self._MoveExistingLogFile():
      return False

    try:
      with open(self.LogFileName, "w", encoding="utf-8", newline="") as file:
        pass
      return True
    except OSError as e:
      self._ReportWarning(f"tDailyTextLogFile: could not create {self.LogFileName}: {e}")
      return False


  ###############################################
  # WriteText - Append text to the current log file
  #

  def WriteText(self, Text):
    try:
      with open(self.LogFileName, "a", encoding="utf-8", newline="") as file:
        file.write(Text)
      return True
    except OSError as e:
      self._ReportWarning(f"tDailyTextLogFile: could not write {self.LogFileName}: {e}")
      return False


  ###############################################
  # _MoveExistingLogFile - Move an existing log to trash, with rename fallback
  #

  def _MoveExistingLogFile(self):
    if not os.path.exists(self.LogFileName):
      return True

    if QFile.moveToTrash(self.LogFileName):
      return True

    BackupFileName = self._BackupFileName()
    try:
      os.replace(self.LogFileName, BackupFileName)
      self._ReportWarning(f"tDailyTextLogFile: could not move {self.LogFileName} to recycle bin; renamed it to {BackupFileName}")
      return True
    except OSError as e:
      self._ReportWarning(f"tDailyTextLogFile: could not rotate {self.LogFileName}: {e}")
      return False


  ###############################################
  # _BackupFileName - Build a unique timestamped backup name
  #

  def _BackupFileName(self):
    Timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BackupFileName = f"{self.LogFileName}.{Timestamp}.bak"
    Index = 1

    while os.path.exists(BackupFileName):
      BackupFileName = f"{self.LogFileName}.{Timestamp}_{Index}.bak"
      Index += 1

    return BackupFileName


  ###############################################
  # _ReportWarning - Write warnings without recursing through any active tee
  #

  def _ReportWarning(self, Message):
    try:
      sys.__stderr__.write(Message + "\n")
      sys.__stderr__.flush()
    except Exception:
      pass

