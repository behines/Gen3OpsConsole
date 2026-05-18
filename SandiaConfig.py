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
  CollectorMapping('1A', 'COM1',  None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('1B', 'COM2',  None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('1C', 'COM3',  'G3V2-0005'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('2A', 'COM4',  None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('2B', 'COM5',  'G3V2-0008'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('2C', 'COM6',  'G3V2-0013'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('3A', 'COM7',  'G3V2-0003'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('3B', 'COM8',  'G3V2-0028'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('3C', 'COM9',  'G3V2-0012'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('4A', 'COM10', 'G3V2-0018'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('4B', 'COM11', 'G3V2-0023'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('4C', 'COM12', None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('5A', 'COM13', 'G3V2-0016'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('5B', 'COM14', 'G3V2-0007'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('5C', 'COM15', 'G3V2-0020'),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('6A', 'COM16', None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('6B', 'COM17', None),  # TODO: assign Sandia COM port and board serial
  CollectorMapping('6C', 'COM18', None),  # TODO: assign Sandia COM port and board serial
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
