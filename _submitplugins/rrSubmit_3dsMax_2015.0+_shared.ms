    -- Royal Render Plugin script for Max 
    -- Author:  Royal Render, Binary Alchemy
    -- Last change: %rrVersion%
    -- Copyright (c) Holger Schoenberger - Binary Alchemy
    -- rrInstall_Copy: \MacroScripts\


struct rrSceneInfo_class
        (
            MaxVersion,
            SceneFile,
            projectpath,
            Renderer,
            RendererType,
            RequiredLicenses,
            imageWidth,
            imageHeight,
            HiddenCommand,
            seqFileOffset,
            seqStart,
            seqEnd,
            seqStep,
            seqFrameset,
            imageFileNameBase,
            channelFileNames,
            channelNames,
            channelIsFullPath,
            channelExt,
            outimageFileName,
            outimageExt,
            outimageChannelName,
            outchannelFileNames,
            outchannelExt,
            Cameras,
            Layer,
            cmdOptions
        )


struct rrSubmit_scriptrender 
(
        
    rrSI= rrSceneInfo_class()
  

    ,fn splitFileName &file &ext = 
        (
        for c = file.count to 1 by -1 do 
            if (file[c]==".") then (
                ext= substring file c (file.count - c+1)
                file= substring file 1 (c-1)
                return OK
            )
        )
        
    ,fn splitFileDir &dir &file = 
        (
        for c = dir.count to 1 by -1 do 
            if ((dir[c]=="\\") or (dir[c]=="/")) then (
                file= substring dir (c+1) (dir.count - c)
                dir= substring dir 1 (c)
                return OK
            )
        )        
    

    ,fn getRRPath =
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
        
    ,fn getTempFileName=
        (
        rnd= random 1 10000
        rnd= rnd as string
        str=sysInfo.tempdir + "rrSubmitMAX_" + rnd + ".xml"  
        str 
        )



    ,fn addOutFileChannel rrJob channelFileName channelName channelIsFullPath channelExt=
        (
            append rrJob.channelNames channelName
            append rrJob.channelFileNames channelFileName
            append rrJob.channelIsFullPath channelIsFullPath
            append rrJob.channelExt channelExt
        )
        
        
        
        
    ,fn getCameras_addChildren theChildren  =
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
    
    ,fn getCameras =
        (
            camobjs = cameras as array
            rrSI.Cameras =#()
            for c in 1 to camobjs.count do     (
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
        
    ,fn setRenderLicense rrJob=
        (
            posi = findString rrJob.Renderer "V_Ray_GPU"
            if (posi != undefined) do (rrJob.Renderer= "VRay"; rrJob.RendererType= "GPU")
            posi = findString rrJob.Renderer "V_Ray"
            if (posi != undefined) do rrJob.Renderer= "VRay"
            posi = findString rrJob.Renderer "Brazil"
            if (posi != undefined) do rrJob.Renderer= "Brazil"
            posi = findString rrJob.Renderer "Default_Scanline"
            if (posi != undefined) do rrJob.Renderer= ""
            posi = findString rrJob.Renderer "Redshift"
            if (posi != undefined) do rrJob.Renderer= "redshift"
            posi = findString rrJob.Renderer "Octane"
            if (posi != undefined) do rrJob.Renderer= "Octane"

            rrJob.RequiredLicenses = rrJob.Renderer
        )
        
    ,fn getSceneInfo autoChannelName=
        (
        rrSI.projectpath = pathConfig.getCurrentProjectFolder()
        rrSI.SceneFile = maxFilePath + maxFileName     
        fileversinfo = dotnetclass "System.Diagnostics.FileVersionInfo"
        myFI = fileversinfo.GetVersionInfo (pathConfig.appendPath (pathConfig.GetDir #maxroot) "3dsmax.exe")
        versions = filterString myFI.FileVersion "."
        ver= versions[1] as integer 
        ver= ver-12 + 2010
        rrSI.MaxVersion= ver as string + "." + versions[2] as string
        rrSI.HiddenCommand = true

        rrSI.Layer = ""
        
        getCameras()
        
        
        
        rrSI.Renderer= classof renderers.current as string
        setRenderLicense rrSI

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
        rrSI.imageFileNameBase= ""
        rrSI.channelFileNames = #()
        rrSI.channelNames = #()
        rrSI.channelIsFullPath = #()
        rrSI.channelExt = #()

        PHXSimulatorCheck = false
        for o in geometry where classof o == PHXSimulator do PHXSimulatorCheck = true
        if (PHXSimulatorCheck) then (
            rrSI.cmdOptions=rrSI.cmdOptions + " \"AllowLocalSceneCopy=0~0\""
        )
        
        if (autoChannelName) then (
            rrSI.cmdOptions=rrSI.cmdOptions + " \"COAutoElementFileName=1~1\""
        ) else (
            rrSI.cmdOptions=rrSI.cmdOptions + " \"COAutoElementFileName=0~0\""
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
        
        
        if (rrSI.Renderer== "VRay") then (
            vray_settings = renderers.current
            if rrSI.RendererType == "GPU" then (
                vray_settings = renderers.current.V_Ray_settings
            )
            if ((vray_settings.gi_on) and (vray_settings.adv_irradmap_mode==6)) then (
                rrSI.imageFileNameBase=vray_settings.adv_irradmap_autoSaveFileName 
                addOutFileChannel rrSI "" "prePass" true ""
                return "done"
            )
        )
        
        

        theManager = maxOps.GetRenderElementMgr(0)
        theManagerActive= theManager.GetElementsActive()
        theManagerNum= theManager.NumRenderElements()
        theManagerActive = (theManagerActive and (theManagerNum>0))
        vrayFBused= (rrSI.Renderer== "VRay" and vray_settings.output_on)
        
        if ( vrayFBused  \
            and (not vray_settings.output_saveRawFile) \
            and (not vray_settings.output_splitgbuffer)
        ) then (
                theManagerActive=false
            )
            
        if ( vrayFBused  \
            and (not vray_settings.output_saveRawFile) \
            and (not theManagerActive)  \
            and (not (vray_settings.output_splitgbuffer and (vray_settings.output_splitAlpha or vray_settings.output_splitRGB)))
            ) then (
            vrayFBused=false
        )
        
        
        if (vrayFBused) then (
                --VRay Framebuffer enabled and used to save files
                if (((not rendSaveFile) or (rendOutputFilename=="")) and (not vray_settings.output_splitgbuffer)) then theManagerActive=false

                if (not vray_settings.output_getsetsfrommax) then (
                    rrSI.imageWidth=vray_settings.output_width
                    rrSI.imageHeight=vray_settings.output_height
                )
                
                if (rendSaveFile) then (
                    -- Small issue with RR: You cannot use different base file names for the VRay elements and the 3dsMax main output file save
                    -- so we use the VRay element base (set later in this script) as 3dsmax output file save.
                    imgFile=rendOutputFilename
                    splitFileName &imgFile &imgExt
                    addOutFileChannel rrSI "" "" false imgExt
                )
                
                if (theManagerActive   \
                    or (vray_settings.output_splitgbuffer and (vray_settings.output_splitAlpha or vray_settings.output_splitRGB))) then (

                    rrSI.imageFileNameBase=vray_settings.output_splitfilename
                    if ((rrSI.imageFileNameBase=="") or (rrSI.imageFileNameBase==undefined)) then (
                        if (rendSaveFile) then (
                            rrSI.imageFileNameBase=rendOutputFilename 
                        )
                    )
                    if (rrSI.imageFileNameBase=="") then (
                        messageBox "You have not set a render output in\nVRay: FrameBuffer: Split render channels ." title:"Royal Render" 
                        return "No render output defined."
                    )
                    if (rrSI.seqFileOffset!=0) then (
                        messageBox "File number base offset with Vray VFB is not suported)." title:"Royal Render" 
                        rrSI.seqFileOffset=0
                    )
                    
                    if (vray_settings.output_splitRGB) then (
                        addOutFileChannel rrSI "RGB_color" "vrayRGB" false ""
                    )
                    if (vray_settings.output_splitAlpha) then (
                        addOutFileChannel rrSI "Alpha" "vrayAlpha" false ""
                    )
                    if (theManagerActive) then  (
                        for n = 0 to (theManager.NumRenderElements()- 1) by 1 do     (
                            element= theManager.GetRenderElement n
                            if (not element.enabled) then continue
                            elemFileName = element.elementName 
                            posi = findString elemFileName "#"
                            if (posi != undefined) then continue 
                            elemFileName = substituteString elemFileName " " "_"
                            addOutFileChannel rrSI elemFileName element.elementName false ""
                        )    
                    )
                )
                if (vray_settings.output_saveRawFile) then (
                    if (rrSI.imageFileNameBase=="") then (
                        rrSI.imageFileNameBase= vray_settings.output_rawFileName
                        if (rrSI.imageFileNameBase=="") then (
                            messageBox "You have not set a render output in VRay: Frame Buffer: Raw image file." title:"Royal Render" 
                            return "No render output defined."
                        )
                        addOutFileChannel rrSI "" "vrayRaw" true ""
                    ) else (
                        addOutFileChannel rrSI vray_settings.output_rawFileName "vrayRaw" true ""
                    )
                ) 
        ) else (
            --VRay Frame Buffer NOT enabled 
            if (rendSaveFile) then (
                rrSI.imageFileNameBase= rendOutputFilename 
                addOutFileChannel rrSI "" "" true ""
                )
            if (rrSI.imageFileNameBase=="") then (
                messageBox "You have not set a render output to save" title:"Royal Render" 
                return "No render output defined."
            )
            if (theManagerActive) then (
                        for n = 0 to (theManager.NumRenderElements()- 1) by 1 do     (
                            element= theManager.GetRenderElement n
                            if (not element.enabled) then continue
                            imgName = theManager.GetRenderElementFileName n
                            if (imgName == undefined) then (
                                imgName= rendOutputFilename
                                splitFileName &imgName &imgExt
                                imgName=""
                            ) else (
                                splitFileName &imgName &imgExt
                                )
                            if (autoChannelName) then (
                                imgName = element.elementName
                                imgName = substituteString imgName " " "_"
                                addOutFileChannel rrSI imgName element.elementName false imgExt
                            ) else (
                                if (imgName != "") then (
                                    addOutFileChannel rrSI imgName element.elementName true ""
                                )
                            )
                        )    
            )
        )
    )

    ,fn WriteNodeToFile out_text nam val =
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
        
        
    ,fn WriteLayerToFile rrJob out_text cam active =
        (    
        format "<Job>\n"  to:out_text 
        WriteNodeToFile out_text "rrSubmitterPluginVersion" "%rrVersion%"
        WriteNodeToFile out_text "SceneOS" "win"
        WriteNodeToFile out_text "Software" "3dsMax" 
        WriteNodeToFile out_text "Layer" rrJob.Layer
        WriteNodeToFile out_text "Camera" cam 
        WriteNodeToFile out_text "IsActive" active
        WriteNodeToFile out_text "Version" rrJob.MaxVersion
        WriteNodeToFile out_text "SceneName" rrJob.SceneFile
        WriteNodeToFile out_text "SceneDatabaseDir" rrJob.projectpath
        WriteNodeToFile out_text "Renderer" rrJob.Renderer
        WriteNodeToFile out_text "RequiredLicenses" rrJob.RequiredLicenses
        WriteNodeToFile out_text "SeqStart" rrJob.seqStart
        WriteNodeToFile out_text "SeqEnd" rrJob.seqEnd
        WriteNodeToFile out_text "SeqStep" rrJob.seqStep
        WriteNodeToFile out_text "SeqFileOffset" rrJob.seqFileOffset
        WriteNodeToFile out_text "SeqFrameSet" rrJob.seqFrameset
        WriteNodeToFile out_text "ImageWidth" rrJob.imageWidth
        WriteNodeToFile out_text "ImageHeight" rrJob.imageHeight
        WriteNodeToFile out_text "ImageFilename" rrJob.outimageFileName
        WriteNodeToFile out_text "ImageExtension" rrJob.outimageExt
        WriteNodeToFile out_text "ImageFramePadding" 4
        WriteNodeToFile out_text "Channel" rrJob.outimageChannelName
        for c = 1 to rrJob.outchannelFileNames.count do (
            WriteNodeToFile out_text "ChannelFilename" rrJob.outchannelFileNames[c]
            WriteNodeToFile out_text "ChannelExtension" rrJob.outchannelExt[c]
        )

        format "</Job>\n"  to:out_text 
        )    
        
    ,fn editChannelEnable rrJob channelName isEnabled =
    -- State Sets can add/remove channels
    (
        elemIdx = findItem rrJob.channelNames channelName
        if isEnabled then (
            if (elemIdx == 0) then (  -- add channel
                imgName = substituteString channelName " " "_"
                addOutFileChannel rrJob imgName channelName false ""
            )
        )
        else (  -- remove channel
            if (elemIdx > 0) then (
                deleteItem rrJob.channelNames elemIdx
                deleteItem rrJob.channelFileNames elemIdx
                deleteItem rrJob.channelIsFullPath elemIdx
                deleteItem rrJob.channelExt elemIdx
            )
        )
    )
    
    ,fn setChannelsOutput rrJob channelIntoSubfolder =
    (
        splitFileName &rrJob.imageFileNameBase &rrJob.outimageExt
        baseExt=rrJob.outimageExt
        
        noChannelRender= ((rrJob.channelFileNames.count==1) and (rrJob.channelIsFullPath[1]==true)  and (rrJob.channelFileNames[1]==""))
        
        rrJob.outimageFileName=rrJob.imageFileNameBase
        if (noChannelRender)  then (
            rrJob.outimageChannelName=rrJob.channelNames[1]
        ) else (
            rrJob.outimageChannelName=rrJob.channelFileNames[1]
            if (channelIntoSubfolder) then (
                splitFileDir &rrJob.imageFileNameBase &imgFile
                rrJob.imageFileNameBase= rrJob.imageFileNameBase + "<Channel>\\"+imgFile
                splitFileDir &rrJob.outimageFileName &imgFile
                rrJob.outimageFileName  = rrJob.outimageFileName  + "<Channel <Channel>>\\"+imgFile
            ) 
            rrJob.imageFileNameBase= rrJob.imageFileNameBase + ".<Channel>."
            rrJob.outimageFileName  = rrJob.outimageFileName  + "<Channel .<Channel>.>"
        ) 
        
        
        
        if ((rrJob.channelIsFullPath[1]) and (rrJob.channelFileNames[1]!="")) then (
            rrJob.outimageFileName= rrJob.channelFileNames[1]
            splitFileName &rrJob.outimageFileName &rrJob.outimageExt
            if (rrJob.channelExt[1]!="") then rrJob.outimageExt=rrJob.channelExt[1]
        )
        
        if ((not rrJob.channelIsFullPath[1]) and (rrJob.channelExt[1]!="")) then (
            rrJob.outimageExt=rrJob.channelExt[1]
        )
        
        
        
        if (rrJob.channelNames[1] == "vrayRaw") then (
            if (renderers.production.fileName_addDot and (rrJob.outimageFileName[rrJob.outimageFileName.count]!=".")) then (
                rrJob.outimageFileName= rrJob.outimageFileName + "."
            )
        )
        else if ( (rrJob.channelNames[1]!="prePass")  and   ((rrJob.outimageFileName[rrJob.outimageFileName.count]) as integer != undefined) and (rrJob.outimageFileName[rrJob.outimageFileName.count]!=".")) then (
            rrJob.outimageFileName= rrJob.outimageFileName+"."
        ) 
        
        rrJob.outchannelFileNames = #()
        rrJob.outchannelExt = #()
        if (rrJob.channelFileNames.count>1) then (
            --add the last channel first
            c=rrJob.channelFileNames.count
            if (rrJob.channelIsFullPath[c]) then (
                imgName=rrJob.channelFileNames[c]
            ) else (
                imgName=rrJob.imageFileNameBase
                imgName = substituteString imgName "..<Channel>" ".<Channel>"
                imgName = substituteString imgName "<Channel>" rrJob.channelFileNames[c]
            )
            imgExt=baseExt
            if (rrJob.channelExt[c]!="") then (
                imgExt=rrJob.channelExt[c]
            ) else if (rrJob.channelIsFullPath[c]) then (
                splitFileName &imgName &imgExt
            )
            append rrJob.outchannelFileNames imgName
            append rrJob.outchannelExt imgExt
        )
            
        for c = 2 to rrJob.channelFileNames.count-1 do (
            if (rrJob.channelIsFullPath[c]) then (
                imgName=rrJob.channelFileNames[c]
            ) else (
                imgName=rrJob.imageFileNameBase
                imgName = substituteString imgName "..<Channel>" ".<Channel>"
                imgName = substituteString imgName "<Channel>" rrJob.channelFileNames[c]
            )
            imgExt=baseExt
            if (rrJob.channelExt[c]!="") then (
                imgExt=rrJob.channelExt[c]
            ) else if (rrJob.channelIsFullPath[c]) then (
                splitFileName &imgName &imgExt
            )
            append rrJob.outchannelFileNames imgName
            append rrJob.outchannelExt imgExt
        )
    )


    
    ,fn getScene  channelIntoSubfolder autoChannelName= (
        getSceneInfo autoChannelName
        if (rrSI.Renderer== "VRay") then (
            vray_settings = renderers.current
            if rrSI.RendererType == "GPU" then (
                vray_settings = renderers.current.V_Ray_settings
            )
            if (vray_settings.output_separateFolders) then (
                channelIntoSubfolder=true
            )
        )    
        rrSI.Renderer = rrSI.Renderer+"-s"
        if ((rrSI.Renderer == "VRay-s") and (vray_settings.imageSampler_type_new == 1) ) then (
            rrSI.Renderer = "Vray-s-resume"
        )
        if ((rrSI.Renderer == "VRay-s") and (rrSI.RendererType == "GPU") ) then (
            rrSI.Renderer = "Vray-s-GPU"
        )
        
        if (rrSI.imageFileNameBase=="") then (
            return "No render output defined."
        )
        
        if (rrSI.channelFileNames.count==0) then (
            messageBox "No output found." title:"Royal Render" 
            return "No render output defined."
        )

        local rrJobs = #(rrSI)

        -- Submit State Sets as Layers starting with "::"
        stateSetsDotNetObject = dotNetObject "Autodesk.Max.StateSets.Plugin"
        stateSets = stateSetsDotNetObject.Instance
        masterState = stateSets.EntityManager.RootEntity.MasterStateSet
        statesList = dotnetobject "System.Collections.Generic.List`1[[Autodesk.Max.StateSets.Entities.StateSets.StateSet, Autodesk.Max.StateSets, Version=19.51.835.0, Culture=neutral, PublicKeyToken=null]]"
        masterState.CollectDescendantStateSets statesList
        stateSets_count = masterState.DescendantStateCount

        
        for i=0 to (stateSets_count - 1) do
        (
            stateSet=statesList.Item[i]
            if (stateSet.IsObjectStateSet) then (
                continue
            )
            else if (stateSet.Children.count == 0) then (
                continue
            )
            else if (masterState.CurrentState != null) then (
                masterState.CurrentState = null
            )
            
            outimageChanged = false
            seqLock = false  -- don't override seqStart/seqEnd
            elemLock = false -- don't override channels
            
            newJob = copy rrJobs[1]
            newJob.Layer = "::" + stateSet.Name

            newJob.channelNames = deepcopy rrSI.channelNames
            newJob.channelFileNames = deepcopy rrSI.channelFileNames
            newJob.channelIsFullPath = deepcopy rrSI.channelIsFullPath
            newJob.channelExt = deepcopy rrSI.channelExt
            newJob.outchannelExt = #()
            newJob.outchannelFileNames = #()
            
            for j=0 to (stateSet.Children.count - 1) do (
                change = stateSet.Children.Item[j]
                rndChange = findString change.AutomaticName "Render Property Changes"
                if (rndChange!=undefined) then (
                    for k=0 to (change.Children.count - 1) do (
                        override = change.Children.Item[k]

                        if (override.AutomaticName == "Save File Path") then (
                            newJob.imageFileNameBase = override.Value
                            outimageChanged = true
                        )
                        if ( (override.AutomaticName == "Start") and (not seqLock) ) then (
                            newJob.seqStart = override.Value as integer
                        )
                        else if ((override.AutomaticName == "End") and (not seqLock) ) then (
                            newJob.seqEnd = override.Value as integer
                        )
                        else if (override.AutomaticName == "TimeType") then (
                            if (override.Value==1) then (
                                rrSI.seqStart=animationRange.start.frame  as integer
                                rrSI.seqEnd=animationRange.start.frame  as integer
                                seqLock = true
                            )
                            else if (rendTimeType==2) then (
                                rrSI.seqStart=animationRange.start.frame as integer
                                rrSI.seqEnd=animationRange.end.frame  as integer
                                seqLock = true
                            )
                            else if (rendTimeType==3) then (
                                rrSI.seqFrameset= rendPickupFrames  -- this value cannot be overridden with state sets
                                rrSI.seqStart=animationRange.start.frame
                                rrSI.seqEnd=animationRange.end.frame
                                seqLock = true
                            )
                        )
                        else if (override.AutomaticName == "NthFrame") then (
                            newJob.seqStep = override.Value as integer
                        )
                        else if (override.AutomaticName == "File Number Base") then (
                            newJob.seqFileOffset = override.Value as integer
                        )
                        else if (override.AutomaticName == "Width") then (
                            newJob.imageWidth = override.Value as integer
                        )
                        else if (override.AutomaticName == "Height") then (
                            newJob.imageHeight = override.Value as integer
                        )
                        else if (override.AutomaticName == "Render parameter changes") then (
                            -- vray overrides
                            irradMapMode = vray_settings.adv_irradmap_mode
                            irradMapPath = vray_settings.adv_irradmap_autoSaveFileName
                            giOn = vray_settings.gi_on
                            splitBuf = vray_settings.output_splitgbuffer
                            
                            for l=0 to (override.Children.count - 1) do (
                                rnd_override = override.Children.Item[l]
                                
                                vrayFname = findString rnd_override.AutomaticName "output_splitfilename"
                                vraySplitBuf = findString rnd_override.AutomaticName "output_splitgbuffer"
                                vrayRaw = findString rnd_override.AutomaticName "output_rawFileName"
                                vrayRGBChan = findString rnd_override.AutomaticName "output_splitRGB"
                                vrayAlphaChan = findString rnd_override.AutomaticName "output_splitAlpha"
                                vrayIrradmapMode = findString rnd_override.AutomaticName "adv_irradmap_mode"
                                vrayIrradmapPath = findString rnd_override.AutomaticName "adv_irradmap_autoSaveFileName"
                                vrayGIon = findString rnd_override.AutomaticName "gi_on"

                                if (vraySplitBuf != undefined) then (
                                    splitBuf = rnd_override.Value
                                    if (not splitBuf) then (
                                        for ch_idx=newJob.channelFileNames.count  to 1 by -1 do (
                                            if newJob.channelNames[ch_idx] == "prePass" then continue
                                            if newJob.channelNames[ch_idx] == "vrayRaw" then continue
                                            if newJob.channelNames[ch_idx] == "" then continue
                                            
                                            deleteItem newJob.channelNames ch_idx
                                            deleteItem newJob.channelFileNames ch_idx
                                            deleteItem newJob.channelIsFullPath ch_idx
                                            deleteItem newJob.channelExt ch_idx
                                        )
                                    )
                                )
                                if (vrayFname != undefined) then (
                                    newJob.imageFileNameBase = rnd_override.Value
                                    outimageChanged = true
                                )
                                if (vrayRGBChan != undefined) then (
                                    editChannelEnable newJob "RGB_color" rnd_override.Value
                                )
                                if (vrayAlphaChan != undefined) then (
                                    editChannelEnable newJob "Alpha" rnd_override.Value
                                )
                                if (vrayIrradmapMode != undefined) then (
                                    irradMapMode = rnd_override.Value
                                )
                                if (vrayIrradmapPath != undefined) then (
                                    irradMapPath = rnd_override.Value
                                )
                                if (vrayGIon != undefined) then (
                                    giOn = rnd_override.Value
                                )
                                
                                if (vrayRaw != undefined) then (
                                    elemIdx = findItem newJob.channelNames "vrayRaw"
                                    if (elemIdx > 0) then (
                                        newJob.channelFileNames[elemIdx] = rnd_override.Value
                                    )
                                    else (
                                        addOutFileChannel newJob rnd_override.Value "vrayRaw" true ""
                                    )
                                )
                            )
                            
                            if ( (giOn) and (irradMapMode==6) ) then (
                                newJob.channelFileNames = #()
                                newJob.channelNames = #()
                                newJob.channelIsFullPath = #()
                                newJob.channelExt = #()
                                
                                newJob.imageFileNameBase=irradMapPath
                                addOutFileChannel newJob "" "prePass" true ""
                                outimageChanged = true
                                elemLock = true
                            )
                        )                       
                        else if (not elemLock) then (
                            elemChange = findString override.AutomaticName "Render Element Change"
                            renderChange = findString override.AutomaticName "Production rendererset to"

                            if (renderChange != undefined) then (
                                rndName = substring override.AutomaticName 28 -1
                                rndName = substituteString rndName " " "_"
                                rndName = substituteString rndName "." "_"
                                rndName = substituteString rndName "-" "_"
                                newJob.Renderer = rndName
                                
                                setRenderLicense newJob
                                newJob.Renderer = newJob.Renderer+"-s"
                            )

                            if (elemChange != undefined) then (
                                elemName = substring override.AutomaticName 2 (elemChange - 4)
                                for l=0 to (override.Children.count - 1) do (
                                    elemOver = override.Children.Item[l]

                                    if (elemOver.AutomaticName=="Enabled") then (
                                        editChannelEnable newJob elemName elemOver.Value
                                    )
                                )
                            )
                        )
                    )
                )
            )
            
            if (not outimageChanged) then (
                newJob.imageFileNameBase = masterState.RenderOutputFilePattern as string
            )
            
            newJob.imageFileNameBase = substituteString newJob.imageFileNameBase "<StateName>" stateSet.Name
            newJob.imageFileNameBase = substituteString newJob.imageFileNameBase "<Layer>" stateSet.Name
            setChannelsOutput newJob channelIntoSubfolder
            append rrJobs newJob
        )

        
        if (rrJobs.count > 1) then (
            -- disable first job (master) if we have layers
            rrSI.Layer = "::MasterLayer"
            jobActive = 0
        )
        else (
            jobActive = 1
        )

        setChannelsOutput rrSI channelIntoSubfolder

        -- Submit Scene States as Layers
        maxLayer= sceneStateMgr.getCount()
        for l = 1 to maxLayer do (
            newJob = copy rrJobs[1]
            newJob.Layer = sceneStateMgr.GetSceneState(l)
            
            lp=-1
            for p=newJob.outImageFileName.count  to 1 by -1 do (
                if (newJob.outImageFileName[p] == "\\") then (
                    lp=p
                    exit
                    )
                )
            if (lp >-1) then (
                newJob.outImageFileName= replace newJob.outImageFileName lp 1 "\\<Layer>\\"
                )
            
            append rrJobs newJob
        )
        
        if (maxLayer > 1) then (
            jobActive = 0
        )

        return rrJobs
    )


    ,fn writeXml  localJobArray localCmdOptions  = (
        -- Write XML file
        XMLfileName= getTempFileName()
        out_text = createFile XMLfileName
        format "<rrJob_submitFile syntax_version=\"6.0\">\n"  to:out_text 
        format "<DeleteXML>1</DeleteXML>\n"  to:out_text 
        format "<NoUTF8Decode>1</NoUTF8Decode>\n"  to:out_text 
        WriteNodeToFile out_text "SubmitterParameter" localCmdOptions
        
        for d = 1 to localJobArray.count do
        (
            local rrJob = localJobArray[d]
            WriteLayerToFile rrJob out_text "" jobActive
            for c = 1 to rrJob.Cameras.count do
            (
                WriteLayerToFile rrJob out_text rrJob.Cameras[c] 0
            )
            jobActive = 1
        )

        format "</rrJob_submitFile>\n"  to:out_text 
        close out_text
        return XMLfileName
    ) 


    ,fn submitXml XMLfileName = (
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

        
    ,fn exec  channelIntoSubfolder autoChannelName= (
    -----------------------------------------------------------------------
    -- Main function body start
    -----------------------------------------------------------------------

        print ("Royal Render (new,"+(channelIntoSubfolder as string)+","+(autoChannelName  as string)+") %rrVersion%")
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
        
        rrJobs= getScene channelIntoSubfolder autoChannelName

        XMLfileName= writeXml rrJobs rrSI.cmdOptions
        submitXml XMLfileName
    )
)

if (rrSubmit_autoSubmit) then
   (
    ex= rrSubmit_scriptrender()
    ex.exec rrSubmit_channelIntoSubfolder rrSubmit_autoChannelName 
   )
