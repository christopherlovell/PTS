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

# Import the relevant PTS classes and modules
from .component import FittingComponent
from ...core.basics.log import log
from ...core.tools import filesystem as fs
from ...core.launch.batchlauncher import BatchLauncher
from .modelgenerators.grid import GridModelGenerator
from .modelgenerators.genetic import GeneticModelGenerator
from ...core.tools import time
from .tables import ParametersTable, ChiSquaredTable, IndividualsTable
from ...core.launch.options import SchedulingOptions
from ...core.advanced.runtimeestimator import RuntimeEstimator
from ...core.tools.stringify import stringify_not_list, stringify
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ...core.advanced.parallelizationtool import ParallelizationTool
from ...core.remote.host import load_host
from ...core.basics.configuration import ConfigurationDefinition, create_configuration_interactive
from .evaluate import prepare_simulation, generate_simulation_name, get_parameter_values_for_named_individual
from ...core.simulation.input import SimulationInput
from ...core.tools import introspection
from ...core.tools import parallelization as par
from .generation import GenerationInfo, Generation
from ...core.tools.stringify import tostr
from ...core.basics.configuration import prompt_proceed
from ...core.prep.smile import SKIRTSmileSchema
from ...core.tools.utils import lazyproperty
from ...core.prep.deploy import Deployer

# -----------------------------------------------------------------

class ParameterExplorer(FittingComponent):
    
    """
    This class...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(ParameterExplorer, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The fitting run
        self.fitting_run = None

        # The ski template
        self.ski = None

        # The SKIRT batch launcher
        self.launcher = BatchLauncher()

        # The generation info
        self.generation_info = GenerationInfo()

        # The generation object
        self.generation = None

        # The model representation to use
        self.representation = None

        # The individuals table
        self.individuals_table = None

        # The parameters table
        self.parameters_table = None

        # The chi squared table
        self.chi_squared_table = None

        # The parameter ranges
        self.ranges = dict()

        # Initf ngemgeg
        self.fixed_initial_parameters = None

        # The generation index and name
        self.generation_index = None
        self.generation_name = None

        # The model generator
        self.generator = None

        # The simulation input
        self.simulation_input = None

        # A dictionary with the scheduling options for the different remote hosts
        self.scheduling_options = dict()

        # The number of wavelengths used
        self.nwavelengths = None

        # Extra input for the model generator
        self.scales = None
        self.most_sampled_parameters = None
        self.sampling_weights = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Load the ski template
        self.load_ski()

        # 3. Set the parameter ranges
        if not self.has_all_ranges: self.set_ranges()

        # 4. Set the generation info
        self.set_info()

        # 5. Create the generation
        self.create_generation()

        # 6. Generate the model parameters
        self.generate_models()

        # 7. Set the paths to the input files
        if self.fitting_run.needs_input: self.set_input()

        # 8. Adjust the ski template
        self.adjust_ski()

        # 9. Set the parallelization scheme for local execution if necessary
        if self.only_local: self.set_parallelization_local()

        # 10. Set the parallelization schemes for the different remote hosts
        if self.uses_schedulers: self.set_parallelization_remote()

        # 11. Estimate the runtimes for the different remote hosts
        if self.uses_schedulers: self.estimate_runtimes()

        # 12. Fill the tables for the current generation
        self.fill_tables()

        # 13. Writing
        self.write()

        # 14. Launch the simulations for different parameter values
        # Test whether simulations are required, because if the optimizer detects recurrence of earlier models,
        # it is possible that no simulations have to be done
        if self.needs_simulations: self.launch()
        else: self.set_finishing_time()

    # -----------------------------------------------------------------

    @property
    def uses_remotes(self):

        """
        This function ...
        :return:
        """

        return self.launcher.uses_remotes

    # -----------------------------------------------------------------

    @property
    def only_local(self):

        """
        This function ...
        :return:
        """

        return self.launcher.only_local

    # -----------------------------------------------------------------

    @property
    def has_all_ranges(self):

        """
        This function ...
        :return:
        """

        # Loop over the free parameter labels
        for label in self.fitting_run.free_parameter_labels:

            # If range is already defined
            if label not in self.ranges: return False

        # All ranges are defined
        return True

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(ParameterExplorer, self).setup(**kwargs)

        # Load the fitting run
        self.fitting_run = self.load_fitting_run(self.config.name)

        # Get ranges
        if "ranges" in kwargs: self.ranges = kwargs.pop("ranges")

        # Get the initial parameter values
        if "fixed_initial_parameters" in kwargs: self.fixed_initial_parameters = kwargs.pop("fixed_initial_parameters")

        # Set options for the batch launcher
        self.set_launcher_options()

        # Check for restarting generations
        if self.config.restart_from_generation is not None: self.clear_for_restart()

        # Set the model generator
        self.set_generator()

        # Check whether this is not the first generation so that we can use remotes with a scheduling system
        #if self.ngenerations == 0 and self.uses_schedulers:
        #    raise ValueError("The specified remote hosts cannot be used for the first generation: at least one remote uses a scheduling system")

        # Check whether initialize_fit has been called
        if self.is_galaxy_modeling:
            if not fs.is_file(self.fitting_run.wavelength_grids_table_path): raise RuntimeError("Call initialize_fit_galaxy before starting the parameter exploration")
            #if not fs.is_file(self.fitting_run.dust_grids_table_path): raise RuntimeError("Call initialize_fit_galaxy before starting the parameter exploration") # doesn't exist anymore: incorporated in the representations

        # Get grid generation settings
        self.scales = kwargs.pop("scales", None)
        self.most_sampled_parameters = kwargs.pop("most_sampled_parameters", None)
        self.sampling_weights = kwargs.pop("sampling_weigths", None)

        # Deploy SKIRT
        if self.has_host_ids and self.config.deploy: self.deploy()

    # -----------------------------------------------------------------

    def deploy(self):

        """
        Thisf unction ...
        :return:
        """

        # Inform the user
        log.info("Deploying SKIRT where necessary ...")

        # Create the deployer
        deployer = Deployer()

        # Don't deploy PTS
        deployer.config.skirt = True
        deployer.config.pts = False

        # Don't do anything locally
        deployer.config.local = False

        # Set the host ids
        deployer.config.host_ids = self.remote_host_ids

        # Check versions between local and remote
        deployer.config.check = self.config.check_versions

        # Update PTS dependencies
        deployer.config.update_dependencies = self.config.update_dependencies

        # Do clean install
        deployer.config.clean = self.config.deploy_clean

        # Pubkey password
        deployer.config.pubkey_password = self.config.pubkey_password

        # Run the deployer
        deployer.run()

    # -----------------------------------------------------------------

    @lazyproperty
    def remote_host_ids(self):

        """
        This function ...
        :return: 
        """

        # Set remote host IDs
        remote_host_ids = []
        if self.fitting_run.ngenerations == 0:
            for host_id in self.config.remotes:
                if load_host(host_id).scheduler:
                    log.warning("Not using remote host '" + host_id + "' for the initial generation because it uses a scheduling system for launching jobs")
                else: remote_host_ids.append(host_id)
        else: remote_host_ids = self.config.remotes

        # Return the host IDs
        return remote_host_ids

    # -----------------------------------------------------------------

    @lazyproperty
    def nhost_ids(self):

        """
        This function ...
        :return:
        """

        return len(self.remote_host_ids)

    # -----------------------------------------------------------------

    @lazyproperty
    def has_host_ids(self):

        """
        This function ...
        :return:
        """

        return self.nhost_ids > 0

    # -----------------------------------------------------------------

    @property
    def record_timing(self):

        """
        This function ...
        :return: 
        """

        if self.config.record_timing: return True
        elif len(self.remote_host_ids) > 0:
            log.warning("Record timing will be enabled because remote execution is used")
            return True
        else: return False

    # -----------------------------------------------------------------

    @property
    def record_memory(self):

        """
        This function ...
        :return: 
        """

        if self.config.record_memory: return True
        elif len(self.remote_host_ids) > 0:
            log.warning("Record memory will be enabled because remote execution is used")
            return True
        else: return False

    # -----------------------------------------------------------------

    @property
    def extract_timeline(self):

        """
        This
        :return: 
        """

        return self.record_timing or self.config.extract_timeline

    # -----------------------------------------------------------------

    @property
    def extract_memory(self):

        """
        This function ...
        :return: 
        """

        return self.record_memory or self.config.extract_memory

    # -----------------------------------------------------------------

    def set_launcher_options(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting options for the batch simulation launcher ...")

        # Basic options
        self.launcher.config.shared_input = True                               # The input directories (or files) for the different simulations are shared
        self.launcher.config.remotes = self.remote_host_ids                         # The remote host(s) on which to run the simulations
        self.launcher.config.attached = self.config.attached                   # Run remote simulations in attached mode
        self.launcher.config.group_simulations = self.config.group             # Group multiple simulations into a single job (because a very large number of simulations will be scheduled) TODO: IMPLEMENT THIS
        self.launcher.config.group_walltime = self.config.walltime             # The preferred walltime for jobs of a group of simulations
        self.launcher.config.cores_per_process = self.config.cores_per_process # The number of cores per process, for non-schedulers
        self.launcher.config.dry = self.config.dry                             # Dry run (don't actually launch simulations, but allow them to be launched manually)
        self.launcher.config.progress_bar = True  # show progress bars for local execution

        # Record memory and timeline information
        if self.record_timing: self.launcher.config.timing_table_path = self.fitting_run.timing_table_path  # The path to the timing table file
        if self.record_memory: self.launcher.config.memory_table_path = self.fitting_run.memory_table_path  # The path to the memory table file

        # Simulation analysis options

        ## General
        self.launcher.config.relative = True

        ## Logging
        self.launcher.config.logging.verbose = True
        self.launcher.config.logging.memory = True

        # ANALYSIS

        # To create the extr, plot, misc directories relative in the simulation directory
        self.launcher.config.analysis.relative = True

        ## Extraction
        self.launcher.config.analysis.extraction.path = "extr"    # name of the extraction directory
        self.launcher.config.analysis.extraction.progress = self.config.extract_progress  # extract progress information
        self.launcher.config.analysis.extraction.timeline = self.extract_timeline # extract the simulation timeline
        self.launcher.config.analysis.extraction.memory = self.extract_memory    # extract memory information

        ## Plotting
        self.launcher.config.analysis.plotting.path = "plot"  # name of the plot directory
        self.launcher.config.analysis.plotting.seds = self.config.plot_seds    # Plot the output SEDs
        self.launcher.config.analysis.plotting.reference_seds = [self.observed_sed_path]  # the path to the reference SED (for plotting the simulated SED against the reference points)
        self.launcher.config.analysis.plotting.format = "pdf"  # plot format
        self.launcher.config.analysis.plotting.progress = self.config.plot_progress
        self.launcher.config.analysis.plotting.timeline = self.config.plot_timeline
        self.launcher.config.analysis.plotting.memory = self.config.plot_memory

        ## Miscellaneous
        self.launcher.config.analysis.misc.path = "misc"       # name of the misc output directory
        if self.is_images_modeling: # images modeling

            self.launcher.config.analysis.misc.fluxes = False
            self.launcher.config.analysis.misc.images = True
            self.launcher.config.analysis.misc.images_wcs = get_images_header_path(self.config.path)
            self.launcher.config.analysis.misc.images_unit = "Jy"
            self.launcher.config.analysis.misc.images_kernels = None
            self.launcher.config.analysis.misc.rebin_wcs = None

        # Galaxy and SED modeling
        else:

            self.launcher.config.analysis.misc.fluxes = True       # calculate observed fluxes
            self.launcher.config.analysis.misc.images = False

        # observation_filters
        self.launcher.config.analysis.misc.observation_filters = self.observed_filter_names
        # observation_instruments
        self.launcher.config.analysis.misc.observation_instruments = [self.earth_instrument_name]

        # Set spectral convolution flag
        self.launcher.config.analysis.misc.spectral_convolution = self.fitting_run.fitting_configuration.spectral_convolution

        # Set the path to the modeling directory to the simulation object
        self.launcher.config.analysis.modeling_path = self.config.path

        # Set analyser classes
        if self.is_images_modeling: self.launcher.config.analysers = ["pts.modeling.fitting.modelanalyser.ImagesFitModelAnalyser"]
        else: self.launcher.config.analysers = ["pts.modeling.fitting.modelanalyser.SEDFitModelAnalyser"]

    # -----------------------------------------------------------------

    def get_initial_generation_name(self):

        """
        This function ...
        :return: 
        """

        return self.fitting_run.get_initial_generation_name()

    # -----------------------------------------------------------------

    def get_genetic_generation_name(self, index):

        """
        This function ...
        :param index: 
        :return: 
        """

        return self.fitting_run.get_genetic_generation_name(index)

    # -----------------------------------------------------------------

    def clear_for_restart(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Clearing things for restarting from generation '" + self.config.restart_from_generation + "' ...")

        # Get the gneration names
        to_clear = self.get_to_clear_generation_names()

        # Get the generations table
        generations_table = self.fitting_run.generations_table
        best_parameters_table = self.fitting_run.best_parameters_table

        # Get the names of the original genetic generations
        original_genetic_generation_names = generations_table.genetic_generations_with_initial
        original_genetic_generations_with_initial_names_and_indices = generations_table.genetic_generations_with_initial_names_and_indices

        # Keep track of the lowest genetic generation index
        lowest_genetic_generation_index = None
        removed_initial = False

        to_be_removed_paths = []

        # Loop over the generations to be cleared
        for generation_name in to_clear:

            # Prompt to proceed
            if prompt_proceed("Are you absolutely sure all output from generation '" + generation_name + "' can be removed?"):

                # Update the lowest genetic generation index
                if generation_name.startswith("Generation"):
                    index = self.fitting_run.index_for_generation(generation_name)
                    if lowest_genetic_generation_index is None or index < lowest_genetic_generation_index: lowest_genetic_generation_index = index

                if generation_name == "initial": removed_initial = True

                # Remove from generations table
                generations_table.remove_entry(generation_name)

                # Remove from best_parameters table
                best_parameters_table.remove_entry(generation_name)

                # Remove from prob/generations
                prob_generations_path = fs.create_directory_in(self.fitting_run.prob_path, "generations")
                prob_generation_path = fs.join(prob_generations_path, generation_name + ".dat")
                #fs.remove_file(prob_generation_path)
                to_be_removed_paths.append(prob_generation_path)

                # Remove directory from generations/
                generation_directory_path = self.fitting_run.get_generation_path(generation_name)
                #fs.remove_directory(generation_directory_path)
                to_be_removed_paths.append(generation_directory_path)

            # User doesn't want to proceed
            else:

                # Exit with an error
                log.error("Cannot proceed without confirmation")
                exit()

        # IF GENETIC GENERATIONS ARE CLEARED, REPLACE THE MAIN ENGINE, MAIN PRNG AND MAIN OPTIMIZER.CFG
        if removed_initial:

            # Remove
            fs.remove_file(self.fitting_run.main_engine_path)
            fs.remove_file(self.fitting_run.main_prng_path)
            fs.remove_file(self.fitting_run.optimizer_config_path)

        # Some genetic generations are cleared, starting with some lowest genetic generation index
        elif lowest_genetic_generation_index is not None:

            # Search for the last remaining generation
            last_remaining_generation = None

            # Determine name of generation just before this index
            for other_name, other_index in original_genetic_generations_with_initial_names_and_indices:
                if other_index == lowest_genetic_generation_index - 1:
                    last_remaining_generation = other_name
                    break

            if last_remaining_generation: raise RuntimeError("Something went wrong")

            # Determine the path of this generation
            generation = self.fitting_run.get_generation(last_remaining_generation)

            # Determine the paths of the engine, prng and optimizer config
            engine_path = generation.engine_path
            prng_path = generation.prng_path
            optimizer_config_path = generation.optimizer_config_path

            # Replace the main engine, prng and optimizer config
            fs.replace_file(self.fitting_run.main_engine_path, engine_path)
            fs.replace_file(self.fitting_run.main_prng_path, prng_path)
            fs.replace_file(self.fitting_run.optimizer_config_path, optimizer_config_path)

        # Remove everything belonging the cleared generations
        fs.remove_directories_and_files(to_be_removed_paths)

        # Save the generations table
        generations_table.save()

        # Save the best parameters table
        best_parameters_table.save()

    # -----------------------------------------------------------------

    def get_to_clear_generation_names(self):

        """
        This function ...
        :return:
        """

        generation_name = self.config.restart_from_generation

        # Check whether the generation exists
        if generation_name not in self.fitting_run.generation_names: raise ValueError("Generation '" + generation_name + "' does not exist")

        # Generation names to clear
        to_clear = []

        # Grid-type generation
        if "grid" in generation_name:

            # Add to be cleared
            to_clear.append(generation_name)

            # Get the timestamp
            generation_time = time.get_time_from_unique_name(generation_name)

            # Loop over other 'grid' generations
            for other_generation_name in self.fitting_run.grid_generations:

                if other_generation_name == generation_name: continue

                # Get time
                other_generation_time = time.get_time_from_unique_name(other_generation_name)

                # If the time is later, add to generation names to be cleared
                if other_generation_time > generation_time: to_clear.append(generation_name)

        # Initial genetic generation
        elif generation_name == self.get_initial_generation_name():

            # All genetic generations have to be cleared
            to_clear = self.fitting_run.genetic_generations

        # Other genetic generation
        elif generation_name.startswith("Generation"):

            # Add to be cleared
            to_clear.append(generation_name)

            # Get the index of the generation
            index = self.fitting_run.index_for_generation(generation_name)

            # Loop over the other genetic generations
            for other_generation_name in self.fitting_run.genetic_generations:

                if other_generation_name == generation_name: continue

                # Get index of other
                other_index = self.fitting_run.index_for_generation(other_generation_name)

                # If the index is higher, add to be cleared
                if other_index > index: to_clear.append(other_generation_name)

        # Could not understand
        else: raise ValueError("Could not understand the nature of generation '" + generation_name + "'")

        # Retunr the list of generation names to clear
        return to_clear

    # -----------------------------------------------------------------

    def set_generator(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the model generator ...")

        # Generate new models based on a simple grid (linear or logarithmic) of parameter values
        if self.config.generation_method == "grid": self.set_grid_generator()

        # Generate new models using genetic algorithms
        elif self.config.generation_method == "genetic": self.set_genetic_generator()

        # Invalid generation method
        else: raise ValueError("Invalid generation method: " + str(self.config.generation_method))

        # Set general options for the model generator
        self.set_generator_options()

        # Debugging
        log.debug("The name of the new generation of parameter exploration is '" + self.generation_name + "'")

    # -----------------------------------------------------------------

    def set_grid_generator(self):

        """
        This function ...
        :param self: 
        :return: 
        """

        # Inform the user
        log.info("Setting grid model generator ...")

        # Set a name for the generation
        self.generation_name = time.unique_name("grid")

        # Create the model generator
        self.generator = GridModelGenerator()

    # -----------------------------------------------------------------

    def set_genetic_generator(self):

        """
        This function ...
        :param self: 
        :return: 
        """

        # Inform the user
        log.info("Setting genetic model generator ...")

        # Not the initial generation
        if self.get_initial_generation_name() in self.fitting_run.generation_names:

            # Set index and name
            self.generation_index = self.fitting_run.last_genetic_generation_index + 1
            self.generation_name = self.get_genetic_generation_name(self.generation_index)

        # Initial generation
        else: self.generation_name = self.get_initial_generation_name()

        # Create the generator
        self.generator = GeneticModelGenerator()

        # Set recurrence settings
        self.generator.config.check_recurrence = self.config.check_recurrence
        self.generator.config.recurrence_rtol = self.config.recurrence_rtol
        self.generator.config.recurrence_atol = self.config.recurrence_atol

    # -----------------------------------------------------------------

    def set_generator_options(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Setting general model generator options ...")

        # Set the modeling path for the model generator
        self.generator.config.path = self.config.path

        # Set generator options
        self.generator.config.ngenerations = self.config.ngenerations # only useful for genetic model generator (and then again, cannot be more then 1 yet)
        self.generator.config.nmodels = self.config.nsimulations

    # -----------------------------------------------------------------

    def load_ski(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the ski file template ...")

        # Load the labeled ski template file
        self.ski = self.fitting_run.ski_template

    # -----------------------------------------------------------------

    def set_ranges(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parameter ranges ...")

        # Create definition
        definition = self.create_parameter_ranges_definition()

        # Get the ranges
        if len(definition) > 0: config = create_configuration_interactive(definition, "ranges", "parameter ranges", add_cwd=False, add_logging=False)

        # No parameters for which the ranges still have to be specified interactively
        else: config = None

        # Set the ranges
        for label in self.fitting_run.free_parameter_labels:

            # If range is already defined
            if label in self.ranges: continue

            # Set the range
            self.ranges[label] = config[label + "_range"]

    # -----------------------------------------------------------------

    def create_parameter_ranges_definition(self):

        """
        This function ...
        :return: 
        """

        # Create a definition
        definition = ConfigurationDefinition(write_config=False)

        # Create info
        extra_info = self.create_parameter_ranges_info()

        # Loop over the free parameters, add a setting slot for each parameter range
        for label in self.fitting_run.free_parameter_labels:

            # Skip if range is already defined for this label
            if label in self.ranges: continue

            # Get the default range
            default_range = self.fitting_run.fitting_configuration[label + "_range"]
            ptype, string = stringify_not_list(default_range)

            # Determine description
            description = "the range of " + label
            description += " (" + extra_info[label] + ")"

            # Add the optional range setting for this free parameter
            definition.add_optional(label + "_range", ptype, description, default_range)

        # Return the definition
        return definition

    # -----------------------------------------------------------------

    def create_parameter_ranges_info(self):

        """
        This function ...
        :return: 
        """

        extra_info = dict()

        # Check if there are any models that have been evaluated
        if self.fitting_run.has_evaluated_models:

            # Inform the user
            # log.info("Determining the parameter ranges based on the current best values and the specified relative ranges ...")

            # Get the best model
            model = self.fitting_run.best_model

            # Debugging
            # log.debug("Using the parameter values of simulation '" + model.simulation_name + "' of generation '" + model.generation_name + "' ...")

            # Get the parameter values of the best model
            parameter_values = model.parameter_values

            # Set info
            for label in parameter_values: extra_info[label] = "parameter value of current best model = " + stringify(parameter_values[label])[1]

        else:

            # Inform the user
            #log.info("Determining the parameter ranges based on the first guess values and the specified relative ranges ...")

            # Get the initial guess values
            parameter_values = self.fitting_run.first_guess_parameter_values

            # Set info
            for label in parameter_values: extra_info[label] = "initial parameter value = " + stringify(parameter_values[label])[1]

        # Return the info
        return extra_info

    # -----------------------------------------------------------------

    def generate_models(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the model parameters ...")

        # Run the model generator
        self.generator.run(fitting_run=self.fitting_run, parameter_ranges=self.ranges,
                           fixed_initial_parameters=self.fixed_initial_parameters, generation=self.generation,
                           scales=self.scales, most_sampled_parameters=self.most_sampled_parameters,
                           sampling_weights=self.sampling_weights, npoints=self.config.npoints)

        # Set the actual number of simulations for this generation
        self.generation_info.nsimulations = self.nmodels

    # -----------------------------------------------------------------

    def set_info(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the generation info ...")

        # Get the previous wavelength grid level
        wavelength_grid_level = self.fitting_run.current_wavelength_grid_level
        #dust_grid_level = self.fitting_run.current_dust_grid_level

        # Determine the wavelength grid level
        #if self.config.refine_wavelengths:
        if self.config.refine_spectral:
            if wavelength_grid_level == self.fitting_run.highest_wavelength_grid_level: log.warning("Cannot refine wavelength grid: highest level reached (" + str(wavelength_grid_level) + ")")
            else: wavelength_grid_level += 1

        # Determine the dust grid level
        #if self.config.refine_dust:
        #    if dust_grid_level == self.fitting_run.highest_dust_grid_level: log.warning("Cannot refine dust grid: highest level reached (" + str(dust_grid_level) + ")")
        #    else: dust_grid_level += 1
        # DETERMINE THE REPRESENTATION
        if self.config.refine_spatial: self.representation = self.fitting_run.next_model_representation # GET NEXT REPRESENTATION (THEY ARE NAMED IN ORDER OF SPATIAL RESOLUTION)
        # Get the previous (current because this generation is just
        else: self.representation = self.fitting_run.current_model_representation # GET LAST REPRESENTATION #self.fitting_run.initial_representation

        # Determine the number of photon packages
        if self.config.increase_npackages: npackages = int(self.fitting_run.current_npackages * self.config.npackages_factor)
        else: npackages = self.fitting_run.current_npackages

        # Determine whether selfabsorption should be enabled
        if self.config.selfabsorption is not None: selfabsorption = self.config.selfabsorption
        else: selfabsorption = self.fitting_run.current_selfabsorption

        # Determine whether transient heating should be enabled
        if self.config.transient_heating is not None: transient_heating = self.config.transient_heating
        else: transient_heating = self.fitting_run.current_transient_heating

        # Set the generation info
        self.generation_info.name = self.generation_name
        self.generation_info.index = self.generation_index
        self.generation_info.method = self.config.generation_method
        self.generation_info.wavelength_grid_level = wavelength_grid_level
        self.generation_info.model_representation_name = self.representation.name
        #self.generation.nsimulations = self.config.nsimulations # DON'T DO IT HERE YET, GET THE NUMBER OF ACTUAL MODELS SPITTED OUT BY THE MODELGENERATOR (RECURRENCE)
        self.generation_info.npackages = npackages
        self.generation_info.selfabsorption = selfabsorption
        self.generation_info.transient_heating = transient_heating

    # -----------------------------------------------------------------

    @lazyproperty
    def use_file_tree_dust_grid(self):

        """
        This function ...
        :return:
        """

        smile = SKIRTSmileSchema()
        return smile.supports_file_tree_grids and self.representation.has_dust_grid_tree

    # -----------------------------------------------------------------

    def set_input(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the input paths ...")

        # Initialize the SimulationInput object
        self.simulation_input = SimulationInput()

        # Set the paths to the input maps
        for name in self.fitting_run.input_map_paths:
            path = self.fitting_run.input_map_paths[name]
            self.simulation_input.add_file(path, name)

        # NEW: DETERMINE AND SET THE PATH TO THE APPROPRIATE DUST GRID TREE FILE
        if self.use_file_tree_dust_grid: self.simulation_input.add_file(self.representation.dust_grid_tree_path)

        # Determine and set the path to the appropriate wavelength grid file
        wavelength_grid_path = self.fitting_run.wavelength_grid_path_for_level(self.generation_info.wavelength_grid_level)
        #self.input_paths.append(wavelength_grid_path)
        self.simulation_input.add_file(wavelength_grid_path)

        # Get the number of wavelengths
        self.nwavelengths = len(WavelengthGrid.from_skirt_input(wavelength_grid_path))

        # Debugging
        log.debug("The wavelength grid for the simulations contains " + str(self.nwavelengths) + " wavelength points")

    # -----------------------------------------------------------------

    def create_generation(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Creating the generation directory")

        # Set the path to the generation directory
        self.generation_info.path = fs.create_directory_in(self.fitting_run.generations_path, self.generation_name)

        # Initialize tables
        self.initialize_generation_tables()

        # Create the generation object
        self.generation = Generation(self.generation_info)

    # -----------------------------------------------------------------

    def initialize_generation_tables(self):

        """
        This function ...
        :return: 
        """

        # Initialize the individuals table
        self.individuals_table = IndividualsTable()

        # Initialize the parameters table
        self.parameters_table = ParametersTable(parameters=self.fitting_run.free_parameter_labels, units=self.fitting_run.parameter_units)

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
        if self.fitting_run.has_wavelength_grids: self.set_wavelength_grid()

        # Set model representation
        self.set_representation()

    # -----------------------------------------------------------------

    def set_npackages(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the number of photon packages to " + str(self.generation_info.npackages) + " ...")

        # Set the number of photon packages per wavelength
        self.ski.setpackages(self.generation_info.npackages)

    # -----------------------------------------------------------------

    def set_selfabsorption(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Enabling dust self-absorption ..." if self.generation_info.selfabsorption else "Disabling dust self-absorption ...")

        # Set dust self-absorption
        if self.generation_info.selfabsorption: self.ski.enable_selfabsorption()
        else: self.ski.disable_selfabsorption()

    # -----------------------------------------------------------------

    def set_transient_heating(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Enabling transient heating ..." if self.generation_info.transient_heating else "Disabling transient heating ...")

        # Set transient heating
        if self.generation_info.transient_heating: self.ski.set_transient_dust_emissivity()
        else: self.ski.set_grey_body_dust_emissivity()

    # -----------------------------------------------------------------

    def set_wavelength_grid(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the name of the wavelengths file to " + fs.name(self.fitting_run.wavelength_grid_path_for_level(self.generation_info.wavelength_grid_level)) + " (level " + str(self.generation.wavelength_grid_level) + ") ...")

        # Set the name of the wavelength grid file
        self.ski.set_file_wavelength_grid(fs.name(self.fitting_run.wavelength_grid_path_for_level(self.generation_info.wavelength_grid_level)))

    # -----------------------------------------------------------------

    def set_representation(self):

        """
        This function ...
        :return:
        """

        # Debugging
        log.debug("Setting the model representation ...")

        # GET DUST GRID
        if self.use_file_tree_dust_grid:

            # Get the file tree dust grid object
            dust_grid = self.representation.create_file_tree_dust_grid(write=False)

            # Make sure it is only the file name, not a complete path
            dust_grid.filename = fs.name(dust_grid.filename)

        # REGULAR DUST GRID OBJECT
        else: dust_grid = self.representation.dust_grid

        # Set the dust grid
        self.ski.set_dust_grid(dust_grid)

    # -----------------------------------------------------------------

    def set_parallelization_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parallelization scheme for local execution ...")

        # Get properties of the local machine
        nnodes = par.nnodes()
        nsockets = par.sockets_per_node()
        ncores = par.cores_per_socket()
        memory = par.virtual_memory().to("Gbyte")
        threads_per_core = par.nthreads_per_core()
        hyperthreading = threads_per_core > 1
        mpi = introspection.has_mpi()

        # Create the parallelization tool
        tool = ParallelizationTool()

        # Set configuration options
        tool.config.ski = self.ski
        tool.config.input = self.simulation_input

        # Set host properties
        tool.config.nnodes = nnodes
        tool.config.nsockets = nsockets
        tool.config.ncores = ncores
        tool.config.memory = memory

        # MPI available and used
        tool.config.mpi = mpi
        tool.config.hyperthreading = hyperthreading
        tool.config.threads_per_core = threads_per_core

        # Number of dust cells
        tool.config.ncells = None  # number of dust cells (relevant if ski file uses a tree dust grid)

        # Don't show
        tool.config.show = False

        # Run the parallelization tool
        tool.run()

        # Get the parallelization scheme
        parallelization = tool.parallelization

        # Debugging
        log.debug("The parallelization scheme for local execution is " + str(parallelization))

        # Set the parallelization scheme
        self.launcher.set_parallelization_for_local(parallelization)

    # -----------------------------------------------------------------

    def set_parallelization_remote(self):

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
            tool.config.ski = self.ski
            tool.config.input = self.simulation_input

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
        estimator = RuntimeEstimator.from_file(self.fitting_run.timing_table_path)

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
            runtime = estimator.runtime_for(self.ski, parallelization, host.id, host.cluster_name, self.config.data_parallel, nwavelengths=self.nwavelengths, plot_path=plot_path)

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
        for host_id in self.launcher.host_ids: self.launcher.set_script_path(host_id, self.generation_info.path)

        # Enable screen output logging for remotes without a scheduling system for jobs
        for host_id in self.launcher.no_scheduler_host_ids: self.launcher.enable_screen_output(host_id)

        # Loop over the simulations, add them to the queue
        for simulation_name in self.simulation_names:

            # Get the parameter values
            parameter_values = self.parameters_table.parameter_values_for_simulation(simulation_name)

            # Prepare simulation directories, ski file, and return the simulation definition
            definition = prepare_simulation(simulation_name, self.ski, parameter_values, self.object_name,
                                            self.simulation_input, self.generation_info.path, scientific=True, fancy=True,
                                            ndigits=self.fitting_run.ndigits_dict)

            # Debugging
            log.debug("Adding a simulation to the queue with:")
            log.debug("")
            log.debug(" - name: " + simulation_name)
            log.debug(" - input: " + str(self.simulation_input))
            log.debug(" - ski path: " + definition.ski_path)
            log.debug(" - output path: " + definition.output_path)
            log.debug("")

            # Put the parameters in the queue and get the simulation object
            self.launcher.add_to_queue(definition, simulation_name)

            # Set scheduling options (for the different remote hosts with a scheduling system)
            for host_id in self.scheduling_options: self.launcher.set_scheduling_options(host_id, simulation_name, self.scheduling_options[host_id])

        # Run the launcher, launches the simulations and retrieves and analyses finished simulations
        self.launcher.run()

        # Check the launched simulations
        self.check_simulations()

    # -----------------------------------------------------------------

    def set_finishing_time(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Setting the generation finishing time (there were no simulations for this generation) ...")

        # Set the time and save the table
        self.fitting_run.generations_table.set_finishing_time(self.generation_name, time.timestamp())
        self.fitting_run.generations_table.save()

    # -----------------------------------------------------------------

    def check_simulations(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Checking the simulations ...")

        simulations = self.launcher.launched_simulations

        # Check the number of simulations that were effectively launched
        if self.nmodels == len(simulations):
            log.success("All simulations were scheduled succesfully")
            return

        # No simulations were launched
        if len(simulations) == 0:

            # Show error message
            log.error("No simulations could be launched: removing generation")
            log.error("Try again later")
            log.error("Cleaning up generation and quitting ...")

            # Remove this generation from the generations table
            self.fitting_run.generations_table.remove_entry(self.generation_name)
            self.fitting_run.generations_table.save()

            # Remove the generation directory
            fs.remove_directory(self.generation_info.path)

            # Quit
            exit()

        # Less simulations were launched
        elif len(simulations) < self.nmodels:

            # Get the names of simulations that were launched
            launched_simulation_names = [simulation.name for simulation in simulations]
            if None in launched_simulation_names: raise RuntimeError("Some or all simulation don't have a name defined")

            # Show error message
            log.error("Launching a simulation for the following models failed:")
            log.error("")

            # Loop over all simulations in the parameters table
            failed_indices = []
            for index, simulation_name in enumerate(self.parameters_table.simulation_names):

                # This simulation is OK
                if simulation_name in launched_simulation_names: continue

                log.error("Model #" + str(index + 1))
                log.error("")
                parameter_values = self.parameters_table.parameter_values_for_simulation(simulation_name)
                for label in parameter_values: log.error(" - " + label + ": " + stringify_not_list(parameter_values[label])[1])
                log.error("")

                failed_indices.append(index)

            # Show error message
            log.error("Removing corresponding entries from the model parameters table ...")

            # Remove rows and save
            self.parameters_table.remove_rows(failed_indices)
            self.parameters_table.save()

        # Unexpected
        else: raise RuntimeError("Unexpected error where nsmulations > nmodels")

    # -----------------------------------------------------------------

    @property
    def model_names(self):

        """
        This function ...
        :return: 
        """

        return self.generator.individual_names

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
    def model_parameters(self):

        """
        This function ...
        :return: 
        """

        return self.generator.parameters

    # -----------------------------------------------------------------

    @property
    def uses_schedulers(self):

        """
        This function ...
        :return:
        """

        return self.launcher.uses_schedulers

    # -----------------------------------------------------------------

    @property
    def simulation_names(self):

        """
        This function ...
        :return: 
        """

        return self.individuals_table.simulation_names

    # -----------------------------------------------------------------

    @property
    def needs_simulations(self):

        """
        This function ...
        :return: 
        """

        return len(self.simulation_names) > 0

    # -----------------------------------------------------------------

    @property
    def generation_path(self):

        """
        This function ...
        :return: 
        """

        return self.generation_info.path

    # -----------------------------------------------------------------

    def fill_tables(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Filling the tables for the current generation ...")

        # Loop over the model names
        counter = 0
        for name in self.model_names:

            # Generate the simulation name
            simulation_name = generate_simulation_name()

            # Debugging
            log.debug("Adding an entry to the individuals table with:")
            log.debug("")
            log.debug(" - Simulation name: " + simulation_name)
            log.debug(" - Individual_name: " + name)
            log.debug("")

            # Add entry
            self.individuals_table.add_entry(simulation_name, name)

            # Get the parameter values
            parameter_values = get_parameter_values_for_named_individual(self.model_parameters, name, self.fitting_run)

            # Debugging
            log.debug("Adding entry to the parameters table with:")
            log.debug("")
            log.debug(" - Simulation name: " + simulation_name)
            for label in parameter_values: log.debug(" - " + label + ": " + tostr(parameter_values[label], scientific=True, fancy=True, ndigits=self.fitting_run.ndigits_dict[label]))
            log.debug("")

            # Add an entry to the parameters table
            self.parameters_table.add_entry(simulation_name, parameter_values)

            # Increment counter
            counter += 1

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # 1. Write the generation info
        self.write_generation_info()

        # 2. Write the generations table
        self.write_generations_table()

        # 2. Write the individuals table
        self.write_individuals()

        # 3. Write the parameters table
        self.write_parameters()

        # 4. Write the (empty) chi squared table
        self.write_chi_squared()

    # -----------------------------------------------------------------

    def write_generation_info(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the generation info ...")

        # Save as a data file
        self.generation_info.saveto(self.generation.info_path)

    # -----------------------------------------------------------------

    def write_generations_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the generations table ...")

        # Add an entry to the generations table
        self.fitting_run.generations_table.add_entry(self.generation_info, self.ranges, self.scales)

        # Save the table
        self.fitting_run.generations_table.save()

    # -----------------------------------------------------------------

    def write_individuals(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Writing the individuals table ...")

        # Save the individuals table
        self.individuals_table.saveto(self.generation.individuals_table_path)

    # -----------------------------------------------------------------

    def write_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the model parameters table ...")

        # Save the parameters table
        self.parameters_table.saveto(self.generation.parameters_table_path)

    # -----------------------------------------------------------------

    def write_chi_squared(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the chi squared table ...")

        # Save the chi squared table
        self.chi_squared_table.saveto(self.generation.chi_squared_table_path)

# -----------------------------------------------------------------
