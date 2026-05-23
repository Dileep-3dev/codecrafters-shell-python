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

    if len(matches) == 1:

        if state == 0:
            return matches[0] + " "

        return None

    if state < len(matches):
        return matches[state]

    return None


# display autocomplete matches
def display_matches(substitution, matches, longest_match_length):

    print()
    print("  ".join(sorted(matches)))

    sys.stdout.write("$ " + readline.get_line_buffer())
    sys.stdout.flush()


# parse redirect
def parse_redirect(args):

    for i, arg in enumerate(args):

        if arg in REDIRECT_OPS and i + 1 < len(args):

            stream, mode = REDIRECT_OPS[arg]

            return stream, mode, i, args[i + 1]

    return None


# remove redirect tokens
def clean_args(args):

    redirect = parse_redirect(args)

    if redirect:

        _, _, op_index, _ = redirect

        return args[:op_index]

    return args


# builtin output handling
def write_output(output, redirect):

    if redirect is None:
        sys.stdout.write(output)
        return

    stream, mode, _, filepath = redirect

    if stream == "stdout":

        with open(filepath, mode) as file:
            file.write(output)

    else:

        sys.stdout.write(output)


# external command execution
def execute_external(program, args):

    executable = locate_in_path(program)

    if not executable:
        print(f"{program}: command not found")
        return

    redirect = parse_redirect(args)

    # no redirect
    if redirect is None:

        try:
            subprocess.run([program] + args)

        except FileNotFoundError:
            print(f"{program}: command not found")

        return

    # redirect exists
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
            stderr=stderr_target,
            text=True
        )

    except FileNotFoundError:
        print(f"{program}: command not found")

    finally:

        if stdout_target:
            stdout_target.close()

        if stderr_target:
            stderr_target.close()


def main():

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

        redirect = parse_redirect(args)
        actual_args = clean_args(args)

        # exit
        if program == "exit":

            if actual_args and actual_args[0] == "0":
                sys.exit(0)

            break

        # echo
        elif program == "echo":

            output = " ".join(actual_args) + "\n"

            write_output(output, redirect)

        # pwd
        elif program == "pwd":

            output = os.getcwd() + "\n"

            write_output(output, redirect)

        # cd
        elif program == "cd":

            if not actual_args:
                os.chdir(os.path.expanduser("~"))
                continue

            path = os.path.expanduser(actual_args[0])

            try:
                os.chdir(path)

            except FileNotFoundError:
                print(f"cd: {actual_args[0]}: No such file or directory")

        # type
        elif program == "type":

            if not actual_args:
                continue

            command_type = actual_args[0]

            if command_type in builtins:

                output = f"{command_type} is a shell builtin\n"

            else:

                executable = locate_in_path(command_type)

                if executable:
                    output = f"{command_type} is {executable}\n"

                else:
                    output = f"{command_type}: not found\n"

            write_output(output, redirect)

        # external commands
        else:
            execute_external(program, args)


if __name__ == "__main__":
    main()