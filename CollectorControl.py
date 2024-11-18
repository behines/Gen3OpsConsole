##########################################################################################
# tCollectorControlWindow - class for the window that contains the 15 individual collectors
#

#################################################
#
# Modules used
#

# module used to get the current date and time
from datetime import datetime, timedelta
from collections import namedtuple


from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtCore import QFile, Qt, QTimer

# Import configuration of the system
from ConfigInfo import *
from Collector  import tCollector


##########################################################################################
##########################################################################################
##########################################################################################
#
# tCollectorControlWindow - class for the main "master control" window of the app
#
# Also includes all top-level sequencing and logic
#

class tCollectorControlWindow(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Collector Control")

    # Create the collector array.  We have to do it here, rather than at a higher level,
    # because the tCollector widget needs to be told its parent
    Collectors = [ tCollector(*port_info, COLLECTOR_BAUD_RATE, self) for port_info in COLLECTOR_PORTS ]

    Collector_iterator = (collector for collector in Collectors)  # Compact generator

    # Create a central widget and grid layout for 5x3 collector panes
    central_widget = QWidget()
    layout = QGridLayout(central_widget)
    
    for row in range(5):
      for col in range(3):
        layout.addWidget(next(Collector_iterator), row, col)

    # Wrap the central widget with a QScrollArea
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(central_widget)

    # Only enable vertical scroll bar
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    # Set the scroll area as the main layout
    main_layout = QVBoxLayout(self)
    main_layout.addWidget(scroll_area)
    self.setLayout(main_layout)

    # Disable the close button in this window
    self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

    self.bAllowClose = False

  def ForceClose(self):
    self.bAllowClose = True
    self.close()

  def closeEvent(self, event):
    if not self.bAllowClose:
      # Ignore any close events
      QMessageBox.warning(self, "Warning", "You cannot close this window directly.")
      event.ignore()

