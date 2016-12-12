#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.prep.installation Contains the SKIRTInstaller and PTSInstaller classes.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import requests
import subprocess
from abc import ABCMeta, abstractmethod

# Import the relevant PTS classes and modules
from ..basics.configurable import Configurable
from ..simulation.execute import SkirtExec
from ..remote.remote import Remote
from ..tools import introspection
from ..tools import filesystem as fs
from ..tools.logging import log
from ..tools import google
from ..tools import network
from ..tools import archive

# -----------------------------------------------------------------

# For SSH key:
# eval $(ssh-agent)
# ssh-add

# -----------------------------------------------------------------

skirt_directories = ["git", "run", "doc", "release", "debug"]
pts_directories = ["pts", "run", "doc", "temp", "remotes", "user", "ext"]

# -----------------------------------------------------------------

class Installer(Configurable):

    """
    This class ...
    """

    __metaclass__ = ABCMeta

    # -----------------------------------------------------------------

    def __init__(self, config=None):

        """
        This function ...
        """

        # Call the constructor of the base class
        super(Installer, self).__init__(config)

        # The remote execution environment
        self.remote = None

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        """

        # 1. Call the setup function
        self.setup()

        # 2. Create the necessary directories
        self.create_directories()

        # 2. Install
        self.install()

        # 3. Test the installation
        self.test()

    # -----------------------------------------------------------------

    def setup(self):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(Installer, self).setup()

        # Setup the remote execution environment if necessary
        if self.config.remote is not None:

            # Create and setup the remote execution environment
            self.remote = Remote()
            self.remote.setup(self.config.remote)

    # -----------------------------------------------------------------

    def create_directories(self):

        """
        THis function ...
        :return:
        """

        # Install locally or remotely
        if self.remote is None: self.create_directories_local()
        else: self.create_directories_remote()

    # -----------------------------------------------------------------

    def install(self):

        """
        This function ...
        :return:
        """

        # Install locally or remotely
        if self.remote is None: self.install_local()
        else: self.install_remote()

    # -----------------------------------------------------------------

    def test(self):

        """
        This function ...
        :return:
        """

        # Test locally or remotely
        if self.remote is None: self.test_local()
        else: self.test_remote()

    # -----------------------------------------------------------------

    @abstractmethod
    def create_directories_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def create_directories_remote(self):

        """
        This fucntion ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def install_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def install_remote(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def test_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @abstractmethod
    def test_remote(self):

        """
        This function ...
        :return:
        """

        pass

# -----------------------------------------------------------------

# Determine Qt configure options
qt_configure_options = []
qt_configure_options.append("-prefix '$HOME/Qt/Desktop/5.2.1'")
qt_configure_options.append("-opensource")
qt_configure_options.append("-confirm-license")
qt_configure_options.append("-c++11")
qt_configure_options.append("-no-javascript-jit")
qt_configure_options.append("-no-qml-debug")
qt_configure_options.append("-no-gif")
qt_configure_options.append("-no-libpng")
qt_configure_options.append("-no-libjpeg")
qt_configure_options.append("-no-freetype")
qt_configure_options.append("-no-harfbuzz")
qt_configure_options.append("-no-openssl")
qt_configure_options.append("-no-xinput2")
qt_configure_options.append("-no-xcb-xlib")
qt_configure_options.append("-no-glib")
qt_configure_options.append("-no-gui")
qt_configure_options.append("-no-widgets")
qt_configure_options.append("-no-nis")
qt_configure_options.append("-no-cups")
qt_configure_options.append("-no-fontconfig")
qt_configure_options.append("-no-dbus")
qt_configure_options.append("-no-xcb")
qt_configure_options.append("-no-eglfs")
qt_configure_options.append("-no-directfb")
qt_configure_options.append("-no-linuxfb")
qt_configure_options.append("-no-kms")
qt_configure_options.append("-no-opengl")
qt_configure_options.append("-nomake tools")
qt_configure_options.append("-nomake examples")

# -----------------------------------------------------------------

class SKIRTInstaller(Installer):

    """
    This class ...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        """

        # Call the constructor of the base class
        super(SKIRTInstaller, self).__init__(config)

        # The paths to the C++ compiler and MPI compiler
        self.compiler_path = None
        self.mpi_compiler_path = None

        # The path to the qmake executable corresponding to the most recent Qt installation
        self.qmake_path = None

        # Path to SKIRT root directory
        self.skirt_root_path = None

        # Path to SKIRT/git
        self.skirt_repo_path = None

        # Path to SKIRT/release
        self.skirt_release_path = None

        # Path to the SKIRT executable
        self.skirt_path = None

    # -----------------------------------------------------------------

    def create_directories_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def create_directories_remote(self):

        """
        This function ...
        :return:
        """

        # Set root path and pacakge path
        self.skirt_root_path = fs.join(self.remote.home_directory, "SKIRT")
        self.skirt_repo_path = fs.join(self.skirt_root_path, "git")
        self.skirt_release_path = fs.join(self.skirt_root_path, "release")

        # Check if already present
        if self.remote.is_directory(self.skirt_root_path):
            if self.config.force: self.remote.remove_directory(self.skirt_root_path)
            else: raise RuntimeError("SKIRT is already installed (or partly present) on the remote host")

        # Make the root directory
        self.remote.create_directory(self.skirt_root_path)

        # Create the other directories
        for name in skirt_directories:

            # Determine path
            path = fs.join(self.skirt_root_path, name)

            # Create the directory
            self.remote.create_directory(path)

    # -----------------------------------------------------------------

    def install_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing SKIRT locally ...")

        # Check compilers (C++ and mpi)
        self.check_compilers_local()

        # Check if Qt is installed
        self.check_qt_local()

        # Install Qt
        self.install_qt_local()

        # Get the SKIRT code
        self.get_skirt_local()

        # Build SKIRT
        self.build_skirt_local()

    # -----------------------------------------------------------------

    def check_compilers_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def check_qt_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def install_qt_local(self):

        """
        This function ...
        :return:
        """

        # Translated from ./makeSKIRT.sh

        # Get a list of qmake paths installed on this system
        qmake_paths = []

        for qt_dir in fs.directories_in_path(fs.home(), startswith="Qt"):
            qmake_paths = fs.files_in_path(qt_dir, recursive=True, exact_name="qmake", extension="")

        for qt_dir in fs.directories_in_path("/usr/local", startswith="Qt"):
            qmake_paths += fs.files_in_path(qt_dir, recursive=True, exact_name="qmake", extension="")

        qmake_path = introspection.qmake_path()
        qmake_paths += [qmake_path] if qmake_path is not None else []

        # Get the most recent installation

        # Check whether the Qt version is supported
        # if [[ $VERSION > '5.2.0' ]]

    # -----------------------------------------------------------------

    def get_skirt_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def build_skirt_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    @property
    def has_qt(self):

        """
        This function ...
        :return:
        """

        return self.qmake_path is not None

    # -----------------------------------------------------------------

    def install_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing SKIRT remotely ...")

        # Check the compilers (C++ and MPI)
        self.check_compilers_remote()

        # Check Qt installation
        self.check_qt_remote()

        # Install Qt if necessary
        if not self.has_qt: self.install_qt_remote()

        # Get the SKIRT code
        self.get_skirt_remote()

        # Build SKIRT
        self.build_skirt_remote()

    # -----------------------------------------------------------------

    def check_compilers_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Checking the presence of C++ and MPI compilers ...")

        # Get the compiler paths
        self.compiler_path = self.remote.find_and_load_cpp_compiler()
        self.mpi_compiler_path = self.remote.find_and_load_mpi_compiler()

    # -----------------------------------------------------------------

    def check_qt_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Checking for Qt installation on remote ...")

        # Load Qt module, find the qmake path
        self.qmake_path = self.remote.find_and_load_qmake()

    # -----------------------------------------------------------------

    def install_qt_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing Qt ...")

        #link = "http://download.qt.io/official_releases/qt/5.5/5.5.1/single/qt-everywhere-opensource-src-5.5.1.tar.gz"

        # Qt URL
        url = "http://download.qt.io/official_releases/qt/5.7/5.7.0/single/qt-everywhere-opensource-src-5.7.0.tar.gz"

        # Determine the path for the Qt source code
        path = fs.join(self.remote.home_directory, "qt.tar.gz")

        # Download Qt
        self.remote.download_from_url_to(url, path)

        # Determine commands
        configure_command = "./configure " + " ".join(qt_configure_options)
        make_command = "make"
        install_command = "make install"

        # Execute the commands
        self.remote.execute_lines(configure_command, make_command, install_command, show_output=True)

    # -----------------------------------------------------------------

    def get_skirt_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Getting the SKIRT source code ...")

        # Get repository link
        if self.config.repository is not None:
            url = introspection.skirt_git_remote_url(self.config.repository)
        elif self.config.private:
            url = introspection.private_skirt_https_link
        else: url = introspection.public_skirt_https_link

        # Do HPC UGent in a different way because it seems only SSH is permitted and not HTTPS (but we don't want SSH
        # because of the private/public key thingy, so use a trick
        if self.remote.host.name == "login.hpc.ugent.be": get_skirt_hpc(self.remote, url, self.skirt_root_path, self.skirt_repo_path)
        else:

            # CONVERT TO HTTPS LINK
            host = url.split("@")[1].split(":")[0]
            user_or_organization = url.split(":")[1].split("/")[0]
            repo_name = url.split("/")[-1].split(".git")[0]
            url = "https://" + host + "/" + user_or_organization + "/" + repo_name + ".git"

            # Set the clone command
            command = "git clone " + url + " " + self.skirt_repo_path

            # Find the account file for the repository host (e.g. github.ugent.be)
            username, password = introspection.get_account(host)

            # Set the command lines
            lines = []
            lines.append(command)
            lines.append(("':", username))
            lines.append(("':", password))

            # Clone the repository
            self.remote.execute_lines(*lines, show_output=True)

        # Set PYTHONPATH
        bashrc_path = fs.join(self.remote.home_directory, ".bashrc")
        lines = []
        export_command = "export PATH=" + fs.join(self.skirt_release_path, "SKIRTmain") + ":" + fs.join(self.skirt_release_path, "FitSKIRTmain") + ":$PATH"
        lines.append("")
        lines.append("# For SKIRT and FitSKIRT, added by PTS (Python Toolkit for SKIRT)")
        lines.append(export_command)
        lines.append("")
        self.remote.append_lines(bashrc_path, lines)

        # Set the path to the main SKIRT executable
        self.skirt_path = fs.join(self.skirt_release_path, "SKIRTmain", "skirt")

        # Run export path in the current shell to make SKIRT command visible
        self.remote.execute(export_command)

        # Load bashrc file
        #self.remote.execute("source " + bashrc_path)

        # Success
        log.success("SKIRT was successfully downloaded")

    # -----------------------------------------------------------------

    def build_skirt_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Building SKIRT ...")

        # Navigate to the SKIRT repo directory
        self.remote.change_cwd(self.skirt_repo_path)

        # Create command strings
        make_make_command = self.qmake_path + " BuildSKIRT.pro -o ../release/Makefile CONFIG+=release"
        nthreads = self.remote.cores_per_socket
        make_command = "make -j " + str(nthreads) + " -w -C ../release"

        # Debugging
        log.debug("Make commands:")
        log.debug(" 1) " + make_make_command)
        log.debug(" 2) " + make_command)

        # Execute the commands
        self.remote.execute(make_make_command, show_output=True)
        self.remote.execute(make_command, show_output=True)

        # Success
        log.success("SKIRT was successfully built")

    # -----------------------------------------------------------------

    def build_skirt_hpc(self):

        """
        This function ...
        :return:
        """

        local_script_path = None

        screen_name = "SKIRT installation"

        # Open the job script file
        script_file = open(local_script_path, 'w')

        # Write a general header to the batch script
        script_file.write("#!/bin/sh\n")
        script_file.write("# Batch script for running SKIRT on a remote system\n")
        script_file.write("# To execute manualy, copy this file to the remote filesystem and enter the following commmand:\n")
        script_file.write("# screen -S " + screen_name + " -L -d -m " + fs.name(local_script_path) + "'\n")
        script_file.write("\n")

        # Load modules
        script_file.write("module load lxml/3.4.2-intel-2015a-Python-2.7.9")
        script_file.write("module load Qt/5.2.1-intel-2015a")

        #
        script_file.write("./makeSKIRT.sh")

        self.remote.start_screen(name, local_script_path, script_destination, screen_output_path=None, keep_remote_script=False)

    # -----------------------------------------------------------------

    def test_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def test_remote(self):

        """
        This function ...
        :return:
        """

        pass

# -----------------------------------------------------------------

# Anaconda 4.2.0

# LINUX

# Python 3.5 version
# 64bit: https://repo.continuum.io/archive/Anaconda3-4.2.0-Linux-x86_64.sh
# 32bit: https://repo.continuum.io/archive/Anaconda3-4.2.0-Linux-x86.sh

# Python 2.7 version
# 64bit: https://repo.continuum.io/archive/Anaconda2-4.2.0-Linux-x86_64.sh
# 32bit: https://repo.continuum.io/archive/Anaconda2-4.2.0-Linux-x86.sh

anaconda_linux_url = "https://repo.continuum.io/archive/Anaconda2-4.2.0-Linux-x86_64.sh"

# MACOS

# Python 3.5 version
# https://repo.continuum.io/archive/Anaconda3-4.2.0-MacOSX-x86_64.sh

# Python 2.7 version
# https://repo.continuum.io/archive/Anaconda2-4.2.0-MacOSX-x86_64.sh

anaconda_macos_url = "https://repo.continuum.io/archive/Anaconda2-4.2.0-MacOSX-x86_64.sh"

# -----------------------------------------------------------------

# MINICONDA

# LINUX

# Python 3.5 version
# 64bit: https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
# 32bit: https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86.sh

# Python 2.7 version
# 64bit: https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh
# 32bit: https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86.sh

miniconda_linux_url = "https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh"

# MACOS

# Python 3.5 version
# https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# Python 2.7 version
# https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh

miniconda_macos_url = "https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh"

# -----------------------------------------------------------------

# Silent installation of Miniconda for Linux and OS X is a simple as specifying the -b and -p arguments of the bash installer. The following arguments are supported:

# -b, batch mode
# -p, installation prefix/path
# -f, force installation even if prefix -p already exists
# Batch mode assumes that you agree to the license agreement, and it does not edit the .bashrc or .bash_profile files.

# A complete example:

# wget http://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh
# bash ~/miniconda.sh -b -p $HOME/miniconda
# export PATH="$HOME/miniconda/bin:$PATH"

# -----------------------------------------------------------------

# These Miniconda installers contain the conda package manager and Python. Once Miniconda is installed, you can use the conda command to install any other packages and create environments, etc. For example:

# $ conda install numpy
# ...
# $ conda create -n py3k anaconda python=3

# There are two variants of the installer: Miniconda is Python 2 based and Miniconda3 is Python 3 based. Note that the choice of which Miniconda is installed only affects the root environment. Regardless of which version of Miniconda you install, you can still install both Python 2.x and Python 3.x environments.

# The other difference is that the Python 3 version of Miniconda will default to Python 3 when creating new environments and building packages. So for instance, the behavior of

# $ conda create -n myenv python
# will be to install Python 2.7 with the Python 2 Miniconda and to install Python 3.5 with the Python 3 Miniconda. You can override the default by explicitly setting python=2 or python=3. It also determines the default value of CONDA_PY when using conda build.

# We have 32-bit Mac OS X binaries available, please contact us for more details at sales@continuum.io.

# Note: If you already have Miniconda or Anaconda installed, and you just want to upgrade, you should not use the installer. Just use conda update. For instance

# $ conda update conda
# will update conda.


###

# Anaconda has all that plus over 720 open source packages that install with Anaconda or can be installed with the simple conda install command.


###

# In your browser download the Miniconda installer for Linux, then in your terminal window type the following and follow the prompts on the installer screens. If unsure about any setting, simply accept the defaults as they all can be changed later:

# bash Miniconda3-latest-Linux-x86_64.sh
# Now close and re-open your terminal window for the changes to take effect.

# To test your installation, enter the command conda list. If installed correctly, you will see a list of packages that were installed.

# -----------------------------------------------------------------

class PTSInstaller(Installer):

    """
    This function ...
    """

    def __init__(self, config=None):

        """
        This function ...
        """

        # Call the constructor of the base class
        super(PTSInstaller, self).__init__(config)

        # Path to python executable
        self.python_path = None

        # Path to PTS root directory
        self.pts_root_path = None

        # Path to PTS/pts
        self.pts_package_path = None

        self.conda_executable_path = None
        self.conda_pip_path = None
        self.conda_python_path = None

        self.pts_path = None

    # -----------------------------------------------------------------

    def create_directories_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def create_directories_remote(self):

        """
        This function ...
        :return:
        """

        # Set root path and pacakge path
        self.pts_root_path = fs.join(self.remote.home_directory, "PTS")
        self.pts_package_path = fs.join(self.pts_root_path, "pts")

        # Check if already present
        if self.remote.is_directory(self.pts_root_path):
            if self.config.force: self.remote.remove_directory(self.pts_root_path)
            else: raise RuntimeError("PTS is already installed (or partly present) on the remote host")

        # Make the root directory
        self.remote.create_directory(self.pts_root_path)

        # Create the other directories
        for name in pts_directories:

            # Determine path
            path = fs.join(self.pts_root_path, name)

            # Create the directory
            self.remote.create_directory(path)

    # -----------------------------------------------------------------

    def install_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing PTS locally ...")

        # Get a python distribution
        self.get_python_distribution_local()

        # Get PTS
        self.get_pts_local()

    # -----------------------------------------------------------------

    def get_python_distribution_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def get_pts_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def install_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing PTS remotely ...")

        # Get a python distribution
        self.get_python_distribution_remote()

        # Get PTS
        self.get_pts_remote()

        # Get PTS dependencies
        self.get_dependencies_remote()

    # -----------------------------------------------------------------

    def get_python_distribution_remote(self):

        """
        This function ...
        :return:
        """

        if self.remote.in_python_virtual_environment():

            self.python_path = self.remote.execute("which python")[0]

        else:

            if self.remote.platform == "MacOS":

                # Add conda path to .profile
                profile_path = fs.join(self.remote.home_directory, ".profile")

                # ...

            elif self.remote.platform == "Linux":

                conda_installer_path = fs.join(self.remote.home_directory, "conda.sh")

                # Download anaconda
                #self.remote.download(miniconda_linux_url, conda_installer_path)

                if not self.remote.is_file(conda_installer_path):

                    # Download the installer
                    self.remote.download_from_url_to(miniconda_linux_url, conda_installer_path)

                #conda_installer_path = fs.join(self.remote.home_directory, fs.name(miniconda_linux_url))

                # Run the installer
                #self.remote.execute("sh " + conda_installer_path, show_output=True)

                conda_installation_path = fs.join(self.remote.home_directory, "miniconda")

                if not self.remote.is_directory(conda_installation_path):

                    command = "bash " + conda_installer_path + " -b -p " + conda_installation_path
                    self.remote.execute(command, show_output=True)

                conda_bin_path = fs.join(conda_installation_path, "bin")
                self.conda_executable_path = fs.join(conda_bin_path, "conda")
                self.conda_pip_path = fs.join(conda_bin_path, "pip")
                self.conda_python_path = fs.join(conda_bin_path, "python")

                # Add conda bin path to bashrc
                bashrc_path = fs.join(self.remote.home_directory, ".bashrc")
                line = 'PATH=' + conda_bin_path + ':$PATH'
                lines = []
                lines.append("")
                lines.append("# For Miniconda, added by PTS (Python Toolkit for SKIRT)")
                lines.append(line)
                lines.append("")

                # Debugging
                log.debug("Adding the conda executables to the PATH ...")
                self.remote.append_lines(bashrc_path, lines)

                # Run commands in current shell, so that the conda commands can be found
                self.remote.execute(line)

                # Debugging
                #log.debug("Sourcing the bashrc file ...")
                #self.remote.execute("source " + bashrc_path)

    # -----------------------------------------------------------------

    def get_pts_remote(self):

        """
        This function ...
        :return:
        """

        if self.config.repository is not None:
            url = introspection.pts_git_remote_url(self.config.repository)
        elif self.config.private:
            url = introspection.private_pts_https_link
        else: url = introspection.public_pts_https_link


        # CONVERT TO HTTPS LINK
        # git@github.ugent.be:sjversto/PTS.git
        # to
        # https://github.ugent.be/SKIRT/PTS.git

        host = url.split("@")[1].split(":")[0]
        user_or_organization = url.split(":")[1].split("/")[0]
        repo_name = url.split("/")[-1].split(".git")[0]

        url = "https://" + host + "/" + user_or_organization + "/" + repo_name + ".git"

        # Set the clone command
        command = "git clone " + url + " " + self.pts_package_path

        # Find the account file for the repository host (e.g. github.ugent.be)
        username, password = introspection.get_account(host)

        # Set the command lines
        lines = []
        lines.append(command)
        lines.append(("':", username))
        lines.append(("':", password))

        # Clone the repository
        self.remote.execute_lines(*lines, show_output=True)

        # Set PYTHONPATH
        bashrc_path = fs.join(self.remote.home_directory, ".bashrc")
        lines = []
        lines.append("")
        lines.append("# For PTS, added by PTS (Python Toolkit for SKIRT)")
        lines.append("export PYTHONPATH=" + self.pts_root_path + ":$PYTHONPATH")
        lines.append('alias pts="python -m pts.do"')
        lines.append('alias ipts="python -im pts.do"')
        lines.append("")
        self.remote.append_lines(bashrc_path, lines)

        # Run commands in current shell, so that the pts command can be found
        self.remote.execute("export PYTHONPATH=" + self.pts_root_path + ":$PYTHONPATH")
        self.remote.execute('alias pts="python -m pts.do"')
        self.remote.execute('alias ipts="python -im pts.do"')

        # Load bashrc file
        # self.remote.execute("source " + bashrc_path)

        # Set the path to the main PTS executable
        self.pts_path = fs.join(self.pts_package_path, "do", "__main__.py")

    # -----------------------------------------------------------------

    def get_dependencies_remote(self):

        """
        This function ...
        :return:
        """

        # Get available conda packages
        output = self.remote.execute("conda search")
        available_packages = []
        for line in output:
            if not line.split(" ")[0]: continue
            available_packages.append(line.split(" ")[0])

        # Get already installed packages
        already_installed = []
        for line in self.remote.execute("conda list"):
            if line.startswith("#"): continue
            already_installed.append(line.split(" ")[0])

        # Use the introspection module on the remote end to get the dependencies and installed python packages
        session = self.remote.start_python_session()
        session.import_package("introspection", from_name="pts.core.tools")
        dependencies = session.get_simple_python_property("introspection", "get_all_dependencies().keys()")
        packages = session.get_simple_python_property("introspection", "installed_python_packages()")
        #self.remote.end_python_session()
        # Don't end the python session just yet

        # Get installation commands
        session.import_package("google", from_name="pts.core.tools")
        installation_commands, installed, not_installed = get_installation_commands(dependencies, packages, already_installed, available_packages, session)

        # Stop the python session
        del session

        # Install
        for module in installation_commands:

            # Debugging
            log.debug("Installing '" + module + "' ...")

            command = installation_commands[module]

            if isinstance(command, list): self.remote.execute_lines(*command, show_output=True)
            elif isinstance(command, basestring): self.remote.execute(command, show_output=True)

        # Show installed packages
        log.info("Packages that were installed:")
        for module in installed: log.info(" - " + module)

        # Show not installed packages
        log.info("Packages that could not be installed:")
        for module in not_installed: log.info(" - " + module)

        # Show already present packages
        log.info("Packages that were already present:")
        for module in already_installed: log.info(" - " + module)

    # -----------------------------------------------------------------

    def test_local(self):

        """
        This function ...
        :return:
        """

        pass

    # -----------------------------------------------------------------

    def test_remote(self):

        """
        This function ...
        :return:
        """

        pass

# -----------------------------------------------------------------

def find_real_name(module_name, available_packages, session):

    """
    This function ...
    :param module_name:
    :param available_packages:
    :param session:
    :return:
    """

    if module_name in available_packages: return module_name

    # Look for real module name
    try:
        module_url = google.lucky(module_name)
    except Exception:
        if session is not None:
            # use google on the remote end, because there are strange errors when using it on the client end when it has
            # a VPN connection open
            module_url = session.get_simple_property("google", "lucky('" + module_name + "')")
        else: return None, None

    # Search for github.com/ name
    session = requests.session()
    r = session.get(module_url)
    page_as_string = r.content

    if "github.com/" in page_as_string:

        module_name = page_as_string.split("github.com/")[1].split("/")[0]

        if module_name in available_packages: return module_name, None
        else: return module_name, "github.com"

    if "pip install" in page_as_string:

        module_name = page_as_string.split("pip install ")[1].split(" ")[0]

        if module_name in available_packages: return module_name, None
        else: return module_name, "pip"

    # Not found
    return None, None

# -----------------------------------------------------------------

def get_installation_commands(dependencies, packages, already_installed, available_packages, session):

    """
    This function ...
    :return:
    """

    installed = []
    not_installed = []

    commands = dict()

    # Loop over the dependencies
    for module in dependencies:

        module_name = module

        if module_name in packages: continue

        # Skip packages from the standard library
        if introspection.is_std_lib(module_name): continue

        # Check if already installed
        if module_name in already_installed: continue

        # Find name, check if available
        module_name, via = find_real_name(module_name, available_packages, session)

        if module_name is None:
            log.warning("Package '" + module + "' can not be installed")
            not_installed.append(module)
            continue

        #log.debug("Installing '" + module + "' ...")

        if via is None:

            command = "conda install " + module_name

            # self.remote.execute(command, show_output=True)

            lines = []
            lines.append(command)
            lines.append(("Proceed ([y]/n)?", "y"))

            #self.remote.execute_lines(*lines, show_output=True)

            commands[module] = lines

        elif via.startswith("pip"):

            command = via

            #self.remote.execute(command, show_output=True)

            commands[module] = command

        else: # not implemented yet

            not_installed.append(module)

        # Add to installed
        installed.append(module_name)

        # Return ...
        return commands, installed, not_installed

# -----------------------------------------------------------------

def get_skirt_hpc(remote, url, skirt_root_path, skirt_repo_path):

    """
    This function ...
    :param remote:
    :param url:
    :param skirt_root_path:
    :param skirt_repo_path:
    :return:
    """

    # CONVERT TO HTTPS ZIP LINK
    # example: https://github.ugent.be/sjversto/SKIRT-personal/archive/master.zip

    # CONVERT TO HTTPS LINK
    host = url.split("@")[1].split(":")[0]
    user_or_organization = url.split(":")[1].split("/")[0]
    repo_name = url.split("/")[-1].split(".git")[0]
    #url = "https://" + host + "/" + user_or_organization + "/" + repo_name + "/archive/master.zip"
    #url = "https://" + host + "/" + user_or_organization + "/" + repo_name + ".git"

    # Find the account file for the repository host (e.g. github.ugent.be)
    username, password = introspection.get_account(host)
    url = "https://" + username + ":" + password + "@" + host + "/" + user_or_organization + "/" + repo_name + ".git"

    # Download the repository to the PTS temporary directory locally
    #zip_path = network.download_file(url, introspection.pts_temp_dir)

    # Clone the repository locally in the pts temporary directory
    temp_repo_path = fs.join(introspection.pts_temp_dir, "skirt-git")
    if fs.is_directory(temp_repo_path): fs.remove_directory(temp_repo_path)
    command = "git clone " + url + " " + temp_repo_path
    subprocess.call(command.split())

    # Zip the repository
    zip_path = fs.join(introspection.pts_temp_dir, "skirt.zip")
    cwd = fs.change_cwd(temp_repo_path)
    zip_command = "git archive --format zip --output " + zip_path + " master"
    subprocess.call(zip_command.split())
    fs.change_cwd(cwd)

    # Transfer to the remote to the SKIRT directory
    remote.upload(zip_path, skirt_root_path)
    remote_zip_path = fs.join(skirt_root_path, fs.name(zip_path))

    # Remove local temporary things
    fs.remove_file(zip_path)
    fs.remove_directory(temp_repo_path)

    # Unpack the zip file into the 'git' directory
    remote.decompress_file(remote_zip_path, skirt_repo_path)

# -----------------------------------------------------------------
