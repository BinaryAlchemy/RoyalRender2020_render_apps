# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode, rrNode
from htorr.rroutput import Output, ProductOutput
import logging


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")

        
def getFilename_convertFrameNr(parm):
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
    newName= "<FN" + str(padding) + ">"
    newName=fr9[:posFr] + newName + fr9[posFrEnd:]
    logger.debug("getFilename_convertFrameNr: {} ".format(newName))

    return newName
        

class rrPythonRop(rrNode):

    name = "rrPythonScript"

    def parse_init(self):
        self.cached_renderproductCount= None
        self.cached_renderproductList= []
        
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
        return (start, end, inc)

    @property
    def rr_jobsettings(self):
        """custom job settings from sparse parameter"""
        try:
            jobsettings = self._node.parm("rr_jobsettings").evalAsString()
        except:
            jobsettings = ""
        return jobsettings

    @property
    def rr_job_variables(self):
        """custom job variables from sparse parameter"""
        try:
            jobvariables = self._node.parm("rr_job_variables").evalAsString()
        except:
            jobvariables = ""
        return jobvariables

    @property
    def rr_env_variables(self):
        """custom env variables from sparse parameter"""
        try:
            envvariables = self._node.parm("rr_env_variables").evalAsString()
        except:
            envvariables = ""
        return envvariables

    @property
    def rr_job_variablesFunc(self):
        scriptPath = self._node.parm("pythonScript").evalAsString()
        flagA = self._node.parm("flagA").evalAsString()
        flagB = self._node.parm("flagB").evalAsString()
        flagC = self._node.parm("flagC").evalAsString()
        addFlags= "Script=" + scriptPath + ";"
        if (flagA and len(flagA)>0):
            addFlags= addFlags + "FlagA=" + flagA + ";"
        if (flagB and len(flagB)>0):
            addFlags= addFlags + "FlagB=" + flagB + ";"
        if (flagC and len(flagC)>0):
            addFlags= addFlags + "FlagC=" + flagC + ";"
        return addFlags

    @property
    def rr_jobsettingsFunc(self):
        try:
            parm = self._node.parm("additionalParams")
            parmValue = parm.eval() 
            if len(parmValue)>0:
                return 'AdditionalCommandlineParam=0~1~{};'.format(parmValue)
        except:
            pass
        return ""

        
    def childclass_parse(self, parseData):
        """Creating a Job instance and parsing all node properties to job properties.
        Additionally do some validation.
        """
        self.parse_init()
        
        job = parseData.Job.create()
        job.software = "Houdini"
        job.software_version = hou.applicationVersionString()
        job.renderer = "Python"
        job.scene = hou.hipFile.path()
        job.layer = self._node.path()
        job.outname = ""
        job.outdir = ""
        job.outext = ""
        job.padding = 1
        job.camera = ""
        job.set_frange(self.frange)
        job.scene_database_dir =  hou.getenv("HIP") 
        job.single_output = True
        job.sceneVar_Job = hou.getenv("JOB","")



        jobsettings = self.rr_jobsettings
        if not jobsettings == "":
            try:
                for setting in jobsettings.split(";"):
                    settingname = setting.split("=")[0]
                    settingvalues = setting.split("=")[-1]
                    values = settingvalues.split("~")
                    logger.debug("Found custom job option: {} Value: {}".format(settingname, values))
                    job.add_custom_option(settingname, values)
                    logger.debug("Submitoptions: {}".format(job.options))
            except:
                logger.info("wrong fromat: rr_jobsettings")

        jobsettings = self.rr_jobsettingsFunc
        if not jobsettings == "":
            try:
                for setting in jobsettings.split(";"):
                    settingname = setting.split("=")[0]
                    settingvalues = setting.split("=")[-1]
                    values = settingvalues.split("~")
                    logger.debug( "Found custom job option: {} Value: {}".format(settingname, values) )
                    job.add_custom_option(settingname, values)
                    logger.debug("Submitoptions Func: {}".format(job.options))
            except:
                logger.info("wrong fromat: rr_jobsettingsFunc")

        jobvariables = self.rr_job_variables
        if not jobvariables == "":
            try:
                for var in jobvariables.split(";"):
                    equalSign= var.find("=")
                    if (equalSign>0):
                        varname = var[:equalSign]
                        varvalue = var[equalSign+1:]
                        varname= varname.strip()
                        varvalue= varvalue.strip()
                        customvarname = "Custom{}".format(varname)
                        logger.debug("Found custom job variable: '{}'  Value: '{}'".format(customvarname, varvalue))
                        job.add_custom_option(customvarname, varvalue, "custom")
            except:
                logger.info("wrong format: rr_job_variables")

        jobvariables = self.rr_job_variablesFunc
        if not jobvariables == "":
            try:
                for var in jobvariables.split(";"):
                    equalSign= var.find("=")
                    if (equalSign>0):
                        varname = var[:equalSign]
                        varvalue = var[equalSign+1:]
                        varname= varname.strip()
                        varvalue= varvalue.strip()
                        customvarname = "Custom{}".format(varname)
                        logger.debug("Found custom job variable: '{}'  Value: '{}'".format(customvarname, varvalue))
                        job.add_custom_option(customvarname, varvalue, "custom")
            except:
                logger.info("wrong format: rr_job_variables")
                
        envvariables = self.rr_env_variables
        if not envvariables == "":
            try:
                for var in envvariables.split(";"):
                    equalSign= var.find("=")
                    if (equalSign>0):
                        varname = var[:equalSign]
                        varvalue = var[equalSign+1:]
                        varname= varname.strip()
                        varvalue= varvalue.strip()
                        logger.debug("Found custom env variable: '{}' Value: '{}'".format(varname, varvalue) )
                        job.add_custom_option(varname, varvalue, "env")
            except:
                logger.info("wrong format: rr_env_variables")

        return job
        

class rrGenericRop(RenderNode):

    name = "rrGenericJob"

    @property
    def scene(self):
        parm = self._node.parm("scenefile")
        parmValue = getFilename_convertFrameNr(parm)
        return parmValue
        
    @property
    def renderer(self):
        parm = self._node.parm("renderer")
        parmValue = parm.eval() 
        return parmValue
        
    @property
    def software(self):
        parm = self._node.parm("renderapp")
        parmValue = parm.eval() 
        return parmValue
        
    @property
    def software_version(self):
        parm = self._node.parm("renderapp_version1")
        parmValue = parm.eval() 
        parm2 = self._node.parm("renderapp_version2")
        parmValue2 = parm2.eval() 
        return parmValue + "." + parmValue2
        
    @property
    def renderer_version(self):
        parm = self._node.parm("renderer_version1")
        parmValue = parm.eval() 
        parm2 = self._node.parm("renderer_version2")
        parmValue2 = parm2.eval() 
        return parmValue + "." + parmValue2
        
    @property
    def path(self):
        parm = self._node.parm("layer")
        parmValue = parm.eval() 
        return parmValue
        
    @property       
    def output_parm(self):
        return  "outputfile"
        
    @property
    def output_evalAtFrameA(self):        
        outName=super(rrGenericRop, self).output_evalAtFrameA
        if self._node.evalParm("execute_output"):
            if len(outName)<4:
                return "<SceneFolder>"
        return outName
        
    @property
    def output_evalAtFrameB(self):
        outName=super(rrGenericRop, self).output_evalAtFrameB
        if self._node.evalParm("execute_output"):
            if len(outName)<4:
                return "<SceneFolder>"
        return outName

    @property
    def outdir(self):    
        outName=super(rrGenericRop, self).outdir
        if self._node.evalParm("execute_output"):
            if len(outName)<4:
                return "<SceneFolder>"
        return outName
        
    @property
    def outname(self):
        outName=super(rrGenericRop, self).outname
        if self._node.evalParm("execute_output"):
            if len(outName)<4:
                return "<SceneFolder>"
        return outName
        
    @property
    def outext(self):
        if self._node.evalParm("execute_output"):
            return ""
        return super(rrGenericRop, self).outext
    
    @property
    def single_output(self):
        if self._node.evalParm("execute_output"):
            return True
        if self._node.evalParm("output_single"):
            return True
        return False

        

class rrDenoiseRop(RenderNode):

    name = "rrdenoise"

    @property
    def scene(self):
        parm = self._node.parm("inputfile")
        parmValue = getFilename_convertFrameNr(parm)
        return parmValue
        
    @property
    def renderer(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.eval() 
        if (parmValue=="rman"):
            return "Denoise"
        elif (parmValue=="arnold"):
            return "DeNoice"
        elif (parmValue=="hou_nvidia"):
            return "NVidia_GPU"
        return "Intel_CPU"
        
    @property
    def software(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.eval() 
        if (parmValue=="rman"):
            return "RenderMan"
        elif (parmValue=="arnold"):
            return "Arnold"
        return "iDeNoise"
        
    @property
    def software_version(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.eval() 
        if (parmValue=="rman"):
            import htorr.rrnode.rop.rr_renderman as rr_renderman
            return  rr_renderman._getRendermanVersion()
        elif (parmValue=="arnold"):
            import htorr.rrnode.rop.rr_arnold as rr_arnold
            return rr_arnold._getArnoldVersion()
        return hou.applicationVersionString()
        
    @property       
    def output_parm(self):
        return  "outputfile"
        
    @property
    def outname(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.eval() 
        if (parmValue=="rman"):
            rrout = Output(self._node.parm("inputfile"), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return rrout.name
        return super(rrDenoiseRop, self).outname

    @property
    def outext(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.eval() 
        if (parmValue=="rman"):
            rrout = Output(self._node.parm("inputfile"), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return rrout.extension
        return super(rrDenoiseRop, self).outext

    @property
    def outpadding(self):
        """Property for the output padding count
        If applicable override output_parm
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            productout = ProductOutput(self.cached_renderproductList[self.cached_renderproductCount-1]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return productout.padding         
        rrout = Output(self._node.parm(self.output_parm), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        return rrout.padding
        
    @property
    def single_output(self):
        return False        

    @property
    def rr_job_variablesFunc(self):
        parm = self._node.parm("denoiser")
        parmValue = parm.evalAsString() 
        if (parmValue=="arnold"):
            return ""
        elif (parmValue=="rman"):
            addFlags=""
            alpha = self._node.parm("aov_alpha").evalAsString()
            albedo = self._node.parm("aov_albedo").evalAsString()
            diffuse = self._node.parm("aov_diffuse").evalAsString()
            irradiance = self._node.parm("aov_irradiance").evalAsString()
            specular = self._node.parm("aov_specular").evalAsString()
            if (alpha and len(alpha)>0):
                addFlags= addFlags + "AlphaName=" + alpha + ";"
            if (albedo and len(albedo)>0):
                addFlags= addFlags + "AlbedoName=" + albedo + ";"
            if (diffuse and len(diffuse)>0):
                addFlags= addFlags + "DiffuseName=" + diffuse + ";"
            if (irradiance and len(irradiance)>0):
                addFlags= addFlags + "IrradianceName=" + irradiance + ";"            
            if (specular and len(specular)>0):
                addFlags= addFlags + "SpecularName=" + specular + ";"            
            return addFlags
        else:    
            addFlags=""
            normal = self._node.parm("hou_normal").evalAsString()
            albedo = self._node.parm("hou_albedo").evalAsString()
            aov = self._node.parm("hou_aov").evalAsString()
            motion = self._node.parm("hou_motion").evalAsString()
            if (normal and len(normal)>0):
                addFlags= addFlags + "NormalName=" + normal + ";"
            if (albedo and len(albedo)>0):
                addFlags= addFlags + "AlbedoName=" + albedo + ";"
            if (motion and len(motion)>0):
                addFlags= addFlags + "MotionName=" + aov + ";"
            if (aov and len(aov)>0):
                addFlags= addFlags + "AOVNames=" + aov + ";"

            opt=""
            if (parmValue=="hou_intel"):
                opt = self._node.parm("hou_option_oidn").evalAsString()
            else:
                opt = self._node.parm("hou_option_optix").evalAsString()
            if (opt and len(opt)>0):
                addFlags= addFlags + "Options=" + opt + ";"

            return addFlags
        
        
        
        
    @property
    def rr_jobsettingsFunc(self):
        options=""
        parm = self._node.parm("denoiser")
        parmValue = parm.evalAsString() 
        if (parmValue=="rman"):
            if (self._node.parm("rman_mode").evalAsString()=="single"):
                options='COCrossFrame=1~0; '
            else:
                options='COCrossFrame=1~1; '
            if (self._node.parm("rman_flow").eval()):
                options= options + 'COFlow=1~1;' 
            else:
                options= options + 'COFlow=1~0; ' 
            a= self._node.parm("rman_asymmetry").eval()
            options= options + 'COAsymmetryFloat=1~1~{}; '.format(int(a*100))
            return options
        elif (parmValue=="arnold"):
            nh= self._node.parm("a_neighborhood").eval()
            r= self._node.parm("a_radius").eval()
            v= self._node.parm("a_variance").eval()
            options= options + 'CONeighborhood=1~1~{}; COSearchRadius=1~1~{}; COVarianceFloat=1~1~{}; '.format(nh, r, int(v*100))
            return options
            
        #Houdini Intel and Optix
        if (self._node.parm("hou_prevFrame").eval()):
            options= options + 'COPrevFrame=1~1; MaxClientsAtATime=0~1; ' 
        else:
            options= options + 'COPrevFrame=1~0; ' 
            
        return options
