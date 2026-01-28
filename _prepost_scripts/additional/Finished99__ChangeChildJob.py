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
import libpyRR39 as rr


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-jid")
parser.add_argument("-authStr")
parser.add_argument("-child")
args = parser.parse_args()


#print("Set up server and login info")
tcp = rr._rrTCP("")
tcp.setServer(rrGlobal.rrServer(), 7773)

#We must NOT use setLogin with the AuthStr of our job as we want to change multiple jobs. 
#You do not need setLogin if you have not enabled "Require Authorization" in rrConfig.
#tcp.setLogin(args.authStr, "")




#Get child job
#Limitations: 
#   This variable is set at submission time. It it currently not updated if you change dependencies after submission
#   It contains one child job only! (And not all jobs that are waiting for this job)
#
#   (Info: If you need all jobs that are waiting, then you should set some CustomIDString for all jobs at submision. 
#   And then use a filter in this script to get all jobs with this CustomIDString) 


#transfer job data from rrServer into our python module class tcp.jobs
if not tcp.jobList_GetInfo(int (args.child)):
  print("Error jobList_GetInfo: " + tcp.errorMessage())
  sys.exit()
  
#access the local data
childJob= tcp.jobs.getJobInfo(int (args.child))
print(childJob.IDstr() + " Scene Name: " + childJob.sceneName)



#do some stuff with the child job
# .
# .
# .
# .





#Optional: If you submit the child job in state "disabled", then you may enable it here.
#This ensures that no child job without the change we just did starts to render.
#Example case for such an issue: If the parent job never finished due to errors and was then deleted by someone, 
# then the child job starts as there is no job to wait for any more.
#Disadvantage of this "security feature" is the user feedback: e.g. Users in rrControl may filter for disabled jobs and enable them because they should render.

if (False):
    print("Sending Job Command")
    jobsApply=[]
    jobsApply.append(int(args.child))
    if not tcp.jobSendCommand(jobsApply,rrJob._LogMessage.lEnable,0):
        print("Error jobSendCommand: " + tcp.errorMessage())



#print "done"
