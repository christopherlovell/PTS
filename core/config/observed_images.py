#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# -----------------------------------------------------------------

# Filters and instruments for which to create the images
definition.add_positional_optional("instruments", "string_list", "instruments for which to create the images")
definition.add_positional_optional("filters", "filter_list", "filters for which to create the images")

# -----------------------------------------------------------------

# Add optional
definition.add_optional("output", "string", "output directory")

# Intermediate results
definition.add_flag("write_intermediate", "write intermediate results", False)
definition.add_flag("keep_intermediate", "keep intermediate results", False)

# Save kernels
definition.add_flag("write_kernels", "write the prepared convolution kernels", False)

# -----------------------------------------------------------------

# Add flags
definition.add_flag("spectral_convolution", "convolve over the wavelengths to get the most accurate images", True)
definition.add_flag("group", "group the images per instrument", False)

# Number of parallel processes to use to create the images
definition.add_optional("nprocesses_local", "positive_integer", "number of parallel processes to use for local calculation", 2)
definition.add_optional("nprocesses_remote", "positive_integer", "number of parallel processes to use for remote calculation", 8)

# -----------------------------------------------------------------

# LIMIT TO THE RATIO BETWEEN CONVOLUTION KERNEL FWHM AND IMAGE PIXELSCALE
definition.add_optional("max_fwhm_pixelscale_ratio", "positive_real", "maximum ratio between the convolution kernel FWHM and the image pixelscale before downsampling is applied", 50)

# REBIN TO SMALLER PIXELSCALES?
definition.add_flag("upsample", "rebin images where upsampling is required?", False)

# -----------------------------------------------------------------

# ADVANCED: regenerate?
definition.add_flag("regenerate", "regenerate images that are already present", False)

# Update PTS on the remote
definition.add_flag("deploy_pts", "deply (install or update) PTS on the remote host", True)
definition.add_flag("update_dependencies", "update PTS dependencies (use with care!)", False)

# -----------------------------------------------------------------
