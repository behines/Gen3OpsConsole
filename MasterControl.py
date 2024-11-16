import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

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
    
    if not self.window:
      QMessageBox.critical(self, "Error", "Failed to load UI file")
      sys.exit(1)
    
    # Integrate the loaded UI
    self.setCentralWidget(ui.centralWidget())  # Use the central widget from the loaded UI
    self.adjustSize()

    self.setWindowTitle('Windsor Master Control Console')

    # Show Collector Control Window
    #self.collector_control_window = CollectorControl()
    #self.collector_control_window.show()


class CollectorPane(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    
    # Load CollectorPane UI dynamically
    loader = QUiLoader()
    ui_file = QFile("CollectorPane.ui")
    ui_file.open(QFile.ReadOnly)
    ui = loader.load(ui_file, self)
    ui_file.close()

    # Set the loaded UI layout to the widget
    layout = self.layout()
    self.setLayout(layout)


class CollectorControl(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Collector Control")
    
    # Create grid layout for 5x3 collector panes
    layout = QGridLayout(self)
    for row in range(5):
      for col in range(3):
        collector_pane = CollectorPane(self)
        layout.addWidget(collector_pane, row, col)
    self.setLayout(layout)

if __name__ == "__main__":
  app = QApplication(sys.argv)

  # Load MasterControl UI dynamically
  #loader = QUiLoader()
  #ui_file = QFile("Gen2OpsConsole.ui")
   
  #ui_file.open(QFile.ReadOnly)
  #MainWin = loader.load(ui_file)
  #ui_file.close()

  MainWin = MasterControl()
  MainWin.show()
  getattr(MainWin, "raise")()
  MainWin.activateWindow()
  
  sys.exit(app.exec())
