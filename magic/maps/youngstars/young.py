#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.maps.youngstars.young Contains the YoungStellarMapMaker class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ....core.tools.logging import log
from ....core.basics.configurable import Configurable
from ....core.filter.filter import parse_filter
from ....core.tools import sequences
from ...core.frame import Frame
from ...core.list import NamedFrameList

# -----------------------------------------------------------------

def make_map(fuv, fuv_atttenuation, old, factor):

    """
    This function ...
    :return: 
    """

    # Create the map maker
    maker = YoungStellarMapsMaker()

    # Set input
    factors = [factor]
    fuv_attenuations = {"standard": fuv_atttenuation}

    # Run the map maker
    maker.run(fuv=fuv, fuv_attenuations=fuv_attenuations, old=old, factors=factors)

    # Return the map
    return maker.single_map

# -----------------------------------------------------------------

def make_maps(fuv, fuv_attenuation, old, factors):

    """
    THis function ...
    :param fuv: 
    :param fuv_attenuation: 
    :param old: 
    :param factors: 
    :return: 
    """

    # Create the map maker
    maker = YoungStellarMapsMaker()

    # Set input
    fuv_attenuations = {"standard": fuv_attenuation}

    # Run the map maker
    maker.run(fuv=fuv, fuv_attenuations=fuv_attenuations, old=old, factors=factors)

    # Return the maps
    return maker.maps

# -----------------------------------------------------------------

class YoungStellarMapsMaker(Configurable):

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
        super(YoungStellarMapsMaker, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The input FUV and FUV error maps
        self.fuv = None
        #self.fuv_errors = None

        # Other input
        self.old = None
        self.fuv_attenuations = None
        self.factors = None

        # Origins
        self.old_origin = None
        self.fuv_attenuations_origins = None

        # The transparent FUV maps
        self.transparent = dict()

        # The maps
        self.maps = dict()

        # The origins
        self.origins = dict()

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Make the map of young stars
        self.make_maps()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(YoungStellarMapsMaker, self).setup(**kwargs)

        # Get input
        self.fuv = kwargs.pop("fuv")
        #self.fuv_errors = kwargs.pop("fuv_errors", None)
        self.old = kwargs.pop("old")
        self.fuv_attenuations = kwargs.pop("fuv_attenuations")

        # Get origins
        self.old_origin = kwargs.pop("old_origin", None)
        self.fuv_attenuations_origins = kwargs.pop("fuv_attenuations_origins", None)

        # Get already calculated maps
        self.maps = kwargs.pop("maps", dict())

        # Set factors
        self.factors = kwargs.pop("factors")

    # -----------------------------------------------------------------

    @property
    def has_origins(self):

        """
        This function ...
        :return: 
        """

        return self.old_origin is not None and self.fuv_attenuations_origins is not None

    # -----------------------------------------------------------------

    def make_maps(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the map of young non-ionizing stars ...")

        # Correct for internal attenuation
        self.correct_for_attenuation()

        # Subtract the contribution of old stars
        self.subtract_old_contribution()

    # -----------------------------------------------------------------

    def correct_for_attenuation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Correcting for attenuation ...")

        # attenuation = -2.5 log (total / transparent)

        # Loop over the different attenuation maps
        for name in self.fuv_attenuations:

            # Get the attenuation map
            attenuation = self.fuv_attenuations[name]

            # Uniformize the attenuation and FUV map
            frames = NamedFrameList(attenuation=attenuation, fuv=self.fuv)
            frames.convolve_and_rebin() # convolve and rebin

            # Calculate the transparent FUV flux
            exponent = frames["attenuation"] / 2.5
            transparent = Frame(frames["fuv"] * 10**exponent.data)

            # Set properties
            transparent.unit = self.fuv.unit
            transparent.wcs = frames.wcs
            transparent.pixelscale = frames.pixelscale
            transparent.distance = frames.distance
            transparent.psf_filter = frames.psf_filter
            transparent.fwhm = frames.fwhm

            # Set the corrected map
            self.transparent[name] = transparent

    # -----------------------------------------------------------------

    def subtract_old_contribution(self):

        """
        Thisnfunction ...
        :return:
        """

        # Inform the user
        log.info("Subtracting the old contribution ...")

        # Normalize the old stellar map
        normalized_old = self.old.normalized()

        # Loop over the transparent maps
        for name in self.transparent:

            # Get the transparent map
            transparent = self.transparent[name]

            # Loop over the different factors
            for factor in self.factors:

                # Determine name
                key = name + "__" + repr(factor)

                # Set the origins
                if self.has_origins:

                    # Set the origins
                    origins = self.fuv_attenuations_origins[name]
                    sequences.append_unique(origins, parse_filter("FUV"))
                    sequences.append_unique(origins, self.old_origin)
                    self.origins[key] = origins

                # Check whether a map is already present
                if key in self.maps:
                    log.warning("The " + key + " young stars map is already created: not creating it again")
                    continue

                # Calculate the non ionizing young stars map from the FUV data
                young_stars = make_corrected_fuv_map(transparent, normalized_old, factor)

                # Normalize
                young_stars.normalize()
                young_stars.unit = None

                # Add the attenuation map to the dictionary
                self.maps[key] = young_stars

    # -----------------------------------------------------------------

    @property
    def single_map(self):

        """
        This fucntion ...
        :return: 
        """

        if len(self.maps) != 1: raise ValueError("Not a single map")
        return self.maps[self.maps.keys()[0]]

# -----------------------------------------------------------------

def make_corrected_fuv_map(fuv, old, factor):

    """
    This function ...
    :param fuv:
    :param old:
    :param factor:
    :return:
    """

    # Inform the user
    log.info("Subtracting the old stellar contribution from the map of the FUV emission with a factor of " + str(factor) + "...")

    ## Subtract old stellar contribution from FUV and MIPS 24 emission

    # From the FUV and 24 micron maps we must subtract the diffuse radiation (old stellar contribution),
    # for this we typically use an exponential disk
    # (scale length determined by GALFIT)

    # Convert to same pixelscale and convolve to same resolution
    frames = NamedFrameList(fuv=fuv, old=old)
    frames.convolve_and_rebin()

    fuv = frames["fuv"]
    old = frames["old"]

    flux_fuv = fuv.sum()

    # typisch 20% en 35% respectievelijk

    total_contribution = factor * flux_fuv

    # Subtract the disk contribution to the FUV image
    new_fuv = fuv - total_contribution * old

    # Make sure all pixels of the disk-subtracted maps are larger than or equal to zero
    #new_fuv[new_fuv < 0.0] = 0.0

    # Set zero where low signal-to-noise ratio
    # new_fuv[self.fuv < self.config.non_ionizing_stars.fuv_snr_level*self.fuv_errors] = 0.0

    # Check unit and WCS
    new_fuv.unit = fuv.unit
    new_fuv.wcs = fuv.wcs

    # Check filter
    new_fuv.filter = "FUV"

    # Set other properties than unit and wcs
    new_fuv.pixelscale = frames.pixelscale
    new_fuv.psf_filter = frames.psf_filter
    new_fuv.fwhm = frames.fwhm
    new_fuv.distance = frames.distance

    # Return the new FUV frame
    return new_fuv

# -----------------------------------------------------------------
