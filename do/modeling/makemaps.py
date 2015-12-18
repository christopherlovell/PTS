#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.makemaps Make maps as input for a SKIRT radiative transfer model

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant PTS classes and modules
from pts.modeling.core import MapMaker

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument('map', type=str, help='the map to be made (dust, old, Y, IY)')
parser.add_argument('--config', type=str, help='the name of a configuration file', default=None)

# Parse the command line arguments
args = parser.parse_args()

# Set the command-line options
path = args.path
config_file = args.config

# -----------------------------------------------------------------

# Create a MapMaker object
maker = MapMaker(config_file)

# Run the map making
maker.run()

# -----------------------------------------------------------------
