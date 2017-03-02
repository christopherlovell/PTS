#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.basics.models Contains the SersicModel, ExponentialDiskModel and DeprojectionModel classes.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import math
from abc import ABCMeta

# Import astronomical modules
from astropy.coordinates import Angle
from astropy.modeling.models import Sersic2D
from astropy.units import dimensionless_angles

# Import the relevant PTS classes and modules
from ...core.basics.composite import SimplePropertyComposite
from ...core.basics.unit import parse_unit as u

# -----------------------------------------------------------------

class Model(SimplePropertyComposite):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

# -----------------------------------------------------------------
#
# 3D MODELS
#
# -----------------------------------------------------------------

def load_3d_model(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Get the first line of the file
    with open(path, 'r') as f: first_line = f.readline()

    # Create the appropriate model
    if "SersicModel3D" in first_line: return SersicModel3D.from_file(path)
    elif "ExponentialDiskModel3D" in first_line: return ExponentialDiskModel3D.from_file(path)
    elif "DeprojectionModel3D" in first_line: return DeprojectionModel3D.from_file(path)
    else: raise ValueError("Unrecognized model file")

# -----------------------------------------------------------------

class SersicModel3D(Model):

    """
    This function ...
    """

    def __init__(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(SersicModel3D, self).__init__()

        # Define properties
        self.add_property("effective_radius", "quantity", "effective radius")
        self.add_property("index", "integer", "sersic index")
        self.add_property("y_flattening", "real", "flattening along y direction", 1.)
        self.add_property("z_flattening", "real", "flattening along z direction", 1.)
        self.add_property("azimuth", "angle", "azimuth angle", Angle(0.0, "deg"))
        self.add_property("tilt", "angle", "tilt angle", Angle(0.0, "deg"))

        # Set properties
        self.set_properties(kwargs)

    # -----------------------------------------------------------------

    @classmethod
    def from_2d(cls, sersic2d, inclination, position_angle, azimuth_or_tilt="azimuth"):

        """
        :param sersic2d:
        :param inclination:
        :param position_angle:
        :param azimuth_or_tilt:
        :return:
        """

        # Get effective radius and Sersic index
        effective_radius = sersic2d.effective_radius
        index = sersic2d.index

        # Tilt angle and z flattening
        if azimuth_or_tilt == "tilt":

            # Calculate the intrinsic flattening
            y_flattening = 1.
            z_flattening = intrinsic_z_flattening(sersic2d.axial_ratio, inclination)

            # Set azimuth
            azimuth = 0. * u("deg")

            # Calculate the tilt angle of the bulge (tilt w.r.t. the x-axis)
            tilt = deproject_pa_to_tilt(sersic2d.position_angle - position_angle, inclination)
            tilt = Angle(90., "deg") - tilt

        # Azimuth angle and y flattening
        elif azimuth_or_tilt == "azimuth":

            # TODO: this is not working right and therefore unusable for the moment

            # Calculate the intrinsic flattening
            y_flattening = intrinsic_z_flattening(sersic2d.axial_ratio, inclination)
            #z_flattening = intrinsic_z_flattening(sersic2d.axial_ratio, inclination)
            z_flattening = 1.

            # Calculate the azimuth angle of the bulge
            azimuth = deproject_pa_to_azimuth(sersic2d.position_angle - position_angle, inclination)

            # Set tilt
            #tilt = Angle(90., "deg")
            tilt = Angle(0., "deg")

        # Other input
        else: raise ValueError("Incorrect value for 'azimuth_or_tilt'")

        # Create a new Sersic model and return it
        return cls(effective_radius=effective_radius, index=index, y_flattening=y_flattening, z_flattening=z_flattening,
                   azimuth=azimuth, tilt=tilt)

# -----------------------------------------------------------------

class ExponentialDiskModel3D(Model):

    """
    This function ...
    """

    def __init__(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(ExponentialDiskModel3D, self).__init__()

        # Define properties
        self.add_property("radial_scale", "quantity", "radial scale")
        self.add_property("axial_scale", "quantity", "axial scale")
        self.add_property("radial_truncation", "real", "radial truncation", 0)
        self.add_property("axial_truncation", "real", "axial truncation", 0)
        self.add_property("inner_radius", "real", "inner radius", 0)
        self.add_property("tilt", "angle", "tilt", Angle(0.0, "deg"))

        # Set properties
        self.set_properties(kwargs)

    # -----------------------------------------------------------------

    @classmethod
    def from_2d(cls, exponentialdiskmodel2d, inclination, position_angle):

        """
        This function ...
        :param exponentialdiskmodel2d:
        :param inclination:
        :param position_angle:
        :return:
        """

        # Get the radial scale
        radial_scale = exponentialdiskmodel2d.scalelength

        # Calculate the intrinsic flattening
        flattening = intrinsic_z_flattening(exponentialdiskmodel2d.axial_ratio, inclination)

        # Calculate the axial scale
        axial_scale = flattening * radial_scale

        # Calculate the tilt angle of the disk (tilt w.r.t. the x-axis)
        #tilt = deproject_pa_to_tilt(parameters.PA - position_angle, inclination)
        tilt = deproject_pa_to_tilt(position_angle - exponentialdiskmodel2d.position_angle, inclination)
        tilt = Angle(90., "deg") - tilt

        # Create a new exponential disk model and return it
        return cls(radial_scale=radial_scale, axial_scale=axial_scale, tilt=tilt)

# -----------------------------------------------------------------

class DeprojectionModel3D(Model):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(DeprojectionModel3D, self).__init__()

        # position angle: -360 deg to 360 deg
        # inclination: 0 deg to 90 deg
        # center in pixel coordinates!

        # Define the properties
        self.add_property("filename", "string", "name of the input FITS file")
        self.add_property("pixelscale", "quantity", "pixelscale of the FITS image")
        self.add_property("position_angle", "angle", "position angle")
        self.add_property("inclination", "angle", "inclination")
        self.add_property("x_size", "positive_integer", "number of x pixels")
        self.add_property("y_size", "positive_integer", "number of y pixels")
        self.add_property("x_center", "real", "x center in image coordinates")
        self.add_property("y_center", "real", "y center in image coordinates")
        self.add_property("scale_height", "quantity", "scale height")

        # Set the properties
        self.set_properties(kwargs)

    # -----------------------------------------------------------------

    @classmethod
    def from_wcs(cls, wcs, galaxy_center, distance, pa, inclination, filepath, scale_height):

        """
        This function ...
        :param wcs:
        :param galaxy_center:
        :param distance:
        :param pa:
        :param inclination:
        :param filepath
        :param scale_height:
        :return:
        """

        # Get the center pixel
        pixel_center = galaxy_center.to_pixel(wcs)
        xc = pixel_center.x
        yc = pixel_center.y

        # Get the pixelscale in physical units
        pixelscale_angular = wcs.average_pixelscale.to("deg")  # in deg
        pixelscale = (pixelscale_angular * distance).to("pc", equivalencies=dimensionless_angles())

        # Get the number of x and y pixels
        x_size = wcs.xsize
        y_size = wcs.ysize

        # Create the deprojection model
        deprojection = cls(filepath, pixelscale, pa, inclination, x_size, y_size, xc, yc, scale_height)

        # Return the deprojection model
        return deprojection

# -----------------------------------------------------------------

def intrinsic_z_flattening(qprime, inclination):

    """
    This function ...
    :param qprime:
    :param inclination:
    """

    # Get the inclination angle in radians
    i = inclination.to("radian").value

    # Calculate the intrinsic flattening
    q = math.sqrt((qprime**2 - math.cos(i)**2)/math.sin(i)**2)

    # Return the intrinsic flattening
    return q

# -----------------------------------------------------------------

def intrinsic_y_flattening(qprime, inclination):

    """
    This function ...
    :param qprime:
    :param inclination:
    :return:
    """

    # Get the inclination angle in radians
    i = inclination.to("radian").value

    # Calculate the 'inclination' w.r.t. the y axis
    #i_wrt_y = 0.5 * math.pi - i

    print(inclination)
    print(qprime)
    print(i_wrt_y)
    print(math.cos(i_wrt_y))
    print(math.sin(i_wrt_y))

    #qprime =

    # Calculate the intrinsic flattening
    q = math.sqrt((qprime ** 2 - math.cos(i_wrt_y) ** 2) / math.sin(i_wrt_y) ** 2)

    # Return the intrinsic flattening
    return q

# -----------------------------------------------------------------

def project_azimuth_to_pa(azimuth, inclination):

    """
    This function ...
    :param azimuth:
    :param inclination:
    """

    # Get the azimuth angle and inclination in radians
    azimuth_radian = azimuth.to("radian").value
    i_radian = inclination.to("radian").value

    denominator = math.sqrt(math.cos(azimuth_radian)**2 * math.cos(i_radian)**2 + math.sin(azimuth_radian)**2)

    cos_pa = math.cos(azimuth_radian) * math.cos(i_radian) / denominator
    sin_pa = math.sin(azimuth_radian) / denominator

    pa_radian = math.atan2(sin_pa, cos_pa) * u("radian")

    return pa_radian.to("deg")

# -----------------------------------------------------------------

def deproject_pa_to_azimuth(pa, inclination):

    """
    This function ...
    :param pa:
    :param inclination:
    :return:
    """

    # Get the PA and inclination in radians
    pa_radian = pa.to("radian").value
    i_radian = inclination.to("radian").value

    denominator = math.sqrt(math.cos(pa_radian)**2 + math.sin(pa_radian)**2 * math.cos(i_radian)**2)

    cos_azimuth = math.cos(pa_radian) / denominator
    sin_azimuth = math.sin(pa_radian) * math.cos(i_radian) / denominator

    azimuth_radian = math.atan2(sin_azimuth, cos_azimuth) * u("radian")

    return azimuth_radian.to("deg")

# -----------------------------------------------------------------

def project_tilt_to_pa(tilt, inclination):

    """
    This function ...
    :param tilt:
    :param inclination:
    :return:
    """

    # Get the tilt angle and inclination in radians
    tilt_radian = tilt.to("radian").value
    i_radian = inclination.to("radian").value

    denominator = math.sqrt(math.sin(tilt_radian)**2 * math.sin(i_radian)**2 + math.cos(tilt_radian)**2)

    cos_pa = math.sin(tilt_radian) * math.sin(i_radian) / denominator
    sin_pa = math.cos(tilt_radian) / denominator

    pa_radian = math.atan2(sin_pa, cos_pa) * u("radian")

    return pa_radian.to("deg")

# -----------------------------------------------------------------

def deproject_pa_to_tilt(pa, inclination):

    """
    This function ...
    :param pa:
    :param inclination:
    :return:
    """

    # Get the PA and inclination in radians
    pa_radian = pa.to("radian").value
    i_radian = inclination.to("radian").value

    denominator = math.sqrt(math.sin(pa_radian)**2 * math.sin(i_radian)**2 + math.cos(pa_radian)**2)

    cos_tilt = math.sin(pa_radian) * math.sin(i_radian) / denominator
    sin_tilt = math.cos(pa_radian) / denominator

    tilt_radian = math.atan2(sin_tilt, cos_tilt) * u("radian")

    return tilt_radian.to("deg")

# -----------------------------------------------------------------

# Test the deprojection functions:

#test_angles = []
#test_angles.append(Angle(33, "deg"))
#test_angles.append(Angle(45, "deg"))
#test_angles.append(Angle(0, "deg"))
#test_angles.append(Angle(90, "deg"))
#test_angles.append(Angle(189, "deg"))

#for test_angle in test_angles:

#    result = deproject_pa_to_tilt(test_angle, Angle(0.0, "deg"))
#    print("Should fail/be zero:", Angle(90., "deg") - result, test_angle)

#    result = deproject_pa_to_tilt(test_angle, Angle(90., "deg"))
#    print("Should be the same:", Angle(90., "deg") - result, test_angle)

    #result = project_tilt_to_pa(test_angle, Angle(0.0, "deg"))
    #print("Should fail/be zero:", Angle(90., "deg") - result, test_angle)

    #result = project_tilt_to_pa(test_angle, Angle(90., "deg"))
    #print("Should be the same:", Angle(90., "deg") - result, test_angle)

# -----------------------------------------------------------------
#
# 2D MODELS
#
# -----------------------------------------------------------------

def load_2d_model(path):

    """
    This function ...
    :param path:
    :return:
    """

    # Get the first line of the file
    with open(path, 'r') as f: first_line = f.readline()

    # Create the appropriate model
    if "SersicModel2D" in first_line: return SersicModel2D.from_file(path)
    elif "ExponentialDiskModel2D" in first_line: return ExponentialDiskModel2D.from_file(path)
    else: raise ValueError("Unrecognized model file")

# -----------------------------------------------------------------

class SersicModel2D(Model):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        The constructor ...
        :param kwargs:
        """

        # Call the constructor of the base class
        super(SersicModel2D, self).__init__()

        # Define properties
        self.add_property("rel_contribution", "real", "relative contribution")
        self.add_property("fluxdensity", "quantity", "flux density")
        self.add_property("axial_ratio", "real", "axial ratio")
        self.add_property("position_angle", "angle", "position angle") # (degrees ccw from North)
        self.add_property("effective_radius", "quantity", "effective radius")
        self.add_property("index", "integer", "sersic index")

        # Set properties
        self.set_properties(kwargs)

# -----------------------------------------------------------------

class ExponentialDiskModel2D(Model):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        The constructor ...
        """

        # Call the constructor of the base class
        super(ExponentialDiskModel2D, self).__init__()

        # Define properties
        self.add_property("rel_contribution", "real", "relative contribution")
        self.add_property("fluxdensity", "quantity", "flux density")
        self.add_property("axial_ratio", "real", "axial ratio")
        self.add_property("position_angle", "angle", "position_angle") # (degrees ccw from North)
        self.add_property("mu0", "quantity", "surface brightness at center")
        self.add_property("scalelength", "quantity", "scale length")

        # Set properties
        self.set_properties(kwargs)

# -----------------------------------------------------------------
