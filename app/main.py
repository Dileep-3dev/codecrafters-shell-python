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
    "history",
]

COMPLETION_SCRIPT_REGISTRY = {}

BACKGROUND_JOBS = []

COMMAND_HISTORY = []

LAST_HISTORY_APPEND_INDEX = 0

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
# LOAD HISTORY FROM HISTFILE
# =========================
def load_history_from_histfile():

    global LAST_HISTORY_APPEND_INDEX

    histfile = os.environ.get(
        "HISTFILE"
    )

    if not histfile:
        return

    try:

        with open(histfile, "r") as file:

            for line in file:

                line = line.rstrip("\n")

                if line.strip():

                    COMMAND_HISTORY.append(
                        line
                    )

        LAST_HISTORY_APPEND_INDEX = len(
            COMMAND_HISTORY
        )

    except:
        pass


# =========================
# GET NEXT JOB NUMBER
# =========================
def get_next_job_number():

    used_numbers = set()

    for job in BACKGROUND_JOBS:
        used_numbers.add(
            job["job_number"]
        )

    job_number = 1

    while job_number in used_numbers:
        job_number += 1

    return job_number


# =========================
# REAP COMPLETED JOBS
# =========================
def reap_completed_jobs():

    global BACKGROUND_JOBS

    output = ""

    total_jobs = len(
        BACKGROUND_JOBS
    )

    jobs_to_remove = []

    for index, job in enumerate(
        BACKGROUND_JOBS
    ):

        process = job["process"]

        if process.poll() is None:
            continue

        marker = " "

        if index == total_jobs - 1:
            marker = "+"

        elif index == total_jobs - 2:
            marker = "-"

        output += (
            f"[{job['job_number']}]"
            f"{marker}  "
            f"{'Done':<24}"
            f"{job['command_done']}\n"
        )

        jobs_to_remove.append(job)

    for job in jobs_to_remove:

        BACKGROUND_JOBS.remove(job)

    if output:
        sys.stdout.write(output)
        sys.stdout.flush()


# =========================
# BUILTIN OUTPUT
# =========================
def builtin_output(program, args):

    actual_args = clean_args(args)

    if program == "echo":

        return (
            " ".join(actual_args)
            + "\n"
        )

    elif program == "pwd":

        return (
            os.getcwd()
            + "\n"
        )

    elif program == "type":

        if not actual_args:
            return ""

        cmd = actual_args[0]

        if cmd in BUILTINS:

            return (
                f"{cmd} is a shell builtin\n"
            )

        executable = locate_in_path(cmd)

        if executable:

            return (
                f"{cmd} is {executable}\n"
            )

        return (
            f"{cmd}: not found\n"
        )

    elif program == "history":

        history_entries = COMMAND_HISTORY

        if (
            len(actual_args) >= 2
            and (
                actual_args[0] == "-r"
                or actual_args[0] == "-w"
                or actual_args[0] == "-a"
            )
        ):

            return ""

        if actual_args:

            try:

                count = int(actual_args[0])

                history_entries = (
                    COMMAND_HISTORY[-count:]
                )

                start_index = (
                    len(COMMAND_HISTORY)
                    - len(history_entries)
                    + 1
                )

            except:

                start_index = 1

        else:

            start_index = 1

        output = ""

        for index, command in enumerate(
            history_entries,
            start=start_index
        ):

            output += (
                f"{index:>5}  "
                f"{command}\n"
            )

        return output

    return ""


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

        if len(matches) == 1:

            match = matches[0]

            if os.path.isdir(match):
                matches[0] = match + "/"
            else:
                matches[0] = match + " "

    else:

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
# MULTI PIPELINE EXECUTION
# =========================
def execute_pipeline(command):

    commands = [
        shlex.split(cmd.strip())
        for cmd in command.split("|")
    ]

    processes = []

    previous_stdout = None

    for index, parts in enumerate(commands):

        program = parts[0]
        args = parts[1:]

        is_last = (
            index == len(commands) - 1
        )

        if program in BUILTINS:

            if previous_stdout is not None:

                previous_stdout.read()

                previous_stdout.close()

            output = builtin_output(
                program,
                args
            )

            if is_last:

                sys.stdout.write(output)

            else:

                temp_process = subprocess.Popen(
                    ["cat"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                )

                temp_process.stdin.write(
                    output
                )

                temp_process.stdin.close()

                previous_stdout = (
                    temp_process.stdout
                )

                processes.append(
                    temp_process
                )

            continue

        process = subprocess.Popen(
            [program] + args,
            stdin=previous_stdout,
            stdout=(
                subprocess.PIPE
                if not is_last
                else None
            ),
            text=True,
        )

        if previous_stdout is not None:
            previous_stdout.close()

        if not is_last:
            previous_stdout = (
                process.stdout
            )

        processes.append(process)

    for process in processes:
        process.wait()


# =========================
# EXTERNAL COMMANDS
# =========================
def execute_external(program, args):

    executable = locate_in_path(program)

    if not executable:
        sys.stderr.write(
            f"{program}: command not found\n"
        )
        return

    background = False

    if args and args[-1] == "&":

        background = True

        args = args[:-1]

    redirect = parse_redirect(args)

    if background:

        process = subprocess.Popen(
            [program] + args
        )

        job_number = get_next_job_number()

        job = {
            "job_number": job_number,
            "pid": process.pid,
            "command_running": (
                f"{program} {' '.join(args)} &"
            ),
            "command_done": (
                f"{program} {' '.join(args)}"
            ),
            "process": process,
        }

        BACKGROUND_JOBS.append(job)

        BACKGROUND_JOBS.sort(
            key=lambda job: job["job_number"]
        )

        print(
            f"[{job_number}] {process.pid}"
        )

        return

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

    global LAST_HISTORY_APPEND_INDEX

    load_history_from_histfile()

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

        reap_completed_jobs()

        try:
            command = input("$ ")

        except EOFError:
            break

        except KeyboardInterrupt:
            print()
            continue

        if not command.strip():
            continue

        COMMAND_HISTORY.append(command)

        if "|" in command:

            execute_pipeline(command)

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

        if program == "exit":

            if actual_args and actual_args[0] == "0":
                sys.exit(0)

            break

        elif program == "echo":

            output = builtin_output(
                program,
                actual_args
            )

            write_output(
                output,
                redirect
            )

        elif program == "pwd":

            output = builtin_output(
                program,
                actual_args
            )

            write_output(
                output,
                redirect
            )

        elif program == "history":

            if (
                len(actual_args) == 2
                and actual_args[0] == "-r"
            ):

                filepath = actual_args[1]

                try:

                    with open(
                        filepath,
                        "r"
                    ) as file:

                        for line in file:

                            line = line.rstrip("\n")

                            if line.strip():

                                COMMAND_HISTORY.append(
                                    line
                                )

                except:
                    pass

                output = ""

            elif (
                len(actual_args) == 2
                and actual_args[0] == "-w"
            ):

                filepath = actual_args[1]

                try:

                    with open(
                        filepath,
                        "w"
                    ) as file:

                        for entry in COMMAND_HISTORY:

                            file.write(
                                entry + "\n"
                            )

                    LAST_HISTORY_APPEND_INDEX = len(
                        COMMAND_HISTORY
                    )

                except:
                    pass

                output = ""

            elif (
                len(actual_args) == 2
                and actual_args[0] == "-a"
            ):

                filepath = actual_args[1]

                try:

                    with open(
                        filepath,
                        "a"
                    ) as file:

                        new_entries = COMMAND_HISTORY[
                            LAST_HISTORY_APPEND_INDEX:
                        ]

                        for entry in new_entries:

                            file.write(
                                entry + "\n"
                            )

                    LAST_HISTORY_APPEND_INDEX = len(
                        COMMAND_HISTORY
                    )

                except:
                    pass

                output = ""

            else:

                output = builtin_output(
                    program,
                    actual_args
                )

            write_output(
                output,
                redirect
            )

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

        elif program == "jobs":

            output = ""

            total_jobs = len(
                BACKGROUND_JOBS
            )

            jobs_to_remove = []

            for index, job in enumerate(
                BACKGROUND_JOBS
            ):

                marker = " "

                if index == total_jobs - 1:
                    marker = "+"

                elif index == total_jobs - 2:
                    marker = "-"

                process = job["process"]

                if process.poll() is None:

                    status = "Running"

                    command_text = (
                        job["command_running"]
                    )

                else:

                    status = "Done"

                    command_text = (
                        job["command_done"]
                    )

                    jobs_to_remove.append(job)

                output += (
                    f"[{job['job_number']}]"
                    f"{marker}  "
                    f"{status:<24}"
                    f"{command_text}\n"
                )

            for job in jobs_to_remove:

                BACKGROUND_JOBS.remove(job)

            write_output(
                output,
                redirect
            )

        elif program == "complete":

            if (
                len(actual_args) == 3
                and actual_args[0] == "-C"
            ):

                COMPLETION_SCRIPT_REGISTRY[
                    actual_args[2]
                ] = actual_args[1]

                output = ""

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

        elif program == "type":

            output = builtin_output(
                program,
                actual_args
            )

            write_output(
                output,
                redirect
            )

        else:
            execute_external(program, args)


if __name__ == "__main__":
    main()