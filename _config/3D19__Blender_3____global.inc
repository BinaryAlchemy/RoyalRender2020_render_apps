#
# Author: Friedrich Wessel, Callisto FX GmbH
# Updated: Holger Schoenberger and Paolo Acampora, Binary Alchemy
# v8.2.45
#
#


################################## Render Settings ################################## 

FlagsRenderQuality0= 
FlagsRenderQuality1= -eaa 3 -ss 1 -mss 1 -ufil false
FlagsRenderQuality2= -eaa 1 -ss 2 -mss 8 -ufil true -rct 0.2 -gct 0.2 -bct 0.2
FlagsRenderQuality3= -eaa 0 -ss 3 -mss 9 -ufil true -rct 0.1 -gct 0.1 -bct 0.1
FlagsRenderQuality4= -eaa 0 -ss 3 -mss 9 -ufil true -rct 0.05 -gct 0.05 -bct 0.05

FlagsRegion= -reg <X1 <X1> ? 0>  <X2 <X2> ? 19999> <Y1 <Y1> ? 0 > <Y2 <Y2> ? 19999>

ImageSizeCommandline= -x <Width> -y  <Height>

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

findFrameNoPre= <ImageFilenameSlash>
findFrameNoPost= <ImageExtensionSlash>


RenderAppWindow_WIN= Error ~ Unable to locate valid BLENDER_APP_DIR ~ 1 ~ Button ~ OK 
RenderAppWindow_WIN= Browse for Folder ~ Select a directory where Blender will store user data ~ 1 ~ Button ~ Cancel 
RenderAppWindow_WIN= Warning ~ Cannot run Blender without a valid setting for BLENDER_APP_DIR ~ 1 ~ Button ~ &No 

IconApp=3D19__Blender.png


::include(<ConfigFileName>__inhouse.inc)
