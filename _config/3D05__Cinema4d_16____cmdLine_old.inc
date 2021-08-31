

##################################   [Windows] [Linux] [Osx] ##################################


CommandLine=<envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine>

CommandLine=
	<SetEnvGlobal>

CommandLine=
	<SetEnvSoft>


CommandLine=
	<ResetExitCode> 

CommandLine=  "<Exe>"
	-nogui
	-render "<Scene>"
	-frame <SeqStart> <SeqEnd> <SeqStep>
	                             <Channel ?  -oimage "<ImageDir><ImageFilenameVariables><EL.>" >
	<Channel <EndsWith(<Channel>, Reg_Multi) -oimage "<ImageDir><ImageFilenameVariables><EL.>" > >
	<Channel -omultipass "<ImageDir><ImageFilenameVariables><EL.>">
	<Layer -take "<Layer>">
	<CPU -threads <CPU> >
	<OverrideImageFormat -oformat <OverrideImageFormat>? >
	<AdditionalCommandlineParam>
	<ClientConfigParam>
	g_prefspath=<rrLocalPrefs><ExeVersion>
	#-parallel
	
	
CommandLine=
	<CheckExitCode> <FN> 

CommandLine=
	"<rrBin64>rrKillWait" 1 QTGUIAGENT true

