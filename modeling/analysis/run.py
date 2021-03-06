#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.analysis.run Contains the AnalysisRun class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from abc import ABCMeta, abstractproperty

# Import the relevant PTS classes and modules
from ...core.tools import filesystem as fs
from ...core.simulation.skifile import LabeledSkiFile, SkiFile
from ..core.model import Model
from ...core.tools import sequences
from ...core.basics.composite import SimplePropertyComposite
from ..fitting.run import FittingRun
from pts.core.tools.utils import lazyproperty
from ...core.tools.serialization import load_dict
from ...core.simulation.tree import DustGridTree
from ...core.simulation.grids import FileTreeDustGrid, load_grid
from ...core.simulation.wavelengthgrid import WavelengthGrid
from ..basics.projection import GalaxyProjection, EdgeOnProjection, FaceOnProjection
from ..basics.instruments import FullInstrument
from ...magic.basics.coordinatesystem import CoordinateSystem
from ...core.basics.log import log
from ...core.remote.remote import load_remote
from ...core.basics.configuration import Configuration
from ...core.simulation.logfile import LogFile
from ...core.tools import strings
from ...core.extract.progress import ProgressTable
from ...core.extract.timeline import TimeLineTable
from ...core.extract.memory import MemoryUsageTable
from ...magic.core.dataset import DataSet
from ..core.environment import colours_name as colour_maps_name
from ..core.environment import ssfr_name as ssfr_maps_name
from ..core.environment import tir_name as tir_maps_name
from ..core.environment import attenuation_name as attenuation_maps_name
from ..core.environment import old_name as old_maps_name
from ..core.environment import young_name as young_maps_name
from ..core.environment import ionizing_name as ionizing_maps_name
from ..core.environment import dust_name as dust_maps_name
from ...core.data.sed import ObservedSED, SED
from ...magic.core.datacube import DataCube

# -----------------------------------------------------------------

wavelengths_filename = "wavelengths.txt"
dustgridtree_filename = "tree.dat"

# -----------------------------------------------------------------

class AnalysisRunInfo(SimplePropertyComposite):

    """
    This class ...
    """

    def __init__(self, **kwargs):

        """
        The constructor ...
        """

        # Call the constructor of the base class
        super(AnalysisRunInfo, self).__init__()

        # Define properties
        self.add_string_property("name", "name of the analysis run")
        self.add_string_property("path", "path of the analysis run")
        self.add_string_property("fitting_run", "fitting run name")
        self.add_string_property("generation_name", "generation name")
        self.add_string_property("simulation_name", "simulation name")
        self.add_string_property("model_name", "name of the model")
        self.add_real_property("chi_squared", "chi squared value of the fitted model")
        self.add_string_property("reference_deprojection", "name of the deprojection model that is used for the creating the instruments")

        # Parameter values dictionary
        self.add_section("parameter_values", "parameter values", dynamic=True)

        # Set properties
        self.set_properties(kwargs)

# -----------------------------------------------------------------

dust_grid_filename = "dust_grid.dg"
wavelength_grid_filename = "wavelength_grid.dat"
dust_grid_build_name = "dust grid"
info_filename = "info.dat"
config_filename = "config.cfg"
launch_config_filename = "launch_config.cfg"
input_filename = "input.dat"
instruments_name = "instruments"
projections_name = "projections"
extract_name = "extr"
plot_name = "plot"
misc_name = "misc"
evaluation_name = "evaluation"
attenuation_name = "attenuation"
colours_name = "colours"
residuals_name = "residuals"
maps_name = "maps"
heating_name = "heating"
dust_grid_tree_filename = "tree.dat"

# Projections
earth_projection_filename = "earth.proj"
faceon_projection_filename = "faceon.proj"
edgeon_projection_filename = "edgeon.proj"

# Instruments
earth_instrument_filename = "earth.instr"
faceon_instrument_filename = "faceon.instr"
edgeon_instrument_filename = "edgeon.instr"

# -----------------------------------------------------------------

class AnalysisRunBase(object):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    @property
    def from_fitting(self):

        """
        This function ...
        :return:
        """

        #return self.fitting_run is not None
        return self.fitting_run_name is not None

    # -----------------------------------------------------------------

    @property
    def from_model(self):

        """
        This function ...
        :return:
        """

        #return self.fitting_run is None
        return self.fitting_run_name is None

    # -----------------------------------------------------------------

    # @abstractproperty
    # def galaxy_name(self):
    #
    #     """
    #     This function ...
    #     :return:
    #     """
    #
    #     pass

    # -----------------------------------------------------------------

    @property
    def from_generation(self):

        """
        This function ...
        :return:
        """

        # Otherwise: from initial guess

        return self.from_fitting and self.generation_name is not None

    # -----------------------------------------------------------------

    @property
    def from_initial_guess(self):

        """
        This function ...
        :return:
        """

        # Otherwise: from best simulation of a certain generation

        return self.from_fitting and self.generation_name is None

    # -----------------------------------------------------------------

    @property
    def name(self):

        """
        This function ...
        :return:
        """

        return self.info.name

    # -----------------------------------------------------------------

    @property
    def generation_name(self):

        """
        This function ...
        :return:
        """

        return self.info.generation_name

    # -----------------------------------------------------------------

    @property
    def simulation_name(self):

        """
        This function ...
        :return:
        """

        return self.info.simulation_name

    # -----------------------------------------------------------------

    @property
    def model_name(self):

        """
        This function ...
        :return:
        """

        return self.info.model_name

    # -----------------------------------------------------------------

    @property
    def input_file_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, input_filename)

    # -----------------------------------------------------------------

    @property
    def ski_file_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, self.galaxy_name + ".ski")

    # -----------------------------------------------------------------

    @property
    def wavelength_grid_path(self):

        """
        This function ...
        :return:
        """

        # Set the path to the wavelength grid file
        return fs.join(self.path, wavelength_grid_filename)

    # -----------------------------------------------------------------

    @property
    def nwavelengths(self):

        """
        This function ...
        :return:
        """

        return len(self.wavelength_grid)

    # -----------------------------------------------------------------

    @property
    def nwavelengths_heating(self):

        """
        This function ...
        :return:
        """

        return len(self.wavelength_grid_heating)

    # -----------------------------------------------------------------

    @property
    def dust_grid_path(self):

        """
        This function ...
        :return:
        """

        # Set the path to the dust grid file
        return fs.join(self.path, dust_grid_filename)

    # -----------------------------------------------------------------

    @property
    def info_path(self):

        """
        This function ...
        :return:
        """

        # Set the path to the analysis run info file
        return fs.join(self.path, info_filename)

    # -----------------------------------------------------------------

    @property
    def config_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, config_filename)

    # -----------------------------------------------------------------

    @property
    def heating_config_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.heating_path, config_filename)

    # -----------------------------------------------------------------

    @property
    def launch_config_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, launch_config_filename)

    # -----------------------------------------------------------------

    @property
    def out_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, "out")

    # -----------------------------------------------------------------

    @property
    def output_path(self):

        """
        This function ...
        :return:
        """

        return self.out_path

    # -----------------------------------------------------------------

    @property
    def logfile_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.out_path, self.galaxy_name + "_log.txt")

    # -----------------------------------------------------------------

    @property
    def extr_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, extract_name)

    # -----------------------------------------------------------------

    @property
    def extract_path(self):

        """
        This function ...
        :return:
        """

        return self.extr_path

    # -----------------------------------------------------------------

    @property
    def progress_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.extr_path, "progress.dat")

    # -----------------------------------------------------------------

    @property
    def timeline_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.extr_path, "timeline.dat")

    #  -----------------------------------------------------------------

    @property
    def memory_path(self):

        """
        Thisf unction ...
        :return:
        """

        return fs.join(self.extr_path, "memory.dat")

    # -----------------------------------------------------------------

    @property
    def plot_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, plot_name)

    # -----------------------------------------------------------------

    @property
    def misc_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, misc_name)

    # -----------------------------------------------------------------

    @property
    def evaluation_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, evaluation_name)

    # -----------------------------------------------------------------

    @property
    def attenuation_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, attenuation_name)

    # -----------------------------------------------------------------

    @property
    def colours_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, colours_name)

    # -----------------------------------------------------------------

    @property
    def colours_observed_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.colours_path, "observed")

    # -----------------------------------------------------------------

    @property
    def colours_simulated_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.colours_path, "simulated")

    # -----------------------------------------------------------------

    @property
    def colours_residuals_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.colours_path, "residuals")

    # -----------------------------------------------------------------

    @abstractproperty
    def colour_names(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def residuals_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, residuals_name)

    # -----------------------------------------------------------------

    @property
    def maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, maps_name)

    # -----------------------------------------------------------------

    @property
    def colour_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, colour_maps_name)

    # -----------------------------------------------------------------

    @property
    def colour_maps_name(self):

        """
        Thisn function ...
        :return:
        """

        return fs.name(self.colour_maps_path)

    # -----------------------------------------------------------------

    @property
    def ssfr_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, ssfr_maps_name)

    # -----------------------------------------------------------------

    @property
    def ssfr_maps_name(self):

        """
        Thisn function ...
        :return:
        """

        return fs.name(self.ssfr_maps_path)

    # -----------------------------------------------------------------

    @property
    def tir_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, tir_maps_name)

    # -----------------------------------------------------------------

    @property
    def tir_maps_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.tir_maps_path)

    # -----------------------------------------------------------------

    @property
    def attenuation_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, attenuation_maps_name)

    # -----------------------------------------------------------------

    @property
    def attenuation_maps_name(self):

        """
        Thisn function ...
        :return:
        """

        return fs.name(self.attenuation_maps_path)

    # -----------------------------------------------------------------

    @property
    def old_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, old_maps_name)

    # -----------------------------------------------------------------

    @property
    def old_maps_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.old_maps_path)

    # -----------------------------------------------------------------

    @property
    def dust_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, dust_maps_name)

    # -----------------------------------------------------------------

    @property
    def dust_maps_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.dust_maps_path)

    # -----------------------------------------------------------------

    @property
    def young_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, young_maps_name)

    # -----------------------------------------------------------------

    @property
    def young_maps_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.young_maps_path)

    # -----------------------------------------------------------------

    @property
    def ionizing_maps_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.maps_path, ionizing_maps_name)

    # -----------------------------------------------------------------

    @property
    def ionizing_maps_name(self):

        """
        Thisf unction ...
        :return:
        """

        return fs.name(self.ionizing_maps_path)

    # -----------------------------------------------------------------

    @property
    def heating_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, heating_name)

    # -----------------------------------------------------------------

    @property
    def dust_grid_build_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, dust_grid_build_name)

    # -----------------------------------------------------------------

    @property
    def dust_grid_simulation_out_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.dust_grid_build_path, "out")

    # -----------------------------------------------------------------

    @property
    def heating_wavelength_grid_path(self):

        """
        This fucntion ...
        :return:
        """

        return fs.join(self.heating_path, wavelength_grid_filename)

    # -----------------------------------------------------------------

    @property
    def heating_instruments_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.heating_path, instruments_name)

    # -----------------------------------------------------------------

    def heating_simulation_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.create_directory_in(self.heating_path, contribution)

    # -----------------------------------------------------------------

    def heating_ski_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.join(self.heating_simulation_path_for_contribution(contribution), self.galaxy_name + ".ski")

    # -----------------------------------------------------------------

    def heating_output_path_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        return fs.join(self.heating_simulation_path_for_contribution(contribution), "out")

    # -----------------------------------------------------------------

    @property
    def analysis_run_name(self):

        """
        This function ...
        :return:
        """

        return self.info.name

    # -----------------------------------------------------------------

    @property
    def dust_grid_simulation_logfile_path(self):

        """
        This function ...
        :return:
        """

        # Determine the output path of the dust grid simulation
        out_path = self.dust_grid_simulation_out_path

        # Determine the log file path
        logfile_path = fs.join(out_path, "dustgrid_log.txt")

        # Return the log file path
        return logfile_path

    # -----------------------------------------------------------------

    @abstractproperty
    def has_dust_grid_simulation_logfile(self):

        """
        This property ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def dust_grid_simulation_logfile(self):

        """
        This property ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def dust_grid_tree(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @lazyproperty
    def ncells(self):

        """
        This function ...
        :return:
        """

        # Read the log file
        if self.has_dust_grid_simulation_logfile:

            # Debugging
            log.debug("Determining the number of dust cells by reading the dust grid simulation's log file ...")

            # Load the log file and get the number of dust cells
            return self.dust_grid_simulation_logfile.dust_cells

        # Log file cannot be found
        else:

            # Debugging
            log.debug("Determining the number of dust cells by reading the dust cell tree data file (this can take a while) ...")

            # Get the number of leave nodes
            return self.dust_grid_tree.nleaves  # requires loading the entire tree file!

    # -----------------------------------------------------------------

    def get_remote_script_input_paths_for_host(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        paths = []

        # Loop over the commands
        for command in self.get_remote_script_commands_for_host(host_id):

            input_path = command.split("-i ")[1]
            if strings.is_quote_character(input_path[0]): input_path = input_path[1:].split(input_path[0])[0]
            else: input_path = input_path.split(" ")[0]

            paths.append(input_path)

        # Return the list of paths
        return paths

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_young(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def nyoung_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_tir(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def ntir_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_ssfr(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def nssfr_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_old(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def nold_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_ionizing(self):

        """
        Thisf unction ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def nionizing_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_dust(self):

        """
        Thisn function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def ndust_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_colours(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def ncolour_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def has_maps_attenuation(self):

        """
        This property ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractproperty
    def nattenuation_maps(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def has_maps(self):

        """
        This unction ...
        :return:
        """

        return self.has_maps_attenuation or self.has_maps_colours or self.has_maps_dust or self.has_maps_ionizing or self.has_maps_old or self.has_maps_ssfr or self.has_maps_tir or self.has_maps_young

    # -----------------------------------------------------------------

    @abstractproperty
    def has_heating(self):

        """
        This property ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def simulated_sed_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.output_path, self.simulation_prefix + "_earth_sed.dat")

    # -----------------------------------------------------------------

    @abstractproperty
    def has_simulated_sed(self):

        """
        This property ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def simulated_fluxes_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.misc_path, self.simulation_prefix + "_earth_fluxes.dat")

    # -----------------------------------------------------------------

    @abstractproperty
    def has_simulated_fluxes(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def simulation_prefix(self):

        """
        This function ...
        :return:
        """

        return self.galaxy_name

    # -----------------------------------------------------------------

    @property
    def simulated_datacube_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.output_path, self.galaxy_name + "_earth_total.fits")

# -----------------------------------------------------------------

class AnalysisRun(AnalysisRunBase):

    """
    This class ...
    """

    def __init__(self, galaxy_name=None, info=None):

        """
        The constructor ...
        :param galaxy_name:
        :param info:
        """

        # Set attributes
        self.galaxy_name = galaxy_name
        self.info = info

        ## Create directories

        # The directory for the projections and the instruments
        if not fs.is_directory(self.projections_path): fs.create_directory(self.projections_path)
        if not fs.is_directory(self.instruments_path): fs.create_directory(self.instruments_path)

        # The directory for the dust grid output
        if not fs.is_directory(self.dust_grid_build_path): fs.create_directory(self.dust_grid_build_path)
        if not fs.is_directory(self.dust_grid_simulation_out_path): fs.create_directory(self.dust_grid_simulation_out_path)

        # Simulation directories
        if not fs.is_directory(self.output_path): fs.create_directory(self.output_path)
        if not fs.is_directory(self.extract_path): fs.create_directory(self.extract_path)
        if not fs.is_directory(self.plot_path): fs.create_directory(self.plot_path)
        if not fs.is_directory(self.misc_path): fs.create_directory(self.misc_path)

        # Evaluation
        if not fs.is_directory(self.evaluation_path): fs.create_directory(self.evaluation_path)

        # Analysis directories
        if not fs.is_directory(self.attenuation_path): fs.create_directory(self.attenuation_path)
        if not fs.is_directory(self.colours_path): fs.create_directory(self.colours_path)
        if not fs.is_directory(self.residuals_path): fs.create_directory(self.residuals_path)
        if not fs.is_directory(self.maps_path): fs.create_directory(self.maps_path)
        if not fs.is_directory(self.heating_path): fs.create_directory(self.heating_path)

        # Maps subdirectories
        if not fs.is_directory(self.colour_maps_path): fs.create_directory(self.colour_maps_path)
        if not fs.is_directory(self.ssfr_maps_path): fs.create_directory(self.ssfr_maps_path)
        if not fs.is_directory(self.tir_maps_path): fs.create_directory(self.tir_maps_path)
        if not fs.is_directory(self.attenuation_maps_path): fs.create_directory(self.attenuation_maps_path)
        if not fs.is_directory(self.old_maps_path): fs.create_directory(self.old_maps_path)
        if not fs.is_directory(self.dust_maps_path): fs.create_directory(self.dust_maps_path)
        if not fs.is_directory(self.young_maps_path): fs.create_directory(self.young_maps_path)
        if not fs.is_directory(self.ionizing_maps_path): fs.create_directory(self.ionizing_maps_path)

        # Heating subdirectories
        if not fs.is_directory(self.heating_instruments_path): fs.create_directory(self.heating_instruments_path)

    # -----------------------------------------------------------------

    @classmethod
    def from_name(cls, modeling_path, name):

        """
        This function ...
        :param modeling_path:
        :param name:
        :return:
        """

        analysis_path = fs.join(modeling_path, "analysis")
        run_path = fs.join(analysis_path, name)
        return cls.from_path(run_path)

    # -----------------------------------------------------------------

    @classmethod
    def from_path(cls, path):

        """
        This function ...
        :param path:
        :return:
        """

        # Determine the info path
        info_path = fs.join(path, info_filename)
        if not fs.is_file(info_path): raise IOError("Could not find the info file")
        else: return cls.from_info(info_path)

    # -----------------------------------------------------------------

    @classmethod
    def from_info(cls, info_path):

        """
        This function ...
        :param info_path:
        :return:
        """

        # Load the analysis run info
        info = AnalysisRunInfo.from_file(info_path)

        # Create the instance
        run = cls(info=info)

        # Set galaxy name
        modeling_path = fs.directory_of(fs.directory_of(run.info.path))
        run.galaxy_name = fs.name(modeling_path)

        # Return the analysis run object
        return run

    # -----------------------------------------------------------------

    @property
    def has_dust_grid_simulation_logfile(self):

        """
        Thisnfunction ...
        :return:
        """

        return fs.is_file(self.dust_grid_simulation_logfile_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid_simulation_logfile(self):

        """
        This function ...
        :return:
        """

        return LogFile.from_file(self.dust_grid_simulation_logfile_path)

    # -----------------------------------------------------------------

    @property
    def has_output(self):

        """
        Thisn function ...
        :return:
        """

        return fs.has_files_in_path(self.output_path)

    # -----------------------------------------------------------------

    @property
    def has_logfile(self):

        """
        This function ...
        :return:
        """

        return fs.is_file(self.logfile_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def logfile(self):

        """
        This function ...
        :return:
        """

        return LogFile.from_file(self.logfile_path)

    # -----------------------------------------------------------------

    @property
    def has_misc(self):

        """
        Thisn function ...
        :return:
        """

        return fs.has_files_in_path(self.misc_path)

    # -----------------------------------------------------------------

    @property
    def has_extracted(self):

        """
        Thisn function ...
        :return:
        """

        return fs.has_files_in_path(self.extr_path)

    # -----------------------------------------------------------------

    @property
    def has_progress(self):

        """
        Thisnfunction ...
        :return:
        """

        return fs.is_file(self.progress_path)

    # -----------------------------------------------------------------

    @property
    def has_timeline(self):

        """
        Thisfunction ...
        :return:
        """

        return fs.is_file(self.timeline_path)

    # -----------------------------------------------------------------

    @property
    def has_memory(self):

        """
        Thisfunction ...
        :return:
        """

        return fs.is_file(self.memory_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def progress(self):

        """
        This function ...
        :return:
        """

        return ProgressTable.from_file(self.progress_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def timeline(self):

        """
        This function ...
        :return:
        """

        return TimeLineTable.from_file(self.timeline_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def memory(self):

        """
        This function ...
        :return:
        """

        return MemoryUsageTable.from_file(self.memory_path)

    # -----------------------------------------------------------------

    @property
    def has_plots(self):

        """
        Thisf unction ...
        :return:
        """

        return fs.has_files_in_path(self.plot_path)

    # -----------------------------------------------------------------

    @property
    def has_attenuation(self):

        """
        This function ...
        :return:
        """

        return fs.is_directory(self.attenuation_path) and not fs.is_empty(self.attenuation_path)

    # -----------------------------------------------------------------

    @property
    def has_colours(self):

        """
        This functino ...
        :return:
        """

        return fs.is_directory(self.colours_path) and not fs.is_empty(self.colours_path)

    # -----------------------------------------------------------------

    @property
    def colour_names(self):

        """
        This function ...
        :return:
        """

        return fs.files_in_path(self.colours_simulated_path, extension="fits", returns="name")

    # -----------------------------------------------------------------

    @property
    def has_residuals(self):

        """
        Thisf unction ...
        :return:
        """

        return fs.is_directory(self.residuals_path) and not fs.is_empty(self.residuals_path)

    # -----------------------------------------------------------------

    @property
    def residual_image_names(self):

        """
        This function ...
        :return:
        """

        return fs.files_in_path(self.residuals_path, extension="fits", not_contains=["significance"], returns="name")

    # -----------------------------------------------------------------

    @property
    def has_maps_attenuation(self):

        """
        Thisn function ...
        :return:
        """

        return fs.is_directory(self.attenuation_maps_path) and not fs.is_empty(self.attenuation_maps_path)

    # -----------------------------------------------------------------

    @property
    def nattenuation_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.attenuation_maps_path, extension="fits"): return fs.nfiles_in_path(self.attenuation_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.attenuation_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_colours(self):

        """
        Thisnfunction ...
        :return:
        """

        return fs.is_directory(self.colour_maps_path) and not fs.is_empty(self.colour_maps_path)

    # -----------------------------------------------------------------

    @property
    def ncolour_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.colour_maps_path, extension="fits"): return fs.nfiles_in_path(self.colour_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.colour_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_dust(self):

        """
        This function ...
        :return:
        """

        return fs.is_directory(self.dust_maps_path) and not fs.is_empty(self.dust_maps_path)

    # -----------------------------------------------------------------

    @property
    def ndust_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.dust_maps_path, extension="fits"): return fs.nfiles_in_path(self.dust_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.dust_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_ionizing(self):

        """
        Thisfunction ...
        :return:
        """

        return fs.is_directory(self.ionizing_maps_path) and not fs.is_empty(self.ionizing_maps_path)

    # -----------------------------------------------------------------

    @property
    def nionizing_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.ionizing_maps_path, extension="fits"): return fs.nfiles_in_path(self.ionizing_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.ionizing_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_old(self):

        """
        This function ...
        :return:
        """

        return fs.is_directory(self.old_maps_path) and not fs.is_empty(self.old_maps_path)

    # -----------------------------------------------------------------

    @property
    def nold_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.old_maps_path, extension="fits"): return fs.nfiles_in_path(self.old_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.old_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_ssfr(self):

        """
        Thisjfunction ...
        :return:
        """

        return fs.is_directory(self.ssfr_maps_path) and not fs.is_empty(self.ssfr_maps_path)

    # -----------------------------------------------------------------

    @property
    def nssfr_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.ssfr_maps_path, extension="fits"): return fs.nfiles_in_path(self.ssfr_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.ssfr_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_tir(self):

        """
        This function ...
        :return:
        """

        return fs.is_directory(self.tir_maps_path) and not fs.is_empty(self.tir_maps_path)

    # -----------------------------------------------------------------

    @property
    def ntir_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.tir_maps_path, extension="fits"): return fs.nfiles_in_path(self.tir_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.tir_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_young(self):

        """
        This function ...
        :return:
        """

        return fs.is_directory(self.young_maps_path) and not fs.is_empty(self.young_maps_path)

    # -----------------------------------------------------------------

    @property
    def nyoung_maps(self):

        """
        This function ...
        :return:
        """

        if fs.has_files_in_path(self.young_maps_path, extension="fits"): return fs.nfiles_in_path(self.young_maps_path, extension="fits")
        else: return fs.nfiles_in_path(self.young_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_heating(self):

        """
        This function ...
        :return:
        """

        return fs.is_file(self.heating_config_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def nfiles(self):

        """
        This function ...
        :return:
        """

        return fs.nfiles_in_path(self.path, recursive=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def disk_space(self):

        """
        This function ...
        :return:
        """

        return fs.directory_size(self.path)

    # -----------------------------------------------------------------

    @property
    def analysis_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.path)

    # -----------------------------------------------------------------

    @property
    def modeling_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.analysis_path)

    # -----------------------------------------------------------------

    @property
    def path(self):

        """
        This function ...
        :return:
        """

        return self.info.path

    # -----------------------------------------------------------------

    @lazyproperty
    def config(self):

        """
        This function ...
        :return:
        """

        return Configuration.from_file(self.config_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_config(self):

        """
        This function ...
        :return:
        """

        return Configuration.from_file(self.heating_config_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_grid(self):

        """
        This function ...
        :return:
        """

        return WavelengthGrid.from_skirt_input(self.wavelength_grid_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_grid_heating(self):

        """
        This function ...
        :return:
        """

        return WavelengthGrid.from_skirt_input(self.heating_wavelength_grid_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid(self):

        """
        This function ...
        :return:
        """

        return load_grid(self.dust_grid_path)

    # -----------------------------------------------------------------

    @property
    def analysis_run_path(self):

        """
        This function ...
        :return:
        """

        return self.info.path

    # -----------------------------------------------------------------

    @property
    def ski_file(self):

        """
        This function ...
        :return:
        """

        return LabeledSkiFile(self.ski_file_path)

    # -----------------------------------------------------------------

    @property
    def input_paths(self):

        """
        This function ...
        :return:
        """

        return load_dict(self.input_file_path)

    # -----------------------------------------------------------------

    @property
    def heating_input_paths(self):

        """
        This function ...
        :return:
        """

        paths = self.input_paths
        paths[wavelengths_filename] = self.heating_wavelength_grid_path
        return paths

    # -----------------------------------------------------------------

    @property
    def dust_grid_tree_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.dust_grid_build_path, dust_grid_tree_filename)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid_tree(self):

        """
        This function ...
        :return:
        """

        # Give debug message
        log.debug("Loading the dust grid tree, this may take a while (depending on the number of nodes) ...")

        # Return the tree
        return DustGridTree.from_file(self.dust_grid_tree_path)

    # -----------------------------------------------------------------

    def create_file_tree_dust_grid(self, search_method="Neighbor", write=False):

        """
        This function ...
        :param search_method:
        :param write:
        :return:
        """

        grid = FileTreeDustGrid(filename=self.dust_grid_tree_path, search_method=search_method, write=write)
        return grid

    # -----------------------------------------------------------------

    @lazyproperty
    def has_dust_grid_tree(self):

        """
        This function ...
        :return:
        """

        return fs.is_file(self.dust_grid_tree_path)

    # -----------------------------------------------------------------

    @property
    def instruments_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, instruments_name)

    # -----------------------------------------------------------------

    @property
    def projections_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.path, projections_name)

    # -----------------------------------------------------------------

    @property
    def earth_projection_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.projections_path, earth_projection_filename)

    # -----------------------------------------------------------------

    @property
    def faceon_projection_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.projections_path, faceon_projection_filename)

    # -----------------------------------------------------------------

    @property
    def edgeon_projection_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.projections_path, edgeon_projection_filename)

    # -----------------------------------------------------------------

    @lazyproperty
    def earth_projection(self):

        """
        This function ...
        :return:
        """

        return GalaxyProjection.from_file(self.earth_projection_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def edgeon_projection(self):

        """
        This function ...
        :return:
        """

        return EdgeOnProjection.from_file(self.edgeon_projection_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def faceon_projection(self):

        """
        This function ...
        :return:
        """

        return FaceOnProjection.from_file(self.faceon_projection_path)

    # -----------------------------------------------------------------

    @property
    def earth_instrument_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.instruments_path, earth_instrument_filename)

    # -----------------------------------------------------------------

    @property
    def faceon_instrument_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.instruments_path, faceon_instrument_filename)

    # -----------------------------------------------------------------

    @property
    def edgeon_instrument_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.instruments_path, edgeon_instrument_filename)

    # -----------------------------------------------------------------

    @lazyproperty
    def earth_instrument(self):

        """
        This function ...
        :return:
        """

        return FullInstrument.from_file(self.earth_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def faceon_instrument(self):

        """
        This function ...
        :return:
        """

        return FullInstrument.from_file(self.faceon_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def edgeon_instrument(self):

        """
        This function ...
        :return:
        """

        return FullInstrument.from_file(self.edgeon_instrument_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def fitting_run_name(self):

        """
        This function ...
        :return:
        """

        return self.info.fitting_run

    # -----------------------------------------------------------------

    @lazyproperty
    def fitting_run(self):

        """
        This function ...
        :return:
        """

        return FittingRun.from_name(self.modeling_path, self.fitting_run_name)

    # -----------------------------------------------------------------

    @lazyproperty
    def model_suite(self):

        """
        This function ...
        :return:
        """

        from ..build.suite import ModelSuite
        return ModelSuite.from_modeling_path(self.modeling_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def model_definition(self):

        """
        This function ...
        :return:
        """

        #from ..build.definition import ModelDefinition
        return self.model_suite.get_model_definition(self.model_name)

    # -----------------------------------------------------------------

    @property
    def model_old_map_name(self):

        """
        This function ...
        :return:
        """

        return self.model_suite.get_old_map_name_for_model(self.model_name)

    # -----------------------------------------------------------------

    @property
    def model_young_map_name(self):

        """
        Thisn function ...
        :return:
        """

        return self.model_suite.get_young_map_name_for_model(self.model_name)

    # -----------------------------------------------------------------

    @property
    def model_ionizing_map_name(self):

        """
        This function ...
        :return:
        """

        return self.model_suite.get_ionizing_map_name_for_model(self.model_name)

    # -----------------------------------------------------------------

    @property
    def model_dust_map_name(self):

        """
        This function ...
        :return:
        """

        return self.model_suite.get_dust_map_name_for_model(self.model_name)

    # -----------------------------------------------------------------

    @property
    def model_old_map(self):

        """
        This function ...
        :return:
        """

        return self.model_suite.load_stellar_component_map(self.model_name, "old")

    # -----------------------------------------------------------------

    @property
    def model_young_map(self):

        """
        Thisn function ...
        :return:
        """

        return self.model_suite.load_stellar_component_map(self.model_name, "young")

    # -----------------------------------------------------------------

    @property
    def model_ionizing_map(self):

        """
        This function ....
        :return:
        """

        return self.model_suite.load_stellar_component_map(self.model_name, "ionizing")

    # -----------------------------------------------------------------

    @property
    def model_dust_map(self):

        """
        This function ...
        :return:
        """

        return self.model_suite.load_dust_component_map(self.model_name, "disk")

    # -----------------------------------------------------------------

    @lazyproperty
    def generation_name(self):

        """
        This function ...
        :return:
        """

        return self.info.generation_name

    # -----------------------------------------------------------------

    @lazyproperty
    def simulation_name(self):

        """
        This function ...
        :return:
        """

        return self.info.simulation_name

    # -----------------------------------------------------------------

    @lazyproperty
    def parameter_values(self):

        """
        This function ...
        :return:
        """

        # Get the ski file
        ski = self.ski_file

        # Get the values of all the labeled parameters
        values = ski.get_labeled_values()

        # Return the parameter values
        return values

    # -----------------------------------------------------------------

    @lazyproperty
    def chi_squared(self):

        """
        This function ...
        :return:
        """

        return self.info.chi_squared

    # -----------------------------------------------------------------

    @lazyproperty
    def model(self):

        """
        This function ...
        :return:
        """

        # Create the model and return it
        return Model(simulation_name=self.simulation_name, chi_squared=self.chi_squared, parameter_values=self.parameter_values)

    # -----------------------------------------------------------------

    @property
    def uses_grid_resolution(self):

        """
        Thisf unction ...
        :return:
        """

        return self.info.reference_deprojection == "grid"

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_deprojection_component_name(self):

        """
        Thisf unction ...
        :return:
        """

        if self.uses_grid_resolution: return None
        return self.info.reference_deprojection

    # -----------------------------------------------------------------

    @lazyproperty
    def is_stellar_reference_deprojection(self):

        """
        This function ...
        :return:
        """

        if self.uses_grid_resolution: raise ValueError("This function shouldn't be called")
        return self.reference_deprojection_component_name in self.model_suite.get_stellar_component_names(self.model_name)

    # -----------------------------------------------------------------

    @lazyproperty
    def is_dust_reference_deprojection(self):

        """
        This function ...
        :return:
        """

        if self.uses_grid_resolution: raise ValueError("This function shouldn't be called")
        return self.reference_deprojection_component_name in self.model_suite.get_dust_component_names(self.model_name)

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_deprojection_component(self):

        """
        This function ...
        :return:
        """

        if self.reference_deprojection_component_name is None: return None
        else:
            if self.is_stellar_reference_deprojection: return self.model_suite.load_stellar_component(self.model_name, self.reference_deprojection_component_name, add_map=False)
            elif self.is_dust_reference_deprojection: return self.model_suite.load_dust_component(self.model_name, self.reference_deprojection_component_name, add_map=False)
            else: raise ValueError("Reference deprojection component name '" + self.reference_deprojection_component_name + "' not recognized as either stellar or dust")

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_deprojection(self):

        """
        Thisf unction ...
        :return:
        """

        if self.reference_deprojection_component_name is None: return None
        else:
            if self.is_stellar_reference_deprojection: return self.model_suite.load_stellar_component_deprojection(self.model_name, self.reference_deprojection_component_name, add_map=False)
            elif self.is_dust_reference_deprojection: return self.model_suite.load_dust_component_deprojection(self.model_name, self.reference_deprojection_component_name, add_map=False)
            else: raise ValueError("Reference deprojection component name '" + self.reference_deprojection_component_name + "' not recognized as either stellar or dust")

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_map(self):

        """
        This function ...
        :return:
        """

        if self.reference_deprojection_component_name is None: return None
        else:
            if self.is_stellar_reference_deprojection: return self.model_suite.load_stellar_component_map(self.model_name, self.reference_deprojection_component_name)
            elif self.is_dust_reference_deprojection: return self.model_suite.load_dust_component_map(self.model_name, self.reference_deprojection_component_name)
            else: raise ValueError("Reference deprojection component name '" + self.reference_deprojection_component_name + "' not recognized as either stellar or dust")

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_map_path(self):

        """
        This function ...
        :return:
        """

        if self.reference_deprojection_component_name is None: return None
        else:
            if self.is_stellar_reference_deprojection: return self.model_suite.get_stellar_component_map_path(self.model_name, self.reference_deprojection_component_name)
            elif self.is_dust_reference_deprojection: return self.model_suite.get_dust_component_map_path(self.model_name, self.reference_deprojection_component_name)
            else: raise ValueError("Reference deprojection component name '" + self.reference_deprojection_component_name + "' not recognized as either stellar or dust")

    # -----------------------------------------------------------------

    @lazyproperty
    def reference_wcs(self):

        """
        This function ...
        :return:
        """

        if self.reference_map_path is None: return None
        else: return CoordinateSystem.from_file(self.reference_map_path)

    # -----------------------------------------------------------------

    @property
    def remote_script_paths(self):

        """
        This function ...
        :return:
        """

        return fs.files_in_path(self.path, extension="sh")

    # -----------------------------------------------------------------

    def get_remote_script_commands(self):

        """
        This fucntion ...
        :return:
        """

        commands = dict()

        # Loop over the script paths
        for path in self.remote_script_paths:

            # Get host ID
            host_id = fs.strip_extension(fs.name(path))

            lines = []

            # Open the file
            for line in fs.read_lines(path):

                if line.startswith("#"): continue
                if not line.strip(): continue

                lines.append(line)

            # Set the commands
            commands[host_id] = lines

        # Return the commands
        return commands

    # -----------------------------------------------------------------

    def get_remote_script_commands_for_host(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        commands = self.get_remote_script_commands()
        if host_id in commands: return commands[host_id]
        else: return []

    # -----------------------------------------------------------------

    def get_heating_ski_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        path = self.heating_ski_path_for_contribution(contribution)
        return SkiFile(path)

    # -----------------------------------------------------------------

    @property
    def has_simulated_sed(self):

        """
        This function ...
        :return:
        """

        return fs.is_file(self.simulated_sed_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_sed(self):

        """
        This function ...
        :return:
        """

        return SED.from_skirt(self.simulated_sed_path)

    # -----------------------------------------------------------------

    @property
    def has_simulated_fluxes(self):

        """
        This function ...
        :return:
        """

        return fs.is_file(self.simulated_fluxes_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_fluxes(self):

        """
        This function ...
        :return:
        """

        return ObservedSED.from_file(self.simulated_fluxes_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_datacube(self):

        """
        This function ...
        :return:
        """

        # Load the datacube
        datacube = DataCube.from_file(self.simulated_datacube_path, self.wavelength_grid)

        # Set the wcs
        datacube.wcs = self.reference_wcs

        # Return the datacube
        return datacube

    # -----------------------------------------------------------------

    # def get_simulated_frame_for_filter(self, fltr, convolve=False):
    #
    #     """
    #     This function ...
    #     :param fltr:
    #     :param convolve:
    #     :return:
    #     """
    #
    #     return self.simulated_datacube.frame_for_filter(fltr, convolve=convolve)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_dataset(self):

        """
        This function ...
        :return:
        """

        get_name_function = lambda filename: filename.split("__")[1]
        return DataSet.from_directory(self.misc_path, get_name=get_name_function)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_frame_list(self):

        """
        This function ...
        :return:
        """

        return self.simulated_dataset.get_framelist(named=False)  # on filter

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_named_frame_list(self):

        """
        This function ...
        :return:
        """

        return self.simulated_dataset.get_framelist(named=True)  # on name

    # -----------------------------------------------------------------

    def get_simulated_frame_for_filter(self, fltr):

        """
        THis function ...
        :param fltr:
        :return:
        """

        # Return the simulated frame
        return self.simulated_frame_list[fltr]

    # -----------------------------------------------------------------

    @lazyproperty
    def maps_collection(self):

        """
        This function ...
        :return:
        """

        from ..maps.collection import MapsCollection
        return MapsCollection.from_modeling_path(self.modeling_path, analysis_run_name=self.name)

    # -----------------------------------------------------------------

    @lazyproperty
    def observation_maps_collection(self):

        """
        Thisn function ...
        :return:
        """

        from ..maps.collection import MapsCollection
        return MapsCollection.from_modeling_path(self.modeling_path)

    # -----------------------------------------------------------------

    @property
    def colours_methods(self):

        """
        Thisfunction ...
        :return:
        """

        return self.observation_maps_collection.get_colours_methods(flatten=True)

    # -----------------------------------------------------------------

    @property
    def colours_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_colours_origins(flatten=True)

    # -----------------------------------------------------------------

    @property
    def ssfr_methods(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_ssfr_methods(flatten=True)

    # -----------------------------------------------------------------

    @property
    def ssfr_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_ssfr_origins(flatten=True)

    # -----------------------------------------------------------------

    @property
    def tir_methods(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_tir_methods(flatten=True)

    # -----------------------------------------------------------------

    @property
    def tir_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_tir_origins(flatten=True)

    # -----------------------------------------------------------------

    @property
    def attenuation_methods(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_attenuation_methods(flatten=True)

    # -----------------------------------------------------------------

    @property
    def attenuation_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_attenuation_origins(flatten=True)

    # -----------------------------------------------------------------

    @property
    def old_methods(self):

        """
        This function ...
        :param self:
        :return:
        """

        return self.observation_maps_collection.get_old_methods(flatten=False)

    # -----------------------------------------------------------------

    @property
    def old_map_methods(self):

        """
        This function ...
        :return:
        """

        #return self.old_methods[self.model_old_map_name] # for flattened
        #return find_value_for_unique_key_nested(self.old_methods, self.model_old_map_name)
        return self.old_methods["disk"][self.model_old_map_name]

    # -----------------------------------------------------------------

    @property
    def old_origins(self):

        """
        Thisfunction ...
        :return:
        """

        return self.observation_maps_collection.get_old_origins(flatten=False)

    # -----------------------------------------------------------------

    @property
    def old_map_origins(self):

        """
        This function ...
        :return:
        """

        #return self.old_origins[self.model_old_map_name] # for flattened
        #return find_value_for_unique_key_nested(self.old_origins, self.model_old_map_name)
        return self.old_origins["disk"][self.model_old_map_name]

    # -----------------------------------------------------------------

    @property
    def old_map_method_and_name(self):

        """
        This function ...
        :return:
        """

        return "disk", self.model_old_map_name

    # -----------------------------------------------------------------

    @property
    def young_methods(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_young_methods(flatten=False)

    # -----------------------------------------------------------------

    @property
    def young_map_methods(self):

        """
        This function ...
        :return:
        """

        #return self.young_methods[self.model_young_map_name]
        return find_value_for_unique_key_nested(self.young_methods, self.model_young_map_name)

    # -----------------------------------------------------------------

    @property
    def young_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_young_origins(flatten=False)

    # -----------------------------------------------------------------

    @property
    def young_map_origins(self):

        """
        This function ...
        :return:
        """

        #return self.young_origins[self.model_young_map_name]
        return find_value_for_unique_key_nested(self.young_origins, self.model_young_map_name)

    # -----------------------------------------------------------------

    @property
    def young_map_method_and_name(self):

        """
        This function ...
        :return:
        """

        keys = find_keys_for_unique_key_nested(self.young_methods, self.model_young_map_name)
        if len(keys) == 1:
            method = None
            map_name = keys[0]
        elif len(keys) == 2:
            method = keys[0]
            map_name = keys[1]
        else: raise ValueError("Something is wrong")
        return method, map_name

    # -----------------------------------------------------------------

    @property
    def ionizing_methods(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_ionizing_methods(flatten=False)

    # -----------------------------------------------------------------

    @property
    def ionizing_map_methods(self):

        """
        This function ...
        :return:
        """

        #return self.ionizing_methods[self.model_ionizing_map_name]
        return find_value_for_unique_key_nested(self.ionizing_methods, self.model_ionizing_map_name)

    # -----------------------------------------------------------------

    @property
    def ionizing_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_ionizing_origins(flatten=False)

    # -----------------------------------------------------------------

    @property
    def ionizing_map_origins(self):

        """
        This function ...
        :return:
        """

        #return self.ionizing_origins[self.model_ionizing_map_name]
        return find_value_for_unique_key_nested(self.ionizing_origins, self.model_ionizing_map_name)

    # -----------------------------------------------------------------

    @property
    def ionizing_map_method_and_name(self):

        """
        This function ...
        :return:
        """

        keys = find_keys_for_unique_key_nested(self.ionizing_methods, self.model_ionizing_map_name)
        if len(keys) == 1:
            method = None
            map_name = keys[0]
        elif len(keys) == 2:
            method = keys[0]
            map_name = keys[1]
        else: raise ValueError("Something is wrong")
        return method, map_name

    # -----------------------------------------------------------------

    @property
    def dust_methods(self):

        """
        Thisf unction ...
        :return:
        """

        return self.observation_maps_collection.get_dust_methods(flatten=False)

    # -----------------------------------------------------------------

    @property
    def dust_map_methods(self):

        """
        This function ...
        :return:
        """

        #return self.dust_methods[self.model_dust_map_name]
        try: return find_value_for_unique_key_nested(self.dust_methods, self.model_dust_map_name)
        except ValueError: return find_value_for_unique_key_nested(self.dust_methods, self.model_dust_map_name.split("_", 1)[1])

    # -----------------------------------------------------------------

    @property
    def dust_origins(self):

        """
        This function ...
        :return:
        """

        return self.observation_maps_collection.get_dust_origins(flatten=False)

    # -----------------------------------------------------------------

    @property
    def dust_map_origins(self):

        """
        This function ...
        :return:
        """

        #return self.dust_origins[self.model_dust_map_name]
        try: return find_value_for_unique_key_nested(self.dust_origins, self.model_dust_map_name)
        except ValueError: return find_value_for_unique_key_nested(self.dust_origins, self.model_dust_map_name.split("_", 1)[1])

    # -----------------------------------------------------------------

    @property
    def dust_map_method_and_name(self):

        """
        This function ...
        :return:
        """

        try: keys = find_keys_for_unique_key_nested(self.dust_methods, self.model_dust_map_name)
        except ValueError: keys = find_keys_for_unique_key_nested(self.dust_methods, self.model_dust_map_name.split("_", 1)[1])

        if len(keys) == 1:
            method = None
            map_name = keys[0]
        elif len(keys) == 2:
            method = keys[0]
            map_name = keys[1]
        else: raise ValueError("Something is wrong")
        return method, map_name

# -----------------------------------------------------------------

class AnalysisRuns(object):

    """
    This function ...
    """

    def __init__(self, modeling_path):

        """
        This function ...
        :param modeling_path:
        """

        self.modeling_path = modeling_path

    # -----------------------------------------------------------------

    @property
    def analysis_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.modeling_path, "analysis")

    # -----------------------------------------------------------------

    @lazyproperty
    def names(self):

        """
        This function ...
        :return:
        """

        return fs.directories_in_path(self.analysis_path, returns="name")

    # -----------------------------------------------------------------

    @lazyproperty
    def paths(self):

        """
        This function ...
        :return:
        """

        return fs.directories_in_path(self.analysis_path, returns="path")

    # -----------------------------------------------------------------

    def __len__(self):

        """
        This function ...
        :return:
        """

        return len(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def empty(self):

        """
        This function ...
        :return:
        """

        return sequences.is_empty(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def has_single(self):

        """
        This function ...
        :return:
        """

        return sequences.is_singleton(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def single_name(self):

        """
        This function ...
        :return:
        """

        return sequences.get_singleton(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def single_path(self):

        """
        This function ...
        :return:
        """

        return self.get_path(self.single_name)

    # -----------------------------------------------------------------

    def get_path(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return fs.join(self.analysis_path, name)

    # -----------------------------------------------------------------

    def load(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        analysis_run_path = self.get_path(name)
        if not fs.is_directory(analysis_run_path): raise ValueError("Analysis run '" + name + "' does not exist")
        return AnalysisRun.from_path(analysis_run_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def single(self):

        """
        This function ...
        :return:
        """

        return AnalysisRun.from_path(self.single_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def last_name(self):

        """
        This function ...
        :return:
        """

        #if self.empty: return None
        #if self.has_single: return self.single_name
        #return sorted(self.names)[-1]

        return fs.name(self.last_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def last_path(self):

        """
        This function ...
        :return:
        """

        #return self.get_path(self.last_name)

        return fs.last_created_path(*self.paths)

    # -----------------------------------------------------------------

    @lazyproperty
    def last(self):

        """
        This function ...
        :return:
        """

        return self.load(self.last_name)

# -----------------------------------------------------------------

class CachedAnalysisRun(AnalysisRunBase):

    """
    This class ...
    """

    def __init__(self, run_path, remote):

        """
        The constructor ...
        :param run_path:
        :param remote:
        """

        # Set attributes
        self.path = run_path
        self.remote = remote

    # -----------------------------------------------------------------

    @property
    def galaxy_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.original_modeling_path)

    # -----------------------------------------------------------------

    @classmethod
    def from_path(cls, path, remote):

        """
        This function ...
        :param path:
        :param remote:
        :return:
        """

        return cls(path, remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def info(self):

        """
        This function ...
        :return:
        """

        return AnalysisRunInfo.from_remote_file(self.info_path, self.remote)

    # -----------------------------------------------------------------

    @property
    def original_path(self):

        """
        This function ...
        :return:
        """

        return self.info.path

    # -----------------------------------------------------------------

    @property
    def original_analysis_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.original_path)

    # -----------------------------------------------------------------

    @property
    def original_modeling_path(self):

        """
        This function ...
        :return:
        """

        return fs.directory_of(self.original_analysis_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def config(self):

        """
        This function ...
        :return:
        """

        return Configuration.from_remote_file(self.config_path, self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def heating_config(self):

        """
        This function ...
        :return:
        """

        return Configuration.from_remote_file(self.heating_config_path, self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_grid(self):

        """
        This function ...
        :return:
        """

        return WavelengthGrid.from_skirt_input(self.wavelength_grid_path, remote=self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def wavelength_grid_heating(self):

        """
        Thisj function ...
        :return:
        """

        return WavelengthGrid.from_skirt_input(self.heating_wavelength_grid_path, remote=self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid(self):

        """
        This function ...
        :return:
        """

        return load_grid(self.dust_grid_path, remote=self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def nfiles(self):

        """
        This function ...
        :return:
        """

        return self.remote.nfiles_in_path(self.path, recursive=True)

    # -----------------------------------------------------------------

    @lazyproperty
    def disk_space(self):

        """
        This function ...
        :return:
        """

        return self.remote.directory_size(self.path)

    # -----------------------------------------------------------------

    @property
    def has_output(self):

        """
        Thisn function ...
        :return:
        """

        return self.remote.has_files_in_path(self.output_path)

    # -----------------------------------------------------------------

    @property
    def has_logfile(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_file(self.logfile_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def logfile(self):

        """
        This function ...
        :return:
        """

        return LogFile.from_remote_file(self.logfile_path, self.remote)

    # -----------------------------------------------------------------

    @property
    def has_misc(self):

        """
        Thisn function ...
        :return:
        """

        return self.remote.has_files_in_path(self.misc_path)

    # -----------------------------------------------------------------

    @property
    def has_extracted(self):

        """
        Thisn function ...
        :return:
        """

        return self.remote.has_files_in_path(self.extr_path)

    # -----------------------------------------------------------------

    @property
    def has_progress(self):

        """
        Thisnfunction ...
        :return:
        """

        return self.remote.is_file(self.progress_path)

    # -----------------------------------------------------------------

    @property
    def has_timeline(self):

        """
        Thisfunction ...
        :return:
        """

        return self.remote.is_file(self.timeline_path)

    # -----------------------------------------------------------------

    @property
    def has_memory(self):

        """
        Thisfunction ...
        :return:
        """

        return self.remote.is_file(self.memory_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def progress(self):

        """
        This function ...
        :return:
        """

        return ProgressTable.from_remote_file(self.progress_path, remote=self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def timeline(self):

        """
        This function ...
        :return:
        """

        return TimeLineTable.from_remote_file(self.timeline_path, remote=self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def memory(self):

        """
        This function ...
        :return:
        """

        return MemoryUsageTable.from_remote_file(self.memory_path, remote=self.remote)

    # -----------------------------------------------------------------

    @property
    def has_plots(self):

        """
        Thisf unction ...
        :return:
        """

        return self.remote.has_files_in_path(self.plot_path)

    # -----------------------------------------------------------------

    @property
    def has_attenuation(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_directory(self.attenuation_path) and not self.remote.is_empty(self.attenuation_path)

    # -----------------------------------------------------------------

    @property
    def has_colours(self):

        """
        This functino ...
        :return:
        """

        return self.remote.is_directory(self.colours_path) and not self.remote.is_empty(self.colours_path)

    # -----------------------------------------------------------------

    @property
    def colour_names(self):

        """
        This function ...
        :return:
        """

        return self.remote.files_in_path(self.colours_simulated_path, extension="fits", returns="name")

    # -----------------------------------------------------------------

    @property
    def has_residuals(self):

        """
        Thisf unction ...
        :return:
        """

        return self.remote.is_directory(self.residuals_path) and not self.remote.is_empty(self.residuals_path)

    # -----------------------------------------------------------------

    @property
    def residual_image_names(self):

        """
        This function ...
        :return:
        """

        return self.remote.files_in_path(self.residuals_path, extension="fits", not_contains=["significance"], returns="name")

    # -----------------------------------------------------------------

    @property
    def has_maps_attenuation(self):

        """
        Thisn function ...
        :return:
        """

        return self.remote.is_directory(self.attenuation_maps_path) and not self.remote.is_empty(self.attenuation_maps_path)

    # -----------------------------------------------------------------

    @property
    def nattenuation_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.attenuation_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.attenuation_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.attenuation_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_colours(self):

        """
        Thisnfunction ...
        :return:
        """

        return self.remote.is_directory(self.colour_maps_path) and not self.remote.is_empty(self.colour_maps_path)

    # -----------------------------------------------------------------

    @property
    def ncolour_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.colour_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.colour_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.colour_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_dust(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_directory(self.dust_maps_path) and not self.remote.is_empty(self.dust_maps_path)

    # -----------------------------------------------------------------

    @property
    def ndust_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.dust_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.dust_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.dust_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_ionizing(self):

        """
        Thisfunction ...
        :return:
        """

        return self.remote.is_directory(self.ionizing_maps_path) and not self.remote.is_empty(self.ionizing_maps_path)

    # -----------------------------------------------------------------

    @property
    def nionizing_maps(self):

        """
        Thisj function ...
        :return:
        """

        if self.remote.has_files_in_path(self.ionizing_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.ionizing_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.ionizing_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_old(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_directory(self.old_maps_path) and not self.remote.is_empty(self.old_maps_path)

    # -----------------------------------------------------------------

    @property
    def nold_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.old_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.old_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.old_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_ssfr(self):

        """
        Thisjfunction ...
        :return:
        """

        return self.remote.is_directory(self.ssfr_maps_path) and not self.remote.is_empty(self.ssfr_maps_path)

    # -----------------------------------------------------------------

    @property
    def nssfr_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.ssfr_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.ssfr_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.ssfr_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_tir(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_directory(self.tir_maps_path) and not self.remote.is_empty(self.tir_maps_path)

    # -----------------------------------------------------------------

    @property
    def ntir_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.tir_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.tir_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.tir_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_maps_young(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_directory(self.young_maps_path) and not self.remote.is_empty(self.young_maps_path)

    # -----------------------------------------------------------------

    @property
    def nyoung_maps(self):

        """
        This function ...
        :return:
        """

        if self.remote.has_files_in_path(self.young_maps_path, extension="fits"): return self.remote.nfiles_in_path(self.young_maps_path, extension="fits")
        else: return self.remote.nfiles_in_path(self.young_maps_path, extension="fits", recursive=True, recursion_level=1)

    # -----------------------------------------------------------------

    @property
    def has_heating(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_file(self.heating_config_path)

    # -----------------------------------------------------------------

    @property
    def ski_file(self):

        """
        This function ...
        :return:
        """

        return LabeledSkiFile.from_remote_file(self.ski_file_path, self.remote)

    # -----------------------------------------------------------------

    @property
    def has_dust_grid_simulation_logfile(self):

        """
        Thisf unction ...
        :return:
        """

        return self.remote.is_file(self.dust_grid_simulation_logfile_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid_simulation_logfile(self):

        """
        This function ...
        :return:
        """

        return LogFile.from_remote_file(self.dust_grid_simulation_logfile_path, self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def dust_grid_tree(self):

        """
        This function ...
        :return:
        """

        # Give debug message
        log.debug("Loading the dust grid tree, this may take a while (depending on the number of nodes) ...")

        # Return the tree
        return DustGridTree.from_remote_file(self.dust_grid_tree_path, self.remote)

    # -----------------------------------------------------------------

    @property
    def remote_script_paths(self):

        """
        This function ...
        :return:
        """

        return self.remote.files_in_path(self.path, extension="sh")

    # -----------------------------------------------------------------

    def get_remote_script_commands(self):

        """
        This fucntion ...
        :return:
        """

        commands = dict()

        # Loop over the script paths
        for path in self.remote_script_paths:

            # Get host ID
            host_id = fs.strip_extension(fs.name(path))

            lines = []

            # Open the file
            for line in self.remote.read_lines(path):

                if line.startswith("#"): continue
                if not line.strip(): continue

                lines.append(line)

            # Set the commands
            commands[host_id] = lines

        # Return the commands
        return commands

    # -----------------------------------------------------------------

    def get_remote_script_commands_for_host(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        commands = self.get_remote_script_commands()
        if host_id in commands: return commands[host_id]
        else: return []

    # -----------------------------------------------------------------

    def get_heating_ski_for_contribution(self, contribution):

        """
        This function ...
        :param contribution:
        :return:
        """

        path = self.heating_ski_path_for_contribution(contribution)
        return SkiFile.from_remote_file(path, self.remote)

    # -----------------------------------------------------------------

    @property
    def has_simulated_sed(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_file(self.simulated_sed_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_sed(self):

        """
        This function ...
        :return:
        """

        return SED.from_skirt(self.simulated_sed_path, remote=self.remote)

    # -----------------------------------------------------------------

    @property
    def has_simulated_fluxes(self):

        """
        This function ...
        :return:
        """

        return self.remote.is_file(self.simulated_fluxes_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def simulated_fluxes(self):

        """
        This function ...
        :return:
        """

        return ObservedSED.from_remote_file(self.simulated_fluxes_path, self.remote)

# -----------------------------------------------------------------

class CachedAnalysisRuns(AnalysisRunBase):

    """
    This class ...
    """

    def __init__(self, modeling_path, remote):

        """
        This function ...
        :param modeling_path:
        :param remote:
        """

        # Set attributes
        self.modeling_path = modeling_path
        self.remote = load_remote(remote, silent=True)

    # -----------------------------------------------------------------

    @property
    def galaxy_name(self):

        """
        This function ...
        :return:
        """

        return fs.name(self.modeling_path)

    # -----------------------------------------------------------------

    @lazyproperty
    def cache_directory_name(self):

        """
        Thisf unction ...
        :return:
        """

        return self.galaxy_name + "_analysis"

    # -----------------------------------------------------------------

    @lazyproperty
    def cache_directory_path(self):

        """
        This function ...
        :return:
        """

        path = fs.join(self.remote.home_directory, self.cache_directory_name)
        if not self.remote.is_directory(path): self.remote.create_directory(path)
        return path

    # -----------------------------------------------------------------

    def get_cache_directory_path_run(self, run_name):

        """
        This function ...
        :param run_name:
        :return:
        """

        path = fs.join(self.cache_directory_path, run_name)
        #if not self.remote.is_directory(path): self.remote.create_directory(path)
        return path

    # -----------------------------------------------------------------

    @lazyproperty
    def names(self):

        """
        This function ...
        :return:
        """

        return self.remote.directories_in_path(self.cache_directory_path, returns="name")

    # -----------------------------------------------------------------

    def __len__(self):

        """
        This function ...
        :return:
        """

        return len(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def empty(self):

        """
        This function ...
        :return:
        """

        return sequences.is_empty(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def has_single(self):

        """
        This function ...
        :return:
        """

        return sequences.is_singleton(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def single_name(self):

        """
        This function ...
        :return:
        """

        return sequences.get_singleton(self.names)

    # -----------------------------------------------------------------

    @lazyproperty
    def single_path(self):

        """
        This function ...
        :return:
        """

        return self.get_path(self.single_name)

    # -----------------------------------------------------------------

    def get_path(self, name):

        """
        Thisn function ...
        :param name:
        :return:
        """

        return self.get_cache_directory_path_run(name)

    # -----------------------------------------------------------------

    def load(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        analysis_run_path = self.get_path(name)
        if not self.remote.is_directory(analysis_run_path): raise ValueError("Analysis run '" + name + "' does not exist")
        return CachedAnalysisRun.from_path(analysis_run_path, self.remote)

    # -----------------------------------------------------------------

    @lazyproperty
    def single(self):

        """
        This function ...
        :return:
        """

        return CachedAnalysisRun.from_path(self.single_path, self.remote)

# -----------------------------------------------------------------

def find_value_for_unique_key_nested(dictionary, key, allow_none=False):

    """
    This function ...
    :param dictionary:
    :param key:
    :param allow_none:
    :return:
    """

    values = []

    for key_i in dictionary:

        # Sub-dict
        if isinstance(dictionary[key_i], dict):
            value = find_value_for_unique_key_nested(dictionary[key_i], key, allow_none=True)
            if value is not None: values.append(value)

        # Matches
        elif key_i == key:
            value = dictionary[key_i]
            values.append(value)

    if len(values) == 0 and not allow_none: raise ValueError("Key not found")
    if len(values) > 1: raise ValueError("Not unique")

    # Return the only value
    if len(values) == 0: return None
    else: return values[0]

# -----------------------------------------------------------------

def find_keys_for_unique_key_nested(dictionary, key, allow_none=False):

    """
    This function ...
    :param dictionary:
    :param key:
    :param allow_none:
    :return:
    """

    keys = []

    for key_i in dictionary:

        # Sub-dict
        if isinstance(dictionary[key_i], dict):

            keys_subdict = find_keys_for_unique_key_nested(dictionary[key_i], key, allow_none=True)
            if keys_subdict is not None:
                keys.append([key_i] + keys_subdict)

        # Matches
        elif key_i == key: keys.append([key])

    if len(keys) == 0 and not allow_none: raise ValueError("Key not found")
    if len(keys) > 1: raise ValueError("Not unique")

    if len(keys) == 0: return None
    else: return keys[0]

# -----------------------------------------------------------------
