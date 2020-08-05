
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

ImageSize= PAL  ~720~576
ImageSize= NTSC  ~720~486
ImageSize= HD  ~ 1920~1080
ImageSize= HD small  ~ 1280~720
ImageSize= 4:3 Small ~ 400~300
ImageSize= 4:3 Big   ~ 1000~750
ImageSize= 16:9     ~ 1024~576

################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90

findFrameNoPre= Rendering frame  
findFrameNoPost=  at

#permanentErrorSearchLine = Invalid License from License Server
permanentErrorSearchLine = doesn't support the required sdk

licenseFailLine=  Missing serial number
licenseFailLine= Error: Invalid License
licenseFailLine= Could not get a license
licenseFailLine= Error running authentication


RealTimeAbortLine= Missing serial number
RealTimeAbortLine= Render failure detected
RealTimeAbortLine= create stack trace
#RealTimeAbortLine= CRITICAL: Stop    We cannot detect this error as there are (Arnold) scenes that report "CRITICAL: Stop [ge_container.h(291)]" once at scene open and continue witrhout issue.
RealTimeAbortLine= MacOSException::SuspendAllThreads
RealTimeAbortLine= aborting render script
RealTimeAbortLine= Could not get a license
RealTimeAbortLine= Error running authentication



ErrorSearchLine = Error rendering document
ErrorSearchLine = Error rendering project
ErrorSearchLine = Rendering failed
ErrorSearchLine = aborting render script
ErrorSearchLine = Not enough memory...


RenderAppWindow_WIN= Plugin Error ~  ~ 1 ~ Button ~ OK
RenderAppWindow_WIN= Application Error ~  ~ 1 ~ Button ~ OK


RemoveFromLog= Contains ~ g_licensepassword

::include(<ConfigFileName>__inhouse.inc)

