#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.units.unit Contains the PhotometricUnit class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math
import copy
import warnings
import traceback

# Import astronomical modules
from astropy.units import Unit, UnitBase, CompositeUnit, spectral, Quantity
from astropy import constants

# Import the relevant PTS classes and modules
from ...magic.basics.pixelscale import Pixelscale
from .quantity import PhotometricQuantity
from .utils import analyse_unit, divide_units_reverse, clean_unit_string, get_physical_type, interpret_physical_type
from .parsing import parse_unit, parse_quantity
from ..tools import types
from ..basics.log import log

# -----------------------------------------------------------------

# Symbols
lambda_symbol = "λ"
nu_symbol = "ν"

# -----------------------------------------------------------------

# LUMINOSITY: W
# WAVELENGTH LUMINOSITY DENSITY: W/micron
# FREQUENCY LUMINOSITY DENSITY: W/Hz
# NEUTRAL LUMINOSITY DENSITY: W

# FLUX: W/m2
# WAVELENGTH FLUX DENSITY: W/m2/micron
# FREQUENCY FLUX DENSITY: W/m2/Hz
# NEUTRAL FLUX DENSITY: W/m2

# INTENSITY: W/sr
# WAVELENGTH INTENSITY DENSITY: W/sr/micron
# FREQUENCY INTENSITY DENSITY: W/sr/Hz
# NEUTRAL INTENSITY DENSITY: W/sr

# SURFACE BRIGHTNESS: W/m2/sr
# WAVELENGTH SURFACE BRIGHTNESS DENSITY: W/m2/sr/micron
# FREQUENCY SURFACE BRIGHTNESS DENSITY: W/m2/sr/Hz
# NEUTRAL SURFACE BRIGHTNESS DENSITY: W/m2/sr

# INTRINSIC SURFACE BRIGHTNESS: W / kpc2
# WAVELENGTH INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2 / micron
# FREQUENCY INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2 / Hz
# NEUTRAL INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2

# AND::: SAME NAME ??

# INTRINSIC SURFACE BRIGHTNESS: W / kpc2 / m2
# WAVELENGTH INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2 / m2 / micron
# FREQUENCY INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2 / m2 /hz
# NEUTRAL INTRINSIC SURFACE BRIGHTNESS DENSITY: W / kpc2 / m2

# -----------------------------------------------------------------

# SKIRT:
# 'W/m': 'wavelengthluminositydensity',
#'W/micron': 'wavelengthluminositydensity',
#'Lsun/micron': 'wavelengthluminositydensity',
#'W/Hz': 'frequencyluminositydensity',
#'erg/s/Hz': 'frequencyluminositydensity',
#'Lsun/Hz': 'frequencyluminositydensity',
#'W/m2': 'neutralfluxdensity',
#'W/m2/sr': 'neutralsurfacebrightness',
#'W/m2/arcsec2': 'neutralsurfacebrightness',
#'W/m3': 'wavelengthfluxdensity',
#'W/m2/micron': 'wavelengthfluxdensity',
#'W/m3/sr': 'wavelengthsurfacebrightness',
#'W/m2/micron/sr': 'wavelengthsurfacebrightness',
#'W/m2/micron/arcsec2': 'wavelengthsurfacebrightness',
#'W/m2/Hz': 'frequencyfluxdensity',
#'Jy': 'frequencyfluxdensity',
#'mJy': 'frequencyfluxdensity',
#'MJy': 'frequencyfluxdensity',
#'erg/s/cm2/Hz': 'frequencyfluxdensity',
#'W/m2/Hz/sr': 'frequencysurfacebrightness',
#'W/m2/Hz/arcsec2': 'frequencysurfacebrightness',
#'Jy/sr': 'frequencysurfacebrightness',
#'Jy/arcsec2': 'frequencysurfacebrightness',
#'MJy/sr': 'frequencysurfacebrightness',
#'MJy/arcsec2': 'frequencysurfacebrightness'

# -----------------------------------------------------------------

speed_of_light = constants.c
#solar_luminosity = 3.846e26 * parse_unit("W")

# -----------------------------------------------------------------

wavelength_times_frequency = speed_of_light

# -----------------------------------------------------------------

class PhotometricUnit(CompositeUnit):

    """
    This function ...
    """

    __slots__ = [] # make the class objects immutable

    # -----------------------------------------------------------------

    def __init__(self, unit, density=False, density_strict=False, brightness=False, brightness_strict=False):

        """
        The constructor ...
        :param unit:
        :param density:
        :param brightness:
        :param density_strict: if strict is True, density=True or density=False is interepreted as a strong necessity:
        an error will be thrown if this class thinks the passed flag is not correctly representing the quantity.
        If strict=False, this means that the density and brightness flag will be used as a guideline, in other words,
        the unit will be a 'density' or 'brightness' according to the flag WHEN IN DOUBT.
        :param brightness_strict: similar to density_strict
        """

        # Unit attributes
        self._base_unit = Unit("")
        self._wavelength_unit = Unit("")
        self._frequency_unit = Unit("")
        self._distance_unit = Unit("")
        self._extent_unit = Unit("")
        self._solid_angle_unit = Unit("")

        # Already a photometric unit
        if isinstance(unit, PhotometricUnit):

            # Set flags
            self.density = unit.density
            self.brightness = unit.brightness

            # Check density and brightness flag with what was passed
            if density_strict:
                if self.density and not density: raise ValueError("Unit passed was spectral density but density=False and density_strict=True")
                if not self.density and density: raise ValueError("Unit passed was not spectral density but density")
            else:
                if not self.density and density: log.warning("density flag has been enabled, but photometric unit passed has density = False")
            if brightness_strict:
                if self.brightness and not brightness: raise ValueError("Unit passed was brightness but brightness=False and brightness_strict=True")
                if not self.brightness and brightness: raise ValueError("Unit passed was not brightness but brightness=True and brightness_strict=True")
            else:
                if not self.brightness and brightness: log.warning("brightness flag has been enabled, but photometric unit passed has brightness = False")

            self.scale_factor = unit.scale_factor
            self.base_unit = unit.base_unit
            self.wavelength_unit = unit.wavelength_unit
            self.frequency_unit = unit.frequency_unit
            self.distance_unit = unit.distance_unit
            self.extent_unit = unit.extent_unit
            self.solid_angle_unit = unit.solid_angle_unit

        # Regular unit
        else:

            # Clean unit string
            if types.is_string_type(unit):
                physical_type = get_physical_type(unit)
                unit = clean_unit_string(unit)
            else: physical_type = None

            # Check whether physical type string is compatible with function arguments
            if physical_type is not None:
                found_density, found_brightness = interpret_physical_type(physical_type)
                if density_strict:
                    if found_density and not density: raise ValueError("Unit string passed indicated a spectral density but density=False and density_strict=True")
                    if not found_density and density: raise ValueError("Unit string passed indicated not a spectral density but density=True and density_strict=True")
                if brightness_strict:
                    if found_brightness and not brightness: raise ValueError("Unit string passed indicated a surface brightness but brightness=False and brightness_strict=True")
                    if not found_brightness and brightness: raise ValueError("Unit string passed indicated not a surface brightness but brightness=True and brightness_strict=True")
                # WE ARE SURE, AND CHECKS PASSED, SO ...
                density = found_density
                brightness = found_brightness
                density_strict = True
                brightness_strict = True

            # Parse the unit
            try: unit = Unit(unit)
            except ValueError as e:
                #traceback.print_exc()
                #print(str(e))
                raise ValueError("Unit is not recognized")
            #unit = Unit(unit)

            # Remove 'per pixel' from the unit
            #if "pix" in str(unit): unit *= "pix"
            if "pix" in unit.bases: unit *= "pix"

            # Set whether it represents a density
            self.density = density

            # Analyse the unit
            self.scale_factor, self.base_unit, self.wavelength_unit, self.frequency_unit, length_unit, self.solid_angle_unit, cannot_be_intrinsic_brightness, intrinsic_scale_unit = analyse_unit(unit)

            # If the wavelength unit is not None or the frequency unit is not None, we have a spectral density
            if self.wavelength_unit is not None and self.wavelength_unit != "":
                if density_strict and not self.density: raise ValueError("The passed unit string does not correspond to a spectral density")
                self.density = True
            if self.frequency_unit is not None and self.frequency_unit != "":
                if density_strict and not self.density: raise ValueError("The passed unit string does not correspond to a spectral density")
                self.density = True

            #print(self.base_unit, cannot_be_intrinsic_brightness)

            # Set the distance or intrinsic scale (extent) unit
            if self.solid_angle_unit != "":

                # if there is a solid angle unit, we can never have an intrinsic surface
                # brightness, which is only power/area. That's why we make the distinction here.

                # CHECK
                if intrinsic_scale_unit is not None: raise ValueError("Cannot have a solid angle unit and also an intrinsic scale unit")

                # Check whether we have an angular surface brightness
                if length_unit != "":

                    # Check if brightness flag is OK
                    if not brightness and brightness_strict: raise ValueError("The passed unit corresponds to a surface brightness")

                    # Set the distance unit
                    self.distance_unit = length_unit

                    # Set the extent unit
                    self.extent_unit = ""

                    # Set the brightness flag
                    self.brightness = True

                # No length unit, we have an intensity
                else:

                    # Check if brightness flag is OK
                    if brightness and brightness_strict: raise ValueError("The passed unit string does not correspond to a surface brightness")

                    # Set the distance and extent units to nothing
                    self.distance_unit = ""
                    self.extent_unit = ""

                    # Set the brightness flag
                    self.brightness = False

            # No solid angle unit, intrinsic surface brightness is possible
            else:

                # No length unit, we have an energy, count rate or (spectral) luminosity (NO NOT ALWAYS)
                if length_unit == "":

                    # SOMETHING
                    if intrinsic_scale_unit is not None:

                        self.distance_unit = ""
                        self.extent_unit = intrinsic_scale_unit

                        self.brightness = True

                    # SOMETHING
                    else:

                        # Check if the brightness flag is OK
                        if brightness and brightness_strict: raise ValueError("The passed unit string does not correspond to a surface brightness")

                        # Set the distance and extent units to nohting
                        self.distance_unit = ""
                        self.extent_unit = ""

                        # Set the brightness flag
                        self.brightness = False

                # There is a length unit, we have either flux or intrinsic surface brightness
                else:

                    # Whether we have flux or instrinsic surface brigthness is completely dependent on the brigthness flag

                    # Check whether we can say that the unit cannot be an intrinsic surface brightness due to its original string specification (e.g. Jansky)
                    if cannot_be_intrinsic_brightness:
                        if brightness and brightness_strict: raise ValueError("The passed unit cannot be a surface brightness")
                        if intrinsic_scale_unit is not None: raise ValueError("Cannot have an intrinsic scale unit")
                        brightness = False

                    # INTRINSIC SURFACE BRIGHTNESS (NO NOT ALWAYS)
                    if brightness:

                        # INTRINSIC SURFACE BRIGHTNESS
                        if intrinsic_scale_unit is not None:

                            self.distance_unit = length_unit
                            self.extent_unit = intrinsic_scale_unit

                        # INTRINSIC SURFACE BRIGHTNESS
                        else:

                            self.distance_unit = ""
                            self.extent_unit = length_unit

                        # Set the brightness flag
                        self.brightness = True

                    # FLUX  (NO NOT ALWAYS)
                    else:

                        # INTRINSIC SURFACE BRIGHTNESS
                        if intrinsic_scale_unit is not None:

                            self.distance_unit = length_unit
                            self.extent_unit = intrinsic_scale_unit

                            # Set brightness flag
                            self.brightness = True

                        # FLUX
                        else:

                            self.distance_unit = length_unit
                            self.extent_unit = ""

                            # Set the brightness flag
                            self.brightness = False

            # Last checks to be sure
            if density and density_strict and not self.is_spectral_density: raise ValueError("The passed unit string does not correspond to a spectral density")
            if not density and density_strict and self.is_spectral_density: raise ValueError("The passed unit string corresponds to a spectral density")
            if brightness and brightness_strict and not self.is_brightness: raise ValueError("The passed unit string does not correspond to a brightness")
            if not brightness and brightness_strict and self.is_brightness: raise ValueError("The passed unit string corresponds to a brightness")

        # Call the constructor of the base class
        super(PhotometricUnit, self).__init__(unit.scale, unit.bases, unit.powers)

    # -----------------------------------------------------------------

    @property
    def base_unit(self):

        """
        This property ...
        :return: 
        """

        return self._base_unit

    # -----------------------------------------------------------------

    @base_unit.setter
    def base_unit(self, unit):

        """
        This function ...
        :return: 
        """

        if types.is_string_type(unit): unit = Unit(unit)
        self._base_unit = unit

    # -----------------------------------------------------------------

    @property
    def wavelength_unit(self):

        """
        This function ...
        :return: 
        """

        return self._wavelength_unit

    # -----------------------------------------------------------------

    @wavelength_unit.setter
    def wavelength_unit(self, unit):

        """
        This function ...
        :return: 
        """

        if types.is_string_type(unit): unit = Unit(unit)
        self._wavelength_unit = unit

    # -----------------------------------------------------------------

    @property
    def frequency_unit(self):

        """
        This function ...
        :return: 
        """

        return self._frequency_unit

    # -----------------------------------------------------------------

    @frequency_unit.setter
    def frequency_unit(self, unit):

        """
        This function ...
        :return: 
        """

        if types.is_string_type(unit): unit = Unit(unit)
        self._frequency_unit = unit

    # -----------------------------------------------------------------

    @property
    def distance_unit(self):

        """
        This function ...
        :return: 
        """

        return self._distance_unit

    # -----------------------------------------------------------------

    @distance_unit.setter
    def distance_unit(self, unit):

        """
        This funciton ...
        :param unit: 
        :return: 
        """

        if types.is_string_type(unit): unit = Unit(unit)
        self._distance_unit = unit

    # -----------------------------------------------------------------

    @property
    def extent_unit(self):
        
        """
        This property ...
        :return: 
        """

        return self._extent_unit

    # -----------------------------------------------------------------

    @extent_unit.setter
    def extent_unit(self, unit):

        """
        This function ...
        :param unit: 
        :return: 
        """

        if types.is_string_type(unit): unit = Unit(unit)
        self._extent_unit = unit

    # -----------------------------------------------------------------

    @property
    def solid_angle_unit(self):

        """
        This function ...
        :return: 
        """

        return self._solid_angle_unit

    # -----------------------------------------------------------------

    @solid_angle_unit.setter
    def solid_angle_unit(self, unit):
        
        """
        This function ...
        :param unit: 
        :return: 
        """
        
        if types.is_string_type(unit): unit = Unit(unit)
        self._solid_angle_unit = unit

    # -----------------------------------------------------------------

    def copy(self):

        """
        This function ...
        :return:
        """

        return copy.deepcopy(self)

    # -----------------------------------------------------------------

    def __pow__(self, p):

        """
        This function ...
        :param p:
        :return:
        """

        # If the power is one, return a copy of this photometric unit
        if p == 1: return self.copy()

        # Not a photometric unit anymore
        else: return CompositeUnit(1, [self], [p])

    # -----------------------------------------------------------------

    def __div__(self, other):

        """
        This function ...
        :param m:
        :return:
        """

        # If other is a string
        if types.is_string_type(other): other = parse_unit(other)

        # Divided by another unit
        if isinstance(other, UnitBase): return divide_units(self, other)

        # Divided by a quantity
        elif hasattr(other, "unit"):

            # Get the new unit
            new_unit = divide_units(self, other.unit)

            # Create a quantity
            self_value = 1.
            quantity = parse_quantity(self_value / other.value * new_unit)

            # Return the quantity
            return quantity

        # Divided by a number
        else: return PhotometricQuantity(1./other, self)

    # -----------------------------------------------------------------

    def __rdiv__(self, other):

        """
        This function ...
        :param m:
        :return:
        """

        # If the other is a string
        if types.is_string_type(other): other = parse_unit(other)

        # Another unit divided by this unit
        if isinstance(other, UnitBase): return divide_units_reverse(self, other)

        # Quantity divided by this unit
        elif hasattr(other, "unit"):

            # Get the new unit
            new_unit = divide_units_reverse(self, other)

            # Create a quantity
            self_value = 1.
            quantity = parse_quantity(other.value / self_value * new_unit)

            # Return the quantity
            return quantity

        # Regular number divided by this unit
        else: return parse_quantity(Quantity(other, 1./self))

    # -----------------------------------------------------------------

    __truediv__ = __div__

    # -----------------------------------------------------------------

    __rtruediv__ = __rdiv__

    # -----------------------------------------------------------------

    def __mul__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        # If the other is a string
        if types.is_string_type(other): other = parse_unit(other)

        # This unit is multiplied with another unit
        if isinstance(other, UnitBase): return multiply_units(self, other)

        # This unit is multiplied with a quantity
        elif hasattr(other, "unit"):

            # Get the new unit
            new_unit = multiply_units(self, other.unit)

            # Create a quantity
            quantity = parse_quantity(other.value * new_unit)

            # Return the quantity
            return quantity

        # Regular number multiplied by this unit
        else: return PhotometricQuantity(other, self)

    # -----------------------------------------------------------------

    __rmul__ = __mul__

    # -----------------------------------------------------------------

    def __eq__(self, other):

        """
        This function ...
        :param other:
        :return:
        """

        # Try to parse as a photometric unit
        try: other = PhotometricUnit(other)
        #except ValueError: raise ValueError("The other unit is not a photometric unit")
        except ValueError: return False

        # Use implementation in base class
        return super(PhotometricUnit, self).__eq__(other)

    # -----------------------------------------------------------------

    @property
    def is_luminosity(self):

        """
        This function ...
        :return:
        """

        return self.base_physical_type == "luminosity"

    # -----------------------------------------------------------------

    @property
    def is_flux(self):

        """
        This function ...
        :return:
        """

        return self.base_physical_type == "flux"

    # -----------------------------------------------------------------

    @property
    def is_intensity(self):

        """
        This function ...
        :return:
        """

        return self.base_physical_type == "intensity"

    # -----------------------------------------------------------------

    @property
    def is_brightness(self):
        
        """
        THis function ...
        :return: 
        """

        return self.is_intrinsic_surface_brightness or self.is_surface_brightness

    # -----------------------------------------------------------------

    @property
    def is_intrinsic_surface_brightness(self):
        
        """
        THis function ...
        :return: 
        """

        return self.base_physical_type == "intrinsic surface brightness"

    # -----------------------------------------------------------------

    @property
    def is_intrinsic_surface_brightness_with_distance(self):

        """
        This function ...
        :return:
        """

        return self.is_intrinsic_surface_brightness and self.has_distance_unit

    # -----------------------------------------------------------------

    @property
    def is_intrinsic_surface_brightness_without_distance(self):

        """
        This function ...
        :return:
        """

        return self.is_intrinsic_surface_brightness and not self.has_distance_unit

    # -----------------------------------------------------------------

    @property
    def is_surface_brightness(self):

        """
        This function ...
        :return:
        """

        return self.base_physical_type == "surface brightness"

    # -----------------------------------------------------------------

    @property
    def is_per_angular_area(self):

        """
        This function ...
        :return: 
        """

        return self.is_intensity or self.is_surface_brightness

    # -----------------------------------------------------------------

    @property
    def is_per_intrinsic_area(self):

        """
        This function ...
        :return: 
        """

        return self.is_intrinsic_surface_brightness

    # -----------------------------------------------------------------

    @property
    def is_per_angular_or_intrinsic_area(self):

        """
        This function ...
        :return: 
        """

        return self.is_per_angular_area or self.is_per_intrinsic_area
        # same as: return self.is_intensity or self.is_brightness
        # same as: return self.is_intensity or self.is_surface_brightness or self.is_intrinsic_surface_brightness

    # -----------------------------------------------------------------

    @property
    def is_per_pixelsize(self):

        """
        This function returns the same as the is_per_angular_or_intrinsic_area() function
        :return: 
        """

        return self.is_per_angular_or_intrinsic_area

    # -----------------------------------------------------------------

    @property
    def corresponding_flux_unit(self):

        """
        This function ...
        :return:
        """

        # Already a flux
        if self.is_flux: return self.copy()

        # Intensity
        elif self.is_intensity:

            new_unit = self * self.solid_angle_unit / "m2"
            new_unit_string = str(new_unit)

        # Luminosity
        elif self.is_luminosity:

            new_unit = self / "m2"
            new_unit_string = str(new_unit)

        # Surface brightness
        elif self.is_surface_brightness:

            new_unit = self * self.solid_angle_unit
            new_unit_string = str(new_unit)

        # Intrinsic surface brightness
        elif self.is_intrinsic_surface_brightness:

            if self.has_distance_unit:

                new_unit = self * self.extent_unit
                new_unit_string = str(new_unit)

            else:

                new_unit = self * self.extent_unit / "m2"
                new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=False, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_luminosity_unit(self):

        """
        This function ...
        :return:
        """

        # From bolometric
        if self.is_bolometric:

            new_unit_string = str(self.base_unit)

        # From neutral density
        elif self.is_neutral_density:

            new_unit_string = str(self.base_unit)

        # From wavelength density
        elif self.is_wavelength_density:

            new_unit = self.base_unit / self.wavelength_unit
            new_unit_string = str(new_unit)

        # From frequency density
        elif self.is_frequency_density:

            new_unit = self.base_unit / self.frequency_unit
            new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=False, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_intensity_unit(self):

        """
        This function ...
        :return:
        """

        # Already intensity
        if self.is_intensity: return self.copy()

        # From luminosity
        elif self.is_luminosity:

            new_unit = self / "sr"
            new_unit_string = str(new_unit)

        # From flux
        elif self.is_flux:

            new_unit = self * self.distance_unit / "sr"
            new_unit_string = str(new_unit)

        # From surface brightness
        elif self.is_surface_brightness:

            new_unit = self * self.distance_unit
            new_unit_string = str(new_unit)

        # From intrinsic surface brightness
        elif self.is_intrinsic_surface_brightness:

            if self.has_distance_unit:

                new_unit = self * self.distance_unit * self.extent_unit / "sr"
                new_unit_string = str(new_unit)

            else:

                new_unit = self * self.extent_unit / "sr"
                new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=False, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_bolometric_unit(self):

        """
        This function ...
        :return:
        """

        # Already a bolometric unit
        if self.is_bolometric: return self.copy()

        # From frequency density
        elif self.is_frequency_density:

            new_unit = self * self.frequency_unit
            new_unit_string = str(new_unit)

        # From wavelength density
        elif self.is_wavelength_density:

            new_unit = self * self.wavelength_unit
            new_unit_string = str(new_unit)

        # From neutral density
        elif self.is_neutral_density:
            new_unit_string = str(self)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=False, density_strict=True, brightness=self.brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_wavelength_density_unit(self):

        """
        This function ...
        :return:
        """

        # Already wavelength density
        if self.is_wavelength_density: return self.copy()

        # Bolometric unit
        elif self.is_bolometric:

            new_unit = self / "micron"
            new_unit_string = str(new_unit)

        # Frequency density unit
        elif self.is_frequency_density:

            new_unit = self * self.frequency_unit / "micron"
            new_unit_string = str(new_unit)

        # Neutral density unit
        elif self.is_neutral_density:

            new_unit = self / "micron"
            new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=True, density_strict=True, brightness=self.brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_frequency_density_unit(self):

        """
        This function ...
        :return:
        """

        # Already frequency density
        if self.is_frequency_density: return self.copy()

        # Bolometric
        elif self.is_bolometric:

            new_unit = self / "Hz"
            new_unit_string = str(new_unit)

        # Wavelength density
        elif self.is_wavelength_density:

            new_unit = self * self.wavelength_unit / "Hz"
            new_unit_string = str(new_unit)

        # Neutral density
        elif self.is_neutral_density:

            new_unit = self / "Hz"
            new_unit_string = str(new_unit)

        # Invalid state
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=True, density_strict=True, brightness=self.brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_neutral_density_unit(self):

        """
        This function ...
        :return:
        """

        # Already neutral density
        if self.is_neutral_density: return self.copy()

        # Bolometric
        elif self.is_bolometric:

            new_unit_string = str(self)

        elif self.is_frequency_density:

            new_unit = self * self.frequency_unit
            new_unit_string = str(new_unit)

        elif self.is_wavelength_density:

            new_unit = self * self.wavelength_unit
            new_unit_string = str(new_unit)

        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=True, density_strict=True, brightness=self.brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_brightness_unit(self):

        """
        This function ...
        :return:
        """

        # Already a brightness
        if self.is_brightness: return self.copy()

        # From luminosity
        elif self.is_luminosity:

            new_unit = self / "m2" / "sr"
            new_unit_string = str(new_unit)

        # From intensity
        elif self.is_intensity:

            new_unit = self / "m2"
            new_unit_string = str(new_unit)

        # From flux
        elif self.is_flux:

            new_unit = self / "sr"
            new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid state")

        # Create the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=True, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_non_brightness_unit(self):

        """
        This function ...
        :return:
        """

        # Not a brightness
        if not self.is_brightness: return self.copy()

        # Per angular area
        elif self.is_per_angular_area:

            new_unit = self * self.solid_angle_unit
            new_unit_string = str(new_unit)

        # Per intrinsic area
        elif self.is_per_intrinsic_area:

            new_unit = self * self.extent_unit
            new_unit_string = str(new_unit)

        # Invalid
        else: raise RuntimeError("Invalid unit")

        # Debugging
        log.debug("New unit string: '" + new_unit_string + "'")

        # Create and return the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=False, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def is_per_angular_or_instrinsic_area(self):

        """
        This function ...
        :return:
        """

        return self.is_per_angular_area or self.is_per_intrinsic_area

    # -----------------------------------------------------------------

    @property
    def corresponding_angular_or_intrinsic_area_unit(self):

        """
        This function ...
        :return:
        """

        # Already:
        # Should cover intensities, surface and intrinsic surface brightnesses
        if self.is_per_angular_or_intrinsic_area: return self.copy()

        # From luminosity
        elif self.is_luminosity:

            new_unit = self / "sr"
            new_unit_string = str(new_unit)
            brightness = False # intensity

        # From flux
        elif self.is_flux:

            new_unit = self / "sr"
            new_unit_string = str(new_unit)
            brightness = True

        # Invalid unit
        else: raise ValueError("Invalid unit")

        # Debugging
        log.debug("New unit string: '" + new_unit_string + "'")

        # Create and return the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_non_angular_or_intrinsic_area_unit(self):

        """
        This function ...
        :return:
        """

        # Already
        if not self.is_per_angular_or_intrinsic_area: return self.copy()

        # From intensity
        elif self.is_intensity:

            new_unit = self * self.solid_angle_unit
            new_unit_string = str(new_unit)

        # From brightness
        elif self.is_brightness:

            new_unit = self * self.extent_unit
            new_unit_string = str(new_unit)

        # Invalid
        else: raise ValueError("Invalid unit")

        # Debugging
        log.debug("New unit string: '" + new_unit_string + "'")

        # Create and return the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=False, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_angular_area_unit(self):

        """
        This function ...
        :return: 
        """

        # Intensity and surface brightness
        if self.is_per_angular_area: return self.copy()

        # Luminosity
        elif self.is_luminosity:

            #new_unit_string = str(self) + " / sr"
            new_unit = self / "sr"
            new_unit_string = str(new_unit)
            brightness = False # is intensity now
            #return PhotometricUnit(str(self) + " / sr", density=self.density, density_strict=True, brightness=False, brightness_strict=True) # is luminosity, not a brightness!!

        # Flux
        elif self.is_flux:

            #new_unit_string = str(self) + " / sr"
            new_unit = self / "sr"
            new_unit_string = str(new_unit)
            brightness = True
            #return PhotometricUnit(str(self) + " / sr", density=self.density, density_strict=True, brightness=True, brightness_strict=True)

        # Intrinsic surface brightness
        elif self.is_intrinsic_surface_brightness:

            #new_unit_string = str(self * self._extent_unit) + "/sr"
            new_unit = self * self._extent_unit / "sr"
            new_unit_string = str(new_unit)

            if self.has_extent_unit: brightness = True # still surface brightness, but now
            else: brightness = False # is intensity now
            #return PhotometricUnit(str(self * self._extent_unit) + "/sr", density=self.density, brightness=True, density_strict=True, brightness_strict=True)

        # Invalid unit
        else: raise RuntimeError("Invalid unit")

        # Debugging
        log.debug("New unit string: '" + new_unit_string + "'")

        # Create and return the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def corresponding_intrinsic_area_unit(self):

        """
        This function ...
        :return: 
        """

        # Intrinsic surface brightness
        if self.is_per_intrinsic_area: return self.copy()

        # Luminosity
        elif self.is_luminosity:

            brightness = True
            #new_unit_string = str(self) + " / pc2"
            new_unit = self / "pc2"
            new_unit_string = str(new_unit)

            #print("new unit string", new_unit_string)
            #return PhotometricUnit(new_unit_string, density=self.density, brightness=True, density_strict=True, brightness_strict=True)

        # Flux
        elif self.is_flux:

            brightness = True
            #new_unit_string = str(self * self.distance_unit) + " / pc2"
            new_unit = self * self.distance_unit / "pc2"
            new_unit_string = str(new_unit)

            #return PhotometricUnit(str(self * self.distance_unit) + " / pc2", density=self.density, brightness=True, density_strict=True, brightness_strict=True)

        # Intensity
        elif self.is_intensity:

            brightness = True
            #new_unit_string = str(self * self.solid_angle_unit) + " / pc2"
            new_unit = self * self.solid_angle_unit / "pc2"
            new_unit_string = str(new_unit)

            #return PhotometricUnit(str(self * self.solid_angle_unit) + " / pc2", density=self.density, brightness=True, density_strict=True, brightness_strict=True)

        # Surface brightness
        elif self.is_surface_brightness:

            brightness = True
            #new_unit_string = str(self * self.distance_unit * self.solid_angle_unit) + "/ pc2"
            new_unit = self * self.distance_unit * self.solid_angle_unit / "pc2"
            new_unit_string = str(new_unit)

            #return PhotometricUnit(str(self * self.distance_unit * self.solid_angle_unit) + "/ pc2", density=self.density, brightness=True, density_strict=True, brightness_strict=True)

        # Invalid
        else: raise RuntimeError("Invalid unit")

        # Debugging
        log.debug("New unit string: '" + new_unit_string + "'")

        # Create and return the new unit
        return PhotometricUnit(new_unit_string, density=self.density, density_strict=True, brightness=brightness, brightness_strict=True)

    # -----------------------------------------------------------------

    @property
    def has_extent_unit(self):

        """
        This function ...
        :return:
        """

        return self.extent_unit != ""

    # -----------------------------------------------------------------

    @property
    def has_distance_unit(self):

        """
        This function ...
        :return:
        """

        return self.distance_unit != ""

    # -----------------------------------------------------------------

    @property
    def has_solid_angle_unit(self):

        """
        This function ...
        :return:
        """

        return self.solid_angle_unit != ""

    # -----------------------------------------------------------------

    @property
    def base_physical_type(self):

        """
        This function ...
        :return:
        """

        # The base unit is a power
        if self.base_unit.physical_type == "power":

            # e.g. '/ kpc2' dependence: ALWAYS INTRINSIC SURFACE BRIGHTNESS
            if self.has_extent_unit: base = "intrinsic surface brightness"
                # SHOULD WE HAVE A DIFFERENT NAME DEPENDING ON WETHER ALSO A DISTANCE UNIT IS PRESENT??

            # e.g. '/ m2' dependence, no e.g. '/ kpc2' dependence
            elif self.has_distance_unit:

                if self.has_solid_angle_unit: base = "surface brightness"
                else: base = "flux"

            # No length unit
            else:

                if self.has_solid_angle_unit: base = "intensity"
                else: base = "luminosity"

        # The base unit is a frequency
        elif self.base_unit.physical_type == "frequency": base = "detection rate"

        # The base unit is dimensionless
        else: base = "detections"

        # Return the base type
        return base

    # -----------------------------------------------------------------

    @property
    def spectral_density_type(self):

        """
        This function ...
        :return:
        """

        # Wavelength densities
        if self.is_wavelength_density: return "wavelength"

        # Frequency densities
        elif self.is_frequency_density: return "frequency"

        # Neutral density or regular power/flux/surfacebrightness
        elif self.is_neutral_density: return "neutral"

        # Not a spectral density
        else: return None

    # -----------------------------------------------------------------

    @property
    def is_spectral_density(self):

        """
        This function ...
        :return:
        """

        return self.density

    # -----------------------------------------------------------------

    @property
    def is_bolometric(self):

        """
        This function ...
        :return:
        """

        return not self.is_spectral_density

    # -----------------------------------------------------------------

    @property
    def is_wavelength_density(self):

        """
        This function ...
        :return:
        """

        if self.wavelength_unit != "":
            assert self.frequency_unit == ""
            return True
        else: return False

    # -----------------------------------------------------------------

    @property
    def is_frequency_density(self):

        """
        This function ...
        :return:
        """

        if self.frequency_unit != "":
            assert self.wavelength_unit == ""
            return True
        else: return False

    # -----------------------------------------------------------------

    @property
    def is_neutral_density(self):

        """
        This function ...
        :return:
        """

        if self.wavelength_unit == "" and self.frequency_unit == "": return self.density
        else: return False

    # -----------------------------------------------------------------

    @property
    def physical_type(self):

        """
        This function ...
        :return:
        """

        # Get the spectral density type
        density_type = self.spectral_density_type

        # Return the type
        if density_type is None: return self.base_physical_type
        else: return " ".join([density_type, self.base_physical_type, "density"])

    # -----------------------------------------------------------------

    @property
    def base_symbol(self):

        """
        This function ...
        :return: 
        """

        if self.is_luminosity: return "L"
        elif self.is_flux: return "F"
        elif self.is_intensity: return "I"
        elif self.is_surface_brightness: return "S"
        elif self.is_intrinsic_surface_brightness: return "S'"
        else: raise ValueError("No symbol for this unit")

    # -----------------------------------------------------------------

    @property
    def symbol(self):

        """
        This function ...
        :return: 
        """

        # Spectral density
        if self.is_spectral_density:

            if self.is_neutral_density:

                prefix = lambda_symbol
                suffix = "_" + lambda_symbol

            elif self.is_frequency_density:

                prefix = ""
                suffix = "_" + nu_symbol

            elif self.is_wavelength_density:

                prefix = ""
                suffix = "_" + lambda_symbol

            else: raise RuntimeError("Something went wrong")

        # Not a spectral density
        else: prefix = suffix = ""

        # Return the symbol
        return prefix + self.base_symbol + suffix

    # -----------------------------------------------------------------

    def conversion_factor(self, to_unit, density=False, wavelength=None, frequency=None, distance=None, solid_angle=None,
                          fltr=None, pixelscale=None, brightness=False, brightness_strict=False, density_strict=False):

        """
        This function ...
        :param to_unit:
        :param density:
        :param wavelength:
        :param frequency:
        :param distance:
        :param solid_angle:
        :param fltr:
        :param pixelscale:
        :param brightness:
        :param brightness_strict:
        :param density_strict:
        :return:
        """

        #print(self, self.density)
        #print(to_unit)

        # Parse "to unit"
        to_unit = PhotometricUnit(to_unit, density=density, brightness=brightness, brightness_strict=brightness_strict, density_strict=density_strict)

        #print("1", self, self.density, self.is_neutral_density, self.is_wavelength_density, self.is_frequency_density)
        #print("2", to_unit, to_unit.density, to_unit.is_neutral_density, to_unit.is_wavelength_density, to_unit.is_frequency_density)

        # Determine wavelength and frequency
        if wavelength is not None:
            if frequency is not None: raise ValueError("Either frequency or wavelength can be specified")
            frequency = wavelength.to("Hz", equivalencies=spectral())
        elif frequency is not None:
            wavelength = frequency.to("micron", equivalencies=spectral())
        elif fltr is not None:
            wavelength = fltr.pivot
            frequency = wavelength.to("Hz", equivalencies=spectral())

        # Same type
        if self.physical_type == to_unit.physical_type:
            #print("here")
            factor = (self / to_unit).to("")
            return factor

        # Convert
        if types.is_string_type(solid_angle):
            from ..tools import parsing
            solid_angle = parsing.quantity(solid_angle)

        # Convert
        if types.is_string_type(distance):
            from ..tools import parsing
            distance = parsing.quantity(distance)

        # Convert
        if types.is_string_type(frequency):
            from ..tools import parsing
            frequency = parsing.quantity(frequency)

        # Convert
        if types.is_string_type(wavelength):
            from ..tools import parsing
            wavelength = parsing.quantity(wavelength)

        # Convert
        if types.is_string_type(pixelscale):
            from ..tools import parsing
            pixelscale = parsing.quantity(pixelscale)

        # Make PixelScale instance
        if isinstance(pixelscale, Quantity): pixelscale = Pixelscale(pixelscale)
        elif isinstance(pixelscale, Pixelscale): pass
        elif pixelscale is None: pass
        else: raise ValueError("Don't know what to do with pixelscale of type " + str(type(pixelscale)))

        # If solid angle is None, convert pixelscale to solid angle (of one pixel)
        if solid_angle is None and pixelscale is not None: solid_angle = pixelscale.solid_angle

        #print(self, self.physical_type, self.is_neutral_density, self.is_wavelength_density, self.is_frequency_density)

        # Neutral density
        if self.is_neutral_density:

            # Convert into new unit by dividing by wavelength or by frequency
            if to_unit.is_wavelength_density:
                if wavelength is None: raise ValueError("Wavelength should be specified for conversion from neutral density to wavelength density")
                new_unit = photometric_unit_from_divide_unit_and_quantity(self, wavelength)
            elif to_unit.is_frequency_density:
                if frequency is None: raise ValueError("Frequency should be specified for conversion from neutral density to frequency density")
                new_unit = photometric_unit_from_divide_unit_and_quantity(self, frequency)
            elif to_unit.is_neutral_density: new_unit = self
            else: raise ValueError("Cannot convert from spectral density to integrated quantity") # asked to convert to not a spectral density

        # Wavelength density
        elif self.is_wavelength_density:

            # Convert into new unit by multiplying with wavelength or with wavelength / frequency
            if to_unit.is_neutral_density:
                if wavelength is None: raise ValueError("Wavelength should be specified for conversion from wavelength density to neutral density")
                new_unit = photometric_unit_from_multiply_unit_and_quantity(self, wavelength)
            elif to_unit.is_frequency_density:
                if wavelength is None: raise ValueError("Wavelength should be specified for conversion from wavelength density to frequency density")
                if frequency is None: raise ValueError("Frequency should be specified for conversion from wavelength density to frequency density")
                new_unit = photometric_unit_from_multiply_unit_and_quantity(self, wavelength / frequency)
            elif to_unit.is_wavelength_density: new_unit = self
            else: raise ValueError("Cannot convert from spectral density to integrated quantity")

        # Frequency density
        elif self.is_frequency_density:

            # Convert into new unit by multiplying with frequency or with frequency / wavelength
            if to_unit.is_neutral_density:
                if frequency is None: raise ValueError("Frequency should be specified for conversion from frequency density to neutral density")
                new_unit = photometric_unit_from_multiply_unit_and_quantity(self, frequency)
            elif to_unit.is_frequency_density: new_unit = self
            elif to_unit.is_wavelength_density:
                if frequency is None: raise ValueError("Frequency should be specified for conversion from frequency density to wavelength density")
                if wavelength is None: raise ValueError("Wavelength should be specified for conversion from frequency density to wavelength density")
                new_unit = photometric_unit_from_multiply_unit_and_quantity(self, frequency / wavelength)
            else: raise ValueError("Cannot convert from spectral density to integrated quantity")

        # Not a spectral density
        else:

            # Cannot convert from an integrated quantity to a spectral density
            if to_unit.is_neutral_density: raise ValueError("Cannot convert from integrated quantity to spectral density")
            elif to_unit.is_frequency_density: raise ValueError("Cannot convert from integrated quantity to spectral density")
            elif to_unit.is_wavelength_density: raise ValueError("Cannot convert from integrated quantity to spectral density")
            else: new_unit = self

        #print(self, self.physical_type, self.base_physical_type)

        # Same base type
        if self.base_physical_type == to_unit.base_physical_type:
            factor = new_unit.to(to_unit)
            return factor

        # Different base type, luminosity
        elif self.base_physical_type == "luminosity":

            # Luminosity to flux
            if to_unit.base_physical_type == "flux":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by 4 pi distance**2
                new_unit /= (4.0 * math.pi * distance**2)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Luminosity to intensity
            elif to_unit.base_physical_type == "intensity":

                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by solid angle
                new_unit /= solid_angle

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Luminosity to surface brightness
            elif to_unit.base_physical_type == "surface brightness":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by 4 pi distance**2 and solid angle
                new_unit /= (4.0 * math.pi * distance**2 * solid_angle)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Luminosity to intrinsic surface brightness
            elif to_unit.is_intrinsic_surface_brightness:

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by pixel area
                area = pixelscale.pixel_area(distance)
                new_unit /= area

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Invalid
            else: raise RuntimeError("We shouldn't reach this part")

            # Return the conversion factor
            return factor

        # Different base type, flux
        elif self.base_physical_type == "flux":

            # Flux to luminosity
            if to_unit.base_physical_type == "luminosity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by 4 pi distance**2
                new_unit *= (4.0 * math.pi * distance ** 2)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Flux to surface brightness
            elif to_unit.base_physical_type == "surface brightness":

                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by solid angle
                new_unit /= solid_angle

                #print("here")

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Flux to intensity
            elif to_unit.base_physical_type == "intensity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by solid angle
                # Multiply by 4 pi distance**2
                new_unit *= (4.0 * math.pi * distance ** 2) / solid_angle

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Flux to intrinsic surface brightness
            elif to_unit.is_intrinsic_surface_brightness:

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by 4 pi distance**2
                new_unit *= 4.0 * math.pi * distance ** 2

                # Divide by pixel area
                area = pixelscale.pixel_area(distance)
                new_unit /= area

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Invalid
            else: raise RuntimeError("We shouldn't reach this part")

            # Return the conversion factor
            return factor

        # Different base type, intensity
        elif self.base_physical_type == "intensity":

            # Intensity to luminosity
            if to_unit.base_physical_type == "luminosity":

                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by solid angle
                new_unit *= solid_angle

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Intensity to flux
            elif to_unit.base_physical_type == "flux":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by solid angle
                # Divide by 4 pi distance**2
                new_unit *= solid_angle / (4.0 * math.pi * distance ** 2)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Intensity to surface brightness
            elif to_unit.base_physical_type == "surface brightness":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Divide by 4 pi distance**2
                new_unit /= (4.0 * math.pi * distance ** 2)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Intensity to intrinsic surface brightness
            elif to_unit.is_intrinsic_surface_brightness:

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by solid angle
                new_unit *= solid_angle

                # Divide by pixel area
                area = pixelscale.pixel_area(distance)
                new_unit /= area

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Invalid
            else: raise RuntimeError("We shouldn't reach this part")

            # Return the conversion factor
            return factor

        # Surface brightness
        elif self.base_physical_type == "surface brightness":

            # Surface brightness to luminosity
            if to_unit.base_physical_type == "luminosity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by 4 pi distance**2 and solid angle
                new_unit *= (4.0 * math.pi * distance ** 2 * solid_angle)

                #print("NEW UNIT", new_unit)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Surface brightness to flux
            elif to_unit.base_physical_type == "flux":

                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by solid angle
                new_unit *= solid_angle

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Surface brightness to intensity
            elif to_unit.base_physical_type == "intensity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by 4 pi distance**2
                new_unit *= (4.0 * math.pi * distance ** 2)

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Surface brightness to intrinsic surface brightness
            elif to_unit.base_physical_type == "intrinsic surface brightness":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by 4 pi distance**2
                new_unit *= (4.0 * math.pi * distance **2)

                # Multiply by solid angle / area
                new_unit *= solid_angle

                # Divide by pixel area
                area = pixelscale.pixel_area(distance)
                new_unit /= area

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Invalid
            else: raise RuntimeError("We shouldn't reach this part")

            # Return the conversion factor
            return factor

        # Intrinsic surface brightness
        elif self.base_physical_type == "intrinsic surface brightness":

            # Intrinsic surface brightness to luminosity
            if to_unit.base_physical_type == "luminosity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by the pixelarea
                area = pixelscale.pixel_area(distance)
                new_unit *= area

                # Determine factor
                factor = new_unit.to(to_unit).value

            # Intrinsic surface brightness to flux
            elif to_unit.base_physical_type == "flux":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by the pixelarea
                area = pixelscale.pixel_area(distance)
                new_unit *= area

                # Divide by 4 pi distance**2
                new_unit /= (4.0 * math.pi * distance ** 2)

                # Determine the factor
                factor = new_unit.to(to_unit).value

            # Intrinsic surface brightness to intensity
            elif to_unit.base_physical_type == "intensity":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by the pixelarea
                area = pixelscale.pixel_area(distance)
                new_unit *= area

                # Divide by solid angle
                new_unit /= solid_angle

                # Determine the factor
                factor = new_unit.to(to_unit).value

            # Intrinsic surface brightness to surface brightness
            elif to_unit.base_physical_type == "surface brightness":

                if distance is None: raise ValueError("Distance should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if pixelscale is None: raise ValueError("Pixelscale should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)
                if solid_angle is None: raise ValueError("Solid angle should be specified for conversion from " + self.physical_type + " to " + to_unit.physical_type)

                # Multiply by the pixelarea
                area = pixelscale.pixel_area(distance)
                new_unit *= area

                # Divide by the solid angle
                new_unit /= solid_angle

                # Divide by 4 pi distance**2
                new_unit /= (4.0 * math.pi * distance ** 2)

                # Determine the factor
                factor = new_unit.to(to_unit).value

            # Invalid
            else: raise RuntimeError("We shouldn't reach this part")

            # Return the conversion factor
            return factor

        # Unknown base type
        else: raise RuntimeError("Unknown base type:" + self.base_physical_type)

# -----------------------------------------------------------------

def is_area(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    return unit.physical_type == "area"

# -----------------------------------------------------------------

def is_inverse_area(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    return (unit**-1).physical_type == "area"

# -----------------------------------------------------------------

def is_solid_angle(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    return unit.physical_type == "solid angle"

# -----------------------------------------------------------------

def is_inverse_solid_angle(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    return (unit**-1).physical_type == "solid angle"

# -----------------------------------------------------------------

def is_length(unit):

    """
    Thins function ...
    :param unit:
    :return:
    """

    return unit.physical_type == "length"

# -----------------------------------------------------------------

def is_wavelength(unit):

    """
    This fucntion ...
    :return:
    """

    return unit.physical_type == "length"

# -----------------------------------------------------------------

def is_frequency(unit):

    """
    This function ...
    :return:
    """

    return unit.physical_type == "frequency"

# -----------------------------------------------------------------

def is_time(unit):

    """
    This function ...
    :return:
    """

    return unit.physical_type == "time"

# -----------------------------------------------------------------

def is_inverse_wavelength(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    if len(unit.bases) != 1: return False
    return unit.bases[0].physical_type == "length" and unit.powers[0] == -1

# -----------------------------------------------------------------

def is_inverse_frequency(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    if len(unit.bases) != 1: return False
    return (unit.bases[0].physical_type == "time" and unit.powers[0] == 1) or (unit.bases[0].physical_type == "frequency" and unit.powers[0] == -1)

# -----------------------------------------------------------------

def is_angle(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    unit = parse_unit(unit)
    return unit.physical_type == "angle"

# -----------------------------------------------------------------

def contains_area(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    for base, power in zip(unit.bases, unit.powers):
        if power == 2 and is_length(base): return True
        if power == 1 and is_area(base): return True

    return False

# -----------------------------------------------------------------

def contains_solid_angle(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    for base, power in zip(unit.bases, unit.powers):
        if power == 2 and is_angle(base): return True
        if power == 1 and is_solid_angle(base): return True

    return False

# -----------------------------------------------------------------

def contains_wavelength(unit):

    """
    This function ...
    :return:
    """

    # Loop over the bases
    for base, power in zip(unit.bases, unit.powers):
        if power == 1 and is_wavelength(base): return True

    return False

# -----------------------------------------------------------------

def contains_frequency(unit):

    """
    This function ...
    :return:
    """

    # Loop over the bases
    for base, power in zip(unit.bases, unit.powers):
        if power == 1 and is_frequency(base): return True
        if power == -1 and is_time(base): return True

    return False

# -----------------------------------------------------------------

def contains_inverse_area(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    # Loop over the bases
    for base, power in zip(unit.bases, unit.powers):
        if power == -1 and is_area(unit): return True
        if power == -2 and is_length(unit): return True

    return False

# -----------------------------------------------------------------

def contains_inverse_solid_angle(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    for base, power in zip(unit.bases, unit.powers):
        if power == -1 and is_solid_angle(unit): return True
        if power == -2 and is_angle(unit): return True

    return False

# -----------------------------------------------------------------

def contains_inverse_frequency(unit):

    """
    This function ...
    """

    # Loop over the bases
    for base, power in zip(unit.bases, unit.powers):
        if power == 1 and is_time(base): return True
        if power == -1 and is_frequency(base): return True
    return False

# -----------------------------------------------------------------

def contains_inverse_wavelength(unit):

    """
    This function ...
    :param unit:
    :return:
    """

    # Loop over the bases
    for base, power in zip(unit.bases, unit.powers):
        if power == -1 and is_wavelength(base): return True
    return False

# -----------------------------------------------------------------

def make_composite_multiplication(unit_a, unit_b):

    """
    This function ...
    :param unit_a:
    :param unit_b:
    :return:
    """

    return CompositeUnit(1, [unit_a, unit_b], [1, 1])

# -----------------------------------------------------------------

def photometric_unit_from_multiply_unit_and_quantity(unit, quantity):

    """
    This function ...
    :param unit:
    :param quantity:
    :return:
    """

    return PhotometricUnit(unit * quantity)

# -----------------------------------------------------------------

def photometric_unit_from_divide_unit_and_quantity(unit, quantity):

    """
    This function ...
    :param unit:
    :param quantity:
    :return:
    """

    return PhotometricUnit(unit / quantity)

# -----------------------------------------------------------------

def photometric_unit_from_divide_unit_and_quantity_reverse(unit, quantity):

    """
    This function ...
    :param unit:
    :param quantity:
    :return:
    """

    return PhotometricUnit(quantity / unit)

# -----------------------------------------------------------------

def multiply_units(unit_a, unit_b):

    """
    This function ...
    :param unit_a:
    :param unit_b:
    :return:
    """

    # If the other unit is dimensionless
    if unit_b == "": return unit_a.copy()

    # If the other unit is dimensionless with a certain scale
    elif unit_b.physical_type == "dimensionless" and unit_b.scale != 1: return PhotometricUnit(CompositeUnit(unit_a.scale * unit_b.scale, unit_a.bases, unit_a.powers), density=unit_a.is_spectral_density)

    # Spectral density
    if unit_a.is_spectral_density:

        # If this is a wavelength density
        if unit_a.is_wavelength_density:

            # From wavelength spectral density to neutral spectral density
            if is_wavelength(unit_b): return PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=True)
            elif contains_wavelength(unit_b): return parse_unit(make_composite_multiplication(unit_a, unit_b), density=True)
            else: return parse_unit(make_composite_multiplication(unit_a, unit_b))

        # If this is a frequency density
        elif unit_a.is_frequency_density:

            # From frequency spectral density to neutral spectral density
            if is_frequency(unit_b): return PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=True)
            elif contains_wavelength(unit_b): return parse_unit(make_composite_multiplication(unit_a, unit_b), density=True)
            else: return parse_unit(make_composite_multiplication(unit_a, unit_b))

        # Neutral density
        else:

            # From netural
            if is_inverse_wavelength(unit_b): return PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=True)
            elif is_inverse_frequency(unit_b): return PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=True)
            elif contains_inverse_wavelength(unit_b): return parse_unit(make_composite_multiplication(unit_a, unit_b), density=True)
            elif contains_inverse_frequency(unit_b): return parse_unit(make_composite_multiplication(unit_a, unit_b), density=True)
            else: return parse_unit(make_composite_multiplication(unit_a, unit_b))

    # Not a spectral density
    else:

        # If unit b is an inverse wavelength
        if is_inverse_wavelength(unit_b):

            unit = PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=False)
            if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by multiplication with the unit '" + str(unit_b) + ". This may not be the intention.")
            return unit

        # If unit b is an inverse frequency
        elif is_inverse_frequency(unit_b):

            unit = PhotometricUnit(make_composite_multiplication(unit_a, unit_b), density=False)
            if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by multiplication with the unit '" + str(unit_b) + ". This may not be the intention.")
            return unit

        # Try parsing as spectral photometric quantity (density=True), but possibly no photometric quantity
        elif contains_inverse_wavelength(unit_b):

            unit = parse_unit(make_composite_multiplication(unit_a, unit_b), density=False)
            try:
                if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by multiplication with the unit '" + str(unit_b) + ". This may not be the intention.")
            except AttributeError: pass
            return unit

        # Try parsing as spectral photometric quantity(density=True), but possibly no photometric quantity
        elif contains_inverse_frequency(unit_b):

            unit = parse_unit(make_composite_multiplication(unit_a, unit_b), density=False)
            try:
                if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by multiplication with the unit '" + str(unit_b) + ". This may not be the intention.")
            except AttributeError: pass
            return unit

        # Parse regularly
        else: return parse_unit(make_composite_multiplication(unit_a, unit_b))

# -----------------------------------------------------------------

def make_composite_division(unit_a, unit_b):

    """
    This function ...
    :param unit_a:
    :param unit_b:
    :return:
    """

    return CompositeUnit(1, [unit_a, unit_b], [1, -1], _error_check=False)

# -----------------------------------------------------------------

def divide_units(unit_a, unit_b, density=None, brightness=None):

    """
    This function ...
    :param unit_a:
    :param unit_b:
    :param density:
    :param brightness:
    :return:
    """

    # Strict?
    density_strict = False
    brightness_strict = False

    # If the other unit is dimensionless
    if unit_b == "": return unit_a.copy()

    # If the other unit is dimensionless with a certain scale
    elif unit_b.physical_type == "dimensionless" and unit_b.scale != 1:

        #return PhotometricUnit(CompositeUnit(unit_a.scale / unit_b.scale, unit_a.bases, unit_a.powers), density=unit_a.is_spectral_density)
        unit = CompositeUnit(unit_a.scale / unit_b.scale, unit_a.bases, unit_a.powers)

        if density is None: density = unit_a.is_spectral_density
        else: density_strict = True

        if brightness is None: brightness = unit_a.is_brightness
        else: brightness_strict = True

    # Make composite unit
    else:

        unit = make_composite_division(unit_a, unit_b)

        # If we have a spectral density
        if unit_a.is_spectral_density:

            # If this is a wavelength density
            if unit_a.is_wavelength_density:

                if is_inverse_wavelength(unit_b):

                    #return PhotometricUnit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                elif contains_inverse_wavelength(unit_b):

                    #return parse_unit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                else:

                    #return parse_unit(make_composite_division(unit_a, unit_b))
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = unit_a.density #False # ?
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

            # If this is a frequency density
            if unit_a.is_frequency_density:

                if is_inverse_frequency(unit_b):

                    #return PhotometricUnit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                elif contains_inverse_frequency(unit_b):

                    #return parse_unit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                else:

                    #return parse_unit(make_composite_division(unit_a, unit_b))
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = unit_a.density #False # ?
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

            # If this is a neutral density
            else:

                # Divice by wavelength unit
                if is_wavelength(unit_b):

                    #return PhotometricUnit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    # CAN ONLY BE TRUE
                    if density is None: density = True
                    elif density is False: raise ValueError("Cannot obtain an bolometric unit")
                    density_strict = True

                    #brightness = unit_a.is_brightness

                # Divide by frequency unit
                elif is_frequency(unit_b):

                    #return PhotometricUnit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    # CAN ONLY BE TRUE
                    if density is None: density = True
                    elif density is False: raise ValueError("Cannot obtain a bolometric unit")
                    density_strict = True

                    #brightness = unit_a.is_brightness

                # Divide by unit containing wavelength unit
                elif contains_wavelength(unit_b):

                    #return parse_unit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    # CAN BE ANYTHING ACTUALLY (ONLY CONTAINS)
                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                # Divide by unit containing frequency unit
                elif contains_frequency(unit_b):

                    #return parse_unit(make_composite_division(unit_a, unit_b), density=True)
                    #unit = make_composite_division(unit_a, unit_b)

                    # CAN BE ANYTHING ACTUALLY (ONLY CONTAINS)
                    if density is None: density = True
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

                else:

                    #return parse_unit(make_composite_division(unit_a, unit_b))
                    #unit = make_composite_division(unit_a, unit_b)

                    if density is None: density = unit_a.density #False
                    else: density_strict = True

                    #brightness = unit_a.is_brightness

        # Not a spectral density
        else:

            # If unit b is a wavelength
            if is_wavelength(unit_b):

                #unit = PhotometricUnit(make_composite_division(unit_a, unit_b), density=False)
                #if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by division with the unit '" + str(unit_b) + "'. This may not be the intention.")
                #return unit
                #unit = make_composite_division(unit_a, unit_b)

                if density is None: density = False
                else: density_strict = True

                #brightness = unit_a.is_brightness

                # Give warning
                if density: warnings.warn("Attempting creation of wavelength spectral density unit from bolometric unit")

            # Unit b is a frequency
            elif is_frequency(unit_b):

                #unit = PhotometricUnit(make_composite_division(unit_a, unit_b), density=False)
                #if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by division with the unit '" + str(unit_b) + "'. This may not be the intention.")
                #return unit
                #unit = make_composite_division(unit_a, unit_b)

                if density is None: density = False
                else: density_strict = True

                #brightness = unit_a.is_brightness

                # Give warning
                if density: warnings.warn("Attempting creation of frequency spectral density unit from bolometric unit")


            # Unit b contains a wavelength
            elif contains_wavelength(unit_b):

                #unit = parse_unit(make_composite_division(unit_a, unit_b), density=False)
                #try:
                #    if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by division with unit '" + str(unit_b) + "'. This may not be the intention.")
                #except AttributeError: pass
                #return unit
                #unit = make_composite_division(unit_a, unit_b)

                if density is None: density = False
                else: density_strict = True

                #brightness = unit_a.is_brightness

                # Give warning
                if density: warnings.warn("Attempting creation of wavelength spectral density unit from bolometric unit")

            # Contains a frequency
            elif contains_frequency(unit_b):

                #unit = parse_unit(make_composite_division(unit_a, unit_b), density=False)
                #try:
                #    if unit.density: warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + unit.physical_type + " by division with unit '" + str(unit_b) + "' . This may not be the intention.")
                #except AttributeError: pass
                #return unit
                #unit = make_composite_division(unit_a, unit_b)

                if density is None: density = False
                else: density_strict = True

                #brightness = unit_a.is_brightness

                # Give warning
                if density: warnings.warn("Attempting creation of frequency spectral density unit from bolometric unit")

            # Parse regularly
            else:

                #return parse_unit(make_composite_division(unit_a, unit_b))
                #unit = make_composite_division(unit_a, unit_b)

                #density = False
                #brightness = unit_a.is_brightness

                ## CANNOT BE SPECTRAL DENSITY
                # OOOORRRR: CAN IMPLY CONVERION TO NEUTRAL DENSITY
                if density is None: density = False
                else: density_strict = True

                # Give warning
                if density: warnings.warn("Attempting creation of neutral spectral density unit from bolometric unit")

        # Per pixel area
        if unit_a.is_per_angular_or_intrinsic_area:

            # divide by inverse area = multiply by area
            if is_inverse_area(unit):

                # Intrinsic surface brightness with distance dependence (flux) as well
                if unit_a.is_intrinsic_surface_brightness_with_distance:

                    if brightness is None: brightness = False  # guess result is Flux, not intrinsic surface brightness
                    else: brightness_strict = True

                # Can never be brightness
                else:

                    if brightness is True: raise ValueError("Cannot create surface brightness unit")
                    brightness = False
                    brightness_strict = True

            # divide by inverse solid angle = multiply by solid angle
            elif is_inverse_solid_angle(unit):

                # CAN NEVER BE BRIGHTNESS ANYMORE
                if brightness is True: raise ValueError("Cannot create surface brightness unit")
                brightness = False
                brightness_strict = True

            # Contains inverse area
            elif contains_inverse_area(unit):

                if brightness is None: brightness = False
                else: brightness_strict = True

            # Contains inverse solid angle
            elif contains_inverse_solid_angle(unit):

                if brightness is None: brightness = False
                else: brightness_strict = True

            # Else
            else:

                if brightness is None: brightness = unit_a.brightness
                else: brightness_strict = True

        # Not per pixel area
        else:

            # If unit b is a wavelength
            if is_area(unit_b):

                # Luminosity
                if unit_a.is_luminosity:

                    if brightness is None: brightness = False  # guess Flux
                    else: brightness_strict = True # anything is possible

                # Intensity
                elif unit_a.is_intensity:

                    #if brightness: raise ValueError("Cannot create surface brightness unit")
                    #brightness = False

                    if brightness is False: raise ValueError("Resulting unit must be surface brightness")
                    brightness = True
                    brightness_strict = True

                # Flux
                elif unit_a.is_flux:

                    if brightness is False: raise ValueError("Resulting unit must be surface brightness")
                    brightness = True
                    brightness_strict = True

                # Other
                else:

                    # Not photometric?
                    if brightness is True: raise ValueError("Cannot create photometric unit")
                    brightness = False
                    brightness_strict = True

            # Solid angle
            elif is_solid_angle(unit_b):

                # Luminosity
                if unit_a.is_luminosity:

                    # Result is intensity
                    if brightness is True: raise ValueError("Cannot create surface brightness")
                    brightness = False
                    brightness_strict = True

                elif unit_a.is_flux:

                    # Result is surface brightness
                    if brightness is False: raise ValueError("Resulting unit must be surface brightness")
                    brightness = True
                    brightness_strict = True

                else:

                    if brightness is True: raise ValueError("Cannot create surface brightness")
                    brightness = False
                    brightness_strict = True

            # Contains area
            elif contains_area(unit_b):

                # Luminosity
                if unit_a.is_luminosity:

                    if brightness is None: brightness = False # guess Flux
                    else: brightness_strict = True

                # Intensity
                elif unit_a.is_intensity:

                    if brightness is None: brightness = True
                    else: brightness_strict = True

                # Flux
                elif unit_a.is_flux:

                    if brightness is None: brightness = True
                    else: brightness_strict = True

                else:

                    # Not photometric?
                    if brightness is None: brightness = False
                    else: brightness_strict = True

            # Contains solid angle
            elif contains_solid_angle(unit_b):

                # Luminosity
                if unit_a.is_luminosity:

                    # Probably intensity
                    if brightness is None: brightness = False
                    else: brightness_strict = True

                # Flux
                elif unit_a.is_flux:

                    # Probably brightness
                    if brightness is None: brightness = True
                    else: brightness_strict = True

                else:

                    if brightness is None: brightness = False
                    else: brightness_strict = True

            # Other
            else:

                if brightness is None: brightness = False
                else: brightness_strict = True

    # Create the new unit
    new_unit = parse_unit(unit, density=density, brightness=brightness, density_strict=density_strict, brightness_strict=brightness_strict)
    #print(new_unit, type(new_unit))

    # Check conversion from bolometric to density or vice versa was made
    if unit_a.is_bolometric and isinstance(new_unit, PhotometricUnit) and new_unit.is_spectral_density:
        warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + new_unit.physical_type + " by division with unit '" + str(unit_b) + "'. This may not be the intention.")
    if unit_a.is_spectral_density and isinstance(new_unit, PhotometricUnit) and new_unit.is_bolometric:
        warnings.warn("A " + unit_a.physical_type + " unit is converted to a " + new_unit.physical_type + " by division with unit '" + str(unit_b) + "'. This may not be the intention.")

    # Return the new unit
    return new_unit

# -----------------------------------------------------------------

def same_physical_type(unit_a, unit_b):

    """
    This function ...
    :param unit_a:
    :param unit_b:
    :return:
    """

    return unit_a.physical_type == unit_b.physical_type

# -----------------------------------------------------------------
