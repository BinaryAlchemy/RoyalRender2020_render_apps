# config file format version 8.0
#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# %rrVersion%
#
#
################################## Identify Render Application ################################## 
Name= Houdini
rendererName= createUSD
Version=18

TYPEv9=FileExport



################################## [Windows] [Linux] [Osx] [KSO] ##################################


CommandLine=<envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine>

CommandLine=
    <CPU <LimitCPUs> <CPU>>

CommandLine=
    <SetEnvGlobal>

CommandLine=
    <SetEnvSoft>


CommandLine=
    <ResetExitCode> 

CommandLine= 
    "<Exe>"
    <PD/ "<rrLocalRenderScripts>kso_houdini.py" >
    -scene "<PD/<Scene>>"
    -renderer "createUSD"
    -exportmode true
    -FrStart <SeqStart>
    -FrEnd <SeqEnd>
    -FrStep <SeqStep>
    -FPadding <ImageFramePadding>
    -FName "<PD/<ImageDir><ImageFilenameVariables>>" 
    <ImageExtension -FExt "<ImageExtension>" >
    <ImageSingleOutputFile -FSingleFile True>
    -rop "<PD/<Layer>>"
    -threads <CPU>
    -renderDemo False 
    -avFrameTime <AvFrameTimeSec>
    <AvFrameTimeMin10 -verbose True>
    <NoFramebyFrameLoop -noFrameLoop True>
    <ImageSingleOutputFile -noFrameLoop True>
    <COIgnoreLoadWarnings -ignoreLoadIssues True>
    <COUnlockAssets -unlockAssets True>
    <COSubFrames -subFrames <COSubFrames>>
    <SequenceDivideMin ? -noFrameLoop True>    
    -PyModPath <rrLocalRenderScripts><EL<PD>>
    <channel -take <channel>>
    <SceneState -wedge <SceneState>>
    <COIgnoreROPDependencies -ignoreROPDependencies>
    <isKSO -KSOMode <isKSOBool> -KSOPort <ksoTCPport> >
    <AdditionalCommandlineParam>
    <ClientConfigParam>
    

CommandLine=
    <CheckExitCode> <FN>


CommandLine=
    "<rrBin64>rrKillWait" 1 hserver true




#################################################
# KSO settings
KSO_Type= TCP

KSO_NewFrame= ksoRenderFrame (<SeqStart>, <SeqEnd>, <SeqStep> )

KSO_Close= ksoQuit()

KSOlog_AppStarted= Scene init done, starting to render

KSOlog_Running= rrKSO server started

KSOlog_FrameDone= rrKSO Frame(s) done

KSOlog_Quit=rrKSO closed




################################## Render Settings ##################################


ImageSizeCommandline= -width <Width> -height <Height>
AllowLocalRenderOut= 0~0


################################## Submitter + Client Settings ################################## 

IconRenderer=r_usd.png

::include(3D06__Houdini____global.inc)

::include(<ConfigFileName>__inhouse.inc)
