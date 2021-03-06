#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.magic.sky.skysubtractor Contains the SkySubtractor class.

# -----------------------------------------------------------------

# Ensure Python 3 functionality
from __future__ import absolute_import, division, print_function

# Import standard modules
import io
import math
import imageio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy.interpolate import CloughTocher2DInterpolator as intp
from scipy.interpolate import SmoothBivariateSpline
from scipy.ndimage import zoom
from itertools import product
from scipy.interpolate import NearestNDInterpolator, interp2d

# Test
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.linear_model import LinearRegression
# from sklearn.pipeline import Pipeline

# Import astronomical modules
from astropy.visualization import SqrtStretch
from astropy.visualization.mpl_normalize import ImageNormalize
from photutils.background import Background2D
from photutils import SigmaClip
from photutils import SExtractorBackground
from astropy.modeling import models
from astropy.modeling.fitting import LevMarLSQFitter, LinearLSQFitter, SLSQPLSQFitter
from astropy import stats
from photutils.background import BkgZoomInterpolator, BkgIDWInterpolator
from photutils.background.core import MeanBackground, MedianBackground, ModeEstimatorBackground, MMMBackground, SExtractorBackground, BiweightLocationBackground
from photutils.background.core import StdBackgroundRMS, MADStdBackgroundRMS, BiweightMidvarianceBackgroundRMS
from photutils.utils import ShepardIDWInterpolator

# Import the relevant PTS classes and modules
from ..core.frame import Frame
from ..basics.mask import Mask
from ..core.detection import Detection
from ..basics.coordinate import PixelCoordinate, SkyCoordinate
from ..region.circle import PixelCircleRegion
from ..region.composite import PixelCompositeRegion
from ..region.list import PixelRegionList, SkyRegionList
from ..tools import plotting, statistics, fitting, plotting
from ...core.basics.configurable import Configurable
from ...core.basics.log import log
#from ...core.basics.distribution import Distribution
from ..misc import chrisfuncs
from ..core.mask import Mask as newMask
from ..core.cutout import CutoutMask
from ...core.basics.map import Map
from ...core.basics.configuration import save_mapping
from ...core.basics.distribution import Distribution
from ...core.plot.distribution import DistributionPlotter
from pts.core.tools.utils import lazyproperty
from ..region.list import load_as_pixel_region_list

# -----------------------------------------------------------------

estimation_methods = ["mean", "median", "polynomial", "pts", "photutils", "caapr"]

# -----------------------------------------------------------------

finishing_steps = ["mean", "median", "polynomial", "interpolation"]
interpolation_methods = ["griddata", "zoom", "IDW", "spline"]

# -----------------------------------------------------------------

estimators = ["mean", "median", "mode", "MMM", "sextractor", "biweight_location"]
noise_estimators = ["stddev", "MAD", "biweight_midvariance"]

# -----------------------------------------------------------------

class SkySubtractor(Configurable):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(SkySubtractor, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The image frame
        self.frame = None

        # The mask of sources
        self.sources_mask = None

        # The extra mask
        self.extra_mask = None

        # The principal shape
        self.principal_shape = None

        # The region of saturated stars
        self.saturation_region = None

        # The region of stars
        self.star_region = None

        # The animation
        self.animation = None

        # The sky region
        self.region = None

        # The output mask (combined input + bad mask + galaxy annulus mask + expanded saturation mask + sigma-clipping mask)
        self.mask = None

        # The output mask, but without sigma clipping
        self.mask_not_clipped = None

        # The estimated sky (a single floating point value or a Frame, depending on the estimation method)
        self.sky = None

        # The estimated sky noise
        self.noise = None

        # Relevant for when estimation method is 'photutils'
        self.phot_sky = None
        self.phot_rms = None
        #self.photutils_background = None
        #self.photutils_background_rms = None
        self.phot_background_mesh = None
        self.phot_background_rms_mesh = None

        # Relevant for when estimation method is 'pts'
        self.apertures_frame = None
        self.apertures_values_frame = None
        self.apertures_noise_frame = None
        self.apertures_mask = None

        # Aperture properties
        self.napertures = None
        self.aperture_radius = None
        self.aperture_centers = None
        self.aperture_values = None
        self.aperture_noise_values = None
        self.aperture_masks = None

        # The estimators
        self.estimator = None
        self.noise_estimator = None

        # The interpolator
        self.interpolator = None

        # The statistics
        self.statistics = None

        # Filled data
        self.filled_values = None
        self.filled_noise = None

        # Mesh info
        self.mesh = None

        # Photutils bkg
        self.photutils_bkg = None

        # The distributions
        self.distributions = Map()


        # Other
        self.phot_boundaries = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Create the sky region
        self.create_region()

        # 3. Create mask
        self.create_mask()

        # 4. Do an extra sigma-clipping step on the data
        if self.config.sigma_clip_mask: self.sigma_clip()

        # 5. Estimate the sky (and sky noise)
        self.estimate()

        # Set statistics
        self.set_statistics()

        # Create distributions
        self.create_distributions()

        # 9. Write
        if self.config.write: self.write()

        # 10. Plot
        if self.config.plot: self.plot()

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Clearing the sky subtractor ...")

        # Set default values for all attributes
        self.frame = None
        self.sources_mask = None
        self.extra_mask = None
        self.principal_shape = None
        self.saturation_region = None
        self.star_region = None
        self.animation = None
        self.mask = None
        self.sky = None
        self.noise = None
        self.phot_sky = None
        self.phot_rms = None
        self.apertures_frame = None
        self.apertures_values_frame = None
        self.apertures_noise_frame = None
        self.apertures_mask = None

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(SkySubtractor, self).setup(**kwargs)

        # Get the frame
        if "frame" in kwargs: self.frame = kwargs.pop("frame")
        elif self.config.image is not None: self.frame = Frame.from_file(self.config.image)
        else: raise ValueError("Frame must be given as input or image path should be set in configuration")

        # Get other required
        if "sources_mask" in kwargs: self.sources_mask = kwargs.pop("sources_mask")
        elif self.config.sources_mask_plane is not None:
            if self.config.image is None: raise ValueError("The image path has to be specified")
            self.sources_mask = Mask.from_file(self.config.image, plane=self.config.sources_mask_plane)

        # NOT REQUIRED ANYMORE?
        if "principal_shape" in kwargs: self.principal_shape = kwargs.pop("principal_shape")
        elif self.config.principal_shape_region is not None: self.principal_shape = load_as_pixel_region_list(self.config.principal_shape_region, self.frame.wcs)[0]

        # Get optional input
        self.extra_mask = kwargs.pop("extra_mask", None)
        self.saturation_region = kwargs.pop("saturation_region", None)
        self.star_region = kwargs.pop("star_region", None)
        self.animation = kwargs.pop("animation", None)

    # -----------------------------------------------------------------

    def create_region(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the sky region ...")

        # If the sky region has to be loaded from file
        if self.config.sky_region is not None:

            sky_region = SkyRegionList.from_file(self.config.sky_region)
            self.region = sky_region.to_pixel(self.frame.wcs)

        # If no region file is given by the user, create an annulus from the principal ellipse
        elif self.principal_shape is not None:

            # Create the sky annulus
            annulus_outer_factor = self.config.mask.annulus_outer_factor
            annulus_inner_factor = self.config.mask.annulus_inner_factor
            inner_shape = self.principal_shape * annulus_inner_factor
            outer_shape = self.principal_shape * annulus_outer_factor

            # Set include flag to false for the inner shape
            inner_shape.include = False

            # Create the annulus
            annulus = PixelCompositeRegion(outer_shape, inner_shape)

            # Create the sky region consisting of only the annulus
            self.region = PixelRegionList()
            self.region.append(annulus)

        #else: log.warning("No central region or sky regions have been defined")

    # -----------------------------------------------------------------

    @property
    def region_bounding_box(self):

        """
        This function ...
        :return: 
        """

        return self.region.bounding_box if self.region is not None else None

    # -----------------------------------------------------------------

    @property
    def region_x_min(self):

        """
        This function ...
        :return: 
        """

        return self.region.x_min if self.region is not None else None

    # -----------------------------------------------------------------

    @property
    def region_x_max(self):

        """
        This function ...
        :return: 
        """

        return self.region.x_max if self.region is not None else None

    # -----------------------------------------------------------------

    @property
    def region_y_min(self):

        """
        This function ...
        :return: 
        """

        return self.region.y_min if self.region is not None else None

    # -----------------------------------------------------------------

    @property
    def region_y_max(self):

        """
        This function ...
        :return: 
        """

        return self.region.y_max if self.region is not None else None

    # -----------------------------------------------------------------

    @lazyproperty
    def outside_mask(self):

        """
        This function ...
        :return:
        """

        # If region is defined
        if self.region is not None:

            # Create a mask from the pixels outside of the sky region
            outside_mask = self.region.to_mask(self.frame.xsize, self.frame.ysize).inverse()
            #masks.append(outside_mask)
            return outside_mask

        # Region not defined
        else: return None

    # -----------------------------------------------------------------

    @lazyproperty
    def principal_mask(self):

        """
        This function ...
        :return:
        """

        # If principal shape is provided
        if self.principal_shape is not None:

            # Create a mask from the principal shape
            principal_mask = self.principal_shape.to_mask(self.frame.xsize, self.frame.ysize)
            #masks.append(principal_mask)
            return principal_mask

        # Principal shape not defined
        else: return None

    # -----------------------------------------------------------------

    @lazyproperty
    def saturation_mask(self):

        """
        This function ...
        :return:
        """

        # Check whether saturation contours are defined
        if self.saturation_region is not None:

            # Expand all contours
            expanded_region = self.saturation_region * self.config.mask.saturation_expansion_factor

            # Create the saturation mask
            saturation_mask = expanded_region.to_mask(self.frame.xsize, self.frame.ysize)
            #self.mask += saturation_mask

            return saturation_mask

        # Saturation region is not provided
        else: return None

    # -----------------------------------------------------------------

    @lazyproperty
    def stars_mask(self):

        """
        This function ...
        :return: 
        """

        # If star region is defined
        if self.star_region is not None:

            # Expand
            expanded_region = self.star_region * self.config.mask.stars_expansion_factor

            # Create the mask
            stars_mask = expanded_region.to_mask(self.frame.xsize, self.frame.ysize)

            # Return the mask
            return stars_mask

        # Star region not provided
        else: return None

    # -----------------------------------------------------------------

    def create_mask(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the sky mask ...")

        # Initialize a list to contain the mask contributions
        masks = []

        # Add sources mask
        masks.append(self.sources_mask)

        # Add outside mask
        if self.outside_mask is not None: masks.append(self.outside_mask)

        # Add principal mask
        if self.principal_mask is not None: masks.append(self.principal_mask)

        # Add saturation mask
        if self.saturation_mask is not None: masks.append(self.saturation_mask)

        # Add stars mask
        if self.stars_mask is not None: masks.append(self.stars_mask)

        # Add the extra mask (if specified)
        if self.extra_mask is not None: masks.append(self.extra_mask)

        # NEW
        self.mask = newMask.union(*masks)

        # Save as the unclipped mask
        self.mask_not_clipped = self.mask

    # -----------------------------------------------------------------

    def sigma_clip(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Performing sigma-clipping on the pixel values ...")

        # Create the sigma-clipped mask
        self.mask = statistics.sigma_clip_mask(self.frame, self.config.sigma_clipping.sigma_level, self.mask, self.config.sigma_clipping.niterations)

    # -----------------------------------------------------------------

    def estimate(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky ...")

        # Estimate the sky by taking the mean value of all pixels that are not masked
        if self.config.estimation.method == "mean": self.estimate_sky_mean()

        # Estimate the sky by taking the median value of all pixels that are not masked
        elif self.config.estimation.method == "median": self.estimate_sky_median()

        # The sky should be estimated by fitting a polynomial function to the pixels
        elif self.config.estimation.method == "polynomial": self.estimate_sky_polynomial()

        # Use photutils to estimate the sky and sky noise
        elif self.config.estimation.method == "photutils": self.estimate_sky_photutils()

        # Use our own method to estimate the sky and sky noise
        elif self.config.estimation.method == "pts": self.estimate_sky_pts()

        # Use the CAAPR method
        elif self.config.estimation.method == "caapr": self.estimate_caapr()

        # Unkown sky estimation method
        else: raise ValueError("Unknown sky estimation method: '" + self.config.estimation.method + "'")

    # -----------------------------------------------------------------

    def estimate_sky_mean(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky by calculating the mean value of all non-masked pixels ...")

        # Create a frame filled with the mean value
        self.sky = self.mean

        # Determine the global noise
        self.noise = self.stddev_subtracted

        # Debugging
        log.debug("The estimated sky value is " + str(self.sky))
        log.debug("The mean sky value after subtraction is " + str(self.mean_subtracted))
        log.debug("The median sky value after subtraction is " + str(self.median_subtracted))
        log.debug("The global noise is " + str(self.noise))

    # -----------------------------------------------------------------

    def estimate_sky_median(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky by calculating the median value of all non-masked pixels ...")

        # Create a frame filled with the median value
        self.sky = self.median

        # Determine the global noise
        self.noise = self.stddev_subtracted

        # Debugging
        log.debug("The estimated sky value is " + str(self.sky))
        log.debug("The mean sky value after subtraction is " + str(self.mean_subtracted))
        log.debug("The median sky value after subtraction is " + str(self.median_subtracted))
        log.debug("The global noise is " + str(self.noise))

    # -----------------------------------------------------------------

    def estimate_sky_polynomial(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky by fitting a polynomial function to all non-masked pixels ...")

        polynomial = fitting.fit_polynomial(self.frame, 3, mask=self.mask)

        # Evaluate the polynomial
        data = fitting.evaluate_model(polynomial, 0, self.frame.xsize, 0, self.frame.ysize)

        #plotting.plot_box(data, title="estimated sky")

        # Create sky map
        # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
        self.sky = Frame(data,
                         wcs=self.frame.wcs,
                         name="sky",
                         description="estimated sky",
                         unit=self.frame.unit,
                         zero_point=self.frame.zero_point,
                         filter=self.frame.filter,
                         sky_subtracted=False,
                         fwhm=self.frame.fwhm)

        # Set the noise
        self.noise = self.stddev_subtracted

        # Debugging
        log.debug("The mean sky value after subtraction is " + str(self.mean_subtracted))
        log.debug("The median sky value after subtraction is " + str(self.median_subtracted))
        log.debug("The global noise is " + str(self.noise))

    # -----------------------------------------------------------------

    def estimate_sky_photutils(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky and sky noise by using photutils ...")

        # Determine box size
        if self.config.estimation.photutils_fixed_width is not None: box_shape = (self.config.estimation.photutils_fixed_width, self.config.estimation.photutils_fixed_width)
        else:
            # Determine radius
            self.determine_aperture_radius()
            box_shape = (self.integer_aperture_diameter, self.integer_aperture_diameter)

        # Determine filter size
        filter_size = (self.config.estimation.photutils_filter_size, self.config.estimation.photutils_filter_size)

        exclude_mesh_percentile = 50.0

        # NEW NEW
        x_min = self.region_x_min
        x_max = self.region_x_max
        y_min = self.region.y_min
        y_max = self.region.y_max

        x_min = max(int(x_min), 0)
        x_max = min(int(x_max), self.frame.xsize)

        y_min = max(int(y_min), 0)
        y_max = min(int(y_max), self.frame.ysize)

        # Set the phot_boundaries
        self.phot_boundaries = dict()
        self.phot_boundaries["x_min"] = x_min
        self.phot_boundaries["x_max"] = x_max
        self.phot_boundaries["y_min"] = y_min
        self.phot_boundaries["y_max"] = y_max

        y_slice = slice(y_min, y_max)
        x_slice = slice(x_min, x_max)

        # NEW NEW: MAKE CUTOUT
        cutout = self.frame[y_slice, x_slice]

        # CUTOUT MASK
        mask_cutout = self.mask[y_slice, x_slice]

        # NEW
        # NO SIGMA CLIP BECAUSE WE HAVE ALREADY DONE THAT OURSELVES
        #sigma_clip = SigmaClip(sigma=3., iters=10)
        sigma_clip = None
        # bkg_estimator = MedianBackground()
        bkg_estimator = SExtractorBackground()
        try:
            bkg = Background2D(cutout, box_shape, filter_size=filter_size, sigma_clip=sigma_clip,
                               bkg_estimator=bkg_estimator, mask=mask_cutout, filter_threshold=None,
                               exclude_mesh_method="threshold",
                               exclude_mesh_percentile=exclude_mesh_percentile)
        except ValueError:

            plotting.plot_box(cutout)
            plotting.plot_mask(mask_cutout, title="mask")
            raise RuntimeError("Sky subtraction is not possible for this image")

        # Keep the background 2D object
        self.photutils_bkg = bkg

        # Masked background
        background = Frame.nans_like(self.frame)
        background[y_slice, x_slice] = bkg.background
        #masked_background = np.ma.masked_array(background, mask=mask_cutout.data)
        #plotting.plot_box(masked_background, title="masked background")
        background[y_slice, x_slice][mask_cutout] = np.NaN

        # Masked background rms
        background_rms = Frame.nans_like(self.frame)
        background_rms[y_slice, x_slice] = bkg.background_rms
        #masked_background_rms = np.ma.masked_array(background_rms, mask=mask_cutout.data)
        background_rms[y_slice, x_slice][mask_cutout] = np.NaN

        # Set as attributes
        #self.photutils_background = background
        #self.photutils_background_rms = background_rms

        #
        self.phot_background_mesh = Frame(bkg.background_mesh)
        self.phot_background_rms_mesh = Frame(bkg.background_rms_mesh)

        # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
        #self.phot_sky = Frame(bkg.background,
        #                       wcs=self.frame.wcs,
        #                       name="phot_sky",
        #                       description="photutils background",
        #                       unit=self.frame.unit,
        #                       zero_point=self.frame.zero_point,
        #                       filter=self.frame.filter,
        #                       sky_subtracted=False,
        #                       fwhm=self.frame.fwhm)

        # NEW NEW
        self.phot_sky = Frame.nans_like(self.frame) #wcs=self.frame.wcs,
        self.phot_sky.name = "phot_sky"
        self.phot_sky.description = "photutils background"
        self.phot_sky.unit = self.frame.unit
        self.phot_sky.zero_point=self.frame.zero_point
        self.phot_sky.filter=self.frame.filter
        self.phot_sky.sky_subtracted=False
        self.phot_sky.fwhm = self.frame.fwhm

        self.phot_sky[y_slice, x_slice] = bkg.background

        # data, wcs=None, name=None, description=None, unit=None, zero_point=None, filter=None, sky_subtracted=False, fwhm=None
        #self.phot_rms = Frame(bkg.background_rms,
        #                       wcs=self.frame.wcs,
        #                       name="phot_rms",
        #                       description="photutils rms",
        #                       unit=self.frame.unit,
        #                       zero_point=self.frame.zero_point,
        #                       filter=self.frame.filter,
        #                       sky_subtracted=False,
        #                       fwhm=self.frame.fwhm)

        self.phot_rms = Frame.nans_like(self.frame)
        #bkg.background_rms
        #wcs=self.frame.wcs
        self.phot_rms.name="phot_rms"
        self.phot_rms.description="photutils rms"
        self.phot_rms.unit=self.frame.unit
        self.phot_rms.zero_point=self.frame.zero_point
        self.phot_rms.filter=self.frame.filter
        self.phot_rms.sky_subtracted=False
        self.phot_rms.fwhm=self.frame.fwhm

        self.phot_rms[y_slice, x_slice] = bkg.background_rms

        ##

        # Use global values
        if self.config.estimation.photutils_global is not None:

            #mean_sky = np.ma.mean(masked_background)
            #median_sky = np.median(masked_background.compressed())

            mean_sky = np.nanmean(background.data)
            median_sky = np.nanmedian(background.data)

            # Median
            if self.config.estimation.photutils_global == "median":

                # Set sky level
                self.sky = median_sky

                # Set noise
                self.noise = np.nanmean(background_rms) #np.ma.mean(masked_background_rms)

            # Mean
            elif self.config.estimation.photutils_global == "mean":

                # Set sky level
                self.sky = mean_sky

                # Set noise
                self.noise = np.nanmean(background_rms) #np.ma.mean(masked_background_rms)

            # Invalid
            else: raise ValueError("Invalid option for 'photutils_global'")

            # Debugging
            log.debug("The estimated sky value is " + str(self.sky))
            log.debug("The mean value after subtraction is " + str(self.mean_subtracted))
            log.debug("The median value after subtraction is " + str(self.median_subtracted))
            log.debug("The standard deviation after subtraction is " + str(self.stddev_subtracted))
            log.debug("The estimated noise is " + str(self.noise))

        # Use frames
        else:

            # Set original photutils frames
            self.sky = self.phot_sky
            self.noise = self.phot_rms

            mean_sky = np.nanmean(self.sky)
            median_sky = np.nanmedian(self.sky)
            mean_noise = np.nanmean(self.noise)

            # Debugging
            log.debug("The mean of the sky frame is " + str(mean_sky))
            log.debug("The median of the sky frame is " + str(median_sky))
            log.debug("The mean of the sky noise frame is " + str(mean_noise))

            # Debugging
            log.debug("The mean value before subtraction is " + str(self.mean_frame))
            log.debug("The median value before subtraction is " + str(self.median_frame))
            log.debug("THe standard deviation before subtration is " + str(self.stddev_frame))

            # Debugging
            log.debug("The mean value before subtraction without sigma-clipping is " + str(self.mean_frame_not_clipped))
            log.debug("The median value before subtraction without sigma-clipping is " + str(self.median_frame_not_clipped))
            log.debug("The standard deviation before subtraction without sigma-clipping is " + str(self.stddev_frame_not_clipped))

            # Debugging
            log.debug("The mean value after subtraction is " + str(self.mean_subtracted))
            log.debug("The median value after subtraction is " + str(self.median_subtracted))
            log.debug("The standard deviation after subtraction is " + str(self.stddev_subtracted))

    # -----------------------------------------------------------------

    def estimate_sky_pts(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky and sky noise by randomly placing apertures ...")

        # 1. Determine the aperture radius
        self.determine_aperture_radius()

        # 2. Determine the number of apertures to use
        self.determine_number_of_apertures()

        # 3. Set the estimators
        self.set_estimators()

        # 4. Create the apertures
        self.create_apertures()

        # 5. Create aperture frames
        self.create_aperture_frames()

        # 6. Finish
        self.finish_sky()

    # -----------------------------------------------------------------

    def determine_aperture_radius(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the aperture radius ...")

        # Whether or not user has chosen this value
        if self.config.estimation.aperture_radius is not None: radius = self.config.estimation.aperture_radius
        else:

            # Check whether the FWHM is defined for the frame
            if self.frame.fwhm is None: raise RuntimeError("The FWHM of the frame is not defined: sky apertures cannot be generated")

            # Determine the radius for the sky apertures
            fwhm_pix = self.frame.fwhm_pix
            radius = self.config.estimation.aperture_fwhm_factor * fwhm_pix

        # Debugging
        log.debug("Using sky apertures with a radius of " + str(radius) + " pixels")

        # Set the aperture radius
        self.aperture_radius = radius

    # -----------------------------------------------------------------

    @lazyproperty
    def integer_aperture_radius(self):

        """
        This function ...
        :return:
        """

        return int(math.ceil(self.aperture_radius))

    # -----------------------------------------------------------------

    @lazyproperty
    def aperture_diameter(self):

        """
        This function ...
        :return:
        """

        return 2.0 * self.aperture_radius

    # -----------------------------------------------------------------

    @lazyproperty
    def integer_aperture_diameter(self):

        """
        This function ...
        :return:
        """

        return 2 * self.integer_aperture_radius

    # -----------------------------------------------------------------

    @lazyproperty
    def mesh_size(self):

        """
        This function ...
        :return:
        """

        return int(math.ceil(self.config.estimation.relative_mesh_scale * self.aperture_diameter))

    # -----------------------------------------------------------------

    @lazyproperty
    def mesh_area(self):

        """
        This function ...
        :return:
        """

        return self.mesh_size * self.mesh_size

    # -----------------------------------------------------------------

    @lazyproperty
    def aperture_area(self):

        """
        This function ...
        :return:
        """

        circle_area = np.pi * self.aperture_radius ** 2
        return circle_area

    # -----------------------------------------------------------------

    @lazyproperty
    def nunmasked_pixels(self):

        """
        This function ....
        :return:
        """

        # Determine the number of unmasked pixels
        npixels = np.sum(self.mask.inverse())
        return npixels

    # -----------------------------------------------------------------

    def determine_number_of_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Determining the number of apertures ...")

        # Assuming optimal hexagonal packing, get an estimate of the maximum number of circles of given radius
        # can fit in the area covered by the pixels that are not masked. This is obviously a significant overestimation
        # especially in the case where the radius becomes of the same order of magnitude as the radius of the
        # galaxy annulus (the hexagonal packing assumes a rectangular area or at least rectangular-like edges)
        # With perfect hexagonal packing, the area of the rectangle that will be covered by the circles is π/(2√3),
        # which is approximately equal to 0.907
        # See: https://www.quora.com/How-many-3-75-inch-circles-will-fit-inside-a-17-inch-square
        coverable_area = 0.907 * self.nunmasked_pixels
        optimal_number_of_apertures = coverable_area / self.aperture_area

        # Debugging
        log.debug("The upper limit to the number of apertures that fit in the part of the frame that is not masked "
                  "(assuming hexagonal packing) is " + str(optimal_number_of_apertures))

        # Determine the number of apertures that are going to be used
        napertures = int(optimal_number_of_apertures * self.config.estimation.relative_napertures_max)

        # Don't take less than 'min_napertures'
        napertures = max(napertures, self.config.estimation.min_napertures)

        # Debugging
        log.debug("A total of " + str(napertures) + " apertures are going to be used to estimate the sky ...")

        # Set the number of apertures
        self.napertures = napertures

    # -----------------------------------------------------------------

    def set_estimators(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the aperture estimators ...")

        # Set value estimator
        self.set_value_estimator()

        # Set noise estaimtor
        self.set_noise_estimator()

    # -----------------------------------------------------------------

    def set_value_estimator(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the aperture value estimator ...")

        # Mean
        if self.config.estimation.estimator == "mean": self.estimator = MeanBackground(sigma_clip=None)

        # Median
        elif self.config.estimation.estimator == "median": self.estimator = MedianBackground(sigma_clip=None)

        # Mode
        elif self.config.estimation.estimator == "mode": self.estimator = ModeEstimatorBackground(sigma_clip=None)

        # MMM
        elif self.config.estimation.estimator == "MMM": self.estimator = MMMBackground(sigma_clip=None)

        # Sextractor
        elif self.config.estimation.estimator == "sextractor": self.estimator = SExtractorBackground(sigma_clip=None)

        # Biweight location
        elif self.config.estimation.estimator == "biweight_location": self.estimator = BiweightLocationBackground(sigma_clip=None)

        # Invalid
        else: raise ValueError("Invalid option for 'estimator'")

    # -----------------------------------------------------------------

    def set_noise_estimator(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the aperture noise estimator ...")

        # Stddev
        if self.config.estimation.noise_estimator == "stddev": self.noise_estimator = StdBackgroundRMS(sigma_clip=None)

        # MAD
        elif self.config.estimation.noise_estimator == "MAD": self.noise_estimator = MADStdBackgroundRMS(sigma_clip=None)

        # Biweight variance
        elif self.config.estimation.noise_estimator == "biweight_variance": self.noise_estimator = BiweightMidvarianceBackgroundRMS(sigma_clip=None)

        # Invalid
        else: raise ValueError("Invalid option for 'noise_estimator'")

    # -----------------------------------------------------------------

    def create_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the apertures ...")

        # Generate the apertures
        aperture_centers, aperture_values, aperture_noise_values, aperture_masks = self.generate_apertures()

        # Remove outliers
        self.aperture_centers, self.aperture_values, self.aperture_noise_values, self.aperture_masks = self.remove_aperture_outliers(aperture_centers, aperture_values, aperture_noise_values, aperture_masks)

    # -----------------------------------------------------------------

    def generate_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the apertures ...")

        # Get arrays of the coordinates of all pixels that are not masked
        pixels_y, pixels_x = np.where(self.mask.inverse())

        # Get the number of pixels that are not masked (also the area of the frame not masked)
        npixels = pixels_x.size

        # Create a mask that tags all pixels that have been covered by one of the apertures
        apertures_mask = Mask.empty_like(self.frame)

        # Counter to keep track of the number of 'succesful' apertures that have been used
        current_napertures = 0

        # Initialize lists to contain the mean sky levels and noise levels in each of the apertures
        aperture_centers = []
        aperture_values = []
        aperture_noise_values = []
        aperture_masks = []

        # Draw random apertures
        while True:

            # Draw a random pixel index
            index = np.random.randint(npixels)

            # Get the x and y coordinate of the pixel
            x = pixels_x[index]
            y = pixels_y[index]

            # Create a coordinate for the center of the aperture
            center = PixelCoordinate(x, y)

            # Create a circular aperture
            circle = PixelCircleRegion(center, self.aperture_radius)

            # Create a Source from the frame
            source = Detection.from_shape(self.frame, circle, 1.3)

            # Get a mask of the pixels that overlap with the sky mask
            sky_mask_cutout = self.mask[source.y_slice, source.x_slice]
            overlapping = sky_mask_cutout * source.mask

            # Calculate the overlap fraction with the sky mask
            number_of_overlapping_pixels = np.sum(overlapping)
            overlap_fraction = number_of_overlapping_pixels / self.aperture_area

            # If the overlap fraction is larger than 50% for this aperture, skip it
            if overlap_fraction >= 0.5:
                log.debug("For this aperture, an overlap fraction of more than 50% was found with the sky mask, skipping ...")
                continue

            # Get a mask of the pixels that overlap with the apertures mask
            apertures_mask_cutout = apertures_mask[source.y_slice, source.x_slice]
            overlapping = apertures_mask_cutout * source.mask

            # Calculate the overlap fraction with the apertures mask
            number_of_overlapping_pixels = np.sum(overlapping)
            overlap_fraction = number_of_overlapping_pixels / self.aperture_area

            # If the overlap fraction is larger than 10% for this aperture, skip it
            if overlap_fraction >= 0.1:
                log.debug("For this aperture, an overlap fraction of more than 10% was found with other apertures, skipping ...")
                continue

            # Add the aperture area to the mask
            apertures_mask[source.y_slice, source.x_slice] += source.mask

            # Debugging
            log.debug("Placed aperture " + str(current_napertures+1) + " of " + str(self.napertures) + " ({0:.2f}%)".format((current_napertures+1)/self.napertures*100.))

            # Add a frame to the animation
            if self.animation is not None:
                plt.figure()
                plt.imshow(apertures_mask, origin="lower")
                plt.title("Aperture mask")
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                im = imageio.imread(buf)
                buf.close()
                self.animation.add_frame(im)

            aperture_mask = sky_mask_cutout + source.background_mask
            cutout_mask = CutoutMask(aperture_mask, source.x_min, source.x_max, source.y_min, source.y_max)

            # Calculate the mean sky value in this aperture
            masked_array_cutout = np.ma.MaskedArray(source.cutout, mask=aperture_mask)

            # plotting.plot_box(masked_array_cutout)

            #aperture_mean = np.ma.mean(masked_array_cutout)
            #aperture_median = np.ma.median(masked_array_cutout)
            # aperture_median2 = np.median(masked_array_cutout.compressed()) # same result, but unnecessary compressed step
            #aperture_stddev = np.std(masked_array_cutout)

            # print("aperture mean:", aperture_mean)
            # print("aperture median:", aperture_median, aperture_median2)
            # print("aperture stddev:", aperture_std)

            # Calculate the value for the aperture
            aperture_value = self.estimator.calc_background(masked_array_cutout)

            # Calcualte the noise value for the aperture
            aperture_noise = self.noise_estimator.calc_background_rms(masked_array_cutout)

            # Add properties of the aperture
            aperture_centers.append(center)
            #aperture_means.append(aperture_mean)
            #aperture_stddevs.append(aperture_stddev)
            aperture_values.append(aperture_value)
            aperture_noise_values.append(aperture_noise)
            aperture_masks.append(cutout_mask)

            # Another succesful aperture
            current_napertures += 1

            # Stop when we have reached the desired number of apertures
            if current_napertures == self.napertures: break

        # Create Numpy arrays from the aperture means and standard deviations
        #aperture_means = np.array(aperture_means)
        #aperture_stddevs = np.array(aperture_stddevs)

        aperture_values = np.array(aperture_values)
        aperture_noise_values = np.array(aperture_noise_values)

        # Return the aperture properties
        return aperture_centers, aperture_values, aperture_noise_values, aperture_masks

    # -----------------------------------------------------------------

    def remove_aperture_outliers(self, aperture_centers, aperture_values, aperture_noise_values, aperture_masks):

        """
        This function ...
        :param aperture_centers:
        :param aperture_values:
        :param aperture_noise_values:
        :param aperture_masks:
        :return:
        """

        # Inform the user
        log.info("Removing aperture outliers ...")

        #means_distribution = Distribution.from_values(aperture_means, bins=50)
        #stddevs_distribution = Distribution.from_values(aperture_stddevs, bins=50)

        #means_distribution.plot("Aperture means before sigma-clipping")
        #stddevs_distribution.plot("Aperture stddevs before sigma-clipping")

        clip_mask = stats.sigma_clip(aperture_noise_values, sigma=3.0, iters=None, copy=False).mask

        clipped_aperture_centers = []
        for i in range(len(clip_mask)):
            if clip_mask[i]: continue
            else: clipped_aperture_centers.append(aperture_centers[i])

        # Clip outliers from the lists
        aperture_centers = clipped_aperture_centers
        aperture_values = np.ma.MaskedArray(aperture_values, clip_mask).compressed()
        aperture_noise_values = np.ma.MaskedArray(aperture_noise_values, clip_mask).compressed()

        indices = np.ma.MaskedArray(range(len(aperture_masks)), mask=clip_mask).compressed()
        clipped_aperture_masks = []
        for index in indices: clipped_aperture_masks.append(aperture_masks[index])

        #means_distribution = Distribution.from_values(aperture_means, bins=50)
        #stddevs_distribution = Distribution.from_values(aperture_stddevs, bins=50)

        #means_distribution.plot("Aperture means after sigma-clipping")
        #stddevs_distribution.plot("Aperture stddevs after sigma-clipping")

        # Return the sigma-clipped aperture properties
        return aperture_centers, aperture_values, aperture_noise_values, clipped_aperture_masks

    # -----------------------------------------------------------------

    def create_aperture_frames(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating aperture frames ...")

        # Initialize frames and mask
        self.apertures_frame = Frame.nans_like(self.frame)
        self.apertures_values_frame = Frame.nans_like(self.frame)
        self.apertures_noise_frame = Frame.nans_like(self.frame)
        self.apertures_mask = newMask.empty_like(self.frame)

        # Loop over the apertures
        for i in range(len(self.aperture_centers)):

            # Create mask
            center = self.aperture_centers[i]
            circle = PixelCircleRegion(center, self.aperture_radius)
            mask = Mask.from_shape(circle, self.frame.xsize, self.frame.ysize)

            # Set
            self.apertures_frame[mask] = self.frame[mask]
            self.apertures_values_frame[mask] = self.aperture_values[i]
            self.apertures_noise_frame[mask] = self.aperture_noise_values[i]
            self.apertures_mask[self.aperture_masks[i]] = True

    # -----------------------------------------------------------------

    def create_mesh_from_filled(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating mesh from filled frames ...")

        # Determine properties of the mesh
        self.determine_mesh_properties()

        # Interpolate
        self.interpolate_aperture_values_to_mesh()

        # Interpolate
        self.interpolate_aperture_noise_to_mesh()

    # -----------------------------------------------------------------

    def create_mesh_from_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating mesh from aperture values ...")

        # Determine mesh properties
        self.determine_mesh_properties_from_apertures()

        # ...

    # -----------------------------------------------------------------

    def determine_mesh_properties_from_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Determining mesh properties ...")

        # Determine number of boxes in both directions
        nyboxes = self.frame.ysize // self.mesh_size
        nxboxes = self.frame.xsize // self.mesh_size
        yextra = self.frame.ysize % self.mesh_size
        xextra = self.frame.xsize % self.mesh_size

        if (xextra + yextra) == 0:
            # no resizing of the data is necessary
            data_ma = np.ma.masked_array(self.filled_values.data, mask=self.mask.data)
            noise_ma = np.ma.masked_array(self.filled_noise.data, mask=self.mask.data)
        else:
            # Pad
            #data_ma = self._pad_data(self.filled_values.data, yextra, xextra)
            #noise_ma = self._pad_data(self.filled_noise.data, yextra, xextra)
            nyboxes = data_ma.shape[0] // self.mesh_size
            nxboxes = data_ma.shape[1] // self.mesh_size

        # a reshaped 2D array with mesh data along the x axis
        #mesh_value_data = np.ma.swapaxes(data_ma.reshape(nyboxes, self.mesh_size, nxboxes, self.mesh_size), 1, 2).reshape(nyboxes * nxboxes, self.mesh_area)
        #mesh_noise_data = np.ma.swapaxes(noise_ma.reshape(nyboxes, self.mesh_size, nxboxes, self.mesh_size), 1, 2).reshape(nyboxes * nxboxes, self.mesh_area)

        # Select meshes
        #mesh_idx = self.select_meshes(mesh_value_data)

        # The mesh data
        #mesh_value_data = mesh_value_data[mesh_idx, :]

        # The mesh noise data
        #mesh_noise_data = mesh_noise_data[mesh_idx, :]

        mesh_shape = (nyboxes, nxboxes)
        #mesh_yidx, mesh_xidx = np.unravel_index(mesh_idx, mesh_shape)

        # Create arrays of mesh_xidx and mesh_yidx
        mesh_xidx = []
        mesh_yidx = []
        #noise_values = []
        for i in range(len(self.aperture_centers)):

            #points.append([self.aperture_centers[i].x, self.aperture_centers[i].y])
            #values.append(self.aperture_values[i])

            # WHICH MESH DOES THIS APERTURE FALL IN?
            xid = None
            yid = None

            ## This is all never going to work...

            mesh_xidx.append(xid)
            mesh_yidx.append(yid)

        # Create mesh info
        self.mesh = Map()

        # Set mesh properties
        self.mesh.box_size = self.mesh_size
        self.mesh.box_area = self.mesh_area
        self.mesh.nxboxes = nxboxes
        self.mesh.nyboxes = nyboxes
        self.mesh.shape = mesh_shape
        self.mesh.mesh_xidx = mesh_xidx
        self.mesh.mesh_yidx = mesh_yidx
        #self.mesh.value_data = mesh_value_data
        #self.mesh.noise_data = mesh_noise_data

        # Debugging
        log.debug("")
        log.debug("Mesh properties:")
        log.debug("")
        log.debug(" - box size: " + str(self.mesh.box_size))
        log.debug(" - box area: " + str(self.mesh.box_area))
        log.debug(" - nxboxes: " + str(self.mesh.nxboxes))
        log.debug(" - nyboxes: " + str(self.mesh.nyboxes))
        log.debug(" - total nboxes: " + str(self.mesh.nxboxes * self.mesh.nyboxes))
        log.debug("")

    # -----------------------------------------------------------------

    def make_filled_maps(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making maps filled with the aperture values ...")

        # Choose the fill method
        if self.config.estimation.fill_method == "NN": self.make_filled_maps_nn()
        elif self.config.estimation.fill_method == "zoom": self.make_filled_maps_zoom()
        else: self.make_filled_maps_interpolate()

    # -----------------------------------------------------------------

    def make_filled_maps_nn(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making a map filled with the aperture values and noise using nearest-neighbor interpolation ...")

        # Create array of points and values
        points = []
        values = []
        noise_values = []
        for i in range(len(self.aperture_centers)):

            points.append([self.aperture_centers[i].x, self.aperture_centers[i].y])
            values.append(self.aperture_values[i])
            noise_values.append(self.aperture_noise_values[i])

        #print("points", points)
        #print("values", values)

        # Create interpolator for values
        interpolator = NearestNDInterpolator(points, values)

        # Set filled values frame
        self.filled_values = Frame.zeros_like(self.frame)

        # Fill
        for x in range(self.frame.xsize):
            for y in range(self.frame.ysize):
                self.filled_values[y, x] = interpolator(x, y)

        # Multiply each patch with its area
        #for unique_value in np.unique(self.mesh.filled_values):
        #    where = self.mesh.filled_values == unique_value
        #    patch_area = np.sum(where)
        #    self.mesh.filled_values[where] *= patch_area

        #print("points", points)
        #print("noise values", noise_values)

        # Create interpolator for noise values
        interpolator = NearestNDInterpolator(points, noise_values)

        # Set filled noise values frame
        self.filled_noise = Frame.zeros_like(self.frame)

        # Fill
        for x in range(self.frame.xsize):
            for y in range(self.frame.ysize):
                self.filled_noise[y, x] = interpolator(x, y)

        # Multiply each patch with its area
        #for unique_value in np.unique(self.mesh.filled_noise):
        #    where = self.mesh.filled_noise == unique_value
        #    patch_area = np.sum(where)
        #    self.mesh.filled_noise[where] *= patch_area

    # -----------------------------------------------------------------

    def make_filled_maps_zoom(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making filled maps using the zoom method ...")

        # Create array of points and values
        x = []
        y = []
        values = []
        noise_values = []
        for i in range(len(self.aperture_centers)):
            x.append(self.aperture_centers[i].x)
            y.append(self.aperture_centers[i].y)
            values.append(self.aperture_values[i])
            noise_values.append(self.aperture_noise_values[i])

        x = np.array(x)
        y = np.array(y)
        values = np.array(values)
        noise_values = np.array(noise_values)



    # -----------------------------------------------------------------

    def make_filled_maps_interpolate(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making maps filled with the aperture values and noise using 2D interpolation ...")

        # Create array of points and values
        x = []
        y = []
        values = []
        noise_values = []
        for i in range(len(self.aperture_centers)):
            x.append(self.aperture_centers[i].x)
            y.append(self.aperture_centers[i].y)
            values.append(self.aperture_values[i])
            noise_values.append(self.aperture_noise_values[i])

        x = np.array(x)
        y = np.array(y)
        values = np.array(values)
        noise_values = np.array(noise_values)

        # Debugging
        print("x", x.shape)
        print("y", y.shape)
        print("values", values.shape)
        print("noise_values", noise_values.shape)

        # Interpolate values
        values_function = interp2d(x, y, values, kind=self.config.estimation.fill_method)

        # Set filled values frame
        self.filled_values = Frame.zeros_like(self.frame)

        # Fill
        for xi in range(self.frame.xsize):
            for yi in range(self.frame.ysize):
                self.filled_values[yi, xi] = values_function(xi, yi)

        # Interpolate noise
        noise_function = interp2d(x, y, noise_values, kind=self.config.estimation.fill_method)

        # Set filled noise values frame
        self.filled_noise = Frame.zeros_like(self.frame)

        # Fill
        for xi in range(self.frame.xsize):
            for yi in range(self.frame.ysize):
                self.filled_noise[yi, xi] = noise_function(xi, yi)

    # -----------------------------------------------------------------

    def determine_mesh_properties(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Determining the mesh properties ...")

        # Determine number of boxes in both directions
        nyboxes = self.frame.ysize // self.mesh_size
        nxboxes = self.frame.xsize // self.mesh_size
        yextra = self.frame.ysize % self.mesh_size
        xextra = self.frame.xsize % self.mesh_size

        if (xextra + yextra) == 0:
            # no resizing of the data is necessary
            data_ma = np.ma.masked_array(self.filled_values.data, mask=self.mask.data)
            noise_ma = np.ma.masked_array(self.filled_noise.data, mask=self.mask.data)
        else:
            # pad or crop the data
            #if self.edge_method == 'pad':
            #    data_ma = self._pad_data(yextra, xextra)
            #    self.nyboxes = data_ma.shape[0] // self.box_size[0]
            #    self.nxboxes = data_ma.shape[1] // self.box_size[1]
            #elif self.edge_method == 'crop':
            #    data_ma = self._crop_data()
            #else:
            #    raise ValueError('edge_method must be "pad" or "crop"')

            # Pad
            data_ma = self._pad_data(self.filled_values.data, yextra, xextra)
            noise_ma = self._pad_data(self.filled_noise.data, yextra, xextra)
            nyboxes = data_ma.shape[0] // self.mesh_size
            nxboxes = data_ma.shape[1] // self.mesh_size

        # a reshaped 2D array with mesh data along the x axis
        mesh_value_data = np.ma.swapaxes(data_ma.reshape(nyboxes, self.mesh_size, nxboxes, self.mesh_size), 1, 2).reshape(nyboxes * nxboxes, self.mesh_area)
        mesh_noise_data = np.ma.swapaxes(noise_ma.reshape(nyboxes, self.mesh_size, nxboxes, self.mesh_size), 1, 2).reshape(nyboxes * nxboxes, self.mesh_area)

        # Select meshes
        mesh_idx = self.select_meshes(mesh_value_data)

        # The mesh data
        mesh_value_data = mesh_value_data[mesh_idx, :]

        # The mesh noise data
        mesh_noise_data = mesh_noise_data[mesh_idx, :]

        ## _calc_bkg_bkgrms function

        #self._mesh_shape = (self.nyboxes, self.nxboxes)

        mesh_shape = (nyboxes, nxboxes)
        mesh_yidx, mesh_xidx = np.unravel_index(mesh_idx, mesh_shape)

        #print("mesh yidx", mesh_yidx)
        #print("mesh_xidx", mesh_xidx)

        # Create mesh info
        self.mesh = Map()

        # Set mesh properties
        self.mesh.box_size = self.mesh_size
        self.mesh.box_area = self.mesh_area
        self.mesh.nxboxes = nxboxes
        self.mesh.nyboxes = nyboxes
        self.mesh.shape = mesh_shape
        self.mesh.mesh_xidx = mesh_xidx
        self.mesh.mesh_yidx = mesh_yidx
        self.mesh.value_data = mesh_value_data
        self.mesh.noise_data = mesh_noise_data

        # Debugging
        log.debug("")
        log.debug("Mesh properties:")
        log.debug("")
        log.debug(" - box size: " + str(self.mesh.box_size))
        log.debug(" - box area: " + str(self.mesh.box_area))
        log.debug(" - nxboxes: " + str(self.mesh.nxboxes))
        log.debug(" - nyboxes: " + str(self.mesh.nyboxes))
        log.debug(" - total nboxes: " + str(self.mesh.nxboxes * self.mesh.nyboxes))
        log.debug("")

        #print(self.mesh.value_data)

    # -----------------------------------------------------------------

    def select_meshes(self, data):

        """
        This function ...
        :param data:
        :return:
        """

        # Inform the user
        log.info("Selecting meshes ...")

        exclude_mesh_percentile = 10.

        # the number of masked pixels in each mesh
        nmasked = np.ma.count_masked(data, axis=1)

        # keep meshes only with at least ``exclude_mesh_percentile``
        # unmasked pixels
        threshold_npixels = (exclude_mesh_percentile / 100. * self.mesh_area)
        mesh_idx = np.where((self.mesh_area - nmasked) >= threshold_npixels)[0]
        if len(mesh_idx) == 0:
            raise ValueError('All meshes contain < {0} ({1} percent per '
                             'mesh) unmasked pixels.  Please check your '
                             'data or decrease "exclude_mesh_percentile".'
                             .format(threshold_npixels, exclude_mesh_percentile))

        return mesh_idx

    # -----------------------------------------------------------------

    def _pad_data(self, input_data, yextra, xextra):

        """
        Pad the ``data`` and ``mask`` to have an integer number of
        background meshes of size ``box_size`` in both dimensions.  The
        padding is added on the top and/or right edges (this is the best
        option for the "zoom" interpolator).

        Parameters
        ----------
        yextra, xextra : int
            The modulus of the data size and the box size in both the
            ``y`` and ``x`` dimensions.  This is the number of extra
            pixels beyond a multiple of the box size in the ``y`` and
            ``x`` dimensions.

        Returns
        -------
        result : `~numpy.ma.MaskedArray`
            The padded data and mask as a masked array.
        """

        ypad = 0
        xpad = 0
        if yextra > 0:
            ypad = self.mesh_size - yextra
        if xextra > 0:
            xpad = self.mesh_size - xextra
        pad_width = ((0, ypad), (0, xpad))

        # mode must be a string for numpy < 0.11
        # (see https://github.com/numpy/numpy/issues/7112)
        mode = str('constant')
        data = np.pad(input_data, pad_width, mode=mode, constant_values=[1.e10])

        # mask the padded regions
        pad_mask = np.zeros_like(data)
        y0 = data.shape[0] - ypad
        x0 = data.shape[1] - xpad
        pad_mask[y0:, :] = True
        pad_mask[:, x0:] = True

        # pad the input mask separately (there is no np.ma.pad function)
        if self.mask is not None:
            mask = np.pad(self.mask, pad_width, mode=mode, constant_values=[True])
            mask = np.logical_or(mask, pad_mask)
        else: mask = pad_mask

        return np.ma.masked_array(data, mask=mask)

    # -----------------------------------------------------------------

    def interpolate_aperture_values_to_mesh(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating mesh of aperture values ...")

        # Create meshed values
        self.mesh.meshed_values = self.create_meshed_data(self.mesh.value_data)

        # Interpolate to create mesh
        interpolated = self.interpolate_meshes(self.mesh.meshed_values)

        # Set interpolated mesh
        self.mesh.interpolated_values = Frame(interpolated)

    # -----------------------------------------------------------------

    def interpolate_aperture_noise_to_mesh(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating mesh of noise values ...")

        # Create meshed values
        self.mesh.meshed_noise = self.create_meshed_data(self.mesh.noise_data)

        # Interpolate to create mesh
        interpolated = self.interpolate_meshes(self.mesh.meshed_noise)

        # Set interpolated mesh
        self.mesh.interpolated_noise = Frame(interpolated)

    # -----------------------------------------------------------------

    def create_meshed_data(self, data):

        """
        This function ...
        :param data:
        :return:
        """

        # Inform the user
        log.info("Creating mesh data by taking the mean value in each box ...")

        # Convert the data to have the mean value in each box
        converted_data = []
        for box_index in range(data.shape[0]):
            mean_box_value = np.ma.mean(data[box_index:])
            converted_data.append(mean_box_value)
        converted_data = np.array(converted_data)

        # Return thed ata
        return converted_data

    # -----------------------------------------------------------------

    def interpolate_meshes(self, data):

        """
        This function ...
        :param data:
        :return:
        """

        # Inform the user
        log.info("Interpolating meshes ...")

        # DEFAULT VALUES:
        # n_neighbors=10, eps=0., power=1., reg=0.
        n_neighbors = 10
        eps = 0.
        power = 1.
        reg = 0.
        #

        #print(self.mesh.mesh_yidx.shape, self.mesh.mesh_xidx.shape)
        #print(self.mesh.mesh_yidx)
        #print(self.mesh.mesh_xidx)

        # Create interpolator based on the aperture data
        yx = np.column_stack([self.mesh.mesh_yidx, self.mesh.mesh_xidx])

        f = ShepardIDWInterpolator(yx, data)

        # Determine the new coordinates
        coords = np.array(list(product(range(self.mesh.nyboxes), range(self.mesh.nxboxes))))

        # Create the image as an 1D array
        img1d = f(coords, n_neighbors=n_neighbors, power=power, eps=eps, reg=reg)

        # Reshape into mesh shape
        return img1d.reshape(self.mesh.shape)

    # -----------------------------------------------------------------

    def finish_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Finishing the sky map ...")

        # Finishing step
        if self.config.estimation.finishing_step == "mean": self.set_sky_mean()
        elif self.config.estimation.finishing_step == "median": self.set_sky_median()
        elif self.config.estimation.finishing_step == "polynomial": self.fit_polynomial_to_apertures()
        elif self.config.estimation.finishing_step == "interpolation": self.interpolate_apertures()
        else: raise ValueError("Invalid finishing step")

    # -----------------------------------------------------------------

    def set_sky_mean(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the sky to the mean of the aperture fluxes ...")

        # Determine the mean sky level
        self.sky = np.mean(self.aperture_values)

        # Determine the global noise level
        self.noise = self.calculate_global_noise_level_constant_sky()

        # Debugging
        log.debug("The estimated sky level is " + str(self.sky))
        log.debug("The estimated sky noise level is " + str(self.noise))

    # -----------------------------------------------------------------

    def set_sky_median(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the sky to the median of the aperture fluxes ...")

        # Determine the median sky level
        self.sky = np.median(self.aperture_values)

        # Calculate the global noise level
        self.noise = self.calculate_global_noise_level_constant_sky()

        # Debugging
        log.debug("The estimated sky level is " + str(self.sky))
        log.debug("The estimated sky noise level is " + str(self.noise))

    # -----------------------------------------------------------------

    def calculate_global_noise_level_constant_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the global noise value for methods that calculate a single, constant sky value for the entire image ...")

        # Calculate large scale variation and pixel to pixel noise
        large_scale_variations_error, pixel_to_pixel_noise = self.calculate_large_scale_variation_and_pixel_to_pixel_noise()

        # Determine the noise by quadratically adding the large scale variation and the mean pixel-by-pixel noise
        value = np.sqrt(large_scale_variations_error ** 2 + pixel_to_pixel_noise ** 2)

        # Return the noise value
        return value

    # -----------------------------------------------------------------

    def calculate_large_scale_variation_and_pixel_to_pixel_noise(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the large scale variation and the pixel to pixel noise of the apertures ...")

        # Calculate the large-scale variation level
        large_scale_variations_error = self.aperture_values.std()

        # Calculate the mean pixel-by-pixel noise over all apertures
        pixel_to_pixel_noise = np.mean(self.aperture_noise_values)

        # Return the result
        return large_scale_variations_error, pixel_to_pixel_noise

    # -----------------------------------------------------------------

    def calculate_global_noise_level_variate_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the global noise value for methods that calculate a variable sky map ...")

        # Calculate large scale variation and pixel to pixel noise
        large_scale_variations_error, pixel_to_pixel_noise = self.calculate_large_scale_variation_and_pixel_to_pixel_noise()

        # Return the average pixel-to-pixel noise
        return pixel_to_pixel_noise

    # -----------------------------------------------------------------

    def fit_polynomial_to_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Fitting a polynomial to the values in each aperture ...")

        # Get list of x and y coordinates
        x_values = [center.x for center in self.aperture_centers]
        y_values = [center.y for center in self.aperture_centers]

        # -- Fit polynomial --

        # Fit polynomial to aperture means
        poly_init = models.Polynomial2D(degree=self.config.estimation.polynomial_degree)
        #fit_model = LevMarLSQFitter()
        #fit_model = NonLinearLSQFitter()
        fit_model = SLSQPLSQFitter()
        polynomial = fit_model(poly_init, x_values, y_values, self.aperture_values)

        # Create x and y meshgrid for evaluating
        y_grid, x_grid = np.mgrid[:self.frame.ysize, :self.frame.xsize]

        # Evaluate the model
        data = polynomial(x_grid, y_grid)

        # Set the sky
        self.sky = Frame(data)

        # plotting.plot_box(data)

        # -- Fit spline --

        #f = interpolate.interp2d(x_values, y_values, aperture_means, kind='cubic')


        #x_grid = np.array(range(self.frame.xsize))
        #y_grid = np.array(range(self.frame.ysize))

        #data = f(x_grid, y_grid)

        # Set new sky frame
        #self.sky = Frame(data)

        ## NEW: NOISE

        # Calculate the global noise level
        self.noise = self.calculate_global_noise_level_variate_sky()

    # -----------------------------------------------------------------

    def interpolate_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating between the values of each aperture to fill the sky frame ...")

        # Choose method
        if self.config.estimation.interpolation_method == "griddata": self.interpolate_griddata()
        elif self.config.estimation.interpolation_method == "zoom": self.interpolate_zoom()
        elif self.config.estimation.interpolation_method == "IDW": self.interpolate_idw()
        elif self.config.estimation.interpolation_method == "spline": self.interpolate_spline()
        else: raise ValueError("Invalid interpolation method: " + self.config.estimation.interpolation_method)

    # -----------------------------------------------------------------

    def interpolate_griddata(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the aperture fluxes using the 'griddata' method")

        # Get lists of x and y values
        x_values = np.array([center.x for center in self.aperture_centers])
        y_values = np.array([center.y for center in self.aperture_centers])

        x_ticks = np.arange(0, self.frame.xsize, 1)
        y_ticks = np.arange(0, self.frame.ysize, 1)
        z_grid = mlab.griddata(x_values, y_values, self.aperture_values, x_ticks, y_ticks)

        # Set the sky frame
        self.sky = Frame(z_grid)

        # Calculate the global noise level
        self.noise = self.calculate_global_noise_level_variate_sky()

    # -----------------------------------------------------------------

    def interpolate_zoom(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the aperture fluxes using the 'zoom' method ...")

        # First fill
        if self.config.estimation.fill_before_mesh:

            # Make filled
            self.make_filled_maps()

            # Create mesh from filled
            self.create_mesh_from_filled()

        # Create mesh directly from apertures
        else: self.create_mesh_from_apertures

        # Final interpolation using zoom method
        data = self.final_interpolation_zoom(self.mesh.interpolated_values.data)

        # Final noise data
        noise = self.final_interpolation_zoom(self.mesh.interpolated_noise.data)

        # Set data
        self.sky = Frame(data)

        # Set noise
        self.noise = Frame(noise)

    # -----------------------------------------------------------------

    def final_interpolation_zoom(self, data):

        """
        This function ...
        :return:
        """

        # UNFORTUNATELY, something like this is not possible

        # Create the interpolator
        #self.interpolator = BkgZoomInterpolator()

        # Interpolate
        #data = self.interpolator(self.background_mesh, self)
        #self.sky = Frame(data)

        # IMPLEMENTATION OF BKGZOOMINTERPOLATOR:

        # DEFAULT SETTINGS
        # order=3, mode='reflect', cval=0.0

        order = 3
        mode = "reflect"
        cval = 0.0
        #

        mesh = np.asanyarray(data)

        if np.ptp(mesh) == 0:
            return np.zeros_like(self.frame) + np.min(mesh)

        edge_method = "pad"

        if edge_method == 'pad':

            # The mesh is first resized to the larger padded-data size
            # (i.e. zoom_factor should be an integer) and then cropped
            # back to the final data size.

            zoom_factor = (int(self.mesh.nyboxes * self.mesh_size / self.mesh.shape[0]),
                           int(self.mesh.nxboxes * self.mesh_size / self.mesh.shape[1]))

            result = zoom(mesh, zoom_factor, order=order, mode=mode, cval=cval)

            return result[0:self.frame.shape[0], 0:self.frame.shape[1]]

        else:

            # The mesh is resized directly to the final data size.
            zoom_factor = (float(self.frame.shape[0] / mesh.shape[0]),
                           float(self.frame.shape[1] / mesh.shape[1]))

            return zoom(mesh, zoom_factor, order=order, mode=mode, cval=cval)

    # -----------------------------------------------------------------

    def interpolate_idw(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the aperture fluxes using the 'IDW' method ...")

        # Create mesh
        self.create_mesh()

        # Final values
        data = self.final_interpolation_idw(self.mesh.interpolated_values)

        # Final noise
        noise = self.final_interpolation_idw(self.mesh.interpolated_noise)

        # Set
        self.sky = Frame(data)

        # Set noise
        self.noise = Frame(noise)

    # -----------------------------------------------------------------

    def final_interpolation_idw(self, data):

        """
        This function ...
        :param data:
        :return:
        """

        # UNFORTUNATELY, SOMETHING LIKE THIS IS NOT POSSIBLE:

        # Create the interpolator
        #self.interpolator = BkgIDWInterpolator()

        # Interpolate
        #data = self.interpolator(self.background_mesh, self)
        #self.sky = Frame(data)

        # IMPLEMENTATION OF BKGIDWINTERPOLATOR:

        # Default values:
        # leafsize=10, n_neighbors=10, power=1.0, reg=0.0

        leafsize = 10
        n_neighbors = 10
        power = 1.0
        reg = 0.0
        #

        mesh = np.asanyarray(data)

        if np.ptp(mesh) == 0: return np.zeros_like(self.frame.data) + np.min(mesh)

        mesh1d = mesh[self.mesh.mesh_yidx, self.mesh.mesh_xidx]
        f = ShepardIDWInterpolator(bkg2d_obj.yx, mesh1d, leafsize=leafsize)

        new_data = f(bkg2d_obj.data_coords, n_neighbors=n_neighbors, power=power, reg=reg)

        new_data = data.reshape(bkg2d_obj.data.shape)

        # Return
        return new_data

    # -----------------------------------------------------------------

    def interpolate_spline(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the aperture fluxes using the 'spline' method ...")

        pass

    # -----------------------------------------------------------------

    def interpolate_spline_old(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Interpolating the aperture fluxes using the 'spline' method ...")

        # Get lists of the x and y values
        x_values = np.array([center.x for center in self.aperture_centers])
        y_values = np.array([center.y for center in self.aperture_centers])

        #X, Y = np.meshgrid(x_values, y_values)

        X = x_values
        Y = y_values
        Z = self.aperture_values

        #print(X, Y, Z)
        #print(len(X), len(Y), len(Z))

        #C = intp((X, Y), Z)
        x_space = np.linspace(0, self.frame.xsize, 1)
        y_space = np.linspace(0, self.frame.ysize, 1)
        xi, yi = np.meshgrid(x_space, y_space)
        #zi = C(xi, yi)

        #self.sky = Frame(zi)

        from scipy.interpolate import LSQBivariateSpline

        spline = SmoothBivariateSpline(X, Y, Z, kx=1, ky=1)
        #spline = LSQBivariateSpline(X, Y, Z, X, Y)
        #zi = spline(xi, yi)
        #self.sky = Frame(zi)

        from scipy.interpolate import griddata


        #x_space = np.linspace(0.3*self.frame.xsize, 0.7*self.frame.xsize)
        #y_space = np.linspace(0.3*self.frame.ysize, 0.7*self.frame.ysize)

        x_space = np.array(range(int(0.3*self.frame.xsize), int(0.7*self.frame.xsize)))
        y_space = np.array(range(int(0.3*self.frame.ysize), int(0.7*self.frame.ysize)))

        znew = griddata((X, Y), Z, (x_space[None,:], y_space[:,None]), method='cubic')

        #plt.figure()
        #levels = np.linspace(min(Z), max(Z), 15)
        #plt.ylabel('Y', size=15)
        #plt.xlabel('X', size=15)
        #cmap = plt.cm.jet_r
        #cs = plt.contourf(x_space, y_space, znew, levels=levels, cmap=cmap)
        #cbar = plt.colorbar(cs)
        #cbar.set_label('Z', rotation=90, fontsize=15)  # gas fraction
        #plt.show()

        self.sky = Frame.zeros_like(self.frame)
        self.sky[int(0.3*self.frame.ysize):int(0.3*self.frame.ysize)+len(y_space), int(0.3*self.frame.xsize):int(0.3*self.frame.xsize)+len(x_space)] = znew

        #self.sky = Frame(znew)

    # -----------------------------------------------------------------

    def plot_interpolated(self):

        """
        This function ...
        :return:
        """

        # Get lists of x and y values
        x_values = np.array([center.x for center in self.aperture_centers])
        y_values = np.array([center.y for center in self.aperture_centers])

        x_ticks = np.arange(0, self.frame.xsize, 1)
        y_ticks = np.arange(0, self.frame.ysize, 1)
        z_grid = mlab.griddata(x_values, y_values, self.aperture_values, x_ticks, y_ticks)

        #self.sky = Frame(z_grid)

        from matplotlib.backends import backend_agg as agg
        from matplotlib import cm

        # plot
        #fig = Figure()  # create the figure
        fig = plt.figure()
        agg.FigureCanvasAgg(fig)  # attach the rasterizer
        ax = fig.add_subplot(1, 1, 1)  # make axes to plot on
        ax.set_title("Interpolated Contour Plot of Experimental Data")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")

        cmap = cm.get_cmap("hot")  # get the "hot" color map
        contourset = ax.contourf(x_ticks, y_ticks, z_grid, 10, cmap=cmap)

        cbar = fig.colorbar(contourset)
        cbar.set_ticks([0, 100])
        fig.axes[-1].set_ylabel("Z")  # last axes instance is the colorbar

        plt.show()

    # -----------------------------------------------------------------

    def estimate_caapr(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the sky using CAAPR ...")

        # Run pod through function that removes large-scale sky using a 2-dimensional polynomial filter
        #pod = CAAPR.CAAPR_Pipeline.PolySub(pod, 2.0 * pod['semimaj_initial_pix'], pod['opt_axial_ratio'],
        #                                   pod['opt_angle'],
        #                                   instant_quit=max([not kwargs_dict['polysub'], pod['band_exclude']]))

        #if pod['verbose']: print('[' + pod['id'] + '] Determining if (and how) background is significantly variable.')

        # Define Keflavich function to downsample an array
        def Downsample(myarr, factor, estimator=np.nanmean):
            ys, xs = myarr.shape
            crarr = myarr[:ys - (ys % int(factor)), :xs - (xs % int(factor))]
            dsarr = estimator(np.concatenate([[crarr[i::factor, j::factor]
                                               for i in range(factor)]
                                              for j in range(factor)]), axis=0)
            return dsarr

        # If polynomial background subraction not wanted, immediately return everything unchanged
        #if instant_quit:
        #    pod['sky_poly'] = False
        #    return pod

        # If image has pixels smaller than some limit, downsample image to improve processing time
        pix_size = pod['pix_arcsec']
        pix_size_limit = 2.0
        if pix_size < pix_size_limit:
            downsample_factor = int(np.ceil(pix_size_limit / pix_size))
        else:
            downsample_factor = 1
        image_ds = Downsample(pod['cutout'], downsample_factor)

        # Downsample related values accordingly
        mask_semimaj_pix = mask_semimaj_pix / downsample_factor
        centre_i = int(round(float((0.5 * pod['centre_i']) - 1.0)))
        centre_j = int(round(float((0.5 * pod['centre_j']) - 1.0)))

        # Find cutoff for excluding bright pixels by sigma-clipping map
        clip_value = chrisfuncs.SigmaClip(image_ds, tolerance=0.01, sigma_thresh=3.0, median=True)
        noise_value = clip_value[0]
        field_value = clip_value[1]
        cutoff = field_value + (cutoff_sigma * noise_value)

        # Mask all image pixels in masking region around source
        image_masked = image_ds.copy()
        ellipse_mask = chrisfuncs.EllipseMask(image_ds, mask_semimaj_pix, mask_axial_ratio, mask_angle, centre_i, centre_j)
        image_masked[np.where(ellipse_mask == 1)] = np.nan

        # Mask all image pixels identified as being high SNR
        image_masked[np.where(image_masked > cutoff)] = np.nan

        # Use astropy to fit 2-dimensional polynomial to the image
        image_masked[np.where(np.isnan(image_masked) == True)] = field_value
        poly_model = astropy.modeling.models.Polynomial2D(degree=poly_order)
        i_coords, j_coords = np.mgrid[:image_masked.shape[0], :image_masked.shape[1]]
        fitter = astropy.modeling.fitting.LevMarLSQFitter()
        i_coords = i_coords.flatten()
        j_coords = j_coords.flatten()
        image_flattened = image_masked.flatten()
        good = np.where(np.isnan(image_flattened) == False)
        i_coords = i_coords[good]
        j_coords = j_coords[good]
        image_flattened = image_flattened[good]
        fit = fitter(poly_model, i_coords, j_coords, image_flattened)

        # Create final polynomial filter (undoing downsampling using lorenzoriano GitHub script)
        i_coords, j_coords = np.mgrid[:image_ds.shape[0], :image_ds.shape[1]]
        poly_fit = fit(i_coords, j_coords)
        poly_full = scipy.ndimage.interpolation.zoom(poly_fit,
                                                     [float(pod['cutout'].shape[0]) / float(poly_fit.shape[0]),
                                                      float(pod['cutout'].shape[1]) / float(poly_fit.shape[1])],
                                                     mode='nearest')  # poly_full = congrid.congrid(poly_fit, (pod['cutout'].shape[0], pod['cutout'].shape[1]), minusone=True)

        # Establish background variation before application of filter
        sigma_thresh = 3.0
        clip_in = chrisfuncs.SigmaClip(pod['cutout'], tolerance=0.005, median=True, sigma_thresh=sigma_thresh)
        bg_in = pod['cutout'][np.where(pod['cutout'] < clip_in[1])]
        spread_in = np.mean(np.abs(bg_in - clip_in[1]))

        # How much reduction in background variation there was due to application of the filter
        image_sub = pod['cutout'] - poly_full
        clip_sub = chrisfuncs.SigmaClip(image_sub, tolerance=0.005, median=True, sigma_thresh=sigma_thresh)
        bg_sub = image_sub[np.where(image_sub < clip_sub[1])]
        spread_sub = np.mean(np.abs(bg_sub - clip_sub[1]))
        spread_diff = spread_in / spread_sub

        # If the filter made significant difference, apply to image and return it; otherwise, just return the unaltered map
        #if spread_diff > 1.1:
        #    if pod['verbose']: print('[' + pod['id'] + '] Background is significantly variable; removing polynomial background fit.')
        #    pod['cutout_nopoly'] = pod['cutout'].copy()
        #    pod['cutout'] = image_sub
        #    pod['sky_poly'] = poly_model
        #else:
        #    if pod['verbose']: print('[' + pod['id'] + '] Background is not significantly variable; leaving image unaltered.')
        #    pod['sky_poly'] = False

        #return pod

    # -----------------------------------------------------------------

    def set_statistics(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting statistics ...")

        # Set
        self.statistics = Map()
        self.statistics.mean = self.mean_subtracted
        self.statistics.median = self.median_subtracted
        self.statistics.stddev = self.stddev_subtracted

    # -----------------------------------------------------------------

    def create_distributions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating distributions ...")

        # Create a masked array
        #masked = np.ma.masked_array(self.frame, mask=self.mask)
        #masked_clipped = np.ma.masked_array(self.frame, mask=self.clipped_mask)

        # Create a figure
        #fig = plt.figure()

        #min_value = self.mean - 4.0 * self.stddev
        #max_value = self.mean + 4.0 * self.stddev

        #value_range = (min_value, max_value)

        # Plot the histograms
        # b: blue, g: green, r: red, c: cyan, m: magenta, y: yellow, k: black, w: white
        #plt.subplot(211)
        #plt.hist(masked.compressed(), 200, range=value_range, alpha=0.5, normed=1, facecolor='g', histtype='stepfilled',
        #         label='not clipped')
        #if self.config.histogram.log_scale: plt.semilogy()

        #plt.subplot(212)
        #plt.hist(masked_clipped.compressed(), 200, range=value_range, alpha=0.5, normed=1, facecolor='g',
        #         histtype='stepfilled', label='clipped')
        #if self.config.histogram.log_scale: plt.semilogy()

        # Save the figure
        #plt.savefig(self.config.writing.histogram_path, bbox_inches='tight', pad_inches=0.25)
        #plt.close()

        # Create original distribution
        self.create_original_distribution()

        # Create no-clipping distribution
        self.create_noclipping_distribution()

        # Create subtracted distribution
        self.create_subtracted_distribution()

    # -----------------------------------------------------------------

    def create_original_distribution(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating distribution of original pixel values with sigma-clipping ...")

        # Get original pixel values
        original_1d = self.frame_masked_array.compressed()

        # Create distribution of original pixel values
        original = Distribution.from_values(original_1d)

        # Set distribution
        self.distributions.original = original

    # -----------------------------------------------------------------

    def create_noclipping_distribution(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating distribution of original pixel values without sigma-clipping ...")

        # Get original pixel values, but not sigma-clipped
        not_clipped_1d = self.not_clipped_masked_array.compressed()

        # Create distribution of pixel values
        not_clipped = Distribution.from_values(not_clipped_1d)

        # Set distribution
        self.distributions.not_clipped = not_clipped

    # -----------------------------------------------------------------

    def create_subtracted_distribution(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating distribution of subtracted pixel values ...")

        # Create distribution of subtracted pixel values
        subtracted = Distribution.from_values(self.subtracted_values)

        # Set distribution
        self.distributions.subtracted = subtracted

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write apertures frame
        if self.config.estimation.method == "pts": self.write_apertures()

        # Write aperture means
        if self.config.estimation.method == "pts": self.write_apertures_value()

        # Write aperture noise
        if self.config.estimation.method == "pts": self.write_apertures_noise()

        # Write filled
        if self.filled_values is not None: self.write_filled()

        # Write mesh
        if self.mesh is not None: self.write_mesh()

        # Write region
        self.write_region()

        # Write mask
        self.write_mask()

        # Write sky
        self.write_sky()

        # Write noise
        self.write_noise()

        # Write subtracted
        self.write_subtracted()

        # Write statistics
        self.write_statistics()

    # -----------------------------------------------------------------

    def write_apertures(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the aperture frame ...")

        # Determine the path
        path = self.output_path_file("apertures.fits")

        # Save
        self.apertures_frame.saveto(path)

    # -----------------------------------------------------------------

    def write_apertures_value(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the aperture values frame ...")

        # Determine the path
        path = self.output_path_file("aperture_values.fits")

        # Save
        self.apertures_values_frame.saveto(path)

    # -----------------------------------------------------------------

    def write_apertures_noise(self):

        """
        THis function ...
        :return:
        """

        # Inform the user
        log.info("Writing the aperture noise frame ...")

        # Determine the path
        path = self.output_path_file("aperture_noise.fits")

        # Save
        self.apertures_noise_frame.saveto(path)

    # -----------------------------------------------------------------

    def write_mesh(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing mesh data ...")

        # Write mesh values
        self.write_mesh_values()

        # Write mesh noise
        self.write_mesh_noise()

    # -----------------------------------------------------------------

    def write_filled(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing filled frames ...")

        # Write filled values
        self.write_filled_values()

        # Write filled noise
        self.write_filled_noise()

    # -----------------------------------------------------------------

    def write_filled_values(self):

        """
        THis function ...
        :return:
        """

        # Inform the user
        log.info("Writing filled values ...")

        # Determine the path
        path = self.output_path_file("filled_values.fits")

        # Save
        self.filled_values.saveto(path)

    # -----------------------------------------------------------------

    def write_filled_noise(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing filled noise ...")

        # Determine the path
        path = self.output_path_file("filled_noise.fits")

        # Save
        self.filled_noise.saveto(path)

    # -----------------------------------------------------------------

    def write_mesh_values(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing interpolated mesh values ...")

        # Detetermine the path
        path = self.output_path_file("interpolated_values_mesh.fits")

        # Write
        self.mesh.interpolated_values.saveto(path)

    # -----------------------------------------------------------------

    def write_mesh_noise(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing interpolated mesh noise ...")

        # Determine the path
        path = self.output_path_file("interpolated_noise_mesh.fits")

        # Write
        self.mesh.interpolated_noise.saveto(path)

    # -----------------------------------------------------------------

    def write_region(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the region ...")

        # Determine the path
        path = self.output_path_file("sky.reg")

        # Save
        self.region.saveto(path)

    # -----------------------------------------------------------------

    def write_mask(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the mask ...")

        # Determine the path
        path = self.output_path_file("mask.fits")

        # Save
        self.mask.saveto(path)

    # -----------------------------------------------------------------

    def write_sky(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the sky ...")

        # Determine the path
        path = self.output_path_file("sky.fits")

        # Save
        self.sky_frame.saveto(path)

    # -----------------------------------------------------------------

    def write_noise(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the noise ...")

        # Determine the path
        path = self.output_path_file("noise.fits")

        # Save
        self.noise_frame.saveto(path)

    # -----------------------------------------------------------------

    def write_subtracted(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the subtracted frame ...")

        # Determine the path
        path = self.output_path_file("subtracted.fits")

        # Save
        self.subtracted.saveto(path)

    # -----------------------------------------------------------------

    def write_statistics(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the statistics ...")

        # Determine the path
        path = self.output_path_file("statistics.dat")

        # Save
        save_mapping(path, self.statistics)

    # -----------------------------------------------------------------

    def plot(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting ...")

        # Plot histograms
        self.plot_histograms()

        # Plot photutils mesh
        if self.config.estimation.method == "photutils": self.plot_photutils_mesh()

    # -----------------------------------------------------------------

    def plot_histograms(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing histograms ...")

        # Write original
        self.write_original_histogram()

        # Write noclipping
        self.write_noclipping_histogram()

        # Write subtracted
        self.write_subtracted_histogram()

    # -----------------------------------------------------------------

    def write_original_histogram(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing original histogram ...")

        # Add distribution
        plotter = DistributionPlotter()
        plotter.add_distribution(self.distributions.original, "original")

        # Determine the path
        path = self.output_path_file("histogram_original.pdf")

        # Run the plotter
        plotter.run(output_path=path)

    # -----------------------------------------------------------------

    def write_noclipping_histogram(self):

        """
        THis function ...
        :return:
        """

        # Inform the user
        log.info("Writing noclipping histogram ...")

        # Add distribution
        plotter = DistributionPlotter()
        plotter.add_distribution(self.distributions.not_clipped, "noclipping")

        # Determine the path
        path = self.output_path_file("histogram_notclipped.pdf")

        # Run the plotter
        plotter.run(output_path=path)

    # -----------------------------------------------------------------

    def write_subtracted_histogram(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing subtracted histogram ...")

        # Add distribution
        plotter = DistributionPlotter()
        plotter.add_distribution(self.distributions.subtracted, "subtracted")

        # Determine the path
        path = self.output_path_file("histogram_subtracted.pdf")

        # Run the plotter
        plotter.run(output_path=path)

    # -----------------------------------------------------------------

    def plot_photutils_mesh(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Plotting the photutils mesh ...")

        # Plot meshes
        plt.figure()
        norm = ImageNormalize(stretch=SqrtStretch())
        plt.imshow(self.frame, origin='lower', cmap='Greys_r', norm=norm)
        self.photutils_bkg.plot_meshes(outlines=True, color='#1f77b4')

        # Determine path
        path = self.output_path_file("photutils_mesh.pdf")

        # Save
        plt.savefig(path)
        plt.close()

    # -----------------------------------------------------------------

    @lazyproperty
    def sky_frame(self):

        """
        This function ...
        :return:
        """

        # Get the frame
        if isinstance(self.sky, Frame): result = self.sky
        else: result = Frame(np.full(self.frame.shape, self.sky))

        # Mask
        if self.extra_mask is not None and self.config.add_extra_mask:
            result[self.extra_mask] = self.config.mask_value

        # Return the result
        return result

    # -----------------------------------------------------------------

    @property
    def noise_frame(self):

        """
        This function ...
        :return:
        """

        # Get the frame
        if isinstance(self.noise, Frame): result = self.noise
        else: result = Frame(np.full(self.frame.shape, self.noise))

        # Mask
        if self.extra_mask is not None and self.config.add_extra_mask:
            result[self.extra_mask] = self.config.mask_value

        # Return the result
        return result

    # -----------------------------------------------------------------

    @property
    def mean(self):

        """
        This function ...
        :return:
        """

        # Return the sigma-clipped mean
        return np.ma.mean(np.ma.masked_array(self.frame, mask=self.mask))

    # -----------------------------------------------------------------

    @property
    def median(self):

        """
        This function ...
        :return:
        """

        # Return the sigma-clipped median
        return np.median(np.ma.masked_array(self.frame, mask=self.mask).compressed())

    # -----------------------------------------------------------------

    @property
    def stddev(self):

        """
        This function ...
        :return:
        """

        # Return the standard deviation of the sigma-clipped frame
        return np.ma.masked_array(self.frame, mask=self.mask).std()

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted(self):

        """
        This function ...
        :return:
        """

        # Subtract
        result = self.frame - self.sky

        # Set zero outside
        if self.config.set_zero_outside:

            # Create a mask from the principal galaxy region
            factor = self.config.zero_outside.factor
            mask = Mask.from_shape(self.principal_shape * factor, self.frame.xsize, self.frame.ysize).inverse()

            # Set the primary frame zero outside the principal ellipse
            result[mask] = self.config.mask_value

        # Eliminate negatives
        if self.config.eliminate_negatives:

            # Set all negative pixels to zero
            result[result <= 0.] = 0.0

        # mask extra
        if self.extra_mask is not None and self.config.add_extra_mask:

            # Set to zero
            result[self.extra_mask] = self.config.mask_value

        # Return the result
        return result

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_compressed(self):

        """
        This function ...
        :return: 
        """

        return self.subtracted_masked_array.compressed()

    # -----------------------------------------------------------------

    @lazyproperty
    def frame_masked_array(self):

        """
        This function ...
        :return:
        """

        return np.ma.masked_array(self.frame.data, mask=self.mask.data)

    # -----------------------------------------------------------------

    @lazyproperty
    def frame_compressed(self):

        """
        This function ...
        :return: 
        """

        return self.frame_masked_array.compressed()

    # -----------------------------------------------------------------

    @lazyproperty
    def mean_frame(self):

        """
        This function ...
        :return: 
        """

        return np.nanmean(self.frame_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def median_frame(self):

        """
        This function ...
        :return: 
        """

        return np.nanmedian(self.frame_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def stddev_frame(self):

        """
        This fucntion ...
        :return: 
        """

        return np.nanstd(self.frame_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def not_clipped_masked_array(self):

        """
        This function ...
        :return:
        """

        return np.ma.masked_array(self.frame.data, mask=self.mask_not_clipped.data)

    # -----------------------------------------------------------------

    @lazyproperty
    def frame_not_clipped_compressed(self):

        """
        This function ...
        :return: 
        """

        return self.not_clipped_masked_array.compressed()

    # -----------------------------------------------------------------

    @lazyproperty
    def mean_frame_not_clipped(self):

        """
        This function ...
        :return: 
        """

        return np.nanmean(self.frame_not_clipped_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def median_frame_not_clipped(self):

        """
        This function ...
        :return: 
        """

        return np.nanmedian(self.frame_not_clipped_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def stddev_frame_not_clipped(self):

        """
        This function ...
        :return: 
        """

        return np.nanstd(self.frame_not_clipped_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_nans(self):

        """
        This function ...
        :return: 
        """

        return np.isnan(self.subtracted.data)

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_nans_masked_array(self):

        """
        This function ...
        :return: 
        """

        return np.ma.masked_array(self.subtracted_nans, mask=self.mask.data)

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_nans_compressed(self):

        """
        This function ...
        :return: 
        """

        return self.subtracted_nans_masked_array.compressed()

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_masked_array(self):

        """
        This function ...
        :return:
        """

        return np.ma.masked_array(self.subtracted.data, mask=self.mask.data)

    # -----------------------------------------------------------------

    @lazyproperty
    def mean_subtracted(self):

        """
        This function ...
        :return:
        """

        #return np.ma.mean(np.ma.masked_array(self.subtracted, mask=self.mask.data))
        return np.nanmean(self.subtracted_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def median_subtracted(self):

        """
        This function ...
        :return:
        """

        #return np.median(np.ma.masked_array(self.subtracted, mask=self.mask.data).compressed())
        #masked_array = np.ma.masked_array(self.subtracted, mask=self.mask.data)
        return np.nanmedian(self.subtracted_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def stddev_subtracted(self):

        """
        This function ...
        :return:
        """

        # return np.ma.masked_array(self.subtracted, mask=self.mask.data).std()
        return np.nanstd(self.subtracted_compressed)

    # -----------------------------------------------------------------

    @lazyproperty
    def subtracted_values(self):

        """
        This function ...
        :return: 
        """

        # Get the subtracted pixel values
        subtracted_1d = self.subtracted_masked_array.compressed()

        # Remove nans
        nans = self.subtracted_nans_compressed

        # Get
        subtracted_values = np.ma.masked_array(subtracted_1d, mask=nans).compressed()

        # Return
        return subtracted_values

# -----------------------------------------------------------------
