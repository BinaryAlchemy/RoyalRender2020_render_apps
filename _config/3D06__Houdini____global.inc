
IconApp=3D06__Houdini.png


################################## Submitter Settings ################################## 

CONoPerFrameLoop= 1 ~ 0
COIgnoreLoadWarnings= 1 ~ 0
COSubFrames = 1 ~ 0 ~ 4
COUnlockAssets = 1 ~ 1


SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
MultiOSScenes=1~1
AllowLocalSceneCopy= 1~0




################################## Client Settings ################################## 



#TexReplaceFormat= .hip ~ Char ~ AlwaysForward

findFrameNoPre= Frame Rendered #

licenseFailLine=  No licenses could be found to run this application

RealTimeAbortLine = ABORT ABORT ABORT
permanentErrorSearchLine = ABORT ABORT ABORT
permanentErrorSearchLine = OperationFailed
permanentErrorSearchLine = Unable to initialize
permanentErrorSearchLine = Unable to connect to hserver for license
permanentErrorSearchLine = The installed OpenGL driver is not able to run OpenGL
permanentErrorSearchLine = There must be a camera in the USD file

errorSearchLine = aborting render script

RenderAppWindow_WIN= Houdini DSO Error ~ Couldn't load ~ 1 ~ Button ~ OK
RenderAppWindow_WIN= Houdini ~ installed OpenGL driver is not able ~ 1 ~ Button ~ OK



::include(3D06__Houdini____global__inhouse.inc)