#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.sequences Provides functions for dealing with sequences (lists, iterables).

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import operator
import itertools
from functools import partial

# -----------------------------------------------------------------

def permutate(lst, lengths=None):

    """
    This function ...
    :param lst: 
    :param lengths: 
    :return: 
    """

    if lengths is None: return itertools.permutations(lst)
    elif isinstance(lengths, int): return itertools.permutations(lst, r=lengths)
    elif isinstance(lengths, list):
        result = []
        for length in lengths: result.extend(itertools.permutations(lst, r=length))
        return result
    else: raise ValueError("Invalid value for 'lengths'")

# -----------------------------------------------------------------

def combinations(lst, lengths, repeat=False):

    """
    This function ...
    :param lst: 
    :param lengths: 
    :param repeat:
    :return: 
    """

    combination_function = itertools.combinations_with_replacement if repeat else itertools.combinations

    if isinstance(lengths, int): return combination_function(lst, r=lengths)
    elif isinstance(lengths, list):
        result = []
        for length in lengths: result.extend(combination_function(lst, r=length))
        return result
    else: raise ValueError("Invalid value for 'lengths")

# -----------------------------------------------------------------

def interleave(seqs):

    """ Interleave a sequence of sequences
    >>> list(interleave([[1, 2], [3, 4]]))
    [1, 3, 2, 4]
    >>> ''.join(interleave(('ABC', 'XY')))
    'AXBYC'
    Both the individual sequences and the sequence of sequences may be infinite
    Returns a lazy iterator
    """

    iters = itertools.cycle(map(iter, seqs))
    while True:
        try:
            for itr in iters:
                yield next(itr)
            return
        except StopIteration:
            predicate = partial(operator.is_not, itr)
            iters = itertools.cycle(itertools.takewhile(predicate, iters))

# -----------------------------------------------------------------

def combine_unique(*args):

    """
    This function ...
    :return:
    """

    unique = set()

    # Add
    for seq in args: unique |= set(seq)

    return list(unique)

# -----------------------------------------------------------------

def find_closest_index(seq, value):

    """
    This function ...
    :param seq:
    :param value:
    :return:
    """

    closest_delta = None
    #closest_delta = float("inf")
    closest_index = None

    #column_unit = table[column_name].unit

    #value_unit = value.unit if hasattr(value, "unit") else None

    # Check units
    #if value_unit is not None:
        #if column_unit is None: raise ValueError("Value has a unit but column has not: cannot compare these values")
        #else: value = value.to(column_unit).value # for correct comparison inside loop
    #elif column_unit is not None: raise ValueError("Value has no unit but the column has: cannot compare these values")

    # Loop over all entries in the sequence
    for i in range(len(seq)):

        delta = abs(seq[i] - value)

        if closest_delta is None or delta < closest_delta:
            closest_delta = delta
            closest_index = i

    return closest_index

# -----------------------------------------------------------------

def find_exact_index(seq, value):

    """
    This function ...
    :param seq:
    :param value:
    :return:
    """

    return seq.index(value)

# -----------------------------------------------------------------

def all_equal(lst):

    """
    This function ...
    :param lst:
    :return:
    """

    first = lst[0]

    for index in range(1,len(lst)):
        if lst[index] != first: return False

    return True

# -----------------------------------------------------------------

def zip_into_dict(list_a, list_b):

    """
    This function ...
    :param list_a:
    :param list_b:
    :return:
    """

    dictionary = dict()
    for item_a, item_b in zip(list_a, list_b): dictionary[item_a] = item_b
    return dictionary

# -----------------------------------------------------------------

def contains_duplicates(sequence):

    """
    This function ...
    :param sequence: 
    :return: 
    """

    return len(set(sequence)) != len(sequence)

# -----------------------------------------------------------------

def contains_same_elements(sequence_a, sequence_b):

    """
    This function ...
    :param sequence_a: 
    :param sequence_b: 
    :return: 
    """

    return set(sequence_a) == set(sequence_b)

# -----------------------------------------------------------------

def elements_not_in_other(sequence_a, sequence_b):

    """
    This function ...
    :param sequence_a: 
    :param sequence_b: 
    :return: 
    """

    elements = set()

    for element in sequence_a:

        if element not in sequence_b: elements.add(element)

    return list(elements)

# -----------------------------------------------------------------

def common_elements(sequence_a, sequence_b):

    """
    This function ...
    :param sequence_a: 
    :param sequence_b: 
    :return: 
    """

    elements = set()

    for element in sequence_a:

        if element in sequence_b: elements.add(element)

    return list(elements)

# -----------------------------------------------------------------

def append_unique(lst, element):

    """
    This function ...
    :param lst: 
    :param element: 
    :return: 
    """

    if element not in lst: lst.append(element)

# -----------------------------------------------------------------

def extend_unique(lst, elements):

    """
    This function ...
    :param lst: 
    :param elements: 
    :return: 
    """

    for element in elements: append_unique(lst, element)

# -----------------------------------------------------------------
