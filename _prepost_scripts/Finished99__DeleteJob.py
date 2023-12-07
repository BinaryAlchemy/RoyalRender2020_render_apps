import sys


print("Deleting this job from the RR queue")

modPath=rrGlobal.rrModPyrrPath()

sys.path.append(modPath)
print("added module path "+modPath)
import libpyRR39 as rr


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-jid")
parser.add_argument("-authStr")
args = parser.parse_args()


print("Set up server and login info")
tcp = rr._rrTCP("")
tcp.setServer(rrGlobal.rrServer(), 7773)
tcp.setLogin(args.authStr, "")


print("Sending Job Command")
jobsApply=[]
jobsApply.append(int(args.jid))
if not tcp.jobSendCommand(jobsApply,rrJob._LogMessage.lDelete,0):
    print("Error jobSendCommand: " + tcp.errorMessage())


print("done")
