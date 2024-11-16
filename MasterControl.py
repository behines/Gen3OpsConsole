import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QScrollArea, QVBoxLayout, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt

class MasterControl(QMainWindow):
  def __init__(self, parent=None):
    super().__init__(parent)
    
    # Load MasterControl UI dynamically
    loader = QUiLoader()
    ui_file = QFile("Gen2OpsConsole.ui")
    
    if not ui_file.exists():
      QMessageBox.critical(self, "Error", "UI file not found: Gen2OpsConsole.ui")
      sys.exit(1)
    
    ui_file.open(QFile.ReadOnly)
    ui = loader.load(ui_file, self)
    ui_file.close()
    
    # Integrate the loaded UI
    self.setCentralWidget(ui.centralWidget())  # Use the central widget from the loaded UI
    self.setWindowTitle('Windsor Master Control Console')

    # Create Collector Control Window
    self.CollectorControlWindow = CollectorControl()
    self.CollectorControlWindow.show()
    getattr(self.CollectorControlWindow, "raise")()
    self.CollectorControlWindow.activateWindow()

  def closeEvent(self, event):
    # Ensure the CollectorControlWindow is closed when the main window is closed
    if self.CollectorControlWindow:
      self.CollectorControlWindow.ForceClose()
    event.accept()  # Proceed with closing MainWin


class CollectorPane(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    
    # Load CollectorPane UI dynamically
    loader = QUiLoader()
    ui_file = QFile("CollectorPane.ui")
    ui_file.open(QFile.ReadOnly)
    ui = loader.load(ui_file, self)
    ui_file.close()

    self.setFixedSize(ui.size())


class CollectorControl(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Collector Control")

    # Create a central widget and grid layout for 5x3 collector panes
    central_widget = QWidget()
    layout = QGridLayout(central_widget)
    
    for row in range(5):
      for col in range(3):
        collector_pane = CollectorPane(self)
        layout.addWidget(collector_pane, row, col)

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


if __name__ == "__main__":
  app = QApplication(sys.argv)

  MainWin = MasterControl()
  MainWin.show()
  getattr(MainWin, "raise")()
  MainWin.activateWindow()
  


  
  sys.exit(app.exec())
