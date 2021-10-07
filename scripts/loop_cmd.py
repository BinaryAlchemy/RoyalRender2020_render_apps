import argparse
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
        padding = next(i for i, c in enumerate(token) if c != '#')
    except StopIteration:
        padding = len(token)

    return replace_frame_placeholder(in_str[:idx] + "{0:0" + str(padding) + "d}" + token[padding:])


def execute_loop(start, end, step, command, shell):
    command = replace_frame_placeholder(command)

    for i in range(start, end + 1, step):
        subprocess.call(command.format(i), shell=shell)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute command in a loop')
    parser.add_argument('start', type=int, help='Sequence Start')
    parser.add_argument('end', type=int, help='Sequence End')
    parser.add_argument('step', type=int, help='Sequence Step')
    parser.add_argument('command', help="Command to loop. Use 'new line' (\\n) to separate multiple lines", nargs='*')

    parser.add_argument('--no-shell', dest='use_shell', action='store_const',
                        const=False, default=True,
                        help="don't execute in a command shell (usually not required)")

    parser.add_argument('--debug', dest='use_debug', action='store_const',
                        const=True, default=False,
                        help='print debug info')

    print("\n -- Loop Command - {0} --\n".format(parser.description))

    args = parser.parse_args()

    for i, arg in enumerate(args.command):
        if " " in arg:
            args.command[i] = '"{0}"'.format(arg)

    full_command = ' '.join(args.command)
    full_command = full_command.replace("\\n", '&')
    full_command = full_command.replace("\\r", '&')

    use_shell = True if any(['&' in args.command, 'echo' in full_command]) else args.use_shell

    if args.use_debug:
        print()
        print("DBG - command arguments", args.command)
        print("DBG - full_command", full_command)
        print("DBG - use_shell", args.use_shell)
        print()

    execute_loop(args.start, args.end, args.step, full_command, use_shell)

    print("\n --- Loop finished ---\n")
