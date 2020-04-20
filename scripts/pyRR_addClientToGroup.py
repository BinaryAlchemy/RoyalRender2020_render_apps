#
# This script adds or removes a client from a client group.
#

def findRR_Root():
    # findRR_Root adds the RR path as search path for the module
    # This function will only work if RR was installed on the machine
    # If you are using it from an external machine, you have to add the path to the rrPy module yourself
    # sys.path.append(MyModulePath)
    import os
    import platform
    import sys
    import struct
    if (not os.environ.has_key('RR_ROOT')):
        return
    modPath=os.environ['RR_ROOT']
    is64bit=(struct.calcsize("P") == 8)
    if (sys.platform.lower() == "win32") :
        if (is64bit):
            modPath=modPath + '/bin/win64'
        else:
            modPath=modPath + '/bin/win'
        modPath=modPath.replace("\\","/")
    elif (sys.platform.lower() == "darwin"):
        if (is64bit):
            modPath=modPath + '/bin/mac64/lib/python/27'
        else:
            modPath=modPath + '/bin/mac/lib/python/27'
    else:
        modPath=modPath + '/bin/lx64/lib'
    #modPath=modPath.replace("_debug","_release")
    sys.path.append(modPath)
    print("added module path "+modPath)
    

findRR_Root()
import libpyRR2 as rrLib
import libpyRR2_datafiles as rrData
import sys
import platform
import argparse
#print("Module version: "+rrData.getRRModuleVersion())



flagAddClient=False
parser = argparse.ArgumentParser()
parser.add_argument("-group")
parser.add_argument("-addClient")
args = parser.parse_args()
if ((args.group== None) or (len(str(args.group))<=0)):
    print("ERROR: No group name specified")
    sys.exit()
if ((args.addClient== None) or (len(str(args.addClient))<=0)):
    print("ERROR: No group add flag specified")
    sys.exit()
    
if (args.addClient=="1" or args.addClient.lower()=="true"):
    args.addClient=True
else:
    args.addClient=False
    


groupCfgFilename=rrData.getRRFolder_cfgUser()
if (len(groupCfgFilename)==0):
    print("ERROR: RR folder not found.")
    sys.exit()
groupCfgFilename=groupCfgFilename+"clientgroups.ini"
#print("RR group cfg file: "+groupCfgFilename)




groupList=rrData._ClientGroupList()
retSuccess= groupList.loadFromFile(groupCfgFilename)
if not retSuccess:
    print("ERROR: Unable to load file '"+groupCfgFilename+"'. "+groupList.getError())
    sys.exit()


foundID= -1
print("Group list loaded ("+str(groupList.count)+" groups)")
for gi in range (groupList.count):
    grp= groupList.clientGroup(gi)
    if (grp.getName().lower()==args.group.lower()):
        foundID=gi


group= rrData._ClientGroup()
if (foundID>=0):
    #print("Found group '"+args.group+"' at index "+str(foundID))
    group= groupList.clientGroup(foundID)
elif (groupList.count < groupList.clientGroupsMax()):
    #print("Create new group '"+args.group+"'")
    group= rrData._ClientGroup()
    group.setName(args.group)
    foundID=groupList.count
    groupList.count= groupList.count + 1
else:
    print("ERROR: Group '"+args.group+"' not found and group limit reached.")
    sys.exit()


machineName= platform.node()
if (args.addClient):
    print("Adding  '"+machineName+"' to group '"+args.group+"'.")
    group.addClient(machineName)
else:
    print("Removing  '"+machineName+"' from group '"+args.group+"'.")
    group.removeClient(machineName)
     


groupList.clientGroupSet(foundID,group)
retSuccess= groupList.saveToFile(groupCfgFilename)
if not retSuccess:
    print("ERROR: Unable to save file '"+groupCfgFilename+"'. "+groupList.getError())
    sys.exit()

print("Group file was saved.")    
               





print("\n\n--- DONE ---\n\n")
