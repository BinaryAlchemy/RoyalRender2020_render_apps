# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy

import traceback 
try:
    from . import royalScheduler 
except:
    traceback.print_exc()

import sys
import os
sharedPath=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.append(sharedPath)
import royalDefs as rrDefs


def registerTypes(type_registry):
    print("\nRegistering royalScheduler " + rrDefs.plugin_version_str+ ". Houdini Python version: "+str(sys.version_info.major)+"."+str(sys.version_info.minor)+"\n") 
    
    type_registry.registerScheduler(royalScheduler.RoyalScheduler, label="royalScheduler") 
