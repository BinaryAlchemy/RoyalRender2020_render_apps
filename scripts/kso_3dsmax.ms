
try (
	logFilename= sysInfo.tempdir+ "rrMaxRender.log"
	out_text = openFile logFilename mode:"a+"
	format "     /n"  to:out_text
	format "     /n"  to:out_text
	close out_text
	-- Use pymxs for 3ds Max 2021 and later
	-- Maybe it even works from 3ds Max 2017 since that was the first version with pymxs
	if (maxVersion())[1] >= 23000 then
		python.ExecuteFile "*rrScriptFolder*\kso_3dsmax_pymxs.py"
	else
		python.ExecuteFile "*rrScriptFolder*\kso_3dsmax.py"
	quitMAX quiet:true exitCode:0 
) catch (
	errMessage=getCurrentException()
	print errMessage
	logFilename= sysInfo.tempdir+ "rrMaxRender.log"
	out_text = openFile logFilename mode:"a+"
	format "     /n"  to:out_text
	format " Error executing render script!/n"  to:out_text
	format errMessage to:out_text
	format "     /n"  to:out_text
	format "     /n"  to:out_text
	format "     /n"  to:out_text
	close out_text
	sleep 2
)
