# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""Submission Script 
This module implements and combines all provided features from the Houdini To Royal Render Plugin into a Submssion Tool which can be accessed via the mehtod submit().

"""

from htorr import rrsubmitter
import logging
from htorr import utils
from htorr import rrnode
from htorr import rrparser
import sys
import os
sharedPath= os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.append(sharedPath)
import royalDefs as rrDefs

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


def submit(rops=[], gui=True):
    logger.debug("------------------------------------"+rrDefs.plugin_version_str+"---------------------------------------")
    logger.debug("------------------------------------"+rrDefs.plugin_version_str+"---------------------------------------")
    logger.debug("UICurrent: {}".format( hou.frame()))
    sel = hou.selectedNodes()

    if sel and not rops:
        rops = []
        for s in sel:
            logger.debug("{}: Selected Node type is {}. Type category is '{}' ".format( s.path(),  s.type().name() , s.type().category()) )
            if s.type().category() == hou.ropNodeTypeCategory():
                rops.append(s)
            elif s.type().category() == hou.lopNodeTypeCategory():
                rops.append(s)
            else:
                logger.warning("{}: Selected Node is no ROP/LOP. Type category is '{}' ".format( s.path(), s.type().category()) )

    if not rops:
        rops = get_scene_rops()

    if not rops:
        hou.ui.displayMessage("No ROPs to submit", buttons=("OK",))
        logger.debug("No ROPs to submit")
        return

    logger.debug("------------ submit: parse_nodes() ------------" )
    submission = parse_nodes(rops)

    logger.debug("------------ submit: rrparser.ParserHandler() ------------" )
    if rrparser.ParserHandler.get():
        msg = "\n".join(rrparser.ParserHandler.get())
        out = hou.ui.displayMessage(
            "HtoRR: Errors occured when parsing ROPs",
            buttons=("Ignore", "Abort"),
            default_choice=1,
            severity=hou.severityType.ImportantMessage,
            close_choice=1,
            details=msg,
            details_label="Following Lines found in Log",
            details_expanded=True,
        )
        if out == 1:
            return

    if not submission:
        hou.ui.displayMessage("No valid ROPs to submit", buttons=("OK",))
        logger.debug("No valid ROPs to submit")
        return

    if not submission.jobs:
        hou.ui.displayMessage("No Jobs to submit", buttons=("OK",))
        logger.debug("No Jobs to submit")
        return

    if not utils.open_save_hip():
        return

    if gui:
        submitter = rrsubmitter.RrGuiSubmitter()
        submitter.submit(submission)
    else:
        submitter = rrsubmitter.RrCmdGlobSubmitter()
        out = submitter.submit(submission)

        if out:
            hou.ui.displayMessage(
                "Successfully submitted {} Jobs".format(len(out)),
                buttons=("OK",),
                details=str(submission),
            )

        else:
            hou.ui.displayMessage(
                "Unable to submit Jobs, see Log",
                severity=hou.severityType.Error,
                buttons=("OK",),
            )


def get_scene_rops():

    rops = []
    if sys.version_info.major == 2:
        for name, typ in hou.ropNodeTypeCategory().nodeTypes().iteritems():
            for r in typ.instances():
                rops.append(r)
        for name, typ in hou.lopNodeTypeCategory().nodeTypes().iteritems():
            for r in typ.instances():
                rops.append(r)
    else:
        for name, typ in hou.ropNodeTypeCategory().nodeTypes().items():
            for r in typ.instances():
                rops.append(r)
        for name, typ in hou.lopNodeTypeCategory().nodeTypes().items():
            for r in typ.instances():
                rops.append(r)

    return rops


def parse_nodes(nodes):
    #create rrNodes from nodes list
    rr_rops = [rrnode.rrNode.create(rop) for rop in nodes]
    for r in rr_rops:
        for d in r.dependencies():
            if d in nodes:
                #remove ROP "d" from nodes list if this rop depends on it
                nodes.remove(d)
    p = rrparser.ParseData()
    rrparser.ParserHandler.clear()
    for n in nodes:
        rn = rrnode.rrNode.create(n)
        #logger.debug("parse_nodes:rn.parse")
        rn.parse(p)
    return p.SubmissionFactory.get()





if __name__ == "__main__":
    submit()
