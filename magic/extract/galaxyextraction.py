#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.galaxyextraction Contains the GalaxyExtractor class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import math
import numpy as np
import matplotlib.pylab as plt

# Import astronomical modules
import astropy.units as u
import astropy.coordinates as coord
from astropy.coordinates import Angle
from astropy.visualization import SqrtStretch, LogStretch
from astropy.visualization.mpl_normalize import ImageNormalize

# Import the relevant AstroMagic classes and modules
from ..basics import Mask, Region, Position, Extent
from ..core import Source
from ..sky import Galaxy
from ..tools import catalogs, regions

# Import the relevant PTS classes and modules
from ...core.basics.configurable import Configurable
from ...core.tools import tables

# -----------------------------------------------------------------

class GalaxyExtractor(Configurable):

    """
    This class
    """

    def __init__(self, config=None):

        """
        The constructor ...
        """

        # Call the constructor of the base class
        super(GalaxyExtractor, self).__init__(config, "magic")

        # -- Attributes --

        # Initialize an empty list for the galaxies
        self.galaxies = []

        # Initialize an empty list to contain the manual sources
        self.manual_sources = []

        # Set the frame to None
        self.frame = None

        # The mask covering pixels that should be ignored throughout the entire extraction procedure
        self.input_mask = None

        # The galactic catalog
        self.catalog = None

        # The galactic statistics
        self.statistics = None

        # Set the mask to None
        self.mask = None

    # -----------------------------------------------------------------

    def run(self, frame, input_mask, catalog=None):

        """
        This function ...
        """

        # 1. Call the setup function
        self.setup(frame, input_mask, catalog)

        # 2. Find and remove the galaxies
        self.find_and_remove_galaxies()

        # 3. If a manual region was specified, remove the corresponding galaxies
        if self.config.manual_region is not None: self.set_and_remove_manual()

        # 4. Set the statistics
        self.set_statistics()

        # 5. Writing phase
        self.write()

    # -----------------------------------------------------------------

    def setup(self, frame, input_mask, catalog=None):

        """
        This function ...
        """

        # Call the setup function of the base class
        super(GalaxyExtractor, self).setup()

        # Inform the user
        self.log.info("Setting up the galaxy extractor ...")

        # Make a local reference to the frame and input mask
        self.frame = frame
        self.input_mask = input_mask
        self.catalog = catalog

        # Create a mask with shape equal to the shape of the frame
        self.mask = Mask(np.zeros_like(self.frame))

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Clearing the galaxy extractor ...")

        # Clear the list of galaxies
        self.galaxies = []

        # Clear the list of manual sources
        self.manual_sources = []

        # Clear the frame and the mask
        self.frame = None
        self.mask = None

    # -----------------------------------------------------------------

    def find_and_remove_galaxies(self):

        """
        This function ...
        :return:
        """

        # If no input catalog was given
        if self.catalog is None:

            # Get list of galaxies
            if self.config.fetching.use_catalog_file: self.import_catalog()
            else: self.fetch_catalog()

        # If an input catalog was given
        self.load_galaxies()

        # Find the sources
        self.find_sources()

        # Find apertures
        if self.config.find_apertures: self.find_apertures()

        # If requested, remove
        if self.config.remove: self.remove_galaxies()

    # -----------------------------------------------------------------

    def set_and_remove_manual(self):

        """
        This function ...
        :return:
        """

        # Set manual galaxies
        self.set_manual()

        # If requested, remove the manually specified galaxies
        if self.config.remove_manual: self.remove_manual()

    # -----------------------------------------------------------------

    @property
    def positions(self):

        """
        This function ...
        :return:
        """

        # Initialize a list to contain the object positions
        positions = []

        # Loop over the galaxies
        for galaxy in self.galaxies:

            # Calculate the pixel coordinate in the frame and add it to the list
            positions.append(galaxy.pixel_position(self.frame.wcs))

        # Return the list
        return positions

    # -----------------------------------------------------------------

    @property
    def principal(self):

        """
        This function ...
        :return:
        """

        # Loop over the list of galaxies
        for galaxy in self.galaxies:

            # Check if it is the principal galaxy; if so, return it
            if galaxy.principal: return galaxy

    # -----------------------------------------------------------------

    @property
    def companions(self):

        """
        This function ...
        :return:
        """

        # Initialize a list to contain the companion galaxies
        companions = []

        # Loop over the list of galaxies
        for galaxy in self.galaxies:

            # Check if it is a companion galaxy; if so, add it to the list
            if galaxy.companion: companions.append(galaxy)

        # Return the list of companion galaxies
        return companions

    # -----------------------------------------------------------------

    def find_sources(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Looking for sources near the galaxy positions ...")

        # Loop over all galaxies in the list
        for galaxy in self.galaxies:

            # If this sky object should be ignored, skip it
            if galaxy.ignore: continue

            # If requested, use the galaxy extents obtained from the catalog to create the source
            if self.config.detection.use_d25 and galaxy.has_extent:

                outer_factor = self.config.detection.background_outer_factor
                expansion_factor = self.config.detection.d25_expansion_factor
                galaxy.source_from_parameters(self.frame, outer_factor, expansion_factor)

            else:

                # Find a source
                try: galaxy.find_source(self.frame, self.config.detection)
                except Exception as e:
                    #import traceback
                    self.log.error("Error when finding source")
                    print(type(e))
                    print(e)
                    #traceback.print_exc()
                    if self.config.plot_track_record_if_exception:
                        if galaxy.has_track_record: galaxy.track_record.plot()
                        else: self.log.warning("Track record is not enabled")

            # If a source was not found for the principal or companion galaxies, force it
            outer_factor = self.config.detection.background_outer_factor
            if galaxy.principal and not galaxy.has_source: galaxy.source_from_parameters(self.frame, outer_factor)
            elif galaxy.companion and not galaxy.has_source and galaxy.has_extent: galaxy.source_from_parameters(self.frame, outer_factor)

        # Inform the user
        self.log.info("Found a source for {0} out of {1} objects ({2:.2f}%)".format(self.have_source, len(self.galaxies), self.have_source/len(self.galaxies)*100.0))

    # -----------------------------------------------------------------

    def import_catalog(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the catalog file
        path = self.full_input_path(self.config.fetching.catalog_path)

        # Inform the user
        self.log.info("Importing galaxy catalog from file " + path + " ...")

        # Load the catalog
        self.catalog = tables.from_file(path)

    # -----------------------------------------------------------------

    def load_galaxies(self):

        """
        This function creates the galaxy list from the galaxy catalog.
        :return:
        """

        # Inform the user
        self.log.info("Loading the galaxies from the catalog ...")

        # Get masks
        special_mask = self.special_mask
        ignore_mask = self.ignore_mask

        # Create the list of galaxies
        for i in range(len(self.catalog)):

            # Get the galaxy properties
            name = self.catalog["Name"][i]
            redshift = self.catalog["Redshift"][i] if not self.catalog["Redshift"].mask[i] else None
            galaxy_type = self.catalog["Type"][i] if not self.catalog["Type"].mask[i] else None
            distance = self.catalog["Distance"][i] * u.Mpc if not self.catalog["Distance"].mask[i] else None
            inclination = Angle(self.catalog["Inclination"][i], u.deg) if not self.catalog["Inclination"].mask[i] else None
            d25 = self.catalog["D25"][i] * u.arcmin if not self.catalog["D25"].mask[i] else None
            major = self.catalog["Major axis length"][i] * u.arcmin if not self.catalog["Major axis length"].mask[i] else None
            minor = self.catalog["Minor axis length"][i] * u.arcmin if not self.catalog["Minor axis length"].mask[i] else None
            position_angle = Angle(self.catalog["Position angle"][i], u.deg) if not self.catalog["Position angle"].mask[i] else None
            ra = self.catalog["Right ascension"][i]
            dec = self.catalog["Declination"][i]
            names = self.catalog["Alternative names"][i].split(", ") if not self.catalog["Alternative names"].mask[i] else []
            principal = self.catalog["Principal"][i]
            companions = self.catalog["Companion galaxies"][i].split(", ") if not self.catalog["Companion galaxies"].mask[i] else []
            parent = self.catalog["Parent galaxy"][i] if not self.catalog["Parent galaxy"].mask[i] else None

            # Create a SkyCoord instance for the galaxy center position
            position = coord.SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg), frame='fk5')

            # Create a new Galaxy instance
            galaxy = Galaxy(i, name, position, redshift, galaxy_type, names, distance, inclination, d25, major, minor, position_angle)

            # Calculate the pixel position of the galaxy in the frame
            pixel_position = galaxy.pixel_position(self.frame.wcs, self.config.transformation_method)

            # Set other attributes
            galaxy.principal = principal
            galaxy.companion = parent is not None
            galaxy.companions = companions
            galaxy.parent = parent

            # Enable track record if requested
            if self.config.track_record: galaxy.enable_track_record()

            # Set attributes based on masks (special and ignore)
            if special_mask is not None: galaxy.special = special_mask.masks(pixel_position)
            if ignore_mask is not None: galaxy.ignore = ignore_mask.masks(pixel_position)

            # If the input mask masks this star's position, skip it (don't add it to the list of stars)
            if self.input_mask is not None and self.input_mask.masks(pixel_position): continue

            # Add the new galaxy to the list
            self.galaxies.append(galaxy)

        # Debug messages
        self.log.debug(self.principal.name + " is the principal galaxy in the frame")
        self.log.debug("The following galaxies are its companions: " + str(self.principal.companions))

    # -----------------------------------------------------------------

    def fetch_catalog(self):

        """
        This function ...
        :param image:
        :param config:
        :return:
        """

        # Inform the user
        self.log.info("Fetching galaxy positions from an online catalog ...")

        # Create the galaxy catalog
        self.catalog = catalogs.create_galaxy_catalog(self.frame)

        # Inform the user
        self.log.debug("Number of galaxies: " + str(len(self.catalog)))

    # -----------------------------------------------------------------

    def find_apertures(self):

        """
        This function ...
        :param frame:
        :return:
        """

        # Inform the user
        self.log.info("Constructing elliptical apertures regions to encompass the detected galaxies ...")

        # Loop over all galaxies
        for galaxy in self.galaxies:

            # If this galaxy should be ignored, skip it
            if galaxy.ignore: continue

            # If the galaxy does not have a source, continue
            if galaxy.has_source: galaxy.find_aperture(self.frame, self.config.apertures)

    # -----------------------------------------------------------------

    def remove_galaxies(self):

        """
        This function ...
        :param image:
        :param galaxies:
        :param config:
        :return:
        """

        # Inform the user
        self.log.info("Removing the galaxies from the frame (except for the principal galaxy and its companions) ...")

        # Loop over all galaxies
        for galaxy in self.galaxies:

            # If this galaxy should be ignored, skip it
            if galaxy.ignore: continue

            # Remove the galaxy from the frame
            if not galaxy.principal and not galaxy.companion: galaxy.remove(self.frame, self.mask, self.config.removal)

        # Add the principal and companion galaxies to the mask
        self.mask += self.principal_mask
        self.mask += self.companion_mask

    # -----------------------------------------------------------------

    @property
    def special_mask(self):

        """
        This function ...
        :param path:
        :return:
        """

        # If no special region is defined
        if self.config.special_region is None: return None

        # Determine the full path to the special region file
        path = self.full_input_path(self.config.special_region)

        # Inform the user
        self.log.info("Setting special region from " + path + " ...")

        # Load the region and create a mask from it
        region = Region.from_file(path, self.frame.wcs)
        special_mask = Mask(region.get_mask(shape=self.frame.shape))

        # Return the mask
        return special_mask

    # -----------------------------------------------------------------

    @property
    def ignore_mask(self):

        """
        This function ...
        :param frame:
        :return:
        """

        # If no ignore region is defined
        if self.config.ignore_region is None: return None

        # Determine the full path to the ignore region file
        path = self.full_input_path(self.config.ignore_region)

        # Inform the user
        self.log.info("Setting region to ignore for subtraction from " + path + " ...")

        # Load the region and create a mask from it
        region = Region.from_file(path, self.frame.wcs)
        ignore_mask = Mask(region.get_mask(shape=self.frame.shape))

        # Return the mask
        return ignore_mask

    # -----------------------------------------------------------------

    def set_manual(self):

        """
        This function ...
        """

        # Determine the full path to the manual region file
        path = self.full_input_path(self.config.manual_region)

        # Inform the user
        self.log.info("Setting region for manual galaxy extraction from " + path + " ...")

        # Load the region and create a mask from it
        region = Region.from_file(path, self.frame.wcs)

        # Loop over the shapes in the region
        for shape in region:

            # Get the center and radius of the shape (can be a circle or an ellipse)
            x_center, y_center, x_radius, y_radius, angle = regions.ellipse_parameters(shape)

            # Create a source
            source = Source.from_ellipse(self.frame, Position(x_center, y_center), Extent(x_radius, y_radius), Angle(angle, u.deg), self.config.manual.background_outer_factor)

            # Add the source to the list of manual sources
            self.manual_sources.append(source)

    # -----------------------------------------------------------------

    def remove_manual(self):

        """
        This function ...
        """

        # Inform the user
        self.log.info("Removing manually specified galaxies from the frame ...")

        # Loop over each item in the list of manual sources
        for source in self.manual_sources:

            # Estimate the background for the source
            source.estimate_background(self.config.manual.interpolation_method, self.config.manual.sigma_clip)

            # Replace the frame in the appropriate area with the estimated background
            source.background.replace(self.frame, where=source.mask)

    # -----------------------------------------------------------------

    @property
    def principal_mask(self):

        """
        This function ...
        :return:
        """

        # Create a new mask with the dimensions of the frame
        mask = Mask(np.zeros_like(self.frame))

        # Add the principal galaxy's mask to the total mask
        mask[self.principal.source.cutout.y_slice, self.principal.source.cutout.x_slice] = self.principal.source.mask

        # Return the mask
        return mask

    # -----------------------------------------------------------------

    @property
    def companion_mask(self):

        """
        This function ...
        :return:
        """

        # Create a new mask with the dimension of the frame
        mask = Mask(np.zeros_like(self.frame))

        # Loop over all companion galaxies
        for galaxy in self.companions:

            # Check if the galaxy has a source and add its mask to the total mask
            if galaxy.has_source: mask[galaxy.source.cutout.y_slice, galaxy.source.cutout.x_slice] = galaxy.source.mask

        # Return the mask
        return mask

    # -----------------------------------------------------------------

    @property
    def region(self):

        """
        This function ...
        :param image:
        :param stars:
        :param config:
        :return:
        """

        # TODO: improve this function

        ra_list = []
        dec_list = []
        height_list = []
        width_list = []
        angle_list = []

        # Loop over all galaxies
        for galaxy in self.galaxies:

            ra_list.append(galaxy.position.ra.value)
            dec_list.append(galaxy.position.dec.value)

            if galaxy.major is not None:

                width = galaxy.major.to("arcsec").value

                if galaxy.minor is not None: height = galaxy.minor.to("arcsec").value
                else: height = width

            else:

                width = self.config.region.default_radius * self.frame.pixelscale.value
                height = self.config.region.default_radius * self.frame.pixelscale.value

            angle = galaxy.pa.degree if galaxy.pa is not None else 0.0

            height_list.append(height)
            width_list.append(width)
            angle_list.append(angle)

        # Create a region and return it
        return regions.ellipses(ra_list, dec_list, height_list, width_list, angle_list)

    # -----------------------------------------------------------------

    def set_statistics(self):

        """
        This function ...
        :return:
        """

        index_column = []
        have_source_column = []

        # Loop over all galaxies
        for galaxy in self.galaxies:

            index_column.append(galaxy.index)
            have_source_column.append(galaxy.has_source)

        # Create data structure and set column names
        data = [index_column, have_source_column]
        names = ["Galaxy index", "Detected"]

        # Create the statistics table
        self.statistics = tables.new(data, names)

    # -----------------------------------------------------------------

    def write_region(self):

        """
        This function ...
        :param frame:
        :return:
        """

        # Determine the full path to the region file
        path = self.full_output_path(self.config.writing.region_path)
        annotation = self.config.writing.region_annotation

        # Inform the user
        self.log.info("Writing galaxy region to " + path + " ...")

        # Create a file
        f = open(path, 'w')

        # Initialize the region string
        print("# Region file format: DS9 version 4.1", file=f)

        # Loop over all galaxies
        for galaxy in self.galaxies:

            # Get the center in pixel coordinates
            center = galaxy.pixel_position(self.frame.wcs)

            # Set the angle
            angle = galaxy.pa.degree if galaxy.pa is not None else 0.0

            if galaxy.major is None:

                color = "red"

                x_radius = self.config.region.default_radius
                y_radius = self.config.region.default_radius

            elif galaxy.minor is None or galaxy.pa is None:

                color = "green"

                x_radius = 0.5 * galaxy.major.to("arcsec").value / self.frame.pixelscale.value
                y_radius = x_radius

            else:

                color = "green"

                x_radius = 0.5 * galaxy.major.to("arcsec").value / self.frame.pixelscale.value
                y_radius = 0.5 * galaxy.minor.to("arcsec").value / self.frame.pixelscale.value

            # Annotation
            if annotation == "name": text = "text = {" + galaxy.name + "}"
            elif annotation == "redshift": text = "text = {" + str(galaxy.redshift) + "}"
            elif annotation == "type": text = "text = {" + str(galaxy.type) + "}"
            elif annotation is None: text = ""
            else: raise ValueError("Invalid option for annotation")

            color_suffix = " # color = " + color
            point_suffix = " # point = x " + text

            # Add point for the center
            print("image;point({},{})".format(center.x, center.y) + point_suffix, file=f)
            print("image;ellipse({},{},{},{},{})".format(center.x, center.y, x_radius, y_radius, angle) + color_suffix, file=f)

            # Add aperture
            if galaxy.has_aperture:

                ap_x_center, ap_y_center = galaxy.aperture.positions[0]
                major = galaxy.aperture.a
                minor = galaxy.aperture.b
                angle = galaxy.aperture.theta / math.pi * 180

                aperture_suffix = " # color = white"

                print("image;ellipse({},{},{},{},{})".format(ap_x_center, ap_y_center, major, minor, angle) + aperture_suffix, file=f)

        # Close the file
        f.close()

    # -----------------------------------------------------------------

    def write_catalog(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the catalog file
        path = self.full_output_path(self.config.writing.catalog_path)

        # Inform the user
        self.log.info("Writing galactic catalog to " + path + " ...")

        # Write the catalog to file
        tables.write(self.catalog, path)

    # -----------------------------------------------------------------

    def write_statistics(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the statistics file
        path = self.full_output_path(self.config.writing.statistics_path)

        # Inform the user
        self.log.info("Writing galactic statistics to " + path + " ...")

        # Write the statistics to file
        tables.write(self.statistics, path)

    # -----------------------------------------------------------------

    def write_masked_frame(self):

        """
        This function ...
        """

        # Determine the full path to the masked frame file
        path = self.full_output_path(self.config.writing.masked_frame_path)

        # Inform the user
        self.log.info("Writing masked frame to " + path + " ...")

        # Create a frame where the objects are masked
        frame = self.frame.copy()
        frame[self.mask] = float(self.config.writing.mask_value)

        # Write out the masked frame
        frame.save(path)

    # -----------------------------------------------------------------

    def write_cutouts(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the cutouts directory
        directory_path = self.full_output_path(self.config.writing.cutouts_path)

        # Inform the user
        self.log.info("Writing cutout boxes to " + directory_path + " ...")

        # Keep track of the number of stars encountered
        principals = 0
        companions = 0
        with_source = 0

        # Loop over all galaxies
        for galaxy in self.galaxies:

            # Check if this is the principal galaxy
            if galaxy.principal:

                # Save the cutout as a FITS file
                path = os.path.join(directory_path, "galaxy_principal_" + str(principals) + ".fits")
                galaxy.source.save(path)

                # Increment the counter of the number of principal galaxies (there should only be one, really...)
                principals += 1

            # Check if this is a companion galaxy
            elif galaxy.companion:

                # Save the cutout as a FITS file
                path = os.path.join(directory_path, "galaxy_companion_" + str(companions) + ".fits")
                galaxy.source.save(path)

                # Increment the counter of the number of companion galaxies
                companions += 1

            # Check if this galaxy has a source
            elif galaxy.has_source:

                # Save the cutout as a FITS file
                path = os.path.join(directory_path, "galaxy_source_" + str(principals) + ".fits")
                galaxy.source.save(path)

                # Increment the counter of the number of galaxies with a source
                with_source += 1

    # -----------------------------------------------------------------

    def write_result(self):

        """
        This function ...
        :return:
        """

        # Determine the full path to the resulting FITS file
        path = self.full_output_path(self.config.writing.result_path)

        # Inform the user
        self.log.info("Writing resulting frame to " + path + " ...")

        # Write out the resulting frame
        self.frame.save(path)

    # -----------------------------------------------------------------

    @property
    def have_source(self):

        """
        This function ...
        :return:
        """

        count = 0
        for galaxy in self.galaxies: count += galaxy.has_source
        return count

    # -----------------------------------------------------------------

    def catalog(self):

        """
        This function ...
        :return:
        """

        # Initialize empty lists for the table columns
        names = []
        redshifts = []
        types = []
        distances = []
        inclinations = []
        d25_list = []
        major_list = []
        minor_list = []
        position_angles = []
        right_ascensions = []
        declinations = []
        other_names_list = []
        principal_list = []
        companions_list = []
        parents = []

        # Loop over all galaxies
        for galaxy in self.galaxies:

            names.append(galaxy.name)
            redshifts.append(galaxy.redshift)
            types.append(galaxy.type)
            if galaxy.distance is not None: distances.append(galaxy.distance.value)
            else: distances.append(None)
            if galaxy.inclination is not None: inclinations.append(galaxy.inclination.degree)
            else: inclinations.append(None)
            if galaxy.d25 is not None: d25_list.append(galaxy.d25.value)
            else: d25_list.append(None)
            if galaxy.major is not None: major_list.append(galaxy.major.value)
            else: major_list.append(None)
            if galaxy.minor is not None: minor_list.append(galaxy.minor.value)
            else: minor_list.append(None)
            if galaxy.pa is not None: position_angles.append(galaxy.pa.degree)
            else: position_angles.append(None)
            right_ascensions.append(galaxy.position.ra.value)
            declinations.append(galaxy.position.dec.value)
            if galaxy.names is not None: other_names_list.append(" ".join(galaxy.names))
            else: other_names_list.append(None)
            principal_list.append(galaxy.principal)
            if galaxy.companions: companions_list.append(" ".join(galaxy.companions))
            else: companions_list.append(None)
            parents.append(galaxy.parent)

        # Create and return the table
        data = [names, redshifts, types, distances, inclinations, d25_list, major_list, minor_list, position_angles, right_ascensions, declinations, other_names_list, principal_list, companions_list, parents]
        names = ['Name', 'Redshift', 'Type', 'Distance', 'Inclination', 'D25', 'Major axis length', 'Minor axis length', 'Position angle', 'Right ascension', 'Declination', 'Alternative names', 'Principal', 'Companion galaxies', 'Parent galaxy']
        meta = {'name': 'stars'}
        table = tables.new(data, names, meta)

        # Set units
        table["Distance"].unit = "Mpc"
        table["Inclination"].unit = "deg"
        table["D25"].unit = "arcmin"
        table["Major axis length"].unit = "arcmin"
        table["Minor axis length"].unit = "arcmin"
        table["Position angle"].unit = "deg"
        table["Right ascension"].unit = "deg"
        table["Declination"].unit = "deg"

        # Return the catalog
        return table

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return:
        """

        x_centers = []
        y_centers = []
        apertures = []

        # Loop over all galaxies
        for galaxy in self.galaxies:

            x_center, y_center = galaxy.position.to_pixel(self.frame.wcs, mode=self.config.transformation_method)
            x_centers.append(x_center)
            y_centers.append(y_center)

            # If the galaxy does not have a source, continue
            if galaxy.has_aperture: apertures.append(galaxy.aperture)

        # Initialize the plot
        #norm = ImageNormalize(stretch=SqrtStretch())
        norm = ImageNormalize(stretch=LogStretch())
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Determine the maximum value in the box and the mimimum value for plotting
        vmax = np.max(self.frame)
        vmin = np.min(self.frame) if vmax <= 0 else 0.0

        # Plot the frame and the segments mask
        ax1.imshow(self.frame, origin='lower', interpolation='nearest', norm=norm, vmin=vmin, vmax=vmax)
        ax2.imshow(self.mask, origin='lower', cmap='jet')

        # Set axes limits
        plt.xlim(0, self.frame.xsize-1)
        plt.ylim(0, self.frame.ysize-1)

        # Plot the apertures
        for aperture in apertures:

            aperture.plot(color='white', lw=1.5, alpha=0.5, ax=ax1)
            aperture.plot(color='white', lw=1.5, alpha=1.0, ax=ax2)

        # Plot centers of the galaxies
        plt.plot(x_centers, y_centers, ls='none', color='white', marker='+', ms=40, lw=10, mew=4)

        # Show the plot
        plt.show()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # If requested, write out the galaxy catalog
        if self.config.write_catalog: self.write_catalog()

        # If requested, write out galaxy statistics
        if self.config.write_statistics: self.write_statistics()

        # If requested, write out the galaxy region
        if self.config.write_region: self.write_region()

        # If requested, write out the frame where the galaxies are masked
        if self.config.write_masked_frame: self.write_masked_frame()

        # If requested, write out the galaxy cutout boxes
        if self.config.write_cutouts: self.write_cutouts()

        # If requested, write out the result
        if self.config.write_result: self.write_result()

# -----------------------------------------------------------------
