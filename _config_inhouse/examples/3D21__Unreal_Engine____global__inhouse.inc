#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
#
# Last change: %rrVersion%
#
# This include file changes Unreal from a per-Client Installation into a RR shared Executable installation.
# RR Shared Executables work this way:
#     If the client gets a Unreal job, then it will sync all files from the <ExeCopyFromDir> to a <ExeCopyToDir> folder on the local drive.
#     It copies the files as applications have a lot of files. And x machines accessing the same files over and over for each function can slow down the network pretty much.
#     The sync is executed each time the client starts a Unreal job. If the files have not been changed, then no file is copied. If a file was removed, it is removed on the local drive as well.
#
#
#
# Installation steps:
# 1) Copy this file into render_apps\_config_inhouse\
# 2) Send a "restart rrClient app" command via rrControl to all active clients. (To reload the config)
# 3) Copy your Blender installation from your workstation 
#   c:\Program Files\Epic Games\UE_5.3   into   RR\render_apps\renderer_exe\unreal engine\win_x64\UE_5.3
#     Of course you need to modify the version 5.3 and the os "win64" with the version you use.
#     If you use multiple versions, copy all folders that you need. The Clients auto-version change works for shared exe as well.
#     Note that it is possible to get an information from the rrClient about the right path.
#     If you skip this step, then the renderlog in step 4 will tell you the right search path.
#
#     Note: If you like, you can reduce the size of the folder.   
#        -   *.pdb files are development files required for finding the source location of a crash.
#        -   *.cpp.obj, *.cc.obj and *.lib files are required if you want to develop (compile) a new application/plugin
#        -   There are some /Debug and /Release folders. Again required for development only
#        -   Folder /Engine/Source
#        -   Folder /Engine/Documentation
#        -   Folder /Samples
#        -   Folder /Engine/Plugins/Experimental/PythonFoundationPackages/Content/Python/Lib/ contains subfolders for each OS.  Remove the OS you do not need.
#        -   *.dll are used on Windows, *.so on Linux and *.dylib on MacOS. Remove the file types you don't need
#        -   There is one huge (5GB) python package which is required for some experimental plugins only. 
#             To find out which experimental plugin uses this module, search for .py files with "import torch".
#             If you do not use them, remove it: \Plugins\Experimental\PythonFoundationPackages\Content\Python\Lib\Win64\site-packages\torch
#        On Windows with UE version 5.3.2, this reduced the application from  233430 files, 39.4GB   to 151971 files, 17,7GB
#
# 4) Send an Unreal job. 
#    The first start will take some time as the clients have to copy a lot of files.


ExeCopyFromDir = <rrSharedExeDir>
ExeCopyToDir   = <rrLocalExeDir>

ExeCopiedWin=  <rrLocalExeDir>UE_*\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
ExeCopiedLx=   <rrLocalExeDir>UE_*\Engine\Binaries\Linux\UnrealEditor
ExeCopiedMac=   <rrLocalExeDir>UE_*\Engine\Binaries\Mac\UnrealEditor



