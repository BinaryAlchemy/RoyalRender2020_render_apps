################################## [Windows] [Linux] [Osx] ##################################

CommandLine=<envFileExecute <rrEnvFile>> 

CommandLine=<rrEnvLine>


CommandLine=
	<SetEnvGlobal>

CommandLine=
	<SetEnvSoft>

CommandLine=
	<ResetExitCode> 
	
CommandLine=  
	"<Exe>"
     --batch 
     --katana-file "<Scene>"
     --render-node "<Layer>"
     <channel --render-views=<channel>>
     -t <SeqStart>-<SeqEnd>
     --threads2d=<Cores>
     --threads3d=<Cores>
	<AdditionalCommandlineParam>
	<ClientConfigParam>

CommandLine=
	<CheckExitCode> <FN>


