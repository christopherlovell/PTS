#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.parsing Provides useful functions for parsing strings into a variety of types.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import re

# Import astronomical modules
from astropy.coordinates import Angle
from astropy.units import Unit

# Import the relevant PTS classes and modules
from ..basics.range import IntegerRange, RealRange, QuantityRange
from ...magic.basics.vector import Vector
from . import filesystem as fs
from ..basics.filter import Filter

# -----------------------------------------------------------------

def boolean(entry):

    """
    Boolean value (True or False). Allowed: 'True', 'T', 'y', 'yes', 'False', 'n', 'no'
    :param entry:
    :return:
    """

    lowercase = entry.lower().strip()

    if lowercase == "true" or lowercase == "y" or lowercase == "yes" or lowercase == "t": return True
    elif lowercase == "false" or lowercase == "n" or lowercase == "no" or lowercase == "f": return False
    else: raise ValueError("Invalid boolean specification: " + entry)

# -----------------------------------------------------------------

def integer(argument):

    """
    Integer value
    :param argument:
    :return:
    """

    return int(argument)

# -----------------------------------------------------------------

def positive_integer(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    value = integer(argument)
    if value < 0: raise ValueError("Value is smaller than zero")
    return value

# -----------------------------------------------------------------

def negative_integer(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    value = integer(argument)
    if value > 0: raise ValueError("Value is greater than zero")
    return value

# -----------------------------------------------------------------

def real(argument):

    """
    Real (floating-point) value
    :param argument:
    :return:
    """

    return float(argument)

# -----------------------------------------------------------------

def positive_real(argument):

    """
    Positive real (floating-point) value (>=0)
    :param argument:
    :return:
    """

    value = real(argument)
    if value < 0: raise ValueError("Value is smaller than zero")
    return value

# -----------------------------------------------------------------

def negative_real(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    value = real(argument)
    if value > 0: raise ValueError("Value is greater than zero")
    return value

# -----------------------------------------------------------------

def fraction(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    value = real(argument)
    if value > 1 or value < 0: raise ValueError("Value should be from 0 to 1")
    return value

# -----------------------------------------------------------------

def string(argument):

    """
    String
    :param argument:
    :return:
    """

    return argument

# -----------------------------------------------------------------

def real_range(argument):

    """
    Range of real (floating-point) values
    :param argument:
    :return:
    """

    min_value, max_value = real_tuple(argument.replace(">", ","))
    return RealRange(min_value, max_value)

# -----------------------------------------------------------------

def integer_range(argument):

    """
    Range of integer values
    :param argument:
    :return:
    """

    min_value, max_value = integer_tuple(argument.replace(">", ","))
    return IntegerRange(min_value, max_value)

# -----------------------------------------------------------------

def quantity_range(argument):

    """
    Range of (Astropy) quantities
    :param argument:
    :return:
    """

    min_quantity, max_quantity = quantity_tuple(argument.replace(">", ","))
    return QuantityRange(min_quantity, max_quantity)

# -----------------------------------------------------------------

def directory_path(argument):

    """
    Converts a relative path or directory name to an absolute directory path, and checks whether this
    directory exists
    :param argument:
    :return:
    """

    path = fs.absolute_path(argument)
    if not fs.is_directory(path): raise ValueError("Is not a directory: " + path)
    return path

# -----------------------------------------------------------------

def directorypath_list(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return [directory_path(path) for path in string_list(argument)]

# -----------------------------------------------------------------

def file_path(argument):

    """
    Converts a relative path or filename to an absolute filepath, and checks whether this file exists
    :param argument:
    :return:
    """

    path = fs.absolute_path(argument)
    if not fs.is_file(path): raise ValueError("Is not a file: " + path)
    return path

# -----------------------------------------------------------------

def filepath_list(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return [file_path(path) for path in string_list(argument)]

# -----------------------------------------------------------------

def integer_tuple(argument):

    """
    Tuple of integer values
    :param argument:
    :return:
    """

    try:
        a, b = map(int, argument.split(','))
        return a, b
    except: raise ValueError("Tuple must be of format a,b")

# -----------------------------------------------------------------

def real_tuple(argument):

    """
    Tuple of real (floating-point) values
    :param argument:
    :return:
    """

    try:
        a, b = map(float, argument.split(","))
        return a, b
    except: raise ValueError("Tuple must be of format a,b")

# -----------------------------------------------------------------

def quantity_tuple(argument):

    """
    Tuple of (Astropy) quantities
    :param argument:
    :return:
    """

    try:
        a, b = map(quantity, argument.split(","))
        return a, b
    except: raise ValueError("Tuple must be of format a unit_a, b unit_b")

# -----------------------------------------------------------------

def mixed_tuple(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return tuple(argument.split(","))

# -----------------------------------------------------------------

def quantity_vector(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    tuple_string = argument.split("(")[1].split(")")[0]
    x, y = tuple_string.split(", ")

    x = quantity(x[2:])
    y = quantity(y[2:])

    return Vector(x, y)

# -----------------------------------------------------------------

def string_list(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return argument.split(",")

# -----------------------------------------------------------------

def mixed_list(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return [eval(value) for value in argument.split(",")]

# -----------------------------------------------------------------

def duration(argument):

    """
    Duration in seconds from hh:mm:ss format
    :param argument:
    :return:
    """

    # Calculate the walltime in seconds
    hours, minutes, seconds = argument.split(':')
    duration = int(hours)*3600 + int(minutes)*60 + int(seconds)

    # Return the duration in seconds
    return duration

# -----------------------------------------------------------------

def integer_list(string):

    """
    A list of integer values, based on a string denoting a certain range (e.g. '3-9') or a
    set of integer values seperated by commas ('2,14,20')
    :param string:
    :return:
    """

    if "-" in string and "," in string:

        parts = string.split(",")
        total_int_list = []
        for part in parts: total_int_list += integer_list(part)
        return total_int_list

    # Split the string
    splitted = string.split('-')

    if len(splitted) == 0: raise ValueError("No range given")
    elif len(splitted) == 1:

        splitted = splitted[0].split(",")

        # Check if the values are valid
        for value in splitted:
            if not value.isdigit(): raise ValueError("Argument contains unvalid characters")

        # Only leave unique values
        return list(set([int(value) for value in splitted]))

    elif len(splitted) == 2:

        if not (splitted[0].isdigit() and splitted[1].isdigit()): ValueError("Not a valid integer range")
        return range(int(splitted[0]), int(splitted[1])+1)

    else: raise ValueError("Values must be seperated by commas or by a '-' in the case of a range")

# -----------------------------------------------------------------

def real_list(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return [real(value) for value in string_list(argument)]

# -----------------------------------------------------------------

def dictionary(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    d = eval(argument)
    if not isinstance(d, dict): raise ValueError("Not a proper specification of a dictionary")
    return d

# -----------------------------------------------------------------

def simulation_ids(string):

    """
    The IDs of remote simulations
    :param string:
    :return:
    """

    # Initialize a dictionary
    delete = dict()

    # If the string is empty, raise an error
    if not string.strip(): raise ValueError("No input for argument")

    # Split the string by the ';' character, so that each part represents a different remote host
    for entry in string.split(";"):

        # Split again to get the host ID
        splitted = entry.split(":")

        # Get the host ID
        host_id = splitted[0]

        # Get the simulation ID's
        values = integer_list(splitted[1])

        # Add the simulation ID's to the dictionary for the correspoding host ID
        delete[host_id] = values

    # Return the dictionary with ID's of simulations that should be deleted
    return delete

# -----------------------------------------------------------------

def unit(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return Unit(argument)

# -----------------------------------------------------------------

def quantity(argument):

    """
    An Astropy quantity.
    >>> quantity("2GB")
    (2.0, 'GB')
    >>> quantity("17 ft")
    (17.0, 'ft')
    >>> quantity("   3.4e-27 frobnitzem ")
    (3.4e-27, 'frobnitzem')
    >>> quantity("9001")
    (9001.0, '')
    >>> quantity("spam sandwhiches")
    (1.0, 'spam sandwhiches')
    >>> quantity("")
    (1.0, '')
    """

    # NEW IMPLEMENTATION
    units = ""
    number = 1.0
    while argument:
        try:
            number = float(argument)
            break
        except ValueError:
            units = argument[-1:] + units
            argument = argument[:-1]
    return number * Unit(units.strip())

    # FIRST IMPLEMENTATION
    #splitted = argument.split()
    #value = float(splitted[0])
    #unit = Unit(splitted[1])
    #return value * unit

    # http://stackoverflow.com/questions/2240303/separate-number-from-unit-in-a-string-in-python

    # SECOND IMPLEMENTATION
    #numeric = '0123456789-.'
    #for i, c in enumerate(argument + " "):
    #    if c not in numeric:
    #        break
    #value = argument[:i]
    #unit = Unit(argument[i:].lstrip())
    #return value * unit

# -----------------------------------------------------------------

def angle(argument, default_unit=None):

    """
    An Astropy Angle
    :param argument:
    :param default_unit:
    :return:
    """

    # OLD IMPLEMENTATION
    #splitted = entry.split()
    #value = float(splitted[0])
    #try: unit = splitted[1]
    #except IndexError: unit = default_unit
    # Create an Angle object and return it
    #if unit is not None: value = Angle(value, unit)
    #return value

    # NEW IMPLEMENTATION
    units = ""
    number = 1.0
    while argument:
        try:
            number = float(argument)
            break
        except ValueError:
            units = argument[-1:] + units
            argument = argument[:-1]

    if not units: # if string is empty

        if default_unit is None: raise ValueError("Unit not specified")
        else: units = default_unit

    # Create and return the Angle object
    return Angle(number, units)

# -----------------------------------------------------------------

def pixel_limits(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    lst = integer_list(argument)
    assert len(lst) == 4
    return lst

# -----------------------------------------------------------------

def calibration_error(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    from ...magic.misc.calibration import CalibrationError
    return CalibrationError.from_string(argument)

# -----------------------------------------------------------------

def url(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not regex.match(argument): raise ValueError("Invalid URL")
    else: return argument

# -----------------------------------------------------------------

def image_path(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    path = file_path(argument)

    if path.endswith("fits"): raise ValueError("Unrecognized file type")
    else: return path

# -----------------------------------------------------------------

def filter(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    return Filter.from_string(argument)

# -----------------------------------------------------------------

def pixelcoordinate(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    from ...magic.basics.coordinate import PixelCoordinate
    x, y = real_tuple(argument)
    return PixelCoordinate(x, y)

# -----------------------------------------------------------------

def skycoordinate(argument):

    """
    This function ...
    :param argument:
    :return:
    """

    from ...magic.basics.coordinate import SkyCoordinate
    ra, dec = quantity_tuple(argument)
    return SkyCoordinate(ra=ra, dec=dec)

# -----------------------------------------------------------------
