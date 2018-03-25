#!/usr/bin/env python
from __future__ import print_function
import traceback
import sys
import os
import shutil
import zipfile
import cProfile
import tempfile
import visualizer.visualize_locally
import json

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import cPickle

from pirates import PiratesGame

# verify we are running in python 2.7
if not (sys.version_info[0] == 2 and sys.version_info[1] == 7):
    print("You are running from python %d.%d. Run from Python 2.7 instead!" % list(sys.version_info[0:2]))
    sys.exit(-1)
try:
    from engine import run_game
except ImportError:
    # this can happen if we're launched with cwd outside our own dir
    # get our full path, then work relative from that
    cmd_folder = os.path.dirname(os.path.abspath(__file__))
    if cmd_folder not in sys.path:
        sys.path.insert(0, cmd_folder)
    # try again
    from engine import run_game

# make stderr red text
try:
    import colorama

    colorama.init()
    colorize = True
    color_default = colorama.Fore.RED
    color_reset = colorama.Style.RESET_ALL
except:
    colorize = False
    color_default = None
    color_reset = None


class Colorize(object):
    def __init__(self, file1, color=color_default):
        self.file = file1
        self.color = color
        self.reset = color_reset

    def write(self, data):
        """
        Writes a given data to the file

        :param data: the data to write
        :type data: str
        """
        if self.color:
            self.file.write(''.join(self.color))
        self.file.write(data)
        if self.reset:
            self.file.write(''.join(self.reset))

    def flush(self):
        """ Flushes the file """
        self.file.flush()

    def close(self):
        """ closes the file """
        self.file.close()


if colorize:
    stderr = Colorize(sys.stderr)
else:
    stderr = sys.stderr


class Comment(object):
    def __init__(self, file1):
        self.file = file1
        self.last_char = '\n'

    def write(self, data):
        """
        Write a given data to the file

        :param data: the data to write
        :type data: str
        """
        for char in data:
            if self.last_char == '\n':
                self.file.write('# ')
            self.file.write(char)
            self.last_char = char

    def flush(self):
        """ Flushes the file """
        self.file.flush()

    def close(self):
        """ Closes the file """
        self.file.close()


class Tee(object):
    """ Write to multiple files at once """

    def __init__(self, *files):
        self.files = files

    def write(self, data):
        """
        Writes a given data to the file

        :param data: the data to write
        :type data: str
        """
        for file1 in self.files:
            file1.write(data)

    def flush(self):
        """ Flushes the file """
        for file1 in self.files:
            file1.flush()

    def close(self):
        """ Closes the file """
        for file1 in self.files:
            file1.close()


class ZipEncapsulator(object):
    """  List of temporary folders used to be deleted """

    def __init__(self):
        self.tempdirs = []

    def unzip(self, zipfilename):
        """
        Gets a path to zipped directory, unzip it, and returns the path to the unzipped directory

        :param zipfilename: the path to the zipped directory
        :type zipfilename: str
        :return: path to the unzipped directory
        :rtype: str
        """
        # here we assume that the 
        self.tempdirs.append(tempfile.mkdtemp(dir=os.path.dirname(zipfilename)))
        with zipfile.ZipFile(zipfilename, 'r') as zippy:
            zippy.extractall(self.tempdirs[-1])
            try:
                new_target = self.tempdirs[-1]
            except:
                print('Empty zipfile found!')
                traceback.print_exc()
                return -1
        return new_target

    def close(self):
        """ Deletes all the temporary directories """
        [shutil.rmtree(td) for td in self.tempdirs]


def main(arguments):
    """
    Validates that the bots' names and the map in the given arguments exists, and then tries to run the game with the
    given arguments

    :param arguments: A namespace, containing the arguments for the run
    :type arguments: Namespace
    :return: -1 on fail, 0 on success
    :rtype: int
    """
    if not len(arguments.bot) == 2:
        print("No 2 bots are present!")
        return -1
    for bot_num, bot_path in enumerate(arguments.bot, start=1):
        if not os.path.exists(bot_path):
            print("Bot #{n} does not exist!".format(n=bot_num))
            return -1
    if not os.path.exists(arguments.map):
        print("The map does not exist!")
        return -1
    try:
        if arguments.profile:
            # put profile file into output dir if we can
            prof_file = "pirates.profile"
            if arguments.log_dir:
                prof_file = os.path.join(arguments.log_dir, prof_file)
            # cProfile needs to be explitly told about out local and global context
            print("Running profile and outputting to {0}".format(prof_file, ), file=stderr)
            cProfile.runctx("run_rounds(arguments)", globals(), locals(), prof_file)
        else:
            run_rounds(arguments)
        return 0
    except Exception:
        traceback.print_exc()
        return -1


def run_rounds(arguments):
    """
    Parses the given arguments and runs the game with them by calling the engine, then receiving the game
    result from the engine and passing it on to the visualizer

    :param arguments: A namespace, containing the arguments for the run
    :type arguments: Namespace
    """

    def get_bot_paths(cmd, zip_encapsulator):
        """
        Gets the path to a single bot.

        :param cmd: the name of the bot file
        :type cmd: string
        :param zip_encapsulator: a zip encapsulator (object that knows how to unzip files)
        :type zip_encapsulator: ZipEncapsulator
        :return: working_dir: the path of the bot directory
            filepath: the path of the bot file
            botname: the name of the bot file
        :rtype: (str, str, str)
        """

        filepath = os.path.realpath(cmd)
        if filepath.endswith('.zip'):
            # if we get zip file - override original filepath for abstraction
            filepath = zip_encapsulator.unzip(filepath)
        working_dir = os.path.dirname(filepath)
        bot_name = os.path.basename(cmd).split('.')[0]
        return working_dir, filepath, bot_name

    # this split of options is not needed, but left for documentation
    game_options = {
        "map": arguments.map,
        "attack_radius2": arguments.attack_radius_2,
        "bermuda_zone_radius_2": arguments.bermuda_zone_radius_2,
        "bermuda_zone_active_turns": arguments.bermuda_zone_active_turns,
        "required_scripts_num": arguments.required_scripts_num,
        "load_time": arguments.load_time,
        "turn_time": arguments.turn_time,
        "recover_errors": arguments.recover_errors,
        "turns": arguments.turns,
        "cutoff_turn": arguments.cutoff_turn,
        "cutoff_percent": arguments.cutoff_percent,
        "max_points": arguments.max_points,
        "randomize_sail_options": arguments.randomize_sail_options,
        "actions_per_turn": arguments.actions_per_turn,
        "reload_turns": arguments.reload_turns,
        "defense_reload_turns": arguments.defense_reload_turns,
        "max_defense_turns": arguments.max_defense_turns,
        "treasure_spawn_turns": arguments.treasure_spawn_turns,
        "spawn_turns": arguments.spawn_turns,
        "turns_to_sober": arguments.turns_to_sober,
        "cloak_duration": arguments.cloak_duration,
        "cloak_reload_turns": arguments.cloak_reload_turns}

    if arguments.player_seed is not None:
        game_options['player_seed'] = arguments.player_seed
    if arguments.engine_seed is not None:
        game_options['engine_seed'] = arguments.engine_seed
    engine_options = {
        "show_traceback": arguments.show_traceback,
        "load_time": arguments.load_time,
        "turn_time": arguments.turn_time,
        "extra_time": arguments.extra_time,
        "map_file": arguments.map,
        "turns": arguments.turns,
        "debug_in_replay": arguments.debug_in_replay,
        "debug_max_length": arguments.debug_max_length,
        "debug_max_count": arguments.debug_max_count,
        "log_replay": arguments.log_replay,
        "log_stream": arguments.log_stream,
        "log_input": arguments.log_input,
        "log_output": arguments.log_output,
        "log_error": arguments.log_error,
        "serial": arguments.serial,
        "strict": arguments.strict,
        "capture_errors": arguments.capture_errors,
        "secure_jail": arguments.secure_jail,
        "end_wait": arguments.end_wait}

    for round1 in range(arguments.rounds):
        # initialize bots
        zip_encapsulator_object = ZipEncapsulator()
        bots = [get_bot_paths(bot, zip_encapsulator_object) for bot in arguments.bot]
        bot_count = len(bots)

        # initialize game
        game_id = "{0}.{1}".format(arguments.game_id, round1) if arguments.rounds > 1 else arguments.game_id
        with open(arguments.map, 'r') as map_file:
            game_options['map'] = map_file.read()
        if arguments.engine_seed:
            game_options['engine_seed'] = arguments.engine_seed + round1
        game_options['bot_names'] = map(lambda some_bot: some_bot[2], bots)

        game_options['init_turn'] = max(arguments.first_turn, 0)

        if arguments.load_pickled_game:
            with open(arguments.load_pickled_game, 'r') as f:
                game = cPickle.load(f)
                game.init_turn = game.turn
        else:
            game = PiratesGame(game_options)

        # insure correct number of bots, or fill in remaining positions
        if game.num_players != len(bots):
            print("Incorrect number of bots for map.  Need {0}, got {1}"
                  .format(game.num_players, len(bots)), file=stderr)

        # initialize file descriptors
        if arguments.log_dir and not os.path.exists(arguments.log_dir):
            os.mkdir(arguments.log_dir)
        if not arguments.log_replay and not arguments.log_stream and (arguments.log_dir or arguments.log_stdout):
            arguments.log_replay = True
        replay_path = None  # used for visualizer launch

        if arguments.log_replay:
            if arguments.log_dir:
                replay_path = os.path.join(arguments.log_dir, '{0}.replay'.format(game_id))
                engine_options['replay_log'] = open(replay_path, 'w')
            if arguments.log_stdout:
                if 'replay_log' in engine_options and engine_options['replay_log']:
                    engine_options['replay_log'] = Tee(sys.stdout, engine_options['replay_log'])
                else:
                    engine_options['replay_log'] = sys.stdout
        else:
            engine_options['replay_log'] = None

        if arguments.log_stream:
            if arguments.log_dir:
                engine_options['stream_log'] = open(os.path.join(arguments.log_dir, '{0}.stream'.format(game_id)), 'w')
            if arguments.log_stdout:
                if engine_options['stream_log']:
                    engine_options['stream_log'] = Tee(sys.stdout, engine_options['stream_log'])
                else:
                    engine_options['stream_log'] = sys.stdout
        else:
            engine_options['stream_log'] = None

        if arguments.log_input and arguments.log_dir:
            engine_options['input_logs'] = [
                open(os.path.join(arguments.log_dir, '{0}.bot{1}.input'.format(game_id, i)), 'w')
                for i in range(bot_count)]
        if arguments.log_output and arguments.log_dir:
            engine_options['output_logs'] = [
                open(os.path.join(arguments.log_dir, '{0}.bot{1}.output'.format(game_id, i)), 'w')
                for i in range(bot_count)]
        if arguments.log_error and arguments.log_dir:
            if arguments.log_stderr:
                if arguments.log_stdout:
                    engine_options['error_logs'] = [Tee(Comment(stderr), open(
                        os.path.join(arguments.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w'))
                                                    for i in range(bot_count)]
                else:
                    engine_options['error_logs'] = [
                        Tee(stderr, open(os.path.join(arguments.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w'))
                        for i in range(bot_count)]
            else:
                engine_options['error_logs'] = [
                    open(os.path.join(arguments.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w')
                    for i in range(bot_count)]
        elif arguments.log_stderr:
            if arguments.log_stdout:
                engine_options['error_logs'] = [Comment(stderr)] * bot_count
            else:
                engine_options['error_logs'] = [stderr] * bot_count

        if arguments.verbose:
            if arguments.log_stdout:
                engine_options['verbose_log'] = Comment(sys.stdout)
            else:
                engine_options['verbose_log'] = sys.stdout

        if arguments.debug:
            engine_options['debug_log'] = sys.stdout

        engine_options['game_id'] = game_id
        if arguments.rounds > 1:
            print('# playgame round {0}, game id {1}'.format(round1, game_id))

        # intercept replay log so we can add player names
        if arguments.log_replay:
            intcpt_replay_io = StringIO()
            real_replay_io = engine_options['replay_log']
            engine_options['replay_log'] = intcpt_replay_io

        if arguments.dump_pickled_game:
            # parse the turns in which to create a pickled file, if there are so
            if arguments.dump_pickled_game_turns:
                try:
                    pickled_game_turns = [int(turn) for turn in arguments.dump_pickled_game_turns]
                except ValueError:
                    raise ValueError('Each value in -T/--dump-pickled-game-turns must be an integer!')
            else:
                raise Exception('Please supply the turns in which to dump the game, using -T!')
            dump_pickled_game_basename = os.path.splitext(arguments.dump_pickled_game)[0]
            dump_pickled_games = {}
            for turn in pickled_game_turns:
                # if turn == -1, then it means the last turn
                if turn == -1:
                    dump_pickled_games[turn] = dump_pickled_game_basename + '_last.pkl'
                else:
                    dump_pickled_games[turn] = dump_pickled_game_basename + '_' + str(turn) + '.pkl'
            engine_options['dump_pickled_games'] = dump_pickled_games
        # if dump_pickled_game_turns is not empty but an out name wasn't supplied
        elif arguments.dump_pickled_game_turns:
            raise Exception('Please supply a name for the pickled game file, using -s!')

        if arguments.regression_output_path:
            engine_options['regression_output_path'] = arguments.regression_output_path

        result = run_game(game, bots, engine_options)

        # destroy temporary directories
        zip_encapsulator_object.close()

        # add player names, write to proper io, reset back to normal
        if arguments.log_replay:
            replay_json = json.loads(intcpt_replay_io.getvalue())
            replay_json['playernames'] = [b[2] for b in bots]
            real_replay_io.write(json.dumps(replay_json))
            intcpt_replay_io.close()
            engine_options['replay_log'] = real_replay_io

        # close file descriptors
        if engine_options['stream_log']:
            engine_options['stream_log'].close()
        if engine_options['replay_log']:
            engine_options['replay_log'].close()
        if 'input_logs' in engine_options:
            for input_log in engine_options['input_logs']:
                input_log.close()
        if 'output_logs' in engine_options:
            for output_log in engine_options['output_logs']:
                output_log.close()
        if 'error_logs' in engine_options:
            for error_log in engine_options['error_logs']:
                error_log.close()
        if replay_path:
            if arguments.no_launch:
                if arguments.html_file:
                    visualizer.visualize_locally.launch(replay_path, True, arguments.html_file)
            else:
                if arguments.html_file is None:
                    visualizer.visualize_locally.launch(replay_path,
                                                        generated_path="replay.{0}.html".format(game_id))
                else:
                    visualizer.visualize_locally.launch(replay_path,
                                                        generated_path=arguments.html_file)
