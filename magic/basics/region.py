#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.basics.region Contains the Region class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import astronomical modules
import pyregion
from astropy import units as u
from astropy.coordinates import Angle

# Import the relevant AstroMagic classes and modules
from .vector import Position, Extent
from .geometry import Ellipse
from .skyregion import SkyRegion
from .skygeometry import SkyCoord, SkyLine, SkyCircle, SkyEllipse, SkyRectangle
from .mask import Mask

# -----------------------------------------------------------------

class Region(list):

    """
    This class ...
    """

    def __init__(self):

        """
        This function ...
        :return:
        """

        # Call the constructor of the base class
        super(Region, self).__init__()

    # -----------------------------------------------------------------

    @classmethod
    def from_file(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Create a new region
        region = cls()

        # Open the region file with pyregion and check if its in image coordinates
        _region = pyregion.open(path)
        if not _region.check_imagecoord(): raise ValueError("Region is not in image coordinates")

        for shape in _region:

            # Skip shapes that are not ellipses or circles
            if shape.name != "ellipse" and shape.name != "circle": continue

            x_center = shape.coord_list[0]
            y_center = shape.coord_list[1]
            x_radius = shape.coord_list[2]
            if shape.name == "ellipse":
                y_radius = shape.coord_list[3]
                try: angle = Angle(shape.coord_list[4], u.Unit("deg"))
                except: angle = Angle(0.0, u.Unit("deg"))
            elif shape.name == "circle":
                y_radius = shape.coord_list[2]
                angle = Angle(0.0, u.Unit("deg"))
            else: raise ValueError("Shapes other than ellipses or circles are not supported yet")

            center = Position(x_center, y_center)
            radius = Extent(x_radius, y_radius)

            # Only works for ellipses for now
            ellipse = Ellipse(center, radius, angle)

            # Add the ellipse to the region
            region.append(ellipse)

        # Return the new region
        return region

    # -----------------------------------------------------------------

    def append(self, shape):

        """
        This function ...
        :param shape:
        :return:
        """

        # Check whether the shape is in sky coordinates
        if not (shape.__class__.__name__ == "Position" or shape.__class__.__name__ == "Circle"
                or shape.__class__.__name__ == "Ellipse" or shape.__class__.__name__ == "Rectangle"):
            raise ValueError("Shape must of of type Position, Circle, Ellipse or Rectangle")

        # Otherwise, add the shape
        super(Region, self).append(shape)

    # -----------------------------------------------------------------

    def __mul__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        new_region = Region()
        for shape in self: new_region.append(shape * value)

        # Return the new region
        return new_region

    # -----------------------------------------------------------------

    def __truediv__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        return self.__div__(value)

    # -----------------------------------------------------------------

    def __div__(self, value):

        """
        This function ...
        :param value:
        :return:
        """

        new_region = Region()
        for shape in self: new_region.append(shape / value)

        # Return the new region
        return new_region

    # -----------------------------------------------------------------

    def to_sky_coordinates(self, wcs):

        """
        This function ...
        :param wcs:
        :return:
        """

        # Initialize a new list contain the shapes in sky coordinates
        new_region = SkyRegion()

        # Fill the new list
        for shape in self:

            if shape.__class__.__name__ == "Position": new_region.append(SkyCoord.from_pixel(shape.x, shape.y, wcs, mode="wcs"))
            elif shape.__class__.__name__ == "Line": new_region.append(SkyLine.from_line(shape, wcs))
            elif shape.__class__.__name__ == "Circle": new_region.append(SkyCircle.from_circle(shape, wcs))
            elif shape.__class__.__name__ == "Ellipse": new_region.append(SkyEllipse.from_ellipse(shape, wcs))
            elif shape.__class__.__name__ == "Rectangle": new_region.append(SkyRectangle.from_rectangle(shape, wcs))
            else: raise ValueError("Unrecognized shape")

        # Return the list of ellipses in image coordinates
        return new_region

    # -----------------------------------------------------------------

    def to_mask(self, wcs):

        """
        This function ...
        :param wcs:
        :return:
        """

        x_size = wcs.naxis1
        y_size = wcs.naxis2

        mask = Mask(np.zeros((y_size, x_size)))

        for shape in self:

            mask += Mask.from_ellipse(x_size, y_size, shape)

        # Return the mask
        return mask

    # -----------------------------------------------------------------

    def save(self, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Create a file
        f = open(path, 'w')

        # Initialize the region string
        print("# Region file format: DS9 version 4.1", file=f)

        # Loop over all ellipses
        for ellipse in self:

            # Get aperture properties
            center = ellipse.center
            major = ellipse.major
            minor = ellipse.minor
            angle = ellipse.angle.degree

            # Write to region file
            print("image;ellipse({},{},{},{},{})".format(center.x+1, center.y+1, major, minor, angle), file=f)

        # Close the file
        f.close()

# -----------------------------------------------------------------
