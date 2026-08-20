# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import os.path
from htorr.rroutput import Output, ProductOutput
from htorr.rrnode.base import RenderNode
import traceback
from pxr import UsdRender

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
        #logger.debug("No renderer set or unable to read: {}".format(traceback.format_exc()))       
        return _NAME_Karma
        
    if (ren == None):
        logger.debug("No renderer set, using Karma ")  
        return _NAME_Karma
        
    ren = ren.lower()
    
    if (len(ren)==0):
        return _NAME_Karma
    if (ren == ("Karma").lower()):
        return _NAME_Karma
    if (ren == ("BRAY_HdKarma").lower()):
        return _NAME_Karma
    if (ren == ("KarmaXPU").lower()):
        return _NAME_Karma
    if (ren == ("BRAY_HdKarmaXPU").lower()):
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


def addKarma_Renderer(renderer):
    renderer = renderer.lower()
    if ("xpu" in renderer):
        return "KarmaRenderer=XPU"
    return ""



def replace_frame_placeholders(text, frame):
    #<F1> is supported by e.g. husk commandline, but not inside Houdini UI
    text = text.replace("<F1>", "$F1")
    text = text.replace("<F2>", "$F2")
    text = text.replace("<F3>", "$F3")
    text = text.replace("<F4>", "$F4")
    text = text.replace("<F5>", "$F5")
    text = text.replace("<F6>", "$F6")
    text = text.replace("<F7>", "$F7")
    text = text.replace("<F8>", "$F8")
    text= hou.text.expandStringAtFrame(text, frame)
    return text


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
            if renderer==_NAME_Karma:
                return addKarma_Renderer(self._node.parm("renderer").eval() )
        except:
            pass
        return ""


    @property
    def single_output(self):
        if self._node.evalParm("fileperframe"):
            f1 = replace_frame_placeholders(self._node.parm(self.output_parm).evalAtFrame(1),1)
            f2 = replace_frame_placeholders(self._node.parm(self.output_parm).evalAtFrame(2),2)
            #logger.debug("{}: UsdRop single_output: {} ".format(self._node.path(), f1))               
            #logger.debug("{}: UsdRop single_output: {} ".format(self._node.path(), f2))               
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
            #logger.debug("{}: outputimage set for archive ".format(self._node.path()))               
            outputFound=True
        except:
            #logger.debug("{}: no outputimage for archive ".format(self._node.path()))  
            pass
        
        if not outputFound:
            stage= None
            import loputils
            lop = self._node.evalParm('loppath')
            #logger.debug("renderproductList: lop is {}".format(lop))
            if self._node.input(0):
                input = self._node.input(0)
                stage = input.stage()
            elif lop:
                lop = self._node.parm("loppath").evalAsNode()
                stage = lop.stage() 
            else:
                logger.error("{}: loppath not set: {}".format(self._node.path(), self._node.evalParm('loppath')))     
            
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

    def getStage(self):
        stage= None
        import loputils
        lop = self._node.evalParm('loppath')
        if self._node.input(0):
            input = self._node.input(0)
            stage = input.stage() # Houdini-native HUSD stage
            #logger.debug("{}: stage from node.input(0)")     
        elif lop:
            lop = self._node.parm("loppath").evalAsNode()
            stage = lop.stage()  # Houdini-native HUSD stage
            #logger.debug("{}: stage from lop.stage() ")     
        else:
            logger.error("{}: loppath not set: {}".format(self._node.path(), self._node.evalParm('loppath')))     
        return stage
        
        
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
        if renderer==_NAME_Arnold:
            return super(UsdStandalone, self).software_version

        if renderer==_NAME_Karma:
            return ""
       
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
    def software_version(self):
        renderer= detectRenderEngine(self._node.parm("renderer"))
        if renderer==_NAME_Arnold:
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()

        return super(UsdStandalone, self).software_version

    @property
    def rr_job_variablesFunc(self):
        try:
            renderer= detectRenderEngine(self._node.parm("renderer"))
            if renderer==_NAME_Renderman:
                return addRenderman_Renderer(self._node.parm("renderer").eval() )
            if renderer==_NAME_Karma:
                return addKarma_Renderer(self._node.parm("renderer").eval() )
                
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
            jobParams= jobParams +  'COSingleRenderProduct=1~1; '
        else:
            jobParams= jobParams +  'AllowLocalRenderOut=0~0; COSingleRenderProduct=0~0; '

        try:
            ren = renderer_parm.eval() 
        except:
            pass
        else:
            if (ren != None):
                ren = ren.lower()
                if "xpugpu" in ren:
                    jobParams= jobParams + 'GPUrequired=0~1; '

        logger.debug("{}: rr_jobsettingsFunc: {} ".format(self._node.path(), jobParams)) 
        
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
        stage= self.getStage()

        if (stage== None):
            logger.debug("{}: no stage found! ".format(self._node.path()))     
            return []

        allproducts = []
        products = stage.GetPrimAtPath("/Render/Products")
        if not products:
            logger.debug("{}: no render products found! ".format(self._node.path()))     
            return []
        productchildren = products.GetAllChildren()
        for prim in productchildren:
            product = {}
            product["name"] = prim.GetName()
            isValidImage=False
            
            a = prim.GetAttribute("productName")
            if a:
                #logger.debug("{}: rendersettings product '{}' '{}'   '{}' ".format(self._node.path(), prim.GetName(), a.Get(0),a.Get(999999) ))     
                product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                isValidImage= product["productOutname"].find("checkpoint")<0 
                product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                product["productOutnameB"] = a.Get(999999) 
                product["attrib"] = a
                
            if a:
                a = prim.GetAttribute("resolution")
                product["resX"] = a.Get()[0]
                product["resY"] = a.Get()[1]
                
            if (isValidImage):
                allproducts.append(product)
                

        renderSettings = stage.GetPrimAtPath("/Render/rendersettings")        
        if renderSettings.IsValid():
            #Render settings overrides the render product to render    
            #Note:  "/Render/rendersettings/products" is not a real prim in the USD stage; it’s a relationship container or “pseudo-prim” that Houdini shows in Solaris.
            settings = UsdRender.Settings(renderSettings)
            rel = settings.GetProductsRel()
            if rel:
                product_paths = rel.GetTargets()  # returns list of prim paths
                if len(product_paths)>0:
                    allproducts = []
                    for path in product_paths:
                        prim = stage.GetPrimAtPath(path)
                        
                        product = {}
                        product["name"] = prim.GetName()
                        isValidImage=False
                        
                        a = prim.GetAttribute("productName")
                        if a:
                            #logger.debug("{}: rendersettings product '{}' '{}'   '{}' ".format(self._node.path(), prim.GetName(), a.Get(0),a.Get(999999) ))     
                            product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                            isValidImage= product["productOutname"].find("checkpoint")<0 
                            product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                            product["productOutnameB"] = a.Get(999999) 
                            product["attrib"] = a
                            
                        if a:
                            a = prim.GetAttribute("resolution")
                            product["resX"] = a.Get()[0]
                            product["resY"] = a.Get()[1]
                        
                        if (isValidImage):
                            allproducts.append(product)
                    allproducts.reverse()
            
            
            #Render settings overrides the resolution     
            res_attr = renderSettings.GetAttribute("resolution")
            if res_attr:
                resolution = res_attr.Get()    
                width  = int(resolution[0])
                height = int(resolution[1])
                #logger.debug("{}: rendersettings res override {}x{} ".format(self._node.path(),width,height))     
                for product in allproducts:
                    product["resX"] = width
                    product["resY"] = height        
                
        #printList_Debug("renderproductList", allproducts)
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

    @property
    def frange(self):
        """Property for frame range.
        Returns Tuple (Frame Start, Frame End, Frame Increment)
        """
        start = self._node.evalParm("f1")
        end = self._node.evalParm("f2")
        inc = self._node.evalParm("f3")
        try:
            framemode = self._node.evalParm("trange")
        except:
            framemode=1
        if framemode == 0:  # Render current frame
            start = int(hou.frame())
            end = int(hou.frame())
            inc = 1
        elif framemode == 3:  # Render stage
            stage= self.getStage()
            if (stage != None):
                tcps = stage.GetTimeCodesPerSecond()
                fps = hou.fps()
                #other function available in case this does not work: "Houdini-native HUSD stage: use timeRange() frame_range = stage.timeRange()"
                start = stage.GetStartTimeCode()
                end = stage.GetEndTimeCode()
                
                start = int(start * fps / tcps) - self._node.evalParm("foffset1")
                end   = int(  end * fps / tcps) + self._node.evalParm("foffset2")
            
        #logger.debug("{} frange {}-{},{}    framemode: {}".format( self._node.path(), start, end, inc, framemode))
        return (start, end, inc)  

class UsdRenderRop(RenderNode):
    """ USD ROP to render """

    name = "usdrender"
    
    
    def getStage(self):
        stage= None
        import loputils
        lop = self._node.evalParm('loppath')
        if self._node.input(0):
            input = self._node.input(0)
            stage = input.stage() # Houdini-native HUSD stage
            #logger.debug("{}: stage from node.input(0)")     
        elif lop:
            lop = self._node.parm("loppath").evalAsNode()
            stage = lop.stage()  # Houdini-native HUSD stage
            #logger.debug("{}: stage from lop.stage() ")     
        else:
            logger.error("{}: loppath not set: {}".format(self._node.path(), self._node.evalParm('loppath')))     
        
        return stage
            
            
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
            if renderer==_NAME_Karma:
                return addKarma_Renderer(self._node.parm("renderer").eval() )
                
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
        stage= self.getStage()

        if (stage== None):
            logger.debug("{}: no stage found! ".format(self._node.path()))     
            return []

        allproducts = []
        products = stage.GetPrimAtPath("/Render/Products")
        if not products:
            logger.debug("{}: no render products found! ".format(self._node.path()))     
            return []
        productchildren = products.GetAllChildren()
        for prim in productchildren:
            product = {}
            product["name"] = prim.GetName()
            isValidImage=False
            
            a = prim.GetAttribute("productName")
            if a:
                #logger.debug("{}: rendersettings product '{}' '{}'   '{}' ".format(self._node.path(), prim.GetName(), a.Get(0),a.Get(999999) ))     
                product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                isValidImage= product["productOutname"].find("checkpoint")<0 
                product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                product["productOutnameB"] = a.Get(999999) 
                product["attrib"] = a
                
            if a:
                a = prim.GetAttribute("resolution")
                product["resX"] = a.Get()[0]
                product["resY"] = a.Get()[1]
                
            if (isValidImage):
                allproducts.append(product)
                

        renderSettings = stage.GetPrimAtPath("/Render/rendersettings")        
        if renderSettings.IsValid():
            #Render settings overrides the render product to render    
            #Note:  "/Render/rendersettings/products" is not a real prim in the USD stage; it’s a relationship container or “pseudo-prim” that Houdini shows in Solaris.
            settings = UsdRender.Settings(renderSettings)
            rel = settings.GetProductsRel()
            if rel:
                product_paths = rel.GetTargets()  # returns list of prim paths
                if len(product_paths)>0:
                    allproducts = []
                    for path in product_paths:
                        prim = stage.GetPrimAtPath(path)
                        
                        product = {}
                        product["name"] = prim.GetName()
                        isValidImage=False
                        
                        a = prim.GetAttribute("productName")
                        if a:
                            #logger.debug("{}: rendersettings product '{}' '{}'   '{}' ".format(self._node.path(), prim.GetName(), a.Get(0),a.Get(999999) ))     
                            product["productOutname"] = a.Get(0) #this should get the name with variables, but .Get() returns nothing...
                            isValidImage= product["productOutname"].find("checkpoint")<0 
                            product["productOutnameA"] = a.Get(1) #automatically cropped to start of nodes frame range. Frame range might be set in ROP only, then render product has frame range "current frame" only...
                            product["productOutnameB"] = a.Get(999999) 
                            product["attrib"] = a
                            
                        if a:
                            a = prim.GetAttribute("resolution")
                            product["resX"] = a.Get()[0]
                            product["resY"] = a.Get()[1]
                        
                        if (isValidImage):
                            allproducts.append(product)
                    allproducts.reverse()
        
        
            #Render settings overrides the resolution     
            res_attr = renderSettings.GetAttribute("resolution")
            if res_attr:
                resolution = res_attr.Get()    
                width  = int(resolution[0])
                height = int(resolution[1])
                #logger.debug("{}: rendersettings res override {}x{} ".format(self._node.path(),width,height))     
                for product in allproducts:
                    product["resX"] = width
                    product["resY"] = height        
                
        #printList_Debug("renderproductList", allproducts)
        return allproducts     


    @property
    def frange(self):
        """Property for frame range.
        Returns Tuple (Frame Start, Frame End, Frame Increment)
        """
        start = self._node.evalParm("f1")
        end = self._node.evalParm("f2")
        inc = self._node.evalParm("f3")
        try:
            framemode = self._node.evalParm("trange")
        except:
            framemode=1
        if framemode == 0:  # Render current frame
            start = int(hou.frame())
            end = int(hou.frame())
            inc = 1
        elif framemode == 3:  # Render stage
            stage= self.getStage()
            if (stage != None):
                tcps = stage.GetTimeCodesPerSecond()
                fps = hou.fps()
                #other function available in case this does not work: "Houdini-native HUSD stage: use timeRange() frame_range = stage.timeRange()"
                start = stage.GetStartTimeCode()
                end = stage.GetEndTimeCode()
                
                start = int(start * fps / tcps) - self._node.evalParm("foffset1")
                end   = int(  end * fps / tcps) + self._node.evalParm("foffset2")
            
        #logger.debug("{} frange {}-{},{}    framemode: {}".format( self._node.path(), start, end, inc, framemode))
        return (start, end, inc)       
                

class UsdRenderRop_LOP(UsdRenderRop):
    """ USD stage/LOP ROP to render """
    name = "usdrender_rop"
    
    
    
class Karma_LOP(RenderNode):
    """ Karma LOP to render """

    name = "karma"

    def getStage(self):
        stage= None
        import loputils
        lop = self._node.evalParm('loppath')
        if self._node.input(0):
            input = self._node.input(0)
            stage = input.stage() # Houdini-native HUSD stage
            #logger.debug("{}: stage from node.input(0)")     
        elif lop:
            lop = self._node.parm("loppath").evalAsNode()
            stage = lop.stage()  # Houdini-native HUSD stage
            #logger.debug("{}: stage from lop.stage() ")     
        else:
            logger.error("{}: loppath not set: {}".format(self._node.path(), self._node.evalParm('loppath')))     
        return stage
        
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

    @property
    def frange(self):
        """Property for frame range.
        Returns Tuple (Frame Start, Frame End, Frame Increment)
        """
        start = self._node.evalParm("f1")
        end = self._node.evalParm("f2")
        inc = self._node.evalParm("f3")
        try:
            framemode = self._node.evalParm("trange")
        except:
            framemode=1
        if framemode == 0:  # Render current frame
            start = int(hou.frame())
            end = int(hou.frame())
            inc = 1
        elif framemode == 3:  # Render stage
            stage= self.getStage()
            if (stage != None):
                tcps = stage.GetTimeCodesPerSecond()
                fps = hou.fps()
                #other function available in case this does not work: "Houdini-native HUSD stage: use timeRange() frame_range = stage.timeRange()"
                start = stage.GetStartTimeCode()
                end = stage.GetEndTimeCode()
                
                start = int(start * fps / tcps) - self._node.evalParm("foffset1")
                end   = int(  end * fps / tcps) + self._node.evalParm("foffset2")
            
        #logger.debug("{} frange {}-{},{}    framemode: {}".format( self._node.path(), start, end, inc, framemode))
        return (start, end, inc)  

    
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