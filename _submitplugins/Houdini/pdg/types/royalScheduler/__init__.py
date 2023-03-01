# Last change: v9.0.00
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
    print("Registering royalScheduler " + rrDefs.plugin_version_str+ ". Houdini Python version: "+str(sys.version_info.major)+"."+str(sys.version_info.minor)) 
    
    type_registry.registerScheduler(royalScheduler.RoyalScheduler, label="royalScheduler") 
