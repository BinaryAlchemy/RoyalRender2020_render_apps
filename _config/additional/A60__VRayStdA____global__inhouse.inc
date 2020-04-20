#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
#
# Last change: %rrVersion%
#
# This include file changes VRay Standalone from a per-Client Installation into a RR shared Executable installation.
# RR Shared Executables work this way:
#     If the client gets a Nuke job, then it will sync all files from the <ExeCopyFromDir> to a <ExeCopyToDir> folder on the local drive.
#     It copies the files as applications have a lot of files. And x machines accessing the same files over and over for each function can slow down the network pretty much.
#     The sync is executed each time the client starts a Nuke job. If the files have not been changed, then no file is copied. If a file was removed, it is removed on the local drive as well.
#
#
#
# Installation steps:
# 1) Copy this file into render_apps\_config\
# 2) Copy VRay to RR\render_apps\renderer_exe\VRay_StdA\win_x64\vray_*
#     Replace * with the vray version.
# 3) Send a restart rrClient app to all clients


ExeCopyFromDir = <rrSharedExeDir>
ExeCopyToDir   = <rrLocalExeDir>

ExeCopiedWin=  <rrLocalExeDir>vray_*\bin\vray.exe
ExeCopiedLx=   <rrLocalExeDir>vray_*/bin/vray
ExeCopiedMac=   <rrLocalExeDir>vray_*/bin/vray



