"""
All objects that are interactable in the game should inherit from this base class
"""
import MapObject


class GameObject(MapObject.MapObject):
    """
    This is a base class for all interactable objects with a location in the game map
    """
    def __init__(self, location, owner, object_id):
        """
        :param location: the object's location
        :type location: LocationClass.Location
        :param owner: the object's owner
        :type owner: PlayerClass.BasePlayer
        :param object_id: the object's id
        :type object_id: int
        """
        super(GameObject, self).__init__()

        self.location = location
        """:type : LocationClass.Location"""
        self.owner = owner
        """:type : PlayerClass.BasePlayer"""
        self.id = object_id
        """:type : int"""

    def get_location(self):
        """
        Gets the object's location

        :return: the object's location
        :rtype: LocationClass.Location
        """
        return self.location
