#######################################################
# SerialPort.py
#
# Defines:
#   tSerialConnectProbe      - Non-blocking "can this port be opened?" health-probe.
#   tAutoOpenSerial          - A QSerialPort whose blocking open/close is driven by the owner
#                              through the probe, so a sick board can never freeze the GUI.
#   tAutoOpenSerialWholeLine - Same, plus line assembly (emits readyLine per complete line).
#
#
# WHY THIS FILE LOOKS THE WAY IT DOES  (read this before changing the connect logic)
# ----------------------------------------------------------------------------------
# This whole app is SINGLE-THREADED: all serial I/O runs on the Qt GUI event loop.  We learned
# the hard way (multiple unpausable freezes, captured by the hang watchdog) that BOTH
# QSerialPort.open() AND QSerialPort.close() make synchronous native Windows driver calls that
# can block FOREVER when the USB-CDC board behind the port is wedged, half-powered, or
# mid-power-cycle - the pending overlapped I/O never completes and never cancels.  On a
# single-threaded app that freezes the entire GUI, in native code, where not even the debugger
# can pause it.
#
# There is no in-thread timeout for a native open()/close().  So the design here is:
#   * The data path (read/write on an already-open port) stays on the GUI thread - QSerialPort
#     wants all its traffic serialized through one event loop, and reads/writes don't block.
#   * The DANGEROUS calls - opening a port, or recovering a dead one - are guarded.  Before the
#     GUI thread ever opens a real QSerialPort, we PROBE the port on a throw-away worker thread
#     (open it, close it) and a GUI timer (never a blocking join) decides ok / fail / timed-out.
#   * We NEVER call the blocking close() to recover a wedged port.  Instead the owner abandons
#     the QSerialPort object (see tCollector) and brings up a fresh one; the abandoned OS handle
#     is freed for free when the device de-enumerates (a USB power-cycle / reset).
#
# So this class no longer auto-opens itself.  The owner (tCollector) drives the connect through
# the probe and only calls AttemptOpenIfNeeded() once a probe has proven the port opens fast.



#################################################
# Modules used
#

import threading

try:
  # pyserial - used ONLY by the throw-away connect-probe.  We deliberately do NOT use QSerialPort
  # for the probe: QSerialPort is a QObject with Qt thread-affinity and must not be touched from a
  # worker thread, whereas a pyserial Serial is a plain object that is safe to open/close on any
  # thread.
  import serial
except ModuleNotFoundError:
  serial = None

from PySide6.QtSerialPort import QSerialPort
from PySide6.QtCore       import Signal, QTimer, QByteArray, QThread, QObject, QElapsedTimer, Qt

from ConfigInfo import SAFE_MODE



#######################################################
#######################################################
#######################################################
#
# tSerialConnectProbe - Non-blocking probe: can this COM port be opened (and closed) quickly?
#

class tSerialConnectProbe(QObject):
  """
  Tests whether a COM port can be opened AND closed within a timeout, WITHOUT ever blocking the
  GUI thread.

  How it works:
    * Start() spawns a daemon worker thread that does pyserial open() then close().  If the
      device is healthy this finishes in milliseconds; if it is wedged the native open()/close()
      blocks and the worker simply parks there forever (harmless - it's off the GUI thread).
    * A GUI-thread QTimer (NOT a blocking join) polls the worker's result and the elapsed time,
      then emits finished() with one of:
        'ok'      - opened and closed cleanly  -> the device is healthy; the owner may now open
                    its real QSerialPort (which will also be fast).
        'fail'    - open/close raised quickly (port absent, or busy because another handle holds
                    it)                          -> not connectable right now; retry later.  NOT a hang.
        'timeout' - neither happened within the budget -> open()/close() is BLOCKED, i.e. the
                    board is wedged-but-present  -> the collector is HUNG.

  A worker stuck in a native call cannot be killed (you can't kill a Python thread blocked in a
  syscall, and QThread.terminate on a serial handle is unsafe).  So we just abandon it as a
  daemon zombie.  That is actually correct: while it is stuck it keeps the COM port busy, so the
  collector stays HUNG until the device truly recovers (e.g. a USB power-cycle), at which point
  the next probe opens+closes cleanly and we reconnect.
  """

  finished = Signal(str)   # 'ok' | 'fail' | 'timeout'


  ###############################################
  # Constructor
  #
  # INPUTS:
  #   portName    - e.g. 'COM46'
  #   baudrate    - the collector baud rate (matters little for an open/close test)
  #   timeoutSecs - how long to wait before declaring 'timeout' (HUNG)
  #

  def __init__(self, portName, baudrate, timeoutSecs, parent=None):
    super().__init__(parent)
    self._portName  = portName
    self._baudrate  = baudrate
    self._timeoutMs = int(timeoutSecs * 1000)
    self._result    = None                 # written by the worker thread: 'ok' / 'fail'
    self._elapsed   = QElapsedTimer()

    # GUI-thread poll timer.  We poll a flag rather than join() the worker so the GUI never blocks.
    self._pollTimer = QTimer(self)
    self._pollTimer.setSingleShot(False)
    self._pollTimer.timeout.connect(self._Poll)


  ###############################################
  # Start - Launch the probe (returns immediately)
  #

  def Start(self):
    self._result = None
    self._elapsed.start()
    # daemon=True so a wedged (un-killable) probe thread never holds up app exit.
    threading.Thread(target=self._Worker, name=f'probe-{self._portName}', daemon=True).start()
    self._pollTimer.start(200)             # poll 5x/sec on the GUI thread


  ###############################################
  # _Worker - Runs on the daemon worker thread: open then close, never on the GUI thread
  #
  # If open() or close() BLOCKS on a wedged device, this thread parks here forever.  That is
  # fine - the GUI keeps running and _Poll() will time us out.  We never set _result in that
  # case, which is exactly how the timeout is detected.
  #

  def _Worker(self):
    try:
      if serial is None:
        raise RuntimeError('pyserial not available')
      s = serial.Serial(self._portName, self._baudrate, timeout=0.2)
      s.close()
      self._result = 'ok'
    except Exception:
      # Port absent (file-not-found), busy (access-denied), or any other fast failure.
      self._result = 'fail'


  ###############################################
  # _Poll - Runs on the GUI thread; decides ok / fail / timeout without ever blocking
  #

  def _Poll(self):
    result = self._result                  # atomic read of a single flag (safe under the GIL)
    if result is not None:
      self._pollTimer.stop()
      self.finished.emit(result)
    elif self._elapsed.elapsed() > self._timeoutMs:
      # Worker is still stuck in a native open()/close() -> the device is wedged.  Abandon the
      # worker (daemon zombie) and report the timeout so the owner can declare HUNG.
      self._pollTimer.stop()
      self.finished.emit('timeout')



#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerial    - Serial port whose (blocking) open/close is driven by the owner
#
# STATE INVARIANT:
#   bIsOpen always reflects whether WE consider the port open and usable.  Note that, by design,
#   bIsOpen can be set False WITHOUT calling the native close() (close() can block on a wedged
#   device) - in that case the OS handle is still held until the owner abandons this object.
#

class tAutoOpenSerial(QSerialPort):
  PortOpenStateChange = Signal(bool)  # Emitted when the port becomes open or goes offline
  ReaderWakeUp        = Signal()


  #######################################################
  # Constructor
  #

  def __init__(self, portName, baudrate=9600, readBufSize=0, parent=None):
    super().__init__(parent)

    self.bIsOpen    = False
    self.bWakingUp  = False
    self.bPrintDiag = False

    self.setPortName(portName)
    self.setBaudRate(baudrate)
    if readBufSize != 0:
      self.setReadBufferSize(readBufSize)

    self.setDataBits(QSerialPort.Data8)
    self.setParity(QSerialPort.NoParity)
    self.setStopBits(QSerialPort.OneStop)
    self.setFlowControl(QSerialPort.NoFlowControl)

    # NOTE: we deliberately do NOT open the port here.  Opening is driven by the owner
    # (tCollector) AFTER a guarded probe (tSerialConnectProbe) has shown the port opens fast, so
    # a wedged board can never block the GUI thread inside QSerialPort.open().  The port starts
    # closed.


  #######################################################
  # Destructor - Closes the port if we still think it is open
  #
  # This is the one place a (potentially blocking) close() can still happen, at GC / shutdown.
  # ABANDONED ports are kept referenced by their owner so this never runs on them.
  #

  def __del__(self):
    if self.bIsOpen:
      self.close()


  #######################################################
  # IsOpen
  #

  def IsOpen(self):
    return self.bIsOpen


  #######################################################
  # AttemptOpenIfNeeded - The real GUI-thread open.  Call this ONLY after a probe said 'ok'.
  #
  # Because a successful probe just proved this exact port opens+closes quickly, the open()
  # below is expected to be fast.  (In --safe mode we never open at all.)
  #

  def AttemptOpenIfNeeded(self):
    # Safe-start (--safe): never open the port.  Keeps all collectors offline so the GUI +
    # Agilent power relays stay usable for remote recovery when boards are wedged.
    if SAFE_MODE:
      return

    if not self.bIsOpen:
      if self.open(QSerialPort.ReadWrite) and self.error() == QSerialPort.NoError:
        # Many USB CDC devices (e.g. TinyUSB on the Pico) gate outbound data on DTR being
        # asserted.  QSerialPort does not assert DTR/RTS automatically on open; PuTTY does.
        self.setDataTerminalReady(True)
        self.setRequestToSend(True)
        self.bIsOpen   = True
        self.bWakingUp = False
        self.PortOpenStateChange.emit(self.bIsOpen)
      else:
        # Open failed (or opened with an error).  Do NOT call the native close() - it can block
        # on a wedged device.  Just mark ourselves offline; the owner will abandon this object.
        self._HandleClose()


  #######################################################
  # _HandleClose - Mark the port offline WITHOUT a native close (close() can block)
  #
  # This sets bIsOpen False and notifies listeners, but does NOT release the OS handle.  The
  # owner is expected to abandon this object and bring up a fresh one; the leaked handle is
  # released when the device de-enumerates.
  #

  def _HandleClose(self):
    if self.bIsOpen:
      self.bIsOpen = False
      self.PortOpenStateChange.emit(self.bIsOpen)


  #######################################################
  # read - Read whatever bytes are buffered (does NOT auto-open; that could block)
  #
  # RETURNS:
  #   Retrieved data as a QByteArray (empty if not open or on error)
  #

  def read(self):
    if not self.bIsOpen:
      return QByteArray()

    data = self.readAll()
    self.flush()

    if self.error() != QSerialPort.NoError:
      # Device errored mid-stream (unplugged / reset / wedged).  Do NOT close() here - a native
      # close() on a wedged device blocks the GUI thread.  Mark offline and let the owner abandon
      # this port and probe-reconnect a fresh one.
      self._HandleClose()
      return QByteArray()

    return data


  #######################################################
  # readString - read() but as a str
  #

  def readString(self):
    data = self.read()
    return str(data.data(), "utf-8") if not data.isEmpty() else ""


  #######################################################
  # write - Write a str or QByteArray (does NOT auto-open; dropped if offline)
  #
  # RETURNS:
  #   Number of bytes written, or -1 if not open / on error
  #

  def write(self, data):
    if not self.bIsOpen:
      return -1

    if isinstance(data, str):
      data = data.encode("utf-8")

    bytes_written = super().write(data)
    if bytes_written == -1 or self.error() != QSerialPort.NoError:
      # Write error - mark offline (no blocking close()); the owner will abandon + reconnect.
      self._HandleClose()
      return -1

    return bytes_written


  #######################################################
  # close - Real (blocking) close.  Used only at intentional shutdown, NOT for recovery.
  #
  # Recovery from a wedged port is done by the owner abandoning this object (see tCollector),
  # precisely because this close() can block on a sick device.
  #

  def close(self):
    if self.isOpen():
      super().close()
    self._HandleClose()



#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerialWholeLine - tAutoOpenSerial that emits readyLine for each complete '\n' line
#

class tAutoOpenSerialWholeLine(tAutoOpenSerial):
  readyLine = Signal(str)  # Emitted for each complete line (including the trailing '\n')


  #######################################################
  # Constructor
  #

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self._lineBuffer = ""  # Buffer for assembling partial lines

    # Assemble lines as bytes arrive.  QueuedConnection (intra-thread) so our drain loop can
    # consume bytes before a duplicate readyRead is dispatched.
    self.readyRead   .connect(self._AssembleLine, Qt.QueuedConnection)
    self.ReaderWakeUp.connect(self.WakeUp,        Qt.QueuedConnection)


  #######################################################
  # WakeUp - Nudge the line assembler (used when telemetry seems to have stalled)
  #

  def WakeUp(self):
    self.bWakingUp = True
    self._AssembleLine()


  #######################################################
  # _AssembleLine - Drain buffered bytes and emit readyLine for each complete line
  #

  def _AssembleLine(self):
    if self.bytesAvailable() == 0:
      # Routine with QueuedConnection - our while loop can pick up bytes before the second
      # signal arrives.
      self.bWakingUp = False
      return

    while self.bytesAvailable() > 0:
      if self.bWakingUp:
        print(f'*****{self.portName()}: Waking up worked*****')
      self.bWakingUp = False
      data = self.read()  # Read available bytes as a QByteArray

      if self.error() != QSerialPort.NoError:
        # Device errored - mark offline (NO blocking close); the owner abandons + reconnects.
        print(f"Serial port error on port {self.portName()}: {self.error()}", flush=True)
        self._HandleClose()
        return

      if data.isEmpty():
        break  # No more data available to read

      if self.bPrintDiag:
        print(str(data.data(), "utf-8", errors="ignore"), end="")

      # The errors="ignore" skips the binary cruft some devices emit right after connecting.
      self._lineBuffer += str(data.data(), "utf-8", errors="ignore")

      # Emit each complete line (handles more than one full line in the buffer).
      while "\n" in self._lineBuffer:
        line, self._lineBuffer = self._lineBuffer.split("\n", 1)
        self.readyLine.emit(line + "\n")
