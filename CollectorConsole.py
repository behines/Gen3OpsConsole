##########################################################################################
# tCollectorConsole - Interactive console window for a single collector
#
# Displays raw serial output (including partial lines like prompts) and sends
# typed commands back to the device.  Host-side command history via Up/Down arrows.
#

from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QLineEdit
from PySide6.QtCore    import Signal, Qt
from PySide6.QtGui     import QFont, QTextCursor


##########################################################################################
# tHistoryLineEdit - QLineEdit with Up/Down command history
#

class tHistoryLineEdit(QLineEdit):
  SendLine = Signal(str)

  def __init__(self, parent=None):
    super().__init__(parent)
    self._history      = []
    self._historyIndex = -1   # -1 means "not navigating history" (showing current draft)
    self._draft        = ""   # text typed before the user started navigating history
    self.setPlaceholderText("Type command and press Enter...")

  def keyPressEvent(self, event):
    key = event.key()

    if key == Qt.Key_Up:
      if not self._history:
        return
      if self._historyIndex == -1:
        self._draft = self.text()          # save whatever is typed
        self._historyIndex = len(self._history) - 1
      elif self._historyIndex > 0:
        self._historyIndex -= 1
      self.setText(self._history[self._historyIndex])
      self.end(False)                      # move cursor to end

    elif key == Qt.Key_Down:
      if self._historyIndex == -1:
        return
      if self._historyIndex < len(self._history) - 1:
        self._historyIndex += 1
        self.setText(self._history[self._historyIndex])
      else:
        self._historyIndex = -1
        self.setText(self._draft)
      self.end(False)

    elif key in (Qt.Key_Return, Qt.Key_Enter):
      line = self.text()
      if line:
        self._history.append(line)
      self._historyIndex = -1
      self._draft        = ""
      self.clear()
      self.SendLine.emit(line)

    else:
      # Any other key: cancel history navigation back to draft
      if self._historyIndex != -1:
        self._historyIndex = -1
        self._draft        = ""
      super().keyPressEvent(event)


##########################################################################################
# tCollectorConsole - Top-level dialog with output pane + history input
#

class tCollectorConsole(QDialog):

  def __init__(self, collectorName, collector, parent=None):
    super().__init__(parent)

    self.setWindowTitle(f"Console - Collector {collectorName}")
    self.resize(800, 400)

    # Output area - read-only, monospace, raw characters appended as they arrive
    self._output = QPlainTextEdit(self)
    self._output.setReadOnly(True)
    self._output.setMaximumBlockCount(2000)
    font = QFont("Courier New", 9)
    font.setStyleHint(QFont.StyleHint.Monospace)
    self._output.setFont(font)

    # Input area
    self._input = tHistoryLineEdit(self)
    self._input.setFont(font)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(4)
    layout.addWidget(self._output, stretch=1)
    layout.addWidget(self._input,  stretch=0)

    # Wire serial output to display - use the line-oriented TextLineReceived signal,
    # which already filters out TEL: telemetry lines in Collector.ProcessLineOfOutput
    collector.TextLineReceived.connect(self._AppendLine)

    # Wire input to serial port
    self._input.SendLine.connect(lambda line: collector.SerialPort.write(line + "\r\n"))

    # Give keyboard focus to the input field
    self._input.setFocus()

  def _AppendLine(self, line: str):
    cursor = self._output.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText(line)
    self._output.setTextCursor(cursor)
    self._output.ensureCursorVisible()
