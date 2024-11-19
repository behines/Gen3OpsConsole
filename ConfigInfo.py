#################################################
#
# CONFIGURATION 
#
# 

from collections import namedtuple

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

# Elements of the AGILENTS array have 7 members.  The DESCRIPTOR_FIELDS tell what each of those 7 entries are
AGILENT_DESCRIPTOR_FIELDS = [ 'Port','Channel list','Thermocouple channels','GHI channels','DNI channels','DNI gain','Front panel channel' ]
AGILENTS = [  [ 'ASRL5::INSTR',              # Port
                '101:120,201:220,301:320',   # Full scan channel list
                '101:120,201:220,301:320',   # Thermocouple channel list
                None,                        # GHI channel
                None,                        # DNI Channel
                8.23,                        # NIP Gain in uV per W/m^2
                303                          # Channel to display on front panel
              ],
              [ 'ASRL7::INSTR',              # Port
                '101:120,201:220',           # Full scan channel list
                '101:120,201:220',           # Thermocouple channel list
                None,                        # GHI channel
                None,                        # DNI Channel
                8.23,                        # NIP Gain in uV per W/m^2
                101                          # Channel to display on front panel
              ],
              [ 'ASRL9::INSTR',              # Port
                '119:120',                   # Full scan channel list
                None,                        # Thermocouple channel list
                120,                         # GHI channel
                119,                         # DNI Channel
                8.23,                        # NIP Gain in uV per W/m^2
                119                          # Channel to display on front panel  105 == NIP channel
              ]
           ]

AGILENT_WITH_POWER_RELAYS = 2     # The third Agilent (counting starts at zero)
NIP_POWER_CHANNELS        = '202:203'
NIP_ON_OFF_BUTTON_CHANNEL = '201'
PYRANOMETER_POWER_CHANNEL = '204'
MOTOR_POWER_CHANNELS      = '218:220'
USB_HUB_POWER_CHANNEL     = '216'
AGILENT_RETRY_TIMEOUT_MIN = 1     # If the Agilent cannot be opened, how long to wait before retrying

##########
# Shutters have a name and an Agilent channel
#

ShutterMapping = namedtuple('ShutterInfo', ['Name', 'Channel'])
SHUTTERS = [
  ShutterMapping('1A', '206'),
  ShutterMapping('1B', '207'),
  ShutterMapping('2A', '208'),
  ShutterMapping('2B', '209'),
  ShutterMapping('3A', '210'),
  ShutterMapping('3B', '211'),
  ShutterMapping('4A', '212'),
  ShutterMapping('4B', '213'),
  ShutterMapping('5A', '214'),
  ShutterMapping('5B', '215'),
]

# The channel number here is 1000*mainframe number + channel number.  So 1303 is channel 303 from 
# the first unit in the list above.
BOX_CHANNEL_FOR_MARQUEE_DISPLAY = 2104  # 2104 = thermocouple 64, in the air just above the sand, in the center    # 1303   # A303 == Thermocouple 43


##########
# COM PORT GENERAL DEFAULT CONFIG
DEFAULT_SERIAL_PORT_RX_BUFFER_SIZE = 2000
DEFAULT_SERIAL_PORT_TX_BUFFER_SIZE = 2000
SERIAL_PORT_RETRY_TIMEOUT_SECS = 60

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
OUTSIDE_TEMP_SENSOR_PORT     = 'COM6'  # Replace with your read serial port
DOME_TEMP_SENSOR_PORT        = 'COM8'
ELECTRONICS_TEMP_SENSOR_PORT = 'COM100'   # Temp of electronics box


##########
# Collector COM ports and serial port config info
#

COLLECTOR_BAUD_RATE      = 38400
COLLECTOR_RX_BUFFER_SIZE =  2000
COLLECTOR_TX_BUFFER_SIZE =  2000

COLLECTOR_PORTS = [
  ['1A', 'COM87'],
  ['1B', 'COM98'],
  ['1C', 'COM95'],
  ['2A', 'COM97'],
  ['2B', 'COM85'],
  ['2C', 'COM89'],
  ['3A', 'COM91'],
  ['3B', 'COM92'],
  ['3C', 'COM64'],
  ['4A', 'COM81'],
  ['4B', 'COM71'],
  ['4C', 'COM66'],
  ['5A', 'COM68'],
  ['5B', 'COM60'],
  ['5C', 'COM62'],
]

#########
# Logging - daily folder is not in Nextcloud, to avoid constant thrashing
LOG_INTERVAL_SECONDS = 5
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