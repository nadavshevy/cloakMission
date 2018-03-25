"""
This class contains the most basic Location class, both the engine PythonRunner use it
"""
import MapObject


class Location(MapObject.MapObject):
    """
    This is the most basic Location class, both the engine and the runner use it.
    """
    def __init__(self, row, col):
        """
        Creates a new instance of the Location class.

        :param row: the row of the location
        :type row: int
        :param col: the col of the location
        :type col: int
        """
        self.row = row
        self.col = col

        super(Location, self).__init__()

    @property
    def as_tuple(self):
        """
        Gets the location as a (row, col) tuple

        :return: the location as a (row, col) tuple
        :type: (int, int)
        """
        return self.row, self.col

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.row == other.row and self.col == other.col:
                return True
            return False
        raise TypeError('Can only equate a location to a different location')

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '<Location :%s>' % str(self)

    def __hash__(self):
        """
        Returns a hash code for the location.
        WARNING: this forces the map to be smaller than 100 rows.
        :return: A hash code for the location
        :rtype: int
        """
        return self.col * 100 + self.row

    def __str__(self):
        return str(self.as_tuple)

    def get_location(self):
        """
        Gets the location

        :return: the location
        :rtype: Location
        """
        return self
