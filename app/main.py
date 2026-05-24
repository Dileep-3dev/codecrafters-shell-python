import sys
import os
import subprocess
import shutil
import shlex
import readline
import selectors


BUILTINS = [
    "echo",
    "exit",
    "type",
    "pwd",
    "cd",
    "complete",
    "jobs",
]

COMPLETION_SCRIPT_REGISTRY = {}

BACKGROUND_JOBS = []

NEXT_JOB_NUMBER = 1

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


def ensure_parent_directory(filepath):

    directory = os.path.dirname(filepath)

    if directory:
        os.makedirs(directory, exist_ok=True)


def parse_redirect(args):

    for i, arg in enumerate(args):

        if arg in REDIRECT_OPS and i + 1 < len(args):

            stream, mode = REDIRECT_OPS[arg]

            return stream, mode, i, args[i + 1]

    return None


def clean_args(args):

    redirect = parse_redirect(args)

    if redirect:

        _, _, index, _ = redirect

        return args[:index]

    return args


# =========================
# PROGRAMMABLE COMPLETION
# =========================
def run_completion_script(command):

    script = COMPLETION_SCRIPT_REGISTRY.get(command)

    if not script:
        return []

    try:

        line = readline.get_line_buffer()

        words = line.split()

        current_word = ""

        if not line.endswith(" "):
            current_word = words[-1]

        previous_word = ""

        if len(words) >= 2:
            previous_word = words[-2]

        # =========================
        # COMP_LINE / COMP_POINT
        # =========================
        env = os.environ.copy()

        env["COMP_LINE"] = line

        env["COMP_POINT"] = str(
            len(line.encode())
        )

        process = subprocess.Popen(
            [
                script,
                command,
                current_word,
                previous_word,
            ],
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
        )

        matches = []

        def handle_output(stream, mask):

            output = stream.readline().rstrip("\n")

            if not output:
                return

            matches.append(output)

        with selectors.DefaultSelector() as selector:

            selector.register(
                process.stdout,
                selectors.EVENT_READ,
                handle_output
            )

            while process.poll() is None:

                events = selector.select()

                for key, mask in events:

                    callback = key.data

                    callback(
                        key.fileobj,
                        mask
                    )

            # drain remaining output
            while True:

                output = process.stdout.readline()

                if not output:
                    break

                matches.append(
                    output.rstrip("\n")
                )

            process.wait()

        return matches

    except:
        return []


# =========================
# AUTOCOMPLETE
# =========================
def complete(text, state):

    line = readline.get_line_buffer()

    words = line.split()

    matches = []

    # -------------------------
    # COMMAND COMPLETION
    # -------------------------
    if len(words) <= 1 and not line.endswith(" "):

        commands = set(BUILTINS)

        path_dirs = os.environ.get(
            "PATH",
            ""
        ).split(os.pathsep)

        for directory in path_dirs:

            if not os.path.isdir(directory):
                continue

            try:

                for entry in os.listdir(directory):

                    full_path = os.path.join(
                        directory,
                        entry
                    )

                    if (
                        os.path.isfile(full_path)
                        and os.access(full_path, os.X_OK)
                    ):
                        commands.add(entry)

            except:
                pass

        matches = sorted([
            cmd for cmd in commands
            if cmd.startswith(text)
        ])

        # auto append space on single command completion
        if len(matches) == 1:

            match = matches[0]

            if os.path.isdir(match):
                matches[0] = match + "/"
            else:
                matches[0] = match + " "

    # -------------------------
    # ARGUMENT COMPLETION
    # -------------------------
    else:

        # programmable completion
        if (
            len(words) >= 1
            and words[0] in COMPLETION_SCRIPT_REGISTRY
        ):

            raw_matches = run_completion_script(
                words[0]
            )

            matches = []

            for match in raw_matches:

                if match.startswith(text):

                    if len(raw_matches) == 1:
                        matches.append(match + " ")
                    else:
                        matches.append(match)

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

                        full_path = os.path.join(
                            directory,
                            entry
                        )

                        if full_path.startswith("./"):
                            full_path = full_path[2:]

                        if os.path.isdir(full_path):
                            matches.append(
                                full_path + "/"
                            )
                        else:
                            matches.append(
                                full_path + " "
                            )

            except:
                pass

            matches = sorted(matches)

    if state < len(matches):
        return matches[state]

    return None


def display_matches(
    substitution,
    matches,
    longest_match_length
):

    print()
    print("  ".join(sorted(matches)))

    sys.stdout.write(
        "$ " + readline.get_line_buffer()
    )

    sys.stdout.flush()


# =========================
# OUTPUT HANDLING
# =========================
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


# =========================
# EXTERNAL COMMANDS
# =========================
def execute_external(program, args):

    global NEXT_JOB_NUMBER

    executable = locate_in_path(program)

    if not executable:
        sys.stderr.write(
            f"{program}: command not found\n"
        )
        return

    # =========================
    # BACKGROUND JOB
    # =========================
    background = False

    if args and args[-1] == "&":

        background = True

        args = args[:-1]

    redirect = parse_redirect(args)

    # =========================
    # BACKGROUND EXECUTION
    # =========================
    if background:

        process = subprocess.Popen(
            [program] + args
        )

        job = {
            "job_number": NEXT_JOB_NUMBER,
            "pid": process.pid,
            "command": f"{program} {' '.join(args)} &",
            "status": "Running",
        }

        BACKGROUND_JOBS.append(job)

        print(
            f"[{NEXT_JOB_NUMBER}] {process.pid}"
        )

        NEXT_JOB_NUMBER += 1

        return

    # =========================
    # FOREGROUND EXECUTION
    # =========================
    if redirect is None:

        subprocess.run([program] + args)

        return

    stream, mode, index, filepath = redirect

    ensure_parent_directory(filepath)

    stdout_target = None
    stderr_target = None

    try:

        if stream == "stdout":
            stdout_target = open(filepath, mode)

        else:
            stderr_target = open(filepath, mode)

        subprocess.run(
            [program] + args[:index],
            stdout=stdout_target,
            stderr=stderr_target,
            text=True
        )

    finally:

        if stdout_target:
            stdout_target.close()

        if stderr_target:
            stderr_target.close()


# =========================
# MAIN
# =========================
def main():

    readline.set_completer(complete)

    readline.set_completer_delims(
        " \t\n"
    )

    readline.parse_and_bind(
        "tab: complete"
    )

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

        # =====================
        # EXIT
        # =====================
        if program == "exit":

            if actual_args and actual_args[0] == "0":
                sys.exit(0)

            break

        # =====================
        # ECHO
        # =====================
        elif program == "echo":

            output = " ".join(
                actual_args
            ) + "\n"

            write_output(output, redirect)

        # =====================
        # PWD
        # =====================
        elif program == "pwd":

            output = os.getcwd() + "\n"

            write_output(output, redirect)

        # =====================
        # CD
        # =====================
        elif program == "cd":

            if not actual_args:
                os.chdir(
                    os.path.expanduser("~")
                )
                continue

            path = os.path.expanduser(
                actual_args[0]
            )

            try:
                os.chdir(path)

            except OSError:

                sys.stderr.write(
                    f"cd: {actual_args[0]}: "
                    "No such file or directory\n"
                )

        # =====================
        # JOBS
        # =====================
        elif program == "jobs":

            output = ""

            for job in BACKGROUND_JOBS:

                output += (
                    f"[{job['job_number']}]+  "
                    f"{job['status']:<24}"
                    f"{job['command']}\n"
                )

            write_output(
                output,
                redirect
            )

        # =====================
        # COMPLETE BUILTIN
        # =====================
        elif program == "complete":

            # complete -C script cmd
            if (
                len(actual_args) == 3
                and actual_args[0] == "-C"
            ):

                COMPLETION_SCRIPT_REGISTRY[
                    actual_args[2]
                ] = actual_args[1]

                output = ""

            # complete -r cmd
            elif (
                len(actual_args) == 2
                and actual_args[0] == "-r"
            ):

                cmd = actual_args[1]

                COMPLETION_SCRIPT_REGISTRY.pop(
                    cmd,
                    None
                )

                output = ""

            # complete -p cmd
            elif (
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

            else:

                output = (
                    "complete is a shell builtin\n"
                )

            write_output(output, redirect)

        # =====================
        # TYPE
        # =====================
        elif program == "type":

            if not actual_args:
                continue

            cmd = actual_args[0]

            if cmd in BUILTINS:

                output = (
                    f"{cmd} is a shell builtin\n"
                )

            else:

                executable = locate_in_path(cmd)

                if executable:

                    output = (
                        f"{cmd} is {executable}\n"
                    )

                else:

                    output = (
                        f"{cmd}: not found\n"
                    )

            write_output(output, redirect)

        # =====================
        # EXTERNAL COMMAND
        # =====================
        else:
            execute_external(program, args)


if __name__ == "__main__":
    main()