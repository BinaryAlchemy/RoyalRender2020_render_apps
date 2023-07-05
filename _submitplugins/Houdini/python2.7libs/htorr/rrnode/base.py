# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import abc
import logging
import re
import htorr.rrparser
import os
import sys
from htorr.rroutput import Output, ProductOutput

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


class rrNode(object):
    """Base Class for all Royal Render Node Wrapper Classes

    All Houdini node wrapper classes should inherit from this class
    and override the childclass_parse method which describes its parsing behavior.

    Most properties are implemented as methods with the property decorator (@property),
    which enables properties with special behavior. While implemented as a method, the properties are accessed normally without parenthesis.

    """

    __metaclass__ = (
        abc.ABCMeta
    )  # meta class which enables the use of abstractmethod decorators

    REGISTRY = {}  # dict of all subclasses with key: cls.name value: cls

    name = "base"  # name for houdini type this wrapper is used for

    def __init__(self, node):
        self._node = node  # original Houdini node instance
        self.logger = logging.getLogger(__name__ + "." + self.name)

        if node:
            #logger.debug(self.path + ": rrNode of type {} created".format(self.name))
            pass

    @abc.abstractmethod
    def childclass_parse(self, parseData):
        """Abstract parse method which must be overriden by child classes to alter behavior when parsed.

        Arguments:
            parseData ParseData -- parseData instance which is used to parse a node into a RR submission
        """
        pass

    @property
    def path(self):
        """Returns {string} path to node in houdini scene"""
        return self._node.path()

    @staticmethod
    def _register_node(name, cls):
        rrNode.REGISTRY[name] = cls

    def dependencies(self):
        """Returns list of houdini nodes which this node depends on 

        Returns:
            hou.Node[] -- List of houdini nodes
        """
        return self._node.inputs()

    def parse(self, parseData):
        """Parses the underlying Houdini node into a Royal Render Submission using the provided parseData.

        Override childclass_parse method in child classed to alter functionality for parsing.
        This method provides some standard parsing funtionality, valid for all subclasses.

        Arguments:
            parseData {htorr.rrparser.ParseData} -- [parseData instance which provides needed fuctionality]
        """
        if self._node.isBypassed():
            self.parse_bypassed(parseData)
        else:
            self.childclass_parse(parseData)

    def parse_bypassed(self, parseData):
        """Parsing behavior when node is bypassed.

        Arguments:
            parseData {htorr.rrparser.ParseData} -- [parseData instance which provides needed fuctionality]
        """
        logger.debug(
            self.path
            + ": Bypassing rrNode of type {} and parsing inputs".format(self.name)
        )
        for i in self._node.inputs():
            n = rrNode.create(i)
            n.parse(parseData)

    @staticmethod
    def create(node):
        """Factory Function to create a Royal Render node instance from a houdini node.

        Depending on the provided Houdini node type this factory function creates an instance of the appropriate
        Royal Render rrNode wrapper class and returns it.

        Arguments:
            node hou.Node -- Houdini Node which will be wrapped by created instance

        Raises:
            ValueError: Value Error if no wrapper class existst for incoming houdini node

        Returns:
            rrNode -- Royal Render node of appropriate type
        """

        if not node:
            raise ValueError("Cant create Node from None objects")

        # node type name as [namespace::]node_name[::version]
        type_ = node.type().nameComponents()[-2]

        if type_ in rrNode.REGISTRY:
            return rrNode.REGISTRY[type_](node)

        elif node.childTypeCategory() == hou.ropNodeTypeCategory():
            return SubnetNode(node)

        else:
            return NoRrNode(node)

    def jobs(self):
        p = htorr.rrparser.ParseData()
        self.parse(p)
        return p.SubmissionFactory.get()

    @property
    def software(self):
        """Property for software name"""
        return "Houdini"

    @property
    def software_version(self):
        """Property software version"""
        return hou.applicationVersionString()
        
    @property
    def scene_database_dir(self):
        """Property for Houdini project directory"""
        return hou.getenv("HIP")        
        
    @property
    def scene(self):
        """Property for Houdini file path"""
        return hou.hipFile.path()

    @property
    def take(self):
        """Property for take name"""
        try:
            if len(hou.takes.takes()) < 2:
                return ""
            take = self._node.evalParm("take")
            if take == "_current_":
                take = hou.takes.currentTake().name()
            return take        
        except:
            return ""

    @property
    def sceneVar_Job(self):
        return hou.getenv("JOB","")

class NoRrNode(rrNode):
    """
    Wrapper Class for all not supported rrNode Types.
    """

    name = "notImplemented"

    def parse(self, parseData):
        if (
            self._node.type().name() != "shell"
            and self._node.type().name() != "renderproduct"
            and self._node.type().name() != "rendersettings"
            and self._node.type().name() != "output"
        ):  
            logger.debug( "{}: Nodetype {} not supported".format( self._node.path(), self._node.type().name() )  )

    def childclass_parse(self):
        pass


class SubnetNode(rrNode):
    """Wrapper Class for all node types which constain ROP networks themselves."""

    name = "subnet"

    def childclass_parse(self, parseData):
        for child_node in self._node.children():
            if not child_node.outputs():
                n = rrNode.create(child_node)
                n.parse(parseData)

    def dependencies(self):
        return self._node.inputs() + self._node.children()


class FetchNode(rrNode):
    """Wrapper Class for all node types which constain ROP networks themselves."""

    name = "fetch"

    def childclass_parse(self, parseData):
        source = self._node.evalParm("source")
        if len(source) > 0:
            sourceNode = self._node.parm("source").evalAsNode()
            n = rrNode.create(sourceNode)
            n.parse(parseData)

    def dependencies(self):
        retNodes = self._node.inputs()
        source = self._node.evalParm("source")
        if len(source) > 0:
            sourceNode = self._node.parm("source").evalAsNode()
            retNodes = retNodes + (sourceNode,)
        logger.debug("{}: dependencies are: {} ".format(self._node.path(), retNodes))
        return retNodes


class RenderNode(rrNode):
    """Wrapper for Houdini Nodes which generates Jobs when parsed.

    Base Class for all Houdini Rop Nodes which actually generated Royal Render Jobs when parsed.
    Usually these are ROP nodes which generate files like Mantra, OpenGL or Alembic.

    This class implements many properties which will be coverted to job parameters when parsed.
    To implement a new wrapper class for a render node, inherit from this class and override the properties which are applicable.
    Try not to override the parse and childclass_parse method.
    """

    name = "renderNodeBase"
   
    def parse_init(self):
        self.cached_renderproductCount= None
        self.cached_renderproductList= []
    
    def parse(self, parseData):
        """Parsing a rrNode into Royal Render submission.

        The methods parse and childclass_parse should not be overridden by any subclass.
        parse and childclass_parse implement all necessary features to parse a render node into a job instance.
        This method converts all implemented properties to appropriate job parameters.
        If archive render is enabled, the node is first casted to its archive representation, parsed, casted to a standalone representation
        and then parsed again. For both parsing the childclass_parse method is used.
        ALl nodes which support archive rendering, have to implement to_archive and to_standalone to cast the wrapper instance to the appropriate class.

        """
       
        # check if node is bypassed
        if self._node.isBypassed():
            return

        if not self.check():
            return
        

        # if node has renderproducts
        #if (self.renderproductCount > 0):
            # Parse Archive
        #    self.to_archive()
        #    archive_job = self.childclass_parse(parseData)

            # Render Jobs
        #    self.to_standalone()
        #    joblist = self.renderproduct_childclass_parse(parseData)
        #    logger.debug("Renderproduct jobs: {}".format(joblist))
        #    for job in joblist:
        #        job.set_dependency([archive_job])
        #    return

        # if node is not an archive render call childclass_parse without casting.
        if not self.archive:
            self.childclass_parse(parseData)
        else:
            # parse 2 nodes when node is an archive render
            # one to be the archive job
            
            
            archive_create= (parseData.archive_mode==0) or (parseData.archive_mode==1)
            archive_render= (parseData.archive_mode==0) or (parseData.archive_mode==2)

            
            if archive_create:
                self.to_archive()
                archive_job = self.childclass_parse(parseData)
            else:
                #we do not want to add the archive job to our main parseData as a job
                #but we need to parse it to get the output image
                parserTemp = htorr.rrparser.ParseData()
                archive_job = self.childclass_parse(parserTemp)

            archiveScene=""
            if archive_job.outdir:
                if not archive_job.single_output:
                    out_file = "{}<FN{}>{}".format(archive_job.outname, archive_job.padding, archive_job.outext)
                    archiveScene = os.path.join(archive_job.outdir, out_file)
                else:
                    out_file = "{}{}".format(archive_job.outname, archive_job.outext)
                    archiveScene = os.path.join(archive_job.outdir, out_file)
            else:
                archiveScene = archive_job.outname

            # the other as standalone job
            if archive_render:
                self.to_standalone()

                standalone_job = self.childclass_parse(parseData)
                standalone_job.scene = archiveScene
                if (archive_create):
                    standalone_job.set_dependency([archive_job])

    def childclass_parse(self, parseData):
        """Creating a Job instance and parsing all node properties to job properties.
        Additionally do some validation.
        """
        self.parse_init()
        
        job = parseData.Job.create()
        job.software = self.software
        job.software_version = self.software_version
        job.renderer = self.renderer
        if job.renderer == None:
            job.renderer=""
        if (len(parseData.rendererPreSuffix)>0):
            job.renderer= parseData.rendererPreSuffix.replace("*", job.renderer)
        job.renderer_version = self.renderer_version
        job.scene = self.scene
        job.layer = self.path
        job.outname = self.outname
        job.outdir = self.outdir
        job.outext = self.outext
        job.padding = self.outpadding
        job.camera = self.camera
        job.set_frange(self.frange)
        job.set_image_size(self.image_size)
        job.pre_number_char = self.pre_number_char
        job.scene_database_dir = self.scene_database_dir
        job.channel = self.take
        job.aovs = self.aovs
        job.gpu = self.gpu
        job.single_output = self.single_output_eval
        job.sceneVar_Job = self.sceneVar_Job

#       This does not work for USD as the camera path in Solaris is different than the camera node in Houdini
#        if self.camera and not hou.node(self.camera):
#            camExist= False            
#            if (not camExist):
#                msg = "'{}': No valid camera at '{}'".format(self.path, self.camera)
#                logger.warning(msg)

        if len(self.outdir) == 0:
            msg = "'{}': No output name set".format(self._node.path())
            logger.warning(msg)

        if not self.single_output_eval:
            f1 = self.output_evalAtFrameA
            f2 = self.output_evalAtFrameB
            fcount = (self.frange[1] - self.frange[0]) / self.frange[2]
            if (f1 == f2) and (fcount > 1) and ((self.cached_renderproductCount is None) or (self.cached_renderproductCount == 0)):
                #self.cached_renderproductCount condition has to be set in case frame range was not set before renderproduct node.
                msg = "'{}': Output name missing frame number: '{}' for frame range {}-{}".format(self._node.path(), self.output_evalAtFrameA, self.frange[0], self.frange[1])
                logger.warning(msg)
                #logger.debug("'{}'  {} {} ".format(self.path, f1, f2 ))

        msg = "'{}': Output name frame number: '{}' for frame range {}-{}".format(self._node.path(), self.output_evalAtFrameA, self.frange[0], self.frange[1])
        logger.debug(msg)

        #always add python version. Required for some 3rdparty plugins to choose the right version (vray, renderman)
        pythonVer= str(sys.version_info.major) + "." +  str(sys.version_info.minor)
        job.add_custom_option("CustomHPyVerP", pythonVer, "custom")
        pythonVer= str(sys.version_info.major) + str(sys.version_info.minor)
        job.add_custom_option("CustomHPyVer", pythonVer, "custom")
        
        # add sparse parameter
        jobsettings = self.rr_jobsettingsFunc
        if not jobsettings == "":
            try:
                for setting in jobsettings.split(";"):
                    equalSign= setting.find("=")
                    if (equalSign>0):                
                        settingname = setting[:equalSign]
                        settingvalues = setting[equalSign+1:]
                        settingname= varname.strip()
                        settingvalues= varvalue.strip()
                        values = settingvalues.split("~")
                        logger.debug( "Found custom job option: {} Value: {}".format(settingname, values) )
                        job.add_custom_option(settingname, values)
                        logger.debug("Submitoptions Func: {}".format(job.options))
            except:
                logger.info("wrong fromat: rr_jobsettingsFunc")
                
        jobsettings = self.rr_jobsettings
        if not jobsettings == "":
            try:
                for setting in jobsettings.split(";"):
                    equalSign= setting.find("=")
                    if (equalSign>0):
                        settingname = setting[:equalSign]
                        settingvalues = setting[equalSign+1:]
                        settingname= varname.strip()
                        settingvalues= varvalue.strip()
                        values = settingvalues.split("~")
                        logger.debug("Found custom job option: {} Value: {}".format(settingname, values))
                        job.add_custom_option(settingname, values)
                        logger.debug("Submitoptions: {}".format(job.options))
            except:
                logger.info("wrong fromat: rr_jobsettings")

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
    """
    def renderproduct_childclass_parse(self, parseData):
        #Creating a Job List from Job instances and parsing all node properties to job properties.
       #Additionally do some validation.
       
        joblist = []
        productlist = self.renderproductList
        logger.debug("Create Jobs for Products: {}".format(productlist))
        for product in productlist:
            job = parseData.Job.create()
            job.software = self.software
            job.software_version = self.software_version
            job.renderer = self.renderer
            if (len(parseData.rendererPreSuffix)>0):
                job.renderer= parseData.rendererPreSuffix.replace("*", job.renderer)
            job.renderer_version = self.renderer_version
            job.scene = product.get("name",self.scene)
            job.layer = self.path

            productout = ProductOutput(product["attrib"])
            job.outname = productout.name
            job.outdir = productout.dir
            job.outext = productout.extension
            job.padding = productout.padding

            job.camera = self.camera
            job.set_frange(self.frange)
            # TODO add resolution (product["resX"],product["resY"])
            job.set_image_size(self.image_size)
            job.pre_number_char = self.pre_number_char
            job.scene_database_dir = self.scene_database_dir
            job.channel = self.take
            job.aovs = self.aovs
            job.gpu = self.gpu
            job.single_output = self.single_output
            job.sceneVar_Job = self.sceneVar_Job
            joblist.append(job)

        return joblist
    """

    @abc.abstractproperty
    def renderer(self):
        """Property for renderer name

        Returns:
            string -- renderer name

        Examples:
            Arnold, Alembic, Mantra
        """
        return

    @abc.abstractproperty
    def renderer_version(self):
        """Property for renderer version"""
        return

    @abc.abstractproperty
    def output_parm(self):
        """Property for the name of the output parameter."""
        return

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
        logger.debug("{} frange {}-{},{}    UICurrent: {}".format( self._node.path(), start, end, inc, hou.frame()))
        return (start, end, inc)

    @property
    def image_size(self):
        """Property for Image Size (Width, Height)"""
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):    
            return(self.cached_renderproductList[self.cached_renderproductCount-1]["resX"]  , self.cached_renderproductList[self.cached_renderproductCount-1]["resY"])

    @property
    def camera(self):
        """Property for camera path.
        If applicable override camera_parm
        """
        if not self.camera_parm:
            return
        path = self._node.evalParm(self.camera_parm)
        return path

    @property
    def camera_parm(self):
        """Property for camera parameter name"""
        return

    @property
    def stereo(self):
        """Boolean property whether the renderer writes two images per frame due to beeing stereo."""
        if self.camera:
            cam = hou.node(self.camera)
            if cam and cam.type().name() == "stereocamrig":
                return True

    @property
    def archive(self):
        """Boolean property whether archive render is enabled."""
        return False

    @property
    def rr_jobsettingsFunc(self):
        """User can add a rr_jobsettings spare parameter, but sometimes we want to support a different parameter name. Then this func returns settings"""
        return ""

    @property
    def rr_job_variablesFunc(self):
        """User can add a rr_job_variables spare parameter, but sometimes we want to support a different parameter name. Then this func returns job vars"""
        return ""

    @property
    def renderproductList(self):
        """List of all renderproducts."""
        return []

    @property
    def licenses(self):
        """Property for licence"""
        # self.logger.info("license property might be deprecated")
        return

    @property
    def pre_number_char(self):
        """ """
        return

    @property
    def aovs(self):
        """Property for AOVS
        Returns list of tuples for each extra file sequences which will be written.
        [[AOV1path, AOV1ext],[AOV2path,AOV2ext]]
        """
        return

    @property
    def gpu(self):
        """Boolean Property whether a GPU is required for rendering."""
        return False

    @property
    def single_output(self):
        """Property boolean whether the output is a single file"""
        return False

    @property
    def single_output_eval(self):
        """Property boolean whether the output is a single file"""
        return self.single_output
        
#    @property
#    def output(self):
#        """Property for the output file.
#        If applicable try to override output_parm.
#        """
#        logger.debug("***********************output ORIGINAL CALLED*********************")
#        if (self.cached_renderproductCount is None):
#            self.cached_renderproductList= self.renderproductList
#            self.cached_renderproductCount= len(self.cached_renderproductList)         
#        if (self.cached_renderproductCount>0):
#            return self.cached_renderproductList[self.cached_renderproductCount-1]["productOutname"]
#        return self._node.evalParm(self.output_parm)
        
    @property
    def output_evalAtFrameA(self):
        """Property for the output file.
        If applicable try to override output_parm.
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            return self.cached_renderproductList[self.cached_renderproductCount-1]["productOutnameA"]
        
        fName= self._node.parm(self.output_parm).evalAtFrame(1)
        #if parm is set via an expression, then it returns an unelevated string "$HIP/render/$HIPNAME.$OS.$F4.exr"
        fName= hou.text.expandStringAtFrame(fName, 1)
        return fName
        
    @property
    def output_evalAtFrameB(self):
        """Property for the output file.
        If applicable try to override output_parm.
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            return self.cached_renderproductList[self.cached_renderproductCount-1]["productOutnameB"]        
        
        fName= self._node.parm(self.output_parm).evalAtFrame(2)
        #if parm is set via an expression, then it returns an unelevated string "$HIP/render/$HIPNAME.$OS.$F4.exr"
        fName= hou.text.expandStringAtFrame(fName, 2)
        return fName

    @property
    def outdir(self):
        """Property for the output directory
        If applicable override output_parm
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            productout = ProductOutput(self.cached_renderproductList[self.cached_renderproductCount-1]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return productout.dir
        rrout = Output(self._node.parm(self.output_parm), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        return rrout.dir

    @property
    def outname(self):
        """Property for the output name
        If applicable override output_parm
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            productout = ProductOutput(self.cached_renderproductList[self.cached_renderproductCount-1]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return productout.name
        
        rrout = Output(self._node.parm(self.output_parm), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        return rrout.name

    @property
    def outext(self):
        """Property for the output extension
        If applicable override output_parm
        """
        if (self.cached_renderproductCount is None):
            self.cached_renderproductList= self.renderproductList
            self.cached_renderproductCount= len(self.cached_renderproductList)         
        if (self.cached_renderproductCount>0):
            productout = ProductOutput(self.cached_renderproductList[self.cached_renderproductCount-1]["attrib"], self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
            return productout.extension
            job.padding = productout.padding         
        
        rrout = Output(self._node.parm(self.output_parm), self._node.evalParm("f1"), self._node.evalParm("f2"), self.single_output_eval)
        return rrout.extension

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

    def check(self):
        """
        Custom method for child classes to override.
        Can be used to determine whether a RenderNode should be parsed.
        If method returns false, then RenderNode will not be parsed.
        """
        return True

    def add_rrfame_tag(self, path):
        """Replacing frame number with frame tag

        Frame tag is needed when an archive sequence is used as a scene to be rendered.

        converters ../scene_0123.ifd to ../scene_<FN4>.ifd

        Arguments:
            path String -- file path

        Returns:
            String -- adjusted file path with frame tag
        """
        self.logger.info("add rrframe_tag used. Might become deprecated")
        m = re.match(r"(.*?)(\d+)(\.[a-zA-z\.]+)$", path)
        if m:
            path = "{}<FN{}>{}".format(m.group(1), len(m.group(2)), m.group(3))
        else:
            msg = "'{}':Unable to add Frame Tag to Output '{}'".format(self.path, path)
            logger.warning(msg)

        return path
        

def node(path):
    """Creates and returns a Royal Render node instance from a houdini node path

    Arguments:
        path String -- Houdini node path

    Returns:
        rrNode -- Royal Render Node
    """
    hounode = hou.node(path)
    return rrNode.create(hounode)
