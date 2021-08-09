

MarkStandardErrorOutput= 0
IconApp=3D02__Maya.png

################################## Submitter Settings ################################## 
SceneFileExtension= *.ma;*.mb
AllowImageNameChange= 1
AllowImageDirChange= 1
SequenceDivide= 0~1
UIStyle= 1~dark






################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90

TexReplaceFormat= .ma ~ Char ~ AlwaysForward
TexReplaceFormat= .mb ~ FOR4 ~ AlwaysForward

licenseFailLine=  No license suitable to run
licenseFailLine=  License was not obtained
licenseFailLine=  could not get a license
licenseFailLine=  can't find any valid product licenses

errorSearchLine=  Error reported, aborting render script
errorSearchLine=  unable to open file
errorSearchLine=  V-Ray: Render interrupted

permanentErrorSearchLine = Unknown Maya file version
permanentErrorSearchLine = Cannot open renderer description file
permanentErrorSearchLine = Cannot render
permanentErrorSearchLine = rrMaya - ERR
#permanentErrorSearchLine = Unexpected Internal Failure  //removes as a plugin could fail which is not used at all
permanentErrorSearchLine = Invalid flag
permanentErrorSearchLine = Requested layer does not exist!


findFrameNoPre= Frame #
findFrameNoPost=  done


RenderAppWindow_WIN= Error ~ Unable to locate valid MAYA_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Fehler ~ Unable to locate valid MAYA_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Browse for Folder ~ Select a directory where Maya will store user data ~ 1 ~ Button ~ Cancel 
RenderAppWindow_WIN= Warning ~ Cannot run Maya without a valid setting for MAYA_APP_DIR ~ 1 ~ Button ~ &No 




RemoveFromLog= StartsWith ~ // generating Maya nodes...
RemoveFromLog= StartsWith ~ // parsing
RemoveFromLog= StartsWith ~ // loading
RemoveFromLog= StartsWith ~ VP2 Error : Failed to initialize graphics device.


::include(3D02__Maya____global__inhouse.inc)

