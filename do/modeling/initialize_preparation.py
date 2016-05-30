#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.initialize_preparation Initialize the data for the radiative transfer modeling pipeline.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant PTS classes and modules
from pts.modeling.preparation.initialization import PreparationInitializer
from pts.core.tools import logging, time, tables
from pts.core.tools import filesystem as fs
from pts.magic.core.frame import Frame

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()

# Basic options
parser.add_argument("image", type=str, nargs='?', help="the name of the image for which to run the initialization")

# Logging
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")
parser.add_argument("--report", action='store_true', help='write a report file')

# Configuration
parser.add_argument("--config", type=str, help="the name of a configuration file")

# Visualisation
parser.add_argument("--visualise", action="store_true", help="make visualisations")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# Set the modeling path and the log path
arguments.path = fs.cwd()
log_path = fs.join(arguments.path, "log")

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = fs.join(log_path, time.unique_name("log") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting initialize_data ...")

# -----------------------------------------------------------------

names_column = []
paths_column = []
prep_names_column = []
names = ["Image name", "Image path", "Preparation name"]

# Loop over all subdirectories of the data directory
for path, name in fs.directories_in_path(fs.join(arguments.path, "data"), not_contains="bad", returns=["path", "name"]):

    # Loop over all FITS files found in the current subdirectory
    for image_path, image_name in fs.files_in_path(path, extension="fits", not_contains="_Error", returns=["path", "name"]):

        # Open the image frame
        frame = Frame.from_file(image_path)

        # Determine the preparation name
        if frame.filter is not None: prep_name = str(frame.filter)
        else: prep_name = image_name

        # Set the row entries
        names_column.append(image_name)
        paths_column.append(image_path)
        prep_names_column.append(prep_name)

# Create the table
data = [names_column, paths_column, prep_names_column]
table = tables.new(data, names)

# Check whether the preparation directory exists
prep_path = fs.join(arguments.path, "prep")
if not fs.is_directory(prep_path): fs.create_directory(prep_path)

# Save the table
prep_info_table_path = fs.join(prep_path, "prep_info.dat")
tables.write(table, prep_info_table_path, format="ascii.ecsv")

# -----------------------------------------------------------------

# Create a PreparationInitializer instance
initializer = PreparationInitializer.from_arguments(arguments)

# Run the data initializer
initializer.run()

# -----------------------------------------------------------------
