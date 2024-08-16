	-- Royal Render Plugin script for Max 
	-- Author:  Royal Render, Holger Schoenberger, Binary Alchemy
	-- Last change: %rrVersion%
	-- Copyright (c) Holger Schoenberger - Binary Alchemy
	-- rrInstall_Copy: \MacroScripts\
	-- rrInstall_Delete: \MacroScripts\rrSubmit_3dsMax_2013.0+.mcr





macroScript rrSubmit_new
category:"RoyalRender"
buttontext:"Submit scene                                    (New Submission)"
tooltip:"Submit scene to rrServer (new)"
(
    global rrSubmit_channelIntoSubfolder = false
    global rrSubmit_autoChannelName = true
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_3dsMax_2015.0+_shared.ms" 
)


macroScript rrSubmit_new_subfolder
category:"RoyalRender"
buttontext:"Submit scene, element subfolders   (New Submission)"
tooltip:"Submit scene to rrServer (new)"
(
    global rrSubmit_channelIntoSubfolder = true
    global rrSubmit_autoChannelName = true
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_3dsMax_2015.0+_shared.ms" 
)



macroScript rrSubmit_new_noautoelement
category:"RoyalRender"
buttontext:"Submit scene, no auto element name (New Submission)"
tooltip:"Submit scene to rrServer, no auto element name (new)"
(
    global rrSubmit_channelIntoSubfolder = false
    global rrSubmit_autoChannelName = false
	global rrSubmit_autoSubmit = true
    fileIn "rrSubmit_3dsMax_2015.0+_shared.ms" 
)

			
macroScript rrSubmit
category:"RoyalRender"
buttontext:"Submit scene    (Old Submission)"
tooltip:"Submit scene to Server (old)"
--fn rrSubmit =
(
	struct rrSceneInfo
		(
			MaxVersion,
			SceneFile,
			projectpath,
			Renderer,
			RequiredLicenses,
			imageWidth,
			imageHeight,
			HiddenCommand,
			seqFileOffset,
			seqStart,
			seqEnd,
			seqStep,
			seqFrameset,
			imageFileName,
			imageExt,
			channelFileNames,
			channelExt,
			channelName,
			Cameras,
			Layer,
			cmdOptions
		)
		
	global rrSI= rrSceneInfo()
	

	fn splitFileName &file &ext = 
		(
		for c = file.count to 1 by -1 do 
			if (file[c]==".") then (
				ext= substring file c (file.count - c+1)
				file= substring file 1 (c-1)
				return OK
			)
		)
	

	fn getRRPath =
		(
		cmdLine= "cmd.exe /c echo %RR_ROOT% > " + sysInfo.tempdir + "env.txt"
		DOSCommand cmdLine
		in_text = openfile (sysInfo.tempdir + "env.txt")
		str = ""
		if (not eof in_text) do
			(
			str = readLine in_text
			)
		close in_text
		deleteFile (sysInfo.tempdir + "env.txt")
		if (str != undefined) then (
		    str = trimRight str
			)
		if ((str.count>0) and (str[1]=="%")) then str = ""
		if (str.count==0) then str = "%RRLocationWin%"
		if ((str.count>0) and (str[1]=="%")) then str = ""
		str 
		)
		
	fn getTempFileName=
		(
		rnd= random 1 10000
		rnd= rnd as string
		str=sysInfo.tempdir + "rrSubmitMAX_" + rnd + ".xml"  
		str 
		)

	fn addOutFileName imgN bufferN channelName=
		(
			if  ((imgN ==  undefined)  or  (imgN == "")) then return OK
			imgE=""
			splitFileName &imgN &imgE
			imgN= imgN+bufferN
			if (rrSI.imageFileName=="") then (
				if (channelName=="" and  imgN != "" and (imgN[imgN.count] as integer != undefined)  ) then (
					imgN= imgN+"."
				) 
				imgN= (pathconfig.convertpathtoabsolute imgN)
				rrSI.imageFileName=imgN
				rrSI.imageExt= imgE
				rrSI.channelName= channelName
			) else (
				append rrSI.channelFileNames imgN
				append rrSI.channelExt imgE
			)
		)
		
		
		
		
	fn getCameras_addChildren theChildren  =
		(
			for c in theChildren do
			(
                if ((classof c == TargetCamera) or (classof c == AlembicCamera) or   (classof c == XRefObject) or  (classof c == FreeCamera)  or  (classof c == Physical) or  (classof c == VRayPhysicalCamera) or  (classof c == VRayDomeCamera) or  (classof c == CoronaCam)) then
				(			
					posi = findString c.name "Target"
					if (posi == undefined) then append rrSI.Cameras c.name
				)
			)
		)
	
	fn getCameras =
		(
			camobjs = cameras as array
			rrSI.Cameras =#()
			for c in 1 to camobjs.count do 	(
				if ((classof camobjs[c] == TargetCamera) or (classof camobjs[c] == AlembicCamera) or   (classof camobjs[c] == XRefObject) or  (classof camobjs[c] == FreeCamera)  or  (classof camobjs[c] == Physical) or  (classof camobjs[c] == VRayPhysicalCamera) or  (classof camobjs[c] == VRayDomeCamera) or  (classof camobjs[c] == CoronaCam)) then
					(
					posi = findString camobjs[c].name "Target"
					if (posi == undefined) then append rrSI.Cameras camobjs[c].name
					)
			)
			for i  in 1 to  (xrefs.getXRefFileCount()) do (
				obj = (xrefs.getxrefFile i).tree
				getCameras_addChildren obj.children 
			)		
		)

		
		
		
	fn getSceneInfo=
		(
		rrSI.projectpath = pathConfig.getCurrentProjectFolder()
		rrSI.SceneFile = maxFilePath + maxFileName 	
		ver= maxVersion()
		ver= ver[1]
		rrSI.HiddenCommand = (ver>=10000)
		ver2 = ver - (( ver / 1000)*1000)
		ver = ver/1000
		if (ver>10) do ver=ver-12+2010
		rrSI.MaxVersion= ver as string + "." + ver2 as string

		rrSI.Layer = #()
		maxLayer= sceneStateMgr.getCount()
		for l = 1 to maxLayer do (
			append rrSI.Layer (sceneStateMgr.GetSceneState(l))
		)		
		
		getCameras()
		
		
		
		rrSI.Renderer= classof renderers.production as string
		posi = findString rrSI.Renderer "V_Ray"
		if (posi != undefined) do rrSI.Renderer= "VRay"
		posi = findString rrSI.Renderer "Brazil"
		if (posi != undefined) do rrSI.Renderer= "Brazil"
		posi = findString rrSI.Renderer "Default_Scanline"
		if (posi != undefined) do rrSI.Renderer= ""
		rrSI.RequiredLicenses = rrSI.Renderer

		rrSI.seqFrameset=""

		if (rendTimeType==1) then (
			rrSI.seqStart=animationRange.start.frame  as integer
			rrSI.seqEnd=animationRange.start.frame  as integer
		) else if (rendTimeType==2) then (
			rrSI.seqStart=animationRange.start.frame as integer
			rrSI.seqEnd=animationRange.end.frame  as integer
		) else if (rendTimeType==3) then (
			rrSI.seqStart=rendStart.frame  as integer
			rrSI.seqEnd=rendEnd.frame  as integer
		) else (
			rrSI.seqFrameset= rendPickupFrames
			rrSI.seqStart=animationRange.start.frame
			rrSI.seqEnd=animationRange.end.frame
		)
		
		rrSI.seqStep=rendNThFrame
		rrSI.seqFileOffset=rendFileNumberBase
		rrSI.cmdOptions=""
		rrSI.imageWidth=renderWidth
		rrSI.imageHeight=renderHeight
		rrSI.imageFileName= ""
		rrSI.imageExt= ""
		rrSI.channelName= ""
		rrSI.channelFileNames = #()
		rrSI.channelExt = #()
		if (rendSaveFile) then (
			addOutFileName rendOutputFilename "" ""
		)
		if (rrSI.Renderer== "VRay") then (
			if (renderers.production.adv_irradmap_mode==6) then (
				addOutFileName renderers.production.adv_irradmap_autoSaveFileName "" "irrMap"
			)
		)
		theManager = maxOps.GetRenderElementMgr(0)
		if (rrSI.Renderer== "VRay" and renderers.production.output_on and renderers.production.adv_irradmap_mode!=6) then (
			rrSI.cmdOptions= rrSI.cmdOptions + " \"TileFrame=0~4\"  "
			if (renderers.production.output_on) then (
				if (not renderers.production.output_getsetsfrommax) then (
					rrSI.imageWidth=renderers.production.output_width
					rrSI.imageHeight=renderers.production.output_height
				)
				if (renderers.production.output_splitgbuffer) then (
					fileNameBase= renderers.production.output_splitfilename
					if (fileNameBase=="") then (
						messageBox "You have not set a render output in VRay: FrameBuffer: Split render channels ." title:"Royal Render" 
						return "No render output defined."
					)
					if (theManager.GetElementsActive()==true) then (
						for n = (theManager.NumRenderElements()- 1) to 0 by -1 do	 (
							element= theManager.GetRenderElement n
							if (not element.enabled) then continue
							elemName = element.elementName 
							posi = findString elemName "#"
							if (posi != undefined) then continue 
							elemClass=(element as string)
							posc = findString elemClass ":"
							elemClass= substring elemClass (posc+1) -1
							elemClassStart=substring  elemClass 1 4
							if (elemClassStart=="VRay" or elemClass=="MultiMatteElement" ) then (
								elemName = "." + elemName + "."
								elemName = substituteString elemName " " "_"
								addOutFileName fileNameBase elemName element.elementName
							) else (
								imgName = theManager.GetRenderElementFileName n
								addOutFileName imgName "" element.elementName
							)
						)
					)
					if (renderers.production.output_splitAlpha) then (
						addOutFileName fileNameBase ".Alpha." "vrayAlpha"
					)
					if (renderers.production.output_splitRGB) then (
						addOutFileName fileNameBase ".RGB_color." "vrayRGB"
					)
				) else (
					--VRay. But no VFB "save seperate render channels"
					if (theManager.GetElementsActive()==true) then (
						for n = (theManager.NumRenderElements()- 1) to 0 by -1 do
						(
							element= theManager.GetRenderElement n
							if (not element.enabled) then continue
							elemName = element.elementName 
							posi = findString elemName "#"
							if (posi == undefined) then continue 
							elemClass=(element as string)
							posc = findString elemClass ":"
							elemClass= substring elemClass (posc+1) -1
							elemClassStart=substring  elemClass 1 4
							if (elemClassStart!="VRay") then (							
								imgName = theManager.GetRenderElementFileName n
								addOutFileName imgName "" element.elementName
							)
						)
					)
				)
				if (renderers.production.output_saveRawFile) then (
					fileNameBase= renderers.production.output_rawFileName
					addOutFileName fileNameBase "" "vrayRaw"
				)
			)
		) else (
			--VRay Frame Buffer NOT enabled 
			if (theManager.GetElementsActive()==true) then (
				for n = (theManager.NumRenderElements()- 1) to 0 by -1 do
				(
					element= theManager.GetRenderElement n
					if (not element.enabled) then continue
					imgName = theManager.GetRenderElementFileName n
					addOutFileName imgName "" element.elementName
				)
			)
		)

		PHXSimulatorCheck = false
		for o in geometry where classof o == PHXSimulator do PHXSimulatorCheck = true
		if (PHXSimulatorCheck) then (
			rrSI.cmdOptions=rrSI.cmdOptions + " \"AllowLocalSceneCopy=0~0\""
                )

		if (IDisplayGamma.colorCorrectionMode== #gamma) then (
			tmpStrg1=fileInGamma as string
			tmpStrg2=fileOutGamma as string
			tmpStrg1 = substituteString tmpStrg1 "." "<dec>"
			tmpStrg2 = substituteString tmpStrg2 "." "<dec>"
			rrSI.cmdOptions=rrSI.cmdOptions + " \"COGammaCorrect=0~0\"  \"AdditionalCommandlineParam=0~0~ -gammaCorrection:1 -gammaValueIn:" + tmpStrg1 + " -gammaValueOut:" + tmpStrg2 +"\" "
			if (fileOutGamma==1.0)  then (
				rrSI.cmdOptions= rrSI.cmdOptions + " \"PreviewGamma2.2=1~1\"  "
			)
		)		
	)

	fn WriteNodeToFile out_text nam val =
		(	
		val = val as string
		val = substituteString val "&" "&amp;"
		val = substituteString val (bit.intAsChar(228)) "&#228;"
		val = substituteString val (bit.intAsChar(196)) "&#196;"
		val = substituteString val (bit.intAsChar(246)) "&#246;"
		val = substituteString val (bit.intAsChar(214)) "&#214;"
		val = substituteString val (bit.intAsChar(252)) "&#252;"
		val = substituteString val (bit.intAsChar(220)) "&#220;"
		val = substituteString val (bit.intAsChar(223)) "&#223;"
		val = substituteString val "<" "&lt;"
		val = substituteString val ">" "&gt;"
		val = substituteString val "\"" "&quot;"
		val = substituteString val "'" "&apos;"
		format "\t<%>%</%>\n" nam val nam to:out_text
		)	
		
		
	fn WriteLayerToFile out_text lay cam active =
		(	
		format "<Job>\n"  to:out_text 
        WriteNodeToFile out_text "rrSubmitterPluginVersion" "%rrVersion%"
		WriteNodeToFile out_text "SceneOS" "win"
		WriteNodeToFile out_text "Software" "3dsMax" 
		WriteNodeToFile out_text "Layer" lay 
		WriteNodeToFile out_text "Camera" cam 
		WriteNodeToFile out_text "IsActive" active
		WriteNodeToFile out_text "Version" rrSI.MaxVersion
		WriteNodeToFile out_text "Scenename" rrSI.SceneFile
		WriteNodeToFile out_text "SceneDatabaseDir" rrSI.projectpath
		WriteNodeToFile out_text "Renderer" rrSI.Renderer
		WriteNodeToFile out_text "RequiredLicenses" rrSI.RequiredLicenses
		WriteNodeToFile out_text "SeqStart" rrSI.seqStart
		WriteNodeToFile out_text "SeqEnd" rrSI.seqEnd
		WriteNodeToFile out_text "SeqStep" rrSI.seqStep
		WriteNodeToFile out_text "SeqFileOffset" rrSI.seqFileOffset
		WriteNodeToFile out_text "SeqFrameSet" rrSI.seqFrameset
		WriteNodeToFile out_text "ImageWidth" rrSI.imageWidth
		WriteNodeToFile out_text "ImageHeight" rrSI.imageHeight
		WriteNodeToFile out_text "Imagefilename" rrSI.imageFileName
		WriteNodeToFile out_text "ImageExtension" rrSI.imageExt
		WriteNodeToFile out_text "ImageFramePadding" 4
		WriteNodeToFile out_text "Channel" rrSI.channelName
		for c = 1 to rrSI.channelFileNames.count do (
			WriteNodeToFile out_text "ChannelFilename" rrSI.channelFileNames[c]
			WriteNodeToFile out_text "ChannelExtension" rrSI.channelExt[c]
		)

		format "</Job>\n"  to:out_text 
		)	
		
-----------------------------------------------------------------------
-- Function body start
-----------------------------------------------------------------------

	print "Royal Render (old) %rrVersion%"
	-- Get all data
	if (maxFileName.count==0) then
		(
		messageBox "Scene was never saved." title:"Royal Render" 
		return "Scene was never saved."
		)
	renderSceneDialog.commit()
	if (getSaveRequired()) then (
		ret=yesNoCancelBox "The Scene has been modified.\nDo you want to save your changes?" title:"Royal Render"
		if (ret==#yes) then (
			saveMaxFile(maxFilePath + maxFileName) 
		)
		if (ret==#cancel) then (
			return "Canceled"
		)
	)
	getSceneInfo()
	if (rrSI.imageFileName=="") then (
		messageBox "You have not defined a render output for your scene." title:"Royal Render" 
		return "No render output defined."
	)
	if (getRenderType()!=#view) then (
		if (not (queryBox "You have enabled Region in your render settings.\nContinue submission?" title:"Royal Render") ) then (
			return "region"
		)
	)

	-- Write XML file
	XMLfileName=getTempFileName()
	out_text = createFile XMLfileName
	format "<rrJob_submitFile syntax_version=\"6.0\">\n"  to:out_text 
	format "<DeleteXML>1</DeleteXML>\n"  to:out_text 
	WriteNodeToFile out_text "SubmitterParameter" rrSI.cmdOptions

	if (rrSI.Layer.count>0) then  (
		WriteLayerToFile out_text "" "" 0
		for c = 1 to rrSI.Cameras.count do
			(
				WriteLayerToFile out_text "" rrSI.Cameras[c] 0
			)
		lp=-1
		for p=rrSI.imageFileName.count  to 1 by -1 do (
			if (rrSI.imageFileName[p] == "\\") then (
				lp=p
				exit
				)
			)
		if (lp >-1) then (
			rrSI.imageFileName= replace rrSI.imageFileName lp 1 "\\<Layer>\\"
			)
		for l = 1 to rrSI.Layer.count do (
			WriteLayerToFile out_text rrSI.Layer[l] "" 0
			for c = 1 to rrSI.Cameras.count do
				(
					WriteLayerToFile out_text rrSI.Layer[l] rrSI.Cameras[c] 0
				)	
			)
	) else (
		WriteLayerToFile out_text "" "" 1
		for c = 1 to rrSI.Cameras.count do
			(
			WriteLayerToFile out_text "" rrSI.Cameras[c] 0
			)
		)
	format "</rrJob_submitFile>\n"  to:out_text 
	close out_text
	
	
	-- start submitter
	RR_ROOT=GetRRPath()
	if (RR_ROOT.count==0) then
		(
		messageBox "No RR_Root variable defined. Please reinstall." title:"Royal Render" 
		return "No RR_Root variable defined. Please reinstall."
		)	
	cmdLine="\"" + RR_ROOT + "\\win__rrSubmitter.bat\"  '" + XMLfileName+"'"
	DOSCommand cmdLine
)




macroScript rrSubmitRPManager
category:"RoyalRender"
buttontext:"Submit RPM Scene   (read RP-Manager passes)"
tooltip:"Submit scene with RP-Manager passes to Server"
--fn rrSubmitRPManager=
(
	struct rrSceneInfo
		(
			MaxVersion,
			SceneFile,
			projectpath,
			Renderer,
			RequiredLicenses,
			imageWidth,
			imageHeight,
			HiddenCommand,
			seqFileOffset,
			seqStart,
			seqEnd,
			seqStep,
			seqFrameset,
			imageFileName,
			imageExtension,
			channelFileNames,
			channelExt,
			Cameras,
			Layer,
			cmdOptions
		)
	global rrSI= rrSceneInfo()

	fn splitFileName &file &ext = 
		(
		for c = file.count to 1 by -1 do 
			if (file[c]==".") then (
				ext= substring file c (file.count - c+1)
				file= substring file 1 (c-1)
				return OK
			)
		)
	

	fn getRRPath =
		(
		cmdLine= "cmd.exe /c echo %RR_ROOT% > " + sysInfo.tempdir + "env.txt"
		DOSCommand cmdLine
		in_text = openfile (sysInfo.tempdir + "env.txt")
		str = ""
		if (not eof in_text) do
			(
			str = readLine in_text
			)
		close in_text
		deleteFile (sysInfo.tempdir + "env.txt")
		if (str != undefined) then (
		    str = trimRight str
			)
		if ((str.count>0) and (str[1]=="%")) then str = ""
		if (str.count==0) then str = "%RRLocationWin%"
		if ((str.count>0) and (str[1]=="%")) then str = ""
		str 
		)
		
	fn getTempFileName=
		(
		rnd= random 1 10000
		rnd= rnd as string
		str=sysInfo.tempdir + "rrSubmitMAX_" + rnd + ".xml"  
		str 
		)		
		
	fn getCameras_addChildren theChildren  =
		(
			for c in theChildren do
			(
				if ((classof c == TargetCamera) or   (classof c == XRefObject) or  (classof c == FreeCamera)  or  (classof c == VRayPhysicalCamera) or  (classof c== VRayDomeCamera)) then
				(			
					posi = findString c.name "Target"
					if (posi == undefined) then append rrSI.Cameras c.name
				)
			)
		)
	
	fn getCameras = 
		(
			camobjs = cameras as array
			rrSI.Cameras =#()
			for c in 1 to camobjs.count do 	(
				if ((classof camobjs[c] == TargetCamera) or (classof camobjs[c] == AlembicCamera) or   (classof camobjs[c] == XRefObject) or  (classof camobjs[c] == FreeCamera)  or  (classof camobjs[c] == Physical) or  (classof camobjs[c] == VRayPhysicalCamera) or  (classof camobjs[c] == VRayDomeCamera)) then
					(
					posi = findString camobjs[c].name "Target"
					if (posi == undefined) then append rrSI.Cameras camobjs[c].name
					)
			)
			for i  in 1 to  (xrefs.getXRefFileCount()) do (
				obj = (xrefs.getxrefFile i).tree
				getCameras_addChildren obj.children 
			)		
		)
		
	fn getSceneInfo=
		(
		rrSI.projectpath = pathConfig.getCurrentProjectFolder()
		rrSI.SceneFile = maxFilePath + maxFileName 	
		ver= maxVersion()
		ver= ver[1]
		rrSI.HiddenCommand = (ver>=10000)
		ver2 = ver - (( ver / 1000)*1000)
		ver = ver/1000
		if (ver>10) do ver=ver-12+2010
		rrSI.MaxVersion= ver as string +"." + ver2 as string
		getCameras()
		rrSI.Renderer= classof renderers.production as string
		posi = findString rrSI.Renderer "V_Ray"
		if (posi != undefined) do rrSI.Renderer= "VRay"
		posi = findString rrSI.Renderer "Brazil"
		if (posi != undefined) do rrSI.Renderer= "Brazil"
		posi = findString rrSI.Renderer "Default_Scanline"
		if (posi != undefined) do rrSI.Renderer= ""
 		rrSI.RequiredLicenses = rrSI.Renderer

		rrSI.seqFrameset=""
		
		if (rendTimeType==1) then (
			rrSI.seqStart=animationRange.start.frame  as integer
			rrSI.seqEnd=animationRange.start.frame  as integer
		) else if (rendTimeType==2) then (
			rrSI.seqStart=animationRange.start.frame as integer
			rrSI.seqEnd=animationRange.end.frame  as integer
		) else if (rendTimeType==3) then (
			rrSI.seqStart=rendStart.frame  as integer
			rrSI.seqEnd=rendEnd.frame  as integer
		) else (
			rrSI.seqFrameset= rendPickupFrames
			rrSI.seqStart=animationRange.start.frame
			rrSI.seqEnd=animationRange.end.frame
		)

		rrSI.seqStep=rendNThFrame
		rrSI.seqFileOffset=rendFileNumberBase
		rrSI.imageWidth= #()
		rrSI.imageHeight= #()
		if (not rendSaveFile) then rendSaveFile= true
		rrSI.imageFileName=rendOutputFilename
		

		rrSI.channelFileNames = #()
		rrSI.channelExt = #()
		rrSI.cmdOptions=""
		if (IDisplayGamma.colorCorrectionMode== #gamma) then (
			tmpStrg1=fileInGamma as string
			tmpStrg2=fileOutGamma as string
			tmpStrg1 = substituteString tmpStrg1 "." "<dec>"
			tmpStrg2 = substituteString tmpStrg2 "." "<dec>"
			rrSI.cmdOptions=" \"COGammaCorrect=0~0\"  \"AdditionalCommandlineParam=0~0~ -gammaCorrection:1 -gammaValueIn:" + tmpStrg1 + " -gammaValueOut:" + tmpStrg2 +"\" "
			if (fileOutGamma==1.0)  then (
				rrSI.cmdOptions= rrSI.cmdOptions + " \"PreviewGamma2.2=1~1\"  "
			)
		)
	)

	fn addOutFileName imgN bufferN channelName=
		(
			if  ((imgN ==  undefined)  or  (imgN == "")) then return OK
			imgE=""
			splitFileName &imgN &imgE
			imgN= imgN+bufferN
			if (rrSI.imageFileName=="") then (
				if (channelName!="" and  imgN != "" and (imgN[imgN.count] as integer != undefined)  ) then (
					imgN= imgN+bufferN+"."
				) 
                imgN= (pathconfig.convertpathtoabsolute imgN)
				rrSI.imageFileName=imgN
				rrSI.imageExt= imgE
				rrSI.channelName= channelName
			) else (
				append rrSI.channelFileNames imgN
				append rrSI.channelExt imgE
			)
		)


		
	fn get_RPM_layer = (
		rrSI.Renderer="RPManager"
		rrSI.Cameras =#()
		rrSI.Layer = #()
		rrSI.seqStart= #()
		rrSI.seqEnd= #()
		rrSI.seqStep= #()
		rrSI.seqFrameset= #()
		rrSI.seqFileOffset= 0
		rrSI.imageFileName= #()
		rrSI.imageExtension= #()
		rrSI.imageWidth= #()
		rrSI.imageHeight= #()
		rrSI.channelFileNames=#()
		currentPass= RPMdata.GetPassSelection()
		
		
		maxLayer= RPMdata.GetPassCount()
		if (maxLayer!=0) then (
			callbacks.removescripts id:#RR_RPMPassChange
			callbacks.addscript #filepostopen "try(filein \"C:\\\\RR_LocalData\\\\RR_RPMPassChange.ms\" ) catch()" id:#RR_RPMPassChange persistent:true
			for l = 1 to maxLayer do (
				pass= RPMdata.GetPassName(l)
				SRange=RPMdata.GetPassRange(l)
				fOut1Add=""
				fOut2Add=""
				fOut3Add=""
				fUse1=false
				fUse2=false
				fUse3=false
				fCam1=RPMdata.GetPassCamera(l)
				fCam2=RPMdata.getPassSecondCamera(l)
				fCam3=RPMdata.getPassThirdCamera(l)
				seqFrameset=""

				if (classof SRange == Point3) then (
					seqStart= (SRange.x as integer)
					seqEnd= (SRange.y as integer)
					seqStep= (SRange.z as integer)
				)  else (
					seqStart= (SRange as integer)
					seqEnd= (SRange as integer)
					seqStep= 1
					) 
				
				
				CamInfo= RPMdata.getPassCameraExtraInfo l
				if ((CamInfo[1]=="Both") or (CamInfo[1]=="Render Only") ) then (
					fOut1Add=CamInfo[2] as string
					fUse1=true
				)
				CamInfo= RPMdata.getPassSecondCameraExtraInfo l
				if ((CamInfo[1]=="Both") or (CamInfo[1]=="Render Only") ) then (
						fOut2Add=CamInfo[2] as string
						fUse2=true
				)
				CamInfo= RPMdata.getPassThirdCameraExtraInfo l
				if ((CamInfo[1]=="Both") or (CamInfo[1]=="Render Only") ) then (
						fOut3Add=CamInfo[2] as string
						fUse3=true
				)
				useSubDirs=RPMdata.getOutputSetupData index:42

				fOut= RPMdata.GetPassOutputPath(l)
				fOutDir= ""
				fOutName= ""
				fOutExt=""
				fOut=filterString fOut "."  splitEmptyTokens:true
				fOutName=fOut[1]
				for i = 2 to fOut.count-1 do (
					fOutName=fOutName+ "." + fOut[i]
				)
				fOutExt="."+fOut[fOut.count]
				fOut=filterString fOutName "\\" splitEmptyTokens:true
				for i = 1 to fOut.count-1 do (
					fOutDir=fOutDir+ fOut[i]+"\\"
				)
				fOutName=fOut[fOut.count]	
				
					
				if (useSubDirs) then (
					if (fUse1) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam1.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut1Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOut1Add+"\\"+fOutName+fOut1Add
							append rrSI.imageFileName comb
						)
					) 
					if (fUse2) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam2.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut2Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOut2Add+"\\"+fOutName+fOut2Add
							append rrSI.imageFileName comb
						)
					) 
					if (fUse3) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam3.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut3Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOut3Add+"\\"+fOutName+fOut3Add
							append rrSI.imageFileName comb
						)
					) 
				) else (
					if (fUse1) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam1.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut1Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOutName+fOut1Add
							append rrSI.imageFileName comb
						)
					) 
					if (fUse2) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam2.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut2Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOutName+fOut2Add
							append rrSI.imageFileName comb
						)
					) 
					if (fUse3) then (
						append rrSI.imageExtension fOutExt
						append rrSI.Cameras fCam3.name
						append rrSI.Layer pass
						append rrSI.seqStart seqStart
						append rrSI.seqEnd seqEnd
						append rrSI.seqStep seqStep
						append rrSI.seqFrameset seqFrameset
						if (fOut3Add=="") then (
							comb=fOutDir+fOutName+fOutExt
							append rrSI.imageFileName comb
						) else (
							comb=fOutDir+fOutName+fOut3Add
							append rrSI.imageFileName comb
						)
					) 
				)
				
				RPMData.RMRestValues(l)
				
				if (rrSI.Renderer== "VRay") then (
					if (renderers.production.adv_irradmap_mode==6) then (
						rrSI.imageFileName=renderers.production.adv_irradmap_autoSaveFileName
					)
				)

				append rrSI.imageWidth renderWidth
				append rrSI.imageHeight renderHeight
				append rrSI.channelFileNames #()
				append rrSI.channelExt #()
				theManager = maxOps.GetRenderElementMgr(0)
				for n = 0 to (theManager.numrenderelements()- 1) do
				(
					imgName = theManager.GetRenderElementFileName n
					if (imgName=="") then (
						imgName= fOutDir+fOutName+"_" + (theManager.GetRenderElement n).elementName + fOutExt
					) 
					imageExt=""
					splitFileName &imgName &imageExt
					append rrSI.channelFileNames[l] imgName
					append rrSI.channelExt[l] imageExt

				)
			)
		)
		RPMData.RMRestValues(currentPass[1])
	)
	
	fn WriteNodeToFile out_text name val =
		(	
		val = val as string
		val = substituteString val "&" "&amp;"
		val = substituteString val (bit.intAsChar(228)) "&#228;"
		val = substituteString val (bit.intAsChar(196)) "&#196;"
		val = substituteString val (bit.intAsChar(246)) "&#246;"
		val = substituteString val (bit.intAsChar(214)) "&#214;"
		val = substituteString val (bit.intAsChar(252)) "&#252;"
		val = substituteString val (bit.intAsChar(220)) "&#220;"
		val = substituteString val (bit.intAsChar(223)) "&#223;"
		val = substituteString val "<" "&lt;"
		val = substituteString val ">" "&gt;"
		val = substituteString val "\"" "&quot;"
		val = substituteString val "'" "&apos;"
		format "\t<%>%</%>\n" name val name to:out_text
		)	
		
		
	fn WriteLayerToFile out_text layerNumber=
		(	
		format "<Job>\n"  to:out_text 
        WriteNodeToFile out_text "rrSubmitterPluginVersion" "%rrVersion%"
		WriteNodeToFile out_text "SceneOS" "win"
		WriteNodeToFile out_text "Software" "3dsMax" 
		WriteNodeToFile out_text "Layer" rrSI.Layer[layerNumber]
		WriteNodeToFile out_text "Camera" rrSI.Cameras[layerNumber]
		WriteNodeToFile out_text "IsActive" 1
		WriteNodeToFile out_text "Version" rrSI.MaxVersion
		WriteNodeToFile out_text "Scenename" rrSI.SceneFile
		WriteNodeToFile out_text "SceneDatabaseDir" rrSI.projectpath
		WriteNodeToFile out_text "Renderer" "RPManager"
		WriteNodeToFile out_text "RequiredLicenses" rrSI.RequiredLicenses
		WriteNodeToFile out_text "SeqStart" rrSI.seqStart[layerNumber]
		WriteNodeToFile out_text "SeqEnd" rrSI.seqEnd[layerNumber]
		WriteNodeToFile out_text "SeqStep" rrSI.seqStep[layerNumber]
		WriteNodeToFile out_text "SeqFileOffset" rrSI.seqFileOffset
		WriteNodeToFile out_text "SeqFrameSet" rrSI.seqFrameset[layerNumber]
		WriteNodeToFile out_text "ImageWidth" rrSI.imageWidth[layerNumber]
		WriteNodeToFile out_text "ImageHeight" rrSI.imageHeight[layerNumber]
		WriteNodeToFile out_text "Imagefilename" rrSI.imageFileName[layerNumber]
		WriteNodeToFile out_text "ImageExtension" rrSI.imageExtension[layerNumber]
		WriteNodeToFile out_text "ImageFramePadding" 4
		for c = 1 to rrSI.channelFileNames[layerNumber].count do (
			WriteNodeToFile out_text "ChannelFilename" rrSI.channelFileNames[layerNumber][c]
                        WriteNodeToFile out_text "ChannelExtension" rrSI.channelExt[layerNumber][c]
		)
		format "</Job>\n"  to:out_text 
		)	
		
-----------------------------------------------------------------------
-- Function body start
-----------------------------------------------------------------------

	print "Royal Render (RPM) %rrVersion%"
	-- Get all data
	if (maxFileName.count==0) then
		(
		messageBox "Scene was never saved." title:"Royal Render" 
		return "Scene was never saved."
		)
		
	renderSceneDialog.commit()
	getSceneInfo()
	get_RPM_layer()
	if (rrSI.Layer.count==0) then (
		messageBox "No RP-Manager pass found." title:"Royal Render" 
		return "No RP-Manager pass found."	
	)
	saveMaxFile(maxFilePath + maxFileName)  -- save required because of RPM callback
	if (getRenderType()!=#view) then (
		if (not (queryBox "You have enabled Region in your render settings.\nContinue submission?" title:"Royal Render") ) then (
			return "region"
		)
	)

	-- Write XML file
	XMLfileName=getTempFileName()
	out_text = createFile XMLfileName
	format "<rrJob_submitFile syntax_version=\"6.0\">\n"  to:out_text 
	format "<DeleteXML>1</DeleteXML>\n"  to:out_text 
	WriteNodeToFile out_text "SubmitterParameter" rrSI.cmdOptions

	for c = 1 to rrSI.Cameras.count do
		(
		WriteLayerToFile out_text c
		)
	format "</rrJob_submitFile>\n"  to:out_text 
	close out_text
	
	
	-- start submitter
	RR_ROOT=GetRRPath()
	if (RR_ROOT.count==0) then
		(
		messageBox "No RR_Root variable defined. Please reinstall." title:"Royal Render" 
		return "No RR_Root variable defined. Please reinstall."
		)	
	cmdLine="\"" + RR_ROOT + "\\win__rrSubmitter.bat\"  '" + XMLfileName+"'"
	DOSCommand cmdLine
)


