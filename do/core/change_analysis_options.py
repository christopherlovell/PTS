#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.core.change_analysis_options Change certain analysis options for a simulation.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, parse_arguments
from pts.core.remote.host import find_host_ids
from pts.core.simulation.remote import get_simulation_for_host

# -----------------------------------------------------------------

# Create the configuration definition
definition = ConfigurationDefinition()

# Add required
definition.add_required("remote", "string", "name of the remote host", choices=find_host_ids())
definition.add_required("id", "positive_integer", "simulation ID")
definition.add_positional_optional("matching", "string", "only adapt settings with a name matching this string", suggestions=["remote"])

# -----------------------------------------------------------------

# Parse the arguments into a configuration
config = parse_arguments("change_analysis_options", definition, description="Change certain analysis options for a simulation")

# -----------------------------------------------------------------

# Open the simulation object
simulation = get_simulation_for_host(config.remote, config.id)

# -----------------------------------------------------------------

# Update
simulation.update_analysis_options()

# -----------------------------------------------------------------

# Check whether analysis options are defined
simulation.analysis.prompt_properties(contains=config.matching)

# -----------------------------------------------------------------

# Save the simulation
simulation.save()

# -----------------------------------------------------------------
