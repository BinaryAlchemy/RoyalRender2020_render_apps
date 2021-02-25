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

::win CommandLine= set   "CUDA_VISIBLE_DEVICES=<GpuListC>"
::lx  CommandLine= setenv CUDA_VISIBLE_DEVICES <GpuListC> 
::osx CommandLine= setenv CUDA_VISIBLE_DEVICES <GpuListC> 

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
	<AdditionalCommandlineParam>
	-a
    -y


CommandLine=
	<CheckExitCode> <FN>

