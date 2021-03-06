#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.maps.html.ionizing Contains the IonizingMapsPageGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ....core.tools import filesystem as fs
from .all import ionizing_name
from .component import ComponentMapsPageGenerator

# -----------------------------------------------------------------

class IonizingMapsPageGenerator(ComponentMapsPageGenerator):

    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param interactive:
        :return:
        """

        # Call the constructor of the base class
        super(IonizingMapsPageGenerator, self).__init__(*args, **kwargs)

    # -----------------------------------------------------------------

    @property
    def map_names(self):

        """
        Thisf unction ...
        :return:
        """

        return self.ionizing_map_names

    # -----------------------------------------------------------------

    @property
    def map_paths(self):

        """
        This function ...
        :return:
        """

        return self.ionizing_map_paths

    # -----------------------------------------------------------------

    @property
    def component_plots_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.plots_path, ionizing_name)

    # -----------------------------------------------------------------

    @property
    def component_map_methods(self):

        """
        This function ...
        :return:
        """

        return self.ionizing_map_methods

    # -----------------------------------------------------------------

    @property
    def component_map_origins(self):

        """
        This function ...
        :return:
        """

        return self.ionizing_map_origins

    # -----------------------------------------------------------------

    @property
    def title(self):

        """
        This function ...
        :return:
        """

        return "Ionizing stellar maps"

    # -----------------------------------------------------------------

    @property
    def sub_name(self):

        """
        This function ...
        :return:
        """

        return ionizing_name

    # -----------------------------------------------------------------

    @property
    def page_path(self):

        """
        This function ...
        :return:
        """

        return self.ionizing_maps_html_page_path

# -----------------------------------------------------------------
