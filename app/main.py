import sys
import os
import subprocess
import shutil
import shlex
import readline


builtins = [
    "echo",
    "exit",
    "type",
    "pwd",
    "cd",
    "complete",
]


COMPLETION_SCRIPT_REGISTRY = {}


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


def run_completion_script(command_name):

    completer = COMPLETION_SCRIPT_REGISTRY.get(command_name)

    if not completer:
        return ""

    try:

        result = subprocess.run(
            [completer],
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.splitlines()

        if lines:
            return lines[0]

    except:
        pass

    return ""


def complete(text, state):

    matches = []

    line = readline.get_line_buffer()

    words = line.split()

    # first token -> command completion
    if len(words) <= 1 and not line.endswith(" "):

        commands = set(builtins)

        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        for directory in path_dirs:

            if not os.path.isdir(directory):
                continue

            try:

                for entry in os.listdir(directory):

                    full_path = os.path.join(directory, entry)

                    if (
                        os.path.isfile(full_path)
                        and os.access(full_path, os.X_OK)
                    ):
                        commands.add(entry)

            except:
                pass

        matches = sorted(
            [cmd for cmd in commands if cmd.startswith(text)]
        )

        # single command match -> add space
        if len(matches) == 1:
            matches[0] += " "

    # everything after first command -> filepath completion
    else:

        if "/" in text:

            directory, prefix = os.path.split(text)

            if directory == "":
                directory = "."

        else:

            directory = "."
            prefix = text

        try:

            for entry in os.listdir(directory):

                if entry.startswith(prefix):

                    full_path = os.path.join(directory, entry)

                    if full_path.startswith("./"):
                        full_path = full_path[2:]

                    if os.path.isdir(full_path):
                        matches.append(full_path + "/")
                    else:
                        matches.append(full_path + " ")

        except FileNotFoundError:
            pass

        matches = sorted(matches)

    if state < len(matches):
        return matches[state]

    return None

    matches = []

    buffer = readline.get_line_buffer()

    tokens = buffer.split()

    completing_command = (
        not buffer.strip()
        or (
            not buffer.endswith(" ")
            and len(tokens) == 1
        )
    )

    # command completion
    if completing_command:

        commands = set(builtins)

        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        for directory in path_dirs:

            if not os.path.isdir(directory):
                continue

            try:

                for entry in os.listdir(directory):

                    full_path = os.path.join(directory, entry)

                    if (
                        entry.startswith(text)
                        and os.path.isfile(full_path)
                        and os.access(full_path, os.X_OK)
                    ):
                        commands.add(entry)

            except:
                pass

        command_matches = sorted(
            [cmd for cmd in commands if cmd.startswith(text)]
        )

        # FIXED: if single directory-like match don't add space
        if len(command_matches) == 1:

            cmd = command_matches[0]

            matches.append(cmd)

        else:
            matches.extend(command_matches)

    # programmable completion
    elif text == "":

        if len(tokens) == 1:

            command_name = tokens[0]

            completion = run_completion_script(command_name)

            if completion:
                matches.append(completion + " ")

    # filepath completion
    else:

        try:

            if "/" in text:

                dirpath, prefix = os.path.split(text)

                if dirpath == "":
                    dirpath = "."

            else:

                dirpath = "."
                prefix = text

            for entry in os.listdir(dirpath):

                if entry.startswith(prefix):

                    full_match = os.path.join(dirpath, entry)

                    if full_match.startswith("./"):
                        full_match = full_match[2:]

                    # directory
                    if os.path.isdir(full_match):
                        matches.append(full_match + "/")

                    # file
                    else:
                        matches.append(full_match + " ")

        except FileNotFoundError:
            pass

    matches = sorted(set(matches))

    if not matches:
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


# parse redirects
def parse_redirect(args):

    for i, arg in enumerate(args):

        if arg in REDIRECT_OPS and i + 1 < len(args):

            stream, mode = REDIRECT_OPS[arg]

            return stream, mode, i, args[i + 1]

    return None


# remove redirects
def clean_args(args):

    redirect = parse_redirect(args)

    if redirect:

        _, _, op_index, _ = redirect

        return args[:op_index]

    return args


# create parent dirs
def ensure_parent_directory(filepath):

    directory = os.path.dirname(filepath)

    if directory:
        os.makedirs(directory, exist_ok=True)


# write output
def write_output(output, redirect):

    if redirect is None:
        sys.stdout.write(output)
        return

    stream, mode, _, filepath = redirect

    ensure_parent_directory(filepath)

    if stream == "stdout":

        with open(filepath, mode) as file:
            file.write(output)

    else:

        with open(filepath, mode):
            pass

        sys.stdout.write(output)


# external commands
def execute_external(program, args):

    executable = locate_in_path(program)

    if not executable:
        sys.stderr.write(f"{program}: command not found\n")
        return

    redirect = parse_redirect(args)

    # no redirect
    if redirect is None:

        try:
            subprocess.run([program] + args)

        except FileNotFoundError:
            sys.stderr.write(f"{program}: command not found\n")

        return

    # redirect exists
    stream, mode, op_index, filepath = redirect

    ensure_parent_directory(filepath)

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
        sys.stderr.write(f"{program}: command not found\n")

    finally:

        if stdout_target:
            stdout_target.close()

        if stderr_target:
            stderr_target.close()


def main():

    readline.set_completer(complete)

    readline.set_completer_delims(" \t\n")

    readline.parse_and_bind("tab: complete")

    readline.set_completion_display_matches_hook(
        display_matches
    )

    while True:

        try:
            command = input("$ ")

        except EOFError:
            break

        except KeyboardInterrupt:
            print()
            continue

        if not command.strip():
            continue

        try:
            parts = shlex.split(command)

        except ValueError:
            continue

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

            except OSError:
                sys.stderr.write(
                    f"cd: {actual_args[0]}: No such file or directory\n"
                )

        # complete builtin
        elif program == "complete":

            # complete -p cmd
            if (
                len(actual_args) == 2
                and actual_args[0] == "-p"
            ):

                cmd = actual_args[1]

                if cmd in COMPLETION_SCRIPT_REGISTRY:

                    output = (
                        f"complete -C "
                        f"'{COMPLETION_SCRIPT_REGISTRY[cmd]}' "
                        f"{cmd}\n"
                    )

                else:

                    output = (
                        f"complete: {cmd}: "
                        "no completion specification\n"
                    )

            # complete -C script cmd
            elif (
                len(actual_args) == 3
                and actual_args[0] == "-C"
            ):

                COMPLETION_SCRIPT_REGISTRY[
                    actual_args[2]
                ] = actual_args[1]

                output = ""

            else:

                output = "complete is a shell builtin\n"

            write_output(output, redirect)

        # type
        elif program == "type":

            if not actual_args:
                continue

            command_type = actual_args[0]

            if command_type in builtins:

                output = (
                    f"{command_type} is a shell builtin\n"
                )

            else:

                executable = locate_in_path(command_type)

                if executable:
                    output = (
                        f"{command_type} is {executable}\n"
                    )

                else:
                    output = (
                        f"{command_type}: not found\n"
                    )

            write_output(output, redirect)

        # external commands
        else:
            execute_external(program, args)


if __name__ == "__main__":
    main()