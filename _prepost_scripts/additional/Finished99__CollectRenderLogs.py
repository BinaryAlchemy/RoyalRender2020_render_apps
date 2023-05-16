### This example post-script gets the job class from the rrServer
### It then loads all render log files of the job
### In the end it updates the user info of the job with some stats


import sys
import os
import traceback

modPath= rrGlobal.rrModPyrrPath()
#modPath="e:/programmierung/RoyalRenderGit_90/project/_debug/bin/win64"
sys.path.append(modPath)
#print("Added module path "+modPath)

if (sys.version_info.major == 2):
    import libpyRR2 as rrLib
elif (sys.version_info.major == 3):
    if (sys.version_info.minor == 7):
        import libpyRR37 as rrLib
    elif (sys.version_info.minor == 9):
        import libpyRR39 as rrLib


jobData_BaseFolder= rrGlobal.rootPath() + "rrJobdata/"
print("jobData_BaseFolder " + jobData_BaseFolder)


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-jid")
parser.add_argument("-authStr")
args = parser.parse_args()
print("jid is " + str(args.jid))


#print("Set up server and login info")
tcp = rrLib._rrTCP("")
tcp.setServer(rrGlobal.rrServer(), 7773)

### AuthStr is required in case anonymous does not have the right to delete jobs.
### Or if you have enabled "Authorization is required for all connections"
### AuthStr will not work via a remote connection
### It uses the rights of the preset user RR Script.
### The login works for commands of this job only

#if ((args.authStr!=None) and (len(args.authStr)>0)):
#    tcp.setLogin(args.authStr, "")



##  This can be used if the variables available for the commandline are not sufficient
##  (See rrHelp Section Customization/ Render Applications/ Render config files/Commandlines )
##  Note: Using commandline variables is a bit faster than requesting the job from the rrServer
print("Get the job class from the rrServer...")
if not tcp.jobList_GetInfo(int (args.jid)):
  print("Error jobList_GetInfo: " + tcp.errorMessage())
  sys.exit()
  
  
  
job= tcp.jobs.getJobInfo(int (args.jid))
print("Scene Name: " + job.sceneName)
jobData_JobLogFolder= jobData_BaseFolder + job.jobFilesFolderName + "/log/"

##get all render log files
import os
for file in os.listdir(jobData_JobLogFolder):
    if not file.endswith(".txt"):
        #should not happen
        continue
    
    ignoreFilesL=[] #create list
    ignoreFilesL.append("--.txt") # job reset info
    ignoreFilesL.append("_R.txt") # Currently Rendering or machine power off while rendering
    ignoreFilesL.append("_C.txt") # Crashed
    ignoreFilesL.append("_A.txt") # Aborted
    ignoreFilesL.append("_E.txt") # Pre-Script
    ignoreFilesL.append("_V.txt") # After Preview-Script
    ignoreFilesL.append("_P.txt") # Post-Script
    ignoreFilesL.append("_F.txt") # Finished Script
    
    #endswith() does not take lists. And tuples do not have an append() function.
    ignoreFiles=tuple(ignoreFilesL)
  
    if file.endswith(ignoreFiles):
        print("--- ignoring " + file)
        continue
    print("--- OPENING " + file)
    try:
        fd = open(os.path.join(jobData_JobLogFolder, file),'r')
        lines = fd.readlines()
        fd.close() 
        for line in lines:
            line=line.replace("\r","")
            line=line.replace("\n","")
            if ("Frame Wall Clock Time" in line):
                print("   |"+line)
            elif ("Update Wall Clock Time" in line):
                print("   |"+line)
            elif ("Peak Memory Usage" in line):
                print("   |"+line)
            elif ("Rendering frame" in line):
                print("   |"+line)
            pass
    except:
       print("ERROR processing file! " + file) 
       print(str(traceback.format_exc()))
        


#Create information for the user in rrControl:
infoLines=""

infoLines= infoLines + "Frame Time: {} sec\n".format(job.infoAverageFrameTime_FramesReturned)

try:
    infoLines= infoLines + "Frame Time: {} kPS*sec\n".format(job.infoAverageFrameTime_FramesReturned_PS/1000)
except:
    #RR 9.0.04 and older
    infoLines= infoLines + "Frame Time: {} kPS*sec\n".format(job.infoRenderTimeSum_PS_FramesReturned/job.infoTotal_FramesReturned/1000)

infoLines= infoLines + "CPU usage during frame (best): {}%\n".format(str(job.infoCpuUsageAverageMax))

try:
    infoLines= infoLines + "Max core usage: {} \n".format(job.infoCoreUsageMax)
except:
    #RR 9.0.04 and older
    pass

try:
    infoLines= infoLines + "Mem usage: {} GiB\n".format(job.infoClients_maxMemoryUsageMB/1024)
except:
    #RR 9.0.04 and older
    infoLines= infoLines + "Mem usage: {} GiB\n".format(job.maxMemoryUsage/1024)



print("Adding Information to job:\n"+infoLines)

jobs_list = []
jobs_list.append(int (args.jid))

#As you can change multiple jobs at once, you require the settings class 2 times
#A) One instance that contains the settings
#B) The other class to tell RR which settings to apply for all jobs
#   Any setting set to anything other than zero/empty will be applied
settings_Value=      rrJob.getClass_SettingsOnly()
settings_ChangeFlag= rrJob.getClass_SettingsOnly()

settings_Value.customDataSet_UserInfo(infoLines)
settings_ChangeFlag.customDataSet_UserInfo("TakeIt")   #any value other than an empty string

if not tcp.jobModify(jobs_list, settings_Value, settings_ChangeFlag):
    print("Error jobModify: " + tcp.errorMessage())


print("-------------- DONE ------------------")
