#######################################################
# SerialPort.py
#
# Defines:
#   tAutoOpenSerial          - QObject facade for a collector serial port.  Native open/read/write/
#                              close calls run only on a daemon pyserial worker thread.
#   tAutoOpenSerialWholeLine - Same, plus line assembly (emits readyLine per complete line).
#
#
# WHY THIS FILE LOOKS THE WAY IT DOES  (read this before changing the connect logic)
# ----------------------------------------------------------------------------------
# The Qt GUI remains single-threaded: widgets, timers, telemetry parsing, and collector state
# updates all run on the GUI event loop.  Native Windows serial calls do NOT.  USB-CDC devices
# can wedge such that open(), close(), and sometimes write/read never return.  If those calls run
# on the GUI thread, the app freezes in native code.
#
# The rule here is therefore simple:
#   * The GUI thread never calls a native serial open/close/read/write for collector ports.
#   * Each collector port owns a throw-away daemon worker thread that uses pyserial.
#   * If a worker blocks forever in a native call, the GUI abandons it and carries on.  The worker
#     and OS handle are freed when the USB device de-enumerates or the process exits.
#   * Worker events are drained by a QTimer on the GUI thread, so Qt signals and UI work still
#     happen in the normal Qt thread.
#
# This deliberately avoids QSerialPort and QSerialPortInfo for collector recovery.  We already
# know the configured COM port; asking the OS to enumerate serial devices from the GUI thread is
# just another native serial path that can block.



#################################################
# Modules used
#

import queue
import threading

try:
  import serial
except ModuleNotFoundError:
  serial = None

from PySide6.QtCore import QByteArray, QObject, QTimer, Signal

from ConfigInfo import SAFE_MODE, SERIAL_CONNECT_PROBE_TIMEOUT_SECS



#######################################################
#######################################################
#######################################################
#
# tPySerialWorker - Worker-thread owner of the native serial handle
#

class tPySerialWorker:

  ###############################################
  # Constructor
  #

  def __init__(self, portName, baudrate, readChunkSize, eventQueue, queuedDataBytes,
               queuedDataLock):
    self._portName        = portName
    self._baudrate        = baudrate
    self._readChunkSize   = max(1, readChunkSize)
    self._readBufferLimit = max(1, readChunkSize)
    self._EventQueue      = eventQueue
    self._QueuedDataBytes = queuedDataBytes
    self._QueuedDataLock  = queuedDataLock
    self._WriteQueue     = queue.Queue()
    self._bStopRequested = threading.Event()
    self._bOpened        = False
    self._Thread         = threading.Thread(target=self._Run,
                                            name=f'serial-{self._portName}',
                                            daemon=True)


  ###############################################
  # Start - Start the daemon worker
  #

  def Start(self):
    self._Thread.start()


  ###############################################
  # Stop - Ask the worker to close and exit without waiting for it
  #

  def Stop(self):
    self._bStopRequested.set()
    self._WriteQueue.put(None)


  ###############################################
  # IsRunning - True while the worker thread has not yet exited
  #
  # A worker parked in a native call (open/read on a wedged device) stays alive long after Stop()
  # is requested.  The facade uses this to tell a finished worker from an intentional zombie.
  #

  def IsRunning(self):
    return self._Thread.is_alive()


  ###############################################
  # QueueWrite - Queue bytes for the worker to write
  #

  def QueueWrite(self, data):
    self._WriteQueue.put(data)


  ###############################################
  # _Run - Open the port and service reads/writes on the worker thread
  #

  def _Run(self):
    SerialDevice = None
    try:
      if serial is None:
        raise RuntimeError('pyserial not available')

      SerialDevice = serial.Serial()
      SerialDevice.port          = self._portName
      SerialDevice.baudrate      = self._baudrate
      SerialDevice.timeout       = 0.05
      SerialDevice.write_timeout = 0.5
      SerialDevice.rtscts        = False
      SerialDevice.dsrdtr        = False
      SerialDevice.xonxoff       = False
      SerialDevice.open()

      self._bOpened = True
      try:
        SerialDevice.setDTR(True)
        SerialDevice.setRTS(True)
      except Exception:
        pass

      self._EventQueue.put(('open', 'open', ''))

      while not self._bStopRequested.is_set():
        self._DrainWriteQueue(SerialDevice)
        if self._bStopRequested.is_set():
          break

        nBytesToRead = 1
        nBytesWaiting = SerialDevice.in_waiting
        if nBytesWaiting > 0:
          nBytesToRead = min(nBytesWaiting, self._readChunkSize)

        Data = SerialDevice.read(nBytesToRead)
        if Data:
          self._QueueData(Data)

      self._CloseSerialDevice(SerialDevice)
      self._EventQueue.put(('closed', 'closed', ''))

    except Exception as e:
      Detail = str(e)
      if self._bOpened:
        self._EventQueue.put(('error', 'error', Detail))
        self._CloseSerialDevice(SerialDevice)
      else:
        self._EventQueue.put(('open_failed', self._ClassifyOpenException(e), Detail))


  ###############################################
  # _DrainWriteQueue - Write all pending output to the serial device
  #

  def _DrainWriteQueue(self, SerialDevice):
    while True:
      try:
        Data = self._WriteQueue.get_nowait()
      except queue.Empty:
        return

      if Data is None:
        self._bStopRequested.set()
        return

      SerialDevice.write(Data)


  ###############################################
  # _QueueData - Queue received bytes without exceeding the facade receive buffer cap
  #

  def _QueueData(self, Data):
    with self._QueuedDataLock:
      nBytesAvailable = self._readBufferLimit - self._QueuedDataBytes[0]
      if nBytesAvailable <= 0:
        return
      if len(Data) > nBytesAvailable:
        Data = Data[:nBytesAvailable]
      self._QueuedDataBytes[0] += len(Data)

    self._EventQueue.put(('data', Data, ''))


  ###############################################
  # _CloseSerialDevice - Close the native handle on the worker thread
  #

  def _CloseSerialDevice(self, SerialDevice):
    if SerialDevice is not None and SerialDevice.is_open:
      SerialDevice.close()


  ###############################################
  # _ClassifyOpenException - Turn pyserial/Windows open failures into collector states
  #

  def _ClassifyOpenException(self, ExceptionObject):
    ErrorText = str(ExceptionObject).lower()

    if ('file not found' in ErrorText or
        'cannot find'    in ErrorText or
        'does not exist' in ErrorText):
      return 'absent'

    if ('access is denied' in ErrorText or
        'permission'       in ErrorText or
        'denied'           in ErrorText or
        'busy'             in ErrorText or
        'in use'           in ErrorText):
      return 'busy'

    return 'error'



#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerial - GUI-thread facade for a worker-owned serial port
#

class tAutoOpenSerial(QObject):
  PortOpenStateChange       = Signal(bool)      # Emitted when the port becomes open/offline
  ReaderWakeUp              = Signal()
  ConnectionAttemptFinished = Signal(str, str) # result, detail: open/timeout/absent/busy/error
  errorOccurred             = Signal(str)


  #######################################################
  # Constructor
  #

  def __init__(self, portName, baudrate=9600, readBufSize=0, parent=None):
    super().__init__(parent)

    self.bIsOpen    = False
    self.bWakingUp  = False
    self.bPrintDiag = False

    self._portName                 = portName
    self._baudrate                 = baudrate
    self._readBufSize              = readBufSize if readBufSize != 0 else 4096
    self._EventQueue               = queue.Queue()
    self._QueuedDataBytes          = [0]
    self._QueuedDataLock           = threading.Lock()
    self._Worker                   = None
    self._StoppedWorker            = None  # last worker we asked to stop, kept only so that
                                           # IsFullyStopped can tell "exited" from "still parked"
    self._bAbandoned               = False
    self._bOpenAttemptInProgress   = False
    self._bOpenAttemptTimedOut     = False
    self._connectTimeoutMs         = int(SERIAL_CONNECT_PROBE_TIMEOUT_SECS * 1000)

    self._DrainTimer = QTimer(self)
    self._DrainTimer.setSingleShot(False)
    self._DrainTimer.timeout.connect(self._DrainWorkerEvents)

    self._ConnectTimeoutTimer = QTimer(self)
    self._ConnectTimeoutTimer.setSingleShot(True)
    self._ConnectTimeoutTimer.timeout.connect(self._OpenAttemptTimedOut)


  #######################################################
  # Destructor - Request worker shutdown without blocking
  #

  def __del__(self):
    if hasattr(self, '_bAbandoned'):
      self.Abandon()


  #######################################################
  # IsOpen
  #

  def IsOpen(self):
    return self.bIsOpen


  #######################################################
  # IsConnectInProgress
  #

  def IsConnectInProgress(self):
    return self._bOpenAttemptInProgress


  #######################################################
  # portName
  #

  def portName(self):
    return self._portName


  #######################################################
  # AttemptOpenIfNeeded - Start the real open on a daemon worker thread
  #

  def AttemptOpenIfNeeded(self):
    if SAFE_MODE or self.bIsOpen or self._bOpenAttemptInProgress or self._bAbandoned:
      return

    self._bOpenAttemptInProgress = True
    self._bOpenAttemptTimedOut   = False
    self._Worker = tPySerialWorker(self._portName, self._baudrate, self._readBufSize,
                                   self._EventQueue, self._QueuedDataBytes,
                                   self._QueuedDataLock)
    self._Worker.Start()
    self._DrainTimer.start(50)
    self._ConnectTimeoutTimer.start(self._connectTimeoutMs)


  #######################################################
  # Abandon - Mark this facade stale and ask the worker to stop without waiting
  #

  def Abandon(self):
    if self._bAbandoned:
      return

    self._bAbandoned             = True
    self.bIsOpen                 = False
    self._bOpenAttemptInProgress = False
    self._ConnectTimeoutTimer.stop()
    self._DrainTimer.stop()
    self._RequestWorkerStop()


  #######################################################
  # close - Compatibility wrapper; never blocks the GUI thread
  #

  def close(self):
    self.Abandon()


  #######################################################
  # read - Compatibility wrapper for old QSerialPort-style callers
  #

  def read(self):
    return QByteArray()


  #######################################################
  # readString - Compatibility wrapper for old QSerialPort-style callers
  #

  def readString(self):
    return ""


  #######################################################
  # write - Queue a str/bytes/QByteArray for worker-thread output
  #
  # RETURNS:
  #   Number of bytes accepted for queueing, or -1 if offline.
  #

  def write(self, data):
    if not self.bIsOpen or self._Worker is None or self._bAbandoned:
      return -1

    if isinstance(data, str):
      Data = data.encode("utf-8")
    elif isinstance(data, QByteArray):
      Data = bytes(data.data())
    else:
      Data = bytes(data)

    self._Worker.QueueWrite(Data)
    return len(Data)


  #######################################################
  # WakeUp - Compatibility hook used by ReaderWakeUp
  #

  def WakeUp(self):
    self.bWakingUp = True


  #######################################################
  # _DrainWorkerEvents - Deliver worker events on the Qt GUI thread
  #

  def _DrainWorkerEvents(self):
    if self._bAbandoned:
      return

    for _ in range(100):
      try:
        Event, Result, Detail = self._EventQueue.get_nowait()
      except queue.Empty:
        break

      if Event == 'open':
        self._HandleOpen()
      elif Event == 'open_failed':
        self._HandleOpenFailed(Result, Detail)
      elif Event == 'data':
        self._RemoveQueuedDataBytes(len(Result))
        self._HandleReceivedBytes(Result)
      elif Event == 'error':
        self._HandleWorkerError(Detail)
      elif Event == 'closed':
        self._HandleWorkerClosed()

    self._StopDrainTimerIfIdle()


  #######################################################
  # _OpenAttemptTimedOut - Declare HUNG while leaving the worker alive
  #

  def _OpenAttemptTimedOut(self):
    if self._bOpenAttemptInProgress and not self._bOpenAttemptTimedOut:
      self._bOpenAttemptInProgress = False
      self._bOpenAttemptTimedOut   = True
      Detail = f'{self._portName} open did not return within {SERIAL_CONNECT_PROBE_TIMEOUT_SECS}s'
      self.ConnectionAttemptFinished.emit('timeout', Detail)


  #######################################################
  # _HandleOpen - Worker opened the port successfully
  #

  def _HandleOpen(self):
    self._ConnectTimeoutTimer.stop()
    self._bOpenAttemptInProgress = False
    self._bOpenAttemptTimedOut   = False
    self.bIsOpen                 = True
    self.ConnectionAttemptFinished.emit('open', '')
    self.PortOpenStateChange.emit(True)


  #######################################################
  # _HandleOpenFailed - Worker could not open the port
  #

  def _HandleOpenFailed(self, result, detail):
    self._ConnectTimeoutTimer.stop()
    self._bOpenAttemptInProgress = False
    self._bOpenAttemptTimedOut   = False
    self._Worker                 = None
    self.ConnectionAttemptFinished.emit(result, detail)


  #######################################################
  # _HandleWorkerError - Worker hit a serial error after the port was open
  #

  def _HandleWorkerError(self, detail):
    self._Worker = None
    self.errorOccurred.emit(detail)
    self._HandleClose()


  #######################################################
  # _HandleWorkerClosed - Worker closed after a requested stop
  #

  def _HandleWorkerClosed(self):
    self._Worker = None
    self._HandleClose()


  #######################################################
  # _HandleClose - Mark this facade offline and notify listeners
  #

  def _HandleClose(self):
    if self.bIsOpen:
      self.bIsOpen = False
      self.PortOpenStateChange.emit(False)


  #######################################################
  # _HandleReceivedBytes - Subclasses consume incoming bytes
  #

  def _HandleReceivedBytes(self, Data):
    pass


  #######################################################
  # _RequestWorkerStop - Ask the current worker to stop and forget it
  #

  def _RequestWorkerStop(self):
    Worker = self._Worker
    self._Worker = None
    if Worker is not None:
      self._StoppedWorker = Worker
      Worker.Stop()


  #######################################################
  # IsFullyStopped - True once no worker of ours is still running
  #
  # An abandoned facade must be kept referenced while its worker is parked in a native call, or
  # the zombie writes into freed state.  Once the thread has exited the facade is inert and its
  # owner may release it.
  #

  def IsFullyStopped(self):
    if self._Worker is not None:
      return False

    if self._StoppedWorker is None:
      return True

    return not self._StoppedWorker.IsRunning()


  #######################################################
  # _StopDrainTimerIfIdle - Stop polling when there is no live worker
  #

  def _StopDrainTimerIfIdle(self):
    if self._Worker is None and not self._bOpenAttemptInProgress and not self.bIsOpen:
      self._DrainTimer.stop()


  #######################################################
  # _RemoveQueuedDataBytes - Release worker receive-buffer budget after draining bytes
  #

  def _RemoveQueuedDataBytes(self, nBytes):
    with self._QueuedDataLock:
      self._QueuedDataBytes[0] = max(0, self._QueuedDataBytes[0] - nBytes)



#######################################################
#######################################################
#######################################################
#
# tAutoOpenSerialWholeLine - tAutoOpenSerial that emits complete '\n' terminated lines
#

class tAutoOpenSerialWholeLine(tAutoOpenSerial):
  readyLine = Signal(str)  # Emitted for each complete line (including the trailing '\n')


  #######################################################
  # Constructor
  #

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self._lineBuffer = ""
    self.ReaderWakeUp.connect(self.WakeUp)


  #######################################################
  # _HandleReceivedBytes - Assemble complete lines from worker bytes
  #

  def _HandleReceivedBytes(self, Data):
    if self.bWakingUp:
      print(f'*****{self.portName()}: Waking up worked*****')
    self.bWakingUp = False

    if self.bPrintDiag:
      print(Data.decode("utf-8", errors="ignore"), end="")

    self._lineBuffer += Data.decode("utf-8", errors="ignore")
    while "\n" in self._lineBuffer:
      line, self._lineBuffer = self._lineBuffer.split("\n", 1)
      self.readyLine.emit(line + "\n")
