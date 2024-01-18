#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# %rrVersion%
#
#
################################## Identify Render Application ################################## 
Name= USD_StdA_single
OverrideClientInstallName= Houdini
Version=18
Type=Archive
TYPEv9=Archive




################################## Render Settings ################################## 


#Deprecated settings
FlagsVerbose0= <AvFrameTimeMin10 -V3a ? -V2>
FlagsVerbose1= -V0
FlagsVerbose2= -V1
FlagsVerbose3= -V4a
FlagsVerbose4= -V7a


FlagsVerboseDefault= <AvFrameTimeMin10 -V3a ? -V2>
FlagsVerboseNone=        -V0
FlagsVerboseWarning=     -V1
FlagsVerboseInformation= -V4a
FlagsVerboseProgress=    -V7a
FlagsVerboseDebug=       -V9ap



################################## Submitter Settings ################################## 
SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
PPDeleteScenefile= 1~0
MultiOSScenes=1~0
SeqDivMIN= 1~1
SeqDivMAX= 1~10
AllowLocalSceneCopy= 0~0

COSingleRenderProduct= 1 ~ 0
COAllowProcedurals= 1 ~ 0
COClassicExr= 1 ~ 0


################################## Client Settings ################################## 

IconApp=r_usd.png


Frozen_MinCoreUsage=1.90

licenseFailLine=  no license available
licenseFailLine=  no licenses could be found to run this application

licenseFailLine=  No karma license found
BrokenImageLine=  No karma license found

licenseFailLine=  Failed to checkout an engine license
BrokenImageLine=  Failed to checkout an engine license




permanentErrorSearchLine = Unable to connect to hserver for license
permanentErrorSearchLine = There must be a camera in the USD file

findFrameNoPre= Frame 
findFrameNoPost=  done 

::include(<ConfigFileName>__inhouse.inc)


