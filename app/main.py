import sys
import os
def main():
    # TODO: Uncomment the code below to pass the first stage
    # sys.stdout.write("$ ")
    while True:
        sys.stdout.write("$ ")
        # Wait for user input
        command = input()
        if command == "exit":
            break
        elif command.startswith("echo "):
            print(command[5:])
        elif command.startswith("type "):
            args = command[5:]
            if args in ["echo", "exit", "type"]:
                print(f"{args} is a shell builtin")
            else:
                path_env = os.environ.get("PATH", "")
                found = False
                for directory in path_env.split(os.pathsep):
                    full_path = os.path.join(directory, args)
                    if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                        print(f"{args} is {full_path}")
                        found = True
                        break
                if not found:
                    print(f"{args}: not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
