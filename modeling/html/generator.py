#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.html.generator Contains the HTMLGenerator class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ...core.tools.logging import log
from ..component.galaxy import GalaxyModelingComponent
from ...core.tools import html
from ...core.tools import filesystem as fs
from ..plotting.model import load_test_components, render_components_html

# -----------------------------------------------------------------

stylesheet_url = "http://users.ugent.be/~sjversto/stylesheet.css"

# -----------------------------------------------------------------

class HTMLGenerator(GalaxyModelingComponent):

    """
    This function ...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param args:
        :param kwargs:
        """

        # Call the constructor of the base class
        super(HTMLGenerator, self).__init__(*args, **kwargs)

        # Tables
        self.info_table = None
        self.properties_table = None
        self.status_table = None

        # Models
        self.old_model = None
        self.young_model = None
        self.ionizing_model = None
        self.dust_model = None

        # Pages
        self.status_page = None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Setup
        self.setup(**kwargs)

        # Make tables
        self.make_tables()

        # Make plots
        self.make_plots()

        # Generaet the html
        self.generate()

        # Write
        self.write()

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(HTMLGenerator, self).setup(**kwargs)

    # -----------------------------------------------------------------

    def make_tables(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making tables ...")

        # Make info table
        self.make_info_table()

        # Make properties table
        self.make_properties_table()

        # Make status table
        self.make_status_table()

    # -----------------------------------------------------------------

    def make_info_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the info table ...")

        # Create the table
        self.info_table = html.SimpleTable(self.galaxy_info.items(), header_row=["Property", "Value"])

    # -----------------------------------------------------------------

    def make_properties_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the properties table ...")

        # Create the table
        self.properties_table = html.SimpleTable(self.galaxy_properties.as_tuples(), header_row=["Property", "Value"])

    # -----------------------------------------------------------------

    def make_status_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making the status table ...")

        # Set the background colours of the cells
        bgcolors = [(None, color) for color in self.status.colors]

        # Create the table
        self.status_table = html.SimpleTable(self.status, header_row=["Step", "Status"], bgcolors=bgcolors)

    # -----------------------------------------------------------------

    def make_geometry_tables(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making geometry tables ...")

        # Old bulge
        self.make_old_bulge_geometry_table()

        # Old disk
        self.make_old_disk_geometry_table()

        # Young stars
        self.make_young_geometry_table()

        # Ionizing stars
        self.make_ionizing_geometry_table()

        # Dust
        self.make_dust_geometry_table()

    # -----------------------------------------------------------------

    def make_old_bulge_geometry_table(self):

        """
        This function ...
        :return:
        """



    # -----------------------------------------------------------------

    def make_old_disk_geometry_table(self):

        """
        This function ...
        :return: 
        """

    # -----------------------------------------------------------------

    def make_young_geometry_table(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def make_ionizing_geometry_table(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def make_dust_geometry_table(self):

        """
        This function ...
        :return:
        """

    # -----------------------------------------------------------------

    def make_plots(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making plots ...")

        # Model
        self.make_model_plots()

    # -----------------------------------------------------------------

    def make_model_plots(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Making model plots ...")

        # TEMPORARY: LOAD TEST COMPONENTS
        components = load_test_components()

        old_components = {"disk": components["old"], "bulge": components["bulge"]}
        young_components = {"young": components["young"]}
        ionizing_components = {"ionizing": components["ionizing"]}
        dust_components = {"dust": components["dust"]}

        # Generate HTML
        self.old_model = render_components_html(old_components, only_body=True, width=400, height=500, style="minimal")
        self.young_model = render_components_html(young_components, only_body=True, width=400, height=500, style="minimal")
        self.ionizing_model = render_components_html(ionizing_components, only_body=True, width=400, height=500, style="minimal")
        self.dust_model = render_components_html(dust_components, only_body=True, width=400, height=500, style="minimal")

    # -----------------------------------------------------------------

    def generate(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the HTML ...")

        # Generate the status
        self.generate_status()

    # -----------------------------------------------------------------

    def generate_status(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Generating the status page ...")

        # Create title
        title = html.fontsize_template.format(size=20, text=html.underline_template.format(text="Modeling of " + self.galaxy_name))

        # Create titles
        title_info = html.underline_template.format(text="GALAXY INFO")
        title_properties = html.underline_template.format(text="GALAXY PROPERTIES")
        title_status = html.underline_template.format(text="MODELING STATUS")
        title_model = html.underline_template.format(text="3D MODEL GEOMETRY")

        body = title + html.newline + html.newline + title_info + html.newline + html.newline + str(self.info_table) + html.newline + html.newline
        body += title_properties + html.newline + html.newline + str(self.properties_table) + html.newline + html.newline
        body += title_status + html.newline + html.newline + str(self.status_table) + html.newline + html.newline

        body += title_model + html.newline + html.newline
        body += html.bold_template.format(text="Old stars") + html.newline + html.newline
        body += self.old_model + html.newline + html.newline

        body += html.bold_template.format(text="Young stars") + html.newline + html.newline
        body += self.young_model + html.newline + html.newline

        body += html.bold_template.format(text="Ionizing stars") + html.newline + html.newline
        body += self.ionizing_model + html.newline + html.newline

        body += html.bold_template.format(text="Dust") + html.newline + html.newline
        body += self.dust_model + html.newline + html.newline

        # Create contents
        contents = dict()
        contents["title"] = "Modeling of " + self.galaxy_name
        contents["head"] = html.link_stylesheet_header_template.format(url=stylesheet_url)
        contents["body"] = body

        # Create the status page
        self.status_page = html.page_template.format(**contents)

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Write status page
        self.write_status_page()

        # Write models page
        self.write_models_page()

    # -----------------------------------------------------------------

    @property
    def status_page_path(self):

        """
        This function ...
        :return:
        """

        return self.environment.html_status_path

    # -----------------------------------------------------------------

    @property
    def models_page_path(self):

        """
        This function ...
        :return:
        """

        return fs.join(self.environment.html_path, "models.html")

    # -----------------------------------------------------------------

    def write_status_page(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing status page ...")

        # Write
        fs.write_text(self.status_page_path, self.status_page)

    # -----------------------------------------------------------------

    def write_models_page(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the models page ...")

# -----------------------------------------------------------------
