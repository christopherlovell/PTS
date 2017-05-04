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

# Import standard modules
from abc import ABCMeta

# Import the relevant PTS classes and modules
from ..tools import filesystem as fs
from .configuration import find_command

# -----------------------------------------------------------------

class Configurable(object):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    _command_name = None

    # -----------------------------------------------------------------

    @classmethod
    def command_name(cls):

        """
        This function ...
        :return:
        """

        if cls._command_name is not None: return cls._command_name

        # Find the corresponding command
        command_name, class_name, configuration_module_path, description = find_command(cls)

        # Set the command name
        cls._command_name = command_name

        # Return the command
        return command_name

    # -----------------------------------------------------------------

    def __init__(self, config=None, interactive=False, unlisted=False, cwd=None):

        """
        The constructor ...
        :param config:
        :param interactive:
        :param unlisted:
        """

        # Set configuration
        self.config = self.get_config(config, interactive=interactive, unlisted=unlisted, cwd=cwd)

        # Set the detached calculations flag
        self.detached = False

    # -----------------------------------------------------------------

    @classmethod
    def get_config(cls, config=None, interactive=False, unlisted=False, cwd=None):

        """
        This function ...
        :param config:
        :param interactive:
        :param unlisted:
        :return:
        """

        from .configuration import get_config_for_class

        # Get the config
        if unlisted:
            from .map import Map
            assert isinstance(config, Map)
            return config
        else: return get_config_for_class(cls, config, interactive=interactive, cwd=cwd)

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # nothing is (yet) required here
        pass

    # -----------------------------------------------------------------

    @property
    def class_name(self):

        """
        This function ...
        :return:
        """

        name = type(self).__name__
        return name

    # -----------------------------------------------------------------

    @property ## I THINK THIS FUNCTION CAN BE REMOVED (IT SHOULD) AND REPLACED BY CLASS_NAME
    def name(self):

        """
        This function ...
        :return:
        """

        name = type(self).__name__.lower()
        if "plotter" in name: return "plotter"
        else: return name

    # -----------------------------------------------------------------

    @property
    def input_path(self):

        """
        This function ...
        :return:
        """

        # If 'input' defined in the config
        if "input" in self.config:

            full_input_path = fs.absolute_or_in(self.config.input, self.config.path)
            if not fs.is_directory(full_input_path): raise ValueError("The input directory does not exist")
            return full_input_path

        # Else, use the working directory as input directory
        else: return self.config.path

    # -----------------------------------------------------------------

    def input_path_file(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return fs.join(self.input_path, name)

    # -----------------------------------------------------------------

    @property
    def output_path(self):

        """
        This function ...
        :return:
        """

        # If 'output' is defined in the config
        if "output" in self.config and self.config.output is not None:

            full_output_path = fs.absolute_or_in(self.config.output, self.config.path)
            if not fs.is_directory(full_output_path): fs.create_directory(full_output_path)
            return full_output_path

        # Else, use the working directory as output directory
        else: return self.config.path

    # -----------------------------------------------------------------

    def output_path_file(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return fs.join(self.output_path, name)

# -----------------------------------------------------------------

class HierarchicConfigurable(Configurable):

    """
    This class ...
    """

    def __init__(self, config):

        """
        The constructor ...
        :param config:
        """

        # Call the constructor of the base class
        super(HierarchicConfigurable, self).__init__(config)

        # The children
        self.children = dict()

    # -----------------------------------------------------------------

    def __getattr__(self, attr):

        """
        This function ...
        Overriding __getattr__ should be fine (will not break the default behaviour) -- __getattr__ is only called
        as a last resort i.e. if there are no attributes in the instance that match the name.
        :param attr:
        :return:
        """

        if attr.startswith("__") and attr.endswith("__"): raise AttributeError("Can't delegate this attribute")
        return self.children[attr]

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Delete its children
        self.children = dict()

    # -----------------------------------------------------------------

    def add_child(self, name, type, config=None):

        """
        This function ...
        :param name:
        :param type:
        :param config:
        :return:
        """

        if name in self.children: raise ValueError("Child with this name already exists")

        # new ...
        if config is None: config = {}
        config["output_path"] = self.config.output_path
        config["input_path"] = self.config.input_path

        self.children[name] = type(config)

    # -----------------------------------------------------------------

    def setup_before(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def setup_after(self):

        """
        This function ...
        :return:
        """

        pass

# -----------------------------------------------------------------
