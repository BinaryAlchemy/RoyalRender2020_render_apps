import sys


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
            

def render_samples_multiply(samples_factor : float):
    if samples_factor == 1.0:
        return

    r_prim = stage.GetPrimAtPath("/Render/rendersettings")
    if not r_prim:
        return

    for attr_name in ("karma:global:samplesperpixel", "karma:object:varianceaa_maxsamples", "karma:object:varianceaa_minsamples"):
        attr = r_prim.GetAttribute(attr_name)
        if attr is None:
            continue

        prev = attr.Get()
        attr.Set(round(prev * samples_factor))
        print(f"SET: {attr_name} changed from {prev} to {r_prim.GetAttribute(attr_name).Get()}")
        


params = Params()
render_samples_multiply(params.samples_factor)
