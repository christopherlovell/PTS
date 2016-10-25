#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

from pts.core.basics.configuration import ConfigurationDefinition
from pts.core.basics.host import find_host_ids

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition()

# Extraction settings
definition.add_section("extraction", "settings for extraction data from the simulation's log files")
definition.sections["extraction"].add_flag("progress", "extract information about the progress in the different simulation phases")
definition.sections["extraction"].add_flag("timeline", "extract timeline information for the different simulation phases on the different processes")
definition.sections["extraction"].add_flag("memory", "extract information about the memory usage during the simulation")

# Plotting settings
definition.add_section("plotting", "settings for plotting simulation data")
definition.sections["plotting"].add_flag("seds", "make plots of the simulated SEDs")
definition.sections["plotting"].add_flag("grids", "make plots of the dust grid")
definition.sections["plotting"].add_flag("progress", "make plots of the progress of the simulation phases as a function of time")
definition.sections["plotting"].add_flag("timeline", "plot the timeline for the different processes")
definition.sections["plotting"].add_flag("memory", "plot the memory consumption as a function of time")
definition.sections["plotting"].add_optional("reference_sed", "file_path", "the path to a reference SED file against which the simulated SKIRT SEDs should be plotted")
definition.sections["plotting"].add_optional("format", "string", "pdf", choices=["pdf", "png"])

# Miscellaneous settings
definition.add_section("misc", "settings for creating data of various types from the simulation output")
definition.sections["misc"].add_flag("wave", "make a wavelength movie through the simulated datacube(s)")
definition.sections["misc"].add_flag("rgb", "make RGB images from the simulated datacube(s)")
definition.sections["misc"].add_flag("fluxes", "calculate observed fluxes from the SKIRT output SEDs")
definition.sections["misc"].add_flag("images", "make observed images form the simulated datacube(s)")
definition.sections["misc"].add_optional("observation_filters", "string_list", "the names of the filters for which to recreate the observations")
definition.sections["misc"].add_optional("observation_instruments", "string_list", "the names of the instruments for which to recreate the observations")
definition.sections["misc"].add_optional("make_images_remote", "string", "Perform the calculation of the observed images on a remote machine (this is a memory and CPU intensive step)", choices=find_host_ids(schedulers=False))
definition.sections["misc"].add_optional("images_wcs", "file_path", "the path to the FITS file for which the WCS should be set as the WCS of the recreated observed images")
definition.sections["misc"].add_optional("images_unit", "string", "the unit to which the recreated observed images should be converted")
definition.sections["misc"].add_optional("images_kernels", "dictionary", "paths to the FITS file of convolution kernel used for convolving the observed images (a dictionary where the keys are the filter names")

# -----------------------------------------------------------------
