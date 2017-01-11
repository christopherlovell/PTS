#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.data.attenuation Contains the AttenuationCurve class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np
from scipy import interpolate

# Import astronomical modules
from astropy.units import Unit, spectral
from astropy.table import Table

# Import the relevant PTS classes and modules
from ...core.tools import tables, introspection
from ...core.tools import filesystem as fs
from ..basics.curve import Curve

# -----------------------------------------------------------------

attenuation_data_path = fs.join(introspection.pts_dat_dir("core"), "attenuation")

# -----------------------------------------------------------------

class AttenuationCurve(Curve):

    """
    This class ...
    """

    @classmethod
    def initialize(cls, wavelengths=None, attenuations=None):

        """
        This function ...
        :param wavelengths:
        :param attenuations:
        :return:
        """

        # Units
        x_unit = "micron"

        # Names
        x_name = "Wavelength"
        y_name = "Attenuation"

        # Descriptions
        x_description = "Wavelength"
        y_description = "Attenuation"

        # Create the curve
        self = super(AttenuationCurve, cls).initialize(x_unit=x_unit, x_name=x_name, y_name=y_name, x_description=x_description, y_description=y_description)

        # Set the data
        if wavelengths is not None and attenuations is not None:

            # Add the data points
            for i in range(len(wavelengths)): self.add_point(wavelengths[i], attenuations[i])

    # -----------------------------------------------------------------

    @classmethod
    def from_seds(cls, total, transparent):

        """
        This function ...
        :param total:
        :param transparent:
        :return:
        """

        # Get the wavelengths
        wavelengths = total.wavelengths(unit="micron", add_unit=False)

        # Get the total and transparent fluxes
        total_fluxes = total.fluxes(asarray=True)
        transparent_fluxes = transparent.fluxes(asarray=True)

        # Calculate the attenuations
        attenuations = -2.5 * np.log10(total_fluxes / transparent_fluxes)

        # Create a new AttenuationCurve instance
        return cls(wavelengths, attenuations)

    # -----------------------------------------------------------------

    def wavelengths(self, unit=None, asarray=False, add_unit=True):

        """
        This function ...
        :param unit:
        :param asarray:
        :param add_unit:
        :return:
        """

        if asarray: return tables.column_as_array(self["Wavelength"], unit=unit)
        else: return tables.column_as_list(self["Wavelength"], unit=unit, add_unit=add_unit)

    # -----------------------------------------------------------------

    def attenuations(self, asarray=False):

        """
        This function ...
        :param asarray:
        :return:
        """

        if asarray: return tables.column_as_array(self["Attenuation"])
        else: return tables.column_as_list(self["Attenuation"])

    # -----------------------------------------------------------------

    def attenuation_at(self, wavelength):

        """
        This function ...
        :param wavelength:
        :return:
        """

        interpolated = interpolate.interp1d(self.wavelengths(unit="micron", asarray=True), self.attenuations(asarray=True), kind='linear')
        return interpolated(wavelength.to("micron").value)

    # -----------------------------------------------------------------

    def normalize_at(self, wavelength, value=1.):

        """
        This function ...
        :param wavelength:
        :param value:
        :return:
        """

        attenuation_wavelength = self.attenuation_at(wavelength)
        self["Attenuation"] /= attenuation_wavelength * value

# -----------------------------------------------------------------

class MilkyWayAttenuationCurve(AttenuationCurve):

    """
    This class ...
    """

    #def __init__(self, rv=None):
    @classmethod
    def initialize(cls):

        """
        This function ...
        :param rv: the value of R(V). If None, the mean Milky Way attenuation curve is generated. (See Fitzpatrick & Massa, 2007)
        """

        # Determine the path to the data file
        #path = fs.join(attenuation_data_path, "AttenuationLawMWRv5.dat")

        # Load the attenuation data
        #wavelengths_angstrom, alambda_av = np.loadtxt(path, unpack=True)

        # Convert wavelengths into micron
        #wavelengths = wavelengths_angstrom * 0.0001

        # Attenuations
        #attenuations = alambda_av

        wavelengths, attenuations = generate_milky_way_attenuations(0.1, 1000, 1000)

        # Call the constructor of the base class
        return super(MilkyWayAttenuationCurve, cls).initialize(wavelengths, attenuations)

# -----------------------------------------------------------------

class SMCAttenuationCurve(AttenuationCurve):

    """
    This class ...
    """

    # Determine the path to the data file
    path = fs.join(attenuation_data_path, "AttenuationLawSMC.dat")

    # -----------------------------------------------------------------

    #def __init__(self):
    @classmethod
    def initialize(cls):

        """
        This function ...
        """

        # Load the attenuation data
        wavelengths_angstrom, alambda_av = np.loadtxt(cls.path, unpack=True)

        # Convert wavelengths into micron
        wavelengths = wavelengths_angstrom * 0.0001

        # Attenuations
        attenuations = alambda_av

        # Call the constructor of the base class
        return super(SMCAttenuationCurve, cls).initialize(wavelengths, attenuations)

# -----------------------------------------------------------------

class CalzettiAttenuationCurve(AttenuationCurve):

    """
    This class ...
    """

    # Determine the path to the data file
    path = fs.join(attenuation_data_path, "AttenuationLawCalzetti.dat")

    # -----------------------------------------------------------------

    #def __init__(self):
    @classmethod
    def initialize(cls):

        """
        This function ...
        """

        # Load the attenuation data
        wavelengths_angstrom, alambda_av = np.loadtxt(cls.path, unpack=True)

        # Convert wavelengths into micron
        wavelengths = wavelengths_angstrom * 0.0001

        # Attenuations
        attenuations = alambda_av

        # Call the constructor of the base class
        return super(CalzettiAttenuationCurve, cls).initialize(wavelengths, attenuations)

# -----------------------------------------------------------------

class BattistiAttenuationCurve(AttenuationCurve):

    """
    This class ...
    """

    #def __init__(self):
    @classmethod
    def initialize(cls):

        """
        This function ...
        """

        # From Battisit et al. 2016

        wl_B16 = np.arange(0.125, 0.832, 0.01)
        x = 1. / wl_B16
        Qfit_B16 = -2.488 + 1.803 * x - 0.261 * x ** 2 + 0.0145 * x ** 3
        interpfunc = interpolate.interp1d(wl_B16, Qfit_B16, kind='linear')
        Qfit_B16_V = interpfunc(0.55)  # Interpolate to find attenuation at V band central wavelengths
        n_atts_B16 = Qfit_B16 / Qfit_B16_V

        wavelengths = wl_B16
        attenuations = Qfit_B16 + 1. # TODO: understand this more ...

        # Call the constructor of the base class
        return super(BattistiAttenuationCurve, cls).initialize(wavelengths, attenuations)

# -----------------------------------------------------------------

class MappingsAttenuationCurve(AttenuationCurve):

    """
    This class ...
    """

    path = fs.join(attenuation_data_path, "AttenuationLawMAPPINGS.dat")

    # -----------------------------------------------------------------

    #def __init__(self, attenuation, wavelength):
    @classmethod
    def initialize(cls, attenuation, wavelength):

        """
        This function ...
        """

        # Load the data
        # wl in micron from long to short wl.
        # ABS attenuations (see header of data file)
        wavelengths, abs_attenuations = np.loadtxt(cls.path, unpack=True)

        # CREATE A TABLE SO WE CAN EASILY SORT THE COLUMNS FOR INCREASING WAVELENGTH
        names = ["Wavelength", "ABS attenuation"]
        # Create the table
        abs_table = tables.new([wavelengths, abs_attenuations], names)
        abs_table["Wavelength"].unit = Unit("micron")
        # Sort the table on wavelength
        abs_table.sort("Wavelength")

        wavelengths = np.array(list(abs_table["Wavelength"]))
        abs_attenuations = np.array(list(abs_table["ABS attenuation"]))

        # Find the ABS attenuation at the specified wavelength
        interpolated = interpolate.interp1d(wavelengths, abs_attenuations, kind='linear')
        abs_wavelength = interpolated(wavelength.to("micron").value)

        # 'Real' attenuations
        attenuations_mappings = abs_attenuations / abs_wavelength * attenuation

        # Call the constructor of the base class
        return super(MappingsAttenuationCurve, cls).initialize(wavelengths, attenuations_mappings)

# -----------------------------------------------------------------

def generate_milky_way_attenuations(wavelength_min, wavelength_max, Nsamp):

    """
    This function ...
    :param wavelength_min:
    :param wavelength_max:
    :param Nsamp:
    :return:
    """

    # Parameter values from Fitzpatrick & Massa 2007, table 5.
    x0 = 4.592
    gamma = 0.922
    c1 = -0.175
    c2 = 0.807
    c3 = 2.991
    c4 = 0.319
    c5 = 6.097
    O1 = 2.055
    O2 = 1.322
    O3 = 0.0
    k_ir = 1.057
    Rv = 3.001

    wl_UV = np.logspace(np.log10(wavelength_min),np.log10(0.2700),Nsamp/2) # UV part stops at 0.27 micron
    wl_ir = np.logspace(np.log10(0.2700),np.log10(wavelength_max),Nsamp/2) # optical-IR part starts at 0.27 micron
    idx = (np.abs(wl_ir-0.550)).argmin() # index closest to V band = 0.55 micron
    idx_U2 = (np.abs(wl_UV-0.2700)).argmin() # index closest to U2 band = 0.27 micron
    idx_U1 = (np.abs(wl_UV-0.2600)).argmin() # index closest to U1 band = 0.26 micron

    # construct UV attenuation curve
    x = 1./wl_UV
    D = Lorentzian(x, x0, gamma)
    k_UV = np.zeros(Nsamp/2)

    for i in range(0,len(x)):
        if x[i] <= c5:
            k_UV[i] = c1 + c2*x[i] + c3*D[i]
        else:
            k_UV[i] = c1 + c2*x[i] + c3*D[i] + c4*(x[i]-c5)**2

    # construct ir attenuation curve
    sample_wl = np.array([10000., 4., 2., 1.3333, 0.5530, 0.4000, 0.3300, 0.2700, 0.2600])
    sample_k = np.append( k_ir*sample_wl[0:4]**-1.84 - Rv, [O3,O2,O1, k_UV[idx_U2], k_UV[idx_U1]])

    spline = interpolate.UnivariateSpline(1./sample_wl,sample_k)
    k_ir = spline(1./wl_ir)

    wl    = np.append(wl_UV,wl_ir)
    Al_Av = np.append(k_UV,k_ir)/Rv + 1.
    return wl, Al_Av

# -----------------------------------------------------------------

def Lorentzian(x, x0, gamma):

    """
    This function ...
    :param x:
    :param x0:
    :param gamma:
    :return:
    """

    return x*x / ((x*x-x0*x0)**2 + (x*gamma)**2)

# -----------------------------------------------------------------
