#######################################################
# tHangWatchdog - Detects and records GUI event-loop freezes
#
# The app is single-threaded: serial I/O, telemetry parsing, instrument polling, and
# sequencing all run on the GUI event loop.  If any of it blocks - especially inside a
# native call, where a debugger cannot even break in - the whole UI freezes and we
# normally have no way to see where.
#
# This watchdog catches that automatically.  A QTimer on the GUI thread "pets" it on a
# short interval.  Each pet (re)arms faulthandler.dump_traceback_later(), whose countdown
# runs on its own C thread, independent of the (possibly wedged) main thread and GIL.
# While the event loop is healthy the pet keeps canceling the pending dump before it can
# fire.  If the loop ever freezes for longer than the timeout, the dump fires and writes
# every thread's Python stack to the hang log - naming the exact wedge location for next
# time.
#



#################################################
# Modules used
#

import faulthandler
import os

from datetime      import datetime
from PySide6.QtCore import QObject, QTimer

from ConfigInfo     import HANG_WATCHDOG_TIMEOUT_SECS, HANG_WATCHDOG_LOG_NAME


##########################################################################################
##########################################################################################
##########################################################################################
# tHangWatchdog
#

class tHangWatchdog(QObject):

  ###############################################
  # Constructor
  #
  # INPUTS:
  #   LogFolder - directory the hang log is written into
  #   parent    - QObject parent (keeps the watchdog and its timer alive)
  #

  def __init__(self, LogFolder, parent=None):
    super().__init__(parent)

    os.makedirs(LogFolder, exist_ok=True)
    self.LogFileName = os.path.join(LogFolder, HANG_WATCHDOG_LOG_NAME)

    # Line-buffered append so our own notes reach disk promptly.  faulthandler writes the
    # dumps directly to the file descriptor, so they survive even if the app is wedged.
    self._LogFile = open(self.LogFileName, "a", buffering=1, encoding="utf-8")
    self._LogFile.write(f"\n===== Hang watchdog armed {datetime.now():%Y-%m-%d %H:%M:%S}, "
                        f"threshold {HANG_WATCHDOG_TIMEOUT_SECS}s =====\n")
    self._LogFile.flush()

    # Also dump on a hard crash (e.g. a segfault in a native extension) to the same file.
    faulthandler.enable(file=self._LogFile)

    # Pet often (and well within the timeout window) so a healthy event loop always cancels
    # the pending dump before it could fire, and so a freeze is detected without much extra
    # latency beyond the threshold itself.
    self._PetTimer = QTimer(self)
    self._PetTimer.setSingleShot(False)
    self._PetTimer.timeout.connect(self._Pet)
    PetIntervalMs = max(1000, min(5000, int(1000 * HANG_WATCHDOG_TIMEOUT_SECS / 3)))
    self._PetTimer.start(PetIntervalMs)

    # Arm immediately so a freeze before the first pet is still caught.
    self._Pet()


  ###############################################
  # _Pet - Cancel the pending dump and re-arm it; called each timer tick
  #
  # While the event loop runs this fires often enough that the dump is always canceled
  # before its countdown elapses.  If the loop freezes, the last-armed dump fires.
  #

  def _Pet(self):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(HANG_WATCHDOG_TIMEOUT_SECS, repeat=False,
                                      file=self._LogFile, exit=False)


  ###############################################
  # Stop - Disarms the watchdog (e.g. at clean shutdown)
  #

  def Stop(self):
    self._PetTimer.stop()
    faulthandler.cancel_dump_traceback_later()
    # We intentionally leave faulthandler.enable() active and the log file open: Stop() runs
    # at app shutdown, and we still want a hard-crash traceback if the teardown itself
    # crashes.  The OS releases the file when the process exits.  (The watchdog is
    # single-instance, so this never leaks; were it ever reconstructed mid-run, Stop would
    # need to faulthandler.disable() and close the file here.)
