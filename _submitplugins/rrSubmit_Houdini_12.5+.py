# Royal Render Plugin script for Houdini 12.5+
# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
# rrInstall_Copy: ../houdini/scripts/
# rrInstall_Change_File: ../houdini/MainMenuCommon.xml, before "</mainMenu>", "<addScriptItem id=\"h.royalrender\">\n	<parent>render_menu</parent>\n	<label>Submit RRender</label>\n	<scriptPath>$HFS/houdini/scripts/rrSubmit_Houdini_12.5+.py</scriptPath>\n	<scriptArgs></scriptArgs>\n	<insertAfter/>\n  </addScriptItem>\n\n"


import hou
import sys
import os
import subprocess



def getRR_Root():
    if os.environ.has_key('RR_ROOT'):
        return os.environ['RR_ROOT']
    HCPath= "%"
    if ((sys.platform.lower() == "win32") or (sys.platform.lower() == "win64")):
        HCPath="%RRLocationWin%"
    elif (sys.platform.lower() == "darwin"):
        HCPath="%RRLocationMac%"
    else:
        HCPath="%RRLocationLx%"
    if HCPath[0]!="%":
        return HCPath
    #raise (NameError, "No RR_ROOT environment variable set!\n")


def append_arnold_params(submit_args):
    try:
        import arnold
    except ImportError:
        return False

    submit_args.append("-customRenVer_Arnold")
    submit_args.append(arnold.AiGetVersionString())
    submit_args.append("-customRenVer_createASS")
    submit_args.append(arnold.AiGetVersionString())
    submit_args.append("-customRenVer_usd_arnold")
    submit_args.append(arnold.AiGetVersionString())
    submit_args.append("-customRenVer_createUSD_arnold")
    submit_args.append(arnold.AiGetVersionString())

    return True


def append_redshift_params(submit_args):
    rs_ver_info = hou.hscript('Redshift_version')

    if len(rs_ver_info) < 1:
        return False  # Unlikely but still worth checking

    if "Unknown" in rs_ver_info[1]:
        return False

    rs_ver = rs_ver_info[0]
    rs_ver = rs_ver.replace("\n", "")
    rs_ver = rs_ver.replace("\r", "")

    submit_args.append("-customRenVer_Redshift")
    submit_args.append(rs_ver)
    submit_args.append("-customRenVer_createRS")
    submit_args.append(rs_ver)
    submit_args.append("-customRenVer_usd_redshift")
    submit_args.append(rs_ver)
    submit_args.append("-customRenVer_createUSD_redshift")
    submit_args.append(rs_ver)
    

    return True


def append_vray_params(submit_args):
    try:
        import vfh
    except ImportError:
        return False

    vray_ver = vfh.getVRayVersionString()

    submit_args.append("-customRenVer_vray")
    submit_args.append(vray_ver)
    submit_args.append("-customRenVer_createVRscene")
    submit_args.append(vray_ver)
    submit_args.append("-customRenVer_usd_vray")
    submit_args.append(vray_ver)
    submit_args.append("-customRenVer_createUSD_vray")
    submit_args.append(vray_ver)
    

    return True


def append_prman_params(submit_args):
    import os
    
    try:
        import about

        rfh_path = os.environ['RFHTREE']
        version = about._rfhReadVersion(os.path.join(rfh_path, about._rfhGetVersion(), 'etc', 'buildid.txt'))
        prman_ver=version["versionStr"]
        prman_ver= prman_ver.replace('RenderMan', '')
        prman_ver= prman_ver.replace('for', '')
        prman_ver= prman_ver.replace('Houdini', '')
        prman_ver= prman_ver.strip()
        
        submit_args.append("-customRenVer_prman")
        submit_args.append(prman_ver)
        submit_args.append("-customRenVer_usd_prman")
        submit_args.append(prman_ver)
        submit_args.append("-customRenVer_createUSD_prman")
        submit_args.append(prman_ver)
    except:
        return False

    return True


def rrSubmit():
    print ("rrSubmit %rrVersion%")
    hou.hipFile.save()
    sceneFile = hou.hipFile.name()
    rrRoot = getRR_Root()

    if not sceneFile:
        raise Exception("rrSubmission FAILED: No scene file to submit")

    exe_args = []

    # first argument is the rrSubmitter executable or starter script/app
    if sys.platform.lower() in ("win32", "win64"):
        exe_args.append(os.path.join(rrRoot, "win__rrSubmitter.bat"))
    elif sys.platform.lower() == "darwin":
        exe_args.append(os.path.join(rrRoot, "/bin/mac64/rrStartLocal"))
        exe_args.append("rrSubmitter")
    else:
        exe_args.append(os.path.join(rrRoot, "lx__rrSubmitter.sh"))

    # then the scene file
    exe_args.append(sceneFile)

    # renderers options
    append_arnold_params(exe_args)
    append_vray_params(exe_args)
    append_redshift_params(exe_args)
    append_prman_params(exe_args)
    
    # finally open
    subprocess.Popen(exe_args)


rrSubmit()
