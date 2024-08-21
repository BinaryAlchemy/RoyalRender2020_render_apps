# Last change: %rrVersion%

REZ_EXE_WIN=   Commandline.exe
REZ_EXE_LX=    Commandline
REZ_EXE_MAC=   Commandline

IconApp=3D05__Cinema4d.png
LicenseFlags=<LicenseFlags>

################################## Render Settings ################################## 



ImageSizeCommandline= -oresolution <Width> <Height>



################################## Submitter Settings ################################## 

SceneFileExtension= *.c4d
SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
AllowLocalSceneCopy= 1~0
UIStyle= 1~dark

CONoFrameLoop= 1 ~ 0


################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90

findFrameNoPre= Rendering frame  
findFrameNoPost=  at

#permanentErrorSearchLine = Invalid License from License Server
permanentErrorSearchLine = doesn't support the required sdk
permanentErrorSearchLine = Please sign into the Maxon App
permanentErrorSearchLine = Click here to activate the license


licenseFailLine= Missing serial number
licenseFailLine= Error: Invalid License
licenseFailLine= Could not get a license
licenseFailLine= Error running authentication
licenseFailLine= Invalid License from License Server

RealTimeAbortLine= Missing serial number
RealTimeAbortLine= Render failure detected
RealTimeAbortLine= create stack trace
#RealTimeAbortLine= CRITICAL: Stop    We cannot detect this error as there are (Arnold, Redshift) scenes that report "CRITICAL: Stop [ge_container.h" and continue without issue.
RealTimeAbortLine= MacOSException::SuspendAllThreads
RealTimeAbortLine= aborting render script
RealTimeAbortLine= Could not get a license
RealTimeAbortLine= Error running authentication
RealTimeAbortLine= Invalid License from License Server



ErrorSearchLine = Error rendering document
ErrorSearchLine = Error rendering project
ErrorSearchLine = Rendering failed
ErrorSearchLine = aborting render script
#Disabled as we have a case in which this error is printed on C4D close. And we do not care about that
#ErrorSearchLine = Not enough memory...
ErrorSearchLine = net.maxon.ui.class.osclipboard is missing
ErrorSearchLine = Invalid License from License Server

RenderAppWindow_WIN= Plugin Error ~  ~ 1 ~ Button ~ OK
RenderAppWindow_WIN= Application Error ~  ~ 1 ~ Button ~ OK


RemoveFromLog= Contains ~ g_licensepassword

::include(<ConfigFileName>__inhouse.inc)

