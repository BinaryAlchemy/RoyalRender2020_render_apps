# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

"""@package rrparser
This module contains classes to parse a node network into Submissions containing Jobs and SubmitOptions.
Core of this module is the ParseData class, which has to be passed on when calling the parse method on a Houdini Node wrapper class.
An instance of ParseData gives access to the other classes implemented in this module. In order to gather the main parsing logic in one place,
most of the parsing logic is contained in these classes, while the parsing logic implemented in the class rrNode and its subclasses is kept to a minimum.
Jobs and Submissions should be created through their dedicated Factories: JobFactory and SubmissionFactory. 
For Wedge, Override and Dependency a dedicated class is available. 
Wedge, Override, Dependency and SubmissionFactory are registered processors in JobFactory. After a job is created by the JobFactory, the job is handed to all the processors, where 
required adjustments can be made, for example adding a job to a submission, creating parameter overrides or setting job dependencies. 
Finally the job is returned, to be further adjusted inside a rrNode instance.
Wedge, Override, Dependency are designed as context managers. The designated usage is to enter these managers if needed, parse all the node inputs and exit when finished.
This is mainly necessary to alter the job processing, whenever a job is created, while beeing inside of a context manager. 
"""

from cmath import log
import logging

from htorr import rrjob

logger = logging.getLogger("HtoRR")


class JobFactory(object):
    """Factory to create instances of Job."""

    def __init__(self):
        self.id = 0
        self.proccessors = []

    def create(self):
        """Returns a Job instance."""
        self.id += 1
        job = rrjob.Job()
        job.pre_id = self.id
        for p in self.proccessors:
            p.process(job)
        return job

    def register(self, proccessor):
        """Register a Processor which will be called when a Job is created."""
        self.proccessors.append(proccessor)


class SubmissionFactory(object):
    """Factory to create instances of Submission.

    Implements Job Processor interface.
    """

    def __init__(self):
        logger.debug("Submission factory init")
        self._submissions = []
        self._stack = []

    def create(self):
        """Creates and returns a Submission instance"""
        s = rrjob.Submission()

        self._submissions.append(s)
        s._factory = self
        return s

    def process(self, job):
        """Adds a job to the latest submission"""
        if self._stack:
            self._stack[-1].jobs.append(job)
            job.submission = self._stack[-1]
        else:
            subm = self.create()
            subm.jobs.append(job)
            job.submission = subm

    def get(self):
        """Merges all created submissions into one submission and returns it"""
        submission_converted = None
        logger.debug("SubmissionFactory, Get")
        
        if len(self._submissions) == 0:
            return None

        # if len(self._submissions) == 1:
        # submission_converted = self._submissions[0]

        submission_converted = rrjob.Submission()
        for s in self._submissions:
            logger.debug("SubmissionFactory.get(): submission.options\n{}".format(s.options))
            logger.debug("SubmissionFactory.get(): submission {}\n".format(s))
            
            #Copies all Jobs, bakes SubmitOptions of Submission into SubmitOptions of jobs and returns baked jobs.
            jobs =s.jobs
            for j in jobs:
                j.options.merge(s.options)
            #logger.debug("Baked_Jobs: Jobs: {}".format(jobs))

            for j in jobs:
                logger.debug("Submission Jobs: {}".format(j))
                submission_converted.jobs.append(j)

        if not submission_converted:
            return None

        return submission_converted


class Dependency(object):
    """Job Processor class to handle job dependencies.

    It is designed as a Singleton. Use class method create() to obtain an instance. This class keeps track of how many times the current instance was entered
    as a context manager by increasing the instance count. When context mangager is exited instance count decreases by one.
    Only if the instance count is zero a new instance will be created, otherwise the current instance will be returned.

    """

    instance_count = 0
    instance = None

    def __init__(self):

        logger.debug("DepManager created")
        self.jobs = [[], []]
        self.index = 1

    def __enter__(self):
        Dependency.instance_count += 1
        return self

    def __exit__(self, *kwargs):
        Dependency.instance_count -= 1
        logger.debug("DepManager closed")

    def next(self):
        """Call to start a new dependency.
        All following jobs which are created will be dependent on the jobs before the function call.
        """
        if not self.jobs[self.index]:
            return
        self.index += 1
        self.jobs.append([])

    @classmethod
    def process(cls, job):
        """Adds dependencies to job

        Adds all jobs at self.jobs[index-1] as dependencies to job and adds job to self.jobs[index]

        Arguments:
            job Job -- job to add dependencies
        """

        if cls.instance_count > 0:
            dm = cls.instance
            job.set_dependency(dm.jobs[dm.index - 1])
            dm.jobs[dm.index].append(job)

    @classmethod
    def create(cls):
        """Factory mehtod for Dependency instances"""
        if cls.instance_count == 0:
            dm = cls()
            cls.instance = dm
        return cls.instance

    @classmethod
    def reset(cls):
        """Since been used as a Singleton, this mehtod resets all values"""
        cls.instance_count = 0
        cls.instance = None
        # logger.debug("Dependency reset")


class Wedge(object):
    """Job Processor class for Wedge functionality.

    Call create method to obtain an instance. Only one instance at a time is supported.
    A Value Error is raised when trying to obtain multiple instances.
    """

    instance = None

    def __init__(self, path):
        self.path = path
        self.count = 0

    def __enter__(self):
        return self

    def __exit__(self, *kwargs):
        self.end()

    def next(self):
        self.count += 1

    @classmethod
    def create(cls, path):
        """Create and return Wedge instance.

        Arguments:
            path String -- Wedge node path

        Raises:
            ValueError: when creating more then one instance

        Returns:
            Wedge -- instance of Wedge class
        """
        if not cls.instance:
            cls.instance = cls(path)
            return cls.instance
        else:
            raise ValueError("Multiple Wedge Nodes not supported")

    @classmethod
    def end(cls):
        """Class method to reset Wedge node. Called as context manager when exited."""
        cls.instance = None

    @classmethod
    def process(cls, job):
        """Processes Job instance to add scene state parameter for wedging.

        Arguments:
            job Job -- job instance to be proccessed.
        """
        if cls.instance:
            job.scene_state = cls.get_state()

    @staticmethod
    def get_state():
        """Static method to obtain wedge state as string, which can be used for job scene state parameter."""
        if Wedge.instance:
            return "{}*{}".format(Wedge.instance.path, Wedge.instance.count)

    @classmethod
    def reset(cls):
        """Resets class attributes."""
        cls.instance = None


class ParseData(object):
    """Class to store classes and class instances which are necessary for parsing nodes.

    An instance of this class gives access to classes and instances in this module which are used by the rrNode parse method to parse a node network into a submission.
    """

    Wedge = Wedge
    Dependency = Dependency

    def __init__(self):
        self.SubmissionFactory = SubmissionFactory()
        self.Job = JobFactory()
        self.Job.register(self.SubmissionFactory)
        self.Job.register(Wedge)
        self.Job.register(Dependency)
        self.archive_mode= 0
        self.rendererPreSuffix= ""

    def __del__(self):
        Wedge.reset()
        Dependency.reset()


class ParserHandler(logging.StreamHandler):
    """Specialized Logging Handler, which can be used to catch logging messages and store them in a list to retrieve at a later point."""

    loggs = []

    def emit(self, record):
        msg = self.format(record)
        ParserHandler.loggs.append(msg)

    @staticmethod
    def clear():
        ParserHandler.loggs = []

    @staticmethod
    def get():
        return ParserHandler.loggs
