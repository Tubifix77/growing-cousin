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


class LocalBody:
    """A temp tree and a subprocess. For tests and for a kernel that has no
    container available. Not a sandbox: it is for running OUR fixtures, never
    untrusted input."""

    def __init__(self, root=None, can_respawn=True):
        # can_respawn=False models the case the parent actually hit: the body is
        # gone AND bringing it back fails too. A body that merely died is
        # recoverable and `ensure_body` is meant to recover it.
        self.can_respawn = can_respawn
        self.root = root or tempfile.mkdtemp(prefix="cousin-body-")
        self.mind = os.path.join(self.root, "mind")
        os.makedirs(os.path.join(self.mind, "tools", "own"), exist_ok=True)
        os.makedirs(os.path.join(self.mind, "data"), exist_ok=True)
        self._alive = True

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
                timeout=timeout,
                env=dict(os.environ, MIND=self.mind, HOME=self.root))
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
        self._cleanup()
        shutil.rmtree(self.root, ignore_errors=True)


class DockerBody:
    """The real body. Same contract as LocalBody.

    Deliberately thin: PID 1 must reap (`--init`), or every orphan becomes a
    permanent zombie -- 9,082 of them in the parent, until the PID namespace was
    full and the body could not fork.
    """

    def __init__(self, container, image=None, mind=None, init=True):
        self.container = container
        self.image = image
        self.mind = mind
        self.init = init

    def responds(self):
        r = self.run("echo alive", timeout=20)
        return (not r.setup_failed) and r.code == 0 and "alive" in r.stdout

    def run(self, cmd, timeout=EXEC_TIMEOUT_SECS):
        try:
            p = subprocess.run(
                ["docker", "exec", self.container, "sh", "-c", cmd],
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
