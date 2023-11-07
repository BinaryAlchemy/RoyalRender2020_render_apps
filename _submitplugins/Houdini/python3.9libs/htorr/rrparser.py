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
import sys
from htorr import rrjob
import traceback

logger = logging.getLogger("HtoRR")

def get_call_stack():
    lineIdx= 0
    allLines=""
    lineCount= len(traceback.format_stack())
    for line in traceback.format_stack():
        lineIdx= lineIdx + 1
        if (lineIdx < lineCount-5):
            continue
        if (lineIdx >= lineCount-1):
            continue
        allLines= allLines+ line.strip() + "\n"
        
    return allLines


class JobFactory(object):
    """Factory to create instances of Job."""

    def __init__(self):
        self.id = 0
        self.proccessors = []

    def create(self, isTempHelper):
        """Returns a Job instance."""
        self.id += 1
        job = rrjob.Job()
        job.pre_id = self.id
        if (not isTempHelper):
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
            #logger.debug("SubmissionFactory.get(): submission.options\n{}".format(s.options))
            #logger.debug("SubmissionFactory.get(): submission {}\n".format(s))
            
            #Copies all Jobs, bakes SubmitOptions of Submission into SubmitOptions of jobs and returns baked jobs.
            jobs =s.jobs
            for j in jobs:
                j.options.merge(s.options)
            #logger.debug("Baked_Jobs: Jobs: {}".format(jobs))
                if sys.version_info.major == 2:
                    for name, label in rrjob.RR_PARMS.iteritems():
                        if name in s.paramOverrides:
                            j.parm[name].set(s.paramOverrides[name])
                else:
                    for name, label in rrjob.RR_PARMS.items():
                        if name in s.paramOverrides:
                            #logger.debug("SubmissionFactory.get():  override {}: {}".format(name, s.paramOverrides[name]))
                            j._parms[name].set( s.paramOverrides[name])
        
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
    
    "index" is the index of the rrDependency input

    """

    logger.debug("DDDDDDDDDDDD  Dependency CLASS CONSTRUCTOR  ")
    instance_count = 0
    instance = None

    def __init__(self):
        self.jobs = [] #1st dimension. Create array by instance
        self.nodeName = [] #Array by instance_count
        self.inputIdx = [] #Array by instance_count

    def __enter__(self):
        Dependency.instance_count += 1
        logger.debug("DDDDDDDDDDDD  Dependency __enter__ {} newCount {}".format(Dependency.instance.nodeName[Dependency.instance_count-1], Dependency.instance_count))
        return self

    def __exit__(self, *kwargs):
        dm = Dependency.instance
        if not dm:
          logger.debug("DDDDDDDDDDDD  Dependency __exit__() NONE  Count: {}".format(Dependency.instance_count))
          # how come we ended up here?
          Dependency.instance_count = 0
          return
        idx_instance= Dependency.instance_count-1
        idx_input= dm.inputIdx[idx_instance]-1 #next is called after the last input, so we have to reduce it by 1
        if (Dependency.instance_count>1 and idx_input>0):
            #now copy the last jobs of this rrDependency into the parent rrDependency
            idx_P_instance= idx_instance-1            
            idx_P_input= dm.inputIdx[idx_P_instance]
            logger.debug("DDDDDDDDDDDD  Dependency __exit__() inst_count {}, name {},  inputIdx {},  job count {}".format(Dependency.instance_count, dm.nodeName[idx_instance],  dm.inputIdx[idx_instance], len(dm.jobs[idx_instance][idx_input])))
            logger.debug("DDDDDDDDDDDD  Dependency __exit__() parent   name {},  inputIdx {},  job count {}".format(dm.nodeName[idx_P_instance],  dm.inputIdx[idx_P_instance], len(dm.jobs[idx_P_instance][idx_P_input])))
            for job in dm.jobs[idx_instance][idx_input]:
                dm.jobs[idx_P_instance][idx_P_input].append(job)
        logger.debug("DDDDDDDDDDDD  Dependency __exit__ {} newCount {}".format(dm.nodeName[idx_instance], Dependency.instance_count-1))
        #remove data of this rrDependency node
        dm.nodeName.pop(idx_instance)
        dm.inputIdx.pop(idx_instance)
        dm.jobs.pop(idx_instance) 
        Dependency.instance_count -= 1
        
        

    def next(self):
        """Call to start a new dependency.
        All following jobs which are created will be dependent on the jobs before the function call.
        """
        idx_instance= self.instance_count-1
        idx_input= self.inputIdx[idx_instance]
        logger.debug("DDDDDDDDDDDD  Dependency next() inst_count {}, name {},  inputIdx {},  job count {}".format(self.instance_count, self.nodeName[idx_instance],  self.inputIdx[idx_instance], len(self.jobs[idx_instance][idx_input])))
        if idx_input >= 0: #there was an input before
            if len(self.jobs[idx_instance][idx_input])==0: # but no jobs added, so we overwrite the last slot
                return
        self.inputIdx[idx_instance] += 1
        self.jobs[idx_instance].append([])  #For this instance, for new inputIdx, create job Array
        

    @classmethod
    def process(cls, job):
        """Adds dependencies to job
        
        Called when a new job is created.
        Adds all jobs of last input self.jobs[inputIdx-1] as dependencies to this new job and adds new job to self.jobs[inputIdx]

        Arguments:
            job Job -- job to add dependencies
        """
        #logger.debug("DDDDDDDDDDDD  Dependency process() \n{}".format(get_call_stack()))
        if cls.instance_count > 0:
            dm = cls.instance
            idx_instance= cls.instance_count-1
            idx_input= dm.inputIdx[idx_instance]
            logger.debug("DDDDDDDDDDDD  Dependency process() inst_count {}, name {},  inputIdx {},  job count {}+1".format(cls.instance_count, dm.nodeName[idx_instance],  dm.inputIdx[idx_instance], len(dm.jobs[idx_instance][idx_input])))
            
            if (idx_input>0):          
                #Add all jobs of last input as dependencies to this new job
                job.add_dependency( dm.jobs[idx_instance][idx_input-1])

            if (cls.instance_count > 1):     
                #Add all jobs of last instance  as dependencies to this new job
                PRE_idx_instance= cls.instance_count-2
                PRE_idx_input= dm.inputIdx[PRE_idx_instance]
                if (PRE_idx_input>0):          
                    job.add_dependency( dm.jobs[PRE_idx_instance][PRE_idx_input-1])

                
            #adds new job to this input self.jobs[inputIdx]
            dm.jobs[idx_instance][idx_input].append(job)
            

    @classmethod
    def create(cls, name):
        """Factory method for Dependency instances"""
        if cls.instance_count == 0:
            dm = cls()
            cls.instance = dm
            cls.instance_count = 0
        cls.instance.nodeName.append(name)
        cls.instance.inputIdx.append(0) #For this instance, create input 0
        cls.instance.jobs.append([]) #For this instance, create input array
        cls.instance.jobs[cls.instance_count].append([]) #For this instance, for input 0, create job array

        logger.debug("DDDDDDDDDDDD  Dependency create {} Instances {} ".format(name, cls.instance_count))
        return cls.instance

    @classmethod
    def reset(cls):
        """Since been used as a Singleton, this method resets all values"""
        logger.debug("DDDDDDDDDDDD  Dependency RESET  \n{}".format(get_call_stack()))
        cls.instance_count = 0
        cls.instance = None


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
    isTempHelper = False  #will not result into any jobs that are submitted

    def __init__(self):
        self.SubmissionFactory = SubmissionFactory()
        self.Job = JobFactory()
        self.Job.register(self.SubmissionFactory)
        self.Job.register(Wedge)
        self.Job.register(Dependency)
        self.archive_mode= 0
        self.rendererPreSuffix= ""

    def __del__(self):
        if (not isTempHelper):
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
