#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, stringify_not_list
from pts.core.tools import filesystem as fs
from pts.modeling.core.component import load_fitting_configuration

# -----------------------------------------------------------------

# Load the fitting configuration
fitting_configuration = load_fitting_configuration(fs.cwd())

# Free parameter labels
free_parameter_labels = fitting_configuration.free_parameters

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition(log_path="log", config_path="config")

# Positional optional parameter
definition.add_positional_optional("generation_method", "string", "the model generation method ('grid', 'instinctive', 'genetic')", "genetic", ["genetic", "grid", "instinctive"])

# Optional parameters
definition.add_optional("remote", "string", "the remote host on which to run the parameters exploration", "nancy")
definition.add_optional("simulations", "integer", "the number of simulations to launch in one batch/generation", 100)

# The ranges of the different free parameters (although the absolute ranges are defined in the fitting configuration,
# give the option to refine these ranges for each exploration step (generation))
for label in free_parameter_labels:

    # Get the default range
    default_range = fitting_configuration[label + "_range"]
    ptype, string = stringify_not_list(default_range)

    # Add the optional range setting for this free parameter
    definition.add_optional(label + "_range", ptype, "the range of " + label, default_range)

# Flags
definition.add_flag("relative", "whether the range values are relative to the best (or initial) parameter value")
definition.add_flag("young_log", "use logarithmic spacing of the young stellar luminosity values")
definition.add_flag("ionizing_log", "use logarithmic spacing of the ionizing stellar luminosity values")
definition.add_flag("dust_log", "use logarithmic spacing of the dust mass values")
definition.add_flag("visualise", "make visualisations")
definition.add_flag("dry", "dry-run (don't actually launch simulations)")
definition.add_flag("refine_wavelengths", "increase the resolution of the wavelength grid for the new batch of simulations")
definition.add_flag("refine_dust", "increase the resolution of the dust cell grid for the new batch of simulations")

# -----------------------------------------------------------------
