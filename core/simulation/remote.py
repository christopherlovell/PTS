#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

"""
This module can be used to launch SKIRT/FitSKIRT simulations remotely
"""

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import pxssh

# Import the relevant PTS classes and modules
from pts.core.basics import Configurable

# -----------------------------------------------------------------

class SkirtRemote(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(SkirtRemote, self).__init__(config, "skirtremote")

        ## Attributes

        # Create the SSH interface
        self.ssh = pxssh.pxssh()

    # -----------------------------------------------------------------

    def login(self):

        """
        This function ...
        :return:
        """

        # Connect to the remote host
        self.ssh.login(self.config.host, self.config.user, self.config.password)

    # -----------------------------------------------------------------

    def submit(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def status(self):

        """
        This function ..
        :return:
        """

        pass

# -----------------------------------------------------------------