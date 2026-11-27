# 🐚 pysh — A POSIX Shell Built From Scratch in Python

A working Unix shell written from first principles in Python, with **no shell libraries** — just
the standard library and the operating system underneath it. Built as part of the
[CodeCrafters](https://codecrafters.io) "Build Your Own Shell" challenge, then taken well past the
base stages.

**~1,350 lines · 75 commits · zero third-party dependencies**

---

## ✨ What it does

This is not a toy REPL that shells out to `os.system`. It implements the pieces a real shell needs:

| Feature | Detail |
|---|---|
| 🔨 **Builtins** | `echo`, `exit`, `type`, `pwd`, `cd`, `history`, `jobs`, `declare`, `complete` |
| 🔗 **Multi-stage pipelines** | `a \| b \| c` — arbitrary length, processes wired together and run concurrently |
| 📤 **Redirection** | `>`, `1>`, `>>`, `1>>`, `2>`, `2>>` — stdout and stderr, truncate and append |
| 🧮 **Parameter expansion** | Shell variables via `declare`, expanded inside tokens at evaluation time |
| ⌨️ **Tab completion** | Built on `readline`, with multi-match display |
| 🧩 **Programmable completion** | A `complete` builtin that registers per-command completion scripts, like bash |
| 🧵 **Background jobs** | `&` execution, job numbering, a `jobs` builtin, and reaping of finished children |
| 📜 **Persistent history** | `history` builtin with load/save to a `HISTFILE` across sessions |
| 🔤 **Correct quoting** | Single quotes, double quotes and escapes handled through `shlex` |
| 🔍 **PATH resolution** | External programs located on `PATH` and executed as child processes |

---

## 🏗️ How it works

```
input line
   │
   ├─▶ readline            line editing, history recall, tab completion
   │
   ├─▶ shlex               tokenize with correct quoting rules
   │
   ├─▶ expand_variables    substitute shell variables into tokens
   │
   ├─▶ parse_redirect      peel off >, >>, 2>, 2>> and their targets
   │
   ├─▶ split on '|'        build the pipeline stages
   │
   ├─▶ builtin?  ──yes──▶  run in-process (cd must change *this* process)
   │        │
   │        no
   │        ▼
   └─▶ execute_pipeline    subprocess.Popen per stage, stdout of each
                           wired to stdin of the next, multiplexed with
                           `selectors` so no stage deadlocks on a full pipe
```

### Design notes

**Builtins must run in-process.** `cd` is the clearest example: if you fork a child to run it, the
child changes directory and exits, and the parent shell has not moved. Anything that mutates shell
state — `cd`, `declare`, `exit` — has to execute inside the shell process itself.

**Pipelines need I/O multiplexing.** Chaining `Popen` objects naively deadlocks as soon as one stage
fills the OS pipe buffer while another is still waiting to write. The pipeline executor uses
`selectors` to watch all the file descriptors at once and drain whichever is ready.

**Quoting is harder than splitting on spaces.** `echo "hello   world"` must preserve the internal
spacing, and `echo 'a"b'` must not treat the inner quote as a delimiter. `shlex` handles the POSIX
rules rather than reimplementing them badly.

**Redirection is parsed, not regexed away.** `REDIRECT_OPS` maps each operator to a target stream
and a file mode, so adding a new operator is a one-line change. Parent directories of a redirect
target are created on demand.

---

## 🚀 Running it

```bash
git clone https://github.com/Dileep-3dev/codecrafters-shell-python.git
cd codecrafters-shell-python

./your_program.sh
```

Requires Python 3.x and [`uv`](https://docs.astral.sh/uv/). No other dependencies.

### Try it

```bash
$ echo "hello world"
hello world

$ ls -la | grep ".py" | wc -l
3

$ echo failure 2> errors.log

$ declare GREETING=hi
$ echo $GREETING
hi

$ sleep 5 &
[1] 48213
$ jobs
[1] Running    sleep 5
```

---

## 📁 Structure

```
codecrafters-shell-python/
├── app/
│   └── main.py          # the entire shell
├── your_program.sh      # launcher
├── pyproject.toml
└── codecrafters.yml
```

`main.py` is organized in labelled sections: parameter expansion, history, job control,
programmable completion, autocomplete, output handling, pipeline execution and external commands.

---

## 🧠 What I learned

- How a REPL becomes a shell once you add process control
- Why `fork`/`exec` semantics mean builtins and externals cannot share one code path
- That pipe buffers are finite, and what happens when you forget
- How `readline` completion hooks actually work, and how bash's `complete` is wired on top of them
- Reading POSIX specs to settle arguments about edge cases instead of guessing

---

## 🗺️ Next

- [ ] Command substitution — `$(...)`
- [ ] Conditional operators — `&&`, `||`
- [ ] Signal handling — `Ctrl-C` interrupting the foreground job only
- [ ] Here-documents — `<<`

---

## 👨‍💻 Author

**Dileep Modalavalasa**
[GitHub](https://github.com/Dileep-3dev) · [LinkedIn](https://www.linkedin.com/in/dileep-modalavalasa-7b3b24343/)
