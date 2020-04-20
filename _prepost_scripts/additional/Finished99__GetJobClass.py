import sys

print "Get the full job class from the rrServer..."

modPath= rrGlobal.rrModPyrrPath()
sys.path.append(modPath)
#print("Added module path "+modPath)
import libpyRR2 as rr


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-jid")
parser.add_argument("-authStr")
args = parser.parse_args()


#print("Set up server and login info")
tcp = rr._rrTCP("")
tcp.setServer(rrGlobal.rrServer(), 7773)
tcp.setLogin(args.authStr, "")

if not tcp.jobList_GetSend(int (args.jid)):
  print("Error jobList_GetSend: " + tcp.errorMessage())
  sys.exit()
  
jobData= tcp.jobs.getJobSend(int (args.jid))
print("Scene Name: " + jobData.sceneName)


#print "done"
