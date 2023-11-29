"""
Imports Royal Render main module for the current version of Python,
e.g. :mod:`libpyRR39`

.. code-block:: python

    from rr_python_utils.load_rrlib import rrLib
"""

import sys
import logging
from .errors import RR_GenericError

loaded_rrLib=False
global rrLib
rrLogger=logging.getLogger("rrPy")

if (sys.version_info.major == 2):
    import libpyRR2 as rrLib
    loaded_rrLib= True
elif (sys.version_info.major == 3):
    if (sys.version_info.minor == 7):
        import libpyRR37 as rrLib
        loaded_rrLib= True
    elif (sys.version_info.minor == 9):
        import libpyRR39 as rrLib
        loaded_rrLib= True
    elif (sys.version_info.minor == 10):
        import libpyRR310 as rrLib
        loaded_rrLib= True
if (not loaded_rrLib):
    raise RR_GenericError("\n    Unable to load RR module for python version {}.{}.\n".format(sys.version_info.major,sys.version_info.minor))
else:
    rrLogger.info("libpyRR loaded ({})".format(rrLib.__file__))
    pass
