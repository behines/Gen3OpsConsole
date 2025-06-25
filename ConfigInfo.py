#################################################
#
# CONFIGURATION 
#
# 

from collections import namedtuple
from enum        import IntEnum, auto

#################################################
#
# CONFIGURATION
#
# NOTE: Actuator configuration (power and shutter relays) is in the Sequencer module
#

##########
# Agilent Channel scan lists and configs
# Note that Agilent baud rate, parity, etc. are defined in Agilent.py since they really aren't 
# anything we want to configure.
#

# The results of GetAgilentInfo.py for each of the three units are as follows.  This allows them to be uniquely
# identified if need be.
#
# Unit 1 (ASRL4):
# HEWLETT-PACKARD,34970A,0,9-1-2
# Card 1:  HEWLETT-PACKARD,34901A,0,2.3
# Card 2:  HEWLETT-PACKARD,34901A,0,2.3
# Card 3:  HEWLETT-PACKARD,34901A,0,2.3
# 
# Unit 2 (ASRL5):
# HEWLETT-PACKARD,34970A,0,9-1-2
# Card 1:  HEWLETT-PACKARD,34901A,0,2.3
# Card 2:  HEWLETT-PACKARD,34901A,0,2.3
# Card 3:  HEWLETT-PACKARD,0,0,0
# 
# Unit 3 (ASRL 6):
# HEWLETT-PACKARD,34970A,0,9-1-2
# Card 1:  HEWLETT-PACKARD,34901A,0,2.0
# Card 2:  HEWLETT-PACKARD,34903A,0,1.0
# Card 3:  HEWLETT-PACKARD,0,0,0


# Elements of the AGILENTS array have 7 members.  The DESCRIPTOR_FIELDS tell what each of those 7 entries are
AGILENT_DESCRIPTOR_FIELDS = [ 'Port','Channel list','Thermocouple channels','GHI channels','DNI channels','DNI gain','Front panel channel' ]
AGILENTS = [  [ 'ASRL4::INSTR',              # Port
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

# CHANNEL NUMBERS UPDATED FOR NEW RELAY PANEL 12/6/2024

AGILENT_WITH_POWER_RELAYS = 2     # The third Agilent (counting starts at zero)
NIP_POWER_CHANNELS        = '202:203'
NIP_ON_OFF_BUTTON_CHANNEL = '201'
PYRANOMETER_POWER_CHANNEL = '204'
MOTOR_POWER_CHANNELS      = '218:220'    
USB_HUB_POWER_CHANNEL     = '217'


##########
# Shutters have a name and an Agilent channel
#

ShutterMapping = namedtuple('ShutterInfo', ['Name', 'Channel'])
SHUTTERS = [
  ShutterMapping('1A', '205'),
  ShutterMapping('1B', '206'),
  ShutterMapping('2A', '207'),
  ShutterMapping('2B', '208'),
  ShutterMapping('3A', '209'),   
  ShutterMapping('3B', '210'),
  ShutterMapping('4A', '211'),
  ShutterMapping('4B', '212'),
  ShutterMapping('5A', '213'),
  ShutterMapping('5B', '214'),
]

# The channel number here is 1000*mainframe number + channel number.  So 1303 is channel 303 from 
# the first unit in the list above.
BOX_CHANNEL_FOR_MARQUEE_DISPLAY = 2104  # 2104 = thermocouple 64, in the air just above the sand, in the center    # 1303   # A303 == Thermocouple 43

SAND_TOP_CHANNEL = 1303  # Thermocouple 43, channel 1303
SAND_MID_CHANNEL = 1302  # Thermocouple 42, channel 1302
SAND_BOT_CHANNEL = 1216  # Thermocouple 36, channel 1216


##########
# COM PORT GENERAL DEFAULT CONFIG
DEFAULT_SERIAL_PORT_RX_BUFFER_SIZE = 2000
DEFAULT_SERIAL_PORT_TX_BUFFER_SIZE = 2000
SERIAL_PORT_RETRY_TIMEOUT_SECS = 60

##########
# Communications retry timeouts
#
AGILENT_RETRY_TIMEOUT_SECS   = 1 * 60    # If the Agilent cannot be opened, how long to wait before retrying
MARQUEE_RETRY_TIMEOUT_SECS   = 1 * 60
COLLECTOR_RETRY_TIMEOUT_SECS = 8
# How many times we are willing to miss telemetry before trying to reopen the port
COLLECTOR_MISSING_TELEM_REOPEN_THRESHOLD = 2

##########
# COM ports for temperature sensors and Marquee display
#

# NOTE: Agilent and marquee serial port configs are in their respective classes
MARQUEE_COM_PORT     = 'COM3'
MARQUEE_BAUD_RATE    = 115200

# Make the buffer big enough to hold 15 minutes of readings, in case we only read every 10 minutes.  
# There are 30 readings per minute of 11 characters each (if there is a CR/LF after each)
TEMP_HUM_BAUD_RATE           = 115200
TEMP_HUM_RX_BUFFER_SIZE      = 15 * 30 * 11
OUTSIDE_TEMP_SENSOR_PORT     = 'COM7'  # Replace with your read serial port
DOME_TEMP_SENSOR_PORT        = 'COM39'
ELECTRONICS_TEMP_SENSOR_PORT = 'COM38'   # Temp of electronics box


##########
# Collector COM ports and serial port config info
#

COLLECTOR_BAUD_RATE      = 38400
COLLECTOR_RX_BUFFER_SIZE =  2000
COLLECTOR_TX_BUFFER_SIZE =  2000

COLLECTOR_PORTS = [
  ['1A', 'COM8'],
  ['1B', 'COM10'],
  ['1C', 'COM12'],
  ['2A', 'COM14'],
  ['2B', 'COM16'],
  ['2C', 'COM18'],
  ['3A', 'COM20'],
  ['3B', 'COM22'],
  ['3C', 'COM25'],
  ['4A', 'COM27'],
  ['4B', 'COM28'],
  ['4C', 'COM31'],
  ['5A', 'COM32'],
  ['5B', 'COM34'],
  ['5C', 'COM36'],
]

class CollectorNativeStates(IntEnum): 
  UNKNOWN                = -1
  OFF                    =  0
  HOME_ELEVATION_LOW     = auto()
  HOME_ELEVATION_HIGH    = auto()
  HOME_ELEVATION_ERROR   = auto()
  CHECK_LIMIT_CABLE      = auto()
  HOME_AZIMUTH_NEG       = auto()
  HOME_AZIMUTH_POS       = auto()
  HOME_UNSTICK           = auto()
  HOME_AZIMUTH_NEG_RETRY = auto()
  HOME_AZIMUTH_ERROR     = auto()
  HOME_COMPLETE          = auto()
  ACQ_BEGIN              = auto()
  ACQ_ELEVATION_WAIT     = auto()
  ACQ_AZ                 = auto()
  ACQ_ERROR              = auto()
  ACQUIRE                = auto()
  WAITING_FOR_SUN        = auto()
  TRACK                  = auto()
  CLOUD_PAUSE            = auto()
  STOW_AZ_HOME           = auto()
  STOW_EL_HOME           = auto()
  STOWING                = auto()
  STOWED                 = auto()
  STOW_ERROR             = auto()
  ERROR                  = auto()

class CollectorMarqueeStates(IntEnum):
  UNKNOWN      = 0
  OFF          = auto()
  HOMING       = auto()
  ACQUIRE      = auto()
  WAIT_FOR_SUN = auto()    
  TRACK        = auto()
  CLOUD_PAUSE  = auto()
  STOWING      = auto()
  STOWED       = auto()
  ERROR        = auto()

CollectorNativeStateToMarqueeState = {
  CollectorNativeStates.UNKNOWN                : CollectorMarqueeStates.UNKNOWN,
  CollectorNativeStates.OFF                    : CollectorMarqueeStates.OFF,
  CollectorNativeStates.HOME_ELEVATION_LOW     : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_ELEVATION_HIGH    : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_ELEVATION_ERROR   : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.CHECK_LIMIT_CABLE      : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.HOME_AZIMUTH_NEG       : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_AZIMUTH_POS       : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_UNSTICK           : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_AZIMUTH_NEG_RETRY : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_AZIMUTH_ERROR     : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.HOME_COMPLETE          : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.ACQ_BEGIN              : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_ELEVATION_WAIT     : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_AZ                 : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_ERROR              : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.ACQUIRE                : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.WAITING_FOR_SUN        : CollectorMarqueeStates.WAIT_FOR_SUN,
  CollectorNativeStates.TRACK                  : CollectorMarqueeStates.TRACK,
  CollectorNativeStates.CLOUD_PAUSE            : CollectorMarqueeStates.CLOUD_PAUSE,
  CollectorNativeStates.STOWING                : CollectorMarqueeStates.STOWING,
  CollectorNativeStates.STOW_AZ_HOME           : CollectorMarqueeStates.STOWING,
  CollectorNativeStates.STOW_EL_HOME           : CollectorMarqueeStates.STOWING,
  CollectorNativeStates.STOWED                 : CollectorMarqueeStates.STOWED,
  CollectorNativeStates.STOW_ERROR             : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.ERROR                  : CollectorMarqueeStates.ERROR,
}

COLLECTOR_LOG_MAXLINES = 200

#########
# Logging - daily folder is not in Nextcloud, to avoid constant thrashing
LOG_INTERVAL_SECONDS = 60
DAILY_FOLDER   = 'WindsorDailyLog'    # Will be placed under "My Documents"
ARCHIVE_FOLDER = 'Nextcloud/Engineering/Calseed Prototype/Data/DailyLogs'  # Logs get copied to here at midnight

# This will be the first line of every data file that is created.  We make it a string of double-quoted strings so that 
# Excel can read it in as strings.  Note the single-quotes around the whole shebang.
HEADER1        = '"Windsor Testbed","Version","1.0"'

# Site Info
SITE_LATITUDE  =   34.183941
SITE_LONGITUDE = -118.168791
SITE_ELEVATION =  331   # meters
SITE_TIMEZONE  = 'America/Los_Angeles'

# Must match value on realtime side for proper display
QUAD_CELL_HANDEDNESS = -1

###########
# NIP Sequencer
#

# Time parameters
NIP_TRACKER_POWER_ON_DELAY     =   3   # How many seconds wo wait after applying power before pressing the Power soft button
NIP_TRACKER_POWER_BUTTON_PRESS_TIME = 2
NIP_STATE_MACHINE_PERIOD       =  60   # How often we wake up and consider changing states
NIP_ACQUIRE_TIMEOUT            = 300  
NIP_DNI_WARNING_TIMEOUT        = 200

# Sunlight parameters
# What fraction of GHI do we need to be seeing in order to assert that the sun is out
NIP_GHI_SUN_IS_OUT_THRESHOLD =   0.45
NIP_GHI_SUN_IS_OUT_MIN       =  30
NIP_DNI_THRESHOLD            =  35    # in W/m^2
NIP_COVER_GLASS_SCALE_FACTOR = 1.19   # Why it's not 1.08 I don't understand



###########
# Collector Sequencer
#


COLLECTOR_STATE_MACHINE_PERIOD = 60

# How long to allow these operations to take
COLL_POWEROFF_TIMEOUT =   5
COLL_POWERON_TIMEOUT  =  30
COLL_UNSTICK_TIMEOUT  = 120


# Start and end times.  How many hours after sunrise to start each collector, and
# how many hours before sunset to shut it down.
COLLECTOR_START_AND_END_TIMES = {
  '1A': [ +2, -1.5 ],
  '1B': [ +2, -1.5 ],
  '1C': [ +2, -1 ],
  '2A': [ +1, -2 ],
  '2B': [ +2, -2 ],
  '2C': [ +2, -1 ],
  '3A': [ +1, -2 ],
  '3B': [ +2, -2 ],
  '3C': [ +2, -1 ],
  '4A': [ +1, -2 ],
  '4B': [ +2, -2 ],
  '4C': [ +2, -1 ],
  '5A': [ +1, -1 ],
  '5B': [ +1, -1 ],
  '5C': [ +1, -1 ],
}


###########
# Thinger.io Internet-of-Things cloud server login params
#

# Replace with your Thinger.io credentials
THINGER_IO_USERNAME    = "behines"
THINGER_IO_DEVICE_ID   = "Windsor"
THINGER_IO_DEVICE_CRED = "LV1xG3FoJ2vKluI@"
THINGER_IO_BUCKET_ID   = "Windsor_Data"
# This is the "Stanley" token under the device at Thinger.io
# THINGER_IO_AUTH_TOKEN  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkZXYiOiJXaW5kc29yIiwiaWF0IjoxNzM0MzI5NzIxLCJqdGkiOiI2NzVmYzU3OTNkMTU0YWI3N2QwM2E4OTQiLCJzdnIiOiJ1cy13ZXN0LmF3cy50aGluZ2VyLmlvIiwidXNyIjoiYmVoaW5lcyJ9.6j-CjLW5naJOGX0re9pbZkwNVCN9HNkzGlrOQlD1Kaw"
# This is the "Windsor_Primary" token under our top-level tokens
#THINGER_IO_AUTH_TOKEN  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJXaW5kc29yX1ByaW1hcnkiLCJzdnIiOiJ1cy13ZXN0LmF3cy50aGluZ2VyLmlvIiwidXNyIjoiYmVoaW5lcyJ9.GW5wKmYfYjJgVvfFfDCZ4fi19_NdvfxA5VqnSDCI--Y"

# This is the "Bearer" token assigned in the Callback pulldown menu for the Windsor device
THINGER_IO_BEARER_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJEZXZpY2VDYWxsYmFja19XaW5kc29yIiwic3ZyIjoidXMtd2VzdC5hd3MudGhpbmdlci5pbyIsInVzciI6ImJlaGluZXMifQ.1ZBsOMKvGqnh-8w2-0OWa6iGcim05X0bBAKQw33XRE8"