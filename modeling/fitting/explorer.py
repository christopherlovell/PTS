#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.explorer Contains the ParameterExplorer class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import astronomical modules
from astropy.units import Unit

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.tools.logging import log
from ...core.tools import filesystem as fs
from ...core.launch.batchlauncher import BatchLauncher
from .modelgenerators.grid import GridModelGenerator
from .modelgenerators.initial import InitialModelGenerator
from .modelgenerators.genetic import GeneticModelGenerator
from .modelgenerators.instinctive import InstinctiveModelGenerator
from ...core.tools import time
from ...core.basics.range import range_around
from ...core.simulation.definition import SingleSimulationDefinition
from .tables import ParametersTable, ChiSquaredTable
from ...core.launch.options import SchedulingOptions
from ...core.advanced.runtimeestimator import RuntimeEstimator
from ...core.tools.stringify import stringify_not_list, stringify
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ...core.advanced.parallelizationtool import ParallelizationTool
from ...core.remote.host import Host

# -----------------------------------------------------------------

class ParameterExplorer(FittingComponent):
    
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
        super(ParameterExplorer, self).__init__(config)

        # -- Attributes --

        # The SKIRT batch launcher
        self.launcher = BatchLauncher()

        # The generation info
        self.generation_info = dict()

        # The parameters table
        self.parameters_table = None

        # The chi squared table
        self.chi_squared_table = None

        # The parameter ranges
        self.ranges = dict()

        # The generation index and name
        self.generation_index = None
        self.generation_name = None

        # The model generator
        self.generator = None

        # The paths to the simulation input files
        self.input_paths = None

        # A dictionary with the scheduling options for the different remote hosts
        self.scheduling_options = dict()

        # The number of wavelengths used
        self.nwavelengths = None

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Set the parameter ranges
        self.set_ranges()

        # 3. Set the generation info
        self.set_info()

        # 4. Create the generation directory
        self.create_generation_directory()

        # 5. Generate the model parameters
        self.generate_models()

        # 6. Set the paths to the input files
        if self.needs_input: self.set_input()

        # 7. Adjust the ski template
        self.adjust_ski()

        # 8. Set the parallelization schemes for the different remote hosts
        if self.uses_schedulers: self.set_parallelization()

        # 9. Estimate the runtimes for the different remote hosts
        if self.uses_schedulers: self.estimate_runtimes()

        # 10. Launch the simulations for different parameter values
        self.launch()

        # 11. Writing
        self.write()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(ParameterExplorer, self).setup()

        # Set options for the batch launcher
        self.set_launcher_options()

        # Set the model generator
        self.set_generator()

        # Check whether this is not the first generation so that we can use remotes with a scheduling system
        #if self.ngenerations == 0 and self.uses_schedulers:
        #    raise ValueError("The specified remote hosts cannot be used for the first generation: at least one remote uses a scheduling system")

        # Check whether initialize_fit has been called
        if self.modeling_type == "galaxy":
            if not fs.is_file(self.wavelength_grids_table_path): raise RuntimeError("Call initialize_fit_galaxy before starting the parameter exploration")
            if not fs.is_file(self.dust_grids_table_path): raise RuntimeError("Call initialize_fit_galaxy before starting the parameter exploration")

    # -----------------------------------------------------------------

    def set_launcher_options(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting options for the batch simulation launcher ...")

        # Set remote host IDs
        remote_host_ids = []
        if self.ngenerations == 0:
            for host_id in self.config.remotes:
                if Host(host_id).scheduler: log.warning("Not using remote host '" + host_id + "' for the initial generation because it uses a scheduling system for launching jobs")
                else: remote_host_ids.append(host_id)
        else: remote_host_ids = self.config.remotes

        # Basic options
        self.launcher.config.shared_input = True                               # The input directories (or files) for the different simulations are shared
        self.launcher.config.remotes = remote_host_ids                         # the remote host(s) on which to run the simulations
        self.launcher.config.group_simulations = self.config.group             # group multiple simulations into a single job (because a very large number of simulations will be scheduled) TODO: IMPLEMENT THIS
        self.launcher.config.group_walltime = self.config.walltime             # the preferred walltime for jobs of a group of simulations
        self.launcher.config.timing_table_path = self.timing_table_path        # The path to the timing table file
        self.launcher.config.memory_table_path = self.memory_table_path        # The path to the memory table file
        self.launcher.config.cores_per_process = self.config.cores_per_process # the number of cores per process, for non-schedulers
        self.launcher.config.dry = self.config.dry                             # dry run (don't actually launch simulations)

        # Simulation analysis options

        ## General
        self.launcher.config.analysis.relative = True

        ## Logging
        self.launcher.config.logging.verbose = True
        self.launcher.config.logging.memory = True
        #self.launcher.config.logging.allocation = True
        #self.launcher.config.logging.allocation_limit = 1e-5

        ## Extraction
        self.launcher.config.analysis.extraction.path = "extr"    # name of the extraction directory
        self.launcher.config.analysis.extraction.progress = True  # extract progress information
        self.launcher.config.analysis.extraction.timeline = True  # extract the simulation timeline
        self.launcher.config.analysis.extraction.memory = True    # extract memory information

        ## Plotting
        self.launcher.config.analysis.plotting.path = "plot"  # name of the plot directory
        self.launcher.config.analysis.plotting.seds = True    # Plot the output SEDs
        self.launcher.config.analysis.plotting.reference_seds = [self.observed_sed_path]  # the path to the reference SED (for plotting the simulated SED against the reference points)
        self.launcher.config.analysis.plotting.format = "png"  # plot in PNG format so that an animation can be made from the fit SEDs

        ## Miscellaneous
        self.launcher.config.analysis.misc.path = "misc"       # name of the misc output directory
        self.launcher.config.analysis.misc.fluxes = True       # calculate observed fluxes
        self.launcher.config.analysis.misc.observation_filters = self.observed_filter_names

        # Set the path to the modeling directory to the simulation object
        self.launcher.config.analysis.modeling_path = self.config.path

        # Set analyser classes
        self.launcher.config.analysers = ["pts.modeling.fitting.modelanalyser.FitModelAnalyser"]

    # -----------------------------------------------------------------

    def set_generator(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the model generator ...")

        # Generate new models based on a simple grid (linear or logarithmic) of parameter values
        if self.config.generation_method == "grid":

            # Set a name for the generation
            self.generation_name = time.unique_name()

            # Create the model generator
            self.generator = GridModelGenerator()

        # Generate new models instinctively based on the current probability distribution of the parameters
        elif self.config.generation_method == "instinctive":

            # Set a name for the generation
            self.generation_name = time.unique_name()

            # Create the model generator
            self.generator = InstinctiveModelGenerator()

        # Generate new models using genetic algorithms
        elif self.config.generation_method == "genetic":

            if "initial" in self.generation_names:

                # Set index and name
                self.generation_index = self.last_genetic_generation_index + 1
                self.generation_name = str("Generation " + str(self.generation_index))

                # Create the model generator
                self.generator = GeneticModelGenerator()

            else:

                # Set the generation name
                self.generation_name = "initial"

                # Create the model generator
                self.generator = InitialModelGenerator()

        # Create the configuration for the generator
        from ...core.basics.configuration import Configuration
        config = Configuration()
        config.path = self.config.path
        config.generation_name = self.generation_name
        config.nmodels = self.config.nsimulations
        config.crossover_rate = self.config.crossover_rate
        config.mutation_rate = self.config.mutation_rate

        # Set the config
        self.generator.config = config

    # -----------------------------------------------------------------

    def set_ranges(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parameter ranges ...")

        # The given ranges are relative to the best or initial value
        if self.config.relative:

            # Check if there are any models that have been evaluated
            if self.has_evaluated_models:

                # Inform the user
                log.info("Determining the parameter ranges based on the current best values and the specified relative ranges ...")

                # Get the best model
                model = self.best_model

                # Debugging
                log.debug("Using the parameter values of simulation '" + model.simulation_name + "' of generation '" + model.generation_name + "' ...")

                # Get the parameter values of the best model
                parameter_values = model.parameter_values

            else:

                # Inform the user
                log.info("Determining the parameter ranges based on the first guess values and the specified relative ranges ...")

                # Get the initial guess values
                parameter_values = self.first_guess_parameter_values

            # Debugging
            log.debug("The values that are used as the centers of the ranges are:")

            # Loop over the free parameter labels
            for label in self.free_parameter_labels:

                # Get the best value (or initial value in the case no generations were lauched yet)
                value = parameter_values[label]

                # Debugging
                log.debug(" - " + label + ": " + str(value))

                # Calculate the range
                rel_min = self.config[label + "_range"].min
                rel_max = self.config[label + "_range"].max
                self.ranges[label] = range_around(value, rel_min, rel_max)

        else:

            # Inform the user
            log.info("Using the specified ranges ...")

            # Loop over the free parameter labels
            for label in self.free_parameter_labels:

                # Get the range
                parameter_range = self.config[label + "_range"]
                if parameter_range is None: parameter_range = self.free_parameter_ranges[label] # absolute range

                # Set the range
                self.ranges[label] = parameter_range

        # Set the ranges for the generator
        for label in self.ranges: self.generator.add_parameter(label, self.ranges[label])

    # -----------------------------------------------------------------

    def generate_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the model parameters ...")

        # Run the model generator
        self.generator.run()

    # -----------------------------------------------------------------

    def set_info(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the generation info ...")

        # Get the previous wavelength grid level
        wavelength_grid_level = self.current_wavelength_grid_level
        dust_grid_level = self.current_dust_grid_level

        # Increase the wavelength grid or dust grid level if requested
        if self.config.refine_wavelengths:
            if wavelength_grid_level == self.highest_wavelength_grid_level: log.warning("Cannot refine wavelength grid: highest level reached (" + str(wavelength_grid_level) + ")")
            else: wavelength_grid_level += 1
        if self.config.refine_dust:
            if dust_grid_level == self.highest_dust_grid_level: log.warning("Cannot refine dust grid: highest level reached (" + str(dust_grid_level) + ")")
            else: dust_grid_level += 1

        # Set the generation info
        self.generation_info["Generation name"] = self.generation_name
        self.generation_info["Generation index"] = self.generation_index
        self.generation_info["Method"] = self.config.generation_method
        self.generation_info["Wavelength grid level"] = wavelength_grid_level
        self.generation_info["Dust grid level"] = dust_grid_level
        self.generation_info["Number of simulations"] = self.config.nsimulations
        self.generation_info["Number of photon packages"] = self.config.npackages
        self.generation_info["Self-absorption"] = self.config.selfabsorption
        self.generation_info["Transient heating"] = self.config.transient_heating

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

        # Determine and set the path to the appropriate wavelength grid file
        wavelength_grid_path = self.wavelength_grid_path_for_level(self.generation_info["Wavelength grid level"])
        self.input_paths.append(wavelength_grid_path)

        # Get the number of wavelengths
        self.nwavelengths = len(WavelengthGrid.from_skirt_input(wavelength_grid_path))

        # Debugging
        log.debug("The wavelength grid for the simulations contains " + str(self.nwavelengths) + " wavelength points")

    # -----------------------------------------------------------------

    def create_generation_directory(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the generation directory")

        # Determine the path to the generation directory
        self.generation_info["Path"] = fs.create_directory_in(self.fit_generations_path, self.generation_name)

        # Determine the path to the generation parameters table
        self.generation_info["Parameter table path"] = fs.join(self.generation_info["Path"], "parameters.dat")

        # Determine the path to the chi squared table
        self.generation_info["Chi squared table path"] = fs.join(self.generation_info["Path"], "chi_squared.dat")

        # Initialize the parameters table
        self.parameters_table = ParametersTable(parameters=self.free_parameter_labels, units=self.parameter_units)

        # Initialize the chi squared table
        self.chi_squared_table = ChiSquaredTable()

    # -----------------------------------------------------------------

    def adjust_ski(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Adjusting the ski template for the properties of this generation ...")

        # Set packages
        self.set_npackages()

        # Set self-absoprtion
        self.set_selfabsorption()

        # Set transient heating
        self.set_transient_heating()

        # Set wavelength grid
        if self.has_wavelength_grids: self.set_wavelength_grid()

        # Set dust grid
        if self.has_dust_grids: self.set_dust_grid()

    # -----------------------------------------------------------------

    def set_npackages(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the number of photon packages to " + str(self.config.npackages) + " ...")

        # Set the number of photon packages per wavelength
        self.ski_template.setpackages(self.config.npackages)

    # -----------------------------------------------------------------

    def set_selfabsorption(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Enabling dust self-absorption ..." if self.config.selfabsorption else "Disabling dust self-absorption ...")

        # Set dust self-absorption
        if self.config.selfabsorption: self.ski_template.enable_selfabsorption()
        else: self.ski_template.disable_selfabsorption()

    # -----------------------------------------------------------------

    def set_transient_heating(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Enabling transient heating ..." if self.config.transient_heating else "Disabling transient heating ...")

        # Set transient heating
        if self.config.transient_heating: self.ski_template.set_transient_dust_emissivity()
        else: self.ski_template.set_grey_body_dust_emissivity()

    # -----------------------------------------------------------------

    def set_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the name of the wavelengths file to " + fs.name(self.wavelength_grid_path_for_level(self.generation_info["Wavelength grid level"])) + " ...")

        # Set the name of the wavelength grid file
        self.ski_template.set_file_wavelength_grid(fs.name(self.wavelength_grid_path_for_level(self.generation_info["Wavelength grid level"])))

    # -----------------------------------------------------------------

    def set_dust_grid(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the dust grid (level " + str(self.generation_info["Dust grid level"]) + ") ...")

        # Set the dust grid
        self.ski_template.set_dust_grid(self.dust_grid_for_level(self.generation_info["Dust grid level"]))

    # -----------------------------------------------------------------

    def set_parallelization(self):

        """
        This function sets the parallelization scheme for those remote hosts used by the batch launcher that use
        a scheduling system (the parallelization for the other hosts is left up to the batch launcher and will be
        based on the current load of the corresponding system).
        :return:
        """

        # Inform the user
        log.info("Setting the parallelization scheme for the remote host(s) that use a scheduling system ...")

        # Loop over the IDs of the hosts used by the batch launcher that use a scheduling system
        for host in self.launcher.scheduler_hosts:

            # Create the parallelization tool
            tool = ParallelizationTool()

            # Set configuration options
            tool.config.ski = self.ski_template
            tool.config.input = self.input_paths

            # Set host properties
            tool.config.nnodes = self.config.nnodes
            tool.config.nsockets = host.cluster.sockets_per_node
            tool.config.ncores = host.cluster.cores_per_sockets
            tool.config.memory = host.cluster.memory

            # MPI available and used
            tool.config.mpi = True
            tool.config.hyperthreading = False # no hyperthreading
            #tool.config.threads_per_core = None

            # Number of dust cells
            tool.config.ncells = None # number of dust cells (relevant if ski file uses a tree dust grid)

            # Run the tool
            tool.run()

            # Get the parallelization
            parallelization = tool.parallelization

            # Get the parallelization scheme for this host
            #parallelization = Parallelization.for_host(host, self.config.nnodes, self.config.data_parallel)

            # Debugging
            log.debug("Parallelization scheme for host " + host.id + ": " + str(parallelization))

            # Set the parallelization for this host
            self.launcher.set_parallelization_for_host(host.id, parallelization)

    # -----------------------------------------------------------------

    def estimate_runtimes(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the runtimes based on the results of previously finished simulations ...")

        # Create a RuntimeEstimator instance
        estimator = RuntimeEstimator.from_file(self.timing_table_path)

        # Initialize a dictionary to contain the estimated walltimes for the different hosts with scheduling system
        walltimes = dict()

        # Loop over the hosts which use a scheduling system and estimate the walltime
        for host in self.launcher.scheduler_hosts:

            # Debugging
            log.debug("Estimating the runtime for host '" + host.id + "' ...")

            # Get the parallelization scheme that we have defined for this remote host
            parallelization = self.launcher.parallelization_for_host(host.id)

            # Visualisation of the distribution of estimated runtimes
            if self.config.visualise: plot_path = fs.join(self.visualisation_path, time.unique_name("explorer_runtimes_" + host.id) + ".pdf")
            else: plot_path = None

            # Estimate the runtime for the current number of photon packages and the current remote host
            runtime = estimator.runtime_for(self.ski_template, parallelization, host.id, host.cluster_name, self.config.data_parallel, nwavelengths=self.nwavelengths)

            # Debugging
            log.debug("The estimated runtime for this host is " + str(runtime) + " seconds")

            # Set the estimated walltime
            walltimes[host.id] = runtime

        # Create and set scheduling options for each host that uses a scheduling system
        for host_id in walltimes: self.scheduling_options[host_id] = SchedulingOptions.from_dict({"walltime": walltimes[host_id]})

    # -----------------------------------------------------------------

    def launch(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching the simulations ...")

        # Set the paths to the directories to contain the launch scripts (job scripts) for the different remote hosts
        # Just use the directory created for the generation
        for host_id in self.launcher.host_ids: self.launcher.set_script_path(host_id, self.generation_info["Path"])

        # Enable screen output logging for remotes without a scheduling system for jobs
        for host_id in self.launcher.no_scheduler_host_ids: self.launcher.enable_screen_output(host_id)

        # Loop over the different parameter combinations
        for i in range(self.nmodels):

            # Set the parameter values as a dictionary for this individual model
            parameter_values = dict()
            for label in self.free_parameter_labels:

                # Get the value for this model from the generator and get the unit defined for this parameter
                value = self.generator.parameters[label][i]

                # Set value with unit
                if self.parameter_units[label] is not None:
                    unit = Unit(self.parameter_units[label])
                    parameter_values[label] = value * unit

                # Set dimensionless value
                else: parameter_values[label] = value

            # Debugging
            log.debug("Adjusting ski file for the following model parameters:")
            for label in parameter_values: log.debug(" - " + label + ": " + stringify_not_list(parameter_values[label])[1])

            # Create a unique name for this combination of parameter values
            simulation_name = time.unique_name()

            # For the luminosity of SpectralLuminosityNormalization components, convert to W/m
            #for label in parameter_values:
            #    if label == "fuv_young" or label == "fuv_ionizing" or label == "i1_old":
            #        parameter_values[label] = parameter_values[label].to("W/m").value

            # Set the parameter values in the ski file template
            self.ski_template.set_labeled_values(parameter_values)

            # Create a directory for this simulation
            simulation_path = fs.create_directory_in(self.generation_info["Path"], simulation_name)

            # Create an output directory for this simulation
            simulation_output_path = fs.create_directory_in(simulation_path, "out")

            # Put the ski file with adjusted parameters into the simulation directory
            ski_path = fs.join(simulation_path, self.object_name + ".ski")
            self.ski_template.saveto(ski_path)

            # Create the SKIRT simulation definition
            definition = SingleSimulationDefinition(ski_path, simulation_output_path, self.input_paths)

            # Debugging
            log.debug("Adding a simulation to the queue with:")
            log.debug(" - name: " + simulation_name)
            log.debug(" - input: " + stringify(self.input_paths)[1])
            log.debug(" - ski path: " + definition.ski_path)
            log.debug(" - output path: " + definition.output_path)

            # Put the parameters in the queue and get the simulation object
            self.launcher.add_to_queue(definition, simulation_name)

            # Set scheduling options (for the different remote hosts with a scheduling system)
            for host_id in self.scheduling_options: self.launcher.set_scheduling_options(host_id, simulation_name, self.scheduling_options[host_id])

            # Add an entry to the parameters table
            self.parameters_table.add_entry(simulation_name, parameter_values)

        # Run the launcher, schedules the simulations
        simulations = self.launcher.run()

    # -----------------------------------------------------------------

    @property
    def nmodels(self):

        """
        This function ...
        :return:
        """

        return self.generator.nmodels

    # -----------------------------------------------------------------

    @property
    def uses_schedulers(self):

        """
        This function ...
        :return:
        """

        return self.launcher.uses_schedulers

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write the generation info
        self.write_generation()

        # Write the parameters table
        self.write_parameters()

        # Write the (empty) chi squared table
        self.write_chi_squared()

    # -----------------------------------------------------------------

    def write_generation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing generation info ...")

        # Generate a timestamp
        timestamp = time.timestamp()

        # Add an entry to the generations table
        name = self.generation_info["Generation name"]
        index = self.generation_info["Generation index"]
        method = self.generation_info["Method"]
        wg_level = self.generation_info["Wavelength grid level"]
        dg_level = self.generation_info["Dust grid level"]
        nsimulations = self.generation_info["Number of simulations"]
        npackages = self.generation_info["Number of photon packages"]
        selfabsorption = self.generation_info["Self-absorption"]
        transientheating = self.generation_info["Transient heating"]
        self.generations_table.add_entry(name, index, timestamp, method, wg_level, dg_level, nsimulations, npackages, selfabsorption, transientheating, self.ranges)

        # Save the table
        self.generations_table.save()

    # -----------------------------------------------------------------

    def write_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the parameter values ...")

        # Save the parameters table
        self.parameters_table.saveto(self.generation_info["Parameter table path"])

    # -----------------------------------------------------------------

    def write_chi_squared(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the chi squared table ...")

        # Save the chi squared table
        self.chi_squared_table.saveto(self.generation_info["Chi squared table path"])

# -----------------------------------------------------------------
