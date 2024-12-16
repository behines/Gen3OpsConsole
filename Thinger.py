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
    self.ThingerURL = "https://api.thinger.io/v1/users/" + THINGER_IO_USERNAME + "/buckets/" + THINGER_IO_BUCKET_ID + "/data"
    self.headers = {
      "Authorization": THINGER_IO_AUTH_TOKEN,
      "Content-Type": "application/json"
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
        print("Data sent to Thinger.io bucket:", data)
      else:
        print(f"Failed to send data. Status code: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
      print(f"Exception occurred while sending data to Thinger.io: {e}")
      