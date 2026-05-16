import sys
import os
import subprocess
import shutil


def locate_in_path(command):
    return shutil.which(command)


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

        # cd
        elif program == "cd":
            if not args:
                continue

            path = args[0]

            if path == "~":
                path = os.path.expanduser("~")

            if os.path.exists(path):
                os.chdir(path)
            else:
                sys.stderr.write(f"cd: {args[0]}: No such file or directory\n")

        # type
        elif program == "type":
            if not args:
                continue

            builtins = ["echo", "exit", "type", "pwd", "cd"]

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
                result = subprocess.run(
                    [program] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                sys.stdout.write(result.stdout)

                if result.stderr:
                    sys.stderr.write(result.stderr)

            else:
                sys.stderr.write(f"{program}: command not found\n")


if __name__ == "__main__":
    main()