#  Render script for Husk
#  Last Change: %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy


import sys
import json
import math

class Params():
    def __init__(self):
        self.samples_factor = 1.0
        
        self.parse_args()

    def parse_args(self):
        for i, arg in enumerate(sys.argv):
            if arg == '-AASamples':
                try:
                    aa_samples = sys.argv[i + 1]
                except IndexError:
                    print(f"WARNING: no value given for parameter {arg}")
                    continue
                
                try:
                    self.samples_factor = float(aa_samples)
                except ValueError:
                    print(f"WARNING: can't convert {arg} {aa_samples} to a decimal number")
            
def getSampleThreshold(half_effect, samples_multi, old_threshold):
    if samples_multi == 1.0:
        return old_threshold
    if (half_effect):
        samples_multi = (samples_multi + 1.0) / 2.0
    new_threshold = math.pow(samples_multi, -2) * old_threshold
    if (new_threshold > 0.75):
        new_threshold = 0.75
    if (new_threshold < 0.0005):
        new_threshold = 0.0005
    return new_threshold

def render_samples_multiply(samples_factor : float):
    if samples_factor == 1.0:
        return
    print("husk_prerender.py version %rrVersion%")

    r_prim = stage.GetPrimAtPath("/Render/rendersettings")
    if not r_prim:
        return

    for attr_name in ("arnold:global:AA_samples_max", "arnold:global:AA_samples", "karma:global:samplesperpixel", "karma:global:samplesperpixel", "karma:object:varianceaa_maxsamples"):
        #print("DGB: {}".format(attr_name) )
        attr = r_prim.GetAttribute(attr_name)
        #print("DGB: attr is {}".format(type(attr)) )
        if attr is None:
            continue
        prev = attr.Get()
        if prev is None:
            continue
        #print("DGB: prev is {}".format(type(prev)) )
        attr.Set(round(prev * samples_factor))
        print("SET: {} changed from {} to {}".format(attr_name, prev, r_prim.GetAttribute(attr_name).Get()) )


    for attr_name in ("arnold:global:AA_adaptive_threshold"):
        attr = r_prim.GetAttribute(attr_name)
        if attr is None:
            continue
        prev = attr.Get()
        if prev is None:
            continue
        attr.Set(getSampleThreshold(True, samples_factor, prev))
        print("SET: {} changed from {0:.4f} to {0:.4f}".format(attr_name, prev, r_prim.GetAttribute(attr_name).Get()) )
      
    attr = r_prim.GetAttribute("karma:global:pixeloracle")
    if attr is not None:
        try:
            attrStr= attr.Get()
            if attrStr is not None:
                if (attrStr.find("variance")>0) and (attrStr.find("minrays")>0):
                    obj = json.loads(attrStr)
                    
                    newThres= getSampleThreshold(True, samples_factor, obj[1]["variance"])
                    print("SET: {} changed from {0:.4f} to {0:.4f}".format("variance", obj[1]["variance"], newThres) )
                    obj[1]["variance"]= newThres
                    
                    oldVal= obj[1]["minrays"]
                    if (samples_factor <= 0.5):
                        obj[1]["minrays"]= -2
                    elif (obj[1]["minrays"] > 0) and (samples_factor < 1.0):
                        obj[1]["minrays"] = round(obj[1]["minrays"] * samples_factor) 
                    print("SET: {} changed from {0:.4f} to {0:.4f}".format("variance", oldVal, obj[1]["minrays"]) )
                    attrStr= json.dumps(obj)
                    attr.Set(attrStr)
        except Exception as e:
            print("ERROR: " +  str(e)+"\n")      


params = Params()
render_samples_multiply(params.samples_factor)
