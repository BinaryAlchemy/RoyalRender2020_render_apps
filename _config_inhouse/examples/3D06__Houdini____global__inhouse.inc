#
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
#
# Last change: %rrVersion%
#
# This include file changes this app from a per-Client Installation into a RR shared Executable installation.
# RR Shared Executables work this way:
#     If the client gets a job, then it will sync the application to the local drive.
#     It copies the app to the local drive as many machines accessing the same files over and over for each function can slow down the network pretty much.
#     The sync is executed each time the client starts a  job. 
#     If the files have not been changed, then no file is copied. If a file was removed, it is removed on the local drive as well.
#
#
#
# Installation steps:
# 1) Copy this file into render_apps\_config_inhouse\
# 2) Send a "restart rrClient app" command via rrControl to all active clients. (To reload the config)
# 3) Copy your application installation 
#      from your workstation c:\Program Files\Side Effects Software\Houdini 20.5.332\ 
#      into RR\render_apps\renderer_exe\houdini\win_x64\Houdini 20.5.332
#     If you use multiple versions, copy all versions that you need. The Clients auto-version change works for shared exe as well
#
#     Note that it is possible to get an information from the rrClient about the right path.
#     If you skip this step, then the renderlog in step 5 will tell you the right path.
#
# 4) Optional: Reduce app size
#    In case of Houdini we have not seen folder that you can easily remove
# 5) Send a job. The first start will take some time as the clients have to copy a lot of files.


ExeCopyFromDir = <rrSharedExeDir>
ExeCopyToDir   = <rrLocalExeDir>

ExeCopiedWin=  <rrLocalExeDir>Houdini*/bin/hython.exe
ExeCopiedLx=   <rrLocalExeDir>Houdini*/bin/hython
ExeCopiedMac=   <rrLocalExeDir>Houdini*/Resources/bin/hython-bin



