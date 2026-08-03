#######################################################
# tMasterConsoleLog - Tee stdout and stderr to MasterConsole.log
#
# Keeps normal terminal output while also appending Python-level console output
# to a daily text log file.
#

import atexit
import sys

from datetime import datetime

from PySide6.QtCore import QObject, Signal

from DailyTextLogFile import tDailyTextLogFile


##########################################################################################
##########################################################################################
##########################################################################################
# tConsoleLineEmitter
#
# Carries each completed console line to whoever wants to display it - in practice the main
# window's Log box.  This exists because the tee is a plain stream object while Qt widgets may
# only be touched from the GUI thread, and write() can be called from any thread.  Connect
# LineWritten with Qt.QueuedConnection and the marshalling is handled for you.
#

class tConsoleLineEmitter(QObject):
  LineWritten = Signal(str)      # one complete console line, already timestamped


  ###############################################
  # Constructor
  #

  def __init__(self):
    super().__init__()
    self._bEmitting = False


  ###############################################
  # EmitLine - Publish one line, refusing to re-enter
  #
  # A slot that printed would come straight back through the tee.  Under a direct connection that
  # is unbounded recursion, so drop the nested line rather than take the console down with it.
  #

  def EmitLine(self, Line):
    if self._bEmitting:
      return

    self._bEmitting = True
    try:
      self.LineWritten.emit(Line)
    finally:
      self._bEmitting = False


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

  def __init__(self, OriginalStream, LogFile, LineEmitter=None):
    self.OriginalStream = OriginalStream
    self.LogFile        = LogFile
    self.LineEmitter    = LineEmitter
    self._bAtLineStart  = True
    self._LineBuffer    = ''


  ###############################################
  # write - Write text to the terminal stream and the timestamped log file
  #
  # Only the log file copy is stamped, so the terminal looks exactly as it always has.  The date
  # is deliberately omitted - the log rotates daily, so time of day is unambiguous, and short
  # lines stay readable.  Milliseconds are included because correlating a USB dropout with the
  # relay operation that may have caused it needs sub-second resolution.
  #

  def write(self, Text):
    self.OriginalStream.write(Text)

    StampedText = self._StampLines(Text)
    self.LogFile.WriteText(StampedText)
    self._EmitCompleteLines(StampedText)

    return len(Text)


  ###############################################
  # _EmitCompleteLines - Hand finished lines to the line emitter
  #
  # The GUI box wants whole lines, not the fragments print() delivers, so hold a partial line
  # back until its newline arrives.  The text is already stamped, so the Log box and
  # MasterConsole.log read identically.
  #

  def _EmitCompleteLines(self, StampedText):
    if self.LineEmitter is None:
      return

    self._LineBuffer += StampedText

    while '\n' in self._LineBuffer:
      Line, self._LineBuffer = self._LineBuffer.split('\n', 1)
      self.LineEmitter.EmitLine(Line)


  ###############################################
  # _StampLines - Prefix every line in Text with the time of day
  #
  # print() delivers one line across several write() calls (the text, then the newline), so a
  # stamp may only be emitted at a real line start.  _bAtLineStart carries that across calls.
  #

  def _StampLines(self, Text):
    if not Text:
      return Text

    Stamp  = datetime.now().strftime("%H:%M:%S.%f")[:-3] + ' '
    Output = []

    for Character in Text:
      if self._bAtLineStart:
        Output.append(Stamp)
        self._bAtLineStart = False

      Output.append(Character)

      if Character == '\n':
        self._bAtLineStart = True

    return ''.join(Output)


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
    self.LineEmitter    = tConsoleLineEmitter()
    self.bInstalled     = False

    self.Install()
    atexit.register(self.Restore)


  ###############################################
  # Install - Replace stdout and stderr with tee streams
  #

  def Install(self):
    if self.bInstalled:
      return

    self.SysModule.stdout = tTeeStream(self.OriginalStdout, self.LogFile, self.LineEmitter)
    self.SysModule.stderr = tTeeStream(self.OriginalStderr, self.LogFile, self.LineEmitter)
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
