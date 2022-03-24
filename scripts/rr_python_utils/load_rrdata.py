import sys
from .errors import RR_GenericError

loaded_rrData=False

if (sys.version_info.major == 2):
    import libpyRR2_datafiles as rrData
    loaded_rrData= True
elif (sys.version_info.major == 3):
    if (sys.version_info.minor == 7):
        import libpyRR37_datafiles as rrData
        loaded_rrData= True
    elif (sys.version_info.minor == 9):
        import libpyRR39_datafiles as rrData
        loaded_rrData= True
if (not loaded_rrData):
    raise RR_GenericError("\n    Unable to load RR module for python version {}.{}.\n".format(sys.version_info.major,sys.version_info.minor))
else:
    print("libpyRR_datafiles loaded ({})".format(rrData.__file__))
    pass
