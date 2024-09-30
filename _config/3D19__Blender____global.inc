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




################################## Client Settings ################################## 
SeperateRenderLogFile= <rrLocalTemp><SceneFileName>.crash.txt

TexReplaceFormat= .blend ~ FOR4 ~ AlwaysForward

licenseFailLine=  No license suitable to run

permanentErrorSearchLine = Unknown Blender file version
permanentErrorSearchLine = Cannot open renderer description file
permanentErrorSearchLine = Cannot render
permanentErrorSearchLine = File written by newer Blender binary

findFrameNoPre= <ImageFilenameSlash>
findFrameNoPost= <ImageExtensionSlash>


RemoveFromLog_NotDebugVerbose= Contains ~ | Updating
RemoveFromLog_NotDebugVerbose= Contains ~ | Synchronizing object |
RemoveFromLog_NotDebugVerbose= Contains ~ | Building OptiX acceleration structure |
RemoveFromLog_NotDebugVerbose= Contains ~ | Updating Images |




RenderAppWindow_WIN= Error ~ Unable to locate valid BLENDER_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Browse for Folder ~ Select a directory where Blender will store user data ~ 1 ~ Button ~ Cancel 
RenderAppWindow_WIN= Warning ~ Cannot run Blender without a valid setting for BLENDER_APP_DIR ~ 1 ~ Button ~ &No 

IconApp=3D19__Blender.png


::include(<ConfigFileName>__inhouse.inc)
