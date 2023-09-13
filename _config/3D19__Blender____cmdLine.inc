#
# Author: Friedrich Wessel, Callisto FX GmbH
# Updated: Holger Schoenberger and Paolo Acampora, Binary Alchemy
# %rrVersion%
#
#


##################################  [Windows] [Linux] [OSX]  ##################################

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
	-b 
    "<Scene>"
	-o "<ImageDir><ImageFilename><FramePadding #>"
	<CustomFrameFormat -F <CustomFrameFormat>>
    <ImageSingleOutputFile ? -x 1>
    <SceneState -S "<SceneState>">
	-s <SeqStart>
	-e <SeqEnd>
	-j <SeqStep>
    <Cores -t <Cores> ? -t 0>
    <COCyclesEnableGPU -P <rrLocalRenderScripts>blender_cycles_enable_gpu.py>
    <COLoadRedshift -P <rrLocalRenderScripts>blender_load_redshift.py>
	<AdditionalCommandlineParam>
	-a
    -y


CommandLine=
	<CheckExitCode> <FN>
    
    
################################## Submitter Settings ##################################    
COCyclesEnableGPU= 0~0
COLoadRedshift= 0~0



################################## Render Settings ################################## 

FlagsRenderQuality0= 
FlagsRenderQuality1= -eaa 3 -ss 1 -mss 1 -ufil false
FlagsRenderQuality2= -eaa 1 -ss 2 -mss 8 -ufil true -rct 0.2 -gct 0.2 -bct 0.2
FlagsRenderQuality3= -eaa 0 -ss 3 -mss 9 -ufil true -rct 0.1 -gct 0.1 -bct 0.1
FlagsRenderQuality4= -eaa 0 -ss 3 -mss 9 -ufil true -rct 0.05 -gct 0.05 -bct 0.05


ImageSizeCommandline= -x <Width> -y  <Height>