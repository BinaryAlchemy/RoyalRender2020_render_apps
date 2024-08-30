    # Last change: %rrVersion%

REZ_EXE_WIN=   kick.exe
REZ_EXE_LX=    kick
REZ_EXE_MAC=   kick





################################## Render Settings ################################## 
sceneIsMultiFrame= 1

FlagsVerboseDefault= -v 1
FlagsVerboseNone= -v 0
FlagsVerboseWarning= -v 1
FlagsVerboseInformation= -v 2
FlagsVerboseProgress= -v 3

FlagsRenderQuality0= 
FlagsRenderQuality1= -as 1 -idisp
FlagsRenderQuality2= -as 4
FlagsRenderQuality3= -as 6
FlagsRenderQuality4= -as 8

FlagsRegion= -rg <X1 <X1> ?0>  <Y1 <Y1> ? 0 > <X2 <X2> ? 19999> <Y2 <Y2> ? 19999>

ImageSizeCommandline= -r <Width> <Height>

################################## Submitter Settings ################################## 

SceneFileExtension= *.ass
SequenceDivide= 0~1
AllowImageNameChange= 1
AllowImageDirChange= 1
PPDeleteScenefile= 1~1
MultiOSScenes=0~0
SeqDivMIN= 1~1
SeqDivMAX= 1~10
AllowLocalSceneCopy= 0~0

COSingleRenderProduct= 1 ~ 1


################################## Client Settings ################################## 

Frozen_MinCoreUsage=1.90

TexReplaceFormat= .ass ~ Char

licenseFailLine=  could not get a license
licenseFailLine=  No license suitable to run
licenseFailLine=  could not connect to license server
licenseFailLine=  error checking out license for arnold
licenseFailLine=  License was not obtained
licenseFailLine=  abort_on_license_fail enabled
licenseFailLine=  aborting render because the abort_on_license_fail option

errorSearchLine=  render terminating early

RealTimeAbortLine= failed authorization

findFrameNoPre= Frame 
findFrameNoPost=  done 

IconApp=empty.png
::include(r_Arnold.inc)


::include(<ConfigFileName>__inhouse.inc)
