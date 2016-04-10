#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.basics.sun Contains the Sun class

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy.units import Unit

# Import the relevant PTS classes and modules
from ..core.sed import IntrinsicSED
from ...core.tools import inspection, filesystem

# -----------------------------------------------------------------

# Determine the path to the Sun SED file
sun_sed_path = filesystem.join(inspection.skirt_repo_dir, "dat", "SED", "Sun", "SunSED.dat")

# -----------------------------------------------------------------

Lsun = 3.839e26 * Unit("W")                 # solar luminosity without solar neutrino radiation

# -----------------------------------------------------------------

# Effective wavelengths (in m)
eff_wavelengths = {"FUV": 152e-9 * Unit("m"),
                   "NUV": 231e-9 * Unit("m"),
                   "U": 365e-9 * Unit("m"),
                   "B": 445e-9 * Unit("m"),
                   "V": 551e-9 * Unit("m"),
                   "R": 658e-9 * Unit("m"),
                   "I": 806e-9 * Unit("m"),
                   "J": 1.22e-6 * Unit("m"),
                   "H": 1.63e-6 * Unit("m"),
                   "K": 2.19e-6 * Unit("m"),
                   "SDSS u": 354e-9 * Unit("m"),
                   "SDSS g": 477e-9 * Unit("m"),
                   "SDSS r": 623e-9 * Unit("m"),
                   "SDSS i": 763e-9 * Unit("m"),
                   "SDSS z": 913e-9 * Unit("m"),
                   "IRAC1": 3.56e-6 * Unit("m"),
                   "IRAC2": 4.51e-6 * Unit("m"),
                   "WISE1": 3.35e-9 * Unit("m"),
                   "WISE2": 4.60e-6 * Unit("m")}

# -----------------------------------------------------------------

#_LX_Wm = _LX_Lsun * Units::Lsun() * SunSED::solarluminosity(this, _ell);

class Sun(object):
    
    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        """

        # Load the intrinsic SED of the sun
        self.sed = IntrinsicSED.from_file(sun_sed_path, skiprows=4) # wavelength in micron, luminosity in W/micron

        # The total luminosity
        self.luminosity = Lsun

    # -----------------------------------------------------------------

    def luminosity_for_filter(self, filter, unit="W/micron"):

        """
        This function ...
        :param filter:
        :param unit:
        :return:
        """

        #luminosities = filter.integrate(self.sed["Wavelength"], self.sed["Luminosity"])

        luminosities = filter.convolve(self.sed["Wavelength"], self.sed["Luminosity"]) # also in W/micron

        return luminosities

# -----------------------------------------------------------------
