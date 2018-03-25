"""
All objects that can move should inherit from this base class
"""
import GameObject


class MovableObject(GameObject.GameObject):
    """
    This is a base class for all moving objects in the game
    """
    def __init__(self, location, owner, object_id, max_speed):
        """
        :param location: the object's location
        :type location: LocationClass.Location
        :param owner: the object's owner
        :type owner: PlayerClass.BasePlayer
        :param object_id: the object's id
        :type object_id: int
        :param max_speed: the object's max speed (max number of steps each turn)
        :type max_speed: int
        """
        super(MovableObject, self).__init__(location, owner, object_id)

        self.max_speed = max_speed
        """:type : int"""
