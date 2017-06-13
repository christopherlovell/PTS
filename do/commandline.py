#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.commandline

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
from operator import itemgetter
import time as _time

# Import the relevant PTS classes and modules
from pts.core.tools import introspection
from pts.core.tools import filesystem as fs
from pts.core.tools import formatting as fmt
from pts.core.tools import time
from pts.core.tools.logging import setup_log

# -----------------------------------------------------------------

def initialize_log(config, remote=None):

    """
    This function ...
    :parma remote:
    :return: 
    """

    # Determine the log level
    level = "INFO"
    if config.debug: level = "DEBUG"
    if config.brief: level = "SUCCESS"

    # Determine log path
    #if args.remote is None: logfile_path = fs.join(config.log_path, time.unique_name("log") + ".txt") if config.report else None
    #else: logfile_path = None

    # Determine the log file path
    if remote is None: logfile_path = fs.join(config.log_path, time.unique_name("log") + ".txt") if config.report else None
    else: logfile_path = None

    # Initialize the logger
    log = setup_log(level=level, path=logfile_path)

    # Return the logger
    return log

# -----------------------------------------------------------------

class Command(object):

    """
    This class ...
    """

    def __init__(self, command, description, settings, input_dict, cwd=None, finish=None):

        """
        This function ...
        :param command:
        :param settings:
        :param input_dict:
        :param cwd:
        :param finish:
        """

        # Set working directory
        if cwd is None:
            self.cwd_specified = False
            cwd = fs.cwd()
        else: self.cwd_specified = True

        # Set attributes
        self.command = command
        self.description = description
        self.settings = settings
        self.input_dict = input_dict
        self.cwd = cwd
        self.finish = finish

# -----------------------------------------------------------------

def start_and_clear(command_name, target, **kwargs):

    """
    This function ...
    :param command_name: 
    :param target: 
    :param kwargs: 
    :return: 
    """

    # Start
    start_target(command_name, target, **kwargs)

    # Remove temp
    print("Clearing temporary data ...")
    introspection.remove_temp_dirs()

# -----------------------------------------------------------------

def start_target(command_name, target, **kwargs):

    """
    This function ...
    :return:
    """

    # Record starting time
    start = _time.time()

    # Run
    target(**kwargs)

    # Record end time
    end = _time.time()
    seconds = end - start

    # Succesfully finished
    print("Finished " + command_name + " in " + str(seconds) + " seconds")

# -----------------------------------------------------------------

def show_all_available(scripts, tables=None):

    """
    This function ...
    :param scripts:
    :param tables:
    :return:
    """

    # The list that will contain the info about all the scripts / table commands
    info = []

    ## Combine scripts and tables

    # Scripts
    for script in scripts:

        subproject = script[0]
        command = script[1]

        # Determine the path to the script
        path = fs.join(introspection.pts_package_dir, "do", subproject, command)

        # Get the description
        description = get_description(path, subproject, command[:-3])

        # Add entry to the info
        title = None
        info.append((subproject, command[:-3], description, "arguments", title))

    # Tables
    for subproject in tables:

        table = tables[subproject]

        # Loop over the entries
        for i in range(len(table["Command"])):

            command = table["Command"][i]
            hidden = False
            if command.startswith("*"):
                hidden = True
                command = command[1:]
            if hidden: continue # skip hidden
            description = table["Description"][i]
            configuration_method = table["Configuration method"][i]
            title = table["Title"][i]
            info.append((subproject, command, description, configuration_method, title))

    # Sort on the 'do' subfolder name
    info = sorted(info, key=itemgetter(0))

    lengths = dict()
    lengths_config_methods = dict()
    for script in info:

        subproject = script[0]
        command = script[1]
        if subproject not in lengths or len(command) > lengths[subproject]: lengths[subproject] = len(command)

        config_method = script[3] if len(script) == 4 else ""
        if subproject not in lengths_config_methods or len(config_method) > lengths_config_methods[subproject]:
            lengths_config_methods[subproject] = len(config_method)

    # Print in columns
    with fmt.print_in_columns(5) as print_row:

        previous_subproject = None
        previous_title = None

        current_dir = None
        for script in info:

            configuration_method = script[3]
            description = script[2]

            # Get the title
            title = script[4]

            # Transform title
            if title is None: title = ""

            coloured_subproject = fmt.green + script[0] + fmt.reset
            coloured_name = fmt.bold + fmt.underlined + fmt.red + script[1] + fmt.reset
            #coloured_config_method = fmt.yellow + pre_config_infix + configuration_method + after_config_infix + fmt.reset
            coloured_config_method = fmt.yellow + "[" + configuration_method + "]" + fmt.reset

            coloured_title = fmt.blue + fmt.bold + title + fmt.reset

            if previous_subproject is None or previous_subproject != script[0]:

                previous_subproject = script[0]
                print_row(coloured_subproject, "/")

            if previous_title is None or previous_title != title:

                previous_title = title

                if title != "":
                    print_row()
                    print_row("", "", coloured_title)

            # Print command
            print_row("", "/", coloured_name, coloured_config_method, description)

# -----------------------------------------------------------------

def show_possible_matches(matches, table_matches=None, tables=None):

    """
    This function ...
    :param matches:
    :param table_matches:
    :param tables:
    :return:
    """

    # The list that will contain the info about all the scripts / table commands
    info = []

    ## Combine script and table matches

    # Scripts
    for script in matches:

        subproject = script[0]
        command = script[1]

        # Determine the path to the script
        path = fs.join(introspection.pts_package_dir, "do", subproject, command)

        # Get the description
        description = get_description(path, subproject, command[:-3])

        # Add entry to the info
        info.append((subproject, command[:-3], description, "arguments"))

    # Tables
    for subproject, index in table_matches:

        command = tables[subproject]["Command"][index]
        hidden = False
        if command.startswith("*"):
            hidden = True
            command = command[1:]
        if hidden: continue # skip if hidden
        description = tables[subproject]["Description"][index]
        configuration_method = tables[subproject]["Configuration method"][index]
        info.append((subproject, command, description, configuration_method))

    # Sort on the 'do' subfolder name
    info = sorted(info, key=itemgetter(0))

    lengths = dict()
    lengths_config_methods = dict()
    for script in info:
        subproject = script[0]
        command = script[1]
        if subproject not in lengths or len(command) > lengths[subproject]: lengths[subproject] = len(command)

        config_method = script[3] if len(script) == 4 else ""
        if subproject not in lengths_config_methods or len(config_method) > lengths_config_methods[subproject]:
            lengths_config_methods[subproject] = len(config_method)

    current_dir = None
    for script in info:

        from_table = len(script) == 4

        configuration_method = script[3] if from_table else ""
        description = script[2] if from_table else ""

        nspaces = lengths[script[0]] - len(script[1]) + 3
        pre_config_infix = " " * nspaces + "[" if from_table else ""
        after_config_infix = "]   " + " " * (lengths_config_methods[script[0]] - len(configuration_method)) if from_table else ""

        coloured_subproject = fmt.green + script[0] + fmt.reset
        coloured_name = fmt.bold + fmt.underlined + fmt.red + script[1] + fmt.reset
        coloured_config_method = fmt.yellow + pre_config_infix + configuration_method + after_config_infix + fmt.reset

        if current_dir == script[0]:
            print(" " * len(current_dir) + "/" + coloured_name + coloured_config_method + description)
        else:
            print(coloured_subproject + "/" + coloured_name + coloured_config_method + description)
            current_dir = script[0]

# -----------------------------------------------------------------

def get_description(script_path, subproject, command):

    """
    This function ...
    :param script_path:
    :param subproject:
    :param command:
    :return:
    """

    description = ""

    with open(script_path, 'r') as script:

        for line in script:

            line = line.rstrip("\n")

            if "## \package" in line:

                splitted = line.split(subproject + "." + command + " ")

                if len(splitted) > 1: description = splitted[1]
                break

    # Return description
    return description

# -----------------------------------------------------------------
