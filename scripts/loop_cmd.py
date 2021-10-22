#python
# -*- coding: cp1252 -*-
######################################################################
#
# Royal Render Render script for executing commands in a loop
# Author:  Royal Render, Paolo Acampora
# Version %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
######################################################################


import subprocess
import sys

if sys.version_info.major == 2:
    range = xrange


def replace_frame_placeholder(in_str, frame_ch="#"):
    try:
        idx = in_str.index(frame_ch)
    except ValueError:
        return in_str

    token = in_str[idx:]

    try:
        padding = next(i for i, c in enumerate(token) if c != frame_ch)
    except StopIteration:
        padding = len(token)

    return replace_frame_placeholder(in_str[:idx] + "{0:0" + str(padding) + "d}" + token[padding:])


def execute_loop(start, end, step, command, shell):
    command = replace_frame_placeholder(command)

    for i in range(start, end + 1, step):
        subprocess.call(command.format(i), shell=shell)


class LoppCmdParser(object):
    def __init__(self, *args):
        self.success = False

        args = list(args)
        try:
            self.start = int(args.pop(0))
            self.end = int(args.pop(0))
            self.step = int(args.pop(0))
        except IndexError:
            raise Exception("not enough arguments")
        except ValueError:
            raise Exception("first three arguments must be numbers (start, end, step)")

        if not args:
            raise Exception("not enough arguments: loop_cmd start end step COMMAND [--debug] [--no-shell]")

        for i in range(-2 if len(args) > 1 else -1, 0):
            if args[i] == "--debug":
                args.pop(i)
                self.use_debug = True
                break
            else:
                self.use_debug = False

        for i in range(-2 if len(args) > 1 else -1, 0):
            if args[i] == "--no-shell":
                args.pop(i)
                self.use_shell = False
                break
            else:
                self.use_shell = True

        for i, arg in enumerate(args):
            if " " in arg:
                args[i] = '"{0}"'.format(arg)

        full_command = ' '.join(args)
        full_command = full_command.replace(" \\n ", '&')

        self.use_shell = True if any(['&' in args, 'echo' in full_command]) else self.use_shell
        self.full_command = full_command
        self.success = True

    def print_args(self):
        for k, v in self.__dict__.items():
            print('"{0}": {1}'.format(k, v))


if __name__ == '__main__':
    description = 'Execute command in a loop'

    print("\n -- Loop Command %rrVersion% - {0} --\n".format(description))

    # remove script invocation (first argument)
    _ = sys.argv.pop(0)
    parser = LoppCmdParser(*sys.argv)

    if parser.use_debug:
        parser.print_args()

    if parser.success:
        execute_loop(parser.start, parser.end, parser.step, parser.full_command, parser.use_shell)

    print("\n --- Loop finished ---\n")
