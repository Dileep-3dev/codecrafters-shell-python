import sys
import os
def main():
    # TODO: Uncomment the code below to pass the first stage
    # sys.stdout.write("$ ")
    while True:
        sys.stdout.write("$ ")
        # Wait for user input
        sys.stdout.flush()
        command = input()
        parts = command.split()
        if not parts:
            continue
        program = parts[0]
        args = parts[1:]
        if program == "exit":
            break
        elif program == "echo":
            print(" ".join(args))
        elif program == "type":
            if args and args[0] in ["echo", "exit", "type"]:
                print(f"{args[0]} is a shell builtin")
            else:
                path_env = os.environ.get("PATH", "")
                found = False
                for directory in path_env.split(os.pathsep):
                    full_path = os.path.join(directory, args[0])
                    if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                        print(f"{args[0]} is {full_path}")
                        found = True
                        break
                if not found:
                    print(f"{args[0]}: not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
