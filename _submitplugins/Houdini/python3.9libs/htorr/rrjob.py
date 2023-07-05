# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""@package rrjob
This module contains all necessary classes to describe data which can be send to Royal Render.
This includes Job, Submission, SubmitOptions and Parameters. Job and Submissions are python classes build after their equivalent entities in Royal Render. 
Their property names are mapped to the official names through the dictionaries RR_PARMS and RR_Options. Usually one Submission instance contains 
multiple job instances.
Both Job and Submission instances can contain SubmitOptions and Parameter instances.
Parameter instances describe the basic settings of a job like scene or frmae range
SubmitOptions modify extra parameter of a Royal Renders job

Job, Submission and SubmitOptions follow the serialize interface which is used by the class XML_Serializer in the rrsubmitter package to convert these 
classes into an appropriate XML file which then can be submitted. To obtain a valid XML file it is important to put a job into an submission 
and serialize the submssion instance.

The dictionaries RR_PARM and RR_OPTIONS are used to map Royal Render parameter and option names to more python friendly names which are used for the 
classes in this module.
"""
import re
from htorr import utils
import os
import sys
from htorr import rrsubmitter

import logging
logger = logging.getLogger("HtoRR")

sharedPath= os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.append(sharedPath)
import royalDefs as rrDefs


RR_PARMS = {
    "plugin_version": "rrSubmitterPluginVersion",
    "software": "Software",
    "software_version": "Version",
    "renderer": "Renderer",
    "renderer_version": "rendererVersion",
    "layer": "Layer",
    "channel": "AOV",
    "scene": "Scenename",
    "outdir": "ImageDir",
    "outname": "Imagefilename",
    "outext": "ImageExtension",
    "padding": "ImageFramePadding",
    "camera": "Camera",
    "fstart": "SeqStart",
    "fend": "SeqEnd",
    "finc": "SeqStep",
    "pre_id": "PreID",
    "scene_state": "SceneState",
    "active": "IsActive",
    "image_width": "ImageWidth",
    "image_height": "ImageHeight",
    "licenses": "RequiredLicenses",
    "foffset": "SeqFileOffset",
    "scene_database_dir": "SceneDatabaseDir",
    "scene_os": "SceneOS",
    "pre_number_char": "ImagePreNumberLetter",
    "stereo_r": "imageStereoR",  # FIXME Farm Stereo
    "stereo_l": "imageStereoL",
    "_single_output": "ImageSingleOutputFile",
    "sceneVar_Job": "CustomHoudiniJob",
    "commandPassword": "CommandPassword",
}

RR_OPTIONS = {
    "seq_divide_min": ["SeqDivMIN", "tuple"],
    "seq_divide_max": ["SeqDivMax", "tuple"],
    "seq_divide_min_comp": ["SeqDivMINComp", "tuple"],
    "seq_divide_max_comp": ["SeqDivMaxComp", "tuple"],
    "required_memory": ["RequiredMemory", "tuple"],
    "allow_local_scene_copy": ["AllowLocalSceneCopy", "tuple"],
    "default_client_group": ["DefaultClientGroup", "tuple"],
    "gpu_required": ["GPUrequired", "tuple"],
    "distribution": ["Distribution", "compound"],
    "priority": ["Priority", "tuple"],
    "littlejob": ["LittleJob", "tuple"],
    "autodelete": ["AutoDeleteFrames", "tuple"],
}

FILE_TYPES = ["bgeo.sc"]


class ParmDesc(object):
    """Descriptor for Parm

    Add this descriptor as an attribute to a class to access parameters in a more pythonic way.
    Instead of instance.parm("parm_name") use instance.parm_name
    """

    def __init__(self, name):
        """Init with name of parameter"""
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.parm(self.name).eval()

    def __set__(self, instance, value):
        instance.parm(self.name).set(value)

    def __repr__(self):
        return self.name


class Parm(object):
    """Class to store and evaluate parm values

    Dedicated class to store and evaluate parm values.
    """

    def __init__(self, name, label, typ):
        """Creates a Parm instance.

        Arguments:
            name string -- name of the parameter
            label string -- label of the parameter as in the Royal Render XML
            typ string -- Type of parameter which might be needed
        """
        self.name = name
        self.label = label
        self.typ = typ
        self.value = None

    def set(self, value):
        """set value of parameter"""
        self.value = value

    def eval(self):
        """evaluates this parameter"""
        return self.value

    @classmethod
    def make(cls, template):
        """method to create new parameter from template"""
        return cls(template.name, template.label, template.typ)


class Job(object):
    """Class to describe Royal Render jobs."""

    """ List of parameters, which are used as a template for new instances of a job.
        Created from RR_PARMS
    """
    _template_parms = []

    def __init__(self):
        """Creates a new Job instance. Uses _template_parms list to initialize a new parm dictionary."""
        self._parms = {}

        for template in Job._template_parms:
            self._parms[template.name] = Parm.make(template)

        self.submission = None  # Submssion instance this job belongs to
        logger.debug("Job submitoptions")
        self.options = SubmitOptions()
        #logger.debug("Job submitoptions end")
        self.aovs = []
        self._dependency = []
        self.active = "true"
        self.foffset = 0
        self.scene_os = utils.get_os_sring()
        self.plugin_version =  rrDefs.plugin_version_str
        self.stereo_r = "_right"
        self.stereo_l = "_left"

    def parm(self, name):
        """Returns Parm with provided name"""
        return self._parms[name]

    def option(self, name):
        """Returns Submit Option with provided name"""
        return self.options[name]

    def add_custom_option(self, name, value, type="tuple"):
        """Adds a custom option and value to Job options"""
        logger.debug("Add custom job option: {} Value: {}".format(name, value))
        self.options.add_custom_option(name, value, type)

    def serialize(self, serializer):
        """Method which can be used by a serializer to serialize an instance of Job.

        Arguments:
            serializer XML_Serializer -- Serializer instance
        """
        serializer.start("Job")
        logger.debug("Job submitoptions serialize")
        self.options.serialize(serializer)
        if sys.version_info.major == 2:
            for name, parm in self._parms.iteritems():
                if parm.eval() != None :
                    serializer.add(parm.label, parm.eval())
        else:
            for name, parm in self._parms.items():
                if parm.eval() != None :
                    serializer.add(parm.label, parm.eval())

        for j in self._dependency:
            serializer.add("WaitForPreID", j.pre_id)

        if self.aovs:
            for aov in self.aovs:
                serializer.add("ChannelFilename", aov[0])
                serializer.add("ChannelExtension", aov[1])
        logger.debug("Job submitoptions serialize end")

    def __str__(self):
        filename = ""
        if self.outname:
            filename = self.outname.split("/")[-1]
        if self.padding:
            for i in range(self.padding):
                filename += "#"
        filename += self.outext if self.outext else ""

        return " {:30.30}{:20.20}{:35.35}{:8.8}{:8.8}".format(
            str(self.layer),
            str(self.camera),
            str(filename),
            str(self.fstart),
            str(self.fend),
        )

    @property
    def gpu(self):
        """Boolean Property whether the output generated by this job is a single file"""
        return self.option("gpu_required").eval()

    @gpu.setter
    def gpu(self, value):
        """Setter for Property gpu"""
        if value:
            self.option("gpu_required").set([1, 1])

    @property
    def single_output(self):
        """Boolean Property whether the output generated by this job is a single file"""
        return self._single_output

    @single_output.setter
    def single_output(self, value):
        """Setter for Property single output"""
        if value:
            self._single_output = "true"

    def set_dependency(self, jobs):
        """Makes this job dependend on the list of jobs provided."""
        self._dependency = jobs

    def set_frange(self, frange):
        """Sets the frame range.

        Arguments:
            frange int[3] -- [Frame Start, Frame End, Frame Increment]
        """
        self.fstart = frange[0]
        self.fend = frange[1]
        self.finc = frange[2]

    def set_image_size(self, image_size):
        if image_size:
            self.image_width = image_size[0]
            self.image_height = image_size[1]


# Create Job parms from dict RR_PARMS
if sys.version_info.major == 2:
    for name, label in RR_PARMS.iteritems():
        setattr(Job, name, ParmDesc(name))
        Job._template_parms.append(Parm(name, label, None))
else:
    for name, label in RR_PARMS.items():
        setattr(Job, name, ParmDesc(name))
        Job._template_parms.append(Parm(name, label, None))


class Submission(object):
    """Class to describe a Submission, which stores Jobs and SubmitOptions.
    Instances of this class can be submitted"""

    def __init__(self):
        logger.info(rrDefs.plugin_version_str)
        self.jobs = []
        #logger.debug(
        #    "Submission init SubmitOptions(); Called from: {} in {}".format(
        #        sys._getframe().f_back.f_code.co_name,
        #        sys._getframe().f_back.f_code.co_filename,
        #    )
        #)
        self.options = SubmitOptions()
        self.paramOverrides =  {}
        self._factory = None

    def __str__(self):
        text = "{:30.30}{:20.20}{:35.35}{:8.8}{:8.8}".format(
            "Layer", "Camera", "Filename", "Start", "End"
        )

        for j in self.jobs:
            text += "\n" + str(j)
        return text

    def option(self, name):
        """Returns SubmitOption with name provided"""
        return self.options[name]

    def add_custom_option(self, name, value, type="tuple"):
        """Adds a custom option and value to SubmitOption"""
        logger.debug("Add custom option: {} Value: {}".format(name, value))
        self.options.add_custom_option(name, value, type)
        # logger.debug("Submitoptions from Submission: {}".format(self.options))

    def add_param_override(self, name, value):
        """Adds a parm override"""
        logger.debug("Add param override: {} = {}".format(name, value))
        self.paramOverrides[name]= value



    """
    A Submission instance can be used as a context manager. But should only be invoked when created by a Submission factory.
    When entered the instance adds itself to a _stack of the factory and removes itself when exitted. This mechanism is needed for parsing. 
    """

    def __enter__(self):
        self._factory._stack.append(self)
        return self

    def __exit__(self, *kwarg):
        self._factory._stack.remove(self)

    def __getitem__(self, key):
        return self.jobs[key]

    def serialize(self, serializer):
        """Method which can be used by a serializer to serialize an instance of Submission.

        Arguments:
            serializer XML_Serializer -- Serializer instance
        """
        serializer.start("rrJob_submitFile", {"syntax_version": "6.0"})

        if "DEBUG" not in os.environ:
            serializer.add("DeleteXML", "1")

        logger.debug("Submission submitoptions serialize")
        self.options.serialize(serializer)
        for j in self.jobs:
            serializer.append(j)
        serializer.end()
        logger.debug("Submission submitoptions serialize end")

    def submit(self, gui=False):
        if gui:
            submitter = rrsubmitter.RrGuiSubmitter()
            submitter.submit(self)
        else:
            submitter = rrsubmitter.RrCmdGlobSubmitter()
            out = submitter.submit(self)
            return out


class SubmitOptions(object):
    """Extended Dictonary to store submit options""" 

    def __str__(self):
        text = "\n     SubmitOptions:"
        if sys.version_info.major == 2:
            for name, parm in self._parms.iteritems():
                try:
                    text += "{}: {}  | ".format(name, parm.eval())
                except:
                    text += "{}:  N/A   | ".format(name, parm.eval())
        else:
            for name, parm in self._parms.items():
                try:
                    text += "{}: {}  | ".format(name, parm.eval())
                except:
                    text += "{}:  N/A   | ".format(name, parm.eval())
        return text

    def __init__(self):
        self._parms = {}
        if sys.version_info.major == 2:
            for name, attribs in RR_OPTIONS.iteritems():
                self._parms[name] = Parm(name, attribs[0], attribs[1])
        else:
            for name, attribs in RR_OPTIONS.items():
                self._parms[name] = Parm(name, attribs[0], attribs[1])

    def add_custom_option(self, name, value, type):
        """Adds custom option to Submit Options Dictionary"""
        self._parms[name] = Parm(name, name, type)
        logger.debug(
            "Added new Parm: {}={} ({})".format(self._parms[name].label, value, type)
        )
        self._parms[name].set(value)
        # logger.debug("Set parm value to {}".format(value))
        # logger.debug("Get parm value {}".format(self._parms[name].eval()))
        #logger.debug("Parms after custom:")
        #logger.debug(self)

    def serialize(self, serializer):
        """Method which can be used by a serializer to serialize SubmitOptions.

        Arguments:
            serializer XML_Serializer -- Serializer instance
        """
        logger.debug("SubmitOptions.serialize(): {}".format(self))
        sdict = {}
        cdict = {}
        elist = []
        if sys.version_info.major == 2:
            for name, parm in self._parms.iteritems():
                if parm.typ == "tuple":
                    logger.debug("Parm: {} Eval: {}".format(parm.label, parm.eval()))
                    if parm.eval():
                        string_tuple = [str(t) for t in parm.eval()]
                        logger.debug(
                            "Add Parameter: {} to sdict with Value: {}".format(
                                parm.label, "~".join(string_tuple)
                            )
                        )
                        sdict[parm.label] = "~".join(string_tuple)
                if parm.typ == "custom":
                    logger.debug("Custom: {} Eval: {}".format(parm.label, parm.eval()))
                    if parm.eval():
                        text = parm.eval()
                        logger.debug(
                            "Add Parameter: {} to cdict with Value: {}".format(
                                parm.label, text
                            )
                        )
                        cdict[parm.label] = text
                if parm.typ == "env":
                    logger.debug("Env: {} Eval: {}".format(parm.label, parm.eval()))
                    if parm.eval():
                        text = parm.eval()
                        logger.debug(
                            "Add Parameter: {} to elist with Value: {}".format(
                                parm.label, text
                            )
                        )
                        elist.append("{}={}".format(parm.label, text))

        else:
            for name, parm in self._parms.items():
                if parm.typ == "tuple":
                    if parm.eval():
                        string_tuple = [str(t) for t in parm.eval()]
                        logger.debug(
                            "3: Add Parameter: {} to sdict with Value: {}".format(
                                parm.label, "~".join(string_tuple)
                            )
                        )
                        sdict[parm.label] = "~".join(string_tuple)
                if parm.typ == "custom":
                    logger.debug("Custom: {} Eval: {}".format(parm.label, parm.eval()))
                    if parm.eval():
                        text = parm.eval()
                        logger.debug(
                            "Add Parameter: {} to cdict with Value: {}".format(
                                parm.label, text
                            )
                        )
                        cdict[parm.label] = text
                if parm.typ == "env":
                    logger.debug("Env: {} Eval: {}".format(parm.label, parm.eval()))
                    if parm.eval():
                        text = parm.eval()
                        logger.debug(
                            "Add Parameter: {} to elist with Value: {}".format(
                                parm.label, text
                            )
                        )
                        elist.append("{}={}".format(parm.label, text))

        try:
            distribution = self._parms["distribution"].eval()
            if distribution == "full":
                pass
            elif distribution == "frameafterframe":
                sdict["DistributeStartToEnd"] = "0~1"
                sdict["MaxClientsAtATime"] = "0~1"
            elif distribution == "oneclient":
                sdict["DistributeStartToEnd"] = "0~1"
                sdict["MaxClientsAtATime"] = "0~1"
                sdict["SeqDivMIN"] = "0~0"
                sdict["SeqDivMax"] = "0~0"
        except KeyError:
            pass

        if sys.version_info.major == 2:
            for name, value in sdict.iteritems():
                serializer.add("SubmitterParameter", "{}={}".format(name, value))
            for name, value in cdict.iteritems():
                serializer.add(name, value)
        else:
            for name, value in sdict.items():
                serializer.add("SubmitterParameter", "{}={}".format(name, value))
            for name, value in cdict.items():
                serializer.add(name, value)

        if not elist == []:
            serializer.add("rrEnvList", " ~~~ ".join(elist))

    def __getitem__(self, key):
        return self._parms[key]

    def merge(self, options):
        """Merge this SubmitOptions instance with another instance.
        This only copies options of the provided instance if this option does not exist.
        """
        # logger.debug("SubmitOptions before merge: {}".format(self))
        if sys.version_info.major == 2:
            for name, parm in self._parms.iteritems():
                #logger.debug("Name: {}".format(name))
                if not parm.eval():
                    #logger.debug("Value: {}".format(parm.eval()))
                    self._parms[name] = options._parms[name]

            for name, parm in options._parms.iteritems():
                if not name in self._parms:
                    self._parms[name] = options._parms[name]

        else:
            for name, parm in self._parms.items():
                if not parm.eval():
                    self._parms[name] = options._parms[name]

            for name, parm in options._parms.items():
                if not name in self._parms:
                    self._parms[name] = options._parms[name]

        # logger.debug("SubmitOptions after merge: {}".format(self))
