# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import os.path
from htorr.rroutput import Output
from htorr.rrnode.base import RenderNode


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


logger = logging.getLogger("HtoRR")


def _getOctaneVersion():
    octaneVersion=  hou.hscript( 'Octane_version')
    octaneVersion= octaneVersion[0]
    pos= octaneVersion.find("Plugin version:")
    if (pos<0):
        return ""
    pos= pos + len("Plugin version:")
    octaneVersion= octaneVersion[pos:]
    pos= octaneVersion.find("(")
    if (pos<0):
        return ""
    octaneVersion= octaneVersion[:pos]
    octaneVersion= octaneVersion.strip()    

    return octaneVersion
            
def getFilename_convertFrameNr(parm):
    #there is no function in Houdini that evals all variables and expressions, but keeps the frame number
    #this one does
    fr1= parm.evalAtFrame(1)
    fr9= parm.evalAtFrame(9999999)
    logger.debug("getFilename_convertFrameNr: {} ".format(fr1))
    logger.debug("getFilename_convertFrameNr: {} ".format(fr9))
    #There are Python expressions that return $F4 even after eval()
    fr1= hou.text.expandStringAtFrame(fr1, 1)
    fr9= hou.text.expandStringAtFrame(fr9, 9999999)
    logger.debug("getFilename_convertFrameNr: {} ".format(fr1))
    logger.debug("getFilename_convertFrameNr: {} ".format(fr9))
    if (fr1==fr9):
        return fr1
    padding=len(fr1)-len(fr9)+7
    posFr= fr9.find("9999999")
    posFrEnd=posFr+7
    newName= "$F" + str(padding)
    newName=fr9[:posFr] + newName + fr9[posFrEnd:]
    logger.debug("getFilename_convertFrameNr: {} ".format(newName))

    return newName            

class OctaneRop(RenderNode):

    name = "Octane_ROP"

    @property
    def camera_parm(self):
        return "HO_renderCamera"

    @property
    def output_parm(self):
        return "HO_img_fileName"
                
    @property
    def outext(self):
        rrout = Output(self._node.parm("HO_img_fileName"), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        if len(rrout.extension) < 1:
            formatIndex= self._node.parm('HO_img_fileFormat').eval()
            if (formatIndex == 0):
                return ".png"
            if (formatIndex == 1):
                return ".png"
            if (formatIndex == 2):
                return ".exr"
            if (formatIndex == 3):
                return ".exr"
            if (formatIndex == 4):
                return ".tif"
            if (formatIndex == 5):
                return ".tif"
            if (formatIndex == 6):
                return ".jpg"
        return rrout.extension

    @property
    def rr_job_variablesFunc(self):
        formatIndex= self._node.parm('HO_img_fileFormat').eval()
        if (formatIndex == 0):
            return "RR_OC_EXT_FLAG=png"
        if (formatIndex == 1):
            return "RR_OC_EXT_FLAG=png16"
        if (formatIndex == 2):
            return "RR_OC_EXT_FLAG=exr16"
        if (formatIndex == 3):
            return "RR_OC_EXT_FLAG=exr32"
        return ""
                
    @property
    def renderer(self):
        return "Octane"

    @property
    def renderer_version(self):
        return _getOctaneVersion()

    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        x = None
        y = None
        if not hou.node(self.camera):
            return
        try:
            if not self._node.evalParm("HO_overrideCameraRes"):
                x, y = utils.get_camera_res(self.camera)
            else:
                if self._node.evalParm("HO_overrideResScale") == "user":
                    x = self._node.evalParm("HO_overrideRes1")
                    y = self._node.evalParm("HO_overrideRes2")
                else:
                    frac = float(self._node.evalParm("HO_overrideResScale"))
                    if (frac==1):
                        frac=1/10
                    elif (frac==2):
                        frac=1/5
                    elif (frac==3):
                        frac=1/4
                    elif (frac==4):
                        frac=1/3
                    elif (frac==5):
                        frac=1/2
                    elif (frac==6):
                        frac=2/3
                    elif (frac==7):
                        frac=3/4                    
                    x, y = utils.get_camera_res(self.camera)
                    x = int(round(x * frac))
                    y = int(round(y * frac))

        except ValueError:
            return

        return(x, y)


    @property
    def archive(self):
        return self._node.parm("HO_abc_exportEnabled").eval() == 1

    @property
    def gpu(self):
        return True

    def to_archive(self):
        self.__class__ = OctaneArchiveROP

    def to_standalone(self):
        archiveName=getFilename_convertFrameNr(self._node.parm("HO_abc_exportFileName"))
        isSingleArchive= (archiveName.find("$F") < 0)
        if (isSingleArchive):
            self.__class__ = OctaneStandalone_singlefile
        else:
            self.__class__ = OctaneStandalone



class OctaneArchiveROP(OctaneRop):

    name = "Octane_ROP_archive"

    @property
    def renderer(self):
        return "createOctane"

    @property
    def output_parm(self):
        # HO_abc_exportMode   expold expnew
        return "HO_abc_exportFileName"

    @property
    def outext(self):
        rrout = Output(self._node.parm("HO_abc_exportFileName"), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        if len(rrout.extension) < 1:
            logger.info("'{}': ABC export ? {}".format(self.path, self._node.parm('HO_abc_exportMode').eval()))
            if self._node.parm('HO_abc_exportMode').eval()==0:
                return ".abc"
            else: 
                return ".orbx"
        return rrout.extension

    @property
    def aovs(self):
        return

    #def check(self):
    #    if self._node.parm('HO_abc_exportMode').eval()=="expold":
    #        logger.info("'{}': ABC export not supported".format(self.path))
    #    return True


    @property
    def gpu(self):
        return False
    
    @property
    def single_output(self):
        archiveName=getFilename_convertFrameNr(self._node.parm("HO_abc_exportFileName"))
        isSingleArchive= (archiveName.find("$F") < 0)
        #single archive files do NOT work as the standalone renderer has no frame commandline flag
        return False
        return isSingleArchive
        
        

class OctaneStandalone_singlefile(OctaneRop):

    name = "Octane_ROP_standalone_singlefile"

    @property
    def software(self):
        return "Octane-singlefile"

    @property
    def software_version(self):
        return OctaneRop.renderer_version.fget(self)

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return

    @property
    def layerName(self):
        return "Render target"
        #return self._node.parm("HO_renderTarget").eval()


class OctaneStandalone(OctaneRop):

    name = "Octane_ROP_standalone"

    @property
    def software(self):
        return "Octane"

    @property
    def software_version(self):
        return OctaneRop.renderer_version.fget(self)

    @property
    def renderer(self):
        return "Houdini"

    @property
    def renderer_version(self):
        return

    @property
    def layerName(self):
        return "Render target"
        #return self._node.parm("HO_renderTarget").eval()

