#!/usr/bin/env python3
"""run.py -- a creature and its cousin, actually running.

    python run.py --cycles 10
    python run.py --cycles 10 --model gemma4:12b --root ./live

Both agents sit on a ladder; `--cousin-rungs` gives the cousin its own, and
the deployed configuration uses that -- a rung that answers cleanly but without
a verdict block is useless to the cousin and fine for the creature. The
creature reads `CREATURE-PROMPT.md`; the cousin reads `MANAGER-PROMPT.md`. The
kernel serves the context and holds the bounds, and decides nothing.

Everything it does is inside `--root`. It never touches Growing Spine.
"""
import argparse
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kernel import backends, body as bodymod, forever, triggers as trigmod
from kernel.cycle import Engine
from kernel.journal import Journal


# The hands a USER of the creature's tools needs, as opposed to the hands a
# BUILDER needs. `recall` reads the memory some tools store their state in
# (`compare-with-baseline` reads its baseline back through it); `remember`
# writes it. Both act on `$MIND`, and the cousin's `$MIND` is a copy remade
# per visit, so `remember` in the cousin's shell changes nothing the creature
# will ever see. `tool-new` and `tool-edit` are building; `say` is the
# creature's half of the human channel. Neither is a user's.
USER_HANDS = ("recall", "remember")


def instrument_names():
    """The cousin's instruments, by name, read from the directory rather than
    typed. A list in prose is a constant nobody chose."""
    d = os.path.join(HERE, "instruments")
    if not os.path.isdir(d):
        return ()
    return tuple(sorted(n for n in os.listdir(d)
                        if os.path.isfile(os.path.join(d, n))))


def install_instruments(body):
    """`ARCHITECTURE.md` \u00a75, specified 2026-09-10 and built 2026-09-18:
    *a handful of small deterministic scripts -- startability, hollow-stub
    detection, duplicate-stem listing, dependency edges, store parse rates.
    They are tools, they live where tools live, and the cousin runs one when it
    wants to know something.*

    **Nothing schedules them, nothing caches them, and nothing turns their
    output into a warning.** That apparatus is the 99% this project deleted,
    and it is also what made the parent's dependency scan cost 187,489 regex
    scans per wake. A fact is gathered when somebody asks for it; deciding that
    the fact matters is the cousin's half.

    **THE CREATURE NEVER GETS THESE.** \u00a72.4: never tell the creature about
    its own bugs, because the diagnosis is its work and its growth. A
    hollow-stub detector pointed at its own library is exactly that sentence
    being broken by a script. They go in the second USER's bin only, which
    `ensure_container` mounts read-only.
    """
    dest = os.path.join(body.root, "bin")
    os.makedirs(dest, exist_ok=True)
    out = []
    d = os.path.join(HERE, "instruments")
    if not os.path.isdir(d):
        return out
    for n in instrument_names():
        dst = os.path.join(dest, n)
        shutil.copy2(os.path.join(d, n), dst)
        os.chmod(dst, 0o755)
        out.append(n)
    return out


def install_hands(body, only=None, keep=()):
    """The creature's hands go on PATH inside the body. They are OURS: protected
    scar tissue, never edited to work around something the creature did.

    `only` names the subset a body gets. The cousin's body used to get NONE,
    which kept it from building (right) and also kept it from running any
    tool that reads the creature's memory through `recall` (wrong, and
    invisible: the tool failed in the cousin's shell for a reason that was
    ours, the cousin reported it faithfully, and the creature was billed).
    """
    dest = os.path.join(body.root, "bin")
    os.makedirs(dest, exist_ok=True)
    if only is not None:
        # A subset is exact: anything else already there is a hand this body
        # must not have, whoever put it there. `keep` is the one exception and
        # it is passed in rather than assumed: the cousin's bin also holds its
        # instruments, which are not hands and must survive this prune.
        for n in os.listdir(dest):
            if n not in only and n not in keep:
                try:
                    os.unlink(os.path.join(dest, n))
                except OSError:
                    pass
    for n in os.listdir(os.path.join(HERE, "hands")):
        src = os.path.join(HERE, "hands", n)
        if not os.path.isfile(src) or (only is not None and n not in only):
            continue
        dst = os.path.join(dest, n)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
    return dest


# Which binary answered the question below. None until something actually
# needed translating, which on a posix host is never -- three states, so
# "nobody asked" and "asked the wrong shell" cannot render the same.
_PREFIX_SHELL = None


def _probe_prefix():
    """ASK the shell where a Windows drive lives. Never assume.

    2026-09-11, in three rounds: first the path was built with `os.path.join`
    and came out with backslashes; then `D:/x` went into PATH, where bash splits
    on the colon and the drive letter becomes its own entry; then it was
    translated Git-Bash style to `/d/x`, and the shell turned out to be WSL,
    where the same directory is `/mnt/d/x`. Each fix was a correct diagnosis of
    a real fault that was not the whole fault.

    Every round produced the same symptom -- the cousin reporting "command not
    found" over a perfectly good tool, truthfully, about an event the harness
    had invented. So this asks the shell instead of reasoning about it.

    **FOURTH ROUND, 2026-09-21, and it is PLAN 18.8 one layer up.** This asked
    a BARE `bash` -- the very name 18.8 had just stopped trusting. On a box
    with WSL installed the launcher answers `/mnt/` while the bash the body
    actually runs answers `/`, so every PATH entry reached the real shell as
    `/mnt/c/...`, a directory that does not exist there, and 23 assertions came
    back 127 with the body reporting healthy. **Asking the shell instead of
    reasoning about it is only right if you ask the shell that will answer.**
    The binary that answered is recorded in `_PREFIX_SHELL`, so a future
    disagreement is visible rather than inferred.
    """
    import subprocess
    global _PREFIX_SHELL
    shell = bodymod.find_bash() or "bash"
    _PREFIX_SHELL = shell
    for pre in ("/mnt/", "/"):
        probe = "test -d %sc && echo yes" % pre
        try:
            r = subprocess.run([shell, "-c", probe], capture_output=True,
                               text=True, timeout=20)
            if "yes" in r.stdout:
                return pre
        except Exception:
            pass
    return "/mnt/"


_PREFIX = None


def bash_path(p):
    """A path THIS shell will accept inside PATH. Windows-only; the real body is
    a Linux container where none of this exists."""
    global _PREFIX
    p = str(p).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        if _PREFIX is None:
            _PREFIX = _probe_prefix()
        p = _PREFIX + p[0].lower() + p[2:]
    return p


def install_python_shim(bindir):
    r"""NOT INSTALLED, and kept only as a record of a fix that caused the fault
    it was meant to prevent.

    A probe said `python: command not found`, so this shim was added to give the
    body the `python3` its prompt promises. But the shell already HAD
    /usr/bin/python3 -- the missing name was `python`, not `python3`. The shim
    then shadowed the real one with a Windows python.exe, which received a WSL
    path and read `/mnt/c/...` as `C:\mnt\c\...`, breaking every tool in the
    body. **Read what the probe said, not what it nearly said.**"""
    shim = os.path.join(bindir, "python3")
    lines = ["#!/bin/sh", 'exec "%s" "$@"' % bash_path(sys.executable), ""]
    with open(shim, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    os.chmod(shim, 0o755)


class PathBody(bodymod.LocalBody):
    """A body whose PATH carries the hands and the creature's own tools."""

    def __init__(self, root=None):
        bodymod.LocalBody.__init__(self, root=root)
        self.bin = None

    _as_shell_path = staticmethod(bash_path)

    def run(self, cmd, timeout=bodymod.EXEC_TIMEOUT_SECS):
        # The tools in this mind ALWAYS go on PATH; our hands only when this
        # body has them. The prompt tells the creature its tools are on PATH,
        # and a prompt that promises something the body does not provide is a
        # contract violation the creature pays for.
        #
        # The hands are conditional because the COUSIN gets one of these too
        # (PLAN item 9) and must not: it is the second user, never a second
        # builder (§2.3), so it gets the library to run and no `tool-edit` to
        # build with. Before 2026-09-16 a bin-less body put NOTHING on PATH,
        # so the cousin's own chosen command met `command not found` -- the
        # relative-root scar, arriving by the one door left open.
        own = bash_path(os.path.join(self.mind, "tools", "own"))
        parts = ([bash_path(self.bin)] if self.bin else []) + [own]
        cmd = ('export PATH="%s:$PATH"; export MIND="%s"; %s'
               % (":".join(parts), bash_path(self.mind), cmd))
        return bodymod.LocalBody.run(self, cmd, timeout=timeout)


def engine_identity(repo, spec=None, cousin_spec=None):
    """Which engine is writing this journal, so every window can name its
    instrument.

    CLAUDE.md §0: *every production figure must name its run* -- and within a
    run, its engine, because the code changed roughly twenty times inside run
    2. Yet the journal's only start record carried `pause` and `max_cycles`,
    so attributing an hour to a commit meant lining up systemd's start times
    against `git log` by hand, which is how a rate gets quoted for the wrong
    code. Recorded once per start, as fields: the commit, whether the tree was
    dirty, the caps in force, the rungs by name.

    `unknown` is an honest answer, and `None` for dirty means *could not
    tell*, never *clean*. Git runs with optional locks off: the deployed unit
    mounts the repo read-only, and a status that cannot write its index must
    still answer.
    """
    import platform
    import subprocess
    sha, dirty = "unknown", None
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            sha = r.stdout.strip()
        s = subprocess.run(["git", "-C", repo, "--no-optional-locks", "status",
                            "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, timeout=10)
        if s.returncode == 0:
            dirty = bool(s.stdout.strip())
    except Exception:
        pass
    from kernel import cycle as cyclemod
    from kernel import journal as journalmod

    def names(rungs):
        return [r.get("name", r.get("model", "?")) for r in (rungs or [])]

    return {
        "engine": sha,
        "dirty": dirty,
        "python": platform.python_version(),
        # From the constants, never retyped: a producer and a checker that
        # each carry their own copy of a number drift.
        "caps": {"exec_stdout": journalmod.EXEC_STDOUT_CHARS,
                 "exec_stderr": journalmod.EXEC_STDERR_CHARS,
                 "exec_cmd": journalmod.EXEC_CMD_CHARS,
                 "history_output": cyclemod.Engine.HISTORY_OUTPUT_CHARS,
                 "history_total": cyclemod.Engine.HISTORY_TOTAL_CHARS,
                 "think_raw": cyclemod.THINK_RAW_CHARS},
        "rungs": names(spec),
        "cousin_rungs": names(cousin_spec),
    }


def record_engine_start(journal, identity, **facts):
    """One record, its own kind, at every start. `facts` are this run's own:
    root, pause, forever."""
    return journal.append("engine_start", **dict(identity, **facts))


SELFCHECK_CANARY = ".cousin-selfcheck-canary"


def selfcheck(body, journal=None, home=None, keys_dir=None):
    """Prove the bounds this deployment relies on by their EFFECT, at every
    start, through the same shell the creature gets. Records; never vetoes.

    CLAUDE.md §5, 2026-09-13: `ProtectSystem=strict`, `ProtectHome=read-only`
    and `ReadWritePaths` were present, parsed and live in the unit for its
    whole life and did NOTHING, because a user unit needs `PrivateUsers=yes`
    for any of them to take effect. Two caps were in series and the one that
    was tuned was not the one that acted. Both were found by testing the
    effect, once, by hand. **A directive read back off a unit proves it was
    PARSED, never that it WORKS** -- so this tests the effects at every start
    and writes the answer where a monitor can read it.

    Three answers per effect, never two: True (proven), False (DISPROVEN) or
    None (not testable here -- no spine on a dev box, a body that did not
    answer). `ok` means *nothing was disproven*; it is never a claim that
    everything was proven, and `unproven` lists what could not be.

    It never refuses to start. A preflight that vetoes on a check is the scar
    one entry up (a transient at 22:00 costing the night); a disproven bound
    is for the monitor to shout about and a human to fix, with the engine
    running exactly as it did before anyone knew.

    It touches nothing of the spine's: the sibling check is a READ attempt
    that is supposed to fail. The home canary is created only where no
    sandbox stops it, and removed in the same command.
    """
    import shlex
    home = home or os.path.expanduser("~")
    out = {}

    def sh(cmd):
        try:
            r = body.run(cmd, timeout=20)
        except Exception as e:
            return None, "", str(e)
        if r.setup_failed:
            return None, r.stdout or "", r.stderr or ""
        return r.code, r.stdout or "", r.stderr or ""

    code, so, _ = sh("echo alive")
    out["body_answers"] = bool(code == 0 and "alive" in so)
    if out["body_answers"]:
        canary = shlex.quote(bash_path(os.path.join(home, SELFCHECK_CANARY)))
        code, so, _ = sh("if touch %s 2>/dev/null; then echo WROTE; rm -f %s; "
                         "else echo BLOCKED; fi" % (canary, canary))
        out["home_write_blocked"] = (None if code is None
                                     else ("BLOCKED" in so and "WROTE" not in so))
        spine = shlex.quote(bash_path(os.path.join(home, "growing-spine")))
        qhome = shlex.quote(bash_path(home))
        # FOUR ANSWERS, NOT THREE. Under the container the whole host home is
        # invisible, so `test -e` on the spine returns ABSENT -- and ABSENT
        # was folded into "cannot tell". That made the STRONGEST possible
        # result ("not even the home this path sits in exists in here")
        # indistinguishable from the weakest ("there is no spine on this
        # box"), which is this project's oldest fault committed inside the
        # selfcheck itself. Found 2026-09-16 by a verifier reading a
        # permanently-null field. The docker drill had the distinction all
        # along (`spine_invisible`); the per-start check did not.
        code, so, _ = sh("if ls %s >/dev/null 2>&1; then echo READABLE; "
                         "elif test -e %s; then echo BLOCKED; "
                         "elif test -e %s; then echo NO_SPINE_HERE; "
                         "else echo HOME_INVISIBLE; fi"
                         % (spine, spine, qhome))
        out["spine_unreadable"] = (
            None if (code is None or "NO_SPINE_HERE" in so)
            else ("BLOCKED" in so or "HOME_INVISIBLE" in so))
        # THE KEY FILES. PLAN item 7: the engine reads them per call and has
        # shared a uid with the creature's shell since deployment, so until
        # the body is a container this comes back False -- which is the point.
        # A bound nobody re-proves is a bound nobody notices losing.
        kd = keys_dir or os.path.join(home, "keys")
        if not os.path.isdir(kd):
            out["keys_unreadable"] = None
        else:
            q = shlex.quote(bash_path(kd))
            code, so, _ = sh("if cat %s/*.key >/dev/null 2>&1; then echo READ; "
                             "else echo BLOCKED; fi" % q)
            out["keys_unreadable"] = (None if code is None
                                      else ("BLOCKED" in so and "READ" not in so))
        code, so, _ = sh("command -v tool-edit >/dev/null 2>&1 && echo HAND")
        out["hand_on_path"] = None if code is None else ("HAND" in so)
        code, so, _ = sh("command -v python3 >/dev/null 2>&1 && echo PY")
        out["python3_on_path"] = None if code is None else ("PY" in so)
    else:
        for k in ("home_write_blocked", "spine_unreadable", "hand_on_path",
                  "python3_on_path", "keys_unreadable"):
            out[k] = None
    from kernel import cycle as cyclemod
    from kernel import journal as journalmod
    out["caps_ordered"] = (journalmod.EXEC_STDOUT_CHARS
                           >= cyclemod.Engine.HISTORY_OUTPUT_CHARS)
    out["unproven"] = sorted(k for k, v in out.items() if v is None)
    out["ok"] = not any(v is False for v in out.values())
    if journal is not None:
        journal.append("selfcheck", **out)
    return out


DOCKER_IMAGE = "growing-cousin-body"
DOCKER_CONTAINER = "growing-cousin-body"


def ensure_container(container, image, host_body, timeout=120):
    """The creature's container, created if absent and started if stopped.

    The creature's world is a BIND MOUNT of the same host directory the
    kernel reads -- `tools/own`, `data`, `state` -- so nothing about its
    library depends on the container surviving. That is what makes
    `DockerBody.respawn` able to do what `LocalBody.respawn` cannot (PLAN
    item 15): restarting this body does not touch what the creature built.

    Our hands go in read-only. They are protected scar tissue and the
    creature has no business editing them, which under `PathBody` was a
    convention and here is a mount option.
    """
    import subprocess
    if not hasattr(os, "getuid"):
        raise RuntimeError("a container body needs a POSIX host")

    def d(*a):
        return subprocess.run(["docker"] + list(a), capture_output=True,
                              text=True, timeout=timeout)

    # WHAT THIS BODY MUST BE MOUNTED WITH -- and the check that it IS. The
    # first version asked only `.State.Running`, so a container created under
    # an earlier configuration was reused as it stood: on 2026-09-16 the
    # cousin's container predated the user-hands mount and came back up
    # without `recall`, exactly the fault the mount had been added to close,
    # while the code said the mount was there. A directive present in the
    # code and absent from the running thing -- §5's oldest systemd shape.
    # Mounts are compared as (source, destination, writable); a mismatch
    # recreates the container, which costs nothing a container holds.
    want = {(os.path.realpath(host_body.mind), bodymod.DockerBody.MIND, True)}
    if getattr(host_body, "bin", None):
        want.add((os.path.realpath(host_body.bin), bodymod.DockerBody.HANDS, False))

    def mounts_of(name):
        r = d("inspect", "-f", "{{json .Mounts}}", name)
        if r.returncode != 0:
            return None
        try:
            import json
            data = json.loads(r.stdout or "[]")
        except ValueError:
            return None
        if not isinstance(data, list):
            # Not a mount list is CANNOT TELL, never a reason to act: a
            # daemon answering nonsense must not have containers recreated
            # under it on the strength of that nonsense.
            return None
        return {(os.path.realpath(m.get("Source", "")), m.get("Destination"),
                 bool(m.get("RW", True))) for m in data if isinstance(m, dict)}

    # WHAT THE BODY'S ENVIRONMENT MUST SAY. `--user uid:gid` with no matching
    # passwd entry leaves `HOME=/`, which is root-owned -- so `pip install
    # --user` dies on `[Errno 13] Permission denied: '/.local'` and the
    # creature cannot do the thing `CREATURE-PROMPT.md` tells it every cycle
    # it can: *act in it freely -- write files, install packages*.
    #
    # Pointing HOME at the mind PROVIDES the capability instead of retracting
    # the promise, and keeps a frozen prompt frozen. It is also the only
    # honest place for it: the mind is the one path that survives the body, so
    # a package installed there is still there after a respawn -- the prompt's
    # own durability rule applied to packages rather than an exception to it.
    # Verified in a throwaway container first: `import six ->
    # /mind/.local/lib/python3.11/site-packages/six.py`, still on the volume
    # afterwards.
    want_env = {"HOME": bodymod.DockerBody.MIND}

    def env_of(name):
        """The container's environment as a dict, or None if it cannot be read."""
        r = d("inspect", "-f", "{{json .Config.Env}}", name)
        if r.returncode != 0:
            return None
        try:
            import json
            data = json.loads(r.stdout or "[]")
        except ValueError:
            return None
        if not isinstance(data, list):
            return None
        out = {}
        for item in data:
            if isinstance(item, str) and "=" in item:
                k, _s, v = item.partition("=")
                out[k] = v
        return out

    def image_of(name):
        """The image id this container was CREATED from, or None."""
        r = d("inspect", "-f", "{{.Image}}", name)
        out = (r.stdout or "").strip()
        return out if r.returncode == 0 and out else None

    def image_now():
        """The image id that tag points at TODAY, or None."""
        r = d("image", "inspect", "-f", "{{.Id}}", image)
        out = (r.stdout or "").strip()
        return out if r.returncode == 0 and out else None

    st = d("inspect", "-f", "{{.State.Running}}", container)
    # THE SAME DRIFT QUESTION, one field over. A container keeps the
    # environment it was created with, so this would otherwise be present in
    # the code and absent from the running thing -- which this function has
    # already been bitten by for mounts and again for the image. BOTH
    # readable or nothing: an unreadable answer is CANNOT TELL and must never
    # destroy a container on the strength of it.
    if st.returncode == 0:
        env = env_of(container)
        if env is not None and any(env.get(k) != v for k, v in want_env.items()):
            print("container %s: environment changed since it was created -- "
                  "recreating (HOME=%r, want %r)"
                  % (container, env.get("HOME"), want_env["HOME"]))
            d("rm", "-f", container)
            st.returncode = 1
    have = mounts_of(container) if st.returncode == 0 else None
    if st.returncode == 0 and have is not None and have != want:
        print("container %s: mounts changed since it was created -- recreating "
              "(had %d mount(s), need %d)" % (container, len(have), len(want)))
        d("rm", "-f", container)
        st.returncode = 1
    # PLAN 18.4. A container is created FROM an image and keeps that image for
    # life, so `docker build` can succeed, the tag can move, and this body goes
    # on running yesterday's Dockerfile while every document says otherwise.
    # §5's oldest systemd shape a third time: present in the code, absent from
    # the running thing -- and the unit rebuilds the image on every start, so
    # the drift is guaranteed rather than unlikely.
    #
    # BOTH ids or nothing. An unreadable answer is CANNOT TELL and must never
    # recreate a container on the strength of it, exactly as for the mounts.
    if st.returncode == 0:
        was, now = image_of(container), image_now()
        if was and now and was != now:
            print("container %s: image changed since it was created -- "
                  "recreating (%s -> %s)" % (container, was[:19], now[:19]))
            d("rm", "-f", container)
            st.returncode = 1
    if st.returncode != 0:
        d("rm", "-f", container)
        argv = ["run", "-d", "--init", "--name", container,
                # The SAME uid that owns the mind on the host, so what the
                # creature writes stays readable by the engine and nothing in
                # the container runs as root.
                "--user", "%d:%d" % (os.getuid(), os.getgid()),
                "--memory", "1g", "--pids-limit", "256",
                "-e", "HOME=%s" % bodymod.DockerBody.MIND,
                "-v", "%s:%s" % (host_body.mind, bodymod.DockerBody.MIND)]
        # The hands only when this body HAS them. The cousin's body does not:
        # it is the second user, never a second builder (§2.3), so it gets the
        # library to run and no `tool-edit` to build with.
        if getattr(host_body, "bin", None):
            argv += ["-v", "%s:%s:ro" % (host_body.bin,
                                         bodymod.DockerBody.HANDS)]
        r = d(*(argv + [image, "sleep", "infinity"]))
        if r.returncode != 0:
            raise RuntimeError("could not start %s: %s"
                               % (container, (r.stderr or "")[-300:]))
    elif "false" in (st.stdout or "").strip().lower():
        d("start", container)
    body = bodymod.DockerBody(container, image=image, mind=host_body.mind)
    # PLAN item 15: a respawn may recreate a CONTAINER and must never recreate
    # a MIND. Only this function knows the mounts, so it hands the body a way
    # back rather than the body guessing one.
    body.recreate = lambda: ensure_container(container, image, host_body,
                                             timeout=timeout)
    return body


def build_ladders(spec, cousin_spec, journal=None, quota_state=None,
                  quota_path=None):
    """The three ladders the engine runs on, and the predicate each is given.

    **One place, because a test has to be able to drive the REAL construction.**
    Until 2026-09-21 this was three inline calls in `main`, so reverting that
    file alone -- removing the creature's predicate entirely -- left all 966
    assertions green: every test built its own ladder and asserted that the
    predicate worked, which says nothing about whether the engine was given
    it. Found by a verifier reverting the file to see what went red, and
    nothing did.

    **A predicate belongs to a QUESTION, not to an agent** (§5, 2026-09-16),
    and there are three questions here:

    - *what do you want to do* -- the creature. A think with no command is a
      REAL ANSWER and must never be rejected, or a rung is walled for thinking
      out loud. Only emptiness is rejected: see `think.unusable_think`.
    - *what do you make of it* -- the cousin. No verdict block is a failure.
    - *what would you like to run* -- the cousin again, and here no block is
      an ANSWER, not a failure, which is why it cannot share the ladder above.

    `quota_state` is SHARED across all three: what we know about a rung's
    quota is a fact about the rung, while what counts as a usable reply is a
    fact about what was asked.
    """
    from kernel import cousin as cousinmod
    from kernel.think import unusable_think
    ask_creature = backends.from_spec(spec, journal=journal,
                                      quota_state=quota_state,
                                      quota_path=quota_path,
                                      reject=unusable_think)
    ask_cousin = backends.from_spec(cousin_spec, journal=journal,
                                    quota_state=quota_state,
                                    quota_path=quota_path,
                                    reject=cousinmod.unusable_reply)
    ask_cousin_invoke = backends.from_spec(cousin_spec, journal=journal,
                                           quota_state=quota_state,
                                           quota_path=quota_path,
                                           reject=cousinmod.unusable_invocation)
    return ask_creature, ask_cousin, ask_cousin_invoke


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=10)
    ap.add_argument("--body", choices=("local", "docker"), default="local",
                    help="`docker` puts the creature in a container whose "
                         "world is a bind mount of <root>/body/mind. It is "
                         "the only body in which the engine's key files are "
                         "out of the creature's reach -- see PLAN item 7.")
    ap.add_argument("--container", default=DOCKER_CONTAINER)
    ap.add_argument("--image", default=DOCKER_IMAGE)
    ap.add_argument("--cousin-shell", action="store_true",
                    help="give the cousin a body of its own, so it can run "
                         "the tool with arguments it chooses instead of bare "
                         "(PLAN item 9). It gets a COPY of the library, "
                         "remade per visit, and none of our hands: it is the "
                         "second user, never a second builder (§2.3).")
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--root", default=os.path.join(HERE, "live"))
    ap.add_argument("--fresh", action="store_true", help="wipe --root first")
    ap.add_argument("--forever", action="store_true",
                    help="run until the stop file appears (--cycles becomes a "
                         "ceiling, 0 for no ceiling)")
    ap.add_argument("--stop-file", default=None,
                    help="touch this to stop after the current cycle "
                         "(default: <root>/STOP)")
    ap.add_argument("--pause", type=float, default=forever.PAUSE_SECS,
                    help="seconds between cycles; the free tier is rate-limited "
                         "and shared with the spine")
    ap.add_argument("--rungs", default=os.path.join(HERE, "rungs.local.json"),
                    help="ladder spec; falls back to --model when absent")
    ap.add_argument("--cousin-rungs", default=None,
                    help="separate ladder for the cousin (default: same as the "
                         "creature's). Serving the cousin from a rung that "
                         "answers cleanly but uselessly produces confident "
                         "garbage instead of a visible failure -- measured "
                         "2026-09-13: one rung returned 14 replies and 0 "
                         "usable verdicts. (The '~13%% of calls' figure that "
                         "used to be quoted here is a design estimate from the "
                         "parent, never measured on this engine; vitals.py "
                         "carries the real ratio.)")
    args = ap.parse_args(argv)

    if args.fresh and os.path.isdir(args.root):
        shutil.rmtree(args.root, ignore_errors=True)
    os.makedirs(args.root, exist_ok=True)

    creature_brief = open(os.path.join(HERE, "CREATURE-PROMPT.md"),
                          encoding="utf-8").read()
    cousin_brief = open(os.path.join(HERE, "MANAGER-PROMPT.md"),
                        encoding="utf-8").read()

    j = Journal(os.path.join(args.root, "journal.jsonl"))
    body = PathBody(os.path.join(args.root, "body"))
    body.bin = install_hands(body)
    if args.body == "docker":
        # The host-side PathBody above is still what creates the mind and
        # installs the hands; the container is then wrapped around exactly
        # those directories.
        body = ensure_container(args.container, args.image, body)
        print("body: container %s from image %s (mind bind-mounted at %s)"
              % (args.container, args.image, bodymod.DockerBody.MIND))

    # 3072 for the creature, not 900. The think contract puts the ```bash block
    # LAST, so a truncated reply loses the entire action and the call is wasted
    # outright -- measured here 2026-09-11 at 2 of 10 cycles, and the parent
    # raised its own ceiling for exactly this reason. max_tokens is a cap, not
    # an allocation: the extra is only spent on replies that were being cut off.
    # The cousin needs MORE, not less, and the opposite was assumed here until
    # 2026-09-13. Its contract also puts the block last, and the rung that
    # carries most of its traffic spends ~94%% of its budget deliberating
    # before reaching it: at 2048 it produced 14 replies and 0 usable verdicts,
    # every one cut at finish=length. Growing Spine reached the same conclusion
    # first -- "verdict-first fights how reasoning models generate", so fund
    # the musing rather than trying to suppress it. The deployed cousin ladder
    # is at 4096.
    spec = backends.load_spec(args.rungs)
    cousin_spec = backends.load_spec(args.cousin_rungs) or spec
    if spec:
        # BUILT IN ONE PLACE, so a test can drive the real construction. Until
        # 2026-09-21 the predicates were wired inline here and every test used
        # a ladder it had built itself, so reverting this file alone left the
        # whole gate green with the creature's predicate gone. That is the
        # 2026-09-16 shape -- a feature inert in production for fifteen hours
        # under a green gate -- and it is the second time this exact wiring
        # has been the thing nothing asserted.
        # ONE quota memory, shared by both ladders. The rungs are the same
        # accounts, so a rung the creature found spent is spent for the cousin
        # too -- two separate memories would each have to learn it, which is
        # two wasted requests against the sibling's account instead of one.
        qpath = os.path.join(args.root, "quota.json")
        qstate = backends.quotamod.load(qpath)
        ask_creature, ask_cousin, ask_cousin_invoke = build_ladders(
            spec, cousin_spec, journal=j, quota_state=qstate, quota_path=qpath)
        spent = backends.quotamod.spent_rungs(qstate)
        if spent:
            print("resumed with rungs still spent: %s" % ", ".join(spent))
        served = " -> ".join(r.get("name", r.get("model", "?")) for r in spec)
    else:
        # No ladder configured. The local standin, and SAY SO -- a run that
        # silently falls back to a standin is a run whose numbers get quoted
        # later as if they came from the real rung.
        ask_creature = backends.ollama(args.model, num_predict=3072)
        ask_cousin = backends.ollama(args.model, num_predict=700)
        ask_cousin_invoke = ask_cousin
        served = "%s (local standin -- no ladder configured)" % args.model

    # Prove both backends answer before a single record is written. A run that
    # cannot reach its models has nothing to report, and a journal full of
    # failures they never produced is worse than no journal.
    #
    # **But that is a rule for a run someone is WATCHING.** 2026-09-12, first
    # start on the laptop: gemini hung, the timeout fired, openrouter was at its
    # quota, and preflight refused -- correct for a bounded run, and exactly
    # wrong for an unattended one, where a transient hiccup at 22:00 costs the
    # whole night. The free tier is unreliable BY DEFINITION; that is the
    # condition this engine lives in, not an exception to it.
    #
    # So in `--forever` a failed preflight is a WARNING and the supervisor's
    # wait/backoff handles it -- that logic exists for precisely this, and it
    # already knows the difference between "come back later" and "broken".
    for ask, what in ((ask_creature, "creature"), (ask_cousin, "cousin")):
        ok, why = backends.preflight(ask, "%s via %s" % (what, served))
        if ok:
            continue
        if not args.forever:
            sys.stderr.write("REFUSED: %s\nNothing was recorded.\n" % why)
            return 3
        sys.stderr.write("WARNING: %s\nStarting anyway: --forever waits rungs "
                         "out rather than giving up on them.\n" % why)
        j.append("preflight_failed", who=what, detail=str(why)[:300])
        break
    if not body.responds():
        sys.stderr.write("REFUSED: the body does not answer a probe.\n")
        return 3

    # The first record of a run says WHICH ENGINE is running, so every figure
    # read out of this journal later can name its instrument. Then the bounds
    # this deployment relies on are tested by their effect and recorded --
    # never enforced here; see `selfcheck`.
    ident = engine_identity(HERE, spec, cousin_spec if spec else None)
    # WHICH BODY, asked of the object rather than of the flag. 2026-09-16:
    # `selfcheck` recorded `keys_unreadable` DISPROVEN at one start and true
    # again at the next, and the journal could not say whether the creature
    # had been contained in between -- that took `git show` against this
    # record's own commit SHA to read the unit file out of it. The newest
    # systemd scar is *there is no directive to read back, only an absence*,
    # and this record reproduced the absence. Asked of the body because the
    # flag is what was believed and the body is what runs.
    record_engine_start(j, ident, root=os.path.abspath(args.root),
                        pause=args.pause, forever=bool(args.forever),
                        body=type(body).__name__,
                        contained=bool(getattr(body, "CONTAINED", False)))
    print("engine %s%s  python %s"
          % (ident["engine"][:12],
             " (UNCOMMITTED CHANGES)" if ident["dirty"] else "",
             ident["python"]))
    sc = selfcheck(body, journal=j)
    disproven = sorted(k for k, v in sc.items() if v is False)
    if disproven:
        sys.stderr.write("SELFCHECK DISPROVED: %s. Starting anyway -- this is "
                         "for the monitor to report and a human to fix; a "
                         "start that refuses on a check is the preflight scar "
                         "again.\n" % ", ".join(disproven))
    else:
        print("selfcheck: nothing disproven%s"
              % ((" (could not test: %s)" % ", ".join(sc["unproven"]))
                 if sc["unproven"] else ""))

    # THE COUSIN'S OWN HANDS (PLAN item 9). A separate root, a separate
    # container, no hands of ours, and `Engine.sync_cousin_world` fills it
    # with a COPY of the creature's library before every visit.
    cousin_body = None
    if args.cousin_shell:
        host = PathBody(os.path.join(args.root, "cousin-body"))
        # A USER's hands only -- `recall` and `remember` -- never a builder's.
        # `ensure_container` mounts them read-only because `bin` is set.
        host.bin = install_hands(host, only=USER_HANDS,
                                 keep=instrument_names())
        # The second user's instruments (ARCHITECTURE 5). The creature's body
        # never calls this.
        install_instruments(host)
        if args.body == "docker":
            cousin_body = ensure_container(args.container + "-user",
                                           args.image, host)
        else:
            cousin_body = host
        # **A COUSIN SHELL IN AN UNCONFINED BODY IS A SECOND BUILDER.** The
        # copy of the library is what keeps §2.3 -- the manager never writes
        # the creature's tools -- and a copy only holds if the body cannot
        # reach past it. `LocalBody` cannot stop that: it is `bash <script>`
        # with `cwd=mind`, and a working directory is a convenience, not a
        # boundary. An independent verifier breached it six ways in minutes,
        # including ADDING a tool to the creature's library.
        #
        # So the deployment refuses the combination outright rather than
        # documenting the danger. Asked of the body, not of the flag: one
        # producer, one checker.
        if not getattr(cousin_body, "CONTAINED", False):
            sys.stderr.write(
                "REFUSED: --cousin-shell needs a body that confines what it "
                "runs, and %s does not.\nThe cousin chooses its own bash; "
                "without confinement the copy of the library it is given is "
                "a\nconvention rather than a boundary, and it can reach the "
                "creature's own tools --\nwhich makes the second USER a "
                "second BUILDER (CLAUDE.md §2.3).\nRun with --body docker, "
                "or without --cousin-shell.\n"
                % type(cousin_body).__name__)
            return 3
        print("cousin shell: %s (the creature's world copied in per visit; "
              "user hands %s; builder hands withheld)"
              % (args.container + "-user" if args.body == "docker"
                 else host.root, ", ".join(USER_HANDS)))

    # The creature's identity is SERVED, never written into the managed file.
    # Conflating them meant the cousin could not write direction without
    # overwriting who the creature is.
    e = Engine(j, body, cousin_brief, ask_creature, ask_cousin,
               os.path.join(args.root, "context.md"),
               creature_brief=creature_brief, cousin_body=cousin_body,
               ask_cousin_invoke=ask_cousin_invoke)

    # Pick up where a killed run left off. Derived from the journal, so there
    # is no savegame to go stale -- a crash costs the cycle in flight and
    # nothing before it.
    prior = e.resume()
    if prior:
        print("resumed: %d cycles already in this journal "
              "(since_visit=%d since_change=%d%s)"
              % (prior, e.cycles_since_visit, e.cycles_since_change,
                 ", carrying a refusal the creature has not read yet"
                 if e.done_blocked else ""))

    stop_file = args.stop_file or os.path.join(args.root, "STOP")
    print("creature + cousin on %s, root=%s" % (served, args.root))
    print("%s\nstop with:  touch %s\n"
          % ("running until stopped" if args.forever
             else "%d cycles" % args.cycles, stop_file))

    t0 = time.time()
    shown = {"i": 0}

    def one_cycle():
        """Raises on failure -- the supervisor decides what a failure means.

        Swallowing the exception here would hide a persistent fault from the
        one thing bounding it, and the loop would spin on a dead rung burning
        quota the spine also pays for.
        """
        shown["i"] += 1
        i, c0 = shown["i"], time.time()
        r = e.run_cycle()
        tools = len(trigmod.list_tools(os.path.join(body.mind, "tools", "own")))
        print("  %3d  %-13s exec=%-2s trig=%-11s verdict=%-8s tools=%-3s %4.0fs"
              % (i,
                 "substantive" if r.get("substantive") else (r.get("reason") or "-"),
                 r.get("executed", 0),
                 ",".join(r.get("triggers") or []) or "-",
                 r.get("verdict") or "-", tools, time.time() - c0),
              flush=True)     # unbuffered: a detached run must be readable live
        return r

    ceiling = None if (args.forever and args.cycles <= 0) else args.cycles
    sup = forever.Supervisor(one_cycle, stop_file, journal=j,
                             pause=args.pause if args.forever else 0.0)
    try:
        ran, why = sup.loop(max_cycles=ceiling)
    except forever.StopRequested as e2:
        sys.stderr.write("REFUSED: %s\n" % e2)
        return 4

    print("\n%d cycles in %.0fs -- %s" % (ran, time.time() - t0, why))
    if sup.ended_in_fault:
        # NON-ZERO, so `Restart=on-failure` actually restarts. Giving up is not
        # finishing, and until 2026-09-13 both exited 0: the engine could
        # abandon the run at 03:00, report success, and lie there until someone
        # looked. systemd bounds the retrying (StartLimitBurst in the unit), so
        # this does not reintroduce the crash loop that exiting 0 was guarding
        # against -- it is restarted a few times and then left down for real.
        sys.stderr.write("GAVE UP: %s\nExiting non-zero so the supervisor "
                         "restarts it rather than leaving it dead.\n" % why)
        return 5
    print("journal kinds: %s" % dict(j.kinds()))
    print("tools built  : %s" % sorted(
        os.listdir(os.path.join(body.mind, "tools", "own"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
