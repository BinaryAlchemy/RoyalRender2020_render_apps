# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

from htorr.rrnode.base import rrNode, RenderNode
import logging

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")


class WedgeNode(rrNode):
    name = "wedge"

    def childclass_parse(self, parseData):

        try:
            input_node = rrNode.create(self._node.inputs()[0])
        except ValueError as e:
            logger.warning(e)
            return
        except IndexError:
            logger.warning("Wedge Node has no Inputs")
            return

        if self._node.evalParm("wedgemethod") != 0:
            logger.warning("{}: Wedge Method not supported".format(self.path))
            return

        if self._node.evalParm("random"):
            logger.warning("{}: Random not supported".format(self.path))
            return

        mulit_parms = self._node.parm("wedgeparams").multiParmInstances()
        wedges = []
        for parm_group in self.get_parm_group(mulit_parms):
            wedge = []
            values = [v.eval() for v in parm_group]
            name, chan, rangex, rangey, steps = values
            stepsize = (rangey - rangex) / (steps - 1) if steps > 1 else 0

            for s in range(steps):
                v = rangex + s * stepsize
                wedge.append("{}_{}".format(name, v))

            wedges.append(wedge)

        wedges_combined = self.combine(wedges)

        wedges_combined_string = ["_".join(s) for s in wedges_combined]

        try:
            wedger = parseData.Wedge.create(self.path)

        except ValueError as e:
            logger.error(e)
            return

        try:
            with wedger:
                for w in wedges_combined_string:
                    hou.putenv("WEDGE", w)
                    input_node.parse(parseData)
                    wedger.next()

        finally:
            hou.unsetenv("WEDGE")

    @staticmethod
    def get_parm_group(parms):
        for i in range(0, len(parms), 5):
            yield parms[i : i + 5]

    @staticmethod
    def combine(list):
        comb_count = 1

        for n in list:
            comb_count *= len(n)

        combinations = []

        for i in range(0, comb_count):
            combination = []
            for l in list:
                index = i % len(l)
                i = i / len(l)
                combination.append(l[index])
            combinations.append(combination)

        return combinations


class MergeNode(rrNode):

    name = "merge"

    def childclass_parse(self, parseData):
        for i in self._node.inputs():
            n = rrNode.create(i)
            n.parse(parseData)


class SwitchNode(rrNode):

    name = "switch"

    def childclass_parse(self, parseData):
        index = self._node.parm("index").eval()
        if index < len(self._node.inputs()):
            n = rrNode.create(self._node.inputs()[index])
            n.parse(parseData)


# --------------- Geometry --------------------


class GeometryRop(RenderNode):
    """Geometry ROP to cache Geo"""

    name = "geometry"

    @property
    def output_parm(self):
        return "sopoutput"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        return "geometry"

    @property
    def licenses(self):
        return "Houdini;geometry"

    @property
    def single_output(self):
        f1 = self._node.parm(self.output_parm).evalAtFrame(1)
        f2 = self._node.parm(self.output_parm).evalAtFrame(2)
        if f1 == f2:
            return True
        else:
            return False

class GeometryRopOut(RenderNode):
    """Geometry ROP to cache Geo"""

    name = "rop_geometry"

    @property
    def output_parm(self):
        return "sopoutput"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        return "geometry"

    @property
    def licenses(self):
        return "Houdini;geometry"


class Filecache(RenderNode):
    """Geometry ROP to cache Geo"""

    name = "filecache"

    @property
    def output_parm(self):
        filemethod = self._node.parm("filemethod").eval() 
        if (filemethod == 1):
            return "file"
            
        return "sopoutput"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        return "geometry"

    @property
    def licenses(self):
        return "Houdini;geometry"
        
    @property
    def single_output(self):
        return (not self._node.evalParm("timedependent"))
            
         


class CompRop(RenderNode):
    """Comp ROP to render Images"""

    name = "comp"

    @property
    def output_parm(self):
        return "copoutput"

    @property
    def renderer_version(self):
        return

    @property
    def renderer(self):
        return "Comp"

    @property
    def licenses(self):
        return "Houdini"
