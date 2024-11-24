##########################################################################################
# tCollectorControlWindow - class for the window that contains the 15 individual collectors
#

#################################################
#
# Modules used
#

from collections import namedtuple

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtCore    import Qt, QFile

# Import configuration of the system
from CollectorPane_ui  import Ui_Form
from ConfigInfo        import *
from Collector         import tCollector
from Utilities         import WaitForSignal



##########################################################################################
##########################################################################################
##########################################################################################
# tCollectorPane  - Class that implements the collector pane and all collector activities
#
# 
#

class tCollectorPane(QWidget):
  
  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, collectorName, portName, baud, parent=None):
    super().__init__(parent)   # QWidget constructor
      
    self.bInit    = False
    self.bResponded  = False
    self.name     = 'Foo' #collectorName
    self.port     = None

    # Load CollectorPane UI dynamically
    #loader = QUiLoader()
    #ui_file = QFile("CollectorPane.ui")
    #ui_file.open(QFile.ReadOnly)
    #self.ui = loader.load(ui_file, self)    # Have to assign to self so that ui and all its children persist after the constructor exits
    #ui_file.close()

    # Auto-bind widgets as attributes of self.  Not needed if we compile the UI with pyside6-uic,
    # but QUiLoader does not do this automatically.
    #for widget in self.ui.findChildren(QWidget):
    #  setattr(self, widget.objectName(), widget)
    # self.setFixedSize(self.ui.size())


    self.ui = Ui_Form()
    self.ui.setupUi(self)
    
    self.setFixedSize(self.size())

    collectorTitle = 'Collector ' + collectorName
    self.ui.CollectorGroup.setTitle(collectorTitle)


    # Create the Collector object that interfaces to the hardware
    self.Collector = tCollector(collectorName, portName, baud)
    self.Collector.SerialPort.PortOpenStateChange.connect(self.ConnectionEvent)


  ###############################################
  # Destructor - Clean up our orphaned child
  # 
  # INPUTS:
  #      
  def __del__(self):
    # Tell the periodic logger thread to shut down, and wait for confirmation
    WaitForSignal(SignalToWaitFor = self.Collector.TheThread.finished, SignalToEmit = self.Collector.RequestExit)
    # Now that the thread has exited, schedule it for deletion
    self.Collector.deleteLater()


  ###############################################
  # ConnectionEvent
  # 
  # INPUTS:
  #   bPortOpenState - True or False depending on whether the port is connected
  #     

  def ConnectionEvent(self):
    # TODO - update display to show connected state
    pass



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
    # Create a central widget and grid layout for 5x3 collector panes
    central_widget = QWidget()
    layout = QGridLayout(central_widget)

    # Create the collector array.  We have to do it here, rather than at a higher level,
    # because the tCollector widget needs to be told its parent.  The collector panes will 
    # create and own the collecor objects
    self.CollectorPanes = [ tCollectorPane(*port_info, COLLECTOR_BAUD_RATE, self) for port_info in COLLECTOR_PORTS ]
    Collector_iterator = (CollectorPane for CollectorPane in self.CollectorPanes)  # Compact generator for use in loop below
    #for row in range(5):
    #  for col in range(3):
    #    layout.addWidget(next(Collector_iterator), row, col)
    layout.addWidget(next(Collector_iterator), 0, 0)

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


  ###############################################
  # ForceClose - used by MainWin to shut us down at exit
  #    

  def ForceClose(self):
    self.bAllowClose = True
    self.close()


  ###############################################
  # closeEvent - rejects any attempt to close the window directly - it must follow MainWin
  #    

  def closeEvent(self, event):
    if not self.bAllowClose:
      # Ignore any close events
      QMessageBox.warning(self, "Warning", "You cannot close this window directly.")
      event.ignore()


  ###############################################
  # CollectorList - Returns a list of all 15 collectors
  # 

  def CollectorList(self):
    CollectorList = [ CollectorPane.Collector for CollectorPane in self.CollectorPanes ]
    return CollectorList
