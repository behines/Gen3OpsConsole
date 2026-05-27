#################################################
#
# SANDIA PROJECT CONFIGURATION
#
# This file contains the site-specific hardware facts for the Sandia
# installation.  Missing hardware is represented with [] for lists and None for
# single ports, channel groups, and credentials.
#

from ProjectConfig import CollectorMapping, PICOTOOL_PATH, tProjectConfig


SANDIA_COLLECTOR_PORTS = [
  CollectorMapping('1A', 'COM22', 'G3V2-0024'),
  CollectorMapping('1B', 'COM11', 'G3V2-0023'),
  CollectorMapping('1C', 'COM21', 'G3V2-0004'),

  CollectorMapping('2A', 'COM14', 'G3V2-0007'),
  CollectorMapping('2B', 'COM7',  'G3V2-0003'),   # This is collector 26.  Board was swapped with Collector 3.
  CollectorMapping('2C', 'COM20', 'G3V2-0021'),

  CollectorMapping('3A', 'COM16', 'G3V2-0014'),
  CollectorMapping('3B', 'COM5',  'G3V2-0008'),
  CollectorMapping('3C', 'COM15', 'G3V2-0020'),

  CollectorMapping('4A', 'COM9',  'G3V2-0012'),
  CollectorMapping('4B', 'COM24', 'G3V2-0006'),   # I had this as G3V2-0024 but I think that was wrong.
  CollectorMapping('4C', 'COM6',  'G3V2-0013'),

  CollectorMapping('5A', 'COM18', 'G3V2-0010'),
  CollectorMapping('5B', 'COM23', 'G3V2-0017'),
  CollectorMapping('5C', 'COM3',  'G3V2-0005'),

  CollectorMapping('6A', 'COM13', 'G3V2-0016'),
  CollectorMapping('6B', 'COM10', 'G3V2-0018'),
  CollectorMapping('6C', 'COM17', 'G3V2-0022'),
]


SANDIA_CONFIG = tProjectConfig(
  Name = "sandia",
  DisplayName = "Sandia",
  WindowTitle = "Sandia Master Control Console",
  MenuTitle = "SandiaOps",
  LogFolder = "SandiaDailyLog",
  LogFilePrefix = "Sandia",
  ArchiveFolder = "SandiaDailyLogArchive",
  HeaderIdentity = '"Sandia NSTTF","Version","1.0"',
  Latitude = 34.963889,
  Longitude = -106.509722,
  Elevation = 1705,  # TODO: confirm exact collector installation elevation
  Timezone = "America/Denver",
  Agilents = [],
  CollectorPorts = SANDIA_COLLECTOR_PORTS,
  CollectorGridRows = 6,
  CollectorGridCols = 3,
  MarqueePort = None,
  MarqueeDisplayOrder = None,
  OutsideTempSensorPort = None,
  DomeTempSensorPort = None,
  ElectronicsTempSensorPort = None,
  PowerRelayAgilentIndex = None,
  MotorPowerChannels = None,
  UsbHubPowerChannel = None,
  NipPowerChannels = None,
  NipOnOffButtonChannel = None,
  PyranometerPowerChannel = None,
  bUseDniToStartDay = False,
  CollectorStartAfterSunriseMinutes = 30,
  CollectorStopBeforeSunsetMinutes = 30,
  PicotoolPath = PICOTOOL_PATH,
  ThingerUserName = None,
  ThingerDeviceId = None,
  ThingerBucketId = None,
  ThingerBearerToken = None,
)
