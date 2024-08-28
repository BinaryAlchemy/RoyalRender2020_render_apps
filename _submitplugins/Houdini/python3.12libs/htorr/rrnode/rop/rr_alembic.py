# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import RenderNode
import logging


logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


class AlembicRop(RenderNode):
    """Alembic ROP to cache Alembic Files"""

    name = "alembic"

    @property
    def output_parm(self):
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


class AlembicRopOut(RenderNode):
    """Alembic ROP Out to cache Alembic Files"""

    name = "rop_alembic"

    @property
    def output_parm(self):
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
