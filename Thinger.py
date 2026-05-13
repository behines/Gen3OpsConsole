#######################################################
# Thinger - interface to the Thinger Internet of Things service
#
# 
#



#################################################
# Modules used
#

import requests
import json
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
    self.ThingerURL = "https://backend.thinger.io/v3/users/" + THINGER_IO_USERNAME + "/devices/" + THINGER_IO_DEVICE_ID + "/callback/data"
    self.headers = {
      "Content-Type": "application/json;charset=UTF-8",
      "Authorization": PROJECT_CONFIG.ThingerBearerToken,
      "Accept": "application/json, text/plain, */*"
    }


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
      response = requests.post(self.ThingerURL, headers=self.headers, json=data)

      if response.status_code == 200:
        # print("Data sent to Thinger.io bucket:", data)
        pass
      else:
        print(f"Failed to send data. Status code: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
      print(f"Exception occurred while sending data to Thinger.io: {e}")
