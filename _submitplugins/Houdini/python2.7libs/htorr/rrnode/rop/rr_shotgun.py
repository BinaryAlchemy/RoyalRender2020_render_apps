# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode
import logging


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


class AlembicRopOutShotgun(RenderNode):
    """Alembic ROP Out Shotgun to cache Alembic Files"""

    name = "sgtk_alembic"

    @property
    def output_parm(self):
        # Relink almebic from inside the node
        an = self.getAlembic()
        if an:
            return an.parm("filename")
        return "filename"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        if self.single_output:
            return "alembic-singleFile"
        else:
            return "alembic"

    @property
    def single_output(self):
        if self._node.evalParm("render_full_range"):
            return True
        else:
            return False

    def getAlembic(self):
        allchildren = self._node.allSubChildren()
        alembicnode = None
        for n in allchildren:
            if n.type().name().lower() == "alembic":
                alembicnode = n
                break
        return alembicnode
