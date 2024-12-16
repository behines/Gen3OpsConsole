#######################################################
# Thinger - interface to the Thinger Internet of Things service
#
# 
#



#################################################
# Modules used
#

from pything import ThingerClient
from ConfigInfo import *


##########################################################################################
##########################################################################################
##########################################################################################
# tThinger
#

class tThinger():

  ###############################################
  # Constructor and destructor
  # 
  # INPUTS:
  #     

  def __init__(self):
    # Initialize Thinger.io client
    self.thing = ThingerClient(THINGER_IO_USERNAME, THINGER_IO_DEVICE_ID, THINGER_IO_DEVICE_CRED)


  ###############################################
  # LogData
  # 
  # Logs Data to the cloud
  #     

  def LogData(self, DNI, GHI, BoxTemp, SandTopTemp, SandMidTemp, SandBotTemp, DomeTemp,  ElecTemp, StanleyTemp):
    data = {
      "DNI"         : DNI,
      "GHI"         : GHI,
      "BoxTemp"     : BoxTemp,
      "SandTopTemp" : SandTopTemp,
      "SandMidTemp" : SandMidTemp,
      "SandBotTemp" : SandBotTemp,
      "DomeTemp"    : DomeTemp,  
      "ElecTemp"    : ElecTemp,
      "StanleyTemp" : StanleyTemp  
    }

    try:
      self.thing.write_bucket(THINGER_IO_BUCKET_ID, data)
      print("Data sent to Thinger.io bucket:", data)

    except Exception as e:
      print("Error sending data to Thinger.io bucket:", e)