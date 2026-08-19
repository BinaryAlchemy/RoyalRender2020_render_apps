#
# Author: Holger Schoenberger and Paolo Acampora, Binary Alchemy
# %rrVersion%
#
#

REZ_EXE_WIN=   blender.exe
REZ_EXE_LX=    blender
REZ_EXE_MAC=   Blender



################################## Submitter Settings ################################## 
StartMultipleInstances= 1~0
SceneFileExtension= *.blend
AllowImageNameChange= 1
AllowImageDirChange= 1
SequenceDivide= 0~1
AllowLocalSceneCopy= 1~0
UIStyle= 1~dark




################################## Client Settings ################################## 
SeparateRenderLogFile= <rrLocalTemp><SceneFileName>.crash.txt

TexReplaceFormat= .blend ~ FOR4 ~ AlwaysForward


FlagsVerboseDefault= --log-level info
FlagsVerboseNone= --log-level fatal
FlagsVerboseWarning= --log-level warning
FlagsVerboseInformation= --log-level info
FlagsVerboseProgress= --log-level info
FlagsVerboseDebug= --log-level debug


licenseFailLine=  No license suitable to run

permanentErrorSearchLine = Unknown Blender file version
permanentErrorSearchLine = Cannot open renderer description file
permanentErrorSearchLine = Cannot render
permanentErrorSearchLine = File written by newer Blender binary

findFrameNoPre= <ImageFilenameSlash>
findFrameNoPost= <ImageExtensionSlash>


RemoveFromLog_NotDebugVerbose= Contains ~ | Updating
#RemoveFromLog_NotDebugVerbose= Contains ~ | Updating Images |
RemoveFromLog_NotDebugVerbose= Contains ~ | Synchronizing object |
RemoveFromLog_NotDebugVerbose= Contains ~ | Building OptiX acceleration structure |
RemoveFromLog_NotDebugVerbose= Contains ~ cycles           | Adaptive sampling::
RemoveFromLog_NotDebugVerbose= Contains ~ cycles           | Rendered
RemoveFromLog_NotDebugVerbose= Contains ~ cycles           | Use



RenderAppWindow_WIN= Error ~ Unable to locate valid BLENDER_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Browse for Folder ~ Select a directory where Blender will store user data ~ 1 ~ Button ~ Cancel 
RenderAppWindow_WIN= Warning ~ Cannot run Blender without a valid setting for BLENDER_APP_DIR ~ 1 ~ Button ~ &No 

IconApp=3D19__Blender.png


::include(<ConfigFileName>__inhouse.inc)
