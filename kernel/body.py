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
    blob = ((stdout or "") + " " + (stderr or "")).lower()
    signs = ("oci runtime exec failed", "procready not received",
             "error executing setns", "container not found",
             "is not running", "cannot exec in a stopped")
    return any(s in blob for s in signs)


#: Everything the creature's shell is allowed to inherit from the engine's own
#: environment. An ALLOW-LIST, not a deny-list: a deny-list has to be updated
#: every time a new secret-shaped variable appears, and it will not be.
CHILD_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TZ", "TERM")


class LocalBody:
    """A temp tree and a subprocess. For tests and for a kernel that has no
    container available. Not a sandbox: it is for running OUR fixtures, never
    untrusted input."""

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
            p = subprocess.run(
                ["bash", name], cwd=self.mind, capture_output=True, text=True,
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

    def __init__(self, container, image=None, mind=None, init=True):
        self.container = container
        self.image = image
        self.mind = mind
        self.init = init

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

    def argv(self, cmd):
        """No `-e` and no `--env`: `docker exec` passes none of the host's
        environment by default, and the whole point of this body is that the
        engine's environment -- and the key files it reads -- are not in the
        creature's world at all."""
        return ["docker", "exec", self.container, "sh", "-c", self.compose(cmd)]

    def responds(self):
        r = self.run("echo alive", timeout=20)
        return (not r.setup_failed) and r.code == 0 and "alive" in r.stdout

    def respawn(self):
        """Restart the container and prove it answers. Unlike `LocalBody`'s,
        this one really can bring the body back: the creature's world is a
        bind mount on the host, so restarting the container does not touch
        it. (`LocalBody.respawn` cannot, which is PLAN item 15.)"""
        try:
            subprocess.run(["docker", "restart", self.container],
                           capture_output=True, text=True, timeout=60)
        except Exception:
            return False
        return self.responds()

    def run(self, cmd, timeout=EXEC_TIMEOUT_SECS):
        try:
            p = subprocess.run(self.argv(cmd),
                               capture_output=True, text=True, timeout=timeout)
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


def ensure_body(body, journal=None):
    """Prove it responds; respawn once if not. Never reads a status field."""
    if body.responds():
        return True
    if journal:
        journal.append("body_unresponsive", detail="exec probe did not answer")
    ok = bool(getattr(body, "respawn", lambda: False)())
    if journal:
        journal.append("body_respawn", ok=ok)
    return ok
