
import socket
import argparse
import sys
parser = argparse.ArgumentParser()
parser.add_argument("-trackerPort", type=int)
parser.add_argument("-webPort", type=int)
parser.add_argument("-childRRJob", type=int)
parser.add_argument("-JobCommandPWHash", type=int)
parser.add_argument("-HoudiniModPath")
args = parser.parse_args()


webPort=9000
if (args.webPort!= None):
    webPort=args.webPort
trackerPort=8000
if (args.trackerPort!= None):
    trackerPort=args.trackerPort


print("RR: ...\n")

hostname = socket.gethostname()
trackerIP = socket.gethostbyname(hostname)
#this might not work for Linux if  hostname in /etc/hosts as 127.0.0.1
#https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib

if (args.HoudiniModPath!= None):
    print("RR: adding Python module path: "+args.HoudiniModPath)
    sys.path.append(args.HoudiniModPath)


print("RR: Updating child job ({}) with my IP and tell it to ignore wait state\n".format(args.childRRJob))
from rr_python_utils.load_rrlib import rrLib  
import rr_python_utils.connection as rr_connect
import rrJob

tcp = rr_connect.server_connect()

if (args.JobCommandPWHash != None):
    tcp.setLogin_JobCommandPWHash(args.JobCommandPWHash)


jobsApply=[]
jobsApply.append(int(args.childRRJob))

if not tcp.jobSetCustomVariables(jobsApply, " CustomSlicerClient=" + trackerIP):
    print("Error jobSetCustomVariables: " + tcp.errorMessage())
    exit(1)


if not tcp.jobSendCommand(jobsApply, rrJob._LogMessage.lIgnoreWaitFor, 0):
    print("Error jobSendCommand: " + tcp.errorMessage())
    exit(1)


import simtracker

print("RR: Starting Simulation Tracker on port {}\n\n".format(trackerPort))
print("Connect your browser to http://{}:{}/ to get information about the tracker state.\n".format(trackerIP, webPort))
print("This is useful to debug and see if machines are checking in and are synchronized.\n\n")

simtracker.setVerbosity(True)

sys.stdout.flush()
simtracker.serve(int(trackerPort), int(webPort))

print("RR: Done\n")


