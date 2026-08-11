# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""@package rrnode

This module/package contains warpper classes for all supported Houdini nodes. An instance of the appropriate wrapper class can be obtained by calling the 
create method from the base class rrNode by passing an instance of hou.node. A wrapper class converts node information in a more Royal Render relevant representation which can be obtained via instance properties of a wrapper class.
All wrapper classes follow the parsing interface from the package rrparser by implementing a parse mehtod. This method uses the passed ParseData instance to convert itself into Submission data. 
To make new warpper classes work inside of this plugins framework they have to conform to the rrNodes interface by implementing them as a subclass of Node or RenderNode.
RenderNode is the base class for all ROPs, like Mantra, OpenGL or Alembic, which generate files. A new implementation of a RenderNode subclass should only override already existing properties. The parsing functionality is already implemented in RenderNode
and should not be overridden in subclasses.
"""

import htorr.rrnode.rop
from htorr.rrnode.base import rrNode

import logging

logger = logging.getLogger("HtoRR")

NODE_REGISTRY = rrNode.REGISTRY

def _subclasses(cls, registry=None):
    if registry is None:
        registry = set()

    subs = cls.__subclasses__()

    for sub in subs:
        if sub in registry:
            return
        registry.add(sub)
        yield sub
        for sub in _subclasses(sub, registry):
            yield sub

def _node_registry():
    """Call register node on rrNode base class for every subclass of rrNode, to register all subclasses of rrNode.
    """
    for cls in _subclasses(rrNode):
        rrNode._register_node(cls.name, cls)
        #logger.debug("Nodetype {} registered".format(cls.name))

        # Test if Subclass Implementations of Abstract Nodes are complete
        try:
            cls(None)
        except TypeError as err:
            if cls.name not in ["renderNodeBase"]:
                logger.error("Nodetype {} incomplete: {}".format(cls.name, err))

_node_registry()