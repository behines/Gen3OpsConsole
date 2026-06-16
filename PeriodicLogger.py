#######################################################
# tPeriodicLogger - Runs once a minute (or so) to do data logging, also sends data to the marquee
#
# This class owns the Marquee display, since that simplifies connectivity.  This is the only 
# class that needs to talk to the marquee display.  Having it own tMarquee means that it is
# owned by the same thread that reads all the states, so it can communicate directly with 
# the marquee display rather than having to use signals.

from PySide6.QtCore import QObject, Signal, QTimer

# Import configuration of the system
from ConfigInfo    import *
from Utilities     import tActiveObject
from Agilent       import tAgilent
from TempHumSensor import tTempHumSensor
from Marquee       import tMarquee
from LogFile       import tLogFile
from Thinger       import tThinger


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

  def __init__(self, Agilents : list[tAgilent], GhiChannelIndex, DniChannelIndex, BoxMeasurementIndex,
               SandTopMeasurementIndex, SandMidMeasurementIndex, SandBotMeasurementIndex,
               DomeTempSensor, OutsideTempSensor, ElectronicsTempSensor, Collectors, LogFile: tLogFile,
               CollectorLogFiles=None, MasterConsoleLog=None, parent=None):
    super().__init__(LOG_INTERVAL_SECONDS * 1000, parent)   # # tActiveObject constructor

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
    self.CollectorLogFiles     = CollectorLogFiles
    self.MasterConsoleLog      = MasterConsoleLog

    # Marquee display
    self.Marquee               = tMarquee(PROJECT_CONFIG.MarqueePort, Collectors, self) if PROJECT_CONFIG.bHasMarquee else None


    # moveToThread() to changes the thread affinity of a QObject (and its children). This means that the object's
    # slots and event handlers will be executed in the thread to which it's moved.

    # Take ownership of the Agilents and temp sensor objects
    for agilent in self.Agilents:
      #agilent.moveToThread(self)
      agilent.setParent(self)

    if self.DomeTempSensor is not None:
      self.DomeTempSensor.setParent(self)
    if self.OutsideTempSensor is not None:
      self.OutsideTempSensor.setParent(self)
    if self.ElectronicsTempSensor is not None:
      self.ElectronicsTempSensor.setParent(self)

    # Create the Thinger.io object for logging to the cloud
    self.Thinger = tThinger() if PROJECT_CONFIG.bHasThinger else None

    # Guards against initiating a new scan cycle while the previous cycle's read is still
    # in progress.  That can only happen if a read runs long (e.g. a wedged scan hitting
    # the AGILENT_SCAN_COMPLETE_TIMEOUT_SECS backstop); without the guard we could re-INIT
    # an Agilent mid-FETCH and scramble its serial conversation.
    self._bLogInProgress = False

    # Create the timer to awaken and read the scanned thermocouples after half a period
    self.ReadScannedResultsTimer = QTimer(self)
    self.ReadScannedResultsTimer.setSingleShot(True)
    self.ReadScannedResultsTimer.timeout.connect(self.LogTemperatureData)

    # start the periodic timer running to cause callbacks to PeriodicMethod
    self.Start()



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
    # Belt-and-suspenders: never start a new scan while the previous cycle's read is still
    # running, or we'd re-INIT an Agilent mid-FETCH and scramble its serial conversation.
    # This only occurs if a read runs long; skip this cycle (the next one will try again).
    if self._bLogInProgress:
      print('tPeriodicLogger: WARNING - previous scan/log cycle still running; '
            'skipping this cycle to avoid overlapping scans', flush=True)
      return

    if len(self.Agilents) > 0:
      self.InitiateScansOnAllAgilents()

    # Exit for now, then awaken 3/4 of the way through the periodic task interval to read the results
    self.ReadScannedResultsTimer.start(1000 * LOG_INTERVAL_SECONDS * 3/4)
    


  ###############################################
  # InitiateScansOnAllAgilents - Kick off the thermocouple scan on all Agilents
  # 

  def InitiateScansOnAllAgilents(self):
    for agilent in self.Agilents:
      with agilent:  # Acquire the lock
        agilent.DoScan()


  ###############################################
  # LogTemperatureData - reentrancy-guarded entry point called by ReadScannedResultsTimer
  #
  # Holds _bLogInProgress for the duration so PeriodicMethod won't kick off an overlapping
  # scan cycle if this read ever runs long.  try/finally guarantees the flag clears even if
  # the read raises, so a one-off error can't permanently wedge all future logging.
  #

  def LogTemperatureData(self):
    self._bLogInProgress = True
    try:
      self._LogTemperatureData()
    finally:
      self._bLogInProgress = False


  ###############################################
  # _LogTemperatureData
  #
  # Note that for the Agilents and Temp sensors and the marquee display, it's okay
  # to use "with" and read directly rather than signaling, because those objects
  # are in the same thread with us.
  #
  # INPUTS:
  #   ScheduledTime - the QDateTime that the method was scheduled to run, in the current time zone

  def _LogTemperatureData(self):
    ###
    # Collect all data
    #

    # Read the Agilents and build out a string
    OutputLine = ''
    for agilent in self.Agilents:
      with agilent:  # Acquire the lock
        OutputLine = OutputLine + agilent.RetrieveScanResults(True) + ','
    # Remove the final extra comma
    OutputLine = OutputLine.rstrip(',')  # Remove trailing comma

    GHI = 0.0
    DNI = 0.0
    BoxTemp = 0.0
    SandTopTemp = 0.0
    SandMidTemp = 0.0
    SandBotTemp = 0.0
    
    try:
      OutputLineParsed = list(map(float,OutputLine.split(',')))
      # Get the "box" reading to send to the marquee display
      if self.BoxMeasurementIndex is not None:
        BoxTemp = OutputLineParsed[self.BoxMeasurementIndex]
        if BoxTemp<-1E37:   # bad thermocouple
          BoxTemp = 0
      if self.SandTopMeasurementIndex is not None:
        SandTopTemp = OutputLineParsed[self.SandTopMeasurementIndex]
        if SandTopTemp < -1E37:
          SandTopTemp = 0
      if self.SandMidMeasurementIndex is not None:
        SandMidTemp = OutputLineParsed[self.SandMidMeasurementIndex]
        if SandMidTemp < -1E37:
          SandMidTemp = 0
      if self.SandBotMeasurementIndex is not None:
        SandBotTemp = OutputLineParsed[self.SandBotMeasurementIndex]
        if SandBotTemp < -1E37:
          SandBotTemp = 0

      # Get the GHI and DNI
      if not self.GhiChannelIndex is None:
        GHI = OutputLineParsed[self.GhiChannelIndex]
      if not self.DniChannelIndex is None:
        DNI = OutputLineParsed[self.DniChannelIndex]
      # Clip nonsensical DNI and GHI values
      GHI = 0.0 if GHI < 0.0 else GHI
      DNI = 0.0 if DNI < 0.0 else DNI
      GHI = 0.0 if GHI > 2000.0 else GHI
      DNI = 0.0 if DNI > 2000.0 else DNI
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
    DomeReadings    = self.DomeTempSensor.GetReading() if self.DomeTempSensor is not None else None
    if DomeReadings == None:
      DomeReadings = [ 0, 0 ]
    DomeTemp = float(DomeReadings[0])

    OutsideReadings = self.OutsideTempSensor.GetReading() if self.OutsideTempSensor is not None else None
    if OutsideReadings == None:
      OutsideReadings = [ 0, 0 ]
    StanTemp = float(OutsideReadings[0])

    ElecBoxReadings = self.ElectronicsTempSensor.GetReading() if self.ElectronicsTempSensor is not None else None
    if ElecBoxReadings == None:
      ElecBoxReadings = [ 0, 0 ]
    ElecTemp = float(ElecBoxReadings[0])

    TempHumidityFields = []
    if PROJECT_CONFIG.bHasOutsideTempSensor:
      TempHumidityFields.extend(OutsideReadings)
    if PROJECT_CONFIG.bHasDomeTempSensor:
      TempHumidityFields.extend(DomeReadings)
    if PROJECT_CONFIG.bHasElectronicsTempSensor:
      TempHumidityFields.extend(ElecBoxReadings)
    if len(TempHumidityFields) > 0:
      if OutputLine != '':
        OutputLine += ','
      OutputLine += ','.join(map(str, TempHumidityFields))

    CpuTempFields = []
    for Collector in self.Collectors:
      CpuTempFields.append(str(Collector.CpuTemp) if Collector.CpuTemp is not None else '')
    if OutputLine != '':
      OutputLine += ','
    OutputLine += ','.join(CpuTempFields)

    CollectorSnapshotFields = []
    for Collector in self.Collectors:
      CollectorSnapshotFields.append(str(Collector.CollectorState.value))
      CollectorSnapshotFields.append(Collector.CollectorState.name)
    OutputLine += ',' + ','.join(CollectorSnapshotFields)

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
      if self.MasterConsoleLog is not None:
        self.MasterConsoleLog.StartNewFile()
      if self.CollectorLogFiles is not None:
        self.CollectorLogFiles.StartNewFiles()
      pass #Sequencer.StartNewDay()

    # Send data to the marquee display
    if self.Marquee is not None:
      with self.Marquee as marquee:
        marquee.SendTemps(*DomeReadings, *OutsideReadings, BoxTemp)
        marquee.SendSun(GHI, DNI)
        for collector in self.Collectors:
          marquee.SendCollectorState(collector.CollectorName, collector.CollectorState)

    print(self.ScheduledTime.toString('yyyy-MM-dd HH:mm:ss'),': Temps: Box=', BoxTemp, 'Dome=', DomeTemp, ' Elec=', ElecTemp,' Stan=', StanTemp,' DNI=', DNI, ' GHI=', GHI, flush=True)
  
    # Log to the cloud
    if self.Thinger is not None:
      self.Thinger.LogData(DNI, GHI, BoxTemp, SandTopTemp, SandMidTemp, SandBotTemp, DomeTemp,  ElecTemp, StanTemp)

    # Return 0 to request continuing scheduling
    return 0
  
