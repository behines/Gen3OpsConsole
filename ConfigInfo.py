#################################################
#
# CONFIGURATION 
#
# 

import sys

from collections import namedtuple
from enum        import IntEnum, auto

from ProjectConfig import AGILENT_DESCRIPTOR_FIELDS, CollectorMapping, PICOTOOL_PATH, tProjectConfig

#################################################
#
# CONFIGURATION SOURCE OF TRUTH
#
# Project configuration should store facts, not duplicate conclusions.
# Hardware lists, ports, channel groups, and credentials are the source of
# truth.  The bHas... values on tProjectConfig are derived properties computed
# from those facts so call sites can stay readable without creating a second
# manually-maintained copy of the same information.
#
# Use [] for an absent multi-device list.  Examples:
#   Agilents       = []
#   CollectorPorts = []
#
# Use None for an absent single device, single channel group, or credential.
# Examples:
#   MarqueePort               = None
#   OutsideTempSensorPort     = None
#   UsbHubPowerChannel        = None
#   ThingerBearerToken        = None
#
# If a site later gains a capability, fill in the underlying list, port,
# channel, or credential field.  Do not edit the derived properties.
#

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

#################################################
#
# Compatibility globals
#
# These names are maintained for older modules that still import flat
# configuration values from ConfigInfo.  The site-specific source of truth now
# lives in WindsorConfig.py and SandiaConfig.py.  SetActiveProject() overwrites
# these globals from PROJECT_CONFIG after parsing --site.
#

AGILENTS                  = []
AGILENT_WITH_POWER_RELAYS = None


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
MARQUEE_BAUD_RATE    = 115200

# Make the buffer big enough to hold 15 minutes of readings, in case we only read every 10 minutes.  
# There are 30 readings per minute of 11 characters each (if there is a CR/LF after each)
TEMP_HUM_BAUD_RATE           = 115200
TEMP_HUM_RX_BUFFER_SIZE      = 15 * 30 * 11


##########
# Collector COM ports and serial port config info
#

COLLECTOR_BAUD_RATE      = 38400
COLLECTOR_RX_BUFFER_SIZE =  2000
COLLECTOR_TX_BUFFER_SIZE =  2000

COLLECTOR_PORTS = []

# Mirror of the embedded TRACKER_STATE enum in Gen3_Tracker/TrackerStates.h.
# Names match the C++ identifiers exactly (minus the TRACKER_ prefix) and
# integer values are explicit so any future firmware drift is obvious on
# review.  UNKNOWN = -1 is a Python-side sentinel for "no telemetry yet".
class CollectorNativeStates(IntEnum):
  UNKNOWN                    = -1
  OFF                        =  0   # TRACKER_OFF
  HOME_OFFSET                =  1   # TRACKER_HOME_OFFSET
  HOME_AZ_NEG                =  2   # TRACKER_HOME_AZ_NEG
  HOME_AZ_ERROR              =  3   # TRACKER_HOME_AZ_ERROR
  HOME_ELEVATION_LOW         =  4   # TRACKER_HOME_ELEVATION_LOW
  HOME_ELEVATION_ERROR       =  5   # TRACKER_HOME_ELEVATION_ERROR
  HOME_COMPLETE              =  6   # TRACKER_HOME_COMPLETE
  ACQ_BEGIN                  =  7   # TRACKER_ACQ_BEGIN
  ACQ_INITIAL_POSITION_WAIT  =  8   # TRACKER_ACQ_INITIAL_POSITION_WAIT
  ACQ_AZ                     =  9   # TRACKER_ACQ_AZ
  ACQ_ERROR                  = 10   # TRACKER_ACQ_ERROR
  ACQUIRE                    = 11   # TRACKER_ACQUIRE
  WAITING_FOR_SUN            = 12   # TRACKER_WAITING_FOR_SUN
  TRACK                      = 13   # TRACKER_TRACK
  DEAD_RECKON                = 14   # TRACKER_DEAD_RECKON
  CLOUD_PAUSE                = 15   # TRACKER_CLOUD_PAUSE
  STOWING                    = 16   # TRACKER_STOWING
  STOWED                     = 17   # TRACKER_STOWED
  STOW_ERROR                 = 18   # TRACKER_STOW_ERROR
  FLATTING                   = 19   # TRACKER_FLATTING
  FLAT                       = 20   # TRACKER_FLAT
  FLAT_ERROR                 = 21   # TRACKER_FLAT_ERROR
  ERROR                      = 22   # TRACKER_ERROR

class CollectorMarqueeStates(IntEnum):
  UNKNOWN      = 0
  OFF          = auto()
  HOMING       = auto()
  HOMED        = auto()
  ACQUIRE      = auto()
  WAIT_FOR_SUN = auto()    
  TRACK        = auto()
  DEAD_RECKON  = auto()
  CLOUD_PAUSE  = auto()
  STOWING      = auto()
  STOWED       = auto()
  ERROR        = auto()

CollectorNativeStateToMarqueeState = {
  CollectorNativeStates.UNKNOWN                    : CollectorMarqueeStates.UNKNOWN,
  CollectorNativeStates.OFF                        : CollectorMarqueeStates.OFF,
  CollectorNativeStates.HOME_OFFSET                : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_AZ_NEG                : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_AZ_ERROR              : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.HOME_ELEVATION_LOW         : CollectorMarqueeStates.HOMING,
  CollectorNativeStates.HOME_ELEVATION_ERROR       : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.HOME_COMPLETE              : CollectorMarqueeStates.HOMED,
  CollectorNativeStates.ACQ_BEGIN                  : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_INITIAL_POSITION_WAIT  : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_AZ                     : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.ACQ_ERROR                  : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.ACQUIRE                    : CollectorMarqueeStates.ACQUIRE,
  CollectorNativeStates.WAITING_FOR_SUN            : CollectorMarqueeStates.WAIT_FOR_SUN,
  CollectorNativeStates.TRACK                      : CollectorMarqueeStates.TRACK,
  CollectorNativeStates.DEAD_RECKON                : CollectorMarqueeStates.DEAD_RECKON,
  CollectorNativeStates.CLOUD_PAUSE                : CollectorMarqueeStates.CLOUD_PAUSE,
  CollectorNativeStates.STOWING                    : CollectorMarqueeStates.STOWING,
  CollectorNativeStates.STOWED                     : CollectorMarqueeStates.STOWED,
  CollectorNativeStates.STOW_ERROR                 : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.FLATTING                   : CollectorMarqueeStates.STOWING,
  CollectorNativeStates.FLAT                       : CollectorMarqueeStates.STOWED,
  CollectorNativeStates.FLAT_ERROR                 : CollectorMarqueeStates.ERROR,
  CollectorNativeStates.ERROR                      : CollectorMarqueeStates.ERROR,
}

COLLECTOR_LOG_MAXLINES = 200

#########
# Logging - daily folder is not in Nextcloud, to avoid constant thrashing
LOG_INTERVAL_SECONDS = 60
DAILY_FOLDER   = None
ARCHIVE_FOLDER = None

# This will be the first line of every data file that is created.  The active
# project supplies a string of double-quoted fields so Excel can read it as
# strings.
HEADER1        = None

# Site Info
SITE_LATITUDE  = None
SITE_LONGITUDE = None
SITE_ELEVATION = None
SITE_TIMEZONE  = None

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
COLLECTOR_START_AFTER_SUNRISE_MINUTES = 30
COLLECTOR_STOP_BEFORE_SUNSET_MINUTES  = 30
USE_DNI_TO_START_DAY                  = True

# How long to allow these operations to take
COLL_POWEROFF_TIMEOUT =   5
COLL_POWERON_TIMEOUT  =  30
COLL_UNSTICK_TIMEOUT  = 120


COLLECTOR_START_AND_END_TIMES = {}


###########
# Thinger.io Internet-of-Things cloud server compatibility values
#
# The source of truth for cloud logging identity and credentials is the active
# tProjectConfig.  These globals exist only for older call sites.
#

THINGER_IO_USERNAME     = None
THINGER_IO_DEVICE_ID    = None
THINGER_IO_BUCKET_ID    = None
THINGER_IO_BEARER_TOKEN = None


from WindsorConfig import WINDSOR_CONFIG
from SandiaConfig  import SANDIA_CONFIG

PROJECT_CONFIGS = {
  "windsor": WINDSOR_CONFIG,
  "sandia" : SANDIA_CONFIG,
}


def _ProjectNameFromCommandLine():
  for i, arg in enumerate(sys.argv):
    if arg == "--site" and i + 1 < len(sys.argv):
      return sys.argv[i + 1].lower()
    if arg.startswith("--site="):
      return arg.split("=", 1)[1].lower()
  return "windsor"


def SetActiveProject(ProjectName):
  global PROJECT_CONFIG, AGILENTS, COLLECTOR_PORTS
  global AGILENT_WITH_POWER_RELAYS
  global DAILY_FOLDER, ARCHIVE_FOLDER, HEADER1
  global SITE_LATITUDE, SITE_LONGITUDE, SITE_ELEVATION, SITE_TIMEZONE
  global COLLECTOR_START_AFTER_SUNRISE_MINUTES, COLLECTOR_STOP_BEFORE_SUNSET_MINUTES
  global USE_DNI_TO_START_DAY, THINGER_IO_USERNAME, THINGER_IO_DEVICE_ID, THINGER_IO_BUCKET_ID, THINGER_IO_BEARER_TOKEN

  if ProjectName not in PROJECT_CONFIGS:
    raise ValueError(f"Unknown site '{ProjectName}'. Expected one of: {', '.join(PROJECT_CONFIGS.keys())}")

  PROJECT_CONFIG = PROJECT_CONFIGS[ProjectName]

  AGILENTS       = PROJECT_CONFIG.Agilents
  COLLECTOR_PORTS = PROJECT_CONFIG.CollectorPorts
  AGILENT_WITH_POWER_RELAYS = PROJECT_CONFIG.PowerRelayAgilentIndex

  DAILY_FOLDER   = PROJECT_CONFIG.LogFolder
  ARCHIVE_FOLDER = PROJECT_CONFIG.ArchiveFolder
  HEADER1        = PROJECT_CONFIG.HeaderIdentity

  SITE_LATITUDE  = PROJECT_CONFIG.Latitude
  SITE_LONGITUDE = PROJECT_CONFIG.Longitude
  SITE_ELEVATION = PROJECT_CONFIG.Elevation
  SITE_TIMEZONE  = PROJECT_CONFIG.Timezone

  COLLECTOR_START_AFTER_SUNRISE_MINUTES = PROJECT_CONFIG.CollectorStartAfterSunriseMinutes
  COLLECTOR_STOP_BEFORE_SUNSET_MINUTES  = PROJECT_CONFIG.CollectorStopBeforeSunsetMinutes
  USE_DNI_TO_START_DAY                  = PROJECT_CONFIG.bUseDniToStartDay

  THINGER_IO_USERNAME = PROJECT_CONFIG.ThingerUserName
  THINGER_IO_DEVICE_ID = PROJECT_CONFIG.ThingerDeviceId
  THINGER_IO_BUCKET_ID = PROJECT_CONFIG.ThingerBucketId
  THINGER_IO_BEARER_TOKEN = PROJECT_CONFIG.ThingerBearerToken


SetActiveProject(_ProjectNameFromCommandLine())
