import sys

print("Get the full job class from the rrServer...")
#  This can be used if the variables available for the commandline are not sufficient
#  (See rrHelp Section Customization/ Render Applications/ Render config files/Commandlines )
#  Using commandline variables is a bit faster than requesting the job from the rrServer


#  AuthStr is required in case anonymous does not have the right to delete jobs.
#  Or if you have enabled "Authorization is required for all connections"
#  AuthStr will not work via a router/remote connection





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
