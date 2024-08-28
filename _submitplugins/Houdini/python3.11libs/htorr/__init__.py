# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""@package htorr
This is the main module for the Houdini to Royal Render Plugin.
All necessary features are made available here to integrate Houdini to Royal Render into custom tools. Import this module to use them. 
"""

import logging
import tempfile
import os
from htorr import rrparser

# TODO: final logging directory for Royal Render
_TEMP_DIR = tempfile.gettempdir()
_TEMP_NAME = "ParserHoudini.log"

# create logger
logger = logging.getLogger("HtoRR")
# create file handler which logs even debug messages
#fh = logging.FileHandler(os.path.join(_TEMP_DIR, _TEMP_NAME))
#fh.setLevel(logging.WARNING)
# create console handler with a higher log level
ch = logging.StreamHandler()
level = logging.DEBUG if "DEBUG" in os.environ else logging.INFO
ch.setLevel(level)

# create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s %(name)s| %(levelname)s:  %(message)s",
                              "%H:%M:%S")
#fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
#logger.addHandler(fh)
logger.addHandler(ch)
logger.setLevel(level) #somehow the ch.setLevel(level) is not applied if the main logger does not have that level


ph = rrparser.ParserHandler()
phformatter = logging.Formatter(
    '%(message)s')
ph.setFormatter(phformatter)
ph.setLevel(logging.WARNING)
logger.addHandler(ph)

from htorr import submit
from htorr.rrnode import rrNode
from htorr.rrjob import Job, Submission
from htorr.rrnode.base import node


