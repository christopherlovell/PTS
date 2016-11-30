#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import the relevant PTS classes and modules
from pts.core.basics.configuration import ConfigurationDefinition

# -----------------------------------------------------------------

# Choices and choices of the different parameters
choices = dict()
choices["distance"] = "distance of the galaxy"
choices["ionizing_scaleheight"] = "scale height of the ionizing stellar component"
choices["sfr_compactness"] = "compactness parameter of the star formation regions"
choices["fuv_young"] = "FUV luminosity of the young stellar component"
choices["old_scaleheight"] = "scale height of the old stellar disk component"
choices["position_angle"] = "position angle of the galaxy"
choices["dust_mass"] = "dust mass"
choices["fuv_ionizing"] = "FUV luminosity of the ionizing stellar component"
choices["metallicity"] = "metallicity"
choices["young_scaleheight"] = "scale height of the young stellar component"
choices["sfr_covering"] = "covering factor of the star formation regions"
choices["dust_scaleheight"] = "scale height of the dust component"
choices["i1_old"] = "I1 luminosity of the old stellar component"
choices["sfr_pressure"] = "pressure on the star formation regions"
choices["inclination"] = "inclination of the galactic plane"

# Types and ranges of the different parameters
types_and_ranges = dict()
types_and_ranges["distance"] = ("quantity", None)
types_and_ranges["ionizing_scaleheight"] = ("quantity", None)
types_and_ranges["sfr_compactness"] = ("quantity", None)
types_and_ranges["fuv_young"] = ("quantity", "0.0 W/micron>1e37 W/micron")
types_and_ranges["old_scaleheight"] = ("quantity", None)
types_and_ranges["position_angle"] = ("angle", None)
types_and_ranges["dust_mass"] = ("quantity", "0.5e7 Msun>3.e7 Msun")
types_and_ranges["fuv_ionizing"] = ("quantity", "0.0 W/micron>1e34 W/micron")
types_and_ranges["metallicity"] = ("real", None)
types_and_ranges["young_scaleheight"] = ("quantity", None)
types_and_ranges["sfr_covering"] = ("real", None)
types_and_ranges["dust_scaleheight"] = ("quantity", None)
types_and_ranges["i1_old"] = ("real", None)
types_and_ranges["sfr_pressure"] = ("quantity", None)
types_and_ranges["inclination"] = ("angle", None)

# Default units of the different parameters
units = dict()
units["distance"] = "Mpc"
units["ionizing_scaleheight"] = "pc"
# sfr_compactness: no unit
units["fuv_young"] = "W/micron"
units["old_scaleheight"] = "pc"
units["position_angle"] = "deg"
units["dust_mass"] = "Msun"
units["fuv_ionizing"] = "W/micron"
# metallicity: no unit
units["young_scaleheight"] = "pc"
# sfr_covering: no unit
units["dust_scaleheight"] = "pc"
units["i1_old"] = "W/micron"
units["sfr_pressure"] = "K/m3"
units["inclination"] = "deg"

# -----------------------------------------------------------------

# Create the configuration
definition = ConfigurationDefinition(write_config=False)

# Add the required setting of the list of free parameters
definition.add_required("free_parameters", "string_list", "parameters to be used as free parameters during the fitting", choices=choices)

# -----------------------------------------------------------------
