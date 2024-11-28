#######################################################
# tLogFile - Used for writing CSV files and managing daily archiving
#
#



#################################################

# Modules used
#

import sys
import os
from datetime import datetime
import shutil
import pytz
from   PySide6.QtCore import QDateTime

##########################################################################################
##########################################################################################
##########################################################################################
# tMarquee 
#
# 
#

class tLogFile:

  #################################################
  #
  # Constructor
  #

  def __init__(self, DailyFolder, ArchiveFolder, Header1, Header2, SITE_TIMEZONE):
    self.DailyFolder   = DailyFolder
    self.ArchiveFolder = ArchiveFolder
    self.Header1       = Header1
    self.Header2       = Header2

    self.SiteTimezone = pytz.timezone(SITE_TIMEZONE)

    # Create the directory structure if it doesn't exist
    os.makedirs(DailyFolder, exist_ok=True)
    os.makedirs(ArchiveFolder, exist_ok=True)

    self.StartNewFile()



  #################################################
  # StartNewFile - 
  #

  def StartNewFile(self):
    now = datetime.now(self.SiteTimezone)
    self.todays_day_of_month = now.day

    datestr = now.strftime("%Y%m%d")
    short_filename = 'Windsor' + datestr + '.csv'
    self.LogFileName = os.path.join(self.DailyFolder, short_filename)

    # Move all log files that aren't for today from the Daily folder to the archive folder
    for filename in os.listdir(self.DailyFolder):
       
      if filename == short_filename:
        continue  # Leave today's file be, don't move it yet
      
      if filename.endswith(".csv"):
        # Construct the source and destination file paths
        source_file = os.path.join(self.DailyFolder, filename)
        destination_file = os.path.join(self.ArchiveFolder, filename)

        # Move the file to the destination folder
        shutil.move(source_file, destination_file)

    # If the file does not exist yet, write the header
    if not os.path.exists(self.LogFileName):
      with open(self.LogFileName, "a", newline="") as file:
        file.write(self.Header1 + '\n')
        file.write(self.Header2 + '\n')



  #################################################
  # CreateMetadataFile - Creates a file that describes the data in the associated 
  # 
  #

  def CreateMetadataFile(self):
    # Version
    # Column titles
    # Units
    # Date
    pass



  #################################################
  # LogRecord - log a data record
  # 
  # timestamp - the datetime of the record
  # OutputDataLine - the comma-separated data string from the Agilent(s)
  #
  # RETURNS:
  #   True if this is the start of a new day, false otherwise

  def LogRecord(self, timestamp: QDateTime, OutputDataLine):
    #date = timestamp.strftime("%m/%d/%Y")
    #currTime = timestamp.strftime("%H:%M:%S")

    # Parse for the day
    date     = timestamp.toString("MM/dd/yyyy")
    # Parse for the time
    currTime = timestamp.toString("HH:mm:ss")

    # Decide if we need to start a new file
    if self.todays_day_of_month != timestamp.date().day():    # timestamp.day:
      self.StartNewFile()
      return True

    # Create a tuple or list for the row.  The * causes the list to be unpacked into its elements for inclusion in the final list
    #line = str(date) + ","+  str(currTime) + "," + OutputDataLine
    line = date + ","+  currTime + "," + OutputDataLine

    # Open csv file and write the row.  The "newline" bit prevents extra newline characters from being inserted on Windows systems.
    with open(self.LogFileName, "a", newline="") as file:
      file.write(line + '\n')

    return False
  