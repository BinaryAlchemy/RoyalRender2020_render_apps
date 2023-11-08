"""
Scripting Utilities for Royal Render's Python Library
=====================================================

Provide functions and classes for caching RR modules, connect to the server, handling error results

.. note::
    importing this package caches Royal Render libraries automatically, see :func:`rr_python_utils.cache.cache_module_locally`

Import Helpers
--------------

Different versions of Python require to import a different Royal Render library:

==============  =====================  ============================  =========================
Python Version   Royal Render Module        Data Module                 Submission Module
==============  =====================  ============================  =========================
    2.7              libpyRR2            libpyRR2_datafiles             libpyRR2_submit
    3.7              libpyRR37           libpyRR37_datafiles            libpyRR37_submit
    3.9          :mod:`libpyRR39`       :mod:`libpyRR39_datafiles`    :mod:`libpyRR39_submit`
==============  =====================  ============================  =========================

Helper modules can make the import easier and ensure script compatibility between Python versions:

:mod:`rr_python_utils.load_rrlib`
---------------------------------
.. automodule:: rr_python_utils.load_rrlib

:mod:`rr_python_utils.load_rrdata`
----------------------------------
.. automodule:: rr_python_utils.load_rrdata

:mod:`rr_python_utils.load_rrsubmit`
------------------------------------
.. automodule:: rr_python_utils.load_rrsubmit

"""

import sys
from . import cache as rr_cache

rr_cache.cache_module_locally()
