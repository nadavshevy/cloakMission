#!/usr/bin/env python

from __future__ import print_function
import time
import traceback
import os
import base64
import sys
from os import walk
from os.path import splitext, join
import cPickle
from sandbox import get_sandbox

import json  # Used for serializing the data communication.

if sys.version_info >= (3,):
    # noinspection PyShadowingBuiltins
    def unicode(s):
        return s


class RunnerLogger(object):
    def __init__(self, input_logs=None, output_logs=None, error_logs=None):
        """
        Logger to handle the Runner logging

        :param input_logs: the input log buffer
        :type input_logs: file
        :param output_logs: the output log buffer
        :type output_logs: file
        :param error_logs: the error log buffer
        :type error_logs: file
        """
        self.input_log = input_logs
        self.output_log = output_logs
        self.error_log = error_logs

    @staticmethod
    def write_to_log(msg, log_object):
        """
        Logs a message to a log object if there is one

        :param msg: the data to be logged
        :type msg: any
        :param log_object: input or output log
        :type log_object:
        """
        if log_object:
            log_object.write(str(msg))
            log_object.flush()

    def input(self, msg):
        """
        Logs the input to the input log if there is one

        :param msg: the data to be logged
        :type msg: any
        """
        self.write_to_log(msg, self.input_log)

    def output(self, msg):
        """
        Logs the output to the output log if there is one

        :param msg: the data to be logged
        :type msg: any
        """
        self.write_to_log(msg, self.output_log)

    def error(self, msg):
        """
        Logs the error to the error log if there is one

        :param msg: the data to be logged
        :type msg: any
        """
        self.write_to_log(msg, self.error_log)


class EngineLogger(object):
    # TODO - implement it to log the engine events
    # a static variables that represent the logging level ( will be changed when will move to python logger )
    LEVEL_NONE = 0
    LEVEL_DEBUG = 1
    LEVEL_INFO = 2
    LEVEL_WARNING = 3
    LEVEL_ERROR = 4

    def __init__(self, buff, level):
        """
        Log handler for the Engine events

        :param buff: the output buffer
        :type buff: file
        :param level: Logging level ( 0: NoFilter, 1:Debug, 2:Info, 3:warnings, 4:Error)
        :type level: int
        """
        self.buffer = buff
        self.level = level

    def _write_data(self, data):
        """
        the handler for the data writing to the buffer
        """
        self.buffer.write(data)

    def debug(self, msg):
        """
        Logs the debug to the debug log if the level is set

        :param msg: the data to be logged
        :type msg: str
        """
        if self.level <= EngineLogger.LEVEL_DEBUG:
            self._write_data(msg)

    def info(self, msg):
        """
        Logs the info to the info log if the level is set

        :param msg: the data to be logged
        :type msg: str
        """
        if self.level <= EngineLogger.LEVEL_INFO:
            self._write_data(msg)

    def warning(self, msg):
        """
        Logs the warning to the warning log if the level is set

        :param msg: the data to be logged
        :type msg: str
        """
        if self.level <= EngineLogger.LEVEL_WARNING:
            self._write_data(msg)

    def error(self, msg):
        """
        Logs the error to the error log if the level is set

        :param msg: the data to be logged
        :type msg: str
        """
        if self.level <= EngineLogger.LEVEL_ERROR:
            self._write_data(msg)


def get_java_path():
    """
    Returns the path for the java.

    :return: the path for the java.
    :rtype: str
    """
    if os.name != "nt":
        return 'java'
    # TODO: search path as well!
    # TODO: actually run os.system('java -version') to see version

    sys_drive = os.getenv("SystemDrive") + os.sep
    javas = []

    paths = [os.path.join(sys_drive, "Program Files", "java"),
             os.path.join(sys_drive, "Program Files (x86)", "java"),
             os.path.join(sys_drive, "Java")]

    for path in paths:
        if os.path.exists(path):
            javas += [os.path.join(path, i) for i in os.listdir(path)]

    javas.reverse()  # this will make us pick the higher version
    for java in javas:
        if 'jdk' in java.lower() and any([ver in java for ver in ['1.6', '1.7', '1.8']]):
            return os.path.join(java, "bin", "java.exe")
    print("Cannot find path of Java JDK version 1.6 or over!")
    # we should really quit but since we don't yet search path - first try default
    return 'java'


class Runner(object):
    def __init__(self, runner, name, game_id, max_debug_length, max_debug_count, status='alive',
                 input_logs=None, output_logs=None, error_logs=None):
        """
        Initialize the runner

        :param runner: the sandbox runner object
        :type runner: sandbox.House
        :param name: the name of the bot
        :type name: str
        :param game_id:the id of the runner
        :type game_id: int
        :param max_debug_length: the max length of the debug messages amount
        :type max_debug_length: int
        :param max_debug_count: the max size of the memory the debug msgs takes
        :type max_debug_count: int
        :param status:  the default status of the runner
        :type status: str
        :param input_logs: log for the input from the bot to the game( downstream  )
        :type input_logs: file
        :param output_logs: log for the output from the game to the bot( upstream  )
        :type output_logs: file
        :param error_logs: log buffer for the errors of the runner\bot
        :type error_logs: file
        """
        self.game_id = game_id
        self.name = name

        self.turn = 0
        self.status = status

        self._runner = runner
        self.logger = RunnerLogger(input_logs=input_logs, output_logs=output_logs, error_logs=error_logs)

        self.max_debug_length = max_debug_length
        self.max_debug_msg_amount = max_debug_count
        self.debug_max_reached = False
        self.debug_size_counter = 0
        self.debug_amount_counter = 0

        self.debug_msgs = []
        self.error_lines = []
        self.actions = {}

    def send(self, data):
        """
        send a data to the runner
        """
        data_str = Runner.format_data(data)

        self._runner.write(data_str)
        self.logger.input(data_str)

    def recv(self):
        """
        receive the data using the protocol and log it to the

        :return: data from the runner
        :rtype: dict
        """
        data = self._runner.read_line()

        self.logger.output(data)
        return Runner.parse_data(data)

    def add_error_msg(self, msgs, turn):
        """
        Adds an error msg to the logger and to the debug list for the replay data

        :param msgs: the messages to be added this turn
        :type msgs: list[str]
        :param turn: the turn number of the error msg
        :type turn: int
        """
        for msg in msgs:
            self.logger.error(str(msg) + "\n")
        self.debug_msgs.append([turn, 2, msgs])

    def add_debug_msg(self, msgs, turn, level=0):
        """
        add a msg to the debug queue

        :param msgs: the list of the wanted msgs
        :type msgs: list[str]
        :param turn: the turn of the debug msg
        :type turn: int
        :param level: the level of the debug msg (used for computability of the replay data)
        :type level: int
        :return:
        """
        # TODO - add max debug quota check
        if not msgs:
            return

        if not self.debug_max_reached:
            msgs_size = sum(map(len, msgs))
            self.debug_size_counter += msgs_size
            self.debug_amount_counter += len(msgs)

            exceeded_max_amount = self.debug_amount_counter > self.max_debug_msg_amount
            exceeded_max_length = self.debug_size_counter > self.max_debug_length

            if exceeded_max_amount or exceeded_max_length:
                self.debug_max_reached = True
                self.debug_msgs.append([turn + 1, 2, ["Exceeded debug messages limit."]])
                self.logger.error("Exceeded debug messages limit.\n")

            else:
                self.debug_msgs.append([turn + 1, level, msgs])

    @staticmethod
    def format_data(data, prettify=False):
        """
        This function formats the data to send using json.

        :param data: The data to format using Json.
        :type data: list or tuple or int or str or dict
        :param prettify: Whether or not to format the data prettily, default is False.
        :type prettify: bool
        :return: The formatted data.
        :rtype: str
        --Warning--
        Tuples will be turned into lists by the json.
        """
        if prettify:
            return json.dumps(data, indent=4, sort_keys=True) + '\n'
        else:
            data_str = json.dumps(data)
            return data_str + '\n'

    @staticmethod
    def parse_data(data_str):
        """
        This turns the received data into a dictionary or list using json.

        :param data_str: The input data to un format.
        :type data_str: str
        :return: A json dictionary of the data. Or an empty dictionary if none was received.
        :rtype: dict
        --Warning--
        Tuples will be turned into lists in the json data.
        """
        # Json data might be incorrect so try and catch is used.
        try:
            return json.loads(data_str)
        except (ValueError, TypeError):
            return dict()

    def __repr__(self):
        """
        Represent the class
        :return: the class str representation
        :rtype: str
        """
        return "<Runner ID:{} Name:{}>".format(self.game_id, self.name)

    def __getattr__(self, item):
        """
        if no attribute with this name here take it from the sandbox

        :param item: the item requested and not in the runner wrapper
        :return: the requested parameter from the runner object
        :rtype: Any
        """
        return getattr(self._runner,  item, None)


class RunnerFactory(object):

    @staticmethod
    def get_runner(bot, game_id, max_debug_length, max_debug_count,
                   input_logs=None, output_logs=None, error_logs=None, secure=None,
                   extra_cmd_args=None):
        """
        Creates a runner and returns it

        :param bot: the tuple of the bot commands and working directories
        :type bot: tuple
        :param game_id: the id of the runner in the game
        :type game_id: int
        :param max_debug_length: the max quota of the size ( memory ) of the msgs
        :type max_debug_length: int
        :param max_debug_count: the quota of the the amount of msgs allowed
        :type max_debug_count: int
        :param input_logs: the input log buffer
        :type input_logs: file / None
        :param output_logs: the output log buffer
        :type output_logs: file / None
        :param error_logs: the error log buffer
        :type error_logs: file / None
        :param secure: flag if the sandbox should be secure ( for the sandbox)
        :type secure: bool
        :param extra_cmd_args: extra arguments for the cmd to run the runner ( mainly for tests )
        :type extra_cmd_args: list[str]
        :return: A runner object
        :rtype: Runner
        """
        bot_cwd, bot_path, bot_name = bot
        # generate the appropriate command from file extension
        bot_cmd = RunnerFactory.generate_cmd(bot_path)
        if extra_cmd_args:
            bot_cmd += " " + " ".join(extra_cmd_args)

        # generate the sandbox from the bot working directory
        sandbox = get_sandbox(bot_cwd, protected_files=[bot_path], secure=secure)

        if bot_cmd:
            sandbox.start(bot_cmd)

        else:
            # couldn't generate bot command - couldn't recognize the language of the code
            raise RuntimeError("Couldn't recognize code language. Are you sure code files are correct?")

        # ensure it started
        if not sandbox.is_alive:
            sandbox.pause()
            raise RuntimeError('bot %s did not start' % bot_name)

        return Runner(runner=sandbox, name=bot_name, game_id=game_id,
                      max_debug_length=max_debug_length,
                      max_debug_count=max_debug_count,
                      input_logs=input_logs,
                      output_logs=output_logs,
                      error_logs=error_logs)

    @staticmethod
    def generate_cmd(bot_path):
        """
        Generates the command to run and returns other information from the filename given

        :param bot_path: the path to the bot file
        :type bot_path: str
        :return: the command to run and returns other information from the filename given
        :rtype: str
        """

        csh_runner_path = os.path.join(os.path.dirname(__file__), "cshRunner.exe")
        java_runner_path = os.path.join(os.path.dirname(__file__), "javaRunner.jar")
        python_runner_path = os.path.join(os.path.dirname(__file__), "pythonRunner.py")

        command = ''

        lang = RunnerFactory.recognize_language(bot_path)
        if lang == 'python':
            command = 'python "%s" "%s"' % (python_runner_path, bot_path)

        elif lang == 'csh':
            # Run with Mono if Unix. But in the future just receive source code (.cs) and compile on the fly
            if os.name == 'nt':
                command = '"%s" "%s"' % (csh_runner_path, bot_path)
            else:
                command = 'mono --debug %s %s' % (csh_runner_path, bot_path)
        elif lang == 'java':
            command = '"%s" -jar "%s" "%s"' % (get_java_path(), java_runner_path, bot_path)
        else:
            if os.path.isdir(bot_path):
                sys.stdout.write("Could't find code in folder! %s\n" % bot_path)
            else:
                sys.stdout.write(
                    'Unknown file format! %s\nPlease give file that ends with .cs , .java or .py\n' % bot_path)

        return command

    @staticmethod
    def recognize_language(bot_path):
        """
        Recognizes the language a bot is written in (Java, C# or Python)

        :param bot_path: the path to the bot file
        :type bot_path: str
        :return: the language the bot is written in (Java, C#, Python or None)
        :rtype: str or None
        """

        '''First do single file case'''
        if not os.path.isdir(bot_path):
            if bot_path.endswith('.py') or bot_path.endswith('.pyc'):
                return 'python'
            elif bot_path.endswith('.cs'):
                return 'csh'
            elif bot_path.endswith('.java'):
                return 'java'
            else:
                return

        ''' Now handle directory case '''
        java_files = RunnerFactory.find_suffix_in_path(bot_path, '.java')
        csh_files = RunnerFactory.find_suffix_in_path(bot_path, '.cs')
        python_files = RunnerFactory.find_suffix_in_path(bot_path, '.py')

        max_files = max(len(java_files), len(csh_files), len(python_files))

        if max_files == 0:
            return

        if len(java_files) == max_files:
            return 'java'
        elif len(csh_files) == max_files:
            return 'csh'
        elif len(python_files) == max_files:
            return 'python'

        return

    @staticmethod
    def find_suffix_in_path(path, suffix):
        """
        Selects all files with a given suffix in a given directory and all of its sub folders

        :param path: the path of the directory
        :type path: str
        :param suffix: files with this suffix will be selected
        :type suffix: str
        :returns: the files with the given suffix
        :rtype: list[str]
        """
        selected_files = []

        for root, dirs, files in walk(path):
            selected_files += RunnerFactory.select_files(root, files, suffix)

        return selected_files

    @staticmethod
    def select_files(root, files, extension):
        """
        Selects files with a given suffix from a list of files

        :param root: the path to the files containing folder
        :type root: str
        :param files: a list of files to select from
        :type files: list[str]
        :param extension: files with this suffix will be selected
        :type extension: str
        :returns: the files with the given suffix
        :rtype: list[file]
        """

        selected_files = []

        for file_path in files:
            # do concatenation here to get full path
            full_path = join(root, file_path)
            file_ext = splitext(file_path)[1]

            if file_ext == extension:
                selected_files.append(full_path)

        return selected_files


# noinspection PyShadowingNames
class Engine(object):
    def __init__(self, bot_paths, options, game):
        """
        Initializing the game

        :param bot_paths: the paths of the bots
        :type bot_paths: list[tuple(file)]
        :param options: the options for the engine
        :type options: dict
        :param game: the game object
        :type game: Game.game
        """

        self.options = options

        self.show_traceback = options.get('show_traceback')

        self.regression_output_path = options.get('regression_output_path')
        self.regression_data = []

        self.replay_log = options.get('replay_log', None)
        self.stream_log = options.get('stream_log', None)
        self.verbose_log = options.get('verbose_log', None)
        self.debug_log = options.get('debug_log', None)

        self.debug_in_replay = options.get('debug_in_replay', None)
        self.debug_max_length = options.get('debug_max_length', None)
        self.debug_max_count = options.get('debug_max_count', None)

        # file descriptors for bots, should be list matching # of bots
        self.input_logs = options.get('input_logs', [None] * len(bot_paths))
        self.output_logs = options.get('output_logs', [None] * len(bot_paths))
        self.error_logs = options.get('error_logs', [None] * len(bot_paths))

        self.capture_errors = options.get('capture_errors', False)
        self.capture_errors_max = options.get('capture_errors_max', 510)

        self.turns = int(options['turns'])
        self.load_time = float(options['load_time']) / 1000
        self.turn_time = float(options['turn_time']) / 1000
        self.extra_time = float(options['extra_time']) / 1000
        self.strict = options.get('strict', False)
        self.end_wait = options.get('end_wait', 0.0)
        self.secure_flag = options.get('secure_jail', None)

        self.location = options.get('location', 'localhost')
        self.game_id = options.get('game_id', 0)
        self.dump_pickled_games = options.get('dump_pickled_games', {})
        self.is_serial = options.get('serial', False)

        self.dump_pickled_game = options.get('dump_pickled_game', None)

        # TODO : check if those are needed
        self.bots = []
        self.bot_status = []
        self.bot_turns = []

        # TODO : check if those are needed
        self.debug_msgs = [[] for _ in range(len(bot_paths))]
        self.debug_msgs_length = [0 for _ in range(len(bot_paths))]
        self.debug_msgs_count = [0 for _ in range(len(bot_paths))]
        self.debug_msgs_exceeded = [False for _ in range(len(bot_paths))]

        self.bot_paths = bot_paths

        self.logger = EngineLogger(self.debug_log, EngineLogger.LEVEL_DEBUG)  # TODO : Change the level and log buffer

        self.runners = []
        self.game = game
        self.turn_num = self.game.init_turn

    def run_game(self):
        """
        runs the game

        :return: the replay data
        :rtype: dict
        """
        error = ''
        try:
            self.handle_game_logic()

        except Exception as e:
            error = traceback.format_exc()
            sys.stderr.write('Error Occurred\n')
            if self.show_traceback:
                error_desc = str(error)
            else:
                error_desc = type(e).__name__ + ': ' + str(e)
            sys.stderr.write(error_desc + '\n')
            if self.verbose_log:  # TODO - Figure out the new log system
                self.verbose_log.write(error)
                # error = str(e)
        finally:
            if self.end_wait:
                for runner in self.runners:
                    runner.resume()
                if self.verbose_log and self.end_wait > 1:
                    self.verbose_log.write('waiting {0} seconds for bots to process end turn\n'.format(self.end_wait))
                time.sleep(self.end_wait)
            for runner in self.runners:
                if runner.is_alive:
                    runner.kill()
                runner.release()

        game_result = self.get_game_results(error)

        if self.replay_log:
            json.dump(game_result, self.replay_log, sort_keys=True)

        return game_result

    def get_game_results(self, error=None):
        """
        get the game result for the game replay

        :param error: a traceback
        :type error: str
        :return: the game results
        :rtype: dict
        """
        if error:
            game_result = {'error': error}
        else:
            scores = self.game.get_scores()
            game_result = {
                'challenge': self.game.__class__.__name__.lower(),
                'location': self.location,
                'game_id': self.game_id,
                'status': [runner.status for runner in self.runners],
                'playerturns': [runner.turn for runner in self.runners],
                'score': scores,
                'winner_names': [self.bot_paths[win][2] for win in self.game.get_winner()],
                'rank': [sorted(scores, reverse=True).index(x) for x in scores],
                'replayformat': 'json',
                'replaydata': self.game.get_replay(),
                'game_length': self.turn_num,
                'debug_messages': map(lambda runner: runner.debug_msgs, self.runners),
            }
            if self.capture_errors:
                game_result['errors'] = [self.error_logs]
        return game_result

    def handle_game_logic(self):
        """
        Run the game main loop logic
        """
        self.create_runners()

        self.start_game()

        for self.turn_num in range(self.game.init_turn, self.turns + 1):

            self.start_turn()

            self.send_turn_data_to_runners()

            self.recv_runners_actions()

            if self.debug_log:
                self.print_debug_msgs()

            self.handle_error_logs()

            alive_bots = filter(lambda runner: self.game.is_alive(runner.game_id), self.runners)
            if self.turn_num > self.game.init_turn:
                if not self.game.game_over():
                    self.process_orders()
                self.end_turn()

            self.handle_eliminated_runners(alive_bots)
            self.handle_verbose_logs()

            if self.game.game_over():
                break

        self.end_game()

    def create_runners(self):
        """
        Creates runner and remembers them
        also bounds the input, output and error logs to the runner
        """
        id_counter = 0
        for bot_id, path in enumerate(self.bot_paths):
            try:
                runner = RunnerFactory.get_runner(path, id_counter,
                                                  max_debug_length=self.debug_max_length,
                                                  max_debug_count=self.debug_max_count,
                                                  input_logs=self.input_logs[bot_id],
                                                  output_logs=self.output_logs[bot_id],
                                                  error_logs=self.error_logs[bot_id],
                                                  secure=self.secure_flag)

                self.runners.append(runner)
                id_counter += 1

            # if starting the runner failed
            except RuntimeError as e:
                self.game.kill_player(bot_id)
                self.logger.error(str(e))

    def start_game(self):
        """
        handle the start game logic
        """
        # TODO - integrate it here ( or in the game start logic handles)
        if self.stream_log:
            # stream the start info - including non-player info
            self.stream_log.write(self.game.get_player_start())
            self.stream_log.flush()
        if self.verbose_log:
            self.verbose_log.write('running for %s turns\n' % self.turns)

        self.game.start_game()

    def end_game(self):
        """
        send bots final state and score, output to replay file
        """
        if self.dump_pickled_game and -1 in self.dump_pickled_game:
            with open(self.dump_pickled_game[-1], 'wb') as f:
                cPickle.dump(self.game, f)

        if self.regression_output_path:
            with open(self.regression_output_path, 'w') as f:
                json.dump(self.regression_data, f, sort_keys=True)

        self.game.finish_game()

        score_line = 'score %s\n' % ' '.join(map(str, self.game.get_scores()))
        status_line = ''
        if self.game.get_winner() and len(self.game.get_winner()) == 1:
            winner = self.game.get_winner()[0]
            winner_line = 'player %s [%s] is the Winner!\n' % (winner + 1, self.bot_paths[winner][2])
        else:
            winner_line = 'Game finished at a tie - there is no winner'
        status_line += winner_line
        end_line = 'end\nplayers %s\n' % len(self.runners) + score_line + status_line

        if self.stream_log:
            self.stream_log.write(end_line)
            self.stream_log.write(self.game.get_state())
            self.stream_log.flush()
        if self.verbose_log:
            self.verbose_log.write(score_line)
            self.verbose_log.write(status_line)
            self.verbose_log.flush()
        else:
            sys.stdout.write(score_line)
            sys.stdout.write(status_line)

    def start_turn(self):
        """
        handle the start turn logic
        """
        if self.turn_num in self.dump_pickled_games:
            with open(self.dump_pickled_games[self.turn_num], 'wb') as f:
                cPickle.dump(self.game, f)

        if self.turn_num > self.game.init_turn:

            # TODO - Integrate it to the code
            if self.stream_log:
                self.stream_log.write('turn %s\n' % self.turn_num)
                self.stream_log.write('score %s\n' % ' '.join([str(s) for s in self.game.get_scores()]))
                self.stream_log.write(self.game.get_state())
                self.stream_log.flush()

            self.game.start_turn()

    def end_turn(self):
        """
        Handle the end turn logic
        """
        self.game.finish_turn()
        if self.regression_output_path:
            self.regression_data.append(self.game.get_current_regression_data())

    def send_turn_data_to_runners(self):
        """
        Send the current state needed for the runner to start the turn / initialize
        """
        for runner in self.runners:
            if self.game.is_alive(runner.game_id):

                if self.turn_num == self.game.init_turn:
                    state_dict = {'type': 'setup', 'data': self.game.get_player_start(runner.game_id)}

                else:
                    state_dict = {'type': 'turn', 'data': self.game.get_player_state(runner.game_id)}
                    # TODO - Check if this is needed here
                    runner.turn = self.turn_num

                runner.send(state_dict)

    def handle_eliminated_runners(self, live_bots):
        """
        send ending info to eliminated bots
        finds the difference from the list to the current status

        :param live_bots: The bots that were alive at the beginning of the turn
        :type live_bots: [Runner]
        """
        bots_eliminated = filter(lambda runner: not self.game.is_alive(runner.game_id), live_bots)

        for runner in bots_eliminated:
            if self.verbose_log:
                self.verbose_log.write('turn %4d bot %s defeated\n' % (self.turn_num, runner.name))
            if runner.status == 'alive':  # could be invalid move
                runner.status = 'defeated'
                runner.turn = self.turn_num

            if self.end_wait:
                runner.resume()
        if bots_eliminated and self.end_wait:
            if self.verbose_log:
                self.verbose_log.write('waiting {0} seconds for bots to process end turn\n'.format(self.end_wait))
            time.sleep(self.end_wait)
        for runner in bots_eliminated:
            runner.kill()

    def handle_error_logs(self):
        """
        Handle the error logs from the runners
        """
        for runner in self.runners:
            if runner.error_lines:
                msg = unicode('\n').join(runner.error_lines) + unicode('\n')
                runner.add_error_msg([msg], turn=self.turn_num)
        for runner in self.runners:
            if runner.status is not None:
                runner.turn = self.turn_num

    def recv_runners_actions(self):
        """
        gets the changes/actions from the bots
        """

        # get moves from each player
        if self.turn_num == self.game.init_turn:
            time_limit = self.load_time
        elif self.turn_num == self.game.init_turn + 1:
            time_limit = self.turn_time * 10
        else:
            time_limit = self.turn_time

        # here is our safe zone, we take factor of 3 for our running more than we show to players
        time_limit *= 3

        if self.is_serial:
            simultaneous_running = 1
        else:
            simultaneous_running = len(self.runners)

        alive_bots = [runner for runner in self.runners if self.game.is_alive(runner.game_id)]

        for group_num in range(0, len(alive_bots), simultaneous_running):
            runners_in_action = alive_bots[group_num: group_num+simultaneous_running]
            # get the moves from each bot
            self.get_moves(runners_in_action, time_limit)

    def print_debug_msgs(self):
        """
        print the debug msgs in the runner actions
        """
        for runner in self.runners:
            bot_name = runner.name
            if not isinstance(runner.actions, dict):
                runner.actions = {}
            if 'data' not in runner.actions.keys():
                runner.actions['data'] = {}
            extracted_bot_moves = runner.actions['data']

            if not isinstance(extracted_bot_moves, dict):
                extracted_bot_moves = {}
            if 'debug_messages' not in extracted_bot_moves.keys():
                extracted_bot_moves['debug_messages'] = []

            # Handle debug messages.
            messages = []
            stop_messages = []
            for bot_debug_message in extracted_bot_moves['debug_messages']:
                if bot_debug_message['type'] == 'message':
                    try:
                        messages.append(base64.b64decode(bot_debug_message['message']))
                    except (TypeError, Exception):
                        messages.append('Invalid debug message.')
                elif bot_debug_message['type'] == 'stop':
                    try:
                        stop_messages.append(base64.b64decode(bot_debug_message['message']))
                    except (TypeError, Exception):
                        stop_messages.append('Invalid stop message.')
            if messages:
                self.logger.debug('turn %4d bot %s Debug prints:\n' % (self.turn_num, bot_name))
                self.logger.debug('Debug>> ' + '\nDebug>> '.join(messages) + '\n')

                runner.add_debug_msg(messages, turn=self.turn_num)
            if stop_messages:
                # The three is the level so it separates the stop messages from the debug messages which are
                # level two.
                runner.add_debug_msg(stop_messages, turn=self.turn_num, level=3)

    def handle_verbose_logs(self):
        """
        with verbose log we want to display the following <pirateCount> <treasureCount> <Ranking/leading> <scores>
        """
        if self.verbose_log:
            stats = self.game.get_stats()
            stat_keys = sorted(stats.keys())
            s = 'turn %4d stats: ' % self.turn_num
            if self.turn_num % 50 == 0:
                self.verbose_log.write(' ' * len(s))
                for key in stat_keys:
                    values = stats[key]
                    self.verbose_log.write(' {0:^{1}}'.format(key, max(len(key), len(str(values)))))
                self.verbose_log.write('\n')
            self.verbose_log.write(s)
            for key in stat_keys:
                values = stats[key]
                if type(values) == list:
                    values = '[' + ','.join(map(str, values)) + ']'
                self.verbose_log.write(' {0:^{1}}'.format(values, max(len(key), len(str(values)))))
            self.verbose_log.write('\n')
        else:
            # no verbose log - print progress every 100 turns
            if self.turn_num % 100 == 0:
                turn_prompt = "turn #%d of max %d\n" % (self.turn_num, self.turns)
                sys.stdout.write(turn_prompt)

    def process_orders(self):
        """
        Process the orders in each runner's actions
        """
        for runner in self.runners:
            bot_name = runner.name
            if not isinstance(runner.actions, dict):
                runner.actions = {}
            if 'data' not in runner.actions.keys():
                runner.actions['data'] = {}
            extracted_bot_moves = runner.actions['data']
            if not isinstance(extracted_bot_moves, dict):
                extracted_bot_moves = {}
            if 'orders' not in extracted_bot_moves.keys():
                extracted_bot_moves['orders'] = []

            valid, ignored, invalid = self.game.do_moves(runner.game_id, extracted_bot_moves['orders'])

            runner.logger.output('# turn %s\n' % self.turn_num)

            if valid:
                valid_in_str_form = map(str, valid)
                runner.logger.output('\n'.join(valid_in_str_form) + '\n')

            if ignored:
                runner.logger.error('turn %4d bot %s ignored actions:\n' % (self.turn_num, bot_name))
                runner.logger.error('\n'.join(ignored) + '\n')

                runner.logger.output('\n'.join(ignored) + '\n')

                runner.add_debug_msg(ignored, turn=self.turn_num, level=1)
            if invalid:
                if self.strict:
                    self.game.kill_player(runner.game_id)
                    runner.status = 'invalid'
                    runner.turn = self.turn_num

                runner.logger.error('turn %4d bot %s invalid actions:\n' % (self.turn_num, bot_name))
                runner.logger.error('\n'.join(invalid) + '\n')

                runner.logger.output('\n'.join(invalid) + '\n')
                runner.add_debug_msg(invalid, turn=self.turn_num, level=1)

    def get_moves(self, runners, time_limit):
        """
        Get the moves from the runners each bot committed in a single turn.

        :param runners: the live runners in the turn
        :type runners: list[Runner]
        :param time_limit: the time limit for the runners
        :type: int
        """
        bot_finished = [not self.game.is_alive(runner.game_id) for runner in runners]

        # resume all bots
        for runner in runners:
            if runner.is_alive:
                runner.resume()

        # don't start timing until the bots are started
        start_time = time.time()

        # loop until received all bots send moves or are dead
        #   or when time is up
        while not all(bot_finished) and time.time() - start_time < time_limit:
            time.sleep(0.003)
            for bot_number, runner in enumerate(runners):
                if bot_finished[bot_number]:
                    continue  # already got bot moves
                if not runner.is_alive:
                    msg = unicode('turn %4d bot %s crashed') % (self.turn_num, runner.game_id)
                    runner.add_error_msg([msg], turn=self.turn_num)
                    runner.status = 'crashed'
                    for x in range(100):  # Reads up to 100 lines of the error
                        line = runner.read_error()
                        if line is None:
                            break
                        runner.add_error_msg([line], turn=self.turn_num)
                    bot_finished[bot_number] = True
                    self.game.kill_player(runner.game_id)
                    continue  # bot is dead

                data = runner.recv()
                if data:
                    runner.actions = data
                    bot_finished[bot_number] = True

                for x in range(100):  # Reads up to 100 lines of the error
                    line = runner.read_error()
                    # TODO - THIS ALSO READS ERRORS WHEN WE DEBUG!!!FIX!!!
                    if line is None:
                        break
                    runner.add_error_msg([line], turn=self.turn_num)

        moves_time = time.time() - start_time

        # pause all bots again
        for runner in runners:
            if runner.is_alive:
                runner.pause()

        # kill timed out bots
        for bot_number, finished in enumerate(bot_finished):
            if not finished:
                runner = runners[bot_number]
                error_msg = unicode('turn %4d bot %s timed out') % (self.turn_num, runner.game_id)
                runner.add_error_msg([error_msg],
                                     turn=self.turn_num)
                runner.status = 'timeout'
                for x in range(100):
                    line = runner.read_error()
                    if line is None:
                        break
                    runner.add_error_msg([line], turn=self.turn_num)
                self.game.kill_player(runner.game_id)
                runner.kill()

        return moves_time


def run_game(game, bot_paths, options):
    """
    Run the game ( for backward compatibility )

    :param game: the game object
    :type game: game.Game
    :param bot_paths: the bot commands from the run game
    :type bot_paths: tuple(str)
    :param options:the game options
    :type options: dict
    :return: the replay of the game
    :rtype: dict
    """
    engine = Engine(bot_paths=bot_paths, options=options, game=game)
    replay = engine.run_game()
    return replay
