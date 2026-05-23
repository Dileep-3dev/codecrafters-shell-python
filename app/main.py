import sys
import os
import subprocess
import shutil
import shlex
import readline


builtins = ["echo", "exit", "type", "pwd", "cd"]


def locate_in_path(command):
    return shutil.which(command)


# autocomplete
def complete(text, state):

    commands = builtins[:]

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_dirs:

        try:
            for file in os.listdir(directory):

                full_path = os.path.join(directory, file)

                if os.access(full_path, os.X_OK):

                    if file not in commands:
                        commands.append(file)

        except FileNotFoundError:
            continue

    matches = [cmd for cmd in commands if cmd.startswith(text)]

    if state < len(matches):
        return matches[state] + " "

    return None


def main():

    # enable tab completion
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")

    while True:

        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input().strip()

        if not command:
            continue

        # redirection support
        if ">" in command or "1>" in command or "2>" in command:
            os.system(command)
            continue

        parts = shlex.split(command)

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

            executable = locate_in_path(program)

            if executable:

                try:
                    subprocess.run([program] + args)

                except FileNotFoundError:
                    print(f"{program}: command not found")

            else:
                print(f"{program}: command not found")


if __name__ == "__main__":
    main()