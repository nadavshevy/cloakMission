"""
This is the main game file, holding practically all of the in-game logic and rules.
"""
# !/usr/bin/env python
from __future__ import print_function
from random import randint, seed
from collections import defaultdict

from MyExceptions import InvalidOrderFormatException, PirateAlreadyActedException, IgnoredOrderException, \
    InvalidOrderException, StepLimitExceededException
from PirateClass import BasePirate
from PlayerClass import BasePlayer
from MapObject import MapObject
from LocationClass import Location
from game import Game
MAX_RAND = 2147483647


PIRATES = 0
LAND = -1
TREASURE = -2

PIRATES_IN_MAP = 'abcdefghij'
MAP_OBJECTS = 'K$.'

MAP_RENDER = PIRATES_IN_MAP + MAP_OBJECTS

# possible directions an pirate can move
# TODO: Move this out to a .json file all runners, classes and such will read from instead of having it set in each one
AIM = {'n': Location(-1, 0),
       'e': Location(0, 1),
       's': Location(1, 0),
       'w': Location(0, -1),
       'a': Location(0, 0),
       'd': Location(0, 0),
       'f': Location(0, 0)}


class PiratesGame(Game):
    """
    The Pirates game object, holding the game state and handling its logic
    """
    def __init__(self, options=None):
        """
        Initiates the Pirates game

        :param options: a dictionary holding most of the game settings
        :type options: dict[str, any]
        """

        Game.__init__(self)

        # setup options
        map_text = options['map']
        map_data = self.parse_map(map_text)

        # override parameters with params we got from map
        for key, val in map_data['params'].items():
            # only get valid keys - keys that already exist
            if key in options:
                options[key] = val

        # Basic game settings, unrelated to the game logic itself
        self.max_turns = int(options['turns'])
        """:type : int"""
        self.max_points = int(options.get('max_points'))
        """:type : int"""
        self.load_time = int(options['load_time'])
        """:type : int"""
        self.turn_time = int(options['turn_time'])
        """:type : int"""
        self.recover_errors = int(options['recover_errors'])
        """:type : int"""
        self.cyclic = options.get('cyclic', False)
        """:type : bool"""
        self.init_turn = int(options.get('init_turn'))
        """:type : int"""
        self.turn = 0
        """:type : int"""
        self.num_players = map_data['num_players']
        """:type : int"""

        # Randomization settings
        self.randomize_sail_options = int(options.get('randomize_sail_options'))
        """:type : int"""
        self.engine_seed = options.get('engine_seed', randint(-MAX_RAND - 1, MAX_RAND))
        """:type : int"""
        seed(self.engine_seed)
        self.player_seed = options.get('player_seed', randint(-MAX_RAND - 1, MAX_RAND))
        """:type : int"""

        # Attack and Defense related settings
        self.attack_radius = int(options['attack_radius2'])
        """:type : int"""
        self.reload_turns = int(options.get('reload_turns'))
        """:type : int"""
        self.defense_reload_turns = int(options.get('defense_reload_turns'))
        """:type : int"""
        self.max_defense_turns = int(options.get('max_defense_turns'))
        """:type : int"""
        self.turns_to_sober = int(options.get('turns_to_sober'))
        """:type : int"""

        # Bermuda Zones and Scripts related settings
        self.bermuda_zone_radius = int(options['bermuda_zone_radius_2'])
        """:type : int"""
        self.bermuda_zone_active_turns = int(options['bermuda_zone_active_turns'])
        """:type : int"""
        self.required_scripts_num = int(options['required_scripts_num'])
        """:type : int"""

        # General Game settings
        self.actions_per_turn = int(options.get('actions_per_turn'))
        """:type : int"""
        self.pirate_spawn_turns = int(options.get('spawn_turns'))
        """:type : int"""
        self.treasure_spawn_turns = int(options.get('treasure_spawn_turns'))
        """:type : int"""

        # Game objects
        bot_names = options['bot_names']
        self.players = [Player(player_id, bot_names[player_id]) for player_id in range(self.num_players)]
        """:type : list[Player]"""
        self.treasures = []
        """:type : list[Treasure]"""
        self.powerups = []
        """:type : list[Powerup]"""
        self.scripts = []
        """:type : list[Script]"""
        self.anti_scripts = []
        """:type : list[Script]"""
        self.bermuda_zones = []
        """:type : list[BermudaZone]"""

        # used to cutoff games early
        self.end_of_game_reason = ''
        """:type : str"""

        # used to calculate the turn when the winner took the lead
        self.winning_bot = []
        """:type : list[int]"""
        self.winning_turn = 0
        """:type : int"""

        # used to calculate when the player rank last changed
        self.ranking_bots = None
        """:type : list[int]"""
        self.ranking_turn = 0
        """:type : int"""

        # cloak settings
        self.cloak_duration = int(options['cloak_duration'])
        """:type : int"""
        self.cloak_reload_turns = int(options['cloak_reload_turns'])
        """:type : int"""

        # initialize size of the map
        map_size = map_data['size']
        self.height = map_size[0]
        """:type : int"""
        self.width = map_size[1]
        """:type : int"""

        # initialize map
        self.map = dict()
        for row in xrange(0, self.height):
            for col in xrange(0, self.width):
                self.map[Location(row, col)] = LAND
        """:type : list[list[int]]"""

        bot_names = options['bot_names']
        self.players = [Player(player_id, bot_names[player_id])
                        for player_id in range(self.num_players)]
        # cache used by neighbourhood_offsets() to determine nearby squares
        self.offsets_cache = {}

        for treasure_data in map_data['treasures']:
            treasure_id = treasure_data[0]
            treasure_location = treasure_data[1]
            treasure_value = treasure_data[2]
            treasure = Treasure(treasure_id, treasure_location, treasure_value)
            self.treasures.append(treasure)

        # initialize powerups
        for powerup_id, powerup_data in enumerate(map_data['powerups']):
            powerup_type = powerup_data[0]
            powerup_location = Location(powerup_data[1], powerup_data[2])
            powerup_start_turn = powerup_data[3]
            powerup_end_turn = powerup_data[4]
            powerup_active_turns = powerup_data[5]

            if powerup_type == 'a':
                powerup_attack_radius = powerup_data[6]
                powerup = AttackPowerup(powerup_id, powerup_location, powerup_start_turn, powerup_end_turn,
                                        powerup_active_turns, powerup_attack_radius)
            elif powerup_type == 'r':
                powerup = RobPowerup(powerup_id, powerup_location, powerup_start_turn, powerup_end_turn,
                                     powerup_active_turns)
            elif powerup_type == 's':
                powerup_carry_treasure_speed = powerup_data[6]
                powerup = SpeedPowerup(powerup_id, powerup_location, powerup_start_turn, powerup_end_turn,
                                       powerup_active_turns, powerup_carry_treasure_speed)
            else:
                raise TypeError('Unknown powerup type')
            self.powerups.append(powerup)

        # initialize scripts
        for script_id, script_data in enumerate(map_data['scripts']):
            script_location = Location(script_data[0], script_data[1])
            script_start_turn = script_data[2]
            script_end_turn = script_data[3]
            script = Script(script_id, script_location, script_start_turn, script_end_turn)
            self.scripts.append(script)

        # initialize anti_scripts
        for anti_script_id, anti_script_data in enumerate(map_data['anti_scripts']):
            anti_script_location = Location(anti_script_data[0], anti_script_data[1])
            anti_script_start_turn = anti_script_data[2]
            anti_script_end_turn = anti_script_data[3]
            anti_script = Script(anti_script_id, anti_script_location, anti_script_start_turn, anti_script_end_turn)
            self.anti_scripts.append(anti_script)

        # initialize pirates
        for player_id, player_pirates in map_data['pirate_locations'].items():
            for pirate_id, pirate_loc in enumerate(player_pirates):
                self.add_initial_pirate(pirate_loc, player_id, pirate_id)

        # this is for the visualizer to display moves which didn't work for various reasons
        self.rejected_moves = []

        # used to give a different ordering of players to each player
        #  initialized to ensure that each player thinks they are player 0
        self.perspectives_key = []
        for player_id in range(self.num_players):
            self.perspectives_key.append([(key + self.num_players - player_id) % self.num_players for key in
                                          range(self.num_players)])

    @property
    def living_pirates(self):
        """
        Get the living_pirates list.

        :return: The living_pirates list.
        :rtype: list[Pirate]
        """
        living_pirates = []
        for player in self.players:
            for pirate in player.living_pirates:
                living_pirates.append(pirate)
        return living_pirates

    @property
    def dead_pirates(self):
        """
        Get the dead_pirates list.

        :return: The dead_pirates list.
        :rtype: list[Pirate]
        """
        dead_pirates = []
        for player in self.players:
            dead_pirates += player.dead_pirates
        return dead_pirates

    @property
    def drunk_pirates(self):
        """
        Get the drunk_pirates list.

        :return: The drunk_pirates  list.
        :rtype: list[Pirate]
        """
        drunk_pirates = []
        for player in self.players:
            drunk_pirates += player.drunk_pirates
        return drunk_pirates

    @property
    def all_pirates(self):
        """
        Get the all pirates list.

        :return: The all pirates list.
        :rtype: list[Pirate]
        """
        all_pirates = []
        for player in self.players:
            all_pirates += player.all_pirates
        return all_pirates

    @property
    def score(self):
        """
        Get the score list list.

        :return: The score list list.
        :rtype: list[int]
        """
        return [player.score for player in self.players]

    @property
    def score_history(self):
        """
        Get the score history list.

        :return: The score history list.
        :rtype: list[list[int]]
        """
        return [player.score_history for player in self.players]

    @property
    def bot_names(self):
        """
        Get the bot names list.

        :return: The bot names list.
        :rtype: list[str]
        """
        return [player.bot_name for player in self.players]

    @property
    def orders(self):
        """
        Get the orders list.

        :return: The orders list.
        :rtype: list[list[dict[str, any]]]
        """
        return [player.orders for player in self.players]

    @property
    def num_scripts(self):
        """
        Get the number of scripts list.

        :return: The number of scripts list.
        :rtype: list[int]
        """
        return [player.num_scripts for player in self.players]

    def euclidean_distance_squared(self, a_loc, b_loc):
        """
        This function returns the euclidean distance squared between location a and location b.

        :param a_loc: The first location.
        :type a_loc: Location
        :param b_loc: The second location.
        :type b_loc: Location
        :return: The squared euclidean distance between the two points.
        :rtype: int
        """
        d_row = abs(a_loc.row - b_loc.row)
        d_col = abs(a_loc.col - b_loc.col)
        if self.cyclic:
            d_row = min(d_row, self.height - d_row)
            d_col = min(d_col, self.width - d_col)
        return d_row ** 2 + d_col ** 2

    def manhattan_distance(self, a_loc, b_loc):
        """
        This function returns the manhattan distance between location a and location b.

        :param a_loc: The first location.
        :type a_loc: Location
        :param b_loc: The second location.
        :type b_loc: Location
        :return: The manhattan distance between the two points.
        :rtype: int
        """
        d_row = abs(a_loc.row - b_loc.row)
        d_col = abs(a_loc.col - b_loc.col)
        if self.cyclic:
            d_row = min(d_row, self.height - d_row)
            d_col = min(d_col, self.width - d_col)
        return d_row + d_col

    @staticmethod
    def parse_map(map_text):
        """
        Parses the map text into a more friendly data structure

        :param map_text: the map as described by text read from the .map file
        :type map_text: str
        :return: a dictionary describing the map objects
        The returned dict holds the following keys:
        'size': (height, width),
        'num_players': num_players,
        'treasures': treasures,
        'powerups': powerups,
        'scripts': scripts,
        'anti_scripts': anti_scripts,
        'pirates': pirates,
        'params': all the other parameters in the map
        :rtype: dict[str, any]
        """
        width = height = None

        # Used to count the rows in the map
        row = 0

        # Used to map treasure data to the proper treasure
        current_treasure_id = 0

        score = None
        num_players = None

        params = {}

        # A list of chars representing the letters that are translated into pirates from the map file. It is assigned
        # after the number of players is known, to know how many letters should it know to parse into pirates.
        pirate_keys_list = None
        treasures_data = dict()
        # This dictionary uses the player's id as key to a value which is a list of all the locations of that player's
        # pirates
        player_pirate_locations = defaultdict(list)
        treasures = []
        powerups = []
        scripts = []
        anti_scripts = []

        for line in map_text.split('\n'):
            line = line.strip()

            # ignore blank lines and comments
            if not line or line[0] == '#':
                continue

            row_key, row_data = line.split(' ', 1)
            row_key = row_key.lower()
            if row_key == 'cols':
                width = int(row_data)

            elif row_key == 'rows':
                height = int(row_data)

            elif row_key == 'players':
                num_players = int(row_data)
                if num_players < 2 or num_players > 10:
                    raise Exception("map", "player count must be between 2 and 10")

            elif row_key == 'score':
                score = list(map(int, row_data.split()))

            elif row_key == 'treasure':
                treasure_params = row_data.split()
                treasure_id = int(treasure_params[0])
                treasure_value = int(treasure_params[1])
                treasures_data[treasure_id] = treasure_value

            elif row_key == 'powerup':
                powerup = row_data.split()
                powerup = [powerup[0]] + map(int, powerup[1:])
                powerups.append(powerup)

            elif row_key == 'script':
                script = row_data.split()
                script = map(int, script)
                scripts.append(script)

            elif row_key == 'anti_script':
                anti_script = row_data.split()
                anti_script = map(int, anti_script)
                anti_scripts.append(anti_script)

            elif row_key == 'm':
                # Initiate the pirate_keys_list
                if pirate_keys_list is None:
                    if num_players is None:
                        raise Exception("map",
                                        "players count expected before map lines")
                    # pirates of team 'a'/'b'/'c'...
                    pirate_keys_list = [chr(ord('a') + i) for i in range(num_players)]

                # row is too short - map must be a full rectangle!
                if len(row_data) != width:
                    raise Exception("map",
                                    "Incorrect number of cols in row %s. "
                                    "Got %s, expected %s."
                                    % (row, len(row_data), width))
                # parse the row
                for col, char in enumerate(row_data):
                    # A pirate
                    if char in pirate_keys_list:
                        player_pirate_locations[pirate_keys_list.index(char)].append(Location(row, col))

                    # A treasure
                    elif char == MAP_OBJECTS[TREASURE]:
                        treasure_value = 1
                        if current_treasure_id in treasures_data.keys():
                            treasure_value = treasures_data[current_treasure_id]
                        treasures.append((current_treasure_id, Location(row, col), treasure_value))
                        current_treasure_id += 1

                    # unknown object
                    elif char != MAP_OBJECTS[LAND]:
                        raise Exception("map", "Invalid character in map: %s" % char)

                row += 1

            else:
                # default collect all other parameters
                params[row_key] = row_data

        if score and len(score) != num_players:
            raise Exception("map",
                            "Incorrect score count.  Expected %s, got %s"
                            % (num_players, len(score)))
        if height != row:
            raise Exception("map",
                            "Incorrect number of rows.  Expected %s, got %s"
                            % (height, row))
        return {
            'size': (height, width),
            'num_players': num_players,
            'treasures': treasures,
            'powerups': powerups,
            'scripts': scripts,
            'anti_scripts': anti_scripts,
            'pirate_locations': player_pirate_locations,
            'params': params
        }

    def get_map(self):
        """
        Gets the map

        :return: returns the map as a list that holds lists of ints, each sub-list is a row of the map and each int
        describes a single square on the map, the value of the int determines what type of object is it: 0: pirate,
        -1: empty spot, -2: treasure
        :rtype: list[list[int]]
        """

        result = [[LAND] * self.width for _ in range(self.height)]
        for location in self.map.keys():
            result[location.row][location.col] = self.map[location]
        return result

    def get_state_changes(self):
        """
        Returns a list of all transient objects on the map.
        Living pirates, pirates killed this turn.
        Changes are sorted so that the same state will result in the same output

        :return: a list holding all of the changes
        :rtype: dict[str, list[dict[str, any]]]
        """
        changes = {}
        treasure_list = []
        for treasure in self.treasures:
            if treasure.is_available:
                treasure_dict = {'type': 'treasure',
                                 'id': treasure.id,
                                 'initial_location': treasure.initial_location.as_tuple,
                                 'value': treasure.value}
                treasure_list.append(treasure_dict)
        changes['treasures'] = treasure_list

        # player special parameters
        players_list = []
        for player in self.players:
            player_dict = {'type': 'player',
                            'id': player.id}
            players_list.append(player_dict)
        changes['players'] = players_list

        # living pirates
        pirates_list = []
        for pirate in self.living_pirates:
            pirate_dict = {'type': 'pirate',
                           'id': pirate.id,
                           'location': pirate.location.as_tuple,
                           'owner': pirate.owner.id,
                           'initial_location': pirate.initial_location.as_tuple,
                           'turns_to_sober': int(pirate.turns_to_sober),
                           'treasure_initial_location': pirate.treasure.initial_location.as_tuple if
                           pirate.has_treasure() else (-1, -1),
                           'treasure_id': (int(pirate.treasure.id) if pirate.has_treasure() else -1),
                           'treasure_value': int(pirate.treasure.value if pirate.has_treasure() else 0),
                           'reload_turns': pirate.reload_turns,
                           'defense_reload_turns': pirate.defense_reload_turns,
                           'defense_expiration_turns': pirate.defense_expiration_turns,
                           'carry_treasure_speed': pirate.carry_treasure_speed,
                           'attack_radius': pirate.attack_radius,
                           'powerups': [powerup for powerup in pirate.powerups]}
            pirates_list.append(pirate_dict)
        changes['pirates'] = pirates_list

        # killed pirates
        dead_pirates_list = []
        for pirate in self.dead_pirates:
            dead_pirate_dict = {'type': 'dead_pirate',
                                'id': pirate.id,
                                'location': pirate.location.as_tuple,
                                'owner': pirate.owner.id,
                                'initial_location': pirate.initial_location.as_tuple,
                                'turns_to_revive': pirate.turns_to_revive,
                                'attack_radius': pirate.attack_radius}
            dead_pirates_list.append(dead_pirate_dict)
        changes['dead_pirates'] = dead_pirates_list

        # powerups
        powerups_list = []
        for powerup in self.powerups:
            if powerup.end_turn > self.turn >= powerup.start_turn:
                powerup_dict = {'type': 'powerup',
                                'id': powerup.id,
                                'powerup_type': powerup.__class__.__name__,
                                'location': powerup.location.as_tuple,
                                'active_turns': powerup.active_turns,
                                'end_turn': powerup.end_turn,
                                'value': powerup.get_value()}
                powerups_list.append(powerup_dict)
        changes['powerups'] = powerups_list

        # scripts
        scripts_list = []
        for script in self.scripts:
            if script.end_turn > self.turn >= script.start_turn:
                script_dict = {'type': 'script',
                               'id': script.id,
                               'location': script.location.as_tuple,
                               'end_turn': script.end_turn}
                scripts_list.append(script_dict)
        changes['scripts'] = scripts_list

        # anti_scripts
        anti_scripts_list = []
        for anti_script in self.anti_scripts:
            if anti_script.start_turn <= self.turn < anti_script.end_turn:
                anti_script_dict = {'type': 'anti_script',
                                    'id': anti_script.id,
                                    'location': anti_script.location.as_tuple,
                                    'end_turn': anti_script.end_turn}
                anti_scripts_list.append(anti_script_dict)
        changes['anti_scripts'] = anti_scripts_list

        # bermuda zones
        bermuda_zones_list = []
        for bermuda_zone in self.bermuda_zones:
            if bermuda_zone.active_turns > 0:
                bermuda_dict = {'type': 'bermuda_zone',
                                'center': bermuda_zone.center.as_tuple,
                                'radius': bermuda_zone.radius,
                                'owner': bermuda_zone.owner,
                                'active_turns': bermuda_zone.active_turns}
                bermuda_zones_list.append(bermuda_dict)
        changes['bermuda_zones'] = bermuda_zones_list

        return changes

    def get_map_output(self):
        """
        Renders the map from the perspective of the given player.
        If player is None, then no squares are hidden and player ids are not reordered.

        :return: a list of strings describing the map
        :rtype: list[str]
        """
        # TODO: get this function working (need to check if this todo is still relevant)
        result = []
        for row in self.get_map():
            result.append(''.join([MAP_RENDER[col] for col in row]))
        return result

    @staticmethod
    def parse_order(order):
        """
        Validates the format of the orders sent by the runners, and sort them to ignored, valid and invalid.
        This function sort the orders based on their format, not on whether they are executable game-wise.

        :param order: a single order the player gives. the order should be in tte following format:
            {'type': 'order','order-type': the type of the order (string), 'acting-pirate': the id of the pirate the
            order is issued to (int), 'order-args': a dictionary holding any additional information the order might
            require, empty dict in case nothing is needed}
        :type order: dict[str, any]
        """
        if order['type'] != 'order':
            if order['type'] != 'message' and order['type'] != 'stop':
                raise InvalidOrderFormatException('unknown action', order)
            return

        if len(order) != 4:
            raise InvalidOrderFormatException('incorrectly formatted order', order)

        # validate for orders
        if 'order_type' not in order:
            raise InvalidOrderFormatException('no order type', order)

        if 'acting_pirate' not in order:
            raise InvalidOrderFormatException('no acting pirate', order)

        if 'order_args' not in order:
            raise InvalidOrderFormatException('no order args', order)

    @staticmethod
    def in_circle(center, radius2, location):
        """
        Returns if location is within a circle of radius2 from center.

        :param center: the center of the circle
        :type center: Location
        :param radius2: the squared radius of the circle
        :type radius2: int
        :param location: the location to check if it's in the circle
        :type location: Location
        :return: If location is within a circle of radius2 from center.
        :rtype: bool
        """
        square_dist = (center.row - location.row) ** 2 + (center.col - location.col) ** 2
        return square_dist <= radius2

    def initial_location_in_circle(self, center, player_id):
        """
        Returns whether one of the player's pirates' initial locations is within bermuda zone radius of center.

        :param center: the location to check whether it is in bermuda zone radius from one of player's initial locations
        :type center: Location
        :param player_id: the id of the player whose initial locations we look for
        :type player_id: int
        :return: Whether one of the player's pirates' initial locations is within bermuda zone radius of center.
        :rtype: bool
        """
        for pirate in self.players[player_id].all_pirates:
            if self.in_circle(center, self.bermuda_zone_radius, pirate.initial_location):
                return True
        return False

    def summon_bermuda_zone(self, pirate):
        """
        Summons a bermuda zone for pirate's owner around pirate.

        :param pirate: The pirate to summon a bermuda zone around
        :type pirate: Pirate
        """
        bermuda_zone = BermudaZone(pirate.owner.id, self.bermuda_zone_active_turns, self.turn, pirate.location,
                                   self.bermuda_zone_radius)
        self.bermuda_zones.append(bermuda_zone)
        pirate.owner.num_scripts = 0

    def validate_order(self, player_id, order, counter_dict):
        """
        Validates the format of the orders sent by the runners, and sort them to ignored, valid and invalid.
        This function sort the orders based on whether or not they are executable game-wise.

        :param player_id: id of the player giving the orders
        :type player_id: int
        :param order: a single order the player gives. the order should be in tte following format:
            {'type':'order','order-type': the type of the order, 'acting-pirate': the id of the pirate the order is
            issued to, 'order-args': additional information the order might require}
        :type order: dict[str, any]
        :param counter_dict: a dictionary with additional information used for turn logic
        :type counter_dict: dict[str, any]
        """
        pirate = self.get_living_pirate(player_id, order['acting_pirate'])

        if pirate is None:
            raise InvalidOrderException('invalid pirate', order)

        # drunk pirates can't act
        if pirate.turns_to_sober > 0:
            raise InvalidOrderException('the pirate is drunk - can\'t do anything', order)

        # a pirate can't do more than 1 order each turn
        if pirate in counter_dict['acting_pirates']:
            raise PirateAlreadyActedException('pirate can\'t do more than 1 order each turn', order, pirate.id)

        # validate that ship cannot attack if it's reloading
        if order['order_type'] == 'attack':
            if pirate.reload_turns > 0:
                raise IgnoredOrderException('attack ignored - pirate ship is reloading', order)
            if pirate.treasure is not None:
                raise IgnoredOrderException('pirate can\'t attack while carrying a treasure', order)
            if len(order['order_args']) != 1 or order['order_args']['target'] is None:
                raise InvalidOrderException('invalid args', order)

            target = self.get_living_pirate(player_id, order['order_args']['target'])
            if target is None:
                raise InvalidOrderException("target pirate doesn't exist", order)

            counter_dict['acting_pirates'].add(pirate)
            return

        # validate that ship cannot defend if it's reloading
        elif order['order_type'] == 'defense':
            if pirate.defense_reload_turns > 0:
                raise IgnoredOrderException('defend ignored - pirate ship is reloading', order)
            if len(order['order_args']) > 0:
                raise InvalidOrderException('invalid args', order)

            counter_dict['acting_pirates'].add(pirate)
            return

        # validate that pirate cannot cloak itself while in cloak or when player cloaked in this turn
        elif order['order_type'] == 'cloak':
            if pirate.cloak_turns > 0:
                raise IgnoredOrderException('cloak ignored - pirate is already invisible', order)

            if len(order['order_args']) > 0:
                raise InvalidOrderException('invalid args', order)

            if counter_dict['cloaked_this_turn']:
                raise InvalidOrderException('pirate already cloaked this turn', order)

            counter_dict['cloaked_this_turn'] = True
            counter_dict['acting_pirates'].add(pirate)
            return

        elif order['order_type'] == 'bermuda':
            if self.initial_location_in_circle(pirate.location, player_id):
                raise IgnoredOrderException('bermuda zone cannot overlap enemy initial locations', order)

            if self.num_scripts[player_id] < self.required_scripts_num:
                raise InvalidOrderException('not enough scripts to summon bermuda zone', order)

            if player_id in [bermuda_zone.owner for bermuda_zone in self.bermuda_zones
                             if bermuda_zone.active_turns > 0]:
                raise InvalidOrderException('bermuda zone already activated', order)

            if counter_dict['bermuda_summoned_this_turn']:
                raise InvalidOrderException('bermuda zone already activated', order)

            if len(order['order_args']) > 0:
                raise InvalidOrderException('invalid args', order)

            counter_dict['bermuda_summoned_this_turn'] = True
            counter_dict['acting_pirates'].add(pirate)
            return

        elif order['order_type'] == 'move':
            if len(order['order_args']) != 1 or 'destination' not in order['order_args']:
                raise InvalidOrderException('invalid args', order)

            destination = order['order_args']['destination']
            # This asserts that destination is a list of two ints.
            if not isinstance(destination, (list, tuple)) or len(destination) != 2 \
                    or not isinstance(destination[0], int) or not isinstance(destination[1], int):
                raise InvalidOrderException('invalid args', order)

            #  locations are sent as lists over the json, this turns them back
            order['order_args']['destination'] = Location(destination[0], destination[1])
            destination = order['order_args']['destination']

            distance_from = self.manhattan_distance(pirate.location, destination)

            if pirate.treasure is not None and distance_from > pirate.carry_treasure_speed:
                raise InvalidOrderException('cannot move than 1 step if carrying a treasure', order)

            if not self.is_move_valid(pirate.location, self.get_direction_letters(pirate.location, destination)):
                raise IgnoredOrderException('order ignored - can\'t move out of map', order)

            if counter_dict['action_counter'] + distance_from > self.actions_per_turn:  # counts movement steps
                raise StepLimitExceededException('total actions per turn {actions} exceeded allowed '
                                                 'maximum {max}'.format(actions=(counter_dict['action_counter'] +
                                                                                 distance_from),
                                                                        max=self.actions_per_turn), order)

            counter_dict['action_counter'] += distance_from
            counter_dict['acting_pirates'].add(pirate)
            return

        else:
            raise InvalidOrderException('invalid order type', order)

    def get_direction_letters(self, loc_a, loc_b):
        """
        Returns the step by step directions from loc_a to loc_b in string format. The directions are:
        North: -y
        South: +y
        East: -x
        West: +x

        :param loc_a: the starting location.
        :type loc_a: Location
        :param loc_b: the destination location.
        :type loc_b: Location
        :return: Returns the step by step directions from loc_a to loc_b in string format.
        :rtype: str
        """
        row1, col1 = loc_a.as_tuple
        row2, col2 = loc_b.as_tuple
        height2 = self.height // 2
        width2 = self.width // 2
        distance = self.manhattan_distance(loc_a, loc_b)

        if row1 == row2 and col1 == col2:
            # return a single move of 'do nothing'
            return ['-']

        direction_letters = []
        for i in range(distance):
            if row1 < row2:
                if row2 - row1 >= height2 and self.cyclic:
                    direction_letters.append('n')
                    row1 -= 1
                    continue
                if row2 - row1 <= height2 or not self.cyclic:
                    direction_letters.append('s')
                    row1 += 1
                    continue
            if row2 < row1:
                if row1 - row2 >= height2 and self.cyclic:
                    direction_letters.append('s')
                    row1 += 1
                    continue
                if row1 - row2 <= height2 or not self.cyclic:
                    direction_letters.append('n')
                    row1 -= 1
                    continue
            if col1 < col2:
                if col2 - col1 >= width2 and self.cyclic:
                    direction_letters.append('w')
                    col1 -= 1
                    continue
                if col2 - col1 <= width2 or not self.cyclic:
                    direction_letters.append('e')
                    col1 += 1
                    continue
            if col2 < col1:
                if col1 - col2 >= width2 and self.cyclic:
                    direction_letters.append('e')
                    col1 += 1
                    continue
                if col1 - col2 <= width2 or not self.cyclic:
                    direction_letters.append('w')
                    col1 -= 1
                    continue
        return direction_letters

    def is_move_valid(self, location, directions):
        """
        Makes sure current location + all moves of current pirate (iteratively!) are valid.
        e.g.: 'n,n,w,w' - going n once is allowed, location updates. going n for the second time is not allowed.
        So the entire order will be ignored.

        :param location: the location to start the movement from
        :type location: Location
        :param directions: a string describing the directions to go.
        :type directions: string
        :return: whether the order is valid or ignored, as well as a string describing the reason
            of the order category.
        :rtype: bool
        """
        current_loc = location
        for direction in directions:
            future_loc = self.destination(current_loc, AIM[direction])
            if self.manhattan_distance(current_loc, future_loc) > 1 and not self.cyclic:
                self.rejected_moves.append([self.turn, current_loc.row, current_loc.col, direction])
                return False
            current_loc = future_loc
        return True

    def do_orders(self):
        """
        Executes the player orders and handles conflicts.
        All pirates are moved to their new positions (current location if they don't have a move command).
        Any pirates who share the same square at the end of the turn are killed.

        """

        # set old pirate locations to land
        for pirate in self.living_pirates:
            self.map[pirate.location] = LAND

        # determine the direction that each pirate moves (holding any pirates that don't have orders)
        pirate_orders = {}
        for player_id in xrange(self.num_players):
            for order in self.orders[player_id]:
                pirate = self.get_living_pirate(player_id, order['acting_pirate'])
                if pirate is None:  # Invalid pirate
                    break

                pirate_orders[pirate] = (order['order_type'], order['order_args'])

        for pirate in self.living_pirates:
            if pirate not in pirate_orders:
                pirate_orders[pirate] = ('-', {})

        # move all the pirates
        next_pirate_locations = defaultdict(list)

        for pirate, (order_type, order_args) in pirate_orders.iteritems():
            new_location = pirate.location
            direction = '-'

            if order_type == 'attack':
                # pirate is attacking this turn
                pirate.attack_turns.extend((self.turn, order_args['target']))
                direction = 'a'
            elif order_type == 'defense':
                # pirate is defending this turn
                pirate.defense_expiration_turns = pirate.max_defense_turns
                direction = 'd'
            elif order_type == 'cloak':
                # pirate is going invisible this turn
                pirate.cloak_turns = self.cloak_duration
                direction = 'c'
            elif order_type == 'bermuda':
                self.summon_bermuda_zone(pirate)
                direction = 'f'
            elif order_type == 'move':
                new_location = order_args['destination']
                direction = self.get_direction_letters(pirate.location, new_location)

            pirate.location = new_location
            pirate.orders.append(direction)
            next_pirate_locations[pirate.location].append(pirate)

            # defense aura is on
            if pirate.defense_expiration_turns > 0:
                pirate.defense_turns.append(self.turn)

        # if pirate is sole occupy of a new square then it survives
        for player in self.players:
            player.living_pirates = []
        colliding_pirates = []

        for location, pirates in next_pirate_locations.iteritems():
            if len(pirates) == 1:
                self.players[pirates[0].owner.id].living_pirates.append(pirates[0])
            else:
                for pirate in pirates:
                    self.kill_pirate(pirate, True)
                    colliding_pirates.append(pirate)

        # set new pirate locations
        for pirate in self.living_pirates:
            self.map[pirate.location] = pirate.owner.id

    def do_defense(self):
        """
        Handles the defense upkeep logic - ticking down defense duration and reload times.

        """
        for pirate in self.living_pirates:
            # if defense expiration is full and defense was activated this turn, start counting defense reload time
            if pirate.defense_expiration_turns == pirate.max_defense_turns and pirate.defense_turns[-1] == self.turn:
                pirate.defense_reload_turns = self.defense_reload_turns
            else:
                if pirate.defense_reload_turns > 0:
                    pirate.defense_reload_turns -= 1
            # count defense expiration
            if pirate.defense_expiration_turns > 0:
                pirate.defense_expiration_turns -= 1

    def do_cloak(self):
        """
        Handles the cloak logic

        """
        for pirate in self.living_pirates:
            if pirate.cloak_turns > 0:
                pirate.cloak_turns -= 1

    def do_bermuda_effect(self):
        """
        Kills all of the pirates who are inside a bermuda zone of the opposing team

        """
        pirates_to_kill = []
        for pirate in self.living_pirates:
            enemy_bermuda_zone_list = [bermuda_zone for bermuda_zone in self.bermuda_zones if
                                       bermuda_zone.owner != pirate.owner.id and bermuda_zone.active_turns > 0]
            for bermuda_zone in enemy_bermuda_zone_list:
                if self.in_circle(bermuda_zone.center, bermuda_zone.radius, pirate.location):
                    pirates_to_kill.append(pirate)
                    break  # continue to next pirate

        for pirate in pirates_to_kill:
            self.kill_pirate(pirate)
            pirate.reason_of_death = 'b'

        # update remaining turns of bermuda zone
        for bermuda_zone in self.bermuda_zones:
            if bermuda_zone.active_turns > 0:
                bermuda_zone.active_turns -= 1

    def do_sober(self):
        """
        Handles the drunk pirate upkeep logic

        """
        pirates_to_sober = []
        for pirate in self.living_pirates:
            if pirate in self.drunk_pirates:
                pirate.drink_history.append(True)
                if pirate.turns_to_sober > 0:
                    pirate.turns_to_sober -= 1
                    # calculate if the turn has come to sober
                if pirate.turns_to_sober == 0:
                    pirates_to_sober.append(pirate)
            else:
                pirate.drink_history.append(False)

        for pirate in pirates_to_sober:
            pirate.owner.drunk_pirates.remove(pirate)

    def do_spawn(self):
        """
        Respawns dead pirates

        """
        pirates_to_revive = []
        for pirate in self.dead_pirates:
            # calculate if the turn has come to revive
            if pirate.turns_to_revive <= 0:
                # verify no one standing in the pirate's location
                occupier = next((next_pirate for next_pirate in self.living_pirates
                                 if next_pirate.location == pirate.initial_location), None)
                if occupier is not None:
                    self.kill_pirate(occupier)
                else:
                    pirates_to_revive.append(pirate)
            else:
                pirate.turns_to_revive -= 1

        # remove pirate from dead list and make new one in the alive
        for pirate in pirates_to_revive:
            pirate.owner.dead_pirates.remove(pirate)
            owner = pirate.owner
            location = pirate.initial_location
            new_pirate = Pirate(location, owner, pirate.id, self.attack_radius, self.max_defense_turns, self.turn)
            self.map[location] = owner.id
            owner.all_pirates.append(new_pirate)
            owner.living_pirates.append(new_pirate)

    def get_last_turn_points(self):
        """
        Get the points achieved last turn

        :return: a list of the points earned by each player last turn
        :rtype: list[int]
        """
        if len(self.score_history[0]) < 2:
            return self.score
        return [player.score_history[-1] - player.score_history[-2] for player in self.players]

    def add_initial_pirate(self, location, owner, pirate_id):
        """
        Creates a pirate in location for player owner with id, then appends it to the necessary lists,
        such as the all pirates list and the map. Used to create the first pirates of the game.

        :param location: The location of the new pirate
        :type location: Location
        :param owner: The id of the pirate's owner
        :type owner: int
        :param pirate_id: The id of the new pirate
        :type pirate_id: int
        :return: Returns the new pirate
        :rtype: Pirate
        """
        pirate = Pirate(location, self.players[owner], pirate_id, self.attack_radius, self.max_defense_turns, self.turn)
        self.map[location] = owner
        self.players[owner].all_pirates.append(pirate)
        self.players[owner].living_pirates.append(pirate)
        return pirate

    def get_living_pirate(self, player_id, pirate_id):
        """
        This function returns a living pirate by pirate id and player owner id. Or None if no pirate is found.

        :param player_id: The id of the owning player.
        :type player_id: int
        :param pirate_id: The id of the pirate.
        :type pirate_id: int
        :return: The found pirate or None if no pirate is found.
        :rtype: Pirate
        """
        try:
            return self.players[player_id].get_living_pirate(pirate_id)
        except IndexError:
            return None

    def drunk_pirate(self, pirate):
        """
        Makes the given pirate drunk.

        :param pirate: The pirate to make drunk
        :type pirate: Pirate
        """
        pirate.owner.drunk_pirates.append(pirate)
        pirate.drink_turns.append(self.turn + 1)
        pirate.turns_to_sober = self.turns_to_sober

    def kill_pirate(self, pirate, ignore_error=False):
        """
        Kills the given pirate, raises an error if the pirate doesn't exist and ignore_error is False.

        :param pirate: The pirate to kill
        :type pirate: Pirate
        :param ignore_error: Determines whether or not an error will be ignored or not if the pirate given is invalid
        :type ignore_error: bool
        :return: Returns the killed pirate
        :rtype: Pirate
        """
        location = pirate.location
        try:
            # if the killed pirate holds treasure
            if pirate.treasure:
                # release it
                pirate.treasure.is_available = True
                pirate.treasure = None

            self.map[location] = LAND
            pirate.owner.dead_pirates.append(pirate)
            pirate.die_turn = self.turn
            pirate.turns_to_revive = self.pirate_spawn_turns
            pirate.is_lost = True

            return pirate.owner.remove_living_pirate(pirate.id)
        except KeyError:
            if not ignore_error:
                raise Exception("Kill pirate error",
                                "Pirate not found at %s" % location)

    @staticmethod
    def in_attack_range(attacker, target):
        """
        Returns if the target is within the attack range of attacker.

        :param attacker: The attacking pirate
        :type attacker: Pirate
        :param target: The target pirate
        :type target: Pirate
        :return: Returns if the target is within attack range of attacker.
        :rtype: bool
        """
        return PiratesGame.in_circle(attacker.location, attacker.attack_radius, target.location)

    def do_attack(self):
        """
        Handles the attacking logic.

        """
        # map pirates (to be killed) to the enemies that kill it
        pirates_to_drunk = set()
        for pirate in self.living_pirates:
            pirate.attack_radius_history.append(pirate.attack_radius)

            if pirate.attack_turns[-2] != self.turn:  # [-2] is the last turn attack was made. [-1] is the attack target

                if pirate.reload_turns > 0:
                    pirate.reload_turns -= 1
                continue

            # attack happened this turn
            if pirate.attack_powerup_active_turns == 0:
                pirate.reload_turns = self.reload_turns

            # attack turn
            robbers = []
            if self.num_players == 2:
                enemy_id = (pirate.owner.id + 1) % 2
                target_pirate = self.get_living_pirate(enemy_id, pirate.attack_turns[-1])
            else:
                # TODO: Attack currently doesn't have enemy owner id and will not work with more then 2 players!
                raise Exception('Attack is not supported for more then one player!')

            if target_pirate:
                if self.in_attack_range(pirate, target_pirate) and target_pirate.turns_to_sober == 0 and \
                                target_pirate.defense_turns[-1] != self.turn:
                    # target not drunk and did not defend and in attack range
                    pirates_to_drunk.add(target_pirate)
                    if target_pirate.treasure:
                        # corner case: a pirate that robbed a treasure cannot be robbed of his 'new' treasure
                        # if attacked also. treasure goes back to its original place

                        # TODO: Rob powerup is unused, should we still support it?
                        if pirate.rob_powerup_active_turns > 0 and target_pirate not in robbers:
                            pirate.treasure = target_pirate.treasure
                            robbers.append(pirate)
                        else:
                            # treasure goes back to its original place and is now available
                            target_pirate.treasure.is_available = True
                        # either way, target will not hold a treasure at the end of the turn
                        target_pirate.treasure = None

        for pirate in pirates_to_drunk:
            self.drunk_pirate(pirate)

    def do_treasures(self):
        """
        Handles the treasure logic:
        updates scores if a ship unloads a treasure
        updates the treasure history for the replay of ships that carry a treasure
        returns treasures to their spawn if their carrying ship got drunk/died
        loads treasures on sober pirates that stand on a treasure

        """
        available_treasures = [treasure for treasure in self.treasures if treasure.is_available]

        # if pirate already has a treasure, update treasure history and ignore the rest
        # check if pirate location is an existing treasure location
        # if yes, pick it up and update treasure history
        # if not, update location history
        for pirate in self.living_pirates:
            if pirate.treasure:
                if pirate.location != pirate.initial_location:
                    pirate.treasure_history.append(pirate.treasure.value)
                else:
                    pirate.treasure_history.append(0)
                    # when ship unloads treasure, start counting spawn turns for the treasure
                    # TODO: this is an unused feature, should we still support it?
                    pirate.treasure.spawn_turns = self.treasure_spawn_turns
                    # update score
                    pirate.owner.score += pirate.treasure.value
                    # release it
                    pirate.treasure = None
            else:
                # if pirate doesnt hold a treasure AND is in an available treasure location, pick it up
                pirate.treasure = next((treasure for treasure in available_treasures if
                                        pirate.location == treasure.location and
                                        pirate not in self.drunk_pirates), None)
                # drunk pirates can't pick up treasures
                if pirate.treasure is not None:
                    pirate.treasure_history.append(pirate.treasure.value)
                    pirate.treasure.is_available = False
                else:
                    pirate.treasure_history.append(0)

        for treasure in self.treasures:
            treasure.is_available_history.append(treasure.is_available)
            if treasure.spawn_turns > 0:
                treasure.spawn_turns -= 1
            if treasure.spawn_turns == 0:
                treasure.is_available = True
                treasure.spawn_turns = -1

    def do_powerups(self):  # TODO: re-name the function
        """
        Handles the powerup logic:
        appends to a pirate's powerup history which powerups he has
        removes powerups from pirates that have expired
        spawns and despawns powerups from the map according to their start/end turns.

        """
        available_powerups = [powerup for powerup in self.powerups if
                              powerup.start_turn <= self.turn < powerup.end_turn]
        for pirate in self.living_pirates:
            # if powerup already activated
            if pirate.attack_powerup_active_turns > 0:
                pirate.attack_powerup_active_turns -= 1
            else:
                pirate.attack_radius = self.attack_radius
            # TODO: Rob powerup is unused, should we still support it?
            if pirate.rob_powerup_active_turns > 0:
                pirate.rob_powerup_active_turns -= 1
                pirate.rob_powerup_history.append(True)
            else:
                if "rob" in pirate.powerups:
                    pirate.powerups.remove("rob")
                pirate.rob_powerup_history.append(False)
            if pirate.speed_powerup_active_turns > 0:
                pirate.speed_powerup_active_turns -= 1
                pirate.speed_powerup_history.append(True)
            else:
                if "speed" in pirate.powerups:
                    pirate.powerups.remove("speed")
                pirate.carry_treasure_speed = 1
                pirate.speed_powerup_history.append(False)

            # check if pirate is standing on an powerup
            powerup = next((powerup for powerup in available_powerups if pirate.location == powerup.location), None)
            if powerup:
                powerup.end_turn = self.turn
                powerup.activate(pirate, self)

    def do_scripts(self):
        """
        Handles the scrip and anti script logic:
        updates the lists holding all the available scripts and anti scripts on the map
        collects scripts and anti scripts if a pirate is standing on top of one

        """
        available_scripts = [script for script in self.scripts if
                             script.start_turn <= self.turn < script.end_turn]

        available_anti_scripts = [anti_script for anti_script in self.anti_scripts if
                                  anti_script.start_turn <= self.turn < anti_script.end_turn]

        for pirate in self.living_pirates:
            # check if pirate is standing on a script
            script = next((script for script in available_scripts if pirate.location == script.location), None)
            if script:
                script.end_turn = self.turn
                pirate.owner.num_scripts += 1

            anti_script = next((anti_script for anti_script in available_anti_scripts if
                                pirate.location == anti_script.location), None)
            if anti_script:
                anti_script.end_turn = self.turn
                if pirate.owner.num_scripts > 0:
                    pirate.owner.num_scripts -= 1

    def destination(self, location, direction):
        """
        Returns the location produced by offsetting location by the given direction (also a location)

        :param location: the starting location
        :type location: Location
        :param direction: the direction to offset to
        :type direction: Location
        :return: The new location
        :rtype: Location
        """
        return Location((location.row + direction.row) % self.height, (location.col + direction.col) % self.width)

    @staticmethod
    def create_location(row, col):
        """
        Creates a location object from given coordinates, is used in tests

        :param row: the location's row
        :type row: int
        :param col: the location's col
        :type col: int
        :return: a location created from row and col
        :rtype: Location
        """
        return Location(row, col)

    def remaining_players(self):
        """
        Returns the players who are still alive

        :return: A list of all the player id's of the living players.
        :rtype: list[int]
        """
        return [player.id for player in self.players if player.is_alive]

    # Common functions for all games
    def game_over(self):
        """
        Determines if the game is over.
        Used by the engine to determine when to finish the game.

        :return: whether the game is over or not
        :rtype: bool
        """
        if len(self.remaining_players()) < 1:
            self.end_of_game_reason = 'No bots left'
            self.winning_bot = []
            return True
        if len(self.remaining_players()) == 1:
            self.winning_bot = self.remaining_players()
            # The NON winning bot, it's the crashed one
            self.end_of_game_reason = 'Bot crashed'
            return True
        if max(self.score) >= self.max_points:
            self.end_of_game_reason = 'Maximum points'
            return True
        return False

    def get_winner(self):
        """
        Returns the winner of the game.
        The winner is defined as the player with the most points.
        In case other bots crash, the remaining bot will win automatically.
        If remaining bots crash on same turn - there will be no winner.

        :return: A list holding the winning pirate's id, or an empty list if there is no winner.
        :rtype: list[int]
        """
        return self.winning_bot

    def kill_player(self, player_id):
        """
        Used by engine to signal that a player is out of the game.

        :param player_id: the player to kill
        :type player_id: int
        """
        self.players[player_id].kill_player()

    def get_current_regression_data(self):
        """
        Returns the regression data of the current turn

        :return: the regression data of the current turn
        :rtype: dict[int, dict[str, object]]
        """
        regression_data = {}
        for player in self.players:
            player_data = {'score': player.score,
                           'pirates': {}}
            for pirate in player.all_pirates:
                player_data['pirates'][pirate.id] = pirate.location.as_tuple
            regression_data[player.id] = player_data
        return regression_data

    def start_game(self):
        """
        Called by engine at the start of the game

        """
        pass

    def finish_game(self):
        """
        Called by the engine at the end of the game.

        """
        if self.end_of_game_reason is None:
            self.end_of_game_reason = 'Turn limit reached'
            if self.get_winner() and len(self.get_winner()) == 1:
                self.end_of_game_reason += ', Bot [' + self.players[self.winning_bot[0]].bot_name + '] won'
            else:
                self.end_of_game_reason += ', there is no winner'
            self.calculate_turn_significance()

    def start_turn(self):
        """
        Called by engine at the start of the turn

        """
        self.turn += 1
        for player in self.players:
            player.orders = []

    def finish_turn(self):
        """
        Called by engine at the end of the turn

        """
        self.do_orders()  # moves the pirates on the map
        self.do_sober()  # handles drunk history and removes drunk pirates who are sober
        self.do_attack()  # handles attacking pirates
        self.do_defense()  # handles defending pirates
        self.do_cloak()  # handles cloaking pirates
        self.do_bermuda_effect()  # kills all pirates in bermuda zone if they do not belong to the player who summoned
        #  it, and updates bermuda zone counter
        self.do_treasures()  # handles treasure - collecting and unloading
        self.do_powerups()  # handles powerups
        self.do_scripts()  # handles scripts
        self.do_spawn()  # spawns new pirates

        # calculate the score for history
        for player in self.players:
            player.score_history.append(player.score)

        self.calculate_turn_significance()

    def calculate_turn_significance(self):
        """
        Updates the player's ranking, and checks if a player had won this turn

        """
        # The index of the score is the id of the player it belongs to, so this turns the score list into the list
        # player ids ordered by their score
        ranking_bots = [sorted(self.score, reverse=True).index(score) for score in self.score]
        if self.ranking_bots != ranking_bots:
            self.ranking_turn = self.turn
        self.ranking_bots = ranking_bots
        winning_bot = [player_id for player_id in range(len(self.score)) if self.score[player_id] == max(self.score)]
        if self.winning_bot != winning_bot:
            self.winning_turn = self.turn
        self.winning_bot = winning_bot

    def get_state(self):
        """
        Get all the state changes
        Used by engine for streaming playback

        :return: A string describing all the changes as they appear in self.get_state_changes()
        :rtype: str
        """
        return self.get_state_changes()

    def get_player_start(self, player_id=None):
        """
        Get game parameters visible to players.
        Used by engine to send bots startup info on turn 0

        :param player_id: The player whose perspective is used to send the details, or None if no perspective is wanted
        :type player_id: int
        :return: A string describing the game settings required for setting up the game at turn 0.
        :rtype: str
        """
        result = {'turn': self.turn,
                  'load_time': self.load_time,
                  'turn_time': self.turn_time,
                  'recover_errors': self.recover_errors,
                  'rows': self.height,
                  'cols': self.width,
                  'max_turns': self.max_turns,
                  'attack_radius2': self.attack_radius,
                  'cloak_duration': self.cloak_duration,
                  'bermuda_zone_active_turns': self.bermuda_zone_active_turns,
                  'required_scripts_num': self.required_scripts_num,
                  'player_seed': self.player_seed,
                  'cyclic': int(self.cyclic),  # send whether map is cyclic or not
                  'num_players': self.num_players,
                  'spawn_turns': self.pirate_spawn_turns,
                  'turns_to_sober': self.turns_to_sober,
                  'max_points': self.max_points,
                  'randomize_sail_options': self.randomize_sail_options,
                  'actions_per_turn': self.actions_per_turn,
                  'reload_turns': self.reload_turns,
                  'defense_reload_turns': self.defense_reload_turns,
                  'max_defense_turns': self.max_defense_turns,
                  'treasure_spawn_turns': self.treasure_spawn_turns,
                  'initial_scores': [0] * self.num_players,
                  # TODO : check if the initialization of this value should be here... as well as the next few
                  'last_turn_scores': [0] * self.num_players,
                  'num_of_scripts': [0] * self.num_players}
        if player_id is not None:
            bot_names = self.order_for_player(player_id, self.bot_names)
            result['bot_names'] = bot_names

        return result

    def get_player_state(self, player_id):
        """
        Creates a dict which communicates the updates to the state.
        All visible transient objects are included.
        Used to tell the bots the changes to the game state.

        :param player_id: the id of the player who's perspective we use
        :type player_id: int
        :return: a dict describing the updates to the state
        :rtype: dict[str, any]
        """
        render_dict = self.get_state_changes()
        # next list all transient objects
        for key, value in render_dict.iteritems():
            # switch player perspective of player numbers
            for sub_part in value:
                # if pirate, hide its location from enemy
                if sub_part['type'] in ['pirate', 'dead_pirate', 'bermuda_zone']:
                    sub_part['owner'] = self.perspectives_key[player_id][sub_part['owner']]
                elif sub_part['type'] == 'player':
                    sub_part['id'] = self.perspectives_key[player_id][sub_part['id']]

        render_dict['game_scores'] = self.order_for_player(player_id, self.score)
        render_dict['last_turn_points'] = self.order_for_player(player_id, self.get_last_turn_points())
        render_dict['num_of_scripts'] = self.order_for_player(player_id, self.num_scripts)

        return render_dict

    def is_alive(self, player_id):
        """
        Determines if a player is still alive

        :param player_id: The id of the player
        :type player_id: int
        :return: whether or not the player is alive
        :rtype: bool
        """
        return self.players[player_id].is_alive

    def do_moves(self, player_id, moves):
        """
        Get game parameters visible to players.
        Used by engine to send bots startup info on turn 0

        :param player_id: The player whose perspective is used to send the details, or None if no perspective is wanted
        :type player_id: int
        :param moves: The moves the player wants to do.
        :type moves: list[dict[str, any]]
        :return: A tuple of the valid orders, and 2 lists of strings describing the invalid and ignored orders.
        :rtype: (list[dict[str, any]], list[str], list[str])
        """
        valid = []
        """:type : list[dict[str, any]]"""
        invalid = []
        """:type : list[(dict[str, any], str]]"""
        ignored = []
        """:type : list[(dict[str, any], str]]"""
        # dictionary for passing arguments between this function and its sub-functions
        counter_dict = {'acting_pirates': set(), 'action_counter': 0,
                        'bermuda_summoned_this_turn': False, 'cloaked_this_turn': False}

        # list of ids of pirates who already acted twice, it's role is to prevent going over all of the orders
        # of a player whenever a PirateAlreadyActed exception is raised
        removed_from_valid_pirate_ids = []
        # A flag determining whether or not movement orders were canceled, for the same reasons as above except for
        # using more moves than allowed in a turn
        move_orders_removed = False
        for order in moves:
            try:
                self.parse_order(order)
                self.validate_order(player_id, order, counter_dict)
                valid.append(order)

            except (InvalidOrderFormatException, InvalidOrderException) as error:
                invalid.append([error.order, error.message])

            except IgnoredOrderException as error:
                ignored.append([error.order, error.message])

            except StepLimitExceededException as error:
                invalid.append((error.order, error.message))
                if not move_orders_removed:
                    orders_to_invalidate = []
                    for valid_order in valid:
                        if valid_order['order_type'] == 'move':
                            invalid.append([valid_order, error.message])
                            orders_to_invalidate.append(valid_order)

                    for order_to_invalidate in orders_to_invalidate:
                        valid.remove(order_to_invalidate)

            except PirateAlreadyActedException as error:
                ignored.append([error.order, error.message])

                if error.pirate_id not in removed_from_valid_pirate_ids:
                    removed_from_valid_pirate_ids.append(error.pirate_id)
                    orders_to_ignore = []

                    for valid_order in valid:
                        if valid_order['acting_pirate'] == error.pirate_id:
                            ignored.append([valid_order, error.message])
                            orders_to_ignore.append(valid_order)

                    for order_to_ignore in orders_to_ignore:
                        valid.remove(order_to_ignore)

        self.players[player_id].orders = valid
        return valid, \
            ['The order: \'%s\' was ignored # %s' % (ignore, reason) for ignore, reason in ignored], \
            ['The order: \'%s\' is invalid # %s' % (error, reason) for error, reason in invalid]

    def get_scores(self, player_id=None):
        """
        Gets the scores of all players, if a player is given it orders it for that player's perspective.

        :param player_id: The id of the player whose perspective to order the scores for, or None if the scores
        shouldn't be ordered
        :type player_id: int
        :return: the list of the scores of each player
        :rtype: list[int]
        """
        if player_id is None:
            return self.score
        else:
            return self.order_for_player(player_id, self.score)

    def order_for_player(self, player_id, data):
        """
        Orders a list of items for a player's perspective of player
        Used by engine for ending bot states

        :param player_id: the id of the player to order data for
        :type player_id: int
        :param data: the data to order
        :type data: list[any]
        :return: the ordered data list
        :rtype: list[any]
        """
        player_perspective_key = self.perspectives_key[player_id]
        return [None if i not in player_perspective_key else
                data[player_perspective_key.index(i)]
                for i in range(max(len(data), self.num_players))]

    def get_stats(self):
        """
        Get current states
        Used by engine to report stats

        :return: a dictionary holding the player stats
        :rtype: dict[str, list[int]]
        """
        pirate_count = [len(player.living_pirates) for player in self.players]

        stats = {
            'pirates': pirate_count,
            'score': self.score
        }
        return stats

    def get_replay(self):
        """
        Return a summary of the entire game
        Used by the engine to create a replay file which may be sed to replay the game.

        :return: a dictionary holding the summary of the game
        :rtype: dict[str, any]
        """
        replay = {
            # required params
            'revision': 3,
            'players': self.num_players,

            # optional params
            'turns': self.max_turns,
            'attack_radius2': self.attack_radius,

            # map
            'map': {
                'rows': self.height,
                'cols': self.width,
                'data': self.get_map_output()
            },

            # pirates
            'pirates': [],

            # map objects
            'treasures': [],
            'powerups': [],
            'scripts': [],
            'anti_scripts': [],
            'bermuda_zones': [],
            'rejected': self.rejected_moves,

            # scores
            'scores': self.score_history,
            'bonus': [0] * self.num_players,
            'cutoff': self.end_of_game_reason
        }

        for pirate in self.all_pirates:
            pirate_data = [pirate.initial_location.row, pirate.initial_location.col, pirate.spawn_turn]  # 2
            if not pirate.die_turn:
                pirate_data.append(self.turn + 1)  # 3
            else:
                pirate_data.append(pirate.die_turn)  # 3
            pirate_data.append(pirate.owner.id)  # 4
            pirate_data.append(pirate.orders)  # 5
            pirate_data.append(pirate.id)  # 6
            pirate_data.append(pirate.reason_of_death)  # 7
            pirate_data.append(''.join([str(i) for i in pirate.treasure_history]))  # 8
            pirate_data.append(pirate.attack_turns)  # 9
            pirate_data.append(pirate.defense_turns)  # 10
            pirate_data.append(''.join(['1' if i else '0' for i in pirate.drink_history]))  # 11
            pirate_data.append(pirate.attack_radius_history)  # 12
            pirate_data.append(''.join(['1' if i else '0' for i in pirate.rob_powerup_history]))  # 13
            pirate_data.append(''.join(['1' if i else '0' for i in pirate.speed_powerup_history]))  # 14

            replay['pirates'].append(pirate_data)

        for treasure in self.treasures:
            replay['treasures'].append([treasure.id, treasure.initial_location.as_tuple, treasure.value,
                                        ''.join(['1' if i else '0' for i in treasure.is_available_history])])

        for powerup in self.powerups:
            replay['powerups'].append(
                    [powerup.id, powerup.__class__.__name__, powerup.location.as_tuple, powerup.start_turn,
                     powerup.end_turn])

        for script in self.scripts:
            replay['scripts'].append([script.id, script.location.as_tuple, script.start_turn, script.end_turn])

        for anti_script in self.anti_scripts:
            replay['anti_scripts'].append(
                    [anti_script.id, anti_script.location.as_tuple, anti_script.start_turn, anti_script.end_turn])

        for bermuda_zone in self.bermuda_zones:
            replay['bermuda_zones'].append([bermuda_zone.owner, bermuda_zone.center.as_tuple, bermuda_zone.start_turn])

        return replay


class Powerup(MapObject):
    """
    This class represents the powerup in-game object, a powerup makes the pirate who picks it stronger for a while.
    """
    def __init__(self, powerup_id, location, start_turn, end_turn, active_turns):
        """
        Initiates the powerup

        :param powerup_id: the id of the powerup
        :type powerup_id: int
        :param location: the location of the powerup
        :type location: Location
        :param start_turn: the first turn the powerup should appear on
        :type start_turn: int
        :param end_turn: the last turn the powerup should appear on
        :type end_turn: int
        :param active_turns: the duration the powerup lasts on the pirate that picks it up
        :type active_turns: int
        """
        super(Powerup, self).__init__()

        self.id = powerup_id
        """:type : int"""
        self.location = location
        """:type : Location"""
        self.start_turn = start_turn
        """:type : int"""
        self.end_turn = end_turn
        """:type : int"""
        self.active_turns = active_turns
        """:type : int"""

    def get_value(self):
        """
        Returns a value for the powerup, should be overridden by powerups with a value

        :return: the value of the powerup
        :rtype: int
        """
        return -1

    def activate(self, pirate, pirates):
        """
        Activates the powerup for the pirate

        :param pirate: the pirate that picks up the powerup
        :type pirate: Pirate
        :param pirates: the pirates game
        :type pirates: PiratesGame
        """
        pass

    def get_location(self):
        """
        gets the treasure's location

        :return: the treasure's location
        :rtype: Location
        """
        return self.location


class AttackPowerup(Powerup):
    """
    The attack powerup increases the attack radius of the pirate who
    picks it up, and allows it to attack without reloading.
    """
    def __init__(self, powerup_id, location, start_turn, end_turn, active_turns, attack_radius):
        """
        Initiates the speed powerup

        :param powerup_id: the id of the powerup
        :type powerup_id: int
        :param location: the location of the powerup
        :type location: Location
        :param start_turn: the first turn the powerup should appear on
        :type start_turn: int
        :param end_turn: the last turn the powerup should appear on
        :type end_turn: int
        :param active_turns: the duration the powerup lasts on the pirate that picks it up
        :type active_turns: int
        :param attack_radius: the squared attack radius of the pirate that has the attack powerup
        :type attack_radius: int
        """
        Powerup.__init__(self, powerup_id, location, start_turn, end_turn, active_turns)
        self.attack_radius = attack_radius
        """:type : int"""

    def activate(self, pirate, pirates):
        """
        Activates the powerup on pirate.

        :param pirate: The pirate that will get the powerup
        :type pirate: Pirate
        :param pirates: the pirates game
        :type pirates: PiratesGame
        """
        pirate.attack_radius = self.attack_radius
        pirate.reload_turns = 0  # no reload turns while having this powerup
        pirate.attack_powerup_active_turns = self.active_turns
        pirate.powerups.append("attack")

    def get_value(self):
        """
        Returns the value of the powerup

        :return: the value of the powerup
        :rtype: int
        """
        return self.attack_radius


# TODO: Rob powerup is unused, should we still support it?
class RobPowerup(Powerup):
    """
    The rob powerup allows the pirate who picks it up to steal a treasure from another pirate when attacking it.
    """
    def __init__(self, powerup_id, location, start_turn, end_turn, active_turns):
        Powerup.__init__(self, powerup_id, location, start_turn, end_turn, active_turns)

    def activate(self, pirate, pirates):
        """
        Activates the powerup on pirate.

        :param pirate: The pirate that will get the powerup
        :type pirate: Pirate
        :param pirates: the pirates game
        :type pirates: PiratesGame
        """
        pirate.rob_powerup_active_turns = self.active_turns
        pirate.powerups.append("rob")

    def get_value(self):
        """
        Returns the value of the powerup

        :return: the value of the powerup
        :rtype: None
        """
        return None


class SpeedPowerup(Powerup):
    """
    The speed powerup allows the pirate who picks it to move more steps while carrying a treasure.
    """
    def __init__(self, powerup_id, location, start_turn, end_turn, active_turns, carry_treasure_speed):
        """
        Initiates the speed powerup

        :param powerup_id: the id of the powerup
        :type powerup_id: int
        :param location: the location of the powerup
        :type location: Location
        :param start_turn: the first turn the powerup should appear on
        :type start_turn: int
        :param end_turn: the last turn the powerup should appear on
        :type end_turn: int
        :param active_turns: the duration the powerup lasts on the pirate that picks it up
        :type active_turns: int
        :param carry_treasure_speed: the max speed this powerup allows a pirate to walk while carrying treasures for its
        duration
        :type carry_treasure_speed: int
        """
        Powerup.__init__(self, powerup_id, location, start_turn, end_turn, active_turns)
        self.carry_treasure_speed = carry_treasure_speed

    def activate(self, pirate, pirates):
        """
        Activates the powerup on pirate.

        :param pirate: The pirate that will get the powerup
        :type pirate: Pirate
        :param pirates: the pirates game
        :type pirates: PiratesGame
        """
        pirate.carry_treasure_speed = self.carry_treasure_speed
        pirate.speed_powerup_active_turns = self.active_turns
        pirate.powerups.append("speed")

    def get_value(self):
        """
        Returns the value of the powerup

        :return: the value of the powerup
        :rtype: int
        """
        return self.carry_treasure_speed


class Script(MapObject):
    """
    The script class. Scripts are collected in order to summon a deadly Bermuda Zone.
    """
    def __init__(self, script_id, location, start_turn, end_turn):
        """
        Initiates the script

        :param script_id: the id of the script
        :type script_id: int
        :param location: the location of the script
        :type location: Location
        :param start_turn: the turn the script should appear on
        :type start_turn: int
        :param end_turn: the last turn the script appears on
        :type end_turn: int
        """
        super(Script, self).__init__()

        self.id = script_id
        """:type : int"""
        self.location = location
        """:type : Location"""
        self.start_turn = start_turn
        """:type : int"""
        self.end_turn = end_turn
        """:type : int"""

    def get_location(self):
        """
        gets the script's location

        :return: the script's location
        :rtype: Location
        """
        return self.location


class Treasure(MapObject):
    """
    The treasure class, treasures are collected for points in order to win the game.
    """
    def __init__(self, treasure_id, location, value, initial_location=None):
        """
        Initiates the treasure

        :param treasure_id: the id of the treasure
        :type treasure_id: int
        :param location: the initial location of the treasure
        :type location: Location
        :param value: the value of the treasure
        :type value: int
        :param initial_location: the initial location of the treasure.
        :type initial_location: Location
        """
        super(Treasure, self).__init__()

        if initial_location is None:
            initial_location = Location(*location.as_tuple)

        self.id = treasure_id
        """:type : int"""
        self.location = location
        """:type : Location"""
        self.value = int(value)
        """:type : int"""
        self.initial_location = initial_location
        """:type : Location"""

        # true if doesnt belong to any pirate
        self.is_available = True
        """:type : bool"""
        self.is_available_history = []
        """:type : list[bool]"""

        self.spawn_turns = -1
        """:type : int"""

    def __str__(self):
        """
        Returns a string describing the treasure

        :return: a string describing the treasure
        :rtype: str
        """
        return '(%s, %s)' % self.location

    def get_location(self):
        """
        gets the treasure's location

        :return: the treasure's location
        :rtype: Location
        """
        return self.location


class BermudaZone(object):
    """
    The Bermuda Zone class. The Bermuda Zone kills all enemy pirates within it's area.
    """
    def __init__(self, owner, active_turns, start_turn, center, radius):
        """
        Initiates the bermuda zone

        :param owner: the id of the owner of the bermuda zone
        :type owner: int
        :param active_turns: the amount of turns the bermuda zone should last
        :type active_turns: int
        :param start_turn: the turn the bermuda zone was created on
        :type start_turn: int
        :param center: the center of the bermuda zone
        :type center: Location
        :param radius: the squared radius of the bermuda zone
        :type radius: int
        """
        self.owner = owner
        """:type : int"""
        self.active_turns = active_turns
        """:type : int"""
        self.start_turn = start_turn
        """:type : int"""
        self.center = center
        """:type : Location"""
        self.radius = radius
        """:type : int"""


class Pirate(BasePirate):
    """
    The Pirate class. The pirates are controlled by the players.
    """
    def __init__(self, location, owner, pirate_id, attack_radius, max_defense_turns, spawn_turn=None):
        """
        :param location: the initial location of the pirate
        :type location: Location
        :param owner: the id of the owner of the pirate
        :type owner: Player
        :param pirate_id: the id of the pirate
        :type pirate_id: int
        :param attack_radius: the pirate's squared attack radius
        :type attack_radius: int
        :param max_defense_turns: the amount of turns this pirate's defense lasts
        :type max_defense_turns: int
        :param spawn_turn: the turn the pirate spawned on
        :type spawn_turn: int
        """

        super(Pirate, self).__init__(location, owner, pirate_id, 6, location, attack_radius, max_defense_turns)

        # the turn this pirate spawned on
        self.spawn_turn = spawn_turn
        """:type : int"""
        # list of turns this pirate attacked on, in the format [turn, target, turn, target, ...]
        self.attack_turns = [-1000, -1]
        """:type : list[int]"""
        # the turn this pirate died on
        self.die_turn = None
        """:type : int | None"""
        # list of turns this pirate became drunk on
        self.drink_turns = [-1000]
        """:type : list[int]"""
        # list of orders this pirate wants to execute
        self.orders = []
        """:type : list[str]"""
        self.reason_of_death = ''
        """:type : str"""

        # list of ints, indicating the value of the treasure the pirate carries. (0 if the pirate didn't carry a
        # treasure in a certain turn)
        self.treasure_history = []
        """:type : list[int]"""
        # list of booleans, indicates if the pirate was drunk this turn
        self.drink_history = []
        """:type : list[bool]"""

        # defense
        # list of turns this pirate defended on
        self.defense_turns = [-1000]
        """:type : list[int]"""

        # attack powerup
        # the amount of turns until this pirate will no longer have attack powerup
        self.attack_powerup_active_turns = 0
        """:type : int"""
        # list of the attack_radius this pirate have on each turn
        self.attack_radius_history = []
        """:type : list[int]"""

        # rob powerup
        # the amount of turns until this pirate will no longer have rob powerup
        self.rob_powerup_active_turns = 0
        """:type : int"""
        # list of booleans, indicates if the pirate had rob powerup or not on each turn
        self.rob_powerup_history = []
        """:type : list[bool]"""

        # speed powerup
        # the amount of turns until this pirate will no longer have speed powerup
        self.speed_powerup_active_turns = 0
        """:type : int"""
        # list of booleans, indicates if the pirate had speed powerup or not on each turn
        self.speed_powerup_history = []
        """:type : list[bool]"""

    def __str__(self):
        """
        Returns a string describing the pirate

        :return: a string describing the pirate
        :rtype: str
        """
        return '(%s, %s, %s, %s, %s, %s, %s)' % \
               (self.location, self.owner.id, self.id, self.spawn_turn, self.die_turn, self.turns_to_sober,
                ''.join(self.orders))


class Player(BasePlayer):
    """
    The player object, and all of it's attributes.
    """
    pass
