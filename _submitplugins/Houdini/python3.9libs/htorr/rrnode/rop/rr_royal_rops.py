# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode, rrNode
import logging


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


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
                return '"AdditionalCommandlineParam=0~1~{}"'.format(parmValue)
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
        parmValue = parm.eval()     
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
        if self._node.evalParm("execute_output"):
            return "<SceneFolder>"
        return super(rrGenericRop, self).output_evalAtFrameA
        
    @property
    def output_evalAtFrameB(self):
        if self._node.evalParm("execute_output"):
            return "<SceneFolder>"
        return super(rrGenericRop, self).output_evalAtFrameB

    @property
    def outdir(self):    
        if self._node.evalParm("execute_output"):
            return "<SceneFolder>"
        return super(rrGenericRop, self).outdir
        
    @property
    def outname(self):
        if self._node.evalParm("execute_output"):
            return ""
        return super(rrGenericRop, self).outname
        
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