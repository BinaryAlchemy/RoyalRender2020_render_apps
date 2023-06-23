# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import math
import os.path

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")

FILE_TYPES = [".bgeo.sc", ".ass.gz", ".ifd.sc", ".exr"]

class Output(object):
    """Helper class to convert houdini output parameters into a more suitable representation for Royal Render.
    """

    def __init__(self, parm, seqStart, seqEnd, singleOutput):
        self.parm = parm
        self.static = True
        self.extension = ""
        self.padding = 0 
        
        try:
            outf1 = parm.evalAtFrame(1)
            outf2 = parm.evalAtFrame(2)
            #if parm is set via an expression, then it returns an unelevated string "$HIP/render/$HIPNAME.$OS.$F4.exr"
            outf1= hou.text.expandStringAtFrame(outf1, 1)
            outf2= hou.text.expandStringAtFrame(outf2, 1)
        except:
            logger.warning("No image output set.")
            self.dir=""
            self.name=""
            return
        
        path_no_ext = ""
        
        logger.debug("Output for frame 1 is {} (I)".format(str(outf1)))
        logger.debug("Output for frame 2 is {} (I)".format(str(outf2)))

        if outf2 != outf1:
            self.static = False
            exp = 0
            while(len( hou.text.expandStringAtFrame(parm.evalAtFrame(math.pow(10,exp)), math.pow(10,exp))) == len(outf1)):
                exp += 1

            self.padding = exp
            index_frame_end = [i for i in range(len(outf1)) if outf1[i]!=outf2[i]][0]
            index_frame_start = index_frame_end - self.padding

            path_no_ext = outf1[:index_frame_start+1]
            self.extension = outf1[index_frame_end+1:]
        else:
            if singleOutput:
                self.extension=""
                path_no_ext=outf1
            else:
                for f in FILE_TYPES:
                    if outf1.endswith(f):
                        self.extension = f
            
                if not self.extension:
                    splittedPoint=parm.eval().rsplit(".",1)
                    if len(splittedPoint)>1:
                        self.extension = "." + splittedPoint[-1]
                
                path_no_ext = outf1[:len(outf1)-len(self.extension)]
        
        self.dir, self.name = os.path.split(path_no_ext)

class ProductOutput(object):
    """Helper class to convert Houdini render product parameters into a more suitable representation for Royal Render."""

    def __init__(self, attrib, seqStart, seqEnd, singleOutput):
        self.attrib = attrib
        self.static = True
        self.extension = ""
        self.padding = 0 

        #logger.debug("Product Output")
        
        try:
            #attrib.Get truncates to range set in scene, therefore we cannot use frame 1 and 2
            outf1 = attrib.Get(1)
            outf2 = attrib.Get(1)
        except:
            logger.debug("No image output set.")
            return
        
        path_no_ext = ""
        
        logger.debug("Output for frame {} is {} (PO)".format(seqStart, outf1))
        logger.debug("Output for frame {} is {} (PO)".format(seqEnd, outf2))

        if outf2 != outf1:
            self.static = False
            exp = 0
            lastOutName="empty"
            while(lastOutName!=attrib.Get(math.pow(10,exp)) and len(attrib.Get(math.pow(10,exp))) == len(outf1)):
                logger.debug("Output len test {} {} {}".format(exp, math.pow(10,exp) , attrib.Get(math.pow(10,exp))  ))
                lastOutName=attrib.Get(math.pow(10,exp))
                exp += 1
            if (lastOutName == attrib.Get(math.pow(10,exp))):
                exp -= 1

            self.padding = exp
            index_frame_end = [i for i in range(len(outf1)) if outf1[i]!=outf2[i]][0]
            while outf1[index_frame_end].isdigit():
                #the first difference might be any digit inside the frame number. e.g. compare .000. with  .0240. 
                index_frame_end += 1
            index_frame_end -=1
            
            index_frame_start = index_frame_end - self.padding

            path_no_ext = outf1[:index_frame_start+1]
            self.extension = outf1[index_frame_end+1:]

            #logger.debug("self.padding {} self.extension {}  path_no_ext {}".format(self.padding, self.extension, path_no_ext))
            #logger.debug("path_no_ext[len(path_no_ext)-1] {}".format(path_no_ext[len(path_no_ext)-1]))
            while path_no_ext[len(path_no_ext)-1].isdigit():
                path_no_ext= path_no_ext[:len(path_no_ext)-1]
                self.padding += 1
                #logger.debug("self.padding {}   path_no_ext {}".format(self.padding, path_no_ext))
            
        
        else:
            for f in FILE_TYPES:
                if outf1.endswith(f):
                    self.extension = f
        
            if not self.extension:
                self.extension = "." + attrib.Get(1).rsplit(".",1)[-1]
            
            path_no_ext = outf1[:len(outf1)-len(self.extension)]
            if not singleOutput:
                path_no_ext= path_no_ext.replace("${F5}","11111")
                path_no_ext= path_no_ext.replace("$F5","11111")
                path_no_ext= path_no_ext.replace("${F4}","1111")
                path_no_ext= path_no_ext.replace("$F4","1111")
                self.padding=0
                while path_no_ext[len(path_no_ext)-1].isdigit():
                    path_no_ext= path_no_ext[:len(path_no_ext)-1]
                    self.padding += 1
                    #logger.debug("self.padding {}   path_no_ext {}".format(self.padding, path_no_ext))
            
            
        #logger.debug("ProductOutput: self.padding {} self.extension {}  path_no_ext {}".format(self.padding, self.extension, path_no_ext))
        self.dir, self.name = os.path.split(path_no_ext)