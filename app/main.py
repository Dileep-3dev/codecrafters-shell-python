import sys
import os
import subprocess


def locate_in_path(command):
    path_env = os.environ.get("PATH", "")

    for directory in path_env.split(os.pathsep):
        full_path = os.path.join(directory, command)

        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = input()
        parts = command.split()

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

        # type
        elif program == "type":
            if not args:
                continue

            builtins = ["echo", "exit", "type", "pwd"]

            if args[0] in builtins:
                print(f"{args[0]} is a shell builtin")

            else:
                executable = locate_in_path(args[0])

                if executable:
                    print(f"{args[0]} is {executable}")
                else:
                    print(f"{args[0]}: not found")

        # external commands
        else:
            executable = locate_in_path(program)

            if executable:
                subprocess.run([program] + args)
            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()