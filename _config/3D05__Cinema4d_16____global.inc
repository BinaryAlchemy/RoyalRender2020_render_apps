# Last change: %rrVersion%

REZ_EXE_WIN=   Commandline.exe
REZ_EXE_LX=    Commandline
REZ_EXE_MAC=   Commandline

IconApp=3D05__Cinema4d.png
LicenseFlags=<LicenseFlags>

################################## Render Settings ################################## 





################################## Submitter Settings ################################## 

SceneFileExtension= *.c4d
SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
AllowLocalSceneCopy= 1~0
UIStyle= 1~dark


################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90

findFrameNoPre= Rendering frame  
findFrameNoPost=  at

permanentErrorSearchLine = doesn't support the required sdk
permanentErrorSearchLine = Please sign into the Maxon App
permanentErrorSearchLine = Click here to activate the license
#permanentErrorSearchLine = Invalid License from License Server
permanentErrorSearchLine = Error running authentication
permanentErrorSearchLine = Missing serial number

licenseFailLine= Could not get a license
#licenseFailLine= Invalid License

RealTimeAbortLine= Missing serial number
RealTimeAbortLine= Render failure detected
RealTimeAbortLine= create stack trace
#RealTimeAbortLine= CRITICAL: Stop    We cannot detect this error as there are (Arnold, Redshift) scenes that report "CRITICAL: Stop [ge_container.h" and continue without issue.
RealTimeAbortLine= MacOSException::SuspendAllThreads
RealTimeAbortLine= aborting render script
RealTimeAbortLine= Could not get a license
RealTimeAbortLine= Error running authentication
RealTimeAbortLine= Invalid License from License Server


ErrorSearchLine = Error running authentication
ErrorSearchLine = Invalid License from License Server
ErrorSearchLine = Error: Invalid License
ErrorSearchLine = Error rendering document
ErrorSearchLine = Error rendering project
ErrorSearchLine = Rendering failed
ErrorSearchLine = aborting render script
#ErrorSearchLine = Not enough memory... #Disabled as we have a case in which this error is printed on C4D close. And we do not care about that
ErrorSearchLine = net.maxon.ui.class.osclipboard is missing
ErrorSearchLine = Invalid License from License Server
errorSearchLine= Several plugins used in this project are missing
#errorSearchLine= Plugin '        # We must not enable this as  C4D 2024 adds Redshift even if it is not used as renderer
errorSearchLine= Could not initialize Renderer


RemoveFromLog= Contains ~ Loading file ~ /corelibs/
RemoveFromLog= StartsWith ~ Warning: Team Render is deactivated
RemoveFromLog= Contains ~ opencl.dll \n Windows System Error #126
RemoveFromLog= Contains ~ g_licenseusername
RemoveFromLog= Contains ~ g_licensepassword
RemoveFromLog_NotDebugVerbose= StartsWith ~ CRITICAL: CONSTSTRING not freed:
RemoveFromLog_NotDebugVerbose= StartsWith ~ Warning: Unknown arguments


RenderAppWindow_WIN= Plugin Error ~  ~ 1 ~ Button ~ OK
RenderAppWindow_WIN= Application Error ~  ~ 1 ~ Button ~ OK


RemoveFromLog= Contains ~ g_licensepassword

::include(<ConfigFileName>__inhouse.inc)

