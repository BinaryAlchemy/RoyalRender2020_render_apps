
IconApp=3D06__Houdini.png


################################## Submitter Settings ################################## 


SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
MultiOSScenes=1~1
AllowLocalSceneCopy= 1~0


ImageSize= PAL  ~720~576
ImageSize= NTSC  ~720~486
ImageSize= HD  ~ 1920~1080
ImageSize= HD small  ~ 1280~720
ImageSize= 4:3 Small ~ 400~300
ImageSize= 4:3 Big   ~ 1000~750
ImageSize= 16:9     ~ 1024~576


################################## Client Settings ################################## 



#TexReplaceFormat= .hip ~ Char ~ AlwaysForward

findFrameNoPre= Frame Rendered #

licenseFailLine=  No licenses could be found to run this application

RealTimeAbortLine = ABORT ABORT ABORT
permanentErrorSearchLine = ABORT ABORT ABORT


permanentErrorSearchLine = OperationFailed
permanentErrorSearchLine = Unable to initialize
permanentErrorSearchLine = Unable to connect to hserver for license

RenderAppWindow_WIN= Houdini DSO Error ~ Couldn't load ~ 1 ~ Button ~ OK

::include(3D06__Houdini____global__inhouse.inc)