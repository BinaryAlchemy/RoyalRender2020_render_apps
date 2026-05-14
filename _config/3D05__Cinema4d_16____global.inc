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
permanentErrorSearchLine = Error running authentication
permanentErrorSearchLine = Missing serial number
#permanentErrorSearchLine = Invalid License from License Server
#permanentErrorSearchLine = err: OperationCancelled   Cannot be enabled as "OperationCancelledError [world.cpp" it happens in 2026 while closing 

licenseFailLine= Could not get a license
#licenseFailLine= Invalid License

RealTimeAbortLine= Missing serial number
RealTimeAbortLine= Render failure detected
RealTimeAbortLine= create stack trace
RealTimeAbortLine= MacOSException::SuspendAllThreads
RealTimeAbortLine= aborting render script
RealTimeAbortLine= Could not get a license
RealTimeAbortLine= Error running authentication
RealTimeAbortLine= Invalid License from License Server
#RealTimeAbortLine= CRITICAL: Stop    This error happens with new C4D installations as well: "CRITICAL: Stop [ge_container.cpp(1111)]". C4D continues without issue afterwards.


ErrorSearchLine = Error running authentication
ErrorSearchLine = Invalid License from License Server
ErrorSearchLine = Error: Invalid License
ErrorSearchLine = Error rendering document
ErrorSearchLine = Error rendering project
ErrorSearchLine = Rendering failed
ErrorSearchLine = aborting render script
ErrorSearchLine = net.maxon.ui.class.osclipboard is missing
ErrorSearchLine = Invalid License from License Server
ErrorSearchLine= Several plugins used in this project are missing
ErrorSearchLine= Could not initialize Renderer
#ErrorSearchLine= Plugin '              # We must not enable this as  C4D 2024 adds Redshift even if it is not used as renderer
#ErrorSearchLine = Not enough memory... # Disabled as we have a case in which this error is printed on C4D close. And we do not care about that


RemoveFromLog= Contains ~ Loading file ~ /corelibs/
RemoveFromLog= StartsWith ~ Warning: Team Render is deactivated
RemoveFromLog= Contains ~ opencl.dll \n Windows System Error #126
RemoveFromLog= Contains ~ g_licenseusername
RemoveFromLog= Contains ~ g_licensepassword
RemoveFromLog= Contains ~ OperationCancelledError [world.cpp
RemoveFromLog_NotDebugVerbose= StartsWith ~ CRITICAL: CONSTSTRING not freed:
RemoveFromLog_NotDebugVerbose= StartsWith ~ Warning: Unknown arguments
RemoveFromLog_NotDebugVerbose= StartsWith ~ CRITICAL: Stop [ge_container.cpp
RemoveFromLog_NotDebugVerbose= Contains ~ datareader_binary_impl.cpp


RenderAppWindow_WIN= Plugin Error ~  ~ 1 ~ Button ~ OK
RenderAppWindow_WIN= Application Error ~  ~ 1 ~ Button ~ OK



::include(<ConfigFileName>__inhouse.inc)

