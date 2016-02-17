#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       AstroMagic -- the image editor for astronomers        **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# -----------------------------------------------------------------
#  Package initialization file
# -----------------------------------------------------------------

## \package pts.magic.basics TO DO
#
# This package ...
#

# -----------------------------------------------------------------

# Import classes to make them available at the level of this subpackage
from .vector import Position, Extent
from .layers import Layers
from .mask import Mask
from .region import Region
from .skyregion import SkyRegion
from .trackrecord import TrackRecord
from .geometry import Line, Circle, Ellipse, Rectangle
from .skygeometry import SkyCoord, SkyLine, SkyCircle, SkyEllipse, SkyRectangle
from .catalogcoverage import CatalogCoverage
from .coordinatesystem import CoordinateSystem
