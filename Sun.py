#######################################################
# Sun - predicted sunrise, sunset, GHI
#
#


#################################################

# Modules used
#

from datetime import datetime
from astral import LocationInfo
from astral.sun import sun, elevation
import pytz
import math


##########################################################################################
##########################################################################################
##########################################################################################
# tSun 
#
# 
#

class tSun:

  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self, latitude, longitude, elevation, timezone):
    self.Location  = LocationInfo(latitude=latitude, longitude=longitude, timezone=timezone)
    self.Location.observer.elevation = elevation
    self.timezone  = pytz.timezone(timezone)



  #################################################
  # GetValues
  #
  # For i

  def GetValues(self):
    local_date = datetime.now(self.timezone)
    # Use standard time date so the day-change trigger fires at standard-time midnight,
    # not DST midnight (which is 1 hour early during summer).
    dst = local_date.dst()
    if dst:
      local_date = local_date - dst
    s = sun(self.Location.observer, date=local_date)

    sunrise = s['sunrise'].astimezone(self.timezone)
    sunset  = s['sunset' ].astimezone(self.timezone)


    # Calculate solar elevation
    sun_elevation = elevation(self.Location.observer, local_date)

    # Assume maximum GHI under clear skies
    GHI_max = 1000  # in W/m²

    # Estimate GHI
    GHI_clear_sky = GHI_max * math.sin(math.radians(sun_elevation))

    return [sunrise,sunset,GHI_clear_sky]
  