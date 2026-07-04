#################################################
#
# BRAD PROJECT CONFIGURATION
#
# This file contains a Sandia-like single-collector configuration for local
# testing.  Missing hardware is represented with [] for lists and None for
# single ports, channel groups, and credentials.
#
# This is for standalone testing by Brad on his computer.
#

from ProjectConfig import CollectorMapping, PICOTOOL_PATH, tProjectConfig


BRAD_COLLECTOR_PORTS = [
  CollectorMapping('1A', 'COM7', 'G3V2-0009'),
]


BRAD_CONFIG = tProjectConfig(
  Name = "brad",
  DisplayName = "Brad",
  WindowTitle = "Brad Master Control Console",
  MenuTitle = "BradOps",
  LogFolder = "BradDailyLog",
  LogFilePrefix = "Brad",
  ArchiveFolder = "BradDailyLogArchive",
  HeaderIdentity = '"Brad","Version","1.0"',
  Latitude = 34.183941,
  Longitude = -118.168791,
  Elevation = 331,
  Timezone = "America/Los_Angeles",
  Agilents = [],
  CollectorPorts = BRAD_COLLECTOR_PORTS,
  CollectorGridRows = 1,
  CollectorGridCols = 1,
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
