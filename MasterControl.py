import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer

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

    # Create grid layout for 5x3 collector panes
    layout = QGridLayout(self)
    self.collector_panes = []

    for row in range(5):
      for col in range(3):
        collector_pane = CollectorPane(self)
        collector_pane.setFixedSize(collector_pane.size())
        layout.addWidget(collector_pane, row, col)
        self.collector_panes.append(collector_pane)
    self.setLayout(layout)


if __name__ == "__main__":
  app = QApplication(sys.argv)

  MainWin = MasterControl()
  MainWin.show()
  getattr(MainWin, "raise")()
  MainWin.activateWindow()
  

  # Show Collector Control Window
  CollectorControlWindow = CollectorControl()
  CollectorControlWindow.show()
  getattr(CollectorControlWindow, "raise")()
  CollectorControlWindow.activateWindow()
  
  sys.exit(app.exec())
