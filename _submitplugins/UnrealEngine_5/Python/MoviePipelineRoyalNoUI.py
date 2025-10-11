# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Plugin script for Unreal Engine
# Copyright (c)  Holger Schoenberger
#
# Last change: %rrVersion%
# 
######################################################################
#
#
# Royal Render No UI Executor
#
# Same as MoviePipelineRoyalSubmit but doesn't show RR Submitter UI
#
# REQUIREMENTS:
#    Requires the "Python Editor Script Plugin" to be enabled in your project.
#
#

import unreal
from MoviePipelineRoyalSubmit import create_base_job, collect_rr_jobs, submit_rr_jobs


@unreal.uclass()
class MoviePipelineRoyalNoUI(unreal.MoviePipelinePythonHostExecutor):

    @unreal.ufunction(override=True)
    def execute_delayed(self, inPipelineQueue):
        base_job_rr = create_base_job()
        rr_jobs = collect_rr_jobs(base_job_rr, inPipelineQueue)
        submit_rr_jobs(base_job_rr, rr_jobs, show_ui=False)

    @unreal.ufunction(override=True)
    def is_rendering(self):
        return False
