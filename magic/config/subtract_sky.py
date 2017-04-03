#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition
from pts.magic.sky.skysubtractor import finishing_steps, interpolation_methods

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition()

# Image path
definition.add_optional("image", "file_path", "name/path of the input image")

# The path of a region file for the sky estimation
definition.add_optional("sky_region", "file_path", "region file for the sky estimation")

# Perform sigma-clipping step
definition.add_flag("sigma_clip_mask", "sigma-clippin", True)

# Estimate the sky (obviously)
definition.add_flag("estimate", "estimate the sky", True)

# Set zero outside of the principal galaxy
definition.add_flag("set_zero_outside", "set zero outside of principal galaxy", False)

# Eliminate negative values (replace them by zero)
definition.add_flag("eliminate_negatives", "replace negative pixels by zero", False)

# Creation of the sky mask
definition.add_section("mask", "creation of sky mask")
definition.sections["mask"].add_optional("annulus_inner_factor", "real", "sky annulus inner factor (based on principal galaxy ellipse", 1.6)
definition.sections["mask"].add_optional("annulus_outer_factor", "real", "sky annulus outer factor (based on principal galaxy ellipse", 4.0)

# Sigma clipping
definition.add_section("sigma_clipping", "sigma clipping")
definition.sections["sigma_clipping"].add_optional("sigma_level", "real", "sigma level", 3.0)

# Histogram
definition.add_section("histogram", "histogram")
definition.sections["histogram"].add_flag("log_scale", "log scale", True)

# Estimation
definition.add_section("estimation", "sky estimation")
definition.sections["estimation"].add_optional("method", "string", "method used for sky estimation", "pts")
definition.sections["estimation"].add_optional("finishing_step", "string", "finishing step", choices=finishing_steps, default="interpolation")
definition.sections["estimation"].add_optional("interpolation_method", "string", "method of interpolation (finishing step)", choices=interpolation_methods, default="zoom")
definition.sections["estimation"].add_optional("aperture_radius", "positive_real", "aperture radius in pixel coordinates (if not defined, aperture_fwhm_factor * fwhm of the frame will be used)")
definition.sections["estimation"].add_optional("aperture_fwhm_factor", "positive_real", "aperture radius = aperture_fwhm_factor * frame FWHM", 4.0)
definition.sections["estimation"].add_optional("relative_napertures_max", "positive_real", "fraction of the theoretical maximal number of apertures to be actually used", 0.5)
definition.sections["estimation"].add_optional("min_napertures", "positive_integer", "minimum number of sky apertures", 40)
definition.sections["estimation"].add_optional("polynomial_degree", "positive_integer", "degree of the polynomial for the finishing step", 2)
definition.sections["estimation"].add_optional("estimator", "string", "estimator for the sky in each aperture", choices=estimators, default="sextractor")
definition.sections["estimation"].add_optional("noise_estimator", "string", "estimator for the noise in each aperture", choices=noise_estimators, default="std")
definition.sections["estimation"].add_optional("photutils_fixed_width", "positive_integer", "fixed value for the width of the grid meshes (otherwise 2 * aperture_fwhm_factor * fwhm is used or 2 * aperture_radius)", suggestions=[50])
definition.sections["estimation"].add_optional("photutils_filter_size", "positive_integer", "filter size", 3)
definition.sections["estimation"].add_optional("photutils_global", "string", "use photutils method but only use the global mean/median value and noise (if None, actual frames are used)", choices=["mean", "median"], suggestions=["median"])

# Setting zero outside
definition.add_section("zero_outside", "setting zero outside")
definition.sections["zero_outside"].add_optional("factor", "real", "factor", 2.0)

# Flags
definition.add_flag("write", "writing")
definition.add_flag("plot", "plotting")

# -----------------------------------------------------------------
