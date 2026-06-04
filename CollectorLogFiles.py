#######################################################
# tCollectorLogFiles - Per-collector text logs for console output
#
# Writes the same non-telemetry collector lines shown in the collector UI to
# daily-folder log files named after the configured collectors.
#

from PySide6.QtCore import QObject

from DailyTextLogFile import tDailyTextLogFile


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

    self.DailyFolder = DailyFolder
    self.Collectors  = Collectors
    self.LogFiles    = {}

    self.StartNewFiles()
    self._ConnectCollectors()


  ###############################################
  # StartNewFiles - Rotate existing collector console logs and create fresh files
  #

  def StartNewFiles(self):
    for Collector in self.Collectors:
      CollectorName = Collector.CollectorName
      self.LogFiles[CollectorName] = tDailyTextLogFile(self.DailyFolder, CollectorName + ".log")


  ###############################################
  # AppendLine - Append a line of collector output to that collector's log file
  #

  def AppendLine(self, CollectorName, Line):
    LogFile = self.LogFiles.get(CollectorName)
    if LogFile is None:
      return

    LogFile.WriteText(Line)


  ###############################################
  # _ConnectCollectors - Connect collector text signals to the appropriate log file
  #

  def _ConnectCollectors(self):
    for Collector in self.Collectors:
      Collector.TextLineReceived.connect(lambda Line, CollectorName=Collector.CollectorName: self.AppendLine(CollectorName, Line))
