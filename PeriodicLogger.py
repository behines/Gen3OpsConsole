#######################################################
# tPeriodicLogger - Runs once a minute (or so) to do data logging, also sends data to the marquee
#
# This class owns the Marquee display, since that simplifies connectivity.  This is the only 
# class that needs to talk to the marquee display.  Having it own tMarquee means that it is
# owned by the same thread that reads all the states, so it can communicate directly with 
# the marquee display rather than having to use signals.

from PySide6.QtCore import QObject, QTimer, Signal

# Import configuration of the system
from ConfigInfo import *
from Utilities  import tPeriodicThread
from Agilent    import tAgilent
from Marquee    import tMarquee


##########################################################################################
##########################################################################################
##########################################################################################
# tPeriodicLogger 
#
#

class tPeriodicLogger(tPeriodicThread):

  #######################
  # Qt Signal declarations.  This is how Qt allows us to make a function call into a
  # different thread.  See https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect
  # 

  DniUpdate     = Signal(float)
  GhiUpdate     = Signal(float)
  BoxTempUpdate = Signal(float)
  DomeTempUpdate = Signal(float)

  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex,
               DomeTempSensor, OutsideTempSensor, ElectronicsTempSensor, Collectors, parent=None):
    super().__init__(parent)   # tPeriodicThread constructor

    self.Agilents = Agilents

    self.GhiChannelIndex       = GhiChannelIndex
    self.DniChannelIndex       = DniChannelIndex
    self.BoxMeasurementIndex   = BoxMeasurementIndex
    self.DomeTempSensor        = DomeTempSensor
    self.OutsideTempSensor     = OutsideTempSensor
    self.ElectronicsTempSensor = ElectronicsTempSensor

    self.Collectors          = Collectors

    # Marquee display
    self.Marquee       = tMarquee(MARQUEE_COM_PORT)

    self.SpawnPeriodicMethodAsThreadAndSetAffinityToNewThread(LOG_INTERVAL_SECONDS * 1000, self.PeriodicMethod)



  ###############################################
  # PeriodicMethod
  # 

  def PeriodicMethod(self):
    self.LogTemperatureData()


  ###############################################
  # LogTemperatureData
  # 
  # INPUTS:
  #   ScheduledTime - the QDateTime that the method was scheduled to run, in the current time zone

  def LogTemperatureData(self):

    ###
    # Collect all data
    #

    # Read the Agilents and build out a string
    OutputLine = ''
    for agilent in self.Agilents:
      with agilent:  # Acquire the lock
        OutputLine = OutputLine + agilent.Read(True) + ','
    # Remove the final extra comma

    # Get the "box" reading to send to the marquee display
    BoxTemp = float(OutputLine.split(',')[self.BoxMeasurementIndex])
    if BoxTemp<-1E37:   # bad thermocouple
      BoxTemp = 0

    # Get the GHI and DNI
    if not self.GhiChannelIndex is None:
      GHI = float(OutputLine.split(',')[self.GhiChannelIndex])
    if not self.DniChannelIndex is None:
      DNI = float(OutputLine.split(',')[self.DniChannelIndex])
    GHI = 0.0 if GHI < 0.0 else GHI
    DNI = 0.0 if DNI < 0.0 else DNI


    # Tell the sequencer about the new values
    #SystemState |= {'GHI': GHI, 'DNI': DNI}


    # Get the dome and outside temp sensor and electronics box temp readings
    DomeReadings    = self.DomeTempSensor.GetReading()
    if DomeReadings == None:
      DomeReadings = [ 0, 0 ]
    DomeTemp = float(DomeReadings[0])

    OutsideReadings = self.OutsideTempSensor.GetReading()
    if OutsideReadings == None:
      OutsideReadings = [ 0, 0 ]
    StanTemp = float(OutsideReadings[0])

    ElecBoxReadings = self.ElecTempSensor.GetReading()
    if ElecBoxReadings == None:
      ElecBoxReadings = [ 0, 0 ]
    ElecTemp = float(ElecBoxReadings[0])

    # Append the Outside and Dome and elec box readings to the data record
    OutputLine = OutputLine + ','.join(map(str, OutsideReadings + DomeReadings + ElecBoxReadings))

    #####
    # Log and display data
    #

    # Pass the timestamp into the logger
    #if LogFile.LogRecord(self.ScheduledTime, OutputLine):
      # If True, we've just crossed midnight - tell the sequencer
    #  pass #Sequencer.StartNewDay()

    # Send data to the marquee display
    CollectorStates =  [ 1,2,3,4,5, 0,0,0,0,0, 5,4,3,2,1 ]
    
    self.Marquee.SendAll(*DomeReadings, *OutsideReadings, BoxTemp, GHI, DNI, CollectorStates)

    print(self.ScheduledTime.strftime('%Y-%m-%d %H:%M:%S'),': Temps: Box=', BoxTemp, 'Dome=', DomeTemp, ' Elec=', ElecTemp,' Stan=',StanTemp,' DNI=', DNI, ' GHI=', GHI)
  