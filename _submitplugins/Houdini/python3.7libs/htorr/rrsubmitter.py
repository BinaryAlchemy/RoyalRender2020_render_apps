# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""@package rrsubmitter
This module contains classes and methods to convert python objects to submittable XML files and to submit these to the farm.
"""

import os
import sys

import subprocess
import re
import random
import logging

from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as et
import xml.dom.minidom

from htorr import utils
import tempfile

logger = logging.getLogger("HtoRR")


def serialize_to_xml(submission):
    """Converts a submssion instance to an xml text.
    
    Arguments:
        submission Submission -- submission instance
    
    Returns:
        String -- XML Text
    """
    serializer = XML_Serializer()
    submission.serialize(serializer)
    return serializer.to_str()


class XML_Serializer(object):
    """Class to serialize objects to a xml text.
       An objects needs to implement the method serialize in order to beeing serializable.
    """
    def __init__(self):
        self._element = None
        self._end = False

    def to_str(self):
        if (sys.version_info.major == 3) and (sys.version_info.minor>=8):
            text = et.tostring(self._element, encoding="utf-8", xml_declaration=True)
        else:
            text = et.tostring(self._element, encoding="utf-8")
            
        if True:
            dom = xml.dom.minidom.parseString(text)
            text = dom.toprettyxml(encoding='utf-8')
        return text

    def add(self, element, value):
        sub = SubElement(self._element, element)
        text = str(value)
        if sys.version_info.major == 2:
            text = text if type(text) is unicode else text.decode("utf8")
        sub.text = text

    def start(self, name, attrib=None):
        self._element = Element(name)
        if attrib:
            if (sys.version_info.major == 2):
                for key, value in attrib.iteritems():
                    self._element.attrib[key] = value
            else:
                for key, value in attrib.items():
                    self._element.attrib[key] = value

    def append(self, obj):
        xml = XML_Serializer()
        obj.serialize(xml)
        self._element.append(xml.get_element())

    def get_element(self):
        return self._element

    def end(self):
        self._end = True


class RrCmdSubmitter(object):
    """Royal Render Commandline Submitter Base Class."""

    def __init__(self):
        """Init Submitter Object.

        Arguments:
            tmp_dir string -- Path to Tmp Dir to save XML File.
        """
        self._tmp_dir = tempfile.gettempdir()

    def write_submission_file(self, text):
        """Write Submission XML File to disk.

        Arguments:
            text string -- XML serialized text

        Returns:
            string - path to written xml file

        """
        random.seed()
        filename = "rrSubmitHoudini_{}.xml".format(random.randrange(1000, 10000, 1))
        path = os.path.join(self._tmp_dir, filename)
        file_ = open(path, 'wb')
        file_.write(text)
        file_.close()

        return path

    @staticmethod
    def get_rr_rrStartLocal_path():
        """Return path to Command Submitter"
        """
        rr_root = utils.get_rr_root()
        if ((sys.platform.lower() == "win32") or
                (sys.platform.lower() == "win64")):
            rr_submitter = rr_root + "\\bin\\win64\\rrStartLocal.exe"
        elif (sys.platform.lower() == "darwin"):
            rr_submitter = rr_root + "/bin/mac64/rrStartLocal"
        else:
            rr_submitter = rr_root + "/bin/lx64/rrStartLocal"

        return rr_submitter
        

class RrCmdGlobSubmitter(RrCmdSubmitter):
    def __init__(self):
        super(RrCmdGlobSubmitter, self).__init__()



    def submit(self, submission):
        """Submit provided Submission instance to farm.
        
        Arguments:
            submission Submission -- submission
        
        Returns:
            int[] -- list of jobs ids
        """
        logger.debug("Submit: {}".format(submission))
        subm_text = serialize_to_xml(submission)
        subm_file_path = self.write_submission_file(subm_text)
        command = (self.get_rr_rrStartLocal_path()
                   + " -sameTerminal rrSubmitterconsole  \"" + subm_file_path
                   + "\"" )
        logger.debug("Submit cmd: {}".format(command))   
        rr_env=os.environ.copy()
        if 'QT_PLUGIN_PATH' in rr_env:
            del rr_env['QT_PLUGIN_PATH']
        if 'QT_LOGGING_RULES' in rr_env:
            del rr_env['QT_LOGGING_RULES']
        if 'QT_QPA_FONTDIR' in rr_env:
            del rr_env['QT_QPA_FONTDIR']
        if 'QT_QPA_PLATFORM_PLUGIN_PATH' in rr_env:
            del rr_env['QT_QPA_PLATFORM_PLUGIN_PATH']


        # Execute RR Submitter with Popen Instance
        # Additional Settings to hide Window
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(command, startupinfo=startupinfo, stdout=subprocess.PIPE, env=rr_env)

        out = proc.communicate()[0]
        out= out.decode('ascii')

        if proc.returncode != 0:
            logger.warning("RR Commandline Submitter cant submit Job:\n"+out)
            return None
            
        #logger.debug("Commandline Submitter output\n-------------------------------\n{}\n------------------------------".format(out))
        try:
            outSplitted = out.split("Job IDs send: ")
            #logger.debug("outSplitted\n-------------------------------\n{}\n------------------------------".format(outSplitted))
            id_string= outSplitted[-1]
            ids = re.findall(r'(\d{12,})', id_string)
            logger.debug("{} Jobs submitted:{}".format(len(ids), ids))
            return ids
        except:
            logger.debug("Jobs submitted")
            ids = []
            ids.append("noID")
            return ""
       


class RrGuiSubmitter(RrCmdSubmitter):
    def __init__(self):
        super(RrGuiSubmitter, self).__init__()



    def submit(self, submission):
        """Submit submission instance to farm.
        Using subprocess to create another process for submission.
        """
        logger.debug("Submit: \n {}".format(submission))
        rr_env=os.environ.copy()
        if 'QT_PLUGIN_PATH' in rr_env:
            del rr_env['QT_PLUGIN_PATH']
        if 'QT_LOGGING_RULES' in rr_env:
            del rr_env['QT_LOGGING_RULES']
        if 'QT_QPA_FONTDIR' in rr_env:
            del rr_env['QT_QPA_FONTDIR']
        if 'QT_QPA_PLATFORM_PLUGIN_PATH' in rr_env:
            del rr_env['QT_QPA_PLATFORM_PLUGIN_PATH']
        
        subm_text = serialize_to_xml(submission)
        subm_file_path = self.write_submission_file(subm_text)
        command = (self.get_rr_rrStartLocal_path()
                   + " rrSubmitter \"" + subm_file_path
                   + "\"")
        logger.debug("Submit cmd: {}".format(command))   
        if (not os.path.exists(self.get_rr_rrStartLocal_path())):
            logger.warning("RR executable does not exist:\n" + self.get_rr_rrStartLocal_path())
        else:
            subprocess.Popen(command, env=rr_env)
