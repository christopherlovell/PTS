#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

# Import standard modules
import numpy as np
import logging
from scipy import ndimage

# Import image modules
import fitting
import plotting
import regions
import statistics
from tools import coordinates, cropping, interpolation

# Import astronomical modules
from photutils import find_peaks
from find_galaxy import FindGalaxy

# *****************************************************************

def locate_peaks(data, sigma=3.0):

    """
    This function looks for peaks in the given frame
    :param data:
    :param sigma:
    :return:
    """

    # Calculate the sigma-clipped statistics of the frame and find the peaks
    mean, median, stddev = statistics.sigma_clipped_statistics(data, sigma=3.0)
    threshold = median + (7.0 * stddev)
    peaks = find_peaks(data, threshold, box_size=5)

    # Return the list of peaks
    return peaks, median

# *****************************************************************

def find_sources(data, region, plot):

    """
    This function searches for sources within a given frame and a region of ellipses
    :param data:
    :param region:
    :param plot:
    :return:
    """

    # Initialize an empty list of sources
    sources = []

    # Inform the user
    logging.info("Looking for sources...")

    # For each object, determine the minimal enclosing box
    for x_min, x_max, y_min, y_max in regions.get_enclosing_boxes(region):

        # Cut out a box of the primary image around the star
        box, x_min, x_max, y_min, y_max = cropping.crop_direct(data, x_min, x_max, y_min, y_max)

        # If the frame is zero in this box, continue to the next object
        if not np.any(box): continue

        # If the box is too small, skip this object
        if box.shape[0] < 5 or box.shape[1] < 5: continue

        # Find peaks
        peaks, median = locate_peaks(box)

        # Find sources
        sources += find_sources_peaks(box-median, peaks, plot=plot, x_shift=x_min, y_shift=y_min)

    # Return the list of sources
    return sources

# *****************************************************************

def find_sources_peaks(data, peaks, plot=None, x_shift=0.0, y_shift=0.0):

    """
    This function searches for sources in the given frame, based on a list of peaks detected in this frame
    :param data: the frame
    :param peaks: the list of peaks
    :param plot: optional, specific plotting flags
    :param x_shift: the shift in the x direction that is required to ...
    :param y_shift: the shift in the y direction that is required to ...
    :return:
    """

    # Initialize an empty list of sources
    sources = []

    if plot is None: plot=[False, False, False, False]

    # No peaks are found above the threshold
    if len(peaks) == 0:

        # Plot the data
        if plot[0]: plotting.plot_box(data)

        # Look for a star
        sources += find_sources_nopeak(data, x_shift, y_shift, plot=plot[0])

    # Exactly one peak is found
    elif len(peaks) == 1:

        x_peak = peaks['x_peak'][0]
        y_peak = peaks['y_peak'][0]

        # Look for a star corresponding to this peak
        sources += find_sources_1peak(data, x_peak, y_peak, x_shift, y_shift, plot=plot[1])

    # Two peaks are found in the box
    elif len(peaks) == 2:

        x_peak1 = peaks['x_peak'][0]
        y_peak1 = peaks['y_peak'][0]

        x_peak2 = peaks['x_peak'][1]
        y_peak2 = peaks['y_peak'][1]

        # Look for stars corresponding to the two found peaks
        sources += find_sources_2peaks(data, x_peak1, y_peak1, x_peak2, y_peak2, x_shift, y_shift, plot=plot[2])

    # More than two peaks are found
    elif len(peaks) > 2:

        # Look for multiple stars
        sources += find_sources_multiplepeaks(data, peaks['x_peak'], peaks['y_peak'], x_shift, y_shift, plot=plot[3])

    # Return the list of sources
    return sources

# *****************************************************************

def find_sources_nopeak(box, x_min, y_min, plot=False):

    """
    This function ...
    :param box:
    :param x_min:
    :param y_min:
    :param plot:
    :return:
    """

    # Initiate an empty list of stars
    sources = []

    # If the box is too small, don't bother looking for stars (anymore)
    if box.shape[0] < 5 or box.shape[1] < 5: return []

    # Fit a 2D Gaussian to the data
    model = fitting.fit_2D_Gaussian(box)

    # Get the parameters of the Gaussian function
    amplitude = model.amplitude
    x_mean = model.x_mean.value
    y_mean = model.y_mean.value

    # Skip non-stars (negative amplitudes)
    if amplitude < 0:

        logging.warning("negative amplitude")
        return []

    # If the center of the Gaussian falls out of the square, skip this star
    if round(x_mean) < 0 or round(x_mean) >= box.shape[0] - 1 or round(y_mean) < 0 or round(y_mean) >= box.shape[1] - 1:

        logging.warning("out of box")
        return []

    # Determine the coordinates of the center pixel of the box
    x_center = 0.5*box.shape[1]
    y_center = 0.5*box.shape[0]

    # Plot if requested
    if plot: plotting.plot_peak_model(box, x_center, y_center, model)

    # Change the coordinates of the model to absolute coordinates
    model.x_mean.value = model.x_mean.value + x_min
    model.y_mean.value = model.y_mean.value + y_min

    # Add the model for this source to the list of sources
    sources.append(model)

    # Return the list of sources (containing only one source in this case)
    return sources

# *****************************************************************

def find_sources_1peak(box, x_peak, y_peak, x_min, y_min, plot=False):

    """
    This function searches for sources ...
    :param box:
    :param x_peak:
    :param y_peak:
    :param x_min:
    :param y_min:
    :param plot:
    :return:
    """

    # Initiate an empty list of stars
    sources = []

    # If the box is too small, don't bother looking for stars (anymore)
    if box.shape[0] < 5 or box.shape[1] < 5: return []

    # Fit a 2D Gaussian to the data
    model = fitting.fit_2D_Gaussian(box, center=(x_peak, y_peak))

    # Get the parameters of the Gaussian function
    amplitude = model.amplitude
    x_mean = model.x_mean.value
    y_mean = model.y_mean.value

    # Skip non-stars (negative amplitudes)
    if amplitude < 0:

        #print "negative amplitude"
        return []

    # If the center of the Gaussian falls out of the square, skip this star
    if round(x_mean) < 0 or round(x_mean) >= box.shape[0] - 1 or round(y_mean) < 0 or round(y_mean) >= box.shape[1] - 1:

        #print "out of box"
        return []

    # Check if the center of the Gaussian corresponds to the position of the detected peak
    diff_x = x_mean - x_peak
    diff_y = y_mean - y_peak

    distance = np.sqrt(diff_x**2+diff_y**2)

    # Check whether the position of the model and the peak are in agreement
    if distance < 1.5: # Potential star detected!

        # Plot if requested
        if plot: plotting.plot_peak_model(box, x_peak, y_peak, model)

        # Change the coordinates of the model to absolute coordinates
        model.x_mean.value = model.x_mean.value + x_min
        model.y_mean.value = model.y_mean.value + y_min

        # Add the model for this source to the list of sources
        sources.append(model)

    # Zoom in on the detected peak
    else:

        # Calculate the size of the smaller box
        smaller_box_ysize = int(round(box.shape[0] / 4.0))
        smaller_box_xsize = int(round(box.shape[1] / 4.0))

        # Create a smaller box
        smaller_box, smaller_xmin, smaller_xmax, smaller_ymin, smaller_ymax = cropping.crop(box, x_peak, y_peak, smaller_box_xsize, smaller_box_ysize)

        # Calculate x and y delta
        x_delta = x_min + smaller_xmin
        y_delta = y_min + smaller_ymin

        # Find relative coordinate of peak
        rel_xpeak, rel_ypeak = coordinates.relative_coordinate(x_peak, y_peak, smaller_xmin, smaller_ymin)

        # Try again (iterative procedure of zooming in, stops if the size of the box becomes too small)
        sources += find_sources_1peak(smaller_box, rel_xpeak, rel_ypeak, x_delta, y_delta)

    # Return the list of sources (containing only one source in this case)
    return sources

# *****************************************************************

def find_sources_2peaks(box, x_peak1, y_peak1, x_peak2, y_peak2, x_min, y_min, plot=False):

    """
    This function searches for sources ...
    :param box:
    :param x_peak1:
    :param y_peak1:
    :param x_peak2:
    :param y_peak2:
    :param x_min:
    :param y_min:
    :param plot:
    :return:
    """

    # Initiate an empty list of stars
    sources = []

    # Calculate the distance between the two peaks
    diff_x = x_peak1 - x_peak2
    diff_y = y_peak1 - y_peak2
    distance = np.sqrt(diff_x**2 + diff_y**2)

    # Calculate the midpoint between the two peaks
    mid_x = 0.5*(x_peak1 + x_peak2)
    mid_y = 0.5*(y_peak1 + y_peak2)

    # The peaks are probably part of the same object
    # So, perform a fit with a Gaussian
    if distance < 4:

        # Do the fit
        model = fitting.fit_2D_Gaussian(box, center=(mid_x, mid_y))

        # Plot if requested
        if plot: plotting.plot_peaks_models(box, [x_peak1, x_peak2], [y_peak1, y_peak2], [model])

        # Change the coordinates of the model to absolute coordinates
        model.x_mean.value = model.x_mean.value + x_min
        model.y_mean.value = model.y_mean.value + y_min

        # Add the model for this source to the list of sources
        sources.append(model)

    # Split the box
    else:

        # Calculate the absolute distance between the two peaks
        delta_x = np.abs(diff_x)
        delta_y = np.abs(diff_y)

        # Cut along the axis where the distance is largest
        if delta_x > delta_y:

            # Create the boxes
            smaller_box_1 = box[:][0:mid_x]
            smaller_box_2 = box[:][mid_x:]

            # Determine the relative positions of the found peaks
            rel_peak1_x, rel_peak1_y = coordinates.relative_coordinate(x_peak1, y_peak1, 0, 0)
            rel_peak2_x, rel_peak2_y = coordinates.relative_coordinate(x_peak2, y_peak2, mid_x, 0)

            # Determine the translation needed for the second cut
            rel_xmin2 = x_min + mid_x
            rel_ymin2 = y_min

        else:

            # Create the boxes
            smaller_box_1 = box[0:mid_y][:]
            smaller_box_2 = box[mid_y:][:]

            # Determine the relative positions of the found peaks
            rel_peak1_x, rel_peak1_y = coordinates.relative_coordinate(x_peak1, y_peak1, 0, 0)
            rel_peak2_x, rel_peak2_y = coordinates.relative_coordinate(x_peak2, y_peak2, 0, mid_y)

            # Determine the translation needed for the second cut
            rel_xmin2 = x_min
            rel_ymin2 = y_min + mid_y

        # Find stars in both of the cuts
        sources += find_sources_1peak(smaller_box_1, rel_peak1_x, rel_peak1_y, x_min, y_min, plot=plot)
        sources += find_sources_1peak(smaller_box_2, rel_peak2_x, rel_peak2_y, rel_xmin2, rel_ymin2, plot=plot)

    # Return the list of sources
    return sources

# *****************************************************************

def find_sources_multiplepeaks(box, x_peaks, y_peaks, x_min, y_min, plot=False):

    """
    This function searches for sources ...
    :param box:
    :param x_peaks:
    :param y_peaks:
    :param x_min:
    :param y_min:
    :param plot:
    :return:
    """

    # Initialize an empty list of stars
    sources = []

    # Calculate the new x and y size of the smaller boxes
    smaller_ysize = int(round(box.shape[0] / 2.0))
    smaller_xsize = int(round(box.shape[1] / 2.0))

    # Define the boundaries of 4 new boxes
    boundaries_list = []
    boundaries_list.append((0,smaller_ysize, 0,smaller_xsize))
    boundaries_list.append((0,smaller_ysize, smaller_xsize,box.shape[1]))
    boundaries_list.append((smaller_ysize,box.shape[0], 0,smaller_xsize))
    boundaries_list.append((smaller_ysize,box.shape[0], smaller_xsize,box.shape[1]))

    # For each new box
    for boundaries in boundaries_list:

        # Create the box
        smaller_box = box[boundaries[0]:boundaries[1],boundaries[2]:boundaries[3]]

        # Initialize empty lists to contain the coordinates of the peaks that fall within the current box
        x_peaks_inside = []
        y_peaks_inside = []

        # Calculate the translation needed for this smaller box
        abs_x_min = x_min + boundaries[2]
        abs_y_min = y_min + boundaries[0]

        # Check how many peaks fall within this box
        for x_peak, y_peak in zip(x_peaks, y_peaks):

            if x_peak >= boundaries[2] and x_peak < boundaries[3] and y_peak >= boundaries[0] and y_peak < boundaries[1]:

                x_peaks_inside.append(x_peak)
                y_peaks_inside.append(y_peak)

        # No peaks in this box
        if len(x_peaks_inside) == 0: continue

        # One peak in this box
        if len(x_peaks_inside) == 1:

            # Determine the relative coordinate of the peak
            x_peak_rel, y_peak_rel = coordinates.relative_coordinate(x_peaks_inside[0], y_peaks_inside[0], boundaries[2], boundaries[0])

            # Find the source
            sources += find_sources_1peak(smaller_box, x_peak_rel, y_peak_rel, abs_x_min, abs_y_min, plot=plot)

        # Two peaks in this box
        elif len(x_peaks_inside) == 2:

            # Determine the relative coordinates of the peaks
            x_peak1_rel, y_peak1_rel = coordinates.relative_coordinate(x_peaks_inside[0], y_peaks_inside[0], boundaries[2], boundaries[0])
            x_peak2_rel, y_peak2_rel = coordinates.relative_coordinate(x_peaks_inside[1], y_peaks_inside[1], boundaries[2], boundaries[0])

            # Find sources
            sources += find_sources_2peaks(smaller_box, x_peak1_rel, y_peak1_rel, x_peak2_rel, y_peak2_rel, abs_x_min, abs_y_min, plot=plot)

        # More than 2 peaks
        else:

            # Initialize empty lists for the relative coordinates of the peaks within this smaller box
            x_peaks_rel = []
            y_peaks_rel = []

            # Calculate these relative coordinates
            for x_peak_inside, y_peak_inside in zip(x_peaks_inside, y_peaks_inside):

                x_peak_rel, y_peak_rel = coordinates.relative_coordinate(x_peak_inside, y_peak_inside, boundaries[2], boundaries[0])
                x_peaks_rel.append(x_peak_rel)
                y_peaks_rel.append(y_peaks_rel)

            # Find sources
            sources += find_sources_multiplepeaks(smaller_box, x_peaks_rel, y_peaks_rel, abs_x_min, abs_y_min, plot=plot)

    # Return the parameters of the found stars
    return sources

# *****************************************************************

def remove_duplicate_sources(sources):

    """
    This function ...
    :param sources:
    :return:
    """

    # Inform the user
    logging.info("Removing duplicates...")

    # Initialize a list that only contains unique sources
    unique_sources = []

    # Loop over all sources, adding them to the list of unique sources if not yet present
    for source in sources:

        # Check if another source on the same location is already present in the unique_sources list
        for unique_source in unique_sources:

            distance = coordinates.distance_models(source, unique_source)
            if distance < 1.0: break

        # No break statement was encountered; add the source to the unique_sources list
        else: unique_sources.append(source)

    # Return the list of unique sources
    return unique_sources

# *****************************************************************

def estimate_background(data, mask, interpolate=True, sigma_clip=True):

    """
    This function ...
    :param data:
    :param mask:
    :return:
    """

    # Sigma clipping
    if sigma_clip: mask = statistics.sigma_clip_mask(data, sigma=3.0, mask=mask)

    # Decide whether to interpolate the background or to calculate a single median background value
    if interpolate: background = interpolation.in_paint(data, mask)

    else:

        # Calculate the median
        median = np.ma.median(np.ma.masked_array(data, mask=mask))

        # Create the background array
        background = np.full(data.shape, median)

    # Return the background
    return background, mask

# *****************************************************************

def make_star_model(shape, data, annuli_mask, fit_mask, background_outer_sigmas, fit_sigmas,
                    model_name, upsample_factor=1.0, interpolate_background=True, sigma_clip_background=True, plot=False):

    """
    This function ...
    :param shape:
    :param data:
    :param annuli_mask:
    :param fit_mask:
    :param background_inner_sigmas:
    :param background_outer_sigmas:
    :param fit_sigmas:
    :param upsample_factor:
    :param interpolate_background:
    :param sigma_clip_background:
    :param plot:
    :return:
    """

    # Get the shape's parameters
    x_center, y_center, x_radius, y_radius = regions.ellipse_parameters(shape)

    # Set the radii for cutting out the background box
    radius = 0.5*(x_radius + y_radius)
    x_radius_outer = background_outer_sigmas*x_radius
    y_radius_outer = background_outer_sigmas*y_radius

    # Cut out the background
    background, x_min_back, x_max_back, y_min_back, y_max_back = cropping.crop(data, x_center, y_center, x_radius_outer, y_radius_outer)

    # Cut out the mask for the background
    background_mask = cropping.crop_check(annuli_mask, x_min_back, x_max_back, y_min_back, y_max_back)

    # Set the radii for cutting out the box for fitting
    x_radius_fitting = fit_sigmas*x_radius
    y_radius_fitting = fit_sigmas*y_radius

    # Cut out a box of selected frame around the star
    star, x_min, x_max, y_min, y_max = cropping.crop(data, x_center, y_center, x_radius_fitting, y_radius_fitting)

    # Cut out the mask for fitting
    star_mask = fit_mask[y_min:y_max, x_min:x_max]

    # Estimate the background
    background_mask_beforeclipping = np.copy(background_mask)
    est_background, background_mask = estimate_background(background, background_mask, interpolate=interpolate_background, sigma_clip=sigma_clip_background)

    # Crop the interpolated background to the frame of the box
    star_background = cropping.crop_check(est_background, x_min-x_min_back, x_max-x_min_back, y_min-y_min_back, y_max-y_min_back)

    # Calculate the relative coordinates of the center
    x_center_rel, y_center_rel = coordinates.relative_coordinate(x_center, y_center, x_min, y_min)

    # Fit the star
    model_function = fitting.fit_2D_model(star, star_mask, star_background, model=model_name, x_center=x_center_rel,
                                          y_center=y_center_rel, radius=radius, x_shift=x_min, y_shift=y_min,
                                          upsample_factor=upsample_factor, pixel_deviation=0.5)

    # Evaluate the model
    evaluated_model = fitting.evaluate_model(model_function, x_min, x_max, y_min, y_max, x_delta=1.0/upsample_factor, y_delta=1.0/upsample_factor)

    # Check for succesful fit
    success = (np.isclose(model_function.x_stddev.value, x_radius, rtol=0.2) and np.isclose(model_function.y_stddev.value, y_radius, rtol=0.2))

    if success:

        if upsample_factor > 1.0: evaluated_model = ndimage.interpolation.zoom(evaluated_model, zoom=1.0/upsample_factor)

        # Plot
        if plot: plotting.plot_star_model(background=np.ma.masked_array(background,mask=background_mask_beforeclipping),
                                          background_clipped=np.ma.masked_array(background,mask=background_mask),
                                          est_background=est_background,
                                          star=np.ma.masked_array(star,mask=star_mask),
                                          est_background_star= star_background,
                                          fitted_star=evaluated_model)

        # Adjust the parameters of the shape to the model of this star
        shape.coord_list[0] = model_function.x_mean.value
        shape.coord_list[1] = model_function.y_mean.value
        shape.coord_list[2] = model_function.x_stddev.value
        shape.coord_list[3] = model_function.y_stddev.value

    # Return ...
    return success, shape, evaluated_model, (x_min, x_max, y_min, y_max)

# *****************************************************************

def find_galaxy_orientation(data, region, plot=False):

    """
    This function ...
    :param data:
    :param region:
    :param plot:
    :return:
    """

    # TODO: improve this function, check the documentation of the FindGalaxy class to improve the fit, instead of using cropping to 'solve' fitting problems

    # Verify that the region contains only one shape
    assert len(region) == 1, "The region can only contain one shape"
    shape = region[0]

    x_position = shape.coord_list[0]
    y_position = shape.coord_list[1]

    # Look for the galaxy orientation
    orientation = FindGalaxy(data[::-1,:], quiet=True, plot=plot)

    # The length of the major axis of the ellipse
    major = 3.0 * orientation.majoraxis

    # The width and heigth of the ellips
    width = major
    height = major * (1 - orientation.eps)

    if not np.isclose(x_position, orientation.ypeak, rtol=0.02) or not np.isclose(y_position, orientation.xpeak, rtol=0.02):

        x_size = data.shape[1]
        y_size = data.shape[0]
        size = max(x_size, y_size)

        smaller_data, x_min, x_max, y_min, y_max = cropping.crop(data, x_position, y_position, size/4.0, size/4.0)

        # Again look for the galaxy orientation
        orientation = FindGalaxy(smaller_data[::-1,:], quiet=True, plot=plot)

        # The length of the major axis of the ellipse
        major = 3.0 * orientation.majoraxis

        # The width and heigth of the ellips
        width = major
        height = major * (1 - orientation.eps)

        # Correct the center coordinate for the cropping
        orientation.ypeak += x_min
        orientation.xpeak += y_min

        if not np.isclose(x_position, orientation.ypeak, rtol=0.02) or not np.isclose(y_position, orientation.xpeak, rtol=0.02):
            logging.warning("Could not find a galaxy at the specified position")

    # Return the parameters of the galaxy
    return (orientation.ypeak, orientation.xpeak, width, height, orientation.theta)

# *****************************************************************