# Last change: %rrVersion%

REZ_EXE_WIN=   UnrealEditor-Cmd.exe
REZ_EXE_LX=    UnrealEditor-Cmd
REZ_EXE_MAC=   UnrealEditor-Cmd


IconApp=3D21__UnrealEngine.png


################################## Submitter Settings ##################################
SequenceDivide= 0~1
SeqDivMIN=0~0
GPUrequired=1~1
AllowLocalSceneCopy= 0~0
DistributeStartToEnd=0~1

################################## Client Settings ##################################

RemoveFromLog= StartsWith ~ ovr_Initialize failed: Unable to load LibOVRRT DLL 

RemoveFromLog_NotDebugVerbose= Contains ~ LogConfig: Set CVar
RemoveFromLog_NotDebugVerbose= Contains ~ LogConfig: CVar
RemoveFromLog_NotDebugVerbose= Contains ~ LogConfig: Applying CVar settings
RemoveFromLog_NotDebugVerbose= Contains ~ LogPluginManager: Mounting Engine plugin
RemoveFromLog_NotDebugVerbose= Contains ~ LogModuleManager: InternalLoadLibrary:
RemoveFromLog_NotDebugVerbose= Contains ~ LogDevObjectVersion:
RemoveFromLog_NotDebugVerbose= Contains ~ LogMovieRenderPipeline: Generated new ShotInfo
RemoveFromLog_NotDebugVerbose= Contains ~ LogMovieRenderPipeline: Reusing existing ShotInfo

::include(<ConfigFileName>__inhouse.inc)
