#################################################
#
# PROJECT CONFIGURATION TYPES
#
# Defines the shared data structures used by ConfigInfo.py and the individual
# site configuration files.
#

from collections import namedtuple
from dataclasses  import dataclass


AGILENT_DESCRIPTOR_FIELDS = [ 'Port','Channel list','Thermocouple channels','GHI channels','DNI channels','DNI gain','Front panel channel' ]
CollectorMapping = namedtuple('CollectorMapping', ['Name', 'Port', 'BoardSerial'])
PICOTOOL_PATH = r"C:\Users\brad\.pico-sdk\picotool\2.0.0\picotool\picotool.exe"


@dataclass
class tProjectConfig:
  Name: str
  DisplayName: str
  WindowTitle: str
  MenuTitle: str
  LogFolder: str
  LogFilePrefix: str
  ArchiveFolder: str
  HeaderIdentity: str
  Latitude: float
  Longitude: float
  Elevation: float
  Timezone: str
  Agilents: list
  CollectorPorts: list
  CollectorGridRows: int
  CollectorGridCols: int
  MarqueePort: str | None
  OutsideTempSensorPort: str | None
  DomeTempSensorPort: str | None
  ElectronicsTempSensorPort: str | None
  PowerRelayAgilentIndex: int | None
  MotorPowerChannels: str | None
  UsbHubPowerChannel: str | None
  NipPowerChannels: str | None
  NipOnOffButtonChannel: str | None
  PyranometerPowerChannel: str | None
  bUseDniToStartDay: bool
  CollectorStartAfterSunriseMinutes: int
  CollectorStopBeforeSunsetMinutes: int
  PicotoolPath: str
  ThingerUserName: str | None
  ThingerDeviceId: str | None
  ThingerBucketId: str | None
  ThingerBearerToken: str | None

  #################################################
  #
  # Derived capability properties
  #
  # Python properties are methods that callers read like normal attributes.
  # For example, call sites use PROJECT_CONFIG.bHasAgilents, but the value is
  # computed from PROJECT_CONFIG.Agilents each time it is read.  That preserves
  # the readable bHas... style without making anyone maintain a second copy of
  # the same fact.
  #
  # The maintenance rule is simple: edit the lists, ports, channel groups, and
  # credentials above.  Do not add manually-entered capability booleans.  Add a
  # property only when multiple call sites need the same capability question
  # answered from real config data.
  #

  @property
  def bHasAgilents(self):
    return len(self.Agilents) > 0

  @property
  def bHasThermocouples(self):
    return any(agilent[AGILENT_DESCRIPTOR_FIELDS.index('Thermocouple channels')] is not None for agilent in self.Agilents)

  @property
  def bHasOutsideTempSensor(self):
    return self.OutsideTempSensorPort is not None

  @property
  def bHasDomeTempSensor(self):
    return self.DomeTempSensorPort is not None

  @property
  def bHasElectronicsTempSensor(self):
    return self.ElectronicsTempSensorPort is not None

  @property
  def bHasTempHumiditySensors(self):
    return self.bHasOutsideTempSensor or self.bHasDomeTempSensor or self.bHasElectronicsTempSensor

  @property
  def bHasMarquee(self):
    return self.MarqueePort is not None

  @property
  def bHasThinger(self):
    return self.ThingerUserName is not None and self.ThingerDeviceId is not None and self.ThingerBucketId is not None and self.ThingerBearerToken is not None

  @property
  def bHasNip(self):
    return self.PowerRelayAgilentIndex is not None and self.NipPowerChannels is not None and self.NipOnOffButtonChannel is not None

  @property
  def bHasPyranometer(self):
    return self.PowerRelayAgilentIndex is not None and self.PyranometerPowerChannel is not None

  @property
  def bHasMotorPowerRelay(self):
    return self.PowerRelayAgilentIndex is not None and self.MotorPowerChannels is not None

  @property
  def bHasUsbPowerRelay(self):
    return self.PowerRelayAgilentIndex is not None and self.UsbHubPowerChannel is not None

  @property
  def bHasPowerRelays(self):
    return self.bHasMotorPowerRelay or self.bHasUsbPowerRelay or self.bHasNip or self.bHasPyranometer

  @property
  def bHasDniSensor(self):
    return any(agilent[AGILENT_DESCRIPTOR_FIELDS.index('DNI channels')] is not None for agilent in self.Agilents)

  @property
  def bHasGhiSensor(self):
    return any(agilent[AGILENT_DESCRIPTOR_FIELDS.index('GHI channels')] is not None for agilent in self.Agilents)
