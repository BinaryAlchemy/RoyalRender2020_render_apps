# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import os.path
from htorr.rroutput import Output
from htorr.rrnode.base import rrNode
import random


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")



class hqSimRop(rrNode):

    name = "hq_sim"
    
    def childclass_parse(self, parseData):
    
        numSlices= 1
        sliceType= self._node.parm("slice_type").eval()
        if (sliceType==0):
            slicediv1= self._node.parm("slicediv1").eval()
            slicediv2= self._node.parm("slicediv2").eval()
            slicediv3= self._node.parm("slicediv3").eval()
            numSlices= slicediv1 * slicediv2 * slicediv3
        elif (sliceType==1):
            numSlices= self._node.parm("num_slices").eval()
        else:
            logger.info("{}: Volume and Particle Slicing supported only!".format(self.path))
            return None
        logger.info("{}: numSlices: {}".format(self.path, numSlices))
        
        commandPassword=''.join(random.choice( 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(35));
        
        jobServer = parseData.Job.create()
        jobServer.software = self.software
        jobServer.software_version = self.software_version
        jobServer.renderer = "pyServer"
        if (len(parseData.rendererPreSuffix)>0):
            jobServer.renderer= parseData.rendererPreSuffix.replace("*", jobServer.renderer)
        jobServer.commandPassword= commandPassword
        jobServer.scene = self.scene
        jobServer.scene_database_dir = self.scene_database_dir
        jobServer.channel = self.take
        jobServer.single_output = True
        jobServer.sceneVar_Job = self.sceneVar_Job
        jobServer.outdir = jobServer.scene_database_dir
        jobServer.add_custom_option("CustomCommandLine",'"<RR_DIR>render_apps/scripts/houdini_simtracker_start.py" <JobCommandPWHash_asText -JobCommandPWHash <JobCommandPWHash_asText>> -childRRJob <WaitChild> -HoudiniModPath "<OSEnv HFS>/houdini/python<HPyVerP>libs"', "custom")
        jobServer.fstart = 1
        jobServer.fend = 1
        jobServer.finc = 1
        jobServer.layer = self._node.parm("hq_driver").eval()
        
        

        
        
        job = parseData.Job.create()
        job.software = self.software
        job.software_version = self.software_version
        job.renderer = "simSlicer"
        if (len(parseData.rendererPreSuffix)>0):
            job.renderer= parseData.rendererPreSuffix.replace("*", job.renderer)
        job.commandPassword= commandPassword #has to be the same as jobServer requires to change this job
        job.scene = self.scene
        job.scene_database_dir = self.scene_database_dir
        job.channel = self.take
        job.single_output = True
        job.sceneVar_Job = self.sceneVar_Job
        job.outdir = job.scene_database_dir
        job.layer = self._node.parm("hq_driver").eval()
        job.add_custom_option("CustomSlicerNode", self._node.parm("hq_sim_controls").eval() , "custom")
        job.add_custom_option("CustomSlicerPort", "8000" , "custom")
        job.add_custom_option("CustomSlicerClient", "localhost" , "custom")
        job.add_custom_option("PPHoudiniStopSimServer", [0, 1])

        job.fstart = 0
        job.fend = numSlices -1
        job.finc = 1
        
        job.set_dependency([jobServer])

        
        

        return job
