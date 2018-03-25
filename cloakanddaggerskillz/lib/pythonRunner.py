# !/usr/bin/env python
"""
The runner module. Used to run python bots.
"""
import sys
import traceback
import random
import base64
import time
import os
import imp
from PirateClass import BasePirate
from MapObject import MapObject
from LocationClass import Location

import json  # Used for serializing the data communication.

DEFAULT_BOT_FILE = 'my_bot.py'

ME = 0

AIM = {'n': Location(-1, 0),
       'e': Location(0, 1),
       's': Location(1, 0),
       'w': Location(0, -1),
       '-': Location(0, 0)}


def format_data(data, prettify=False):
    """
    This function formats the data to send using json.
    --Warning--
    Tuples will be turned into lists by the json.

    :param data: The data to format using Json.
    :type data: list or tuple or int or str or dict
    :param prettify: Whether or not to format the data prettily, default is False.
    :type prettify: bool
    :return: The formatted data.
    :rtype: str
    """
    if prettify:
        return json.dumps(data, indent=4, sort_keys=True) + '\n'
    else:
        data_str = json.dumps(data)
        return data_str + '\n'


def parse_data(data_str):
    """
    This turns the received data into a dictionary or list using json.
    --Warning--
    Tuples will be turned into lists in the json data.

    :param data_str: The input data to un format.
    :type data_str: str
    :return: A json dictionary of the data. Or an empty dictionary if none was received.
    :rtype: dict
    """
    # Json data might be incorrect so try and catch is used.
    try:
        return json.loads(data_str)
    except (ValueError, TypeError):
        return dict()


def sort_by_id(list_to_sort):
    """
    Sorts a list of objects by the objects' id.

    :param list_to_sort: the list to sort
    :type list_to_sort: list[object]
    :return: the sorted list
    :rtype: list[object]
    """
    return sorted(list_to_sort, key=lambda x: x.id)


class Pirates(object):
    """
    The pirates game class, this holds all of the game data and basic API for the bots.
    """
    def __init__(self):
        # generic game settings
        self.turn_time = 0
        """:type : int"""
        self.load_time = 0
        """:type : int"""
        self.turn_start_time = None
        """:type : float"""
        self.num_players = 0
        """:type : int"""
        self.max_turns = 0
        """:type : int"""
        self.max_points = 0
        """:type : int"""
        self.actions_per_turn = 0
        """:type : int"""
        self.turn = 0
        """:type : int"""
        self.cyclic = True
        """:type : bool"""
        self._recover_errors = True
        """:type : bool"""

        # random settings
        self.player_seed = 0
        """:type : int"""
        self.randomize_sail_options = False  # don't randomize
        """:type : bool"""

        # map attributes
        self.cols = None
        """:type : int"""
        self.rows = None
        """:type : int"""

        # map objects
        self.all_treasures = []
        """:type : list[Treasure]"""
        self.all_pirates = []
        """:type : list[Pirate]"""

        # attack and defense settings
        self.attack_radius2 = 0
        """:type : int"""
        self.reload_turns = 0
        """:type : int"""
        self.defense_reload_turns = 0
        """:type : int"""
        self.max_defense_turns = 0
        """:type : int"""
        self.turns_to_sober = 0
        """:type : int"""

        # scripts and bermuda zones settings
        self.bermuda_zone_active_turns = 0
        """:type : int"""
        self.required_scripts_num = 0
        """:type : int"""
        self._num_scripts = []
        """:type : list[int]"""

        # other settings
        self.treasure_spawn_turns = 2000
        """:type : int"""
        self.spawn_turns = 0
        """:type : int"""
        self.directions = AIM.keys()
        """:type : list[str]"""

        # player stats
        self._scores = []
        """:type : list[int]"""
        self._last_turn_points = []
        """:type : list[int]"""
        self._bot_names = []
        """:type : list[str]"""
        self.ME = ME
        """:type : int"""
        # this is only true for 1 vs 1
        self.ENEMY = 1
        """:type : int"""
        self.NEUTRAL = None
        """:type : None"""

        # The orders the bot wants to run.
        self._orders = []
        """:type : list[dict[str, any]]"""
        # The debug messages the bot wants to send.
        self._debug_messages = []
        """:type : list[dict[str, str]]"""

        # Remember if the runner has been initiated yet.
        self.initiated = False
        """:type : bool"""

    def __setup(self, data):
        """
        This method parses the initial setup starting game consts and data.

        :param data: The data to initiate from, should be data dictionary from the engine.
        :type data: dict[str, object]
        """
        conversion_dictionary = {
            'cols': 'cols',
            'rows': 'rows',
            'player_seed': 'player_seed',
            'cyclic': 'cyclic',
            'spawn_turns': 'spawn_turns',
            'turns_to_sober': 'turns_to_sober',
            'turn_time': 'turn_time',
            'load_time': 'load_time',
            'attack_radius2': 'attack_radius2',
            'bermuda_zone_active_turns': 'bermuda_zone_active_turns',
            'required_scripts_num': 'required_scripts_num',
            'max_turns': 'max_turns',
            'max_points': 'max_points',
            'randomize_sail_options': 'randomize_sail_options',
            'actions_per_turn': 'actions_per_turn',
            'reload_turns': 'reload_turns',
            'defense_reload_turns': 'defense_reload_turns',
            'max_defense_turns': 'max_defense_turns',
            'treasure_spawn_turns': 'treasure_spawn_turns',
            'turn': 'turn',
            'num_players': 'num_players',
            'initial_scores': '_scores',
            'last_turn_scores': '_last_turn_points',
            'num_of_scripts': '_num_scripts',
            'bot_names': '_bot_names',
            'recover_errors': '_recover_errors'
        }
        # Check that no data is missing from the input data.
        for key, value in conversion_dictionary.iteritems():
            if key not in data.keys():
                raise ValueError('Missing key {key} from json dict.'.format(key=key))
            if not hasattr(self, value):
                raise ValueError('Missing key {key} from self.'.format(key=value))

        for key, value in data.iteritems():
            setattr(self, conversion_dictionary[key], value)
        random.seed(self.player_seed)

        # Make sure the runner knows it has been initiated.
        self.initiated = True

    def __update(self, data):
        """
        This method updates the state of the game objects.

        :param data: The data to update from, should be data dictionary from the engine.
        :type data: dict[str, any]
        """
        # start timer
        self.turn_start_time = time.time()

        expected = ['game_scores',
                    'last_turn_points',
                    'num_of_scripts',
                    'treasures',
                    'bermuda_zones',
                    'powerups',
                    'scripts',
                    'anti_scripts',
                    'pirates',
                    'dead_pirates',
                    'players'
                    ]

        # Check that all expected keys are here.
        for expected_key in expected:
            if expected_key not in data.keys():
                raise ValueError('Expected key {key} missing from json data dictionary.'.format(key=expected_key))

        self.all_pirates = []
        self.all_treasures = []
        self.all_powerups = []
        self.all_scripts = []
        self.all_anti_scripts = []
        self.all_bermuda_zones = []
        self._sorted_my_pirates = []
        self._sorted_enemy_pirates = []
        self._orders = []
        self._debug_messages = []
        self.turn += 1
        # update map and create new pirate/treasure lists
        for key, value in data.iteritems():
            if key == 'game_scores':
                self._scores = value
            elif key == 'last_turn_points':
                self._last_turn_points = value
            elif key == 'num_of_scripts':
                self._num_scripts = value
            elif key == 'treasures':
                for treasure in value:
                    treasure_id = treasure['id']
                    initial_location = Location(*treasure['initial_location'])
                    value = treasure['value']
                    self.all_treasures.append(Treasure(treasure_id, initial_location, value))
            elif key == 'bermuda_zones':
                for zone in value:
                    center = Location(*zone['center'])
                    radius = zone['radius']
                    owner = zone['owner']
                    remaining_turns = zone['active_turns']
                    self.all_bermuda_zones.append(BermudaZone(center, radius, owner, remaining_turns))
            elif key == 'powerups':
                for powerup in value:
                    powerup_id = powerup['id']
                    powerup_type = powerup['powerup_type']
                    location = Location(*powerup['location'])
                    active_turns = powerup['active_turns']
                    end_turn = powerup['end_turn']
                    value = powerup['value']
                    if powerup_type == "RobPowerup":
                        self.all_powerups.append(RobPowerup(powerup_id, location, active_turns, end_turn))
                    elif powerup_type == "SpeedPowerup":
                        self.all_powerups.append(SpeedPowerup(powerup_id, location, active_turns, end_turn, value))
                    elif powerup_type == "AttackPowerup":
                        self.all_powerups.append(AttackPowerup(powerup_id, location, active_turns, end_turn, value))
                    else:
                        raise TypeError('Unknown powerup type: {type}'.format(type=powerup_type))
            elif key == 'scripts':
                for script in value:
                    script_id = script['id']
                    location = Location(*script['location'])
                    end_turn = script['end_turn']
                    self.all_scripts.append(Script(script_id, location, end_turn))
            elif key == 'anti_scripts':
                for anti_script in value:
                    anti_script_id = anti_script['id']
                    location = Location(*anti_script['location'])
                    end_turn = anti_script['end_turn']
                    self.all_anti_scripts.append(Script(anti_script_id, location, end_turn))
            elif key == 'pirates':
                for pirate in value:
                    pirate_id = pirate['id']
                    location = Location(*pirate['location'])
                    owner = pirate['owner']
                    initial_location = Location(*pirate['initial_location'])
                    attack_radius = pirate['attack_radius']
                    # TODO: make owner into a player object, from int
                    pirate_object = Pirate(location, owner, pirate_id, self.actions_per_turn, initial_location,
                                           attack_radius)

                    pirate_object.turns_to_sober = pirate['turns_to_sober']
                    pirate_object.reload_turns = pirate['reload_turns']
                    pirate_object.defense_reload_turns = pirate['defense_reload_turns']
                    pirate_object.defense_expiration_turns = pirate['defense_expiration_turns']
                    pirate_object.carry_treasure_speed = pirate['carry_treasure_speed']
                    pirate_object.attack_radius = pirate['attack_radius']
                    pirate_object.powerups = pirate['powerups']

                    treasure_id = pirate['treasure_id']
                    if treasure_id != -1:
                        treasure_initial_location = Location(*pirate['treasure_initial_location'])
                        treasure_value = pirate['treasure_value']
                        treasure = Treasure(treasure_id, treasure_initial_location, treasure_value)
                        pirate_object.treasure = treasure

                    self.all_pirates.append(pirate_object)

            elif key == 'dead_pirates':
                for dead_pirate in value:
                    pirate_id = dead_pirate['id']
                    location = Location(*dead_pirate['location'])
                    owner = dead_pirate['owner']
                    initial_location = Location(*dead_pirate['initial_location'])
                    attack_radius = dead_pirate['attack_radius']
                    pirate_object = Pirate(location, owner, pirate_id, self.actions_per_turn, initial_location,
                                           attack_radius)
                    pirate_object.turns_to_revive = dead_pirate['turns_to_revive']
                    pirate_object.is_lost = True

                    self.all_pirates.append(pirate_object)

            elif key == 'players':
                pass
            
            else:
                raise ValueError('Unrecognized key in the json dict.')

        # create main helper members which are lists sorted by IDs
        self._sorted_my_pirates = sort_by_id([pirate for pirate in self.all_pirates
                                              if pirate.owner == ME])
        self._sorted_enemy_pirates = sort_by_id([pirate for pirate in self.all_pirates
                                                if pirate.owner != ME])

    def __get_directions(self, loc1, loc2):
        """
        Determines the fastest (closest) directions to reach a destination from a given location
        This method will work for locations or instances with location members

        :param loc1: the source location
        :type loc1: Location
        :param loc2: the destination
        :type loc2: Location
        :return: the fastest directions from loc1 to loc2, the directions are a string containing  'n','s','e','w' only
        :rtype: list[str]
        """

        row1, col1 = self.get_location(loc1).as_tuple
        row2, col2 = self.get_location(loc2).as_tuple
        half_map_height = self.rows//2
        half_map_width = self.cols//2
        distance = self.distance(loc1, loc2)

        if row1 == row2 and col1 == col2:
            # return a single move of 'do nothing'
            return ['-']

        directions = []
        for i in range(distance):
            if row1 < row2:
                if row2 - row1 >= half_map_height and self.cyclic:
                    directions.append('n')
                    row1 -= 1
                    continue
                if row2 - row1 <= half_map_height or not self.cyclic:
                    directions.append('s')
                    row1 += 1
                    continue
            if row2 < row1:
                if row1 - row2 >= half_map_height and self.cyclic:
                    directions.append('s')
                    row1 += 1
                    continue
                if row1 - row2 <= half_map_height or not self.cyclic:
                    directions.append('n')
                    row1 -= 1
                    continue
            if col1 < col2:
                if col2 - col1 >= half_map_width and self.cyclic:
                    directions.append('w')
                    col1 -= 1
                    continue
                if col2 - col1 <= half_map_width or not self.cyclic:
                    directions.append('e')
                    col1 += 1
                    continue
            if col2 < col1:
                if col1 - col2 >= half_map_width and self.cyclic:
                    directions.append('e')
                    col1 += 1
                    continue
                if col1 - col2 <= half_map_width or not self.cyclic:
                    directions.append('w')
                    col1 -= 1
                    continue
        if self.randomize_sail_options:
            random.shuffle(directions)
        return directions

    ''' Treasure related API '''
    def treasures(self):
        """
        Returns a list of all the treasures in the game

        :return: list of all the treasures in the game
        :rtype: list[Treasure]
        """
        return [treasure for treasure in self.all_treasures]

    ''' Pirate related API '''

    def all_my_pirates(self):
        """
        Returns a list of all friendly pirates

        :return: list of all my pirates sorted by ID
        :rtype: list[Pirate]
        """
        return self._sorted_my_pirates

    def my_living_pirates(self):
        """
        Returns a list of all friendly pirates that are currently in the game (on screen)

        :return: list of all friendly pirates that are currently in the game
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.all_my_pirates() if not pirate.is_lost]

    def my_pirates_with_treasures(self):
        """
        Returns a list of all friendly pirates that carry treasure

        :return: list of all friendly pirates that carry treasure
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.my_living_pirates() if pirate.has_treasure()]

    def my_pirates_without_treasures(self):
        """
        Returns a list of all friendly pirates that are currently in the game (on screen) and not carry treasure

        :return: list of all friendly pirates that not carry treasure
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.my_living_pirates() if not pirate.has_treasure()]

    def my_drunk_pirates(self):
        """
        Returns a list of all friendly drunk pirates

        :return: list of all friendly drunk pirates
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.my_living_pirates() if pirate.turns_to_sober > 0]

    def my_sober_pirates(self):
        """
        Returns a list of all friendly non-drunk pirates that are currently in the game (on screen)

        :return: list of all friendly non-drunk pirates
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.my_living_pirates() if pirate.turns_to_sober <= 0]

    def my_lost_pirates(self):
        """
        Returns a list of all friendly pirates that are currently out of the game (lost)

        :return: list of all friendly pirates that are currently out of the game (lost)
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.all_my_pirates() if pirate.is_lost]

    def all_enemy_pirates(self):
        """
        Returns a list of all enemy pirates

        :return: list of all enemy pirates sorted by ID
        :rtype: list[Pirate]
        """
        return self._sorted_enemy_pirates

    def enemy_living_pirates(self):
        """
        Returns a list of all enemy pirates that are currently in the game (on screen)

        :return: list of all enemy pirates that are currently in the game
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.all_enemy_pirates() if not pirate.is_lost]

    def enemy_lost_pirates(self):
        """
        Returns a list of all enemy pirates that are currently out of the game (lost)

        :return: list of all enemy pirates that are currently out of the game (lost)
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.all_enemy_pirates() if pirate.is_lost]

    def enemy_pirates_with_treasures(self):
        """
        Returns a list of all enemy pirates that carry treasure

        :return: list of all enemy pirates that carry treasure
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.enemy_living_pirates() if pirate.has_treasure()]

    def enemy_pirates_without_treasures(self):
        """
        Returns a list of all enemy pirates that are currently in the game (on screen) and not carry treasure

        :return: list of all enemy pirates that not carry treasure
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.enemy_living_pirates() if not pirate.has_treasure()]

    def enemy_drunk_pirates(self):
        """
        Returns a list of all enemy drunk pirates

        :return: list of all enemy drunk pirates
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.enemy_living_pirates() if pirate.turns_to_sober > 0]

    def enemy_sober_pirates(self):
        """
        Returns a list of all enemy non-drunk pirates that are currently in the game (on screen)

        :return: list of all enemy non-drunk pirates
        :rtype: list[Pirate]
        """
        return [pirate for pirate in self.enemy_living_pirates() if pirate.turns_to_sober <= 0]

    def get_my_pirate(self, pirate_id):
        """
        Returns a friendly pirate by id

        :param pirate_id: the id of the pirate
        :type pirate_id: int
        :return: the friendly pirate that has the given id
        :rtype: Pirate
        """
        if pirate_id < 0 or pirate_id >= len(self.all_my_pirates()):
            return None
        return self.all_my_pirates()[pirate_id]

    def get_enemy_pirate(self, pirate_id):
        """
        Returns an enemy pirate by id

        :param pirate_id: the id of the pirate
        :type pirate_id: int
        :return: the enemy pirate that has the given id
        :rtype: Pirate
        """
        if pirate_id < 0 or pirate_id >= len(self.all_enemy_pirates()):
            return None
        return self.all_enemy_pirates()[pirate_id]

    def get_pirate_on(self, obj):
        """
        Returns the pirate on the given location, or None if there isn't one

        :param obj: the given location. it may be tuple or an object with 'location' attribute
        :type obj: Location | object
        :return: the pirate on the given location
        :rtype: Pirate
        """
        # this will return an pirate or None if no pirate in that location
        location = self.get_location(obj)
        return next((pirate for pirate in self.all_pirates if pirate.location == location), None)

    ''' Powerup API '''

    def powerups(self):
        """
        Returns a list of all the powerups that are currently on the map

        :return: list of all the powerups that are currently on the map
        :rtype: list[Powerup]
        """
        return self.all_powerups

    ''' Scripts API '''

    def scripts(self):
        """
        Returns a list of all the scripts that are currently on the map

        :return: list of all the scripts that are currently on the map
        :rtype: list[Script]
        """
        return self.all_scripts

    def get_my_scripts_num(self):
        """
        Returns the number of my scripts

        :return: number of my scripts
        :rtype: int
        """
        return self._num_scripts[self.ME]

    def get_enemy_scripts_num(self):
        """
        Returns the number of enemy scripts

        :return: number of enemy scripts
        :rtype: int
        """
        return self._num_scripts[self.ENEMY]

    ''' Bermuda Zone API '''

    def get_my_bermuda_zone(self):
        """
        Returns my bermuda zone

        :return: my bermuda zone
        :rtype: BermudaZone
        """
        return next((bermuda_zone for bermuda_zone in self.all_bermuda_zones if bermuda_zone.owner == self.ME), None)

    def get_enemy_bermuda_zone(self):
        """
        Returns enemy bermuda zone

        :return: enemy bermuda zone
        :rtype: BermudaZone
        """
        return next((bermuda_zone for bermuda_zone in self.all_bermuda_zones if bermuda_zone.owner == self.ENEMY), None)

    def summon_bermuda_zone(self, pirate):
        """
        Summons bermuda zone with the given pirate

        :param pirate: the pirate that summons the bermuda zone
        :type pirate: Pirate
        """
        self._orders.append({'type': 'order', 'order_type': 'bermuda', 'acting_pirate': pirate.id, 'order_args': {}})

    def in_enemy_bermuda_zone(self, location):
        """
        Checks if a given location is in enemy bermuda zone

        :param location: the location to check
        :type location: Location
        :return: True if the location is in enemy bermuda zone, otherwise False
        :rtype: bool
        """
        enemy_zone = self.get_enemy_bermuda_zone()
        if enemy_zone is None:
            return False
        square_distance = (enemy_zone.center.row - location.row) ** 2 + (enemy_zone.center.col - location.col) ** 2
        return square_distance <= enemy_zone.radius

    ''' Action API '''

    def get_sail_options(self, pirate, destination, moves):
        """
        Returns the different locations options for a given pirate to get as close as it can to a given destination
        with a given number of steps

        :param pirate: the pirate to go to the destination
        :type pirate: Pirate
        :param destination: the destination for the pirate to go to. Must be either a location, or an object with
        location attribute
        :type destination: Location | object
        :param moves: the number of moves the pirate will use
        :type moves: int
        :return: list of locations that will get the pirate as close as it can to the destination
        :rtype: list[Location]
        """
        error_string = "moves must be non negative!"
        assert(moves >= 0), error_string
        if pirate.location == self.get_location(destination):
            return [pirate.location]
        directions = self.__get_directions(pirate.location, self.get_location(destination))

        set_of_directions = []
        for direction in directions:
            if direction not in set_of_directions:
                set_of_directions.append(direction)

        pivot = directions.index(set_of_directions[-1])

        first_distance = pivot - moves if pivot - moves > 0 else 0
        second_distance = pivot + moves if pivot + moves < len(directions) else len(directions)
        optional_direction = directions[first_distance:second_distance]

        if len(optional_direction) < moves:
            sail_options = [self.destination(pirate, optional_direction)]
        else:
            sail_options = [self.destination(pirate, optional_direction[i:moves+i]) for i in
                            xrange(len(optional_direction) - moves + 1)]

        if self.randomize_sail_options:
            random.shuffle(sail_options)

        return sail_options

    def set_sail(self, pirate, destination):
        """
        Moves a given pirate to the given destination

        :param pirate: the pirate to move to the destination
        :type pirate: Pirate
        :param destination: the location to move the pirate to
        :type destination: Location
        """
        # already in destination
        if pirate.location == destination:
            self.debug("WARNING: Pirate %d tried to set sail to its current location.", pirate.id)
            return
        self._orders.append({'type': 'order', 'order_type': 'move', 'acting_pirate': pirate.id,
                             'order_args': {'destination': destination.as_tuple}})

    def attack(self, pirate, target):
        """
        Orders a given pirate to attack a given target

        :param pirate: the pirate that will attack
        :type pirate: Pirate
        :param target: the pirate that will be attacked
        :type target: Pirate
        """
        error_string = "pirate cannot attack a teammate"
        assert(pirate.owner != target.owner), error_string
        self._orders.append({'type': 'order', 'order_type': 'attack', 'acting_pirate': pirate.id,
                            'order_args': {'target': target.id}})

    def defend(self, pirate):
        """
        Orders a given pirate to defend itself.

        :param pirate: the pirate that will defend
        :type pirate: Pirate
        """
        self._orders.append({'type': 'order', 'order_type': 'defense', 'acting_pirate': pirate.id,
                            'order_args': {}})

    ''' Primary helper API '''

    def distance(self, loc1, loc2):
        """
        Calculate the closest distance between two locations

        :param loc1: a location, it may be tuple or an object with 'location' attribute
        :type loc1: Location | object
        :param loc2: a location, it may be tuple or an object with 'location' attribute
        :type loc2: Location | object
        :return: the distance between the two locations
        :rtype: int
        """
        ''
        row1, col1 = self.get_location(loc1).as_tuple
        row2, col2 = self.get_location(loc2).as_tuple

        if not self.cyclic:
            d_col = abs(col1 - col2)
            d_row = abs(row1 - row2)
        else:
            d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
            d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def destination(self, pirate, directions):
        """
        Calculates the new location a pirate will be in after moving in a given directions

        :param pirate: the pirate that will move
        :type pirate: Pirate
        :param directions: the directions that the pirate will move in
        :type directions: list[str]
        :return: the location the pirate will be in after moving in the given directions
        :rtype: Location
        """
        row, col = self.get_location(pirate).as_tuple
        for direction in directions:
            d_row, d_col = AIM[direction].as_tuple
            if self.cyclic:
                row, col = ((row + d_row) % self.rows, (col + d_col) % self.cols)
            else:
                row, col = ((row + d_row), (col + d_col))
        return Location(row, col)

    def in_range(self, obj1, obj2):
        """
        Checks if two objects or locations are in attack range.

        :param obj1: a location, it may be tuple or an object with 'location' attribute
        :type obj1: Location | object
        :param obj2: a location, it may be tuple or an object with 'location' attribute
        :type obj2: Location | object
        :return: True if the two objects or locations are in attack range, otherwise False
        :rtype: bool
        """
        loc1 = self.get_location(obj1)
        loc2 = self.get_location(obj2)
        row_distance, col_distance = loc1.row-loc2.row, loc1.col-loc2.col
        distance_squared = row_distance**2 + col_distance**2
        if 0 < distance_squared <= self.attack_radius2:
            return True
        return False

    ''' Debug related API '''

    def debug(self, *args):
        """
        Debugs a message

        :param args: the message
        :type args: str | string format
        """
        if len(args) == 0:
            return
        message = args[0]
        if len(args) > 1:
            message = args[0] % args[1:]
        # encode to base64 to avoid people printing weird stuff.
        self._debug_messages.append({'type': 'message', 'message': base64.b64encode(message)})

    ''' MetaGame API '''

    def get_scores(self):
        """
        Returns game scores to the client-side such that it is ordered - first score is his

        :return: the game scores
        :rtype: list[int]
        """
        return self._scores

    def get_my_score(self):
        """
        Returns my score

        :return: my score
        :rtype: int
        """
        return self._scores[self.ME]

    def get_enemy_score(self):
        """
        Returns enemy score

        :return: enemy score
        :rtype: int
        """
        return self._scores[self.ENEMY]

    def get_last_turn_points(self):
        """
        Returns the scores the players goal in the last turn.
        This list is ordered so that first place is the current player and the next is the enemy.

        :return: the scores the players goal in the last turn
        :rtype: list[int]
        """
        return self._last_turn_points

    def get_turn(self):
        """
        Returns the current turn number

        :return: the current turn number
        :rtype: int
        """
        return self.turn

    def get_max_turns(self):
        """
        Returns the maximum number of turns in this game

        :return: the maximum number of turns in this game
        :rtype: int
        """
        return self.max_turns

    def get_max_points(self):
        """
        Returns number of points needed to end the game

        :return: number of points needed to end the game
        :rtype: int
        """
        return self.max_points

    def get_attack_radius(self):
        """
        Returns the attack radius squared

        :return: the attack radius squared
        :rtype: int
        """
        return self.attack_radius2

    def get_bermuda_zone_active_turns(self):
        """
        Returns the number of turns a bermuda zone remains active after activating

        :return: number of turns a bermuda zone remains active
        :rtype: int
        """
        return self.bermuda_zone_active_turns

    def get_required_scripts_num(self):
        """
        Returns the number of needed scripts in order to activate bermuda zone

        :return: the number of needed scripts in order to activate bermuda zone
        :rtype: int
        """
        return self.required_scripts_num

    def get_reload_turns(self):
        """
        Returns the number of reload turns after attack (until a pirate can attack again)

        :return: the number of reload turns after attack
        :rtype: int
        """
        return self.reload_turns

    def get_defense_reload_turns(self):
        """
        Returns the number of reload turns after defend (until a pirate can defend again)

        :return: the number of reload turns after defend
        :rtype: int
        """
        return self.defense_reload_turns

    def get_actions_per_turn(self):
        """
        Returns the number of moves a player can commit in a single turn

        :return: the number of moves a player can commit in a single turn
        :rtype: int
        """
        return self.actions_per_turn

    def get_spawn_turns(self):
        """
        Returns the number of turns it takes a pirate to respawn after it died

        :return: the number of turns it takes a pirate to respawn
        :rtype: int
        """
        return self.spawn_turns

    def get_turns_to_sober(self):
        """
        Returns the number of turns a pirate is drunk after it's attacked

        :return: the number of turns a pirate is drunk after it's attacked
        :rtype: int
        """
        return self.turns_to_sober

    def get_max_defense_turns(self):
        """
        Returns the number of turns a pirate is protected after defending

        :return: the number of turns a pirate is protected after defending
        :rtype: int
        """
        return self.max_defense_turns

    def time_remaining(self):
        """
        Returns the remaining time until the bot times out

        :return: the remaining time until the bot times out
        :rtype: int
        """
        return ((self.turn == 1) * 9 + 1) * self.turn_time - int(1000 * (time.time() - self.turn_start_time))

    def get_opponent_name(self):
        """
        Returns the opponent's name

        :return: the opponent's name
        :rtype: str
        """
        return self._bot_names[self.ENEMY]

    ''' Terrain API '''

    def is_occupied(self, loc):
        """
        Checks if a given location is occupied by a pirate

        :param loc: the location to check
        :type loc: Location
        :return: True if the location is occupied, otherwise false
        :rtype: bool
        """
        return loc in [pirate.location for pirate in self.all_pirates if not pirate.is_lost]

    def get_rows(self):
        """
        Returns the number of rows in the board

        :return: the number of rows
        :rtype: int
        """
        return self.rows

    def get_cols(self):
        """
        Returns the number of cols in the board

        :return: the number of cols
        :rtype: int
        """
        return self.cols

    def stop_point(self, message):
        """
        Sends a stop-point to the visualizer with the given message.
        :param message: the message to be write
        :type message: str
        """
        self._debug_messages.append({'type': 'stop', 'message': base64.b64encode(message)})

    ''' Inner API functions '''

    @staticmethod
    def get_location(obj):
        """
        Gets the location of a given object. Raises a TypeError if the object doesn't have a location attribute

        :param obj: the object to get the location from. It may be an object with a 'location' member or a tuple
        :type obj: any
        :return: the location of the given object
        :rtype: Location
        """
        if hasattr(obj, 'location'):
            return obj.location
        elif isinstance(obj, Location):
            return obj
        # The object isn't a location, or doesn't have a location property
        # TODO: should this raise an exception?
        raise TypeError(str(obj) + ' ' + str(type(obj)))

    def get_anti_scripts(self):
        """
        Returns all the anti-scripts in the game

        :return: all the anti-scripts in the game
        :rtype: list[Script]
        """
        return self.all_anti_scripts


    def __finish_turn(self, debug_only=False):
        """
        This method returns the wanted orders to the engine after formatting them.

        :param debug_only: Whether to send only debug messages or all orders. Use this to send only debug messages in
        the case of an exception.
        :type debug_only: bool
        """
        orders_to_send = self._orders
        if debug_only:
            orders_to_send = []
        messages_to_send = self._debug_messages
        sys.stdout.write(format_data({'type': 'bot_orders', 'data': {'orders': orders_to_send,
                                                                     'debug_messages': messages_to_send}}))
        sys.stdout.flush()

    @staticmethod
    def create_location(row, col):
        """
        Creates a location from the given row, col

        :param row: the row of the location
        :type row: int
        :param col: the col of the location
        :type col: int
        :return: the new location
        :rtype: Location
        """
        return Location(row, col)

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        """
        Parses input, updates game state and calls the bot classes do_turn method

        :param bot: the bot to call do_turn on
        :type bot: BotController
        """
        pirates = Pirates()
        while True:
            received_data = parse_data(sys.stdin.readline())  # string new line char
            try:
                if not received_data:
                    break
                if 'type' not in received_data.keys():
                    raise TypeError('Missing type parameter from json dictionary.')
                if 'data' not in received_data.keys():
                    raise TypeError('Missing data parameter from json dictionary.')

                if received_data['type'] == 'setup':
                    pirates.__setup(received_data['data'])
                elif received_data['type'] == 'turn':
                    # Make sure the runner has been initiated correctly.
                    if not pirates.initiated:
                        raise Exception('Attempt to run runner without initiating it first.')

                    pirates.__update(received_data['data'])
                    # call the do_turn method of the class passed in
                    if pirates._recover_errors:
                        try:
                            bot.do_turn(pirates)
                        except:
                            error_msg = "Exception occurred during do_turn: \n" + traceback.format_exc()
                            pirates.debug(error_msg)
                    else:
                        bot.do_turn(pirates)
                else:
                    raise ValueError('Unrecognized json dictionary type, {type}.'.format(type=received_data['type']))
                pirates.__finish_turn()
            except KeyboardInterrupt:
                raise


class Pirate(BasePirate):
    """
    The Pirate class. Pirates are controlled by the players.
    """
    def __repr__(self):
        return "<Pirate ID:%d Owner:%s Loc:%s>" % (self.id, self.owner, self.location.as_tuple)

    def __hash__(self):
        return self.id * 10 + self.owner


class Powerup(MapObject):
    """
    The Powerup class. Powerups make the pirate who picks them up stronger for a while.
    """
    def __init__(self, powerup_id, powerup_type, location, active_turns, end_turn):
        super(Powerup, self).__init__()

        self.id = powerup_id
        """:type : int"""
        self.type = powerup_type
        """:type : str"""
        self.location = location
        """:type : Location"""
        self.active_turns = active_turns
        """:type : int"""
        self.end_turn = end_turn
        """:type : int"""

    def __repr__(self):
        return "<Powerup Location:%s>" % self.location.as_tuple

    def get_location(self):
        """
        Gets the powerup's location

        :return: the powerup's location
        :rtype: Location
        """
        return self.location


class RobPowerup(Powerup):
    """
    The RobPowerup allows the pirate who picks it to take treasures from other pirates by attacking the.
    """
    def __init__(self, powerup_id, location, end_turn, active_turns):
        Powerup.__init__(self, powerup_id, "Rob", location, end_turn, active_turns)


class SpeedPowerup(Powerup):
    """
    The SpeedPowerup allows a pirate to take more steps while carrying a treasure
    """
    def __init__(self, powerup_id, location, end_turn, active_turns, carry_treasure_speed):
        Powerup.__init__(self, powerup_id, "Speed", location, end_turn, active_turns)
        self.carry_treasure_speed = carry_treasure_speed
        """:type : int"""


class AttackPowerup(Powerup):
    """
    The AttackPowerup allows a pirate to attack without reloading, and increases its attack radius
    """
    def __init__(self, powerup_id, location, end_turn, active_turns, attack_radius):
        Powerup.__init__(self, powerup_id, "Attack", location, end_turn, active_turns)
        self.attack_radius = attack_radius
        """:type : int"""


class Script(MapObject):
    """
    The Scripts are collected in order to summon a deadly Bermuda Zone
    """
    def __init__(self, script_id, loc, end_turn):
        super(Script, self).__init__()

        self.id = script_id
        """:type : int"""
        self.location = loc
        """:type : Location"""
        self.end_turn = end_turn
        """:type : int"""

    def __repr__(self):
        return "<Script ID:%d, Location:%s>" % (self.id, self.location.as_tuple)

    def get_location(self):
        """
        gets the script's location

        :return: the script's location
        :rtype: Location
        """
        return self.location


class Treasure(MapObject):
    """
    The Treasures are collected in order to gain points and win the game
    """
    def __init__(self, treasure_id, location, value, is_taken=False):
        """

        :param treasure_id: the treasure's id
        :type treasure_id: int
        :param location: the treasure's location
        :type location: Location
        :param value: the treasure's value
        :type value: int
        :param is_taken: whether or not the treasure is being carried by a pirate
        :type is_taken: bool
        """
        super(Treasure, self).__init__()

        self.id = treasure_id
        """:type : int"""
        self.location = location
        """:type : Location"""
        self.value = value
        """:type : int"""
        self.is_taken = is_taken
        """:type : bool"""

    def __cmp__(self, other):
        return type(other) is Treasure and self.__dict__ == other.__dict__

    def __eq__(self, other):
        return self.__cmp__(other)

    def __repr__(self):
        return "<Treasure ID:%d, location:%s, value:%d>" % (self.id, self.location.as_tuple, self.value)

    def get_location(self):
        """
        gets the treasure's location

        :return: the treasure's location
        :rtype: Location
        """
        return self.location


class BermudaZone(object):
    """
    The BermudaZone destroys all enemy pirates within it.
    """
    def __init__(self, center, radius, owner, remaining_turns):
        self.center = center
        """:type : Location"""
        self.radius = radius
        """:type : int"""
        self.owner = owner
        """:type : int"""
        self.remaining_turns = remaining_turns
        """:type : int"""


class BotController(object):
    """ Wrapper class for bot. May accept either a file or a directory and will add correct folder to path """
    def __init__(self, runner_bot_path):
        if runner_bot_path.endswith('.py'):
            file_directory, file_name = os.path.split(runner_bot_path)
            name, ext = os.path.splitext(file_name)

            module_file, file_name, description = imp.find_module(name, [file_directory])
            self.bot = imp.load_module('bot', module_file, file_name, description)
            """:type : module"""
            module_file.close()
        else:
            self.bot = imp.load_compiled('bot', runner_bot_path)
            """:type : module"""

    def do_turn(self, game):
        """
        Calls the main function in the bot.

        :param game: the game object to pass to the bot.
        :type game: Pirates
        """
        self.bot.do_turn(game)
        # Make sure no self collisions
        # game.cancel_collisions()


if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        psyco = None
        pass

    # try to initiate bot from file path or directory path
    try:
        try:
            # Check if we are on debug mode.
            debug_option = sys.argv[2]
            if debug_option == 'test_python_runner_json_communication_pipe_data_transfer':
                while True:
                    data_dict = parse_data(sys.stdin.readline())
                    if not data_dict:
                        continue
                    sys.stdout.write(format_data(data_dict))
                    sys.stdout.flush()
        except IndexError:
            pass

        # verify we got correct number of arguments
        try:
            file_path = sys.argv[1]
        except IndexError:
            sys.stderr.write('Usage: pythonRunner.py <bot_path or bot_directory>\n')
            sys.exit(-1)

        # add python to path and start the BotController
        if os.path.isdir(file_path):
            sys.path.append(file_path)
            bot_path = os.path.join(file_path, DEFAULT_BOT_FILE)
        else:
            sys.path.append(os.path.dirname(file_path))
            bot_path = file_path

        Pirates.run(BotController(bot_path))

    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
