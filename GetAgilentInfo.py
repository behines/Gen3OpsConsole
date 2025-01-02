# Short program to query an Agilent unit for its configuration.
# Usage: 
#   python GetAgilentInfo.py 5
#  will report on the unit on COM5

import pyvisa
import argparse

BAUD_RATE    = 9600        # I had it much higher, but I was getting input buffer overruns, even with RTS/CTS configured.  This fixed it, and is plenty fast for us.
DATA_BITS    = 8
PARITY       = pyvisa.constants.Parity.none 
STOP_BITS    = pyvisa.constants.StopBits.one
FLOW_CONTROL = pyvisa.constants.ControlFlow.rts_cts


def main():
  # Create the argument parser
  parser = argparse.ArgumentParser(description="Read device info from a serial port.")
  
  # Add a port argument
  parser.add_argument("port", type=int, help="The serial port number to connect to (e.g., 5 for COM5")
  
  # Parse the arguments
  args = parser.parse_args()
  
  # Access the port argument
  port = args.port
  
  instr_string = f"ASRL{port}::INSTR"

  # Your logic here
  print(f"Connecting to Agilent on: {instr_string}")
  
  rm=pyvisa.ResourceManager('@py')
  dev=rm.open_resource(instr_string)
  dev.baud_rate=9600
  dev.data_bits=8
  dev.parity=pyvisa.constants.Parity.none
  dev.stop_bits=pyvisa.constants.StopBits.one
  dev.flow_control=pyvisa.constants.ControlFlow.rts_cts
 
  print(' ')
  print(dev.query('*IDN?'), end='')

  print('Card 1: ', dev.query('SYST:CTYPE? 100'), end='')
  print('Card 2: ', dev.query('SYST:CTYPE? 200'), end='')
  print('Card 3: ', dev.query('SYST:CTYPE? 300'), end='')


if __name__ == "__main__":
  main()