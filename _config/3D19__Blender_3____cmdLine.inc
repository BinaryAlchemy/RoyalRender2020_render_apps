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
    -P "<rrLocalRenderScripts>kso_blender.py"
	<SceneState -S "<SceneState>">
	--python-use-system-env -y --
	<isKSO -rKso -rKSOport <ksoTCPport> >
	<GPUrequired -rGPU>
    <COLoadRedshift -rLoadRS>
    <COGPU_Add_CPU -rGPU_CPU>
    <COGPU_Use_Optix -rGPU_Optix>
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
	-rAA <AAsamplesMultiply>
	<AdditionalCommandlineParam>
    -rPyModPath <rrLocalRenderScripts><EL<PD>>
    <NoFramebyFrameLoop -NoFramebyFrameLoop>

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
COLoadRedshift= 0~0

################################## Render Settings ################################## 

FlagsRegion= -rMinX <X1 <X1f> ? 0>  -rMaxX <X2 <X2f> ? 1>  -rMinY <Y1 <Y1f> ? 0 > -rMaxY <Y2 <Y2f> ? 1>

ImageSizeCommandline= -rX <Width> -rY <Height>
