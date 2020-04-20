#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
#
# Last change: %rrVersion%
#
# This include file changes Nuke from a per-Client Installation into a RR shared Executable installation.
# RR Shared Executables work this way:
#     If the client gets a Nuke job, then it will sync all files from the <ExeCopyFromDir> to a <ExeCopyToDir> folder on the local drive.
#     It copies the files as applications have a lot of files. And x machines accessing the same files over and over for each function can slow down the network pretty much.
#     The sync is executed each time the client starts a Nuke job. If the files have not been changed, then no file is copied. If a file was removed, it is removed on the local drive as well.
#
#
#
# Installation steps:
# 1) Copy this file into render_apps\_config\
#     The already existing file C13__Nuke____global.inc has a line to include this file
# 2) Copy your Nuke installation from your workstation C:\Program Files\Nuke9.0v8 into RR\render_apps\renderer_exe\nuke\win_x64\Nuke9.0v8
#     If you use multiple versions, copy all folders that you need. The Clients auto-version change works for shared exe as well
# 3) Delete the documentation folder from each Nuke install (saves to copy 8000+ files for each version)
# 4) Send a restart rrClient app to all clients
# 5) Send a Nuke job. The first start will take some time as the clients have to copy a lot of files.


ExeCopyFromDir = <rrSharedExeDir>
ExeCopyToDir   = <rrLocalExeDir>

ExeCopiedWin=  <rrLocalExeDir>nuke*/Nuke*.exe
ExeCopiedLx=   <rrLocalExeDir>nuke*/Nuke*
ExeCopiedMac=   <rrLocalExeDir>nuke*/Nuke*



