"""
This class contains the most basic Pirate class, both the engine Pirate class and the PythonRunner Pirate class inherit
from it.
"""
import MovableObject


class BasePirate(MovableObject.MovableObject):
    """
    This is the most basic Pirate class, both the engine Pirate class and the PythonRunner Pirate class inherit from it.
    """
    def __init__(self, location, owner, pirate_id, max_speed, initial_location, attack_radius, max_defense_turns=0):
        """
        :param location: the location of the pirate
        :type location: LocationClass.Location
        :param owner: the id of the owner of the pirate
        :type owner: PlayerClass.BasePlayer
        :param pirate_id: the id of the pirate
        :type pirate_id: int
        :param max_speed: the pirate's speed
        :type max_speed: int
        :param initial_location: the initial location of the pirate
        :type initial_location: Location
        :param attack_radius: the pirate's squared attack radius
        :type attack_radius: int
        :param max_defense_turns: the amount of turns this pirate's defense lasts once activated
        :type max_defense_turns: int
        """
        super(BasePirate, self).__init__(location, owner, pirate_id, max_speed)

        self.initial_location = initial_location
        """:type : LocationClass.Location"""
        self.is_lost = False
        """:type : bool"""
        # turns until the pirate respawn
        self.turns_to_revive = 0
        """:type : int"""
        self.reload_turns = 0
        """:type : int"""
        self.defense_reload_turns = 0
        """:type : int"""
        # the number of turns until the pirate's defense will expire
        self.defense_expiration_turns = 0
        """:type : int"""
        # the amount of turns this pirate's defense lasts once activated
        self.max_defense_turns = max_defense_turns
        """:type : int"""
        self.turns_to_sober = 0
        """:type : int"""
        # the amount of turns until left for cloak
        self.cloak_turns = 0
        """:type : int"""
        self.treasure = None
        """:type : pirates.Treasure | pythonRunner.Treasure"""
        # powerups
        self.attack_radius = attack_radius
        """:type : int"""
        self.carry_treasure_speed = 1
        """:type : int"""
        self.powerups = []
        """:type : list[str]"""

    def has_treasure(self):
        """
        Returns whether or not the pirate has treasure

        :return: True if the pirate has treasure, False otherwise
        """
        return self.treasure is not None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.id == other.id and self.owner == other.owner:
                return True
        return False

    def __repr__(self):
        return "<Pirate ID:%d Owner:%d Loc:%s>" % (self.id, self.owner.id, self.location.as_tuple)

    def __hash__(self):
        return self.id * 10 + self.owner.id
