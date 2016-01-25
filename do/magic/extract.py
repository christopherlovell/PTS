#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.magic.extract Run galaxy, star and sky extraction on an image

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import argparse

# Import the relevant AstroMagic classes and modules
from pts.magic.core import Image
from pts.magic.basics import Mask
from pts.magic import Extractor
from pts.core.tools import configuration

# -----------------------------------------------------------------

def int_list(string):

    """
    This function returns a list of integer values, based on a string denoting a certain range (e.g. '3-9') or a
    set of integer values seperated by commas ('2,14,20')
    :param string:
    :return:
    """

    # Split the string
    splitted = string.split('-')

    if len(splitted) == 0: raise argparse.ArgumentError("not_stars/remove_stars/not_saturation", "No range given")
    elif len(splitted) == 1:

        splitted = splitted[0].split(",")

        # Check if the values are valid
        for value in splitted:
            if not value.isdigit(): raise argparse.ArgumentError("not_stars/remove_stars/not_saturation", "Argument contains unvalid characters")

        # Only leave unique values
        return list(set([int(value) for value in splitted]))

    elif len(splitted) == 2:

        if not (splitted[0].isdigit() and splitted[1].isdigit()): raise argparse.ArgumentError("not_stars/remove_stars/not_saturation", "Not a valid integer range")
        return range(int(splitted[0]), int(splitted[1])+1)

    else: raise argparse.ArgumentError("not_stars/remove_stars/not_saturation", "Values must be seperated by commas or by a '-' in the case of a range")

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()
parser.add_argument("image", type=str, help="the name of the input image")
parser.add_argument('--report', action='store_true', help='write a report file')
parser.add_argument('--config', type=str, help='the name of a configuration file', default=None)
parser.add_argument("--settings", type=configuration.from_string, help="settings")
parser.add_argument("--regions", action="store_true", help="write regions")
parser.add_argument("--catalogs", action="store_true", help="write catalogs")
parser.add_argument("--masks", action="store_true", help="write masks")
parser.add_argument("--segments", action="store_true", help="write segmentation map of other sources")
parser.add_argument("--build", action="store_true", help="build the stellar catalog")
parser.add_argument("--not_stars", type=int_list, help="the indices of stars which should not be removed")
parser.add_argument("--remove_stars", type=int_list, help="the indices of stars that should be removed")
parser.add_argument("--not_saturation", type=int_list, help="the indices of stars which are not sources of saturation")
parser.add_argument("--filecatalog", action="store_true", help="use file catalogs")
parser.add_argument("-i", "--input", type=str, help="the name of the input directory")
parser.add_argument("-o", "--output", type=str, help="the name of the output directory")
parser.add_argument("--ignore", type=str, help="the name of the file specifying regions to ignore")
parser.add_argument("--special", type=str, help="the name of the file specifying regions with objects needing special attention")
parser.add_argument("--debug", action="store_true", help="enable debug logging mode")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# -- Input --

# If an input directory is given
if arguments.input is not None:

    # Determine the full path to the input directory
    arguments.input_path = os.path.abspath(arguments.input)

    # Give an error if the input directory does not exist
    if not os.path.isdir(arguments.input_path): raise argparse.ArgumentError(arguments.input_path, "The input directory does not exist")

# If no input directory is given, assume the input is placed in the current working directory
else: arguments.input_path = os.getcwd()

# -- Output --

# If an output directory is given
if arguments.output is not None:
    
    # Determine the full path to the output directory
    arguments.output_path = os.path.abspath(arguments.output)
    
    # Create the directory if it does not yet exist
    if not os.path.isdir(arguments.output_path): os.makedirs(arguments.output_path)

# If no output directory is given, place the output in the current working directory
else: arguments.output_path = os.getcwd()

# -----------------------------------------------------------------

# Determine the full path to the image
image_path = os.path.abspath(arguments.image)

# Open the image
image = Image(image_path)

# -----------------------------------------------------------------

# Create a mask for the nans in the primary
mask = Mask.is_nan(image.frames.primary)

# Create an Extractor instance and configure it according to the command-line arguments
extractor = Extractor.from_arguments(arguments)

# Run the extractor
extractor.run(image.frames.primary, mask)

# Save the result
extractor.write_result(image.original_header)

# -----------------------------------------------------------------
