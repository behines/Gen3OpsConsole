#######################################################
# tPeriodicLogger - Runs once a minute (or so) to do data logging, also sends data to the marquee
#
# This class owns the Marquee display, since that simplifies connectivity.  This is the only 
# class that needs to talk to the marquee display.  Having it own tMarquee means that it is
# owned by the same thread that reads all the states, so it can communicate directly with 
# the marquee display rather than having to use signals.

from PySide6.QtCore import QObject, Signal

# Import configuration of the system
from ConfigInfo    import *
from Utilities     import tActiveObject
from Agilent       import tAgilent
from TempHumSensor import tTempHumSensor
from Marquee       import tMarquee
from LogFile       import tLogFile


##########################################################################################
##########################################################################################
##########################################################################################
# tPeriodicLogger 
#
#

class tPeriodicLogger(tActiveObject):

  #######################
  # Qt Signal declarations.  This is how Qt allows us to make a function call into a
  # different thread.  See https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect
  # 

  DniUpdate         = Signal(float)
  GhiUpdate         = Signal(float)
  BoxTempUpdate     = Signal(float)
  DomeTempUpdate    = Signal(float)
  ElecTempUpdate    = Signal(float)
  StanTempUpdate    = Signal(float)
  SandTopTempUpdate = Signal(float)
  SandMidTempUpdate = Signal(float)
  SandBotTempUpdate = Signal(float)

  ###############################################
  # Constructor
  # 
  # 
  # INPUTS:
  #
  #   parent - if provided, will be ignored, activeobject have to have no parent
  #     

  def __init__(self, Agilents, GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex,
               SandTopMeasurementIndex, SandMidMeasurementIndex, SandBotMeasurementIndex,
               DomeTempSensor, OutsideTempSensor, ElectronicsTempSensor, Collectors, LogFile: tLogFile, parent=None):
    super().__init__(parent)   # tPeriodicThread constructor

    self.Agilents = Agilents

    self.GhiChannelIndex       = GhiChannelIndex
    self.DniChannelIndex       = DniChannelIndex
    self.BoxMeasurementIndex   = BoxMeasurementIndex

    self.SandTopMeasurementIndex = SandTopMeasurementIndex
    self.SandMidMeasurementIndex = SandMidMeasurementIndex
    self.SandBotMeasurementIndex = SandBotMeasurementIndex

    self.DomeTempSensor        = DomeTempSensor       
    self.OutsideTempSensor     = OutsideTempSensor    
    self.ElectronicsTempSensor = ElectronicsTempSensor

    self.Collectors            = Collectors
    self.LogFile               = LogFile

    # Marquee display
    self.Marquee               = tMarquee(MARQUEE_COM_PORT, Collectors, self)


    # moveToThread() to changes the thread affinity of a QObject (and its children). This means that the object's
    # slots and event handlers will be executed in the thread to which it's moved.

    # Take ownership of the Agilents and temp sensor objects
    for agilent in self.Agilents:
      #agilent.moveToThread(self)
      agilent.setParent(self)

    self.DomeTempSensor       .setParent(self)
    self.OutsideTempSensor    .setParent(self)
    self.ElectronicsTempSensor.setParent(self)

    # StartThread moves ourself, and all our children, to the thread
    self.StartThread(LOG_INTERVAL_SECONDS * 1000, "Logger")



  ###############################################
  # Destructor
  # 
  # This will be called when the thread exits
  #     

  def __del__(self):
    pass
    #self.ShutDownComplete.emit()


  ###############################################
  # PeriodicMethod
  # 

  def PeriodicMethod(self):
    return self.LogTemperatureData()


  ###############################################
  # LogTemperatureData
  # 
  # Note that for the Agilents and Temp sensors and the marquee display, it's okay
  # to use "with" and read directly rather than signaling, because those objects 
  # are in the same thread with us.
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
    OutputLine = OutputLine.rstrip(',')  # Remove trailing comma
    
    try:
      OutputLineParsed = list(map(float,OutputLine.split(',')))
      # Get the "box" reading to send to the marquee display
      BoxTemp     = OutputLineParsed[self.BoxMeasurementIndex]
      if BoxTemp<-1E37:   # bad thermocouple
        BoxTemp = 0
      SandTopTemp = OutputLineParsed[self.SandTopMeasurementIndex]
      if SandTopTemp < -1E37:
        SandTopTemp = 0
      SandMidTemp = OutputLineParsed[self.SandMidMeasurementIndex]
      if SandMidTemp < -1E37:
        SandMidTemp = 0
      SandBotTemp = OutputLineParsed[self.SandBotMeasurementIndex]
      if SandBotTemp < -1E37:
        SandBotTemp = 0

      # Get the GHI and DNI
      if not self.GhiChannelIndex is None:
        GHI = OutputLineParsed[self.GhiChannelIndex]
      if not self.DniChannelIndex is None:
        DNI = OutputLineParsed[self.DniChannelIndex]
      GHI = 0.0 if GHI < 0.0 else GHI
      DNI = 0.0 if DNI < 0.0 else DNI
    except (ValueError, IndexError, TypeError) as e:
      GHI = 0.0
      DNI = 0.0
      BoxTemp = 0.0
      SandTopTemp = 0
      SandMidTemp = 0
      SandBotTemp = 0      

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

    ElecBoxReadings = self.ElectronicsTempSensor.GetReading()
    if ElecBoxReadings == None:
      ElecBoxReadings = [ 0, 0 ]
    ElecTemp = float(ElecBoxReadings[0])

    # Append the Outside and Dome and elec box readings to the data record
    OutputLine = OutputLine + ','.join(map(str, OutsideReadings + DomeReadings + ElecBoxReadings))

    self.DniUpdate        .emit(DNI)
    self.GhiUpdate        .emit(GHI)
    self.BoxTempUpdate    .emit(BoxTemp)
    self.DomeTempUpdate   .emit(DomeTemp)
    self.ElecTempUpdate   .emit(ElecTemp)
    self.StanTempUpdate   .emit(StanTemp)
    self.SandTopTempUpdate.emit(SandTopTemp)
    self.SandMidTempUpdate.emit(SandMidTemp)
    self.SandBotTempUpdate.emit(SandBotTemp)

    #####
    # Log and display data
    #

    # Pass the timestamp into the logger
    if self.LogFile.LogRecord(self.ScheduledTime, OutputLine):
    # If True, we've just crossed midnight - tell the sequencer
      pass #Sequencer.StartNewDay()

    # Send data to the marquee display
    with self.Marquee as marquee:    
      marquee.SendTemps(*DomeReadings, *OutsideReadings, BoxTemp)
      marquee.SendSun(GHI, DNI)

    print(self.ScheduledTime.toString('yyyy-MM-dd HH:mm:ss'),': Temps: Box=', BoxTemp, 'Dome=', DomeTemp, ' Elec=', ElecTemp,' Stan=',StanTemp,' DNI=', DNI, ' GHI=', GHI, flush=True)
  
    # Return 0 to request continuing scheduling
    return 0
  