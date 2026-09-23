#!/usr/bin/env python3
"""body.py -- where the creature's commands actually run.

An interface, because the body is disposable by design and because tests must
not need a container. `LocalBody` runs in a temp tree; `DockerBody` runs in the
real thing. The kernel never knows which.

Bounds that must hold whichever body is in use, each from a parent scar:

- **Every exec has a timeout**, and the timeout binds the EXEC, not just the
  child it spawns.
- **Liveness is proved by DOING, never by a status field.** `docker inspect
  .State.Running` read `true` for three and a half hours while the body could
  not fork a single process, and the creature received OCI errors shaped exactly
  like the output of its own commands.
- **Infrastructure failure goes to stderr with stdout EMPTY.** If the body
  itself is broken, that must never arrive looking like a command's output.
"""
import os
import re
import shutil
import time
import subprocess
import tempfile

EXEC_TIMEOUT_SECS = 300


class ExecResult:
    def __init__(self, stdout, stderr, code, setup_failed=False):
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.setup_failed = setup_failed

    def __repr__(self):
        return "ExecResult(code=%r, setup_failed=%r)" % (self.code, self.setup_failed)


def exec_setup_failure(stdout, stderr, code):
    """THE one classifier for 'the body broke' vs 'the command failed'.

    Called by the producer and by any checker. The parent's rule: a producer and
    a checker that share a literal will drift and no test notices, so there is
    exactly one of these.
    """
    # A COMMAND THAT SUCCEEDED DID NOT FAIL TO START, whatever it printed.
    # The markers below are matched anywhere in the output, and "is not
    # running" is ordinary English: a tool reporting `worker is not running`
    # and exiting 0 would have had its output discarded and its exit relabelled
    # as a broken body -- and, on the cousin's side, its verdict never asked
    # for. Measured over the live journal 2026-09-21 before adding this: 0 hits
    # in 2,929 records, so it was a latent hazard rather than a live defect.
    # The spine's version of this function has asked the question first since
    # 2026-08, and says why: 125-128 are also legitimate exit codes for a
    # command that really did run.
    if code == 0:
        return False
    blob = ((stdout or "") + " " + (stderr or "")).lower()
    signs = ("oci runtime exec failed", "procready not received",
             "error executing setns", "container not found",
             "is not running", "cannot exec in a stopped",
             # The body runs with --pids-limit 256, so a fork storm inside it
             # makes docker refuse to start the process at all. Without this
             # the refusal reaches the cousin shaped exactly like the tool's
             # own output, which is a fabricated experience (§2.5) with the
             # framework as its author. Safe to add only because of the
             # guard above: a healthy command may legitimately print it.
             "resource temporarily unavailable",
             "error response from daemon",
             "no such container")
    return any(s in blob for s in signs)


#: Everything the creature's shell is allowed to inherit from the engine's own
#: environment. An ALLOW-LIST, not a deny-list: a deny-list has to be updated
#: every time a new secret-shaped variable appears, and it will not be.
CHILD_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TZ", "TERM")


# WINDOWS PUTS A TRAP AHEAD OF PATH, AND IT COST THIS PROJECT ITS SECOND
# THE CODEC IS NAMED, NEVER THE HOST'S PREFERENCE. `text=True` with no
# `encoding=` decodes with `locale.getpreferredencoding(False)`, which is a
# property of the machine the ENGINE runs on -- not of the creature, whose
# tools write UTF-8. 939 of 2,792 live outputs contain non-ASCII (`…` from our
# own withheld-marker, and `✓ ⏰ ↔` from `plan` itself).
#
# Found 2026-09-23 by running the engine against a local model on the Windows
# box, which is the development environment §4 asks for and which this project
# had not used for a multi-cycle run. There, preferred is cp1252 and BOTH
# failure modes are the framework corrupting the creature's work:
#
#   - bytes cp1252 maps land as mojibake -- `✓` arrives as `â`, silently;
#   - bytes it does not map (0x8f, 0x90, 0x9d) raise UnicodeDecodeError in
#     subprocess's reader thread, and the output is simply gone.
#
# Linux is safe today only by accident of PEP 538: Python coerces the C locale
# to UTF-8, so a unit with no `LANG` still decodes correctly. That is the
# 2026-09-13 scar's shape -- a protection that holds because of the
# environment rather than because anything declared it -- so it is declared.
#
# `errors="replace"` rather than strict: the creature's own output must never
# be able to kill its own command. A replacement character is a visible,
# honest loss; an exception here returns `setup_failed=True`, which respawns
# the body and discards the visit, blaming infrastructure for a tick mark.
#
# GATE. `subprocess.run(["bash", ...])` resolves the name through
# CreateProcess, which searches `System32` BEFORE anything on PATH -- and
# `System32\bash.exe` is the **WSL launcher**. It starts a different kernel
# with a different filesystem, is handed a Windows `cwd` and a relative script
# name, and fails on every command while looking like a shell that answered.
#
# Measured 2026-09-17 by an independent verifier: 92 failures, twice, identical
# by name, `code=124` zero times -- every one a cascade from that single bare
# name. Same shape as the relative-root scar of 2026-09-12: the body reports
# healthy and nothing it runs can see the world it was pointed at.
#
# **Invariant: a body resolves the interpreter it promises, and RECORDS which
# binary answered.** A search order nobody chose is a constant nobody chose.
WSL_LAUNCHER_DIRS = ("system32", "syswow64")


def usable_bash(candidates):
    """The first candidate that is a real bash rather than Windows' launcher.

    None when there is no such thing, because a body that cannot keep its
    promise must say so rather than quietly run a different kernel.
    """
    for p in candidates:
        if not p:
            continue
        # SPLIT ON BOTH SEPARATORS, never `os.path`. Caught by the laptop gate
        # the minute this shipped: on Linux `os.path.dirname` does not treat a
        # backslash as a separator, so a Windows path inspected on Linux has
        # no parent at all and the trap check silently never fired. A policy
        # that only holds on the platform it was written for is the constant
        # nobody chose, one level up.
        parts = [q for q in re.split(r"[\\/]+", p.strip()) if q]
        parent = parts[-2].lower() if len(parts) >= 2 else ""
        if parent in WSL_LAUNCHER_DIRS:
            continue
        return p
    return None


_BASH = []


def find_bash():
    """An absolute bash, chosen once and cached. `None` if none is usable."""
    if _BASH:
        return _BASH[0]
    import shutil as _sh
    seen, cands = set(), []

    def add(p):
        if p and p not in seen:
            seen.add(p)
            cands.append(p)

    add(os.environ.get("COUSIN_BASH"))      # an operator's override, honoured first
    add(_sh.which("bash"))
    # Git for Windows ships the bash this project's scripts are written for.
    for root in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"),
                 os.environ.get("ProgramFiles(x86)")):
        if not root:
            continue
        for rel in (("Git", "bin", "bash.exe"), ("Git", "usr", "bin", "bash.exe")):
            add(os.path.join(root, *rel))
    for p in ("/bin/bash", "/usr/bin/bash", "/usr/local/bin/bash"):
        add(p)
    cands = [p for p in cands if os.path.isfile(p)] or cands
    _BASH.append(usable_bash(cands))
    return _BASH[0]


class LocalBody:
    """A temp tree and a subprocess. For tests and for a kernel that has no
    container available. Not a sandbox: it is for running OUR fixtures, never
    untrusted input."""

    # NOTHING HERE CONFINES ANYTHING, and callers must be able to ask rather
    # than know. `run` is `bash <script>` with `cwd=self.mind`: a working
    # directory is a convenience, not a boundary, and `..`, an absolute path
    # or `$MIND/../..` walks straight out of it.
    #
    # Added 2026-09-16 after an independent verifier breached the cousin's
    # supposed boundary six ways in this body -- including ADDING a tool to
    # the creature's library, which makes the second user a second builder,
    # the one thing §2.3 exists to forbid.
    CONTAINED = False

    def __init__(self, root=None, can_respawn=True):
        # can_respawn=False models the case the parent actually hit: the body is
        # gone AND bringing it back fails too. A body that merely died is
        # recoverable and `ensure_body` is meant to recover it.
        self.can_respawn = can_respawn
        # ABSOLUTE, always. Commands run with cwd=self.mind, so a relative root
        # yields relative PATH entries that resolve against the mind directory
        # and therefore point nowhere -- every tool becomes `command not found`
        # while the body still looks healthy.
        #
        # 2026-09-12, measured: a run started with `--root live` produced 13
        # consecutive honest RETURNED verdicts saying the command was not found,
        # and the creature responded exactly as it should have -- by rebuilding
        # the tool three different ways (fetcher.py, fetcher, fetcher_wrapper.sh).
        # **The framework broke the work and the creature was billed for it**,
        # which is the one outcome this project exists to prevent. Normalising
        # here rather than at the caller because there is no caller who benefits
        # from a relative root, and any caller can forget.
        # RECORDED, not inferred. `--body docker` shipped once while the
        # engine still ran `LocalBody`, and nothing could see which it was.
        self.shell_path = find_bash()
        self.root = os.path.abspath(root or tempfile.mkdtemp(prefix="cousin-body-"))
        self.mind = os.path.join(self.root, "mind")
        os.makedirs(os.path.join(self.mind, "tools", "own"), exist_ok=True)
        os.makedirs(os.path.join(self.mind, "data"), exist_ok=True)
        self._alive = True

    def child_env(self):
        """What the creature's shell inherits. **An allow-list.**

        Until 2026-09-13 this was `dict(os.environ, ...)`: the creature's bash
        received the ENGINE's entire environment. Found by an outside review of
        the public repo, and confirmed on the live laptop the same evening --
        a creature-style command run from the body's own directory read
        `~/keys/*.key` and listed the spine's directory, `config.yaml` included.

        The input to this shell is bash written by free-tier third-party
        models. This class's own docstring says it is "not a sandbox... for
        running OUR fixtures, never untrusted input", and it has been running
        untrusted input in production since deployment. That contradiction is
        the finding; this is the cheap half of the repair.

        What this DOES fix: every secret-shaped variable in the engine's
        environment -- including any rung configured with `key_env` -- stops
        being one `echo` away.

        What it does NOT fix, and must not be read as fixing: the key FILES
        stay readable by any process running as this user, because the engine
        reads them per call and shares a uid with the shell it spawns. Closing
        that needs `DockerBody` -- which the design has always named as the
        real body -- or systemd `LoadCredential=` plus `InaccessiblePaths=` on
        the key directory. That is a deployment decision and it is Tue's.

        HOME points into the body, so `~` in a generated command resolves to
        the creature's own tree rather than the host's.
        """
        env = {k: os.environ[k] for k in CHILD_ENV_KEEP if k in os.environ}
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        env["HOME"] = self.root
        env["MIND"] = self.mind
        return env

    def responds(self):
        """Ask it to DO something. Never trust a status field."""
        try:
            r = self.run("echo alive", timeout=15)
            return (not r.setup_failed) and r.code == 0 and "alive" in r.stdout
        except Exception:
            return False

    def run(self, cmd, timeout=EXEC_TIMEOUT_SECS):
        if not self._alive:
            return ExecResult("", "body is down", 128, setup_failed=True)
        # Write the command to a script in the mind and run it by a RELATIVE
        # name. Never as an argv string, never as an absolute path.
        #
        # 2026-09-11, measured twice. First: `bash -c "<cmd>"` lost `$MIND` out
        # of a QUOTED heredoc -- `<< 'EOF'`, which by definition does not expand
        # -- so the creature's tool reached disk as `os.path.expandvars("")`
        # with a hole in its own comment, died on every run, and the cousin
        # reported that honestly six times. **The framework damaged the work and
        # the creature was blamed for it.** Then the fix -- writing a script and
        # running it by path -- moved the problem instead of removing it: the
        # path was spelled for the wrong shell and every command returned 127.
        #
        # A relative script has neither failure: nothing to mangle, nothing to
        # spell. (stdin via `bash -s` was tried in between and hung.)
        name = ".cmd-%d.sh" % os.getpid()
        # The environment the creature's shell gets is an ALLOW-LIST; see
        # `child_env` for why, and for what it deliberately does not fix.
        # $MIND is derived by the SHELL from its own working directory, not
        # handed in from outside. Passing it through `env=` sets a host variable
        # that the shell may never inherit -- measured 2026-09-11: it arrived
        # empty, so every tool the creature wrote to "$MIND/data/..." would have
        # written to "/data" and died on permissions. `pwd` is always right and
        # needs no translation, because the working directory IS the mind.
        preamble = 'export MIND="$(pwd)"\n'
        with open(os.path.join(self.mind, name), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(preamble + (cmd if cmd.endswith("\n") else cmd + "\n"))
        try:
            # RELATIVE, because cwd is already the mind. An absolute path would
            # have to be spelled the way this particular shell spells host
            # paths, and getting that wrong is what produced 127 on every
            # command a moment ago. A relative name needs no translation at all.
            shell = self.shell_path
            if not shell:
                # Honest infrastructure failure, never shaped like the
                # creature's own output: stdout stays empty and the caller
                # sees `setup_failed`.
                return ExecResult(
                    "", "no usable bash on this host: the only candidates are "
                    "Windows' WSL launcher, which cannot see this working "
                    "directory. Set COUSIN_BASH to a real bash.", 127,
                    setup_failed=True)
            p = subprocess.run(
                [shell, name], cwd=self.mind, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout, env=self.child_env())
            out, err, code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            # A timeout is the bound working, not an error to hide.
            return ExecResult("", "timed out after %ds" % timeout, 124)
        except Exception as e:
            return ExecResult("", "%s: %s" % (type(e).__name__, e), 128,
                              setup_failed=True)
        if exec_setup_failure(out, err, code):
            # stdout EMPTY: infrastructure breakage must never reach the
            # creature shaped like its own command's output.
            return ExecResult("", (out or "") + (err or ""), code,
                              setup_failed=True)
        return ExecResult(out, err, code)

    def kill(self):
        self._alive = False

    def respawn(self):
        if not self.can_respawn:
            return False
        self._alive = True
        return self.responds()

    def _cleanup(self):
        try:
            os.unlink(os.path.join(self.mind, ".cmd-%d.sh" % os.getpid()))
        except OSError:
            pass

    def destroy(self):
        """Remove the body. Returns whether the root actually went away.

        `ignore_errors=True` alone is a cleanup that cannot report its own
        failure. On Windows the just-exited `bash` can still hold the command
        script for a moment, rmtree fails, and NOTHING says so -- measured
        2026-09-12, 191 stale `cousin-*` directories in temp while the gate was
        intermittently failing its liveness assertion. One retry clears the
        lock; the return value means a caller that cares can find out, instead
        of the fault being invisible by construction.
        """
        self._cleanup()
        for attempt in (0, 1):
            shutil.rmtree(self.root, ignore_errors=True)
            if not os.path.exists(self.root):
                return True
            if attempt == 0:
                time.sleep(0.2)
        return False


class DockerBody:
    """The real body. Same contract as LocalBody.

    Deliberately thin: PID 1 must reap (`--init`), or every orphan becomes a
    permanent zombie -- 9,082 of them in the parent, until the PID namespace was
    full and the body could not fork.
    """

    # Where the creature's world is mounted INSIDE the container. `self.mind`
    # stays the HOST path, because the kernel reads those files itself -- the
    # library listing, the memory, the tool inventory. The two must never be
    # confused: a host path inside a container command is the relative-root
    # scar with a different spelling.
    MIND = "/mind"
    HANDS = "/hands"

    # A CONTAINER IS A BOUNDARY. Only what is bind-mounted exists inside it,
    # so a body whose mount is its own mind cannot reach anything else --
    # which is what lets the cousin's copy be structural rather than a guard.
    CONTAINED = True

    def __init__(self, container, image=None, mind=None, init=True,
                 recreate=None):
        self.container = container
        self.image = image
        self.mind = mind
        self.init = init
        # Supplied by the caller that knows the mounts. See `respawn`.
        self.recreate = recreate

    def compose(self, cmd):
        """The creature's command, with the world its prompt promises.

        `DockerBody` was written and never exercised, and it ran
        `docker exec <container> sh -c <cmd>` bare: no working directory, no
        PATH. The prompt tells the creature its tools are on PATH and its
        hands are callable by name, and `PathBody` keeps that promise by
        overriding `run` -- so switching bodies would have silently broken
        every tool while the body reported healthy. That is exactly the
        2026-09-12 relative-root scar, which cost thirteen honest refusals
        and a creature rebuilding one tool three ways.
        """
        return ('export PATH="%s:%s/tools/own:$PATH"; export MIND="%s"; '
                'export HOME="%s"; cd "%s" || exit 1; %s'
                % (self.HANDS, self.MIND, self.MIND, self.MIND, self.MIND, cmd))

    SHELL = "bash"

    def argv(self, cmd):
        """No `-e` and no `--env`: `docker exec` passes none of the host's
        environment by default, and the whole point of this body is that the
        engine's environment -- and the key files it reads -- are not in the
        creature's world at all.

        **`bash`, because that is the shell the contract names.** The prompt
        says *write ```bash blocks*, the parser requires the `bash` tag, and
        `LocalBody` ran `bash <script>` -- while this ran `sh -c`, which on
        the image is dash. Switching bodies for item 7 changed the creature's
        interpreter without anyone deciding to. Measured 2026-09-16 over 307
        commands: zero dash-only failures, one bash-only construct written --
        so the cost was nil and this is a promise-keeping fix, not a rescue.
        It is fixed anyway, because a promise the body does not keep is the
        relative-root scar's shape, and the next model may write `[[`."""
        return ["docker", "exec", self.container, self.SHELL, "-c",
                self.compose(cmd)]

    def responds(self):
        r = self.run("echo alive", timeout=20)
        return (not r.setup_failed) and r.code == 0 and "alive" in r.stdout

    def respawn(self):
        """Bring the body back: restart it, and RECREATE it if it is gone.

        **PLAN item 15, decided 2026-09-16, and item 7 is what decided it.**
        The question was whether a body that cannot be respawned should end
        the run. For `LocalBody` the answer stays no and the gap stays open,
        because its "body" IS the creature's world: recreating it would hand
        back an empty tree and call that a recovery, which is §2.1 violated
        by the framework itself.

        A container is not like that. The creature's world is a bind mount on
        the HOST -- its 71 tools, its data, its memory -- and the container is
        just a process with an interpreter in it. Restarting or even
        rebuilding one destroys nothing. So the rule that falls out is:

          **a respawn may recreate a CONTAINER, and must never recreate a
          MIND.**

        `recreate` is supplied by whoever built the body (`run.py`), because
        it is the only thing that knows the mounts; without it this degrades
        to a restart and still never invents a world.
        """
        try:
            r = subprocess.run(["docker", "restart", self.container],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60)
        except Exception:
            return False
        if r.returncode == 0 and self.responds():
            return True
        if callable(getattr(self, "recreate", None)):
            try:
                self.recreate()
            except Exception:
                return False
            return self.responds()
        return False

    def run(self, cmd, timeout=EXEC_TIMEOUT_SECS):
        # A COMMAND THE SHELL CANNOT BE GIVEN IS NOT A BROKEN BODY. A NUL byte
        # makes `subprocess` raise before the process exists, and that left by
        # the generic handler below as `setup_failed=True` -- so the framework
        # would have declared the BODY broken over a byte in the creature's own
        # text, respawned it, and on the cousin's side thrown the probe away as
        # LOST. A fabricated infrastructure failure with us as its author
        # (§2.5). Never seen live; fixed because the cost of being wrong is a
        # respawn and a discarded visit, and the fix is one branch.
        if "\x00" in (cmd or ""):
            return ExecResult(
                "", "the command contains a null byte, which no shell can be "
                "given; nothing was run", 126)
        try:
            p = subprocess.run(self.argv(cmd),
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=timeout)
            out, err, code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            return ExecResult("", "timed out after %ds" % timeout, 124)
        except Exception as e:
            return ExecResult("", "%s: %s" % (type(e).__name__, e), 128,
                              setup_failed=True)
        if exec_setup_failure(out, err, code):
            return ExecResult("", (out or "") + (err or ""), code,
                              setup_failed=True)
        return ExecResult(out, err, code)


def ensure_body(body, journal=None, who="creature"):
    """Prove it responds; respawn once if not. Never reads a status field.

    `who` names the inhabitant whose body this is. The cousin got a body of
    its own on 2026-09-16 and nothing ever proved it before use: a dead
    cousin container would have handed the cousin an OCI error as the tool's
    own transcript, and the cousin would have judged the creature's work on
    it. Both bodies now go through here, and the record says which."""
    if body.responds():
        return True
    if journal:
        journal.append("body_unresponsive", who=who,
                       detail="exec probe did not answer")
    ok = bool(getattr(body, "respawn", lambda: False)())
    if journal:
        journal.append("body_respawn", who=who, ok=ok)
    return ok
