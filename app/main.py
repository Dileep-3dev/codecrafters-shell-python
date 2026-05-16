import sys
import os
import subprocess
import shutil
import shlex


builtins = ["echo", "exit", "type", "pwd", "cd"]


def locate_in_path(command):
    return shutil.which(command)


def main():
    while True:

        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input().strip()

        if not command:
            continue

        # IMPORTANT: handles quotes properly
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

            # cd -> home directory
            if not args:
                os.chdir(os.path.expanduser("~"))
                continue

            path = args[0]

            # handle "~"
            if path == "~":
                path = os.path.expanduser("~")

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