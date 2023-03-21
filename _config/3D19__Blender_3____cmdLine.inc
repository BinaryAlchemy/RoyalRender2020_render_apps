#
# Author: Paolo Acampora, Binary Alchemy
# %rrVersion%
#
#


##################################  [Windows] [Linux] [OSX] [KSO]  ##################################

CommandLine= <envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine>

CommandLine=
	<SetEnvGlobal>

CommandLine=
	<SetEnvSoft>

CommandLine=
	<OSSetEnv CUDA_VISIBLE_DEVICES ; <GpuListC>>

CommandLine=
 echo crash file in 
 <rrLocalTemp><SceneFileName>.crash.txt

CommandLine=
	<ResetExitCode> 


CommandLine=   "<Exe>"
    <Cores -t <Cores> ? -t 0>
	-b
    -P "<rrLocalRenderScripts>\kso_blender.py"
	<SceneState -S "<SceneState>">
	--python-use-system-env -y --
	<isKSO -rKso -rKSOport <ksoTCPport> >
	<COCyclesEnableGPU -rGPU>
    <COLoadRedshift -rLoadRS>
	-rStart <SeqStart>
	-rEnd <SeqEnd>
	-rStep <SeqStep>
	-rBlend "<Scene>"
	-rOut "<ImageDir><ImageFilename>"
	-rPad "<ImageFramePadding>"
	-rExt "<ImageExtension>"
	<AppRenderer -rRenderer <AppRenderer>>
	<Layer -rLayer "<Layer>">
	<CustomFrameFormat -rFormat <CustomFrameFormat>>
	<COAntiAliasMultiFloat -rAA <COAntiAliasMultiFloat>>
	<AdditionalCommandlineParam>
    -rPyModPath <rrLocalRenderScripts><EL<PD>>

CommandLine=
	<CheckExitCode> <FN>
    

#################################################
# KSO settings
KSO_Type= TCP

KSO_NewFrame= set_average_frame_time(<AvFrameTimeSec>) \nkso_render_frames(<SeqStart>, <SeqEnd>, <SeqStep>)

KSO_Close= ksoQuit()

KSOlog_AppStarted= Scene init done, starting to render

KSOlog_Running= rrKSO server started

KSOlog_FrameDone= rrKSO Frame(s) done

KSOlog_Quit=rrKSO closed



################################## Submitter Settings ##################################    
COCyclesEnableGPU= 0~0
COLoadRedshift= 0~0
COAntiAliasMultiFloat= 1 ~ 1 ~ 100

################################## Render Settings ################################## 

FlagsRegion= -reg <X1 <X1> ? 0>  <X2 <X2> ? 19999> <Y1 <Y1> ? 0 > <Y2 <Y2> ? 19999>

ImageSizeCommandline= -rX <Width> -rY <Height>
