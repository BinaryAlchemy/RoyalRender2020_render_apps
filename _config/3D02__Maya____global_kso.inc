

IconApp=3D02__Maya.png
MarkStandardErrorOutput= 0
MultiOSScenes=0~1


################################## Submitter Settings ################################## 

SceneFileExtension= *.ma;*.mb
AllowImageNameChange= 1
AllowImageDirChange= 1
SequenceDivide= 0~1
UIStyle= 1~dark


ImageSize= PAL  ~720~576
ImageSize= NTSC  ~720~486
ImageSize= HD  ~ 1920~1080
ImageSize= HD small  ~ 1280~720
ImageSize= 4:3 Small ~ 400~300
ImageSize= 4:3 Big   ~ 1000~750
ImageSize= 16:9     ~ 1024~576

CODisableImagePlanes= 1~0
CONoPerFrameLoop= 1 ~ 0


################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90


licenseFailLine=  No license suitable to run
licenseFailLine=  License was not obtained
licenseFailLine=  could not get a license
#licenseFailLine=  All licenses in use  //not reliable as Arnold RLM sometimes checks 10 times to get a license. Or RLM lic server is used in combination with CLM
licenseFailLine=  can't find any valid product licenses


errorSearchLine=  Error reported, aborting render script
errorSearchLine=  unable to open file
errorSearchLine=  V-Ray: Render interrupted

permanentErrorSearchLine = Cannot open renderer description file
permanentErrorSearchLine = Cannot render
permanentErrorSearchLine = rrMaya - ERR
#permanentErrorSearchLine = Unexpected Internal Failure  //removes as a plugin could fail which is not used at all
permanentErrorSearchLine = Invalid flag
permanentErrorSearchLine = Requested layer does not exist!

RealTimeAbortLine= Stack trace:
#RealTimeAbortLine= Unknown Maya file version
RealTimeAbortLine= Fatal Error. Attempting to save in
RealTimeAbortLine= Failed batch render
#RealTimeAbortLine= All licenses in use   //not reliable as Arnold RLM sometimes checks 10 times to get a license. Or RLM lic server is used in combination with CLM


findFrameNoPre= Frame #
findFrameNoPost=  done


RenderAppWindow_WIN= Error ~ Unable to locate valid MAYA_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Browse for Folder ~ Select a directory where Maya will store user data ~ 1 ~ Button ~ Cancel 
RenderAppWindow_WIN= Warning ~ Cannot run Maya without a valid setting for MAYA_APP_DIR ~ 1 ~ Button ~ &No 



RemoveFromLog= StartsWith ~ // generating Maya nodes...
RemoveFromLog= StartsWith ~ // parsing
RemoveFromLog= StartsWith ~ // loading
RemoveFromLog= StartsWith ~ VP2 Error : Failed to initialize graphics device.
#The RR render script kso_maya.py has its own report if the OpenColorIO file is missing. Removal of this message is required for cross OS rendering
RemoveFromLog= Contains ~ Missing OpenColorIO configuration file
RemoveFromLog= Contains ~ UUID already in use
RemoveFromLog= Contains ~ has no '.ai_translator' attribute
RemoveFromLog= Contains ~ pgYetiDLRender.dll: The specified module 
RemoveFromLog= Contains ~ pgYetiPrmanRender.dll: The specified 
RemoveFromLog= Contains ~ This file contains legacy render layers and Maya is currently in Render Setup mode
RemoveFromLog= StartsWith ~ Warning: Unknown object type: pgYeti
RemoveFromLog= Contains ~ ERROR   | there is no camera!






::include(3D02__Maya____global_kso__inhouse.inc)

