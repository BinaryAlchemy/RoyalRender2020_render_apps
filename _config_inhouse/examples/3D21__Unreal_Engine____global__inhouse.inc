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
# 2) Copy your Blender installation from your workstation c:\Program Files\Epic Games\UE_5 into RR\render_apps\renderer_exe\Unreal Engine\win_x64\UE_5
#     Of course you need to modify the version 2.81 with the version you use.
#     If you use multiple versions, copy all folders that you need. The Clients auto-version change works for shared exe as well
# 3) Send a restart rrClient app to all clients
# 4) Send an Unreal job. The first start will take some time as the clients have to copy a lot of files.


ExeCopyFromDir = <rrSharedExeDir>
ExeCopyToDir   = <rrLocalExeDir>

ExeCopiedWin=  <rrLocalExeDir>UE_*\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
ExeCopiedLx=   <rrLocalExeDir>UE_*\Engine\Binaries\Linux\UnrealEditor
ExeCopiedMac=   <rrLocalExeDir>UE_*\Engine\Binaries\Mac\UnrealEditor



