#######################################################
# tCollectorLogFiles - Per-collector text logs for console output
#
# Writes the same non-telemetry collector lines shown in the collector UI to
# daily-folder log files named after the configured collectors.
#

import os
from datetime import datetime

from PySide6.QtCore import QObject, QFile


##########################################################################################
##########################################################################################
##########################################################################################
# tCollectorLogFiles
#
#

class tCollectorLogFiles(QObject):

  ###############################################
  # Constructor
  #

  def __init__(self, DailyFolder, Collectors, parent=None):
    super().__init__(parent)

    self.DailyFolder  = DailyFolder
    self.Collectors   = Collectors
    self.LogFileNames = {}

    os.makedirs(self.DailyFolder, exist_ok=True)

    self.StartNewFiles()
    self._ConnectCollectors()


  ###############################################
  # StartNewFiles - Rotate existing collector console logs and create fresh files
  #

  def StartNewFiles(self):
    os.makedirs(self.DailyFolder, exist_ok=True)

    for Collector in self.Collectors:
      CollectorName = Collector.CollectorName
      LogFileName   = os.path.join(self.DailyFolder, CollectorName + ".log")

      self.LogFileNames[CollectorName] = LogFileName

      if not self._MoveExistingLogFile(LogFileName):
        continue

      with open(LogFileName, "w", encoding="utf-8", newline="") as file:
        pass


  ###############################################
  # AppendLine - Append a line of collector output to that collector's log file
  #

  def AppendLine(self, CollectorName, Line):
    LogFileName = self.LogFileNames.get(CollectorName)
    if LogFileName is None:
      return

    try:
      with open(LogFileName, "a", encoding="utf-8", newline="") as file:
        file.write(Line)
    except OSError as e:
      print(f"CollectorLogFiles: could not write {LogFileName}: {e}", flush=True)


  ###############################################
  # _ConnectCollectors - Connect collector text signals to the appropriate log file
  #

  def _ConnectCollectors(self):
    for Collector in self.Collectors:
      Collector.TextLineReceived.connect(lambda Line, CollectorName=Collector.CollectorName: self.AppendLine(CollectorName, Line))


  ###############################################
  # _MoveExistingLogFile - Move an existing log to trash, with rename fallback
  #

  def _MoveExistingLogFile(self, LogFileName):
    if not os.path.exists(LogFileName):
      return True

    if QFile.moveToTrash(LogFileName):
      return True

    BackupFileName = self._BackupFileName(LogFileName)
    try:
      os.replace(LogFileName, BackupFileName)
      print(f"CollectorLogFiles: could not move {LogFileName} to recycle bin; renamed it to {BackupFileName}", flush=True)
      return True
    except OSError as e:
      print(f"CollectorLogFiles: could not rotate {LogFileName}: {e}", flush=True)
      return False


  ###############################################
  # _BackupFileName - Build a unique timestamped backup name
  #

  def _BackupFileName(self, LogFileName):
    Timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BackupFileName = f"{LogFileName}.{Timestamp}.bak"
    Index = 1

    while os.path.exists(BackupFileName):
      BackupFileName = f"{LogFileName}.{Timestamp}_{Index}.bak"
      Index += 1

    return BackupFileName

