import sys
import os
import subprocess
import shutil
import shlex
import readline


builtins = ["echo", "exit", "type", "pwd", "cd"]


REDIRECT_OPS = {
    ">": ("stdout", "w"),
    "1>": ("stdout", "w"),
    ">>": ("stdout", "a"),
    "1>>": ("stdout", "a"),
    "2>": ("stderr", "w"),
    "2>>": ("stderr", "a"),
}


def locate_in_path(command):
    return shutil.which(command)


# autocomplete
def complete(text, state):

    commands = set(builtins)

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:

        if not os.path.isdir(directory):
            continue

        try:
            for file in os.listdir(directory):

                full_path = os.path.join(directory, file)

                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    commands.add(file)

        except:
            pass

    matches = sorted([cmd for cmd in commands if cmd.startswith(text)])

    # single completion -> auto add space
    if len(matches) == 1:

        if state == 0:
            return matches[0] + " "

        return None

    if state < len(matches):
        return matches[state]

    return None


# show all matches on double tab
def display_matches(substitution, matches, longest_match_length):

    print()
    print("  ".join(sorted(matches)))

    sys.stdout.write("$ " + readline.get_line_buffer())
    sys.stdout.flush()


# parse redirection
def parse_redirect(args):

    for i, arg in enumerate(args):

        if arg in REDIRECT_OPS and i + 1 < len(args):

            stream, mode = REDIRECT_OPS[arg]

            return stream, mode, i, args[i + 1]

    return None


# external command execution
def execute_external(program, args):

    executable = locate_in_path(program)

    if not executable:
        print(f"{program}: command not found")
        return

    redirect = parse_redirect(args)

    # no redirection
    if redirect is None:

        try:
            subprocess.run([program] + args)

        except FileNotFoundError:
            print(f"{program}: command not found")

        return

    # with redirection
    stream, mode, op_index, filepath = redirect

    stdout_target = None
    stderr_target = None

    try:

        if stream == "stdout":
            stdout_target = open(filepath, mode)

        else:
            stderr_target = open(filepath, mode)

        subprocess.run(
            [program] + args[:op_index],
            stdout=stdout_target,
            stderr=stderr_target
        )

    except FileNotFoundError:
        print(f"{program}: command not found")

    finally:

        if stdout_target:
            stdout_target.close()

        if stderr_target:
            stderr_target.close()


def main():

    # autocomplete setup
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")
    readline.set_completion_display_matches_hook(display_matches)

    while True:

        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input().strip()

        if not command:
            continue

        parts = shlex.split(command)

        if not parts:
            continue

        program = parts[0]
        args = parts[1:]

        # exit
        if program == "exit":

            if args and args[0] == "0":
                sys.exit(0)

            break

        # echo
        elif program == "echo":
            print(" ".join(args))

        # pwd
        elif program == "pwd":
            print(os.getcwd())

        # cd
        elif program == "cd":

            if not args:
                os.chdir(os.path.expanduser("~"))
                continue

            path = os.path.expanduser(args[0])

            try:
                os.chdir(path)

            except FileNotFoundError:
                print(f"cd: {args[0]}: No such file or directory")

        # type
        elif program == "type":

            if not args:
                continue

            command_type = args[0]

            if command_type in builtins:
                print(f"{command_type} is a shell builtin")

            else:

                executable = locate_in_path(command_type)

                if executable:
                    print(f"{command_type} is {executable}")

                else:
                    print(f"{command_type}: not found")

        # external commands
        else:
            execute_external(program, args)


if __name__ == "__main__":
    main()