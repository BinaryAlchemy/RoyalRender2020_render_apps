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
   


def addRenderman_Renderer(renderer):
    renderer = renderer.lower()
    if renderer == ("HdPrman").lower():
        return "PrmanRenderer="
    elif renderer == ("HdPrmanXpu").lower():
        return "PrmanRenderer=Xpu"
    elif renderer == ("HdPrmanXpuCpu").lower():
        return "PrmanRenderer=XpuCpu"
    elif renderer == ("HdPrmanXpuGpu").lower():
        return "PrmanRenderer=XpuGpu"
    return ""


class UsdRop(RenderNode):
    """ USD ROP to write USD Files"""

    name = "usd"

    @property
    def output_parm(self):
        return "lopoutput"

    @property
    def renderer_version(self):
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            if (len(renderer)==0) or renderer == "karma" or renderer == ("BRAY_HdKarma").lower():
                return ""
            elif renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                import htorr.rrnode.rop.rr_arnold as rr_arnold
                return rr_arnold._getArnoldVersion()
            elif renderer == "prman" or renderer == "renderman" or renderer == ("HdPrmanLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
                import htorr.rrnode.rop.rr_renderman as rr_renderman
                return  rr_renderman._getRendermanVersion()
            elif renderer == "rs" or renderer == "redshift":
                import htorr.rrnode.rop.rr_redshift as rr_redshift
                return rr_redshift._getRedshiftVersion()
            elif renderer == "vray" or renderer == "v-ray" or renderer == ("HdVRayRendererPlugin").lower():
                import htorr.rrnode.rop.rr_vray as rr_vray
                return rr_vray._getVRayVersion()
            else:
                logger.warning("{}: Unknown Renderer '{}' ".format(self._node.path(), renderer))
        except:
            logger.debug("{}: No renderer set or unable to read version: {}".format(self._node.path(),traceback.format_exc()))        
        return ""    

    @property
    def renderer(self):
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            
            if (len(renderer)==0) or renderer == "karma" or renderer == ("BRAY_HdKarma").lower():
                return "createUSD_karma"
            elif renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                return "createUSD_arnold"
            elif renderer == "prman" or renderer == "renderman" or renderer == ("HdPrmanLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
                return "createUSD_prman"
            elif renderer == "rs" or renderer == "redshift":
                return "createUSD_redshift"
            elif renderer == "v-ray" or renderer == "vray" or renderer == ("HdVRayRendererPlugin").lower():
                return "createUSD_vray"
            else:
                logger.warning("{}: Unknown USD Renderer '{}' ".format(self._node.path(), renderer))
        except:
            logger.debug("{}: No renderer set, using Karma ".format(self._node.path()))        
        return "createUSD_karma"

    @property
    def rr_job_variablesFunc(self):
        try:
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
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            if renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                if (self.sceneIsSingleFile):
                    return "Arnold-singlefile"
                else: 
                    return "Arnold"
            #all other renderer are using husk.exe, so continue function
        except:
            logger.debug("{}: No renderer set, using husk for Karma ".format(self._node.path()))                
        if (self.sceneIsSingleFile):
            return "USD_StdA_single"
        else:
            return "USD_StdA"
        
    @property
    def renderer(self):
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            if (len(renderer)==0) or renderer == "karma" or renderer == ("BRAY_HdKarma").lower():
                return ""
            elif renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                return "HtoA"
            elif renderer == "prman" or renderer == "renderman" or renderer == ("HdPrmanLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
                return "prman"
            elif renderer == "rs" or renderer == "redshift":
                return "redshift"
            elif renderer == "vray" or renderer == "v-ray" or renderer == ("HdVRayRendererPlugin").lower():
                return "VRay"
            else:
                logger.warning("{}: Unknown Renderer '{}' ".format(self._node.path(), renderer))
        except:
            logger.debug("{}: No renderer set, using Karma ".format(self._node.path()))        
        return ""    
    
    @property
    def renderer_version(self):
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            if (len(renderer)==0) or renderer == "karma" or renderer == ("BRAY_HdKarma").lower():
                return ""
            elif renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                import htorr.rrnode.rop.rr_arnold as rr_arnold
                return rr_arnold._getArnoldVersion()
            elif renderer == "prman" or renderer == "renderman" or renderer == ("HdPrmanLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
                import htorr.rrnode.rop.rr_renderman as rr_renderman
                return  rr_renderman._getRendermanVersion()
            elif renderer == "rs" or renderer == "redshift":
                import htorr.rrnode.rop.rr_redshift as rr_redshift
                return rr_redshift._getRedshiftVersion()
            elif renderer == "vray" or renderer == "v-ray" or renderer == ("HdVRayRendererPlugin").lower():
                import htorr.rrnode.rop.rr_vray as rr_vray
                return rr_vray._getVRayVersion()
            else:
                logger.warning("{}: Unknown Renderer '{}' ".format(self._node.path(), renderer))
        except:
            logger.debug("{}: No renderer set or unable to read version: {}".format(self._node.path(),traceback.format_exc()))        
        return ""    

    @property
    def rr_job_variablesFunc(self):
        try:
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
                jobParams= jobParams+ ' "AdditionalCommandlineParam=0~1~ -s {}"'.format(parmValue)
        except:
            logger.debug("{}: no rendersettings set ".format(self._node.path()))              
        
        allproducts = self.renderproductList
        if (len(allproducts)==1):
            jobParams= jobParams +  ' "COSingleRenderProduct=1~1"'
            
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
        renderer_parm = self._node.parm("renderer")
        renderer = renderer_parm.eval()
        renderer = renderer.lower()

        if (renderer == ("HdArnoldRendererPlugin").lower()):
            return "usd_arnold"
        elif renderer == ("BRAY_HdKarma").lower():
            return "usd_karma"
        elif renderer == ("HdVRayRendererPlugin").lower():
            return "usd_vray"
        elif renderer == ("HdPrmanLoaderRendererPlugin").lower() \
              or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
              or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
            return "usd_prman"
        else:
            logger.warning("{}: Unknown USD Renderer '{}' ".format(self._node.path(), renderer))
        return "usd_karma"

    @property
    def renderer_version(self):
        try:
            renderer_parm = self._node.parm("renderer")
            renderer = renderer_parm.eval() 
            renderer = renderer.lower()
            if (len(renderer)==0) or renderer == "karma" or renderer == ("BRAY_HdKarma").lower():
                return ""
            elif renderer == "arnold" or renderer == "htoa" or renderer == ("hdarnoldrendererplugin").lower():
                import htorr.rrnode.rop.rr_arnold as rr_arnold
                return rr_arnold._getArnoldVersion()
            elif renderer == "prman" or renderer == "renderman" or renderer == ("HdPrmanLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuLoaderRendererPlugin").lower() or renderer == ("HdPrmanXpuCpuLoaderRendererPlugin").lower() \
                  or renderer == ("HdPrmanXpuGpuLoaderRendererPlugin").lower():
                import htorr.rrnode.rop.rr_renderman as rr_renderman
                return  rr_renderman._getRendermanVersion()
            elif renderer == "rs" or renderer == "redshift":
                import htorr.rrnode.rop.rr_redshift as rr_redshift
                return rr_redshift._getRedshiftVersion()
            elif renderer == "vray" or renderer == "v-ray" or renderer == ("HdVRayRendererPlugin").lower():
                import htorr.rrnode.rop.rr_vray as rr_vray
                return rr_vray._getVRayVersion()
            else:
                logger.warning("{}: Unknown Renderer '{}' ".format(self._node.path(), renderer))
        except:
            logger.debug("{}: No renderer set or unable to read version: {}".format(self._node.path(),traceback.format_exc()))        
        return ""    

    @property
    def rr_job_variablesFunc(self):
        try:
            return addRenderman_Renderer(self._node.parm("renderer").eval() )
        except:
            pass
        return ""


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