"""
This is the base player class which the runner and game use
"""


class BasePlayer(object):
    """
    The player object, and all of it's attributes.
    """
    def __init__(self, player_id, bot_name):
        """
        Initiates the player.

        :param player_id: the ID of the player
        :type player_id: int
        :param bot_name: the name of the the bot that belongs to the player
        :type bot_name: str
        """
        self.id = player_id
        """:type : int"""
        self.bot_name = bot_name
        """:type : str"""
        self.is_killed = False
        """:type : bool"""
        self.orders = []
        """:type : list[dict[str, any]]"""
        self.score = 0
        """:type : int"""
        self.score_history = []
        """:type : list[int]"""
        self.num_scripts = 0
        """:type : int"""
        self.turns_to_cloak = 0
        """:type : int"""

        self.living_pirates = []  # pirates that are currently alive
        """:type : list[Pirate]"""
        self.dead_pirates = []  # pirates that are currently dead
        """:type : list[Pirate]"""
        self.drunk_pirates = []  # pirates that are currently drunk
        """:type : list[Pirate]"""
        self.all_pirates = []  # all pirates that have been created
        """:type : list[Pirate]"""

    def get_living_pirate(self, pirate_id):
        """
        This function returns a living pirate by pirate id. Or None if no pirate is found.

        :param pirate_id: The id of the pirate.
        :type pirate_id: int
        :return: The found pirate or None if no pirate is found.
        :rtype: Pirate
        """
        for pirate in self.living_pirates:
            if pirate.id == pirate_id:
                return pirate
        return None

    def remove_living_pirate(self, pirate_id):
        """
        This function removes and returns a living pirate by pirate id. Or None if no pirate is found.

        :param pirate_id: The id of the pirate.
        :type pirate_id: int
        :return: The found pirate or None if no pirate is found.
        :rtype: Pirate
        """
        for index, pirate in enumerate(self.living_pirates):
            if pirate.id == pirate_id:
                return self.living_pirates.pop(index)

    def kill_player(self):
        """
        Kills the player

        """
        self.is_killed = True

    @property
    def is_alive(self):
        """
        Gets whether the player is alive

        """
        return not self.is_killed and bool(self.all_pirates)

    def __str__(self):
        """
        Returns a string describing the player

        :return: a string describing the player
        :rtype: str
        """
        return '(%s, %s, %s, %s, %s)' % (self.id, self.bot_name, self.score, self.num_scripts,
                                         ''.join(str(self.orders)))
