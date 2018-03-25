"""
Parses the cmd parameters, and executes the game
"""


import argparse
import ConfigParser
import os
import sys

from lib import playgame

CONFIG_FILE_NAME = os.path.join('lib', 'game_cfg.txt')


def main(argv):
    """
    Runs the game using the arguments given, with the arguments in the config as the default ones

    :param argv: a list of the arguments given to the program (except the program's name)
    :type argv: list[str]
    """
    config_options = parse_config(CONFIG_FILE_NAME)
    arguments_options = parse_args(argv, **config_options)
    playgame.main(arguments_options)


def parse_config(config_file_name):
    """
    Parses the config file given

    :param config_file_name: the name of the config file to parse
    :type config_file_name: str
    :return: a dictionary, where each key-value pair represents a key-value pair in the config file
    :rtype: dict[str, str]
    """

    config = ConfigParser.ConfigParser()
    config.read(config_file_name)
    main_cfg_section = config.sections()[0]

    options = config.options(main_cfg_section)
    results = {}
    for option in options:
        try:
            results[option] = config.get(main_cfg_section, option)
        except:
            print('exception on %s!' % option)
            results[option] = None
    return results


def parse_args(args, **defaults):
    """
    Parses the arguments given

    :param args: the arguments to parse
    :type args: list[str]
    :param defaults: the default values of the arguments
    :type defaults: dict[str, str]
    :return: a populated namespace containing the arguments
    :rtype: Namespace
    """
    parser = argparse.ArgumentParser()
    parser.set_defaults(**defaults)

    parser.add_argument('--show-traceback', action='store_true',
                        help='show the traceback when errors occur in the engine')

    # the pickled engine to start from
    parser.add_argument('-i', '--load-pickled-game',
                        default=None,
                        help='Name of the pickled game to use when starting')
    # the pickled file to create
    parser.add_argument('-s', '--dump-pickled-game',
                        default=None,
                        help='Name of the pickled game to create at the end of the game')
    parser.add_argument('-T', '--dump-pickled-game-turns', nargs='+',
                        default=None,
                        help='List of the turns in which to output a pickle file; Supply with -1 for a pickle when the'
                             'game ends')

    parser.add_argument('--regression-output', dest='regression_output_path',
                        default=None,
                        help='Name of the regression file to create at the end of the game')

    # maximum number of turns that the game will be played
    parser.add_argument('-t', '--turns',
                        type=int,
                        help='Maximum number of turns in the game')

    # the turn in which the game will start
    parser.add_argument('-f', '--first-turn',
                        type=int, default=-1,
                        help='First turn of the game')

    parser.add_argument('--serial',
                        action='store_true',
                        help='Run bots in serial, instead of parallel.')

    parser.add_argument('--recover-errors',
                        default=False, action='store_true',
                        help='Instruct runners to recover errors in do_turn')

    parser.add_argument('--abort-errors', dest='recover_errors',
                        action='store_false',
                        help='Instruct runners to not recover errors in do_turn')

    parser.add_argument('--turn-time',
                        default=100, type=int,
                        help='Amount of time to give each bot, in milliseconds')
    parser.add_argument('--load-time',
                        default=5000, type=int,
                        help='Amount of time to give for load, in milliseconds')

    parser.add_argument('--extra-time',
                        default=1000, type=int,
                        help='Amount of extra total time to give each bot (in serial mode), in milliseconds')

    parser.add_argument('-r', '--rounds',
                        default=1, type=int,
                        help='Number of rounds to play')
    parser.add_argument('--player-seed',
                        default=None, type=int,
                        help='Player seed for the random number generator')
    parser.add_argument('--engine-seed',
                        default=None, type=int,
                        help='Engine seed for the random number generator')

    parser.add_argument('--strict',
                        action='store_true', default=False,
                        help='Strict mode enforces valid moves for bots')
    parser.add_argument('--capture-errors',
                        action='store_true', default=False,
                        help='Capture errors and stderr in game result')
    parser.add_argument('--end-wait',
                        default=0.25, type=float,
                        help='Seconds to wait at end for bots to process end')
    parser.add_argument('--secure-jail',
                        action='store_true', default=False,
                        help='Use the secure jail for each bot (*nix only)')
    parser.add_argument('--fill',
                        action='store_true', default=False,
                        help='Fill up extra player starts with last bot specified')
    parser.add_argument('-p', '--position',
                        default=0, type=int,
                        help='Player position for first bot specified')

    parser.add_argument('--no-launch',
                        action='store_true', default=False,
                        help='Prevent visualizer from launching')

    # pirates specific game options
    game_group = parser.add_argument_group('Game Options', 'Options that affect the game mechanics for pirates')
    game_group.add_argument('--attack-radius-2',
                            type=int,
                            help='Attack radius of pirate ships squared')
    game_group.add_argument('--bermuda-zone-radius-2',
                            type=int,
                            help='Bermuda zone radius squared')
    game_group.add_argument('--bermuda-zone-active-turns',
                            type=int,
                            help='Number of turns for bermuda zone to be on')
    game_group.add_argument('--required-scripts-num',
                            type=int,
                            help='Number of needed scripts to summon bermuda zone')
    game_group.add_argument('--max-points',
                            type=int,
                            help='Points to reach to end game')
    game_group.add_argument('--randomize-sail-options',
                            default=0, type=int,
                            help='Do we want to randomize sail options')
    game_group.add_argument('--actions-per-turn',
                            type=int,
                            help='How many actions can be performed by player in one turn')
    game_group.add_argument('--reload-turns',
                            type=int,
                            help='How many turns ship can not move after attacking')
    game_group.add_argument('--defense-reload-turns',
                            type=int,
                            help='How many turns ship can not move after defending')
    game_group.add_argument('--max-defense-expiration', dest='max_defense_turns',
                            type=int,
                            help='How many turns till pirate ship defense expires')
    game_group.add_argument('--treasure-spawn-turns',
                            type=int,
                            help='How many turns for a treasure to respawn after successfully unloaded')
    game_group.add_argument('--spawn-turns',
                            type=int,
                            help='Turns for unit to respawn')
    game_group.add_argument('--turns-to-sober',
                            type=int,
                            help='Turns for unit to sober up')
    game_group.add_argument('--cutoff-turn', type=int, default=150,
                            help='Number of turns cutoff percentage is maintained to end game early')
    game_group.add_argument('--cutoff-percent', type=float, default=0.85,
                            help='Number of turns cutoff percentage is maintained to end game early')
    game_group.add_argument('--debug-max-count',
                            default=10000, type=int,
                            help='Maximum number of debug message to be stored in replay data')
    game_group.add_argument('--debug-max-length',
                            default=200000, type=int,
                            help='Maximum total length of debug message to be stored in replay data')
    game_group.add_argument('--cloak-duration',
                            type=int,default=20,
                            help='How many turns till pirate ship cloak expires')
    game_group.add_argument('--cloak-reload-turns',
                            type=int,default=15,
                            help='How many turns till player can cloak again')
    # the log directory must be specified for any logging to occur, except:
    #    bot errors to stderr
    #    verbose levels 1 & 2 to stdout and stderr
    #    profiling to stderr
    # the log directory will contain
    #    the replay or stream file used by the visualizer, if requested
    #    the bot input/output/error logs, if requested    
    log_group = parser.add_argument_group('Logging Options', 'Options that control the logging')
    log_group.add_argument('-g', '--game', dest='game_id', default=0, type=str,
                           help='game id to start at when numbering log files')
    log_group.add_argument('-l', '--log-dir', default=None,
                           help='Directory to dump replay files to.')
    log_group.add_argument('--debug-in-replay',
                           action='store_true', default=False,
                           help='Specify if should insert debug/warning/error prints in replay file')
    log_group.add_argument('-R', '--log-replay',
                           action='store_true', default=False),
    log_group.add_argument('-S', '--log-stream',
                           action='store_true', default=False),
    log_group.add_argument('-I', '--log-input',
                           action='store_true', default=False,
                           help='Log input streams sent to bots')
    log_group.add_argument('-O', '--log-output',
                           action='store_true', default=False,
                           help='Log output streams from bots')
    log_group.add_argument('-E', '--log-error',
                           action='store_true', default=False,
                           help='log error streams from bots')
    log_group.add_argument('-e', '--log-stderr',
                           action='store_true', default=False,
                           help='additionally log bot errors to stderr')
    log_group.add_argument('-o', '--log-stdout',
                           action='store_true', default=False,
                           help='additionally log replay/stream to stdout')
    # verbose will not print bot input/output/errors
    # only info+debug will print bot error output
    log_group.add_argument('-v', '--verbose',
                           action='store_true', default=False,
                           help='Print out status as game goes.')
    log_group.add_argument('-d', '--debug',
                           action='store_true', default=False,
                           help='Print debug messages from bots.')
    log_group.add_argument('--profile',
                           action='store_true', default=False,
                           help='Run under the python profiler')
    log_group.add_argument('--html', dest='html_file',
                           default=None,
                           help='Output file name for an html replay')

    # the bots AND the map
    parser.add_argument('bot', nargs='+', type=str,
                        help='Names of the bots')
    parser.add_argument('--map-file', dest='map', type=str,
                        default=os.path.join('maps', 'default_map.map'),
                        help='Name of the map')
    return parser.parse_args(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
