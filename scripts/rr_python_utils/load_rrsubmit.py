"""
Imports Royal Render submission module for the current version of Python,
e.g. :mod:`libpyRR39_submit`

.. code-block:: python

    from rr_python_utils.load_rrsubmit import rrSubmitLib
"""
import sys
import logging
from .errors import RR_GenericError

loaded_rrSubmit=False
global rrSubmitLib
rrLogger=logging.getLogger("rrPy")

if (sys.version_info.major == 2):
    import libpyRR2_submit as rrSubmitLib
    loaded_rrSubmit= True
elif (sys.version_info.major == 3):
    if (sys.version_info.minor == 7):
        import libpyRR37_submit as rrSubmitLib
        loaded_rrSubmit= True
    elif (sys.version_info.minor == 9):
        import libpyRR39_submit as rrSubmitLib
        loaded_rrSubmit= True
    elif (sys.version_info.minor == 10):
        import libpyRR310_submit as rrSubmitLib
        loaded_rrSubmit= True
if (not loaded_rrSubmit):
    raise RR_GenericError("\n    Unable to load RR module for python version {}.{}.\n".format(sys.version_info.major,sys.version_info.minor))
else:
    rrLogger.info("libpyRR_submit loaded ({})".format(rrSubmitLib.__file__))
    pass
