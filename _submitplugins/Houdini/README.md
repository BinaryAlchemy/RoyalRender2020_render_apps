________________________________________________
# Houdini To Royal Render

Houdini to Royal Render (htorr) is a python based houdini plugin which enables artist to submit Royal Render jobs directly within Houdini.
It is capable of parsing ROP networks into Royal Render submissions and send these to the farm. 

________________________________________________
# Help files

For more information, please check the rrHelp files section 
Render Apps/Houdini/Submission/Scripted




rrSubmitter:
 * Test Stereo rig
 * Takes
 (* Disable AllowLocalSceneCopy )??
 * Support json format for env, jobVar and SubmitterOptions
 
Gallery:
  Auto-fill temp path
 
PDG:
 * Optional: use MQServer proxy Local and Farm.
        - Farm: Start and keep as job or detact job from process?
                What if rrClient is busy with other task? rrClient setup separate thread for MQServer only?
                What if multiple artists want to submit? => requires different rrClients/MQServers
 * Test more TOP nodes
     - e.g. ffmpeg



