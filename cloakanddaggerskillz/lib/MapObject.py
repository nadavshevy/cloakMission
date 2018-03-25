"""
This module holds the base classes for any object with a location on the map, and the location itself
"""
from abc import ABCMeta, abstractmethod


class MapObject(object):
    """
    This is a base class for all objects with a location in the game map
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_location(self):
        """
        Gets the object's location

        :return: the object's location
        :rtype: LocationClass.Location
        """
        raise NotImplemented('must implement get_location method')
