#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.region.line Contains the LineRegion class and subclasses.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from .region import Region, PixelRegion, SkyRegion, PhysicalRegion
from ..basics.coordinate import PixelCoordinate, SkyCoordinate, PhysicalCoordinate

# -----------------------------------------------------------------

class LineRegion(Region):

    """
    This class ...
    """

    def __init__(self, start, end, **kwargs):

        """
        The constructor ...
        :param start:
        :param end:
        :param kwargs:
        """

        # Set the attributes
        self.start = start
        self.end = end

        # Call the constructor of the base class
        super(LineRegion, self).__init__(**kwargs)

    # -----------------------------------------------------------------

    @property
    def axis1_center(self):

        """
        This property ...
        :return:
        """

        return 0.5*(self.start.axis1 + self.end.axis1)

    # -----------------------------------------------------------------

    @property
    def axis2_center(self):

        """
        This property ...
        :return:
        """

        return 0.5*(self.start.axis2 + self.end.axis2)

# -----------------------------------------------------------------

class PixelLineRegion(LineRegion, PixelRegion):

    """
    This class ...
    """

    def __init__(self, start, end, **kwargs):

        """
        The constructor ...
        :param start:
        :param end:
        :param kwargs:
        """

        # Check the arguments
        if not isinstance(start, PixelCoordinate): raise ValueError("Start must be a pixel coordinate")
        if not isinstance(end, PixelCoordinate): raise ValueError("End must be a pixel coordinate")

        # Call the constructor of the base class
        super(PixelLineRegion, self).__init__(start, end, **kwargs)

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return PixelCoordinate(self.axis1_center, self.axis2_center)

# -----------------------------------------------------------------

class SkyLineRegion(LineRegion, SkyRegion):

    """
    This class ...
    """

    def __init__(self, start, end, **kwargs):

        """
        The constructor ...
        :param start:
        :param end:
        :param kwargs:
        """

        # Check the arguments
        if not isinstance(start, SkyCoordinate): raise ValueError("Start must be a sky coordinate")
        if not isinstance(end, SkyCoordinate): raise ValueError("End must be a sky coordinate")

        # Call the constructor of the base class
        super(SkyLineRegion, self).__init__(start, end, **kwargs)

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return SkyCoordinate(self.axis1_center, self.axis2_center)

# -----------------------------------------------------------------

class PhysicalLineRegion(LineRegion, PhysicalRegion):

    """
    This class ...
    """

    def __init__(self, start, end, **kwargs):

        """
        The constructor ...
        :param start:
        :param end:
        :param kwargs:
        """

        # Check the arguments
        if not isinstance(start, PhysicalCoordinate): raise ValueError("Start must be a physical coordinate")
        if not isinstance(end, PhysicalCoordinate): raise ValueError("End must be a physical coordinate")

        # Call the constructor of the base class
        super(PhysicalLineRegion, self).__init__(start, end, **kwargs)

    # -----------------------------------------------------------------

    @property
    def center(self):

        """
        This function ...
        :return:
        """

        return PhysicalCoordinate(self.axis1_center, self.axis2_center)

# -----------------------------------------------------------------