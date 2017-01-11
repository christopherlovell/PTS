#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.parallelization Functions related to parallelization.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import psutil
import multiprocessing

# Import astronomical modules
from astropy.units import Unit

# -----------------------------------------------------------------

def ncores():

    """
    This function ...
    :return:
    """

    return psutil.cpu_count(logical=False)

# -----------------------------------------------------------------

def nthreads_per_core():

    """
    This function ...
    :return:
    """

    return psutil.cpu_count() / ncores()

# -----------------------------------------------------------------

def virtual_memory():

    """
    This function ...
    :return:
    """

    return float(psutil.virtual_memory().total) * Unit("byte")

# -----------------------------------------------------------------
