#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.modelanalyser Contains the ModelAnalyser class, used for analysing the goodness
#  of the radiative transfer model.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import numpy as np

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.tools.logging import log
from ...core.tools import filesystem, tables
from ..core.sed import ObservedSED

# -----------------------------------------------------------------

class ModelAnalyser(FittingComponent):

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
        super(ModelAnalyser, self).__init__(config)

        # -- Attributes --

        # Set the simulation object to None initially
        self.simulation = None

        # The flux calculator
        self.flux_calculator = None

        # The weights given to each band for the calculation of the chi squared
        self.weights = None

        # The observed fluxes
        self.fluxes = None

        # The flux differences table
        self.differences = None

        # The calculated chi squared value
        self.chi_squared = None

    # -----------------------------------------------------------------

    def run(self, simulation, flux_calculator):

        """
        This function ...
        :param simulation:
        :param flux_calculator:
        :return:
        """

        # 1. Call the setup function
        self.setup(simulation, flux_calculator)

        # 2. Load the observed SED
        self.load_observed_sed()

        # 3. Calculate the differences
        self.calculate_differences()

        # 4. Calculate the chi squared for this model
        self.calculate_chi_squared()

        # 5. Write
        self.write()

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Clearing the model analyser ...")

        # Set the attributes to default values
        self.simulation = None
        self.flux_calculator = None
        self.fluxes = None
        self.differences = None
        self.chi_squared = None

    # -----------------------------------------------------------------

    def setup(self, simulation, flux_calculator):

        """
        This function ...
        :param simulation:
        :param flux_calculator:
        :return:
        """

        # Call the setup function of the base class
        super(ModelAnalyser, self).setup()

        # Make a local reference to the simulation object
        self.simulation = simulation

        # Make a local reference to the flux calculator
        if flux_calculator is None:
            raise RuntimeError("No ObservedFluxCalculator found; the calculate_observed_fluxes flag must be enabled on "
                               "each simulation that is part of the radiative transfer modeling")
        self.flux_calculator = flux_calculator

        # Load the weights table
        self.weights = tables.from_file(self.weights_table_path, fix_float=True) # For some reason, the weights are parsed as strings instead of floats (but not from the command line!!??)

        # Initialize the differences table
        names = ["Instrument", "Band", "Flux difference", "Relative difference", "Chi squared term"]
        data = [[], [], [], [], []]
        dtypes = ["S5", "S7", "float64", "float64", "float64"]
        self.differences = tables.new(data, names, dtypes=dtypes)

    # -----------------------------------------------------------------

    def load_observed_sed(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the observed SED ...")

        # Determine the path to the fluxes table
        fluxes_path = filesystem.join(self.phot_path, "fluxes.dat")

        # Load the observed SED
        self.fluxes = ObservedSED.from_file(fluxes_path)

    # -----------------------------------------------------------------

    def calculate_differences(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the differences between the observed and simulated SED ...")

        # In the flux-density tables derived from the simulation (created by the ObservedFluxCalculator object),
        # search the one corresponding to the "earth" instrument
        table_name = self.galaxy_name + "_earth"
        if table_name not in self.flux_calculator.tables: raise RuntimeError("Could not find a flux-density table for the 'earth' instrument")

        # Get the table
        table = self.flux_calculator.tables[table_name]

        print(self.weights)

        # Loop over the entries in the fluxdensity table (SED) derived from the simulation
        for i in range(len(table)):

            #observatory = table["Observatory"][i]
            instrument = table["Instrument"][i]
            band = table["Band"][i]
            wavelength = table["Wavelength"][i]
            fluxdensity = table["Flux"][i]

            # Find the corresponding flux in the SED derived from observation
            observed_fluxdensity = self.fluxes.flux_for_band(instrument, band, unit="Jy").value

            # Find the corresponding flux error in the SED derived from observation
            observed_fluxdensity_error = self.fluxes.error_for_band(instrument, band, unit="Jy").average.to("Jy").value

            # If no match with (instrument, band) is found in the observed SED
            if observed_fluxdensity is None:
                log.warning("The observed flux density could not be found for the " + instrument + " " + band + " band")
                continue

            difference = fluxdensity - observed_fluxdensity
            relative_difference = difference / observed_fluxdensity

            # Find the index of the current band in the weights table
            index = tables.find_index(self.weights, key=[instrument, band], column_name=["Instrument", "Band"])

            # Get the weight
            weight = self.weights["Weight"][index] # apparently, this is a string, so parsing the table went wrong ...
            weight = float(weight)

            # Calculate the chi squared term
            chi_squared_term = weight * difference ** 2 / observed_fluxdensity_error ** 2

            # Add an entry to the differences table
            self.differences.add_row([instrument, band, difference, relative_difference, chi_squared_term])

    # -----------------------------------------------------------------

    def calculate_chi_squared(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Calculating the chi squared value for this model ...")

        # The chi squared value is the sum of all the terms (for each band)
        self.chi_squared = np.sum(self.differences["Chi squared term"])

        # Debugging
        log.debug("Found a chi squared value of " + str(self.chi_squared))

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the flux differences
        self.write_differences()

        # Write the chi-squared value
        self.write_chi_squared()

    # -----------------------------------------------------------------

    def write_differences(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the table with the flux-density differences for the current model ...")

        # Determine the path to the differences table
        path = filesystem.join(self.fit_res_path, self.simulation.name, "differences.dat")

        # Save the differences table
        tables.write(self.differences, path)

    # -----------------------------------------------------------------

    def write_chi_squared(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adding the chi squared value for the current model to the chi squared data file ...")

        # Open the chi squared file (in 'append' mode)
        resultfile = open(self.chi_squared_table_path, 'a')

        # Add a line to the chi squared file containing the simulation name and the chi squared value
        resultfile.write(self.simulation.name + " " + str(self.chi_squared) + "\n")

        # Close the output file
        resultfile.close()

# -----------------------------------------------------------------
