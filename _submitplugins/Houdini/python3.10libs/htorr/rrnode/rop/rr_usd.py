# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import os.path
from htorr.rroutput import Output, ProductOutput
from htorr.rrnode.base import RenderNode
import traceback

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")

def printList_Debug(title, liste):
    msg= title +":"
    for it in liste:
        msg= msg + "\n" + str(it )
    logger.debug(msg)
   
_NAME_Karma= "Karma"
_NAME_Arnold= "Arnold"
_NAME_Arnold_husk= "Arnold-Husk"
_NAME_Renderman= "Renderman"
_NAME_Redshift= "Redshift"
_NAME_VRay= "VRay"


def detectRenderEngine(renderer_parm):
    try:
        ren = renderer_parm.eval() 
    except:
        logger.debug("No renderer set or unable to read: {}".format(traceback.format_exc()))       
        return _NAME_Karma
        
    if (ren == None):
        logger.debug("No renderer set, using Karma ")  
        return _NAME_Karma
        
    ren = ren.lower()
    if (len(ren)==0) or ren == ("Karma").lower() or ren == ("BRAY_HdKarma").lower():
        return _NAME_Karma
        
    if (ren == ("Arnold").lower()):
        return _NAME_Arnold
    if (ren == ("HtoA").lower()):
        return _NAME_Arnold
    if (ren == ("HdArnoldRendererPlugin").lower()):
        return _NAME_Arnold
        
    if (ren == ("Arnold-Husk").lower()):
        return _NAME_Arnold_husk
        
    if (ren == ("prman").lower()):
        return _NAME_Renderman
    if (ren == ("renderman").lower()):
        return _NAME_Renderman
    if (ren == ("HdPrmanLoaderRendererPlugin").lower()):
        return _NAME_Renderman
    if (ren == ("prman-xpu").lower()):
        return _NAME_Renderman
    if (ren == ("prman-xpuCpu").lower()):
        return _NAME_Renderman
    if (ren == ("prman-xpuGpu").lower()):
        return _NAME_Renderman
    if (ren == ("HdPrmanXpuLoaderRendererPlugin").lower()):
        return _NAME_Renderman
    if (ren == ("HdPrmanXpuCpuLoaderRendererPlugin").lower()):
        return _NAME_Renderman
    if (ren == ("HdPrmanXpuGpuLoaderRendererPlugin").lower()):
        return _NAME_Renderman
        
    if (ren == ("rs").lower()):
        return _NAME_Redshift
    if (ren == ("Redshift").lower()):
        return _NAME_Redshift
    if (ren == ("HdRedshiftRendererPlugin").lower()):
        return _NAME_Redshift
        
    if (ren == ("vray").lower()):
        return _NAME_VRay
    if (ren == ("v-ray").lower()):
        return _NAME_VRay
    if (ren == ("HdVRayRendererPlugin").lower()):
        return _NAME_VRay

    logger.warning("Unknown Renderer '{}'. Using Karma. ".format(ren))
    return _NAME_Karma

def addRenderman_Renderer(renderer):
    renderer = renderer.lower()
    if ("xpu" in renderer):
        if ("xpucpu" in renderer):
            return "PrmanRenderer=XpuCpu"
        if ("xpugpu" in renderer):
            return "PrmanRenderer=XpuGpu"
        return "PrmanRenderer=Xpu"

    return ""


class UsdRop(RenderNode):
    """ USD ROP to write USD Files"""

    name = "usd"

    @property
    def output_parm(self):
        return "lopoutput"

    @property
    def renderer_version(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return ""

        elif renderer==_NAME_Arnold:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()

        elif renderer==_NAME_Arnold_husk:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        
        elif renderer==_NAME_Renderman:
            import htorr.rrnode.rop.rr_renderman as rr_renderman
            return  rr_renderman._getRendermanVersion()
        
        elif renderer==_NAME_Redshift:
            import htorr.rrnode.rop.rr_redshift as rr_redshift
            return rr_redshift._getRedshiftVersion()
        
        elif renderer==_NAME_VRay:
            import htorr.rrnode.rop.rr_vray as rr_vray
            return rr_vray._getVRayVersion()
            
        return ""    

    @property
    def renderer(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return "createUSD_karma"
        elif renderer==_NAME_Arnold:
            return "createUSD_arnold"
        elif renderer==_NAME_Arnold_husk:
            return "createUSD_arnold"
        elif renderer==_NAME_Renderman:
            return "createUSD_prman"
        elif renderer==_NAME_Redshift:
            return "createUSD_redshift"
        elif renderer==_NAME_VRay:
            return "createUSD_vray"
        
        return "createUSD_karma"


    @property
    def rr_job_variablesFunc(self):
        try:
            renderer= detectRenderEngine(self._node.parm("renderer"))
            if renderer==_NAME_Renderman:
                return addRenderman_Renderer(self._node.parm("renderer").eval() )
        except:
            pass
        return ""


    @property
    def single_output(self):
        if self._node.evalParm("fileperframe"):
            f1 = self._node.parm(self.output_parm).evalAtFrame(1)
            f2 = self._node.parm(self.output_parm).evalAtFrame(2)
            if (f1 == f2):
                return True
            return False
        else:
            # A .usd sequence must have fileperframe enabled, so we must render a single output
            return True

    @property
    def archive(self):
        outputFound=False
        try:
            parm = self._node.parm("outputimage")
            parmValue = parm.eval()
            logger.debug("{}: outputimage set, archive ".format(self._node.path()))               
            outputFound=True
        except:
            logger.debug("{}: no outputimage, no archive ".format(self._node.path()))  
        
        if not outputFound:
            stage= None
            import loputils
            lop = self._node.evalParm('loppath')
            logger.debug("renderproductList: lop is {}".format(lop))
            if lop:
                lop = self._node.parm("loppath").evalAsNode()
                stage = lop.stage() 
            else:
                input = self._node.input(0)
                stage = input.stage()
            
            if (stage== None):
                return []

            products = stage.GetPrimAtPath("/Render/Products")
            if products:
                outputFound=True

        return outputFound

       
    def to_archive(self):
        self.__class__ = UsdArchiveROP

    def to_standalone(self):
        isSingleOut=self.single_output
        self.__class__ = UsdStandalone
        self.setSingleScene(isSingleOut)
            



class UsdRop_LOP(UsdRop):
    """ USD stage/LOP ROP to write USD Files"""
    name = "usd_rop"

class UsdArchiveROP(UsdRop):
    """ child of UsdRop for create+render jobs"""
    name = "usd_create"

    @property
    def aovs(self):
        return

    @property
    def gpu(self):
        return False

class UsdStandalone(UsdRop):
    """ child of UsdRop for create+render jobs"""
    name = "usd_render"

    def setSingleScene(self, isSingle):
        self.sceneIsSingleFile = isSingle

    @property
    def software(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Arnold:
            if (self.sceneIsSingleFile):
                return "Arnold-singlefile"
            else: 
                return "Arnold"
            #all other renderer are using husk.exe, so continue function
            
        if (self.sceneIsSingleFile):
            return "USD_StdA_single"
        else:
            return "USD_StdA"
        
    @property
    def renderer(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return ""
        elif renderer==_NAME_Arnold:
            return "HtoA"
        elif renderer==_NAME_Arnold_husk:
            return "HtoA"
        elif renderer==_NAME_Renderman:
            return "prman"
        elif renderer==_NAME_Redshift:
            return "redshift"
        elif renderer==_NAME_VRay:
            return "VRay"
        return ""
    
    @property
    def renderer_version(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return ""
            
        elif renderer==_NAME_Arnold:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        
        elif renderer==_NAME_Arnold_husk:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        
        elif renderer==_NAME_Renderman:
            import htorr.rrnode.rop.rr_renderman as rr_renderman
            return  rr_renderman._getRendermanVersion()
        
        elif renderer==_NAME_Redshift:
            import htorr.rrnode.rop.rr_redshift as rr_redshift
            return rr_redshift._getRedshiftVersion()
        
        elif renderer==_NAME_VRay:
            import htorr.rrnode.rop.rr_vray as rr_vray
            return rr_vray._getVRayVersion()
        
        return ""

    @property
    def rr_job_variablesFunc(self):
        try:
            renderer= detectRenderEngine(self._node.parm("renderer"))
            if renderer==_NAME_Renderman:
                return addRenderman_Renderer(self._node.parm("renderer").eval() )
        except:
            pass
        return ""

            
    @property
    def rr_jobsettingsFunc(self):
        jobParams=""
        try:
            parm = self._node.parm("rendersettings")
            parmValue = parm.eval() 
            if len(parmValue)>0:
                jobParams= jobParams+ 'AdditionalCommandlineParam=0~1~ -s {};'.format(parmValue)
        except:
            logger.debug("{}: no rendersettings set ".format(self._node.path()))              
        
        allproducts = self.renderproductList
        if (len(allproducts)==1):
            jobParams= jobParams +  'COSingleRenderProduct=1~1;'

        try:
            ren = renderer_parm.eval() 
        except:
            pass
        else:
            if (ren != None):
                ren = ren.lower()
                if "xpugpu" in ren:
                    jobParams= jobParams + 'GPUrequired=0~1; '
                    
        return jobParams

    @property
    def output_parm(self):
        try:
            parm = self._node.parm("outputimage")
            parmValue = parm.eval() 
        except:
            logger.debug("{}: no outputimage set ".format(self._node.path()))     
            return ""             
        return "outputimage"

    @property
    def renderproductList(self):
        stage= None
        import loputils
        lop = self._node.evalParm('loppath')
        logger.debug("renderproductList: lop is {}".format(lop))
        noStage=True
        if lop:
            lop = self._node.parm("loppath").evalAsNode()
            if lop:
                stage = lop.stage() 
                noStage=False
            else:
                logger.error("{}: loppath does not exist: {}".format(self._node.path(), self._node.evalParm('loppath')))     
        if (noStage):
            input = self._node.input(0)
            if input:
                stage = input.stage()
        
        if (stage== None):
            logger.debug("{}: no stage found! ".format(self._node.path()))     
            return []

        allproducts = []
        products = stage.GetPrimAtPath("/Render/Products")
        if not products:
            logger.debug("{}: no render products found! ".format(self._node.path()))     
            return []
        productchildren = products.GetAllChildren()
        for c in productchildren:
            name = c.GetName()
            attribs = c.GetAttributes()
            product = {}
            product["name"] = name
            isValidImage=False
            for a in attribs:
                if a.GetName().find("productName") > -1:
                    #logger.debug("renderproductList: productOutname: {}".format(a.Get()))
                    product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                    isValidImage= product["productOutname"].find("checkpoint")<0 
                    product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                    product["productOutnameB"] = a.Get(999999) 
                    product["attrib"] = a
                if a.GetName().find("resolution") > -1:
                    product["resX"] = a.Get()[0]
                    product["resY"] = a.Get()[1]
            if (isValidImage):
                allproducts.append(product)
        printList_Debug("renderproductList", allproducts)
        return allproducts

    @property
    def aovs(self):
        allproducts = self.renderproductList
        aovs = []
        for i in range(0, len(allproducts)-1): # -1 as the last one is used as main output name
            productout = ProductOutput(allproducts[i]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            aovs.append( (os.path.join(productout.dir,productout.name), productout.extension) )    
        return aovs 
        
    @property
    def single_output(self):
        return False
            
        
        

class UsdRenderRop(RenderNode):
    """ USD ROP to render """

    name = "usdrender"

    @property
    def output_parm(self):
        #logger.debug("{}: output_parm is set to {} ".format(self._node.path(), self._node.parm("outputimage").eval() ) )        
        return "outputimage"

    @property
    def renderer(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return "usd_karma"
        elif renderer==_NAME_Arnold:
            return "usd_arnold"
        elif renderer==_NAME_Arnold_husk:
            return "usd_arnold"
        elif renderer==_NAME_Renderman:
            return "usd_prman"
        elif renderer==_NAME_Redshift:
            return "usd_redshift"
        elif renderer==_NAME_VRay:
            return "usd_vray"

        return "usd_karma"

    @property
    def renderer_version(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Karma:
            return ""
            
        elif renderer==_NAME_Arnold:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        
        elif renderer==_NAME_Arnold_husk:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        
        elif renderer==_NAME_Renderman:
            import htorr.rrnode.rop.rr_renderman as rr_renderman
            return  rr_renderman._getRendermanVersion()
        
        elif renderer==_NAME_Redshift:
            import htorr.rrnode.rop.rr_redshift as rr_redshift
            return rr_redshift._getRedshiftVersion()
        
        elif renderer==_NAME_VRay:
            import htorr.rrnode.rop.rr_vray as rr_vray
            return rr_vray._getVRayVersion()
        
        return ""


    @property
    def rr_job_variablesFunc(self):
        try:
            renderer= detectRenderEngine(self._node.parm("renderer"))
            if renderer==_NAME_Renderman:
                return addRenderman_Renderer(self._node.parm("renderer").eval() )
        except:
            pass
        return ""

    @property
    def rr_jobsettingsFunc(self):
        jobParams=""
        try:
            ren = renderer_parm.eval() 
        except:
            pass
        else:
            if (ren != None):
                ren = ren.lower()
                if "xpugpu" in ren:
                    jobParams= jobParams + 'GPUrequired=0~1; '
                
        return jobParams


    @property
    def single_output(self):
        return False
        
    @property
    def aovs(self):
        allproducts = self.renderproductList
        aovs = []
        for i in range(0, len(allproducts)-1): # -1 as the last one is used as main output name
            productout = ProductOutput(allproducts[i]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            aovs.append( (os.path.join(productout.dir,productout.name), productout.extension) )    
        return aovs 
        
    @property
    def renderproductList(self):
        stage= None
        import loputils
        lop = self._node.evalParm('loppath')
        logger.debug("renderproductList: lop is {}".format(lop))
        noStage=True
        if lop:
            lop = self._node.parm("loppath").evalAsNode()
            if lop:
                stage = lop.stage() 
                noStage=False
            else:
                logger.error("{}: loppath does not exist: {}".format(self._node.path(), self._node.evalParm('loppath')))     
        if (noStage):
            input = self._node.input(0)
            if input:
                stage = input.stage()
        
        if (stage== None):
            logger.debug("{}: no stage found! ".format(self._node.path()))     
            return []

        allproducts = []
        products = stage.GetPrimAtPath("/Render/Products")
        if not products:
            logger.debug("{}: no render products found! ".format(self._node.path()))     
            return []
        productchildren = products.GetAllChildren()
        for c in productchildren:
            name = c.GetName()
            attribs = c.GetAttributes()
            product = {}
            product["name"] = name
            isValidImage=False
            for a in attribs:
                if a.GetName().find("productName") > -1:
                    #logger.debug("renderproductList: productOutname: {}".format(a.Get()))
                    product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                    isValidImage= product["productOutname"].find("checkpoint")<0 
                    product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                    product["productOutnameB"] = a.Get(999999) 
                    product["attrib"] = a
                if a.GetName().find("resolution") > -1:
                    product["resX"] = a.Get()[0]
                    product["resY"] = a.Get()[1]
            if (isValidImage):
                allproducts.append(product)
        printList_Debug("renderproductList", allproducts)
        return allproducts        

class UsdRenderRop_LOP(UsdRenderRop):
    """ USD stage/LOP ROP to render """
    name = "usdrender_rop"
    
    
    
class Karma_LOP(RenderNode):
    """ Karma LOP to render """

    name = "karma"

    @property
    def output_parm(self):
        return "picture"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        return "usd_karma"

    @property
    def camera_parm(self):
        return "camera"

    @property
    def single_output(self):
        return False    
        
    @property
    def image_size(self):
        from htorr.rrnode.rop import utils
        x = None
        y = None

        try:
            x= self._node.evalParm("resolutionx")
            y= self._node.evalParm("resolutiony")

        except ValueError:
            return

        return(x, y)
        
    def dependencies(self):
        #use same function as Subnet Node 
        return self._node.inputs() + self._node.children()    


    
class USDStitchClips_ROP(RenderNode):

    name = "usdstitchclips"

    @property
    def output_parm(self):
        return "outtemplatefile1"

    @property
    def renderer(self):
        return "anyNode"

    @property
    def single_output(self):
        return True    

    @property
    def renderer_version(self):
        return
        

    
class USDStitch_ROP(RenderNode):

    name = "usdstitch"

    @property
    def output_parm(self):
        return "outfile1"

    @property
    def renderer(self):
        return "anyNode"

    @property
    def single_output(self):
        return True    

    @property
    def renderer_version(self):
        return        