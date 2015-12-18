#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.configurable Contains the Configurable class, a class for representing classes that can be
#  configured with a configuration file.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ..tools import configuration, logging

# -----------------------------------------------------------------

class Configurable(object):

    """
    This class ...
    """

    def __init__(self, config, subpackage):

        """
        The constructor ...
        :param config:
        :param subpackage:
        :return:
        """

        # Set the configuration object
        self.config = configuration.set(subpackage, self.name, config)
        
        # Set the logger to None initially
        self.log = None

    # -----------------------------------------------------------------

    def setup(self):
        
        """
        This function ...
        """
    
        # Create the logger
        self.log = logging.new_log(self.name, self.config.logging.level)
        if self.config.logging.path is not None: logging.link_file_log(self.log, self.config.logging.path, self.config.logging.level)

    # -----------------------------------------------------------------

    @property
    def name(self):

        """
        This function ...
        :return:
        """

        name = type(self).__name__.lower()
        if "plotter" in name: return "plotter"
        else: return name

# -----------------------------------------------------------------
