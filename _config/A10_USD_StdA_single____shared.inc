#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# %rrVersion%
#
#
################################## Identify Render Application ################################## 
Name= USD_StdA
OverrideClientInstallName= Houdini
Version=18
Type=Archive



##################################   [Windows] [Linux] [Osx] ##################################

CommandLine=<envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine> 


CommandLine=
	<SetEnvGlobal>


CommandLine=
	<SetEnvSoft>


CommandLine=
	<ResetExitCode> 


CommandLine=  
	::win  @echo 
	::lx   /bin/echo
	::osx  /bin/echo
	"*************** Rendering frame <FN> ***************"



CommandLine=  "<Exe><ED>husk"
	<AdditionalCommandlineParam>
	<ClientConfigParam>
    <verboseLevel>
    --usd-input <PD/<Scene>>
    <Cores --threads <Cores>>
	-o <ImageSingleOutputFile	"<PD/<ImageDir><ImageFilename>>"	? "<PD/<ImageDir><ImageFilename>$F<ImageFramePadding><ImageExtension>>" >
    -f <SeqStart> -n <TotalFrames> -i <SeqStep>

CommandLine=
	<CheckExitCode> <FN>

CommandLine=  
	::win  @echo 
	::lx   /bin/echo
	::osx  /bin/echo
	"*************** Frame <FN> done ***************"

################################## Render Settings ################################## 
FlagsVerbose0= <AvFrameTimeMin10 -V2a ? -V2>
FlagsVerbose1= -V0
FlagsVerbose2= -V1
FlagsVerbose3= -V3a
FlagsVerbose4= -V7a


################################## Submitter Settings ################################## 
SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
PPDeleteScenefile= 1~0
MultiOSScenes=1~0
SeqDivMIN= 1~1
SeqDivMAX= 1~10
AllowLocalSceneCopy= 0~0

################################## Client Settings ################################## 

IconApp=r_usd.png


Frozen_MinCoreUsage=1.90

licenseFailLine=  no license available
licenseFailLine=  no licenses could be found to run this application

permanentErrorSearchLine = Unable to connect to hserver for license
permanentErrorSearchLine = There must be a camera in the USD file

findFrameNoPre= Frame 
findFrameNoPost=  done 

::include(<ConfigFileName>__inhouse.inc)


