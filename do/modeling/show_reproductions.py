#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.evolve.show_reproductions Show the reproductions.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition, ArgumentConfigurationSetter
from pts.core.tools.logging import setup_log
from pts.core.tools import filesystem as fs
from pts.modeling.fitting.component import get_run_names
from pts.modeling.core.environment import GalaxyModelingEnvironment
from pts.modeling.fitting.component import load_fitting_run

# -----------------------------------------------------------------

modeling_path = fs.cwd()

# -----------------------------------------------------------------

# Create configuration definition
definition = ConfigurationDefinition()
run_names = get_run_names(modeling_path)
if len(run_names) == 0: raise RuntimeError("There are no fitting runs")
elif len(run_names) == 1: definition.add_fixed("fitting_run", "string", run_names[0])
else: definition.add_required("fitting_run", "string", "name of the fitting run to use", choices=run_names)

# Generation
definition.add_positional_optional("generations", "string_list", "name of the generations for which to show the reproductions")

# Create the configuration
setter = ArgumentConfigurationSetter("show_reproductions")
config = setter.run(definition)

# Set logging
log = setup_log("DEBUG")

# -----------------------------------------------------------------

# Load the modeling environment
environment = GalaxyModelingEnvironment(modeling_path)

# -----------------------------------------------------------------

# Load the fitting run
fitting_run = load_fitting_run(modeling_path, config.fitting_run)
#print(fitting_run.parameter_base_types)

# -----------------------------------------------------------------

# Get generation names
generations = config.generations if config.generations is not None else fitting_run.genetic_generations

# -----------------------------------------------------------------

print("")

# Loop over the generations
for generation_name in generations:

    print(generation_name)
    print("")

    # Get the generation
    generation = fitting_run.get_generation(generation_name)
    platform = fitting_run.get_generation_platform(generation_name)

    # -----------------------------------------------------------------

    # Show
    platform.show_reproductions()

# -----------------------------------------------------------------
