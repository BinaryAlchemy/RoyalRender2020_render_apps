

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
    -noFrameLoop <CONoFrameLoop True ? False>
    -sceneOS <sceneOS>
    <Channel -Channel <Channel> >
    <Camera -camera <Camera> >
    <CPU -threads <CPU> >
    <Layer -take "<Layer>" -c4dtake "<Layer>">
    <AdditionalCommandlineParam>
	<ClientConfigParam>
	<COArnoldDriverOut -arnoldDriverOut true>
    g_prefspath=<rrLocalPrefs><ExeVersion>
	
CommandLine=
	<CheckExitCode> <FN>

CommandLine=
	"<rrBin64>rrKillWait" 1 QTGUIAGENT true

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


FlagsRegion= -RegionLeft  <X1 <X1> ?0> -RegionRight <X2 <X2> ? <Width>>  -RegionTop <Y1 <Y1> ? 0 >  -RegionBtm <Y2 <Y2> ? <Height>>
ImageSizeCommandline= -width <Width> -height <Height>

################################## Client Settings ################################## 

errorSearchLine= Several plugins used in this project are missing
errorSearchLine= Plugin '
errorSearchLine= Could not initialize Renderer


RemoveFromLog= Contains ~ Loading file ~ /corelibs/
RemoveFromLog= StartsWith ~ Warning: Team Render is deactivated
RemoveFromLog= Contains ~ opencl.dll \n Windows System Error #126
RemoveFromLog= Contains ~ g_licenseusername
RemoveFromLog= Contains ~ g_licensepassword

