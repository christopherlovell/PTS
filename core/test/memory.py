#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.test.memory Contains the MemoryTester class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ...core.tools import filesystem as fs
from ..basics.configurable import Configurable
from ..simulation.execute import SkirtExec
from ..simulation.skifile import SkiFile
from ..advanced.memoryestimator import MemoryEstimator
from ..launch.batchlauncher import BatchLauncher
from ..simulation.definition import SingleSimulationDefinition, create_definitions
from ..config.launch_batch import definition
from ..basics.configuration import InteractiveConfigurationSetter
from ..launch.options import LoggingOptions
from ..simulation.parallelization import Parallelization

# -----------------------------------------------------------------

class MemoryTester(Configurable):
    
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
        super(MemoryTester, self).__init__(config)

        # Local SKIRT execution environment
        self.skirt = SkirtExec()

        # Remote SKIRT batch execution environment
        self.launcher = BatchLauncher()

        # The memory estimator
        self.estimator = MemoryEstimator()

        # The path to the output directory
        self.out_path = None

        # The simulation definition file (if single ski path is specified)
        self.definition = None

        # The logging options
        self.logging = None

        # The parallelization scheme
        self.parallelization = None

        # The simulations that have been run
        self.simulations = []

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function
        self.setup(**kwargs)

        # Launch the simulations
        self.launch()

        # Load the data
        self.load_data()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(MemoryTester, self).setup(**kwargs)

        # Set the output path
        self.out_path = fs.join(self.config.path, "out")

        # Create the output directory
        if fs.is_directory(self.out_path): raise RuntimeError("The output directory already exists")
        else: fs.create_directory(self.out_path)

        # If a remote is specified, setup the batch launcher
        if self.config.remote: self.setup_launcher()

    # -----------------------------------------------------------------

    def setup_launcher(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Preparing the batch launcher ...")

        #definition = ConfigurationDefinition(write_config=False)
        setter = InteractiveConfigurationSetter(self.class_name, add_logging=False)

        # Create new config
        self.launcher.config = setter.run(definition, prompt_optional=False)

        # Set working directory
        self.launcher.config.path = self.config.path

        # Set output directory path
        self.launcher.config.output = self.out_path

        # Set options for the batch launcher: basic options
        self.launcher.config.shared_input = True
        #self.launcher.config.group_simulations = True  # group multiple simulations into a single job (because a very large number of simulations will be scheduled)
        self.launcher.config.remotes = [self.config.remote]  # the remote hosts on which to run the simulations

        #self.launcher.config.timing_table_path = self.timing_table_path  # The path to the timing table file
        #self.launcher.config.memory_table_path = self.memory_table_path  # The path to the memory table file
        #self.launcher.config.retrieve_types = ["log"]  # only log files should be retrieved from the simulation output
        #self.launcher.config.keep = self.config.keep

        # Logging options
        self.launcher.config.logging.verbose = True
        self.launcher.config.logging.memory = True
        self.launcher.config.logging.allocation = False

        # Look for ski files recursively if necessary
        self.launcher.config.recursive = self.config.recursive

        # Run in attached mode
        self.launcher.config.attached = True

        # Run in emulation mode
        self.launcher.config.emulate = True

        # Number of cores per process
        self.launcher.config.cores_per_process = 4

    # -----------------------------------------------------------------

    def launch(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching simulation(s) ...")

        # If no ski file is specified, the batch launcher will take all ski files in the working directory
        # If a ski file is specified
        if self.config.ski is not None:

            # Determine the full ski path
            ski_path = fs.join(self.config.path, self.config.ski)

            # Open the ski file
            ski = SkiFile(ski_path)

            # Check whether input is required
            if ski.needs_input: input_paths = ski.input_paths(self.config.input, self.config.path)
            else: input_paths = None

            # Create simulation definition
            self.definition = SingleSimulationDefinition(ski_path, self.out_path, input_paths)

        # Launch locally or remotely
        if self.config.remote: self.launch_remote()
        else: self.launch_local()

    # -----------------------------------------------------------------

    def launch_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching locally ...")

        # Create the logging options
        #self.logging = LoggingOptions(verbose=True, memory=True, allocation=True, allocation_limit=1e-5)
        self.logging = LoggingOptions(verbose=True, memory=True, allocation=False, allocation_limit=1e-5)

        # Set the parallelization scheme
        self.parallelization = Parallelization.for_local(nprocesses=self.config.nprocesses)

        # If a single ski file was specified
        if self.definition is not None:

            # Run the simulation
            simulation = self.skirt.run(self.definition, self.logging, self.parallelization, emulate=True)

            # Set the list of simulations
            self.simulations = [simulation]

        else:

            # Create simulation definitions from the working directory and add them to the queue
            for definition in create_definitions(self.config.path, self.config.output, self.config.input, recursive=self.config.recursive):

                # Run the simulation
                simulation = self.skirt.run(definition, self.logging, self.parallelization, emulate=True)

                # Add to the list of simulation
                self.simulations.append(simulation)

    # -----------------------------------------------------------------

    def launch_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching remotely ...")

        # Set the parallelization scheme
        #ncores = math.floor(self.launcher.single_remote.free_sockets) * self.launcher.single_remote.cores_per_socket
        threads_per_core = 1
        ncores = self.config.nprocesses
        self.parallelization = Parallelization(ncores, threads_per_core, self.config.nprocesses)

        # If single ski file was specified
        if self.definition is not None: self.launcher.add_to_queue(definition, definition.prefix, parallelization=self.parallelization)

        # Else, set the parallelization
        else: self.launcher.set_parallelization_for_host(self.launcher.single_host.id, self.parallelization)

        # Run the batch launcher
        self.simulations = self.launcher.run()

    # -----------------------------------------------------------------

    def load_data(self):

        """
        This function ...
        :return:
        """

        # Loop over the simulations
        for simulation in self.simulations:

            # Get the log file
            log_file = simulation.log_file

            # Get the peak memory usage
            memory = log_file.peak_memory

            # Load the ski file
            ski = SkiFile(simulation.ski_path)

            # Configure the memory estimator tool
            self.estimator.config.ski = ski
            self.estimator.config.input = self.config.path
            self.estimator.config.ncells = None
            self.estimator.config.probe = False

            # Run the estimator
            self.estimator.run()

            # Get the parallel and serial part of the memory
            parallel = self.estimator.parallel_memory
            serial = self.estimator.serial_memory

            # Calculate the total memory requirement
            total = parallel + serial


            print(memory, parallel, serial, parallel + serial)

            # Calculate the procentual difference
            #diff = (consumed_memory - estimated_memory) / consumed_memory * 100.0

# -----------------------------------------------------------------
