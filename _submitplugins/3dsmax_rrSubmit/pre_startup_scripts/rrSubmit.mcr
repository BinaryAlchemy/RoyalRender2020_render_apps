	-- Royal Render Plugin script for Max 
	-- Author:  Royal Render, Holger Schoenberger, Binary Alchemy
	-- Last change: %rrVersion%
	-- Copyright (c) Holger Schoenberger - Binary Alchemy



macroScript rrSubmit_new
category:"RoyalRender"
buttontext:"Submit scene"
tooltip:"Submit scene to Royal Render"
IconName:"rrSubmit.png"
(
    global rrSubmit_channelIntoSubfolder = false
    global rrSubmit_autoChannelName = true
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_shared.ms" 
)


macroScript rrSubmit_new_subfolder
category:"RoyalRender"
buttontext:"Submit scene, element subfolders"
tooltip:"Submit scene to Royal Render, create subfolders for elements"
IconName:"rrSubmit.png"
(
    global rrSubmit_channelIntoSubfolder = true
    global rrSubmit_autoChannelName = true
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_shared.ms" 
)



macroScript rrSubmit_new_noautoelement
category:"RoyalRender"
buttontext:"Submit scene, no auto element name"
tooltip:"Submit scene to Royal Render, no auto element name"
IconName:"rrSubmit.png"
(
    global rrSubmit_channelIntoSubfolder = false
    global rrSubmit_autoChannelName = false
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_shared.ms" 
)

