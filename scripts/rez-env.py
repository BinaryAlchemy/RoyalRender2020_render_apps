#  Script for Rez to fix commandline issues
#  Last Change: %rrVersion%
#  Copyright (c)  Holger Schoenberger - Binary Alchemy

import sys

def escape_string(value):
    import re
    from rez.rex import EscapedString
    from functools import partial
    """Escape the <, >, ^, and & special characters reserved by Windows.

    Args:
        value (str/EscapedString): String or already escaped string.

    Returns:
        str: The value escaped for Windows.

    """
    value = EscapedString.promote(value)
    value = value.expanduser()
    result = ''
    
    _env_var_regex = re.compile("%([A-Za-z0-9_]+)%")    # %ENVVAR%
    # Regex to aid with escaping of Windows-specific special chars:
    # http://ss64.com/nt/syntax-esc.html
    _escape_re = re.compile(r'(?<!\^)[&<>]|(?<!\^)\^(?![&<>\^])|(\|)')
    _escaper = partial(_escape_re.sub, lambda m: '^' + m.group(0))    

    for is_literal, txt in value.strings:
        if is_literal:
            txt = _escaper(txt)
            # Note that cmd uses ^% while batch files use %% to escape %
            txt = _env_var_regex.sub(r"%%\1%%", txt)
        else:
            txt = _escaper(txt)
        result += txt
    return result
    
print("\n\n----------------------------------------")    
print("rrRez: Running Royal Render embedded Rez")    
import rez.utils._version as rezVer
print("rrRez: REZ module version: " + rezVer._rez_version)
print("----------------------------------------\n\n")    

if (False):
    print("------------------ARGS------------------")
    for i in range(0, len(sys.argv)):
        print(str(i) + ":" + sys.argv[i] )
    print("----------------------------------------")

    
if (sys.platform.lower() == "win32"):
    print("Escaping Windows commandline flags.")
    for i in range(1, len(sys.argv)):
        sys.argv[i]= escape_string(sys.argv[i])

if (False):
    print("------------------ARGS------------------")
    for i in range(0, len(sys.argv)):
        print(str(i) + ":" + sys.argv[i] )
    print("----------------------------------------")



if (True):
    rezPackageList=[]
    for i in range(1, len(sys.argv)):
        if (sys.argv[i] == "--"):
            break
        rezPackageList.append(sys.argv[i])
    if ('rrLocalRoot' in os.environ):
        rezInfoFolder= os.environ['rrLocalRoot']
        rezInfoFolder= rezInfoFolder.replace("\\","/")
        rezInfoFolder= rezInfoFolder + "rez/"
        try:
            if (not os.path.isdir(rezInfoFolder)):
                os.mkdir(rezInfoFolder)
            for i in range(0, len(rezPackageList)):  
                rezFilename=rezInfoFolder + rezPackageList[i] + ".timestamp"
                f = open(rezFilename, "w")
                f.write("This Rez Package was used")
                f.close()
        except Exception as e:
            print("Unable to create Rez Pack timestamp info: "+str(e))
        
            
    print("----------------------------------------")

print("rrRez: Starting Rez...") 
if (sys.version_info.major > 2):
    sys.stdout.flush()        
    sys.stderr.flush()   

from rez.cli._entry_points import run_rez_env
sys.exit(run_rez_env())
