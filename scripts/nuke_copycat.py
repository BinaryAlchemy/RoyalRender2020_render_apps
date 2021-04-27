
import nuke
import sys


#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def writeInfo(msg):
    print(msg)

def writeDebug(msg):
    return
    print("DBG: " + msg)

def writeWarning(msg):
    print("WRN: " + msg)

def writeError(msg):
    print("ERR: " + msg)



if __name__ == "__main__":
    writeInfo("Nuke CopyCat. Royal Render version %rrVersion%." )
    srcFilename = sys.argv[1]  # scene path
    nodeName = sys.argv[2]  # copycat node name
    
    writeInfo("Opening script file...")
    nuke.scriptOpen(srcFilename)
    
    writeInfo("Starting CopyCat node " + nodeName + " ...")
    nuke.toNode(nodeName)['startTraining'].execute()
    writeInfo("Done ")
    
    