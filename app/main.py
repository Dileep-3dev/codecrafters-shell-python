import sys

commands = {
    "type": lambda userInput: print(f"{args} is a shell builtin")
    if (args := userInput[5:]) in commands
    else print(f"{args}: not found"),
}
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
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
