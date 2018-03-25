# !/usr/bin/env python
"""
A basic game base class. Games run by the engine should inherit from it and implement it's functions.
"""


class Game(object):
    """
    The base Game class, all games run by the engine should inherit from it.
    """
    def __init__(self):
        """
        Creates a new instance of the Game class.

        """
        pass

    # common functions for all games used by engine

    def start_game(self):
        """
        Starts the game

        """
        pass

    def start_turn(self):
        """
        Do things needed for start of turn (cleanup, etc...)

        """
        pass

    def finish_turn(self):
        """
        Do things needed for finishing a turn (resolving orders, scoring, etc...)

        """
        pass

    def finish_game(self):
        """
        Do things needed for finishing a game (scoring, etc...)

        """
        pass

    def kill_player(self, player_id):
        """
        Remove a player from the game, may be a crashed/timed out bot

        :param player_id: The id of the player to kill
        :type player_id: int
        """
        pass

    def is_alive(self, player_id):
        """
        Return if a player is alive, might be removed by game mechanics

        :param player_id: the id of the player to check
        :type player_id: id
        :return: Whether the player is alive or not
        :rtype: bool
        """
        pass

    def game_over(self):
        """
        Returns if the game is over due to a win condition

        :return: Whether the game is over or not
        :rtype: bool
        """
        pass

    def get_state(self):
        """
        Used by engine to get the current game state for the streaming format
        :return: The current game state
        :rtype: str
        """
        pass

    def get_player_start(self, player_id=None):
        """
        Used for turn 0, sending minimal info for bot to load, when passed none, the output is used at the start of the
        streaming format.

        :param player_id: The id of the player to send the information for
        :type player_id: int
        :return: The game start information
        :rtype: str
        """
        pass

    def get_player_state(self, player_id):
        """
        Used for sending state to bots for each turn

        :param player_id: The id of the player to send the information to
        :type player_id: int
        :return: The current game state as viewed by the player
        :rtype: str
        """
        pass

    def do_moves(self, player_id, moves):
        """
        Process a single player's moves, may be appropriate to resolve during finish turn

        :param player_id: the id of the player to process the orders of
        :type player_id: int
        :param moves: the orders of the player
        :type moves: list[dict[str, any]]
        :return: A tuple of the valid orders, and 2 lists of strings describing the invalid and ignored orders.
        :rtype: (list[dict[str, any]], list[str], list[str])
        """
        pass

    def get_scores(self):
        """
        Used for ranking

        """
        pass

    def get_stats(self):
        """
        Can be used to determine fairness of game and other stuff for visualizers

        """
        pass

    def get_replay(self):
        """
        Used for getting a compact replay of the game

        """
        pass
