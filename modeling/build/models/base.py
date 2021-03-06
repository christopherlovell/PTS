#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.build.models.base Contains the ModelBuilderBase class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ..component import BuildComponent
from ....core.tools import filesystem as fs

# -----------------------------------------------------------------

class ModelBuilderBase(BuildComponent):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(ModelBuilderBase, self).__init__(*args, **kwargs)

        # The path for this model
        self.model_path = None

        # The path for the stellar components
        self.model_stellar_path = None

        # The path for the dust components
        self.model_dust_path = None

    # -----------------------------------------------------------------

    @property
    def model_name(self):

        """
        This function ...
        :return:
        """

        return self.config.name

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(ModelBuilderBase, self).setup(**kwargs)

        # Set the model path and create it
        self.model_path = fs.join(self.models_path, self.model_name)

        # Check whether there is not yet a directory for this model
        if fs.is_directory(self.model_path):
            if fs.is_empty(self.model_path, recursive=True): fs.clear_directory(self.model_path)
            elif self.config.overwrite: fs.clear_directory(self.model_path)
            else: raise IOError("A directory for a model called '" + self.model_name + "' already exists")
        else: fs.create_directory(self.model_path)

        # Set the path of the directory for the stellar components
        self.model_stellar_path = fs.create_directory_in(self.model_path, "stellar")

        # Set the path of the directory for the dust components
        self.model_dust_path = fs.create_directory_in(self.model_path, "dust")

# -----------------------------------------------------------------
