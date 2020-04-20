
import nuke

import os
import sys


#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def writeInfo(msg):
    print(msg)

def writeDebug(msg):
    return
    print("DBG: " + msg)

def writeWarning(msg):
    print("WRN: " + msg)

def writeError(msg):
    print("ERR: " + msg)


def ireplaceStartsWith(text, old, new ):
    idx = 0
    while idx < len(text):
        index_l = text.lower().find(old.lower(), idx)
        if index_l == -1:
            return text
        if index_l > 0:
            return text
        text = text[:index_l] + new + text[index_l + len(old):]
        idx = index_l + len(old)
    return text



def getAllNodes(typeName):
    allNo=nuke.allNodes()
    fileNodes=[]
    for gz in allNo:
        if isGizmo(gz):
            with gz:
                gList = nuke.allNodes(typeName)
                for gnode in gList:
                    if (gnode['disable'].value()):
                        continue
                    #pathScripted=gnode['file'].value()
                    #if ((pathScripted== None) or (len(pathScripted)<3)):
                    #    continue
                    fileNodes.append(gz)
                    break
    fileNodes=fileNodes+ nuke.allNodes(typeName)
    return fileNodes


def getAllWriteNodes():
    return getAllNodes('Write') + getAllNodes('DeepWrite') + getAllNodes('WriteGeo') + getAllNodes('WriteGeo2')

def getAllReadNodes():
    return getAllNodes('Read') + getAllNodes('DeepRead') + getAllNodes('ReadGeo') + getAllNodes('ReadGeo2') + getAllNodes('Camera2')


def convertPath(writeNode, orgDir, orgDirWinDrive, locDir, createFolder, attrName):
    """Convert output path of writeNode, return True if the destination folder can be created,
    False if creation failed, None if there is no path to create
    """
    pathScripted= writeNode[attrName].value()
    #writeInfo("    "+writeNode['name'].value()+":  original value: "+pathScripted)
    if ((pathScripted== None) or (len(pathScripted)<3)):
        return
    if ("[string" in pathScripted) or ("[value" in pathScripted) or ("[python" in pathScripted):
        pathResolved= nuke.filename(writeNode)
    else:
        pathResolved= pathScripted
    if not (('\\' in pathResolved) or ('/' in pathResolved)):
        writeInfo("    "+writeNode['name'].value()+":   invalid file value: "+pathResolved)
        return
    pathResolved_new= ireplaceStartsWith(pathResolved, orgDir, locDir)
    pathResolved_new= ireplaceStartsWith(pathResolved_new, orgDirWinDrive, locDir)
    writeNode[attrName].setValue(pathResolved_new)
    if (pathScripted!=pathResolved_new):
        if (pathScripted!=pathResolved):
            writeInfo("    "+writeNode['name'].value()+":   "+pathScripted+" => "+pathResolved+" => "+pathResolved_new)
        else:
            writeInfo("    "+writeNode['name'].value()+":   "+pathResolved+" => "+pathResolved_new)
    writeDir=os.path.dirname(pathResolved_new)
    if (createFolder and (not os.path.exists(writeDir))):
        writeInfo("     creating directory: "+writeDir)

        try:
            os.makedirs(writeDir)
        except IOError as e:
            error_msg = "Error creating directory '{0}'".format(writeDir)
            if e:
                error_msg += ": " + e.message
            writeInfo(error_msg)
            return False

    return True


def isGizmo(node):
    gizmo = isinstance(node, nuke.Gizmo)
    return gizmo



def makeLocalRenderOut(orgDir, orgDirWinDrive, locDir, write_node_name=None):
    """Set output paths to the RR local directory. If specified, only the Write Node
    named 'write_node_name' is  processed
    """
    writeInfo("-----------------LocalRenderOut-----------------")

    orgDir=orgDir.replace("\\","/")
    locDir=locDir.replace("\\","/")
    orgDirWinDrive=orgDirWinDrive.replace("\\","/")

    writeInfo("Replacing: "+orgDir+" => "+locDir)
    writeInfo("Replacing: "+orgDirWinDrive+" => "+locDir)
    writeInfo("")

    #replace all scripted paths in all read nodes
    #change render path to local render out
    n = getAllWriteNodes()

    write_node_found = False
    for writeNode in n:
        if (writeNode['disable'].value()):
            continue
        if write_node_name and writeNode['name'].value() != write_node_name:
            continue

        writeDebug("\t writeNode: " + writeNode['name'].value())
        write_node_found = True
##        if isGizmo(writeNode):
##            with writeNode:
##                gList = nuke.allNodes('Write') + nuke.allNodes('DeepWrite')
##                for gnode in gList:
##                    if (gnode['disable'].value()):
##                        continue
##                    convertPath(gnode, orgDir, orgDirWinDrive, locDir, True,"file")
##        else:
        convertPath(writeNode, orgDir, orgDirWinDrive, locDir, True,"file")

    if not write_node_found:
        if write_node_name:
            writeWarning("Write node not found: '{0}'".format(write_node_name))
        else:
            writeWarning("No Write nodes found")


    #replace all scripted paths in all read nodes
    n = getAllReadNodes()
    for readNode in n:
        if (readNode['disable'].value()):
            continue
        pathScripted=readNode['file'].value()
        if ((pathScripted== None) or (len(pathScripted)<3)):
            continue
        pathResolved=nuke.filename(readNode)
        readNode['file'].setValue(pathResolved)
        if (pathScripted!=pathResolved):
            writeInfo("    "+readNode['name'].value()+":   "+pathScripted+" => "+pathResolved)


    writeInfo("")
    writeInfo("-----------------LocalRenderOut done-----------------")
    writeInfo("")

def crossOSConvert_sub(sceneOS, ourOS, write_node_name=None):
    if (ourOS != sceneOS):
        writeInfo("-----------------crossOSConvert-----------------")
        import rrScriptHelper
        osConvert= rrScriptHelper.rrOSConversion()
        osConvert.loadSettings()
        fromOS, toOS = osConvert.getTable(sceneOS,True)
        if (len(fromOS)>0):
            for i in range(len(fromOS)):
                fromOS[i]=fromOS[i].replace("\\","/")
                toOS[i]=toOS[i].replace("\\","/")
                writeInfo("OS conversion:  %-30s  =>  %-30s" % (fromOS[i] , toOS[i]) )

                n = getAllWriteNodes()
                for writeNode in n:
                    if (writeNode['disable'].value()):
                        continue
                    if write_node_name and writeNode['name'].value() != write_node_name:
                        continue
                    convertPath(writeNode, fromOS[i], fromOS[i], toOS[i], False,"file")


                n = getAllReadNodes()
                for readNode in n:
                    if (readNode['disable'].value()):
                        continue
                    convertPath(readNode, fromOS[i], fromOS[i], toOS[i], False,"file")

                n = getAllNodes("Vectorfield")
                for node in n:
                    if (node['disable'].value()):
                        continue
                    convertPath(node, fromOS[i], fromOS[i], toOS[i], False,"vfield_file")




def crossOSConvert(pyModPath, sceneOS, write_node_name=None):
    """Convert filepaths of read and write nodes to the client OS. If specified, only the Write Node
    named 'write_node_name' is  processed
    """
    writeInfo("Appending to python search path: '" +pyModPath+"'" )
    sys.path.append(pyModPath)
    import rrScriptHelper
    ourOS= rrScriptHelper.getOS()
    if (sceneOS=="Mac"):
        sceneOS=3
    elif (sceneOS=="Linux"):
        sceneOS=2
    else:
        sceneOS=1

    #crossOSConvert_sub(sceneOS, ourOS)
    crossOSConvert_sub(1,ourOS)
    crossOSConvert_sub(2,ourOS)
    crossOSConvert_sub(3,ourOS)

    writeInfo("")
    writeInfo("-----------------crossOSConvert done-----------------")
    writeInfo("")


if __name__ == "__main__":
    srcFilename = sys.argv[1]  # original scene path (<SceneOrg>)
    locFileName = sys.argv[2]  # local path for the converted scene (<Scene>)
    srcBasePath = sys.argv[3]  # path on the fileserver, last few folders truncated (<rrLocalRenderoutOrg>)
    srcBasePath_DriveLetter = sys.argv[4]  # drive letter path on the fileserver, last few folders truncated (<NoUNC <rrLocalRenderoutOrg>>)
    locOutputPath = sys.argv[5]  # .../RR_localdata/renderout (<rrLocalRenderout>)
    locRenderScripts= sys.argv[6]  # ../RR_localdata/renderscripts (<rrLocalRenderScripts>)
    sceneOSstr = sys.argv[7]  # "The OS that was used to create the scene (<sceneOSstr>)"

    # optional parameters
    try:
        layer_parm = sys.argv.index("-rrLayer")
    except ValueError:
        layer = None
    else:
        layer = sys.argv[layer_parm + 1]
        if layer == "** All **":
            layer = None

    try:
        image_name_parm = sys.argv.index("-rrImageName")
    except ValueError:
        image_name = None
    else:
        image_name = sys.argv[image_name_parm + 1]


    nuke.scriptOpen(srcFilename)
    crossOSConvert(locRenderScripts, sceneOSstr, write_node_name=layer)
    makeLocalRenderOut(srcBasePath, srcBasePath_DriveLetter, locOutputPath, write_node_name=layer)
    nuke.scriptSaveAs(locFileName, 1)
