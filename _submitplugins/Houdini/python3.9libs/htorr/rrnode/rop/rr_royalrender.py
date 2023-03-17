# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import logging
import traceback
from htorr.rrnode.base import rrNode

logger = logging.getLogger("HtoRR")

try:
    import hou
except ImportError:
    logger.info("Module imported outside of hython environment")



class SubmitterNode(rrNode):

    name = "rrSubmitter"

    def childclass_parse(self, parseData):
        preSubmitCmd = self._node.evalParm("rr_presubmit_command")
        if (preSubmitCmd!=None and (len(preSubmitCmd)>0) ):
            try:
                preReturn=eval(preSubmitCmd)
                logger.debug("preReturn " + str(preReturn) +  "   " + str(type(preReturn)))
                if (preReturn==False):
                    logger.error("{}: Pre-Submission command returned FALSE!".format(self._node.path()))
                    return
            except:
                logger.error("{}: Pre-Submission command failed.\n{}".format(self._node.path(), traceback.format_exc()))
                return

        autosave = self._node.evalParm("rr_autosave")
        if autosave:
            logger.debug("automatically saved changes")
            hou.hipFile.save()

        # warn_unsaved_changes = self._node.evalParm("rr_warn_unsaved_changes")
        # if warn_unsaved_changes and hou.hipFile.hasUnsavedChanges():
        #      if not htorr.utils.open_save_hip():
        #       return
        logger.debug("RRRop -start")
        submission = parseData.SubmissionFactory.create()
        submit_dependencies = False
        
        # Custom
        if self._node.evalParm("rr_jobsettings_enabled"):
            jobsettings = self._node.parm("rr_jobsettings").evalAsString()
            try:
                for setting in jobsettings.split(";"):
                    settingname = setting.split("=")[0]
                    settingvalues = setting.split("=")[-1]
                    values = settingvalues.split("~")
                    logger.debug(
                        "Found custom option: {} Value: {}".format(settingname, values)
                    )
                    submission.add_custom_option(settingname, values)
                    logger.debug(
                        "RRRoyalrenderrop, Submitoptions: {}".format(submission.options)
                    )
            except:
                logger.info("wrong fromat: rr_jobsettings")

        if self._node.evalParm("rr_job_variables_enabled"):
            jobvariables = self._node.parm("rr_job_variables").evalAsString()
            try:
                for var in jobvariables.split(";"):
                    equalSign= var.find("=")
                    if (equalSign>0):
                        varname = var[:equalSign]
                        varvalue = var[equalSign+1:]
                        varname= varname.strip()
                        varvalue= varvalue.strip()
                        customvarname = "Custom{}".format(varname)
                        submission.add_custom_option(customvarname, varvalue, "custom")
            except:
                logger.info("wrong format: rr_job_variables")

        if self._node.evalParm("rr_env_variables_enabled"):
            envvariables = self._node.parm("rr_env_variables").evalAsString()
            try:
                for var in envvariables.split(";"):
                    equalSign= var.find("=")
                    if (equalSign>0):
                        varname = var[:equalSign]
                        varvalue = var[equalSign+1:]
                        varname= varname.strip()
                        varvalue= varvalue.strip()
                        submission.add_custom_option(varname, varvalue, "env")
            except:
                logger.info("wrong format: rr_env_variables")

        if self._node.evalParm("rr_distribution_enabled"):
            distribution = self._node.evalParm("rr_distribution")
            if distribution == 0:
                # submission.add_option("distribution", "full")
                submission.option("distribution").set("full")
            elif distribution == 1:
                # submission.add_option("distribution", "frameafterframe")
                submission.option("distribution").set("frameafterframe")
            else:
                # submission.add_option("distribution", "oneclient")
                submission.option("distribution").set("oneclient")

        if not self._node.parm("rr_seq_devidex").isDisabled():

            seq_divide_min = int(self._node.evalParm("rr_seq_devidex"))
            seq_divide_max = int(self._node.evalParm("rr_seq_devidey"))

            submission.option("seq_divide_min").set([1, seq_divide_min])
            submission.option("seq_divide_max").set([1, seq_divide_max])
            # submission.add_option("SeqDivMIN", "1~{}".format(seq_divide_min))
            # submission.add_option("SeqDivMax", "1~{}".format(seq_divide_max))

        if self._node.evalParm("rr_required_memory_enabled"):
            required_memory = int(self._node.evalParm("rr_required_memory"))
            submission.option("required_memory").set([1, required_memory])
            # submission.add_option("RequiredMemory",
            #                      "1~{}".format(required_memory))

        if self._node.evalParm("rr_priority_enabled"):
            priority = int(self._node.evalParm("rr_priority"))
            submission.option("priority").set([1, priority])

        if self._node.evalParm("rr_littlejob_enabled"):
            littlejob = 1 if self._node.evalParm("rr_littlejob") else 0
            submission.option("littlejob").set([1, littlejob])

        if self._node.evalParm("rr_autodelete_enabled"):
            autodelete = 1 if self._node.evalParm("rr_autodelete") else 0
            submission.option("autodelete").set([1, autodelete])

        if self._node.evalParm("rr_autodependency_enabled"):
            autodependency = 1 if self._node.evalParm("rr_autodependency") else 0
            submission.add_custom_option("COIgnoreROPDependencies", [0, 1])
            submit_dependencies = True

        if self._node.evalParm("rr_local_scene_copy_enabled"):
            lsc = 1 if self._node.evalParm("rr_local_scene_copy") else 0
            submission.option("allow_local_scene_copy").set([0, lsc])
            # submission.add_option(
            #            "AllowLocalSceneCopy", "0~{}".format(lsc))

        if (self._node.parm("rr_assignment").eval() == 2) and self._node.parm(
            "rr_client_groups"
        ).eval():
            groups_selected = self._node.parm("rr_client_groups").eval()
            submission.option("default_client_group").set(
                [1, groups_selected.replace(" ", ";")]
            )
            # submission.add_option(
            #            "DefaultClientGroup", "1~{}".format(groups_selected.replace(" ",";")))

        if (self._node.parm("rr_assignment").eval() == 1) and self._node.parm(
            "rr_clients"
        ).eval():
            clients_selected = self._node.parm("rr_clients").eval()
            submission.option("default_client_group").set(
                [1, clients_selected.replace(" ", ";")]
            )
            # submission.add_option(
            #            "DefaultClientGroup", "1~{}".format(clients_selected.replace(" ",";")))




        if self._node.evalParm("rr_scenename_enable"):
            scName = str(self._node.evalParm("rr_scenename"))
            submission.add_custom_option("CustomSceneName", scName, "custom")


        if self._node.evalParm("rr_camera_enabled"):
            camera = self._node.evalParm("rr_camera")
            submission.add_param_override("camera", camera)

        if self._node.evalParm("rr_frange_enabled"):
            submission.add_param_override("fstart", self._node.evalParm("rr_frange1"))
            submission.add_param_override("fend", self._node.evalParm("rr_frange2"))
            submission.add_param_override("finc", self._node.evalParm("rr_frange3"))

        if self._node.evalParm("rr_res_enabled"):
            submission.add_param_override("image_width", self._node.evalParm("rr_res1"))
            submission.add_param_override("image_height", self._node.evalParm("rr_res2"))

        if self._node.evalParm("rr_take_enabled"):
            take = self._node.parm("rr_take").evalAsString()
            submission.add_param_override("channel", take)


        logger.debug("RRRop -before submission")
        
        bak_rendererPreSuffix= parseData.rendererPreSuffix
        bak_archive_mode= parseData.archive_mode
        parseData.archive_mode=self._node.parm("rr_archive_mode").eval()
        if self._node.evalParm("rr_renderconfig_enable"):
            parseData.rendererPreSuffix=self._node.parm("rr_renderconfig").eval()
        try:
            with submission:
                submitted = []
                if self._node.inputs():
                    if submit_dependencies:
                        with parseData.Dependency.create() as d:
                            for i in reversed(self._node.inputAncestors()):
                                if not i.path() in submitted:
                                    n = rrNode.create(i)
                                    n.parse(parseData)
                                    d.next()
                                    logger.debug("Added {} to submission".format(i.path()))
                                    submitted.append(i.path())
                    else:
                        for i in self._node.inputs():
                            if not i.path() in submitted:
                                n = rrNode.create(i)
                                n.parse(parseData)
                                logger.debug("Added {} to submission".format(i.path()))
                                submitted.append(i.path())
                else:
                    driver = self._node.parm("rr_driver").evalAsNode()
                    if driver:
                        n = rrNode.create(driver)
                        n.parse(parseData)
                        logger.debug("Added {} to submission".format(driver.path()))
                        if submit_dependencies:
                            with parseData.Dependency.create() as d:
                                for i in reversed(driver.inputAncestors()):
                                    if not i.path() in submitted:
                                        n = rrNode.create(i)
                                        n.parse(parseData)
                                        d.next()
                                        logger.debug(
                                            "Added {} to submission".format(i.path())
                                        )
                                        submitted.append(i.path())
        except:
            logger.error("\n   SubmitterNode 'parseChildren' Exception.\n")
            logger.error(str(traceback.format_exc()))
                                    
        parseData.archive_mode= bak_archive_mode
        parseData.rendererPreSuffix= bak_rendererPreSuffix
        logger.debug("RRRop -end")

    def dependencies(self):
        if self._node.inputs():
            return self._node.inputs()
        else:
            return [self._node.parm("rr_driver").evalAsNode()]


class SubmitterNodeLop(SubmitterNode):

    name = "rrSubmitterLOP"

class DependencyNode(rrNode):

    name = "rrDependency"

    def childclass_parse(self, parseData):
        #logger.debug("UICurrent: {}".format( hou.frame()))
        with parseData.Dependency.create() as d:
            for i in self._node.inputs():
                n = rrNode.create(i)
                n.parse(parseData)
                d.next()
