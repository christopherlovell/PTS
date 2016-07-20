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
import urllib
from abc import ABCMeta, abstractmethod

# Import the relevant PTS classes and modules
from ..basics.configurable import Configurable
from ..simulation.execute import SkirtExec
from ..simulation.remote import Remote
from ..tools import introspection
from ..tools import filesystem as fs
from ..tools.logging import log

# -----------------------------------------------------------------

# For SSH key:
# eval $(ssh-agent)
# ssh-add

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

# Private repository links
private_skirt_ssh_link = "git@github.ugent.be:SKIRT/SKIRT.git"
private_skirt_https_link = "https://github.ugent.be/SKIRT/SKIRT.git"

# Public repository links
public_skirt_https_link = "https://github.com/SKIRT/SKIRT.git"

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

        # The path to the qmake executable corresponding to the most recent Qt installation
        self.qmake_path = None

    # -----------------------------------------------------------------

    def install_local(self):

        """
        This function ...
        :return:
        """

        # Install Qt
        self.install_qt_local()

        # Get the SKIRT code
        self.get_skirt_local()

        # Install SKIRT
        self.install_skirt_local()

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

    # -----------------------------------------------------------------

    def install_skirt_local(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def install_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing remotely ...")

        # Install Qt
        self.install_qt_remote()

        # Get the SKIRT code
        self.get_skirt_remote()

        # Install SKIRT
        self.install_skirt_remote()

    # -----------------------------------------------------------------

    def install_qt_remote(self):

        """
        This function ...
        :return:
        """

        link = "http://download.qt.io/official_releases/qt/5.5/5.5.1/single/qt-everywhere-opensource-src-5.5.1.tar.gz"

        # Determine the path for the Qt source code
        path = fs.join(None, "qt.tar.gz")

        # Create a
        urllib.urlretrieve(self.config.qt_link, path)

        # FOR HPC: module load Qt/5.2.1-intel-2015a

    # -----------------------------------------------------------------

    def get_skirt_remote(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def install_skirt_remote(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def test_local(self):

        """
        This function ...
        :return:
        """

# -----------------------------------------------------------------

# Private repository links
private_pts_ssh_link = "git@github.ugent.be:SKIRT/PTS.git"
private_pts_https_link = "https://github.ugent.be/SKIRT/PTS.git"

# Public repository links
public_pts_link = "https://github.com/SKIRT/PTS.git"

# -----------------------------------------------------------------

class PTSInstaller(Installer):

    """
    This function ...
    """

    def install_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing PTS locally ...")

    # -----------------------------------------------------------------

    def install_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Installing PTS remotely ...")

    # -----------------------------------------------------------------

    def test_local(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def test_remote(self):

        """
        This function ...
        :return:
        """

# -----------------------------------------------------------------
