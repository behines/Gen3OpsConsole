#################################################
#
# WINDSOR PROJECT CONFIGURATION
#
# This file contains the site-specific hardware facts for the Windsor
# installation.  Shared config types, enums, timing defaults, and compatibility
# exports remain in ConfigInfo.py.
#

from ProjectConfig import CollectorMapping, PICOTOOL_PATH, tProjectConfig


WINDSOR_AGILENTS = [  [ 'ASRL4::INSTR',              # Port
                        '101:120,201:220,301:320',   # Full scan channel list
                        '101:120,201:220,301:320',   # Thermocouple channel list
                        None,                        # GHI channel
                        None,                        # DNI Channel
                        8.23,                        # NIP Gain in uV per W/m^2
                        303                          # Channel to display on front panel
                      ],
                      [ 'ASRL5::INSTR',              # Port
                        '101:120,201:220',           # Full scan channel list
                        '101:120,201:220',           # Thermocouple channel list
                        None,                        # GHI channel
                        None,                        # DNI Channel
                        8.23,                        # NIP Gain in uV per W/m^2
                        101                          # Channel to display on front panel
                      ],
                      [ 'ASRL6::INSTR',              # Port
                        '119:120',                   # Full scan channel list
                        None,                        # Thermocouple channel list
                        120,                         # GHI channel
                        119,                         # DNI Channel
                        8.23,                        # NIP Gain in uV per W/m^2
                        119                          # Channel to display on front panel  105 == NIP channel
                      ]
                   ]


WINDSOR_COLLECTOR_PORTS = [
  CollectorMapping('1A', 'COM8',  None),  # TODO: assign active Windsor board serial
  CollectorMapping('1B', 'COM10', None),  # TODO: assign active Windsor board serial
  CollectorMapping('1C', 'COM12', None),  # TODO: assign active Windsor board serial
  CollectorMapping('2A', 'COM14', None),  # TODO: assign active Windsor board serial
  CollectorMapping('2B', 'COM16', None),  # TODO: assign active Windsor board serial
]


MARQUEE_COM_PORT                = 'COM3'
OUTSIDE_TEMP_SENSOR_PORT        = 'COM7'   # Replace with your read serial port
DOME_TEMP_SENSOR_PORT           = 'COM39'
ELECTRONICS_TEMP_SENSOR_PORT    = 'COM38'  # Temp of electronics box

# CHANNEL NUMBERS UPDATED FOR NEW RELAY PANEL 12/6/2024
AGILENT_WITH_POWER_RELAYS       = 2        # The third Agilent (counting starts at zero)
NIP_POWER_CHANNELS              = '202:203'
NIP_ON_OFF_BUTTON_CHANNEL       = '201'
PYRANOMETER_POWER_CHANNEL       = '204'
MOTOR_POWER_CHANNELS            = '218:220'
USB_HUB_POWER_CHANNEL           = '217'

# This is the "Bearer" token assigned in the Callback pulldown menu for the Windsor device
THINGER_IO_BEARER_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJEZXZpY2VDYWxsYmFja19XaW5kc29yIiwic3ZyIjoidXMtd2VzdC5hd3MudGhpbmdlci5pbyIsInVzciI6ImJlaGluZXMifQ.1ZBsOMKvGqnh-8w2-0OWa6iGcim05X0bBAKQw33XRE8"


WINDSOR_CONFIG = tProjectConfig(
  Name = "windsor",
  DisplayName = "Windsor",
  WindowTitle = "Windsor Master Control Console",
  MenuTitle = "WindsorOps",
  LogFolder = "WindsorDailyLog",
  LogFilePrefix = "Windsor",
  ArchiveFolder = "Nextcloud/Engineering/Calseed Prototype/Data/DailyLogs",
  HeaderIdentity = '"Windsor Testbed","Version","1.0"',
  Latitude = 34.183941,
  Longitude = -118.168791,
  Elevation = 331,
  Timezone = "America/Los_Angeles",
  Agilents = WINDSOR_AGILENTS,
  CollectorPorts = WINDSOR_COLLECTOR_PORTS,
  CollectorGridRows = 2,
  CollectorGridCols = 3,
  MarqueePort = MARQUEE_COM_PORT,
  OutsideTempSensorPort = OUTSIDE_TEMP_SENSOR_PORT,
  DomeTempSensorPort = DOME_TEMP_SENSOR_PORT,
  ElectronicsTempSensorPort = ELECTRONICS_TEMP_SENSOR_PORT,
  PowerRelayAgilentIndex = AGILENT_WITH_POWER_RELAYS,
  MotorPowerChannels = MOTOR_POWER_CHANNELS,
  UsbHubPowerChannel = USB_HUB_POWER_CHANNEL,
  NipPowerChannels = NIP_POWER_CHANNELS,
  NipOnOffButtonChannel = NIP_ON_OFF_BUTTON_CHANNEL,
  PyranometerPowerChannel = PYRANOMETER_POWER_CHANNEL,
  bUseDniToStartDay = True,
  CollectorStartAfterSunriseMinutes = 30,
  CollectorStopBeforeSunsetMinutes = 30,
  PicotoolPath = PICOTOOL_PATH,
  ThingerUserName = "behines",
  ThingerDeviceId = "Windsor",
  ThingerBucketId = "Windsor_Data",
  ThingerBearerToken = THINGER_IO_BEARER_TOKEN,
)
