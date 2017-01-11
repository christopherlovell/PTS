#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sources.batchfinder Contains the SourceFinder class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from multiprocessing import Pool

# Import the relevant PTS classes and modules
from .extended import ExtendedSourceFinder
from .point import PointSourceFinder
from .other import OtherSourceFinder
from ..basics.mask import Mask
from ..tools import wavelengths
from ...core.basics.configurable import Configurable
from ...core.tools.logging import log
from ..core.dataset import DataSet
from ...core.tools import filesystem as fs
from ..region.list import SkyRegionList
from ..core.image import Image
from ...core.basics.table import SmartTable
from ..catalog.extended import ExtendedSourceCatalog
from ..catalog.point import PointSourceCatalog
from ..catalog.fetcher import CatalogFetcher
from .list import GalaxyList, StarList
from ..object.galaxy import Galaxy
from ..object.star import Star
from ...core.data.sed import ObservedSED
from ...core.basics.filter import Filter
from ...core.basics.curve import FilterCurve

# -----------------------------------------------------------------

class FWHMTable(FilterCurve):

    """
    This function ...
    """

    @classmethod
    def initialize(cls):

        """
        This function ...
        :return:
        """

        # Call the initialize function of the base class
        return super(FWHMTable, cls).initialize("FWHM", "FWHM of the PSF", "arcsec")

    # -----------------------------------------------------------------

    def add_fwhm(self, fltr, fwhm):

        """
        This function ...
        :param fltr:
        :param fwhm:
        :return:
        """

        self.add_point(fltr, fwhm)

    # -----------------------------------------------------------------

    def fwhm_for_filter(self, fltr):

        """
        This function ...
        :param fltr:
        :return:
        """

        return self.value_for_filter(fltr)

# -----------------------------------------------------------------

class GalaxyTable(SmartTable):

    """
    This class ...
    """

    column_info = [("Index", int, None, "index of the extended source in the catalog"),
                   ("Name", str, None, "name of the galaxy")]

    # -----------------------------------------------------------------

    @classmethod
    def initialize(cls, filters):

        """
        This function ...
        :param filters:
        :return:
        """

        # Loop over the filters
        for fltr in filters:

            column_name = str(fltr) + " flux"
            cls.column_info.append((column_name, float, "Jy", str(fltr) + " flux density"))

        # Call the initialize function of the base class
        return super(GalaxyTable, cls).initialize()

    # -----------------------------------------------------------------

    def add_galaxy(self, galaxy):

        """
        This function ...
        :param galaxy:
        :return:
        """

        values = []

        index = galaxy.index
        name = galaxy.name

        values.append(index)
        values.append(name)

        # Loop over the filters for which we need a flux
        for name in self.colnames:

            # Skip
            if not name.endswith("flux"): continue

            # Filter
            fltr = Filter.from_string(name.split(" flux")[0])

            # Get flux
            flux = galaxy.sed.flux_for_filter(fltr)

            # Add the flux to the values
            values.append(flux)

        # Add a row to the table
        self.add_row(values)

# -----------------------------------------------------------------

class StarTable(SmartTable):

    """
    This class ...
    """

    column_info = [("Index", int, None, "index of the point source in the catalog"),
                   ("Catalog", str, None, "original catalog"),
                   ("ID", str, None, "ID of the point source in the original catalog")]

    # -----------------------------------------------------------------

    @classmethod
    def initialize(cls, filters):

        """
        This function ...
        :param filters:
        :return:
        """

        # Loop over the filters
        for fltr in filters:

            column_name = str(fltr) + " FWHM"
            cls.column_info.append((column_name, float, "arcsec", str(fltr) + " FWHM"))

        # Loop over the filters
        for fltr in filters:

            column_name = str(fltr) + " flux"
            cls.column_info.append((column_name, float, "Jy", str(fltr) + " flux density"))

        # Call the initialize function of the base class
        return super(StarTable, cls).initialize()

    # -----------------------------------------------------------------

    def add_star(self, star):

        """
        This function ...
        :param star:
        :return:
        """

        values = []

        catalog = star.catalog
        id = star.id

        values.append(catalog)
        values.append(id)

        # Loop over the filters for which we need a FWHM
        for name in self.colnames:

            # FWHM
            if name.endswith("FWHM"):

                # Filter
                fltr = Filter.from_string(name.split(" FWHM")[0])

                fwhm = star.fwhms[name]


            # Flux
            elif name.endswith("flux"):

                # Filter
                fltr = Filter.from_string(name.split(" flux")[0])

                # Get flux
                flux = star.sed.flux_for_filter(fltr)

                # Add the flux to the values
                values.append(flux)

            else: continue

        self.add_row(values)

# -----------------------------------------------------------------

# FROM HELGA
# [A nearby galaxy] It is consequently contaminated by the light of thousands
# of foreground stars, especially in the UV and optical part
# of the spectrum. At longer wavelengths, the infrared emission of
# background galaxies becomes the main source of contaminating
# sources. At Herschel wavelengths, however, most of the emission
# from non-[the galaxy] point sources is negligible even at scales
# of the SPIRE 500 µm beam.
#
# The extended emission of the Milky Way Galactic Cirrus is prominently visible
# here. This dust emission can fortunately be associated with
# HI emission. Using the velocity information of HI maps, the
# Galactic cirrus can partly be disentangled from the emission of
# [the galaxy]. Paper I [of HELGA] goes into more detail about this technique.
#
# We made use of SExtractor v2.8.6 (Bertin & Arnouts 1996)
# to list the location of all point sources above a certain threshold
# (5 times the background noise level). The program simultaneously
# produces background maps that can be tweaked to represent
# the diffuse emission from M 31. In this way, we could
# replace the non-M 31 point sources with the local M 31 background
# value obtained from these maps.
#
# For each source an optimal radius was derived by comparing
# the pixel flux with the local background at increasing distance
# from the peak location. Once the pixel-to-background flux
# ratio dropped below 2, the radius was cut off at that distance.
# Based on this radius, a total flux was extracted in order to make
# colour evaluations. We constructed point source masks for the
# GALEX, SDSS, WISE, and Spitzer subsets based on different
# colour criteria.

# The GALEX and SDSS point sources were evaluated based
# on their UV colour. This technique was applied by Gil de Paz
# et al. (2007) for over 1000 galaxies and proved successful. In
# practice, we mask all sources with

# |FUV-NUV| > 0.75

# if they are detected at the 1σ level in their particular wavelength
# band. SExtractor identified 58 330 point sources in the UV fields,
# of which over 51 000 were masked in the FUV and NUV. Many
# point sources from the UV catalogue were not detected at optical
# bands, hence only 25 000 sources were masked in the SDSS
# bands. Around 7000 sources were identified as extragalactic.
# They were therefore assumed to belong to M 31 and were not
# masked.

# As an example, Fig. A.1 shows the u-band image of M 31
# before and after the mask was applied. The contamination of the
# image has been significantly reduced using the above technique.
# The point sources in the WISE and the Spitzer IRAC
# and MIPS frames were masked analogously, based on their

# IRAC colours (see below). At these wavelengths, however, the
# non-M 31 point sources are a mix of foreground stars and background
# galaxies. Furthermore, some bright sources may be associated
# with HII regions in M 31 and must not be masked. We designed
# a scheme based on the technique by Muñoz-Mateos et al.
# (2009b), which was successfully applied to the SINGS galaxies.
# Foreground stars have almost no PAH emission, while the diffuse
# ISM in galaxies shows a roughly constant F5.8/F8 ratio (Draine
# & Li 2007). Background galaxies are redshifted spirals or ellipticals
# and can consequently have a wide range in F5.8/F8. It is
# thus possible to construct a rough filter relying on the difference
# in MIR flux ratios. First, it was checked which point source extracted
# from the IRAC 3.6 µm had a non-detection at 8 µm. This
# riterion proved to be sufficient to select the foreground stars
# in the field. A second, colour-based, criterion disentangled the
# background galaxies from the HII regions:

# 0.29 < F5.8 / F8 < 0.85
# F3.6 / F5.8 < 1.58

# Figure A.2 shows the colour−colour diagram for these sources.
# The HII regions follow a more or less horizontal track at the
# lower-left part of the plot. The colour criteria for filtering out
# these HII regions were obtained empirically to ensure effective
# identification. Once identified, these star forming regions were
# consequently not masked. The resulting mask was applied to all
# IRAC and MIPS bands. Sources that were not detected at longer
# wavelengths were obviously not masked. Figure A.1 shows the
# IRAC 3.6 µm image of M 31 before and after the mask was applied.

# -----------------------------------------------------------------

class SourceFinder(Configurable):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(SourceFinder, self).__init__(config)

        # -- Attributes --

        # The process pool
        self.pool = None

        # The frames
        self.frames = dict()

        # The error maps
        self.error_maps = dict()

        # The masks
        self.special_masks = dict()
        self.ignore_masks = dict()

        # Downsampled images
        self.downsampled = None
        self.original_wcs = None

        # The catalog fetcher
        self.fetcher = CatalogFetcher()

        # The catalog of extended sources and the catalog of point sources
        self.extended_source_catalog = None
        self.point_source_catalog = None

        # Ignore images
        self.ignore = []
        self.ignore_stars = []
        self.ignore_other_sources = []

        # The regions covering areas that should be ignored throughout the entire extraction procedure
        self.special_region = None
        self.ignore_region = None

        # The name of the principal galaxy
        self.galaxy_name = None

        ### from the extended/point source finders

        # The tables
        self.extended_tables = dict()
        self.point_tables = dict()

        # The regions
        self.extended_regions = dict()
        self.point_regions = dict()
        self.saturation_regions = dict()
        self.other_regions = dict()

        # The segmentation maps
        self.segments = dict()

        ###

        ### The finished products:

        # The tables
        self.galaxy_table = None
        self.star_table = None

        # The regions
        self.galaxy_regions = None
        self.star_regions = None
        self.saturation_regions = None

        # The segmentation maps
        self.galaxy_segments = None
        self.star_segments = None

        ###

        # Settings for the star finder for different bands
        self.star_finder_settings = dict()

        # Extended sources and point source
        self.extended_sources = dict()
        self.point_sources = dict()

        # Galaxy and star lists
        self.galaxies = GalaxyList()
        self.stars = StarList()

        # The PSFs
        self.psfs = dict()

        # The statistics table
        self.statistics = None

        # The photometry table
        self.photometry = None

    # -----------------------------------------------------------------

    def add_frame(self, name, frame, star_finder_settings=None, error_map=None):

        """
        This function ...
        :param name:
        :param frame:
        :param star_finder_settings:
        :param error_map:
        :return:
        """

        # Check if name not already used
        if name in self.frames: raise ValueError("Already a frame with the name " + name)

        # Set the frame
        self.frames[name] = frame

        # If error map is given
        if error_map is not None: self.error_maps[name] = error_map

        # Set the settings
        if star_finder_settings is not None: self.star_finder_settings[name] = star_finder_settings

    # -----------------------------------------------------------------

    def add_error_map(self, name, error_map):

        """
        This function ...
        :param name:
        :param error_map:
        :return:
        """

        # Check if name in frames
        if name not in self.frames: raise ValueError("Frame with the name '" + name + "' has not been added")

        # Set the error map
        self.error_maps[name] = error_map

    # -----------------------------------------------------------------

    @property
    def min_pixelscale(self):

        """
        This function ...
        :return:
        """

        pixelscale = None

        # Loop over the images
        for name in self.frames:

            wcs = self.frames[name].wcs
            if pixelscale is None or wcs.average_pixelscale < pixelscale: pixelscale = wcs.average_pixelscale

        # Return the minimum pixelscale
        return pixelscale

    # -----------------------------------------------------------------

    @property
    def bounding_box(self):

        """
        This function ...
        :return:
        """

        # Region of all the bounding boxes
        boxes_region = SkyRegionList()

        # Add the bounding boxes as sky rectangles
        for name in self.frames: boxes_region.append(self.frames[name].wcs.bounding_box)

        # Return the bounding box of the region of rectangles
        return boxes_region.bounding_box

    # -----------------------------------------------------------------

    @property
    def filters(self):

        """
        This function ...
        :return:
        """

        return [frame.filter for frame in self.frames.values()]

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 3. Find the galaxies
        self.find_galaxies()
        
        # 3. Find the stars
        if self.config.find_stars: self.find_stars()

        # 4. Look for other sources
        if self.config.find_other_sources: self.find_other_sources()

        # 5. Perform the photometry
        #self.do_photometry()

        # Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(SourceFinder, self).setup(**kwargs)

        # Initialize the process pool
        self.pool = Pool(processes=self.config.nprocesses)

        # Load the images (from config or input kwargs)
        if "frames" in kwargs:
            self.frames = kwargs.pop("frames")
            if "error_maps" in kwargs: self.error_maps = kwargs.pop("error_maps")
        elif "dataset" in kwargs:
            dataset = kwargs.pop("dataset")
            self.frames = dataset.get_frames()
            self.error_maps = dataset.get_errormaps()
        else: self.load_frames()

        # Get the settings
        if "star_finder_settings" in kwargs: self.star_finder_settings = kwargs.pop("star_finder_settings")

        # Ignore certain images
        self.ignore = kwargs.pop("ignore", [])

        # Ignore stars in certain images
        self.ignore_stars = kwargs.pop("ignore_stars", [])

        # Ignore other sources in certain images
        self.ignore_other_sources = kwargs.pop("ignore_other_sources", [])

        # Load special region
        self.special_region = SkyRegionList.from_file(self.config.special_region) if self.config.special_region is not None else None

        # Load ignore region
        self.ignore_region = SkyRegionList.from_file(self.config.ignore_region) if self.config.ignore_region is not None else None

        # Create the masks
        self.create_masks()

        # Initialize images for the segmentation maps
        for name in self.frames: self.segments[name] = Image("segments")

        # DOWNSAMPLE ??

        # Initialize the galaxy segments
        self.galaxy_segments = Image("galaxies")

        # Initialize the star segments
        self.star_segments = Image("stars")

        # Initialize the galaxy table
        self.galaxy_table = GalaxyTable.initialize(self.filters)

        # Initialiee the star table
        self.star_table = StarTable.initialize(self.filters)

    # -----------------------------------------------------------------

    def load_frames(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the frame(s) ...")

        # Create new dataset
        if self.config.dataset.endswith(".fits"):

            # Load the image
            image = Image.from_file(self.config.dataset)

            # Determine the name for this image
            name = str(image.filter)

            # Add the primary frame
            self.add_frame(name, image.primary)

            # Add the error map
            if image.has_errors: self.add_error_map(name, image.errors)

        # Load dataset from file
        elif self.config.dataset.endswith(".dat"):

            # Get the dataset
            dataset = DataSet.from_file(self.config.dataset)

            # Get the frames
            self.frames = dataset.get_frames()

            # Get the error maps
            self.error_maps = dataset.get_errormaps()

        # Invalid value for 'dataset'
        else: raise ValueError("Parameter 'dataset' must be filename of a dataset file (.dat) or a FITS file (.fits)")

    # -----------------------------------------------------------------

    def create_masks(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the masks ...")

        # Special mask
        if self.special_region is not None:

            # Loop over the frames
            for name in self.frames:

                # Create the mask
                special_mask = Mask.from_region(self.special_region, self.frames[name].xsize, self.frames[name].ysize)

                self.special_masks[name] = special_mask

        # Ignore mask
        if self.ignore_region is not None:

            # Loop over the frames
            for name in self.frames:

                # Create the mask
                ignore_mask = Mask.from_region(self.ignore_region, self.frames[name].xsize, self.frames[name].ysize)

                self.ignore_masks[name] = ignore_mask

    # -----------------------------------------------------------------

    def find_galaxies(self):
        
        """
        This function ...
        """

        # Inform the user
        log.info("Finding the galaxies ...")

        # Fetch catalog of extended sources
        if self.config.extended_sources_catalog is not None: self.extended_source_catalog = ExtendedSourceCatalog.from_file(self.config.extended_sources_catalog)
        else: self.fetch_extended_sources_catalog()

        # Find extended sources
        self.find_extended_sources()

        # Make list of galaxies
        self.collect_galaxies()

        # Create galaxy table
        self.create_galaxy_table()

    # -----------------------------------------------------------------

    def fetch_extended_sources_catalog(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching catalog of extended sources ...")

        # Fetch the catalog
        self.extended_source_catalog = self.fetcher.get_extended_source_catalog(self.bounding_box)

    # -----------------------------------------------------------------

    def find_extended_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finding extended sources ...")

        # Dictionary to keep result handles
        results = dict()

        # Loop over the images
        for name in self.frames:

            # Ignore if requested
            if name in self.ignore: continue

            # Get the frame
            frame = self.frames[name]

            # Get masks
            special_mask = self.special_masks[name] if name in self.special_masks else None
            ignore_mask = self.ignore_masks[name] if name in self.ignore_masks else None
            bad_mask = None

            # Get configuration
            config = self.config.galaxies.copy()

            # Do the detection
            result = self.pool.apply_async(detect_extended_sources, args=(frame, self.extended_source_catalog, config, special_mask, ignore_mask, bad_mask,))
            results[name] = result

        # Process results
        for name in results:

            # Get result
            table, regions, segments = results[name].get()

            # Set galaxies
            self.extended_tables[name] = table

            # Set region list
            self.extended_regions[name] = regions

            # Set segmentation map
            # Add the segmentation map of the galaxies
            self.segments[name].add_frame(segments, "extended")

        # Close and join the process pool
        #self.pool.close()
        #self.pool.join()

    # -----------------------------------------------------------------

    def collect_galaxies(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Collecting galaxies ...")

        # Loop over the extended sources
        for index in range(len(self.extended_source_catalog)):

            # Get the galaxy position
            position = self.extended_source_catalog.get_position(index)

            # Create SED
            sed = ObservedSED()

            # Loop over the frames
            for name in self.frames:

                # Get the flux for this frame
                flux = self.extended_tables[name].get_flux(index)

                # Add the flux to the SED
                if flux is not None: sed.add_entry(self.frames[name].filter, flux)

            # Get other properties
            name = self.extended_source_catalog.get_name(index)
            redshift = self.extended_source_catalog.get_redshift(index)
            galaxy_type = self.extended_source_catalog.get_type(index)
            names = self.extended_source_catalog.get_names(index)
            distance = self.extended_source_catalog.get_distance(index)
            inclination = self.extended_source_catalog.get_inclination(index)
            d25 = self.extended_source_catalog.get_d25(index)
            major = self.extended_source_catalog.get_major(index)
            minor = self.extended_source_catalog.get_minor(index)
            posangle = self.extended_source_catalog.get_position_angle(index)
            principal = self.extended_source_catalog.is_principal(index)
            companions = self.extended_source_catalog.get_companions(index)
            parent = self.extended_source_catalog.get_parent(index)

            # Create the galaxy
            galaxy = Galaxy(index=index, position=position, sed=sed, name=name, redshift=redshift, galaxy_type=galaxy_type,
                            names=names, distance=distance, inclination=inclination, d25=d25, major=major, minor=minor,
                            position_angle=posangle, principal=principal, companions=companions, parent=parent)

            # Add the galaxy to the list
            self.galaxies.append(galaxy)

    # -----------------------------------------------------------------

    def create_galaxy_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the galaxy table ...")

        # Add the galaxies
        for galaxy in self.galaxies: self.galaxy_table.add_galaxy(galaxy)

    # -----------------------------------------------------------------

    def find_stars(self):
        
        """
        This function ...
        """

        # Inform the user
        log.info("Finding the stars ...")

        # Get catalog
        if self.config.point_sources_catalog is not None: self.point_source_catalog = PointSourceCatalog.from_file(self.config.point_sources_catalog)
        else: self.fetch_point_sources_catalog()

        # Find point sources
        self.find_point_sources()

        # Collect stars
        self.collect_stars()

        # Create the star table
        self.create_star_table()

    # -----------------------------------------------------------------

    def fetch_point_sources_catalog(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fetching catalog of point sources ...")

        # Get the coordinate box and minimum pixelscale
        coordinate_box = self.bounding_box
        min_pixelscale = self.min_pixelscale

        # Fetch
        self.point_source_catalog = self.fetcher.get_point_source_catalog(coordinate_box, min_pixelscale, self.config.stars.fetching.catalogs)

    # -----------------------------------------------------------------

    def find_point_sources(self):

        """
        This function ...
        :return:
        """

        # Dictionary to keep result handles
        results = dict()

        # Loop over the images
        for name in self.frames:

            # Ignore if requested
            if name in self.ignore: continue
            if name in self.ignore_stars: continue

            # Get the frame
            frame = self.frames[name]

            # Don't run the star finder if the wavelength of this image is greater than 25 micron
            if frame.wavelength is not None or frame.wavelength > wavelengths.ranges.ir.mir.max:

                # No star subtraction for this image
                log.info("Finding point sources will not be performed for the '" + name "' image")
                continue

            # Inform the user
            log.info("Finding the point sources ...")

            # Get masks
            special_mask = self.special_masks[name] if name in self.special_masks else None
            ignore_mask = self.ignore_masks[name] if name in self.ignore_masks else None
            bad_mask = None

            # Create configuration
            config = self.config.stars.copy()
            if name in self.star_finder_settings: config.set_items(self.star_finder_settings[name])

            # Do the detection
            result = self.pool.apply_async(detect_point_sources, args=(frame, self.galaxies, self.point_source_catalog, config, special_mask, ignore_mask, bad_mask,))
            results[name] = result

        # Process results
        for name in results:

            # Get result
            # stars, star_region_list, saturation_region_list, star_segments, kernel, statistics
            #stars, star_region_list, saturation_region_list, star_segments, kernel, statistics = results[name].get()
            table, regions, saturation_regions, segments = results[name].get()

            # Set table
            self.point_tables[name] = table

            # Set regions
            self.point_regions[name] = regions
            self.saturation_regions[name] = saturation_regions

            # Set segmentation map
            # Add the segmentation map of the galaxies
            self.segments[name].add_frame(segments, "point")

            # Set the PSF
            #self.psfs[name] = kernel

            # Get the statistics
            #self.statistics[name] = statistics

            # Show the FWHM
            #log.info("The FWHM that could be fitted to the point sources in the " + name + " image is " + str(self.statistics[name].fwhm))

        # Close and join the process pool
        self.pool.close()
        self.pool.join()

    # -----------------------------------------------------------------

    def collect_stars(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Collecting stars ...")

        # Loop over the point sources
        for index in range(len(self.point_source_catalog)):

            # Get the position of the point source
            position = self.point_source_catalog.get_position(index)

            # Create SED
            sed = ObservedSED()

            # Loop over the frames
            for name in self.frames:

                # Get the flux for this frame
                flux = self.point_tables[name].get_flux(index)

                # Add the flux to the SED
                if flux is not None: sed.add_entry(self.frames[name].filter, flux)

            # Check whether it can be identified as a star

            fuv = Filter.from_string("FUV")
            nuv = Filter.from_string("NUV")

            # Check the FUV-NUV colour
            fuv_nuv_colour = sed.colour(fuv, nuv)

            if abs(fuv_nuv_colour) < 0.75: continue # not a star

            #| FUV - NUV | > 0.75
            # if they are detected at the 1σ level in their particular wavelength
            # band.

            # IRAC colours (see below). At these wavelengths, however, the
            # non-M 31 point sources are a mix of foreground stars and background
            # galaxies. Furthermore, some bright sources may be associated
            # with HII regions in M 31 and must not be masked. We designed
            # a scheme based on the technique by Muñoz-Mateos et al.
            # (2009b), which was successfully applied to the SINGS galaxies.
            # Foreground stars have almost no PAH emission, while the diffuse
            # ISM in galaxies shows a roughly constant F5.8/F8 ratio (Draine
            # & Li 2007). Background galaxies are redshifted spirals or ellipticals
            # and can consequently have a wide range in F5.8/F8. It is
            # thus possible to construct a rough filter relying on the difference
            # in MIR flux ratios. First, it was checked which point source extracted
            # from the IRAC 3.6 µm had a non-detection at 8 µm. This
            # criterion proved to be sufficient to select the foreground stars
            # in the field. A second, colour-based, criterion disentangled the
            # background galaxies from the HII regions:

            irac_i1 = Filter.from_string("IRAC I1")
            irac_i3 = Filter.from_string("IRAC I3")
            irac_i4 = Filter.from_string("IRAC I4")

            # 0.29 < F5.8 / F8 < 0.85
            # F3.6 / F5.8 < 1.58

            i3_i4_colour = sed.colour(irac_i3, irac_i4)
            i1_i3_colour = sed.colour(irac_i1, irac_i3)

            if i3_i4_colour < 0.29: continue
            if i3_i4_colour > 0.85: continue

            if i1_i3_colour > 1.58: continue

            ###

            # Get other properties
            catalog = self.point_source_catalog.get_catalog(index)
            id = self.point_source_catalog.get_id(index)
            ra_error = self.point_source_catalog.get_ra_error(index)
            dec_error = self.point_source_catalog.get_dec_error(index)

            # Create FWHM table
            fwhms = FWHMTable.initialize()

            # Loop over the frames
            for name in self.frames:

                # Get the FWHM
                fwhm = self.point_tables[name].get_fwhm(index)

                # Add an entry to the FWHM table
                if fwhm is not None: fwhms.add_fwhm(self.frames[name].filter, fwhm)

            # Create the star object
            star = Star(index=index, position=position, sed=sed, catalog=catalog, id=id, ra_error=ra_error, dec_error=dec_error, fwhms=fwhms)

            # Add the star to the list
            self.stars.append(star)

    # -----------------------------------------------------------------

    def create_star_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the star table ...")

        # Loop over the stars
        for star in self.stars: self.star_table.add_star(star)

    # -----------------------------------------------------------------

    def find_other_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finding sources in the frame not in the catalog ...")

        # Dictionary to keep result handles
        results = dict()

        # Loop over the frames
        for name in self.frames:

            # Ignore if requested
            if name in self.ignore: continue
            if name in self.ignore_other_sources: continue

            # Get the frame
            frame = self.frames[name]

            # If the wavelength of this image is greater than 25 micron, don't classify the sources that are found
            #if frame.wavelength is not None and frame.wavelength > wavelengths.ranges.ir.mir.max: self.trained_finder.config.classify = False
            #else: self.trained_finder.config.classify = True

            # Get masks
            special_mask = self.special_masks[name] if name in self.special_masks else None
            ignore_mask = self.ignore_masks[name] if name in self.ignore_masks else None
            bad_mask = None

            # Create the configuration
            config = self.config.other_sources.copy()

            galaxies = self.galaxies

            # Get other input
            #galaxies = self.galaxies[name]
            stars = self.stars[name]
            galaxy_segments = self.segments[name].frames.galaxies
            star_segments = self.segments[name].frames.stars
            kernel = self.psfs[name]

            # Do the detection
            # frame, config, galaxies, stars, galaxy_segments, star_segments, kernel, special_mask, ignore_mask, bad_mask
            result = self.pool.apply_async(detect_other, args=(frame, config, galaxies, stars, galaxy_segments, star_segments, kernel, special_mask, ignore_mask, bad_mask,))
            results[name] = result

        # Process results
        for name in results:

            # Get the result
            region_list, segments = results[name].get()

            # Add the region
            self.other_regions[name] = region_list

            # Add the segmentation map of the other sources
            self.segments[name].add_frame(segments, "other")

        # Close and join the process pool
        self.pool.close()
        self.pool.join()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # 1. Write the catalogs
        self.write_catalogs()

        # 2. Write the tables
        self.write_tables()

        # 3. Write region lists
        self.write_regions()

        # 4. Write segmentation maps
        self.write_segments()

    # -----------------------------------------------------------------

    def write_catalogs(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing catalogs ...")

        # Write extended sources catalog
        self.write_extended_source_catalog()

        # Write point sources catalog
        self.write_point_source_catalog()

    # -----------------------------------------------------------------

    def write_extended_source_catalog(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the catalog of extended sources ...")

        # Write
        path = self.output_path_file("extended_sources.cat")
        self.extended_source_catalog.saveto(path)

    # -----------------------------------------------------------------

    def write_point_source_catalog(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the catalog of point sources ...")

        # Write
        path = self.output_path_file("point_sources.cat")
        self.point_source_catalog.saveto(path)

    # -----------------------------------------------------------------

    def write_tables(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing tables ...")

        # Write galaxy table
        self.write_galaxy_table()

        # Write star table
        self.write_star_table()

    # -----------------------------------------------------------------

    def write_galaxy_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing galaxy table ...")

        # Write
        path = self.output_path_file("galaxies.dat")
        self.galaxy_table.saveto(path)

    # -----------------------------------------------------------------

    def write_star_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing star table ...")

        # Write
        path = self.output_path_file("stars.dat")
        self.star_table.saveto(path)

    # -----------------------------------------------------------------

    def write_regions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the regions ...")

        # Write galaxy regions
        self.write_galaxy_regions()

        # Write star regions
        self.write_star_regions()

    # -----------------------------------------------------------------

    def write_galaxy_regions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the galaxy regions ...")

        # Determine the path
        path = self.output_path_file("galaxies.reg")

        # Save
        self.galaxy_regions.saveto(path)

    # -----------------------------------------------------------------

    def write_star_regions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the star regions ...")

        # Determine the path
        path = self.output_path_file("stars.reg")

        # Save
        self.star_regions.saveto(path)

    # -----------------------------------------------------------------

    def write_saturation_regions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the saturation regions ...")

        # Determine the path
        path = self.output_path_file("saturation_" + name + ".reg") if len(self.frames) > 1 else self.output_path_file("saturation.reg")

        # Save
        self.saturation_regions[name].to_pixel(self.frames[name].wcs).saveto(path)

    # -----------------------------------------------------------------

    def write_segments(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the segmentation maps ...")

        # Galaxy segments
        self.write_galaxy_segments()

        # Star segments
        self.write_star_segments()

    # -----------------------------------------------------------------

    def write_galaxy_segments(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the galaxy segments ...")

    # -----------------------------------------------------------------

    def write_star_segments(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the star segments ...")

# -----------------------------------------------------------------

def detect_extended_sources(frame, catalog, config, special_mask, ignore_mask, bad_mask):

    """
    This function ...
    :param frame:
    :param catalog:
    :param config:
    :param special_mask:
    :param ignore_mask:
    :param bad_mask:
    :return:
    """

    # Create the galaxy finder
    finder = ExtendedSourceFinder(config)

    # Run the finder
    finder.run(frame=frame, catalog=catalog, special_mask=special_mask, ignore_mask=ignore_mask, bad_mask=bad_mask)

    # Set the name of the principal galaxy
    # self.galaxy_name = self.galaxy_finder.principal.name

    # Get the galaxy region
    # galaxy_sky_region = self.galaxy_finder.finder.galaxy_sky_region
    # if galaxy_sky_region is not None:
    #    galaxy_region = galaxy_sky_region.to_pixel(image.wcs)

    if finder.regions is not None:

        galaxy_sky_regions = finder.regions.to_sky(frame.wcs)

        # if self.downsampled:
        #    sky_region = self.galaxy_sky_region
        #    return sky_region.to_pixel(self.original_wcs) if sky_region is not None else None
        # ele: return self.galaxy_finder.region

        # Get region list
        regions = galaxy_sky_regions

    else: regions = None

    if finder.segments is not None:

        # if self.galaxy_finder.segments is None: return None
        # if self.downsampled:

        #    segments = self.galaxy_finder.segments
        #    upsampled = segments.upsampled(self.config.downsample_factor, integers=True)
        #    upsampled.unpad(self.pad_x, self.pad_y)
        #    return upsampled

        # else: return self.galaxy_finder.segments

        # Get the segments
        segments = finder.segments

    else: segments = None

    # Get the source table
    table = finder.table

    # Inform the user
    log.success("Finished finding the extended sources for '" + frame.name + "' ...")

    # Return the output
    #return galaxies, region_list, segments

    # Return the source table, regions and segments
    return table, regions, segments

# -----------------------------------------------------------------

def detect_point_sources(frame, galaxies, catalog, config, special_mask, ignore_mask, bad_mask):

    """
    This function ...
    :param frame:
    :param galaxies:
    :param catalog:
    :param config:
    :param special_mask:
    :param ignore_mask:
    :param bad_mask:
    :return:
    """

    # Create the star finder
    finder = PointSourceFinder(config)

    # Run the finder
    finder.run(frame=frame, galaxies=galaxies, catalog=catalog, special_mask=special_mask, ignore_mask=ignore_mask, bad_mask=bad_mask)

    if finder.regions is not None:

        star_sky_region = finder.regions.to_sky(frame.wcs)

        # if self.downsampled:
        #    sky_region = self.star_sky_region
        #    return sky_region.to_pixel(self.original_wcs) if sky_region is not None else None
        # else: return self.star_finder.star_region

        regions = star_sky_region

    else: regions = None

    if finder.saturation_regions is not None:

        saturation_sky_region = finder.saturation_regions.to_sky(frame.wcs)

        # if self.downsampled:
        #    sky_region = self.saturation_sky_region
        #    return sky_region.to_pixel(self.original_wcs) if sky_region is not None else None
        # else: return self.star_finder.saturation_region

        saturation_regions = saturation_sky_region

    else: saturation_regions = None

    if finder.segments is not None:

        # if self.star_finder.segments is None: return None
        # if self.downsampled:
        #    segments = self.star_finder.segments
        #    upsampled = segments.upsampled(self.config.downsample_factor, integers=True)
        #    upsampled.unpad(self.pad_x, self.pad_y)
        #    return upsampled
        # else: return self.star_finder.segments

        segments = finder.segments

    else: segments = None

    # Set the stars
    #stars = finder.stars

    # Get the table
    table = finder.table

    # kernel = self.star_finder.kernel # doesn't work when there was no star extraction on the image, self.star_finder does not have attribute image thus cannot give image.fwhm
    # Set the kernel (PSF)
    #if finder.config.use_frame_fwhm and frame.fwhm is not None:
    #    fwhm = frame.fwhm.to("arcsec").value / frame.average_pixelscale.to("arcsec/pix").value
    #    sigma = fwhm * statistics.fwhm_to_sigma
    #    kernel = Gaussian2DKernel(sigma)
    #else: kernel = finder.kernel

    # Inform the user
    log.success("Finished finding the point sources for '" + frame.name + "' ...")

    # Return the output
    #return stars, star_region_list, saturation_region_list, star_segments, kernel, statistics

    # Return the source table, regions, saturation regions, and segments
    return table, regions, saturation_regions, segments

# -----------------------------------------------------------------

def detect_other(frame, config, galaxies, stars, galaxy_segments, star_segments, kernel, special_mask, ignore_mask, bad_mask):

    """
    This function ...
    :param frame:
    :param config:
    :param galaxies:
    :param stars:
    :param galaxy_segments:
    :param star_segments:
    :param kernel:
    :param special_mask:
    :param ignore_mask:
    :param bad_mask:
    :return:
    """

    # Create the other source finder
    finder = OtherSourceFinder(config)

    # Run the finder just to find sources
    finder.run(frame=frame, galaxies=galaxies, stars=stars, special_mask=special_mask,
                            ignore_mask=ignore_mask, bad_mask=bad_mask,
                            galaxy_segments=galaxy_segments,
                            star_segments=star_segments, kernel=kernel)

    if finder.region is not None:

        other_sky_region = finder.region.to_sky(frame.wcs)

        # if self.downsampled:
        #    sky_region = self.other_sky_region
        #    return sky_region.to_pixel(self.original_wcs) if sky_region is not None else None
        # else: return self.trained_finder.region

    else: other_sky_region = None

    if finder.segments is not None:

        # if self.trained_finder.segments is None: return None
        # if self.downsampled:
        #    segments = self.trained_finder.segments
        #    upsampled = segments.upsampled(self.config.downsample_factor, integers=True)
        #    upsampled.unpad(self.pad_x, self.pad_y)
        #    return upsampled
        # else: return self.trained_finder.segments

        other_segments = finder.segments

    else: other_segments = None

    # Inform the user
    log.success("Finished finding other sources for '" + frame.name + "' ...")

    # Return the output
    return other_sky_region, other_segments

# -----------------------------------------------------------------

# From: https://github.com/fred3m/astropyp/blob/master/astropyp/phot/calibrate.py

import numpy as np
from astropy.table import Table, join

def clip_color_outliers(color, ref_color, dbscan_kwargs={}, show_plots=True):

    """
    Use DBSCAN clustering to only select the points in color-color space
    that are part of the main cluster

    Parameters
    ----------
    color: array-like
        Array of instrumental colors
    ref_color: array-like
        Array of colors from a reference catalog
    dbscan_kwargs: dict
        Dictionary of keyword arguments to pass to DBSCAN. Typical
        parameters are 'eps', the maximum separation for points in a
        group and 'min_samples', the minimum number of points for a
        cluster to be grouped together. No kwargs are required.

    Returns
    -------
    idx: array
        Indices of points that are NOT outliers
    groups: array
        Group numbers. Outliers have group number ``-1``.
    labels: array
        Label for each point in color, ref_color with the group
        number that it is a member of
    """

    try:
        from sklearn.cluster import DBSCAN
    except ImportError:
        raise ImportError("You must have sklearn installed to clip outliers")

    coords = np.array([color, ref_color])
    coords = coords.T
    db = DBSCAN(**dbscan_kwargs).fit(coords)
    groups = np.unique(db.labels_)
    if show_plots:
        import matplotlib.pyplot as plt
        # for gid in groups:
        #    idx = gid==db.labels_
        #    plt.plot(color[idx],ref_color[idx], '.')
        idx = db.labels_ >= 0
        plt.plot(color[~idx], ref_color[~idx], 'r.')
        plt.plot(color[idx], ref_color[idx], '.')
        plt.title('Outliers in red')
        plt.xlabel('instrumental color')
        plt.ylabel('reference color')
        plt.show()

    idx = db.labels_ > -1
    return idx, groups, db.labels_

# -----------------------------------------------------------------

def calibrate_color(instr_color, airmass, a, b, k1, k2):

    """
    Transform colors to a different photometric system.
    See Landolt 2007 for more.
    """

    return a + b * (1 / (1 + k2 * airmass)) * (instr_color - k1 * airmass)

# -----------------------------------------------------------------

def calculate_color_coeffs(instr_color, ref_color, airmass, init_params):

    """
    Using the procedure in Landolt 2007 we adjust the colors to a set
    of reference colors.
    """

    from scipy.optimize import curve_fit

    def get_color(measurements, a, b, k1, k2):
        # Unpack the observations and call the calibrate_color function
        # (for consistency)
        instr_color, airmass = measurements
        return calibrate_color(instr_color, airmass, a, b, k1, k2)

    results = curve_fit(get_color, [instr_color, airmass], ref_color,
                        init_params)
    return results

# -----------------------------------------------------------------

def calibrate_magnitude(instr_mag, airmass, ref_color,
                        zero, extinct, color, instr=None):
    """
    Calibrate instrumental magnitude to a standard photometric system.
    This assumes that ref_color has already been adjusted for any
    non-linearities between the instrumental magnitudes and the
    photometric system. Otherwise use `~calibrate_magnitude_full`
    """
    if instr is None:
        result = instr_mag - extinct * airmass + zero + color * ref_color
    else:
        result = instr * (instr_mag - extinct * airmass) + zero + color * ref_color
    return result

# -----------------------------------------------------------------

def calibrate_magnitude_full(instr_mag, airmass, instr_color,
                             a, b, k1, k2, zero, extinct, color, instr=None):
    """
    Using the transformation in Landolt 2007, calibrate an instrumental
    magnitude to a photometric standard.
    """
    adjusted_color = calibrate_color(instr_color, airmass, a, b, k1, k2)
    result = calibrate_magnitude(instr_mag, airmass, adjusted_color,
                                 zero, extinct, color, instr)
    return result

# -----------------------------------------------------------------

def calculate_izY_coeffs(instr_mag, instr_color, airmass,
                         ref_mag, ref_color, dbscan_kwargs={}, show_plots=True,
                         color_init_params=None, mag_init_params=None, cluster=True):
    """
    Use the procedure from Landolt 2007 to calibrate to a given
    standard catalog (including adjusting the instrumental colors to the
    standard catalog colors).
    """
    from scipy.optimize import curve_fit

    def get_mag(measurements, zero, extinct, color, instr=None):
        instr_mag, airmass, ref_color = measurements
        result = calibrate_magnitude(instr_mag, airmass, ref_color,
                                     zero, extinct, color, instr)
        return result

    # Calculate the coefficients to adjust to the standard colors
    if color_init_params is None:
        color_init_params = [2., 1., .1, .1]

    if cluster:
        idx, groups, labels = clip_color_outliers(
            instr_color, ref_color, dbscan_kwargs, show_plots)
        color_result = calculate_color_coeffs(
            instr_color[idx], ref_color[idx], airmass[idx], color_init_params)
    else:
        color_result = calculate_color_coeffs(
            instr_color, ref_color, airmass, color_init_params)
    a, b, k1, k2 = color_result[0]
    adjusted_color = calibrate_color(instr_color, airmass, a, b, k1, k2)

    if show_plots:
        import matplotlib.pyplot as plt
        for am in np.unique(airmass):
            aidx = airmass[idx] == am
            x = np.linspace(np.min(instr_color[idx][aidx]),
                            np.max(instr_color[idx][aidx]), 10)
            y = calibrate_color(x, am, a, b, k1, k2)
            plt.plot(instr_color[idx][aidx], ref_color[idx][aidx],
                     '.', alpha=.1)
            plt.plot(x, y, 'r')
            plt.title('Airmass={0:.2f}'.format(am))
            plt.xlabel('Instrumental Color')
            plt.ylabel('Reference Color')
            plt.show()
        plt.plot(adjusted_color, ref_color, '.', alpha=.1)
        plt.title('Calibrated Color')
        plt.xlabel('Adjusted Color')
        plt.ylabel('Standard Color')
        plt.axis('equal')
        plt.show()

    # Fit the coefficients
    measurements = [instr_mag, airmass, adjusted_color]
    if mag_init_params is None:
        mag_init_params = [25., .1, .1]
    mag_result = curve_fit(get_mag, measurements, ref_mag, mag_init_params)
    # Package the results
    if len(mag_result[0]) == 3:
        zero, extinct, color = mag_result[0]
        instr = None
    else:
        zero, extinct, color, instr = mag_result[0]
    results = color_result[0].tolist() + mag_result[0].tolist()

    if show_plots:
        mag = calibrate_magnitude_full(instr_mag, airmass, instr_color,
                                       a, b, k1, k2, zero, extinct, color, instr)
        diff = mag - ref_mag
        rms = np.sqrt(np.mean(diff) ** 2 + np.std(diff) ** 2)
        plt.plot(mag, diff, '.', alpha=.1)
        plt.title('Calibrated magnitudes, rms={0:.4f}'.format(rms))
        plt.ylim([-.15, .15])
        plt.xlabel('mag')
        plt.ylabel('diff from standard')
        plt.show()
    return results, color_result[1], mag_result[1]

# -----------------------------------------------------------------

def calculate_coeffs_by_frame(instr_mag, instr_color, airmass,
                              ref_mag, ref_color, catalog_frame, frames,
                              dbscan_kwargs={}, color_init_params=None,
                              mag_init_params=[25., .1, .1], show_plots=True):
    """
    Calculate coefficients to transform instrumental magnitudes
    to a standard photometric catalog individually for each frame.
    """
    # Clip outliers from the entire catalog
    idx, groups, labels = clip_color_outliers(
        instr_color, ref_color, dbscan_kwargs, show_plots)
    mag = np.zeros((np.sum(idx),))
    mag[:] = np.nan

    # Create a table to hold the coefficients
    frame_count = len(frames)
    a = np.zeros((frame_count,), dtype=float)
    b = np.zeros((frame_count,), dtype=float)
    k1 = np.zeros((frame_count,), dtype=float)
    k2 = np.zeros((frame_count,), dtype=float)
    zero = np.zeros((frame_count,), dtype=float)
    color = np.zeros((frame_count,), dtype=float)
    extinct = np.zeros((frame_count,), dtype=float)
    instr = np.zeros((frame_count,), dtype=float)
    frame_coeff = np.zeros((frame_count,), dtype='S4')

    # For each frame calculate the coefficients
    for n, frame in enumerate(frames):
        fidx = catalog_frame[idx] == frame
        result = calculate_izY_coeffs(
            instr_mag[idx][fidx], instr_color[idx][fidx], airmass[idx][fidx],
            ref_mag[idx][fidx], ref_color[idx][fidx],
            dbscan_kwargs, show_plots=False, cluster=False,
            color_init_params=color_init_params,
            mag_init_params=mag_init_params)
        if len(mag_init_params) == 3:
            a[n], b[n], k1[n], k2[n], zero[n], extinct[n], color[n] = result[0]
        else:
            a[n], b[n], k1[n], k2[n], zero[n], extinct[n], color[n], instr[n] = result[0]
        frame_coeff[n] = frame
    # Build the table
    if len(mag_init_params) == 3:
        result = Table([a, b, k1, k2, zero, extinct, color, frame_coeff],
                       names=('a', 'b', 'k1', 'k2', 'zero', 'extinct', 'color', 'frame'))
    else:
        result = Table([a, b, k1, k2, zero, extinct, color, instr, frame_coeff],
                       names=('a', 'b', 'k1', 'k2', 'zero', 'extinct', 'color', 'instr', 'frame'))
    return result

# -----------------------------------------------------------------

def calibrate_photometry_by_frame(instr_mag, instr_color, airmass,
                                  catalog_frame, coeffs):
    """
    Transform instrumental magnitudes to a standard photometric
    catalog using different coefficients for each frame
    """
    catalog = Table([catalog_frame, np.arange(len(instr_mag), dtype=int)],
                    names=('frame', 'index'))
    joint_tbl = join(catalog, coeffs)
    joint_tbl.sort('index')
    if 'instr' in coeffs.columns.keys():
        mag = calibrate_magnitude_full(
            instr_mag, airmass, instr_color,
            joint_tbl['a'], joint_tbl['b'], joint_tbl['k1'],
            joint_tbl['k2'], joint_tbl['zero'],
            joint_tbl['extinct'], joint_tbl['color'],
            joint_tbl['instr'])
    else:
        mag = calibrate_magnitude_full(
            instr_mag, airmass, instr_color,
            joint_tbl['a'], joint_tbl['b'], joint_tbl['k1'],
            joint_tbl['k2'], joint_tbl['zero'],
            joint_tbl['extinct'], joint_tbl['color'])
    return mag

# -----------------------------------------------------------------

def find_star_in_list(stars, index):

    """
    This function ...
    :param stars:
    :param index:
    :return:
    """

    for star in stars:

        if star.index == index: return star

    return None

# -----------------------------------------------------------------
