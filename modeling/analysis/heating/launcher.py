#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.analysis.heating.launch Contains the DustHeatingContributionLauncher class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import copy

# Import astronomical modules
from astropy.units import Unit

# Import the relevant PTS classes and modules
from .component import DustHeatingAnalysisComponent
from ....core.tools import filesystem as fs
from ....core.launch.batchlauncher import BatchLauncher
from ....core.simulation.definition import SingleSimulationDefinition
from ....core.tools.logging import log
from ...core.emissionlines import EmissionLines
from ....core.basics.range import RealRange
from ...fitting.wavelengthgrids import create_one_logarithmic_wavelength_grid

# -----------------------------------------------------------------

contributions = ["total", "old", "young", "ionizing", "unevolved"]
component_names = {"old": ["Evolved stellar bulge", "Evolved stellar disk"],
                    "young": "Young stars",
                    "ionizing": "Ionizing stars",
                    "unevolved": ["Young stars", "Ionizing stars"]}

# -----------------------------------------------------------------

class DustHeatingContributionLauncher(DustHeatingAnalysisComponent):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(DustHeatingContributionLauncher, self).__init__(config)

        # -- Attributes --

        # The SKIRT batch launcher
        self.launcher = BatchLauncher()

        # The analysis run
        self.analysis_run = None

        # Create directory for instruments created for investigating heating
        self.heating_instruments_path = None

        # The path to the wavelength grid file
        self.heating_wavelength_grid_path = None

        # The ski file for the model
        self.ski = None

        # The ski files for the different contributions
        self.ski_files = dict()

        # The paths to the simulation input files
        self.input_paths = None

        # The wavelength grid
        self.wavelength_grid = None

        # The instruments
        self.instruments = dict()

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # Create the wavelength grid
        self.create_wavelength_grid()

        # 4. Create the instruments
        self.create_instruments()

        # Set the simulation input
        self.set_input()

        # 5. Create the ski files for the different contributors
        self.adjust_ski()

        # 6. Writing
        self.write()

        # 7. Launch the simulations
        self.launch()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(DustHeatingContributionLauncher, self).setup()

        # Load the analysis run
        self.load_run()

        # Set options for the batch launcher
        self.set_launcher_options()

    # -----------------------------------------------------------------

    def load_run(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the analysis run " + self.config.run + " ...")

        # Get the run
        self.analysis_run = self.get_run(self.config.run)

        self.heating_instruments_path = fs.create_directory_in(self.analysis_run.path, "heating")

        self.heating_wavelength_grid_path = fs.join(self.)

    # -----------------------------------------------------------------

    def set_launcher_options(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting options for the batch simulation launcher ...")

        # Set options for the BatchLauncher
        self.launcher.config.shared_input = True  # The input directories for the different simulations are shared
        # self.launcher.config.group_simulations = True  # group multiple simulations into a single job
        self.launcher.config.remotes = self.config.remotes  # the remote hosts on which to run the simulations
        self.launcher.config.logging.verbose = True

    # -----------------------------------------------------------------

    def create_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the wavelength grid ...")

        # Create the emission lines instance
        emission_lines = EmissionLines()

        # Fixed wavelengths in the grid
        fixed = [self.i1_filter.pivotwavelength(), self.fuv_filter.pivotwavelength()] # in micron

        # Range in micron
        micron_range = RealRange(self.config.wg.range.min.to("micron").value, self.config.wg.range.max.to("micron").value)

        # Create and set the grid
        self.wavelength_grid = create_one_logarithmic_wavelength_grid(micron_range, self.config.wg.npoints, emission_lines, fixed)

    # -----------------------------------------------------------------

    def create_instruments(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the instruments ...")

        # Debugging
        log.debug("Creating a simple instrument for the earth projection ...")

        # Create the instrument and add it to the dictionary
        self.instruments["earth"] = self.create_instrument("simple", "earth")

        # Debugging
        log.debug("Creating a frame instrument for the faceon projection ...")

        # Create the instrument and add it to the dictionary
        self.instruments["faceon"] = self.create_instrument("frame", "faceon")

    # -----------------------------------------------------------------

    def set_input(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the input paths ...")

        # Set the paths to the input maps
        self.input_paths = self.input_map_paths

        # Determine and set the path to the wavelength grid file
        self.input_paths.append(self.heating_wavelength_grid_path)

    # -----------------------------------------------------------------

    def adjust_ski(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adjusting the ski files for simulating the different contributions ...")

        # Remove the existing instruments
        self.ski.remove_all_instruments()

        # Add the instruments
        for name in self.instruments: self.ski.add_instrument(self.instruments[name])

        # Parameters of the wavelength grid
        min_wavelength = self.config.wavelengths.min * Unit(self.config.wavelengths.unit)
        max_wavelength = self.config.wavelengths.max * Unit(self.config.wavelengths.unit)
        points = self.config.wavelengths.npoints

        # Set the logarithmic wavelength grid
        self.ski.set_log_wavelength_grid(min_wavelength, max_wavelength, points, write=True)

        # Set the number of photon packages
        self.ski.setpackages(self.config.npackages)

        # Set dust system writing options
        self.ski.set_write_convergence()
        self.ski.set_write_density()
        #self.ski.set_write_depth_map()
        #self.ski.set_write_quality()
        self.ski.set_write_cell_properties()
        #self.ski.set_write_cells_crossed()
        #self.ski.set_write_emissivity()
        #self.ski.set_write_temperature()
        #self.ski.set_write_isrf()
        self.ski.set_write_absorption()
        self.ski.set_write_grid()

        # Loop over the different contributions, create seperate ski file instance
        for contribution in self.contributions:

            # Debugging
            log.debug("Adjusting ski file for the contribution of the " + contribution + " stellar population ...")

            # Create a copy of the ski file instance
            ski = copy.deepcopy(self.ski)

            # Remove other stellar components, except for the contribution of the total stellar population
            if contribution != "total": ski.remove_stellar_components_except(self.component_names[contribution])

            # For the simulation with only the ionizing stellar component, also write out the stellar density
            if contribution == "ionizing": ski.set_write_stellar_density()

            # Add the ski file instance to the dictionary
            self.ski_files[contribution] = ski

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the wavelength grid
        self.write_wavelength_grid()

        # Write the instruments
        self.write_instruments()

        # Write the ski files
        self.write_ski_files()
        
    # -----------------------------------------------------------------

    def write_instruments(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the instruments ...")

        # Loop over the instruments
        for name in self.instruments:

            # Determine path
            path = fs.join(heating_instruments_path, name + ".instr")

            # Save
            self.instruments[name].save(path)

    # -----------------------------------------------------------------

    def write_ski_files(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the ski files ...")

        # Loop over the contributions
        for contribution in self.ski_files:

            # Determine the path to the ski file
            path = self.ski_paths[contribution]

            # Debugging
            log.debug("Writing the ski file for the " + contribution + " stellar population to '" + path + "' ...")

            # Save the ski file
            self.ski_files[contribution].saveto(path)

    # -----------------------------------------------------------------

    def launch(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching the simulations ...")

        # Determine the path to the analysis/heating/scripts path (store batch scripts there for manual inspection)
        scripts_path = fs.join(self.analysis_heating_path, "scripts")
        if not fs.is_directory(scripts_path): fs.create_directory(scripts_path)
        for host_id in self.launcher.host_ids:
            script_dir_path = fs.join(scripts_path, host_id)
            if not fs.is_directory(script_dir_path): fs.create_directory(script_dir_path)
            self.launcher.set_script_path(host_id, script_dir_path)

        # Set the paths to the screen output directories (for debugging) for remotes without a scheduling system for jobs
        for host_id in self.launcher.no_scheduler_host_ids: self.launcher.enable_screen_output(host_id)

        # Loop over the contributions
        for contribution in self.ski_paths:

            # Determine a name for this simulation
            simulation_name = self.galaxy_name + "_heating_" + contribution

            # Get the ski path for this simulation
            ski_path = self.ski_paths[contribution]

            # Get the local output path for the simulation
            output_path = self.output_paths[contribution]

            # Create the SKIRT simulation definition
            definition = SingleSimulationDefinition(ski_path, self.analysis_in_path, output_path)

            # Debugging
            log.debug("Adding the simulation of the contribution of the " + contribution + " stellar population to the queue ...")

            # Put the parameters in the queue and get the simulation object
            self.launcher.add_to_queue(definition, simulation_name)

            # Set scheduling options (for the different remote hosts with a scheduling system)
            #for host_id in self.scheduling_options: self.launcher.set_scheduling_options(host_id, simulation_name, self.scheduling_options[host_id])

        # Run the launcher, schedules the simulations
        simulations = self.launcher.run()

        # Loop over the scheduled simulations (if something has to be set)
        #for simulation in simulations: pass

# -----------------------------------------------------------------
