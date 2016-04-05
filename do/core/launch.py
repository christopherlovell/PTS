#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.core.launch Launch a SKIRT simulation locally or remotely with the best performance, based on the
#  current load of the system.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import argparse

# Import the relevant PTS classes and modules
from pts.core.launch.launcher import SkirtLauncher
from pts.core.launch.remotelauncher import SkirtRemoteLauncher
from pts.core.tools import logging, time, parsing

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument("file", type=str, help="the name of the ski/fski file")
parser.add_argument("-i", "--input", type=str, help="the simulation input path")
parser.add_argument("-o", "--output", type=str, help="the simulation output path")
parser.add_argument("-r", "--remote", type=str, help="run the simulation remotely")
parser.add_argument("-c", "--cluster", type=str, help="add the name of the cluster if different from the default")
parser.add_argument("-p", "--parallel", type=parsing.int_tuple, help="specify the parallelization scheme (processes, threads per process)")
parser.add_argument("-t", "--walltime", type=parsing.duration, help="specify an estimate for the walltime of the simulation for the specified parallelization scheme")
parser.add_argument("--relative", action="store_true", help="treats the given input and output paths as being relative to the ski/fski file")
parser.add_argument("--brief", action="store_true", help="enable brief console logging")
parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging mode")
parser.add_argument("-m", "--memory", action="store_true", help="enable memory logging mode")
parser.add_argument("-a", "--allocation", action="store_true", help="enable memory (de)allocation logging mode")
parser.add_argument("-e", "--emulate", action="store_true", help="emulate the simulation while limiting computation")
parser.add_argument("--extractprogress", action="store_true", help="extract the progress from the log files")
parser.add_argument("--extracttimeline", action="store_true", help="extract the timeline from the log files")
parser.add_argument("--extractmemory", action="store_true", help="extract the memory usage from the log files")
parser.add_argument("--plotseds", action="store_true", help="make plots of the output SEDs")
parser.add_argument("--plotgrids", action="store_true", help="make plots of the dust grid")
parser.add_argument("--plotprogress", action="store_true", help="make plots of the progress of the different processes as a function of time")
parser.add_argument("--plottimeline", action="store_true", help="make a plot of the timeline for the different processes")
parser.add_argument("--plotmemory", action="store_true", help="make a plot of the memory consumption as a function of time")
parser.add_argument("--makergb", action="store_true", help="add this option to make RGB images from the SKIRT output")
parser.add_argument("--makewave", action="store_true", help="add this option to make a wave movie from the SKIRT output")
parser.add_argument("--fluxes", action="store_true", help="add this option to calculate observed fluxes from the SKIRT output SEDs")
parser.add_argument("--images", action="store_true", help="add this option to make observed images from the SKIRT output datacubes")
parser.add_argument("--debug", action="store_true", help="add this option to enable debug output")
parser.add_argument('--report', action='store_true', help='write a report file')
parser.add_argument("--keep", action="store_true", help="add this option to keep the remote input and output")
parser.add_argument("--retrieve", type=parsing.string_list, help="specify the types of output files that have to be retrieved")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# Determine the full path to the parameter file
arguments.filepath = os.path.abspath(arguments.file)

# Determine the full path to the input and output directories
if arguments.input is not None: arguments.input_path = os.path.abspath(arguments.input)
if arguments.output is not None: arguments.output_path = os.path.abspath(arguments.output)

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = os.path.join(os.getcwd(), time.unique_name("launch") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting launch ...")

# -----------------------------------------------------------------

# If the parameter file describes a SKIRT simulation
if arguments.filepath.endswith(".ski"):

    # Either create a SkirtRemoteLauncher or a SkirtLauncher
    if arguments.remote: launcher = SkirtRemoteLauncher.from_arguments(arguments)
    else: launcher = SkirtLauncher.from_arguments(arguments)

    # Run the launcher (the simulation is performed locally or remotely depending on which launcher is used)
    launcher.run()

# If the parameter file describes a FitSKIRT simulation
elif arguments.filepath.endswith(".fski"):

    raise ValueError("Launching FitSkirt simulations is not supported yet")

# If the parameter file has a different extension
else: raise argparse.ArgumentError(arguments.filepath, "The parameter file is not a ski or fski file")

# -----------------------------------------------------------------
