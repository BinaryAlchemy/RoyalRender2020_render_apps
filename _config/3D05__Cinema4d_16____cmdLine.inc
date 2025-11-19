

##################################   [Windows] [Linux] [Osx] [KSO] ##################################


CommandLine=<envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine>

CommandLine=
	<SetEnvGlobal>

CommandLine=
	<SetEnvSoft>

CommandLine=
	<OSSetEnv CUDA_VISIBLE_DEVICES ; <GpuListC>> 
    
CommandLine=
    ::win <rrLocalBin><OsxApp rrCopy> -oa <rrLocalRenderScripts>kso_c4d.pyp "%C4D_rrRenderScriptFolder%<PD>kso_c4d.pyp"
    ::osx <rrLocalBin><OsxApp rrCopy> -oa <rrLocalRenderScripts>kso_c4d.pyp "${C4D_rrRenderScriptFolder}<PD>kso_c4d.pyp"

CommandLine=
	<ResetExitCode> 

CommandLine= "<Exe>"
    -nogui
    -parallel
    ::win %LicenseFlags%
    ::osx $LicenseFlags
    ::lx  $LicenseFlags
    -Scene "<Scene>"
    <DoNotCheckForFrames ? -FName "<ImageDir><ImageFilename>" >
    ::win <DoNotCheckForFrames ? -FNameVar "<ImageDir><ImageFilenameVariables>" >
    ::osx <DoNotCheckForFrames ? -FNameVar '<ImageDir><ImageFilenameVariables>' >
    <ImageSingleOutputFile ? -FExt "<ImageExtension>" >
    -FrStart <SeqStart> -FrEnd <SeqEnd> -FrStep <SeqStep>
    -PyModPath <rrLocalRenderScripts><EL<PD>>
    <isKSO -KSOMode <isKSOBool> -KSOPort <ksoTCPport> >
    -FPadding <ImageFramePadding>
    <AppRenderer -renderer <AppRenderer>>
    -avFrameTime <AvFrameTimeSec>
    -noFrameLoop <NoFramebyFrameLoop True ? False>
    -sceneOS <sceneOS>
    -rAA <AAsamplesMultiply>
    <Channel -Channel <Channel> >
    <Camera -camera <Camera> >
    <CPU -threads <CPU> >
    <Layer -take "<Layer>" -c4dtake "<Layer>">
    <COOCIOfix -OCIOfix True>
    <AdditionalCommandlineParam>
	<ClientConfigParam>
	<COArnoldDriverOut -arnoldDriverOut true>
    <CODisableRenderError -disableRenderError True>
    <verboseLevel>
    g_prefspath=<rrLocalPrefs><ExeVersion>
	
CommandLine=
	<CheckExitCode> <FN>

CommandLine=
	"<rrBin64>rrKillWait" 1 QTGUIAGENT -this -withoutParent

#################################################
# KSO settings
KSO_Type= TCP

KSO_NewFrame= arg.avFrameTime= <AvFrameTimeSec> \nksoRenderFrame (<SeqStart>, <SeqEnd>, <SeqStep> )

KSO_Close= ksoQuit()

KSOlog_AppStarted= Scene init done, starting to render

KSOlog_Running= rrKSO server started

KSOlog_FrameDone= rrKSO Frame(s) done

KSOlog_Quit=rrKSO closed

################################## Render Settings ################################## 


COOCIOfix= 1 ~ 1
CODisableRenderError= 1 ~ 0


FlagsRegion= -RegionLeft  <X1 <X1> ?0> -RegionRight <X2 <X2> ? <Width>>  -RegionTop <Y1 <Y1> ? 0 >  -RegionBtm <Y2 <Y2> ? <Height>>
ImageSizeCommandline= -width <Width> -height <Height>

FlagsVerboseDefault= 
FlagsVerboseNone=        -verbose 0
FlagsVerboseWarning=     -verbose 1
FlagsVerboseInformation= -verbose 2
FlagsVerboseProgress=    -verbose 3
FlagsVerboseDebug=       -verbose 4





################################## Client Settings ################################## 
