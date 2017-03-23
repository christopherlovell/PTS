#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.simulation.arguments Contains the SkirtArguments class, used for representing the set of
#  command-line arguments that can be passed to SKIRT.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import fnmatch

# Import the relevant PTS classes and modules
from .simulation import SkirtSimulation
from ..basics.map import Map
from ..tools import filesystem as fs
from .definition import SingleSimulationDefinition, MultiSimulationDefinition
from ..tools.logging import log
from .input import SimulationInput

# -----------------------------------------------------------------

class SkirtArguments(object):

    """
    This class ...
    """

    def __init__(self, definition=None, logging_options=None, parallelization=None, emulate=False):

        """
        The constructor ...
        :param definition:
        :param logging_options:
        :param parallelization:
        :return:
        """

        # TODO: discriminate between different types of 'SimulationDefinition' (multiple or single)

        # Options for the ski file pattern
        self.ski_pattern = definition.ski_path if definition is not None else None
        self.recursive = None
        self.relative = None

        # The input and output paths
        self.input_path = definition.input_path if definition is not None else None
        self.output_path = definition.output_path if definition is not None else None

        # Other options
        self.emulate = emulate    # Run in emulation mode
        self.single = False       # True if only a single simulation is expected

        # Options for logging
        self.logging = Map()
        self.logging.brief = logging_options.brief if logging_options is not None else False     # Brief console logging
        self.logging.verbose = logging_options.verbose if logging_options is not None else False  # Verbose logging
        self.logging.memory = logging_options.memory if logging_options is not None else False  # State the amount of used memory with each log message
        self.logging.allocation = logging_options.allocation if logging_options is not None else False # Write log messages with the amount of (de)allocated memory
        self.logging.allocation_limit = logging_options.allocation_limit if logging_options is not None else 1e-5  # The lower limit for the amount of (de)allocated memory to be logged

        # Options for parallelization
        self.parallel = Map()
        self.parallel.simulations = None  # The number of parallel simulations
        self.parallel.threads = parallelization.threads if parallelization is not None else None # The number of parallel threads per simulation
        self.parallel.processes = parallelization.processes if parallelization is not None else None # The number of parallel processes per simulation
        self.parallel.dataparallel = parallelization.data_parallel if parallelization is not None else False  # Run in data parallelization mode

    # -----------------------------------------------------------------

    @property
    def prefix(self):

        """
        This function ...
        :return:
        """

        if not fs.is_file(self.ski_pattern): raise RuntimeError("Cannot determine the prefix for the ski pattern '" + self.ski_pattern + "'. Does it define multiple files?")
        return fs.strip_extension(fs.name(self.ski_pattern))

    # -----------------------------------------------------------------

    @classmethod
    def from_config(cls, config):

        """
        This function ...
        :param config:
        :return:
        """

        # Create a new instance
        arguments = cls()

        # Loop over the entries in the configuration and create an attribute with the same name
        for entry in config: setattr(arguments, entry, config[entry])

        # Return the arguments instance
        return arguments

    # -----------------------------------------------------------------

    @classmethod
    def from_definition(cls, definition, logging_options, parallelization, emulate=False):

        """
        This function ...
        :param definition:
        :param logging_options:
        :param parallelization:
        :param emulate:
        :return:
        """

        # If the first argument defines a single simulation
        if isinstance(definition, SingleSimulationDefinition):

            # Create the SkirtArguments object
            arguments = SkirtArguments(logging_options=logging_options, parallelization=parallelization)

            # Set the base simulation options such as ski path, input path and output path (remote)
            arguments.ski_pattern = definition.ski_path
            arguments.input_path = definition.input_path
            arguments.output_path = definition.output_path

            arguments.single = True

            arguments.emulate = emulate

            return arguments

        # If the first argument defines multiple simulations
        elif isinstance(definition, MultiSimulationDefinition): raise NotImplementedError("Not implemented yet")

        # Invalid first argument
        else: raise ValueError("Invalid argument for 'definition'")

    # -----------------------------------------------------------------

    @classmethod
    def single(cls, ski_path, input_path, output_path, processes=None, threads=None, verbose=False, memory=False):

        """
        This function ...
        :param ski_path:
        :param input_path:
        :param output_path:
        :param processes:
        :param threads:
        :param verbose:
        :param memory:
        :return:
        """

        # Create a SkirtArguments instance
        arguments = cls()

        # Set the options
        arguments.ski_pattern = ski_path
        arguments.single = True
        arguments.recursive = False
        arguments.relative = False
        arguments.parallel.processes = processes
        arguments.parallel.threads = threads
        arguments.input_path = input_path
        arguments.output_path = output_path
        arguments.logging.verbose = verbose
        arguments.logging.memory = memory

        # Return the new instance
        return arguments

    # -----------------------------------------------------------------

    def simulations(self, simulation_names=None, simulation_name=None):

        """
        This function ...
        :param simulation_names:
        :param simulation_name:
        :return:
        """

        # Initialize a list to contain the simulation objects
        simulations = []

        # Loop over the seperate ski files defined in the ski pattern
        pattern = [self.ski_pattern] if isinstance(self.ski_pattern, basestring) else self.ski_pattern
        for skifile in pattern:

            # Determine the directory path and the actual file descriptor
            root, name = fs.directory_and_name(skifile)

            # Construct the 'dirlist' variable; this is a list of 3-tuples (dirpath, dirnames, filenames)
            if self.recursive: dirlist = os.walk(root)
            else: dirlist = [(root, [], filter(lambda fn: os.path.isfile(os.path.join(root,fn)), os.listdir(root)))]

            # Search for ski files matching the pattern and construct SkirtSimulation objects
            for dirpath, dirnames, filenames in dirlist:
                for filename in fnmatch.filter(filenames, name):

                    # Determine input and output path
                    inp = os.path.join(dirpath, self.input_path) if (self.relative and self.input_path is not None) else self.input_path
                    out = os.path.join(dirpath, self.output_path) if (self.relative and self.output_path is not None) else self.output_path

                    # Create the simulation and add it to the list
                    filepath = fs.join(dirpath, filename)
                    sim_name = simulation_names[filepath] if simulation_names is not None and filepath in simulation_names else None
                    simulations.append(SkirtSimulation(filename, inpath=inp, outpath=out, ski_path=filepath, name=sim_name))

        # Check whether the ski pattern is ought to represent only one particular simulation
        if self.single:

            # If multiple matching ski files are found, raise an error
            if len(simulations) > 1: raise ValueError("The specified ski pattern defines multiple simulations")
            else: simulation = simulations[0]

            # Set name and return simulation
            if simulation_name is not None: simulation.name = simulation_name
            return simulation

        # Else, just return the list of simulations (even when containing only one item)
        else:
            if simulation_name is not None: raise ValueError("'simulation_name' cannot be specified if single=False")
            return simulations

    # -----------------------------------------------------------------

    def to_command(self, skirt_path, mpi_command, scheduler, bind_to_cores=False, threads_per_core=1, to_string=False, remote=None):

        """
        This function ...
        :param skirt_path:
        :param mpi_command:
        :param scheduler:
        :param bind_to_cores:
        :param threads_per_core:
        :param to_string:
        :param remote:
        :return:
        """

        # If the input consists of a list of paths, check whether they represent files in the same directory
        if isinstance(self.input_path, list): input_dir_path = SimulationInput(*self.input_path).to_single_directory()
        elif isinstance(self.input_path, basestring): input_dir_path = SimulationInput(self.input_path).to_single_directory()
        elif isinstance(self.input_path, SimulationInput): input_dir_path = self.input_path.to_single_directory()
        elif self.input_path is None: input_dir_path = None
        else: raise ValueError("Type of simulation input not recognized")

        # Create the argument list
        arguments = skirt_command(skirt_path, mpi_command, bind_to_cores, self.parallel.processes, self.parallel.threads, threads_per_core, scheduler, remote)

        # Parallelization options
        if self.parallel.threads > 0: arguments += ["-t", str(self.parallel.threads)]
        if self.parallel.simulations > 1 and self.parallel.processes <= 1: arguments += ["-s", str(self.parallel.simulations)]
        if self.parallel.dataparallel and self.parallel.processes > 1: arguments += ["-d"]

        # Logging options
        if self.logging.brief: arguments += ["-b"]
        if self.logging.verbose: arguments += ["-v"]
        if self.logging.memory: arguments += ["-m"]
        if self.logging.allocation: arguments += ["-l", str(self.logging.allocation_limit)]

        # Options for input and output
        if input_dir_path is not None: arguments += ["-i", input_dir_path]
        if self.output_path is not None: arguments += ["-o", self.output_path]

        # Other options
        if self.emulate: arguments += ["-e"]

        # Ski file pattern
        if self.relative: arguments += ["-k"]
        if self.recursive: arguments += ["-r"]
        if isinstance(self.ski_pattern, basestring): arguments += [self.ski_pattern]
        elif isinstance(self.ski_pattern, list): arguments += self.ski_pattern
        else: raise ValueError("The ski pattern must consist of either a string or a list of strings")

        # If requested, convert the argument list into a string
        if to_string:

            # Create the final command string for this simulation
            command = " ".join(arguments)

            # Return the command string
            return command

        # Otherwise, return the list of argument values
        else: return arguments

    # -----------------------------------------------------------------

    def copy(self):

        """
        This function creates a copy of this SkirtArguments object
        :return:
        """

        # Create a new SkirtArguments object
        arguments = SkirtArguments()

        ## Set options identical to this instance

        # Options for the ski file pattern
        arguments.ski_pattern = self.ski_pattern
        arguments.recursive = self.recursive
        arguments.relative = self.relative

        # The input and output paths
        arguments.input_path = self.input_path
        arguments.output_path = self.output_path

        # Other options
        arguments.emulate = self.emulate    # Run in emulation mode
        arguments.single = self.single     # True if only a single simulation is expected

        # Options for logging
        arguments.logging.brief = self.logging.brief            # Brief console logging
        arguments.logging.verbose = self.logging.verbose        # Verbose logging
        arguments.logging.memory = self.logging.memory          # State the amount of used memory with each log message
        arguments.logging.allocation = self.logging.allocation  # Write log messages with the amount of (de)allocated memory
        arguments.logging.allocation_limit = self.logging.allocation_limit  # The lower limit for the amount of (de)allocated memory to be logged

        # Options for parallelization
        arguments.parallel.simulations = self.parallel.simulations   # The number of parallel simulations
        arguments.parallel.threads = self.parallel.threads           # The number of parallel threads per simulation
        arguments.parallel.processes = self.parallel.processes       # The number of parallel processes per simulation
        arguments.parallel.dataparallel = self.parallel.dataparallel # Run in data parallelization mode

        # Return the new object
        return arguments

    # -----------------------------------------------------------------

    def __str__(self):

        """
        This function ...
        """

        properties = []
        properties.append("ski path: " + self.ski_pattern)
        properties.append("recursive: " + str(self.recursive))
        properties.append("relative: " + str(self.relative))
        properties.append("input path: " + str(self.input_path))
        properties.append("output path: " + str(self.output_path))
        properties.append("emulate: " + str(self.emulate))
        properties.append("single: " + str(self.single))
        properties.append("brief: " + str(self.logging.brief))
        properties.append("verbose: " + str(self.logging.verbose))
        properties.append("memory: " + str(self.logging.memory))
        properties.append("allocation: " + str(self.logging.allocation))
        properties.append("allocation_limit: " + str(self.logging.allocation_limit))
        properties.append("simulations: " + str(self.parallel.simulations))
        properties.append("threads: " + str(self.parallel.threads))
        properties.append("processes: " + str(self.parallel.processes))
        properties.append("data-parallization: " + str(self.parallel.dataparallel))

        return_str = self.__class__.__name__ + ":\n"
        for property in properties: return_str += " -" + property + "\n"
        return return_str

    # -----------------------------------------------------------------

    def __repr__(self):

        """
        This function ...
        """

        return '<' + self.__class__.__name__ + " ski path: '" + self.ski_pattern + "'>"

# -----------------------------------------------------------------

def skirt_command(skirt_path, mpi_command, bind_to_cores, processes, threads, threads_per_core, scheduler, remote=None):

    """
    This function ...
    :param skirt_path:
    :param mpi_command:
    :param bind_to_cores:
    :param processes:
    :param threads:
    :param threads_per_core:
    :param scheduler:
    :param remote:
    :return:
    """

    # Multiprocessing mode
    if processes > 1:

        # Determine the command based on whether or not a scheduling system is used
        if scheduler: command = mpi_command.split()
        else: command = mpi_command.split() + ["-np", str(processes)]

        # If 'process to core' binding must be enabled, add the 'cpus-per-proc' option
        # (see https://www.open-mpi.org/faq/?category=tuning)
        if bind_to_cores:
            # Hyperthreading: threads_per_core will be > 1
            # No hyperthreading: threads_per_core will be 1
            # cores / process = (cores / thread) * (threads / process)
            cores_per_process = int(threads / threads_per_core)

            # Check if cpus-per-proc option is possible
            if remote is None or remote.mpi_knows_cpus_per_proc_option:
                command += ["--cpus-per-proc", str(cores_per_process)] # "CPU'S per process" means "core per process" in our definitions
            else: log.warning("The MPI version on the remote host does not know the 'cpus-per-proc' command. Processes cannot be bound to cores")

        # Add the SKIRT path and return the final command list
        command += [skirt_path]
        return command

    # Singleprocessing mode, no MPI command or options
    else: return [skirt_path]

# -----------------------------------------------------------------
