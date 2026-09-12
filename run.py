#!/usr/bin/env python3
"""run.py -- a creature and its cousin, actually running.

    python run.py --cycles 10
    python run.py --cycles 10 --model gemma4:12b --root ./live

Both agents are the same model, because both sit on the same ladder. The
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

from kernel import backends, body as bodymod
from kernel.cycle import Engine
from kernel.journal import Journal


def install_hands(body):
    """The creature's hands go on PATH inside the body. They are OURS: protected
    scar tissue, never edited to work around something the creature did."""
    dest = os.path.join(body.root, "bin")
    os.makedirs(dest, exist_ok=True)
    for n in os.listdir(os.path.join(HERE, "hands")):
        src = os.path.join(HERE, "hands", n)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dest, n)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
    return dest


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
    """
    import subprocess
    for pre in ("/mnt/", "/"):
        probe = "test -d %sc && echo yes" % pre
        try:
            r = subprocess.run(["bash", "-c", probe], capture_output=True,
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
        if self.bin:
            # The creature's own tools go on PATH too. The prompt tells it its
            # tools are on PATH; a prompt that promises something the body does
            # not provide is a contract violation, and the creature pays for it.
            own = bash_path(os.path.join(self.mind, "tools", "own"))
            cmd = ('export PATH="%s:%s:$PATH"; export MIND="%s"; %s'
                   % (bash_path(self.bin), own, bash_path(self.mind), cmd))
        return bodymod.LocalBody.run(self, cmd, timeout=timeout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=10)
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--root", default=os.path.join(HERE, "live"))
    ap.add_argument("--fresh", action="store_true", help="wipe --root first")
    ap.add_argument("--rungs", default=os.path.join(HERE, "rungs.local.json"),
                    help="ladder spec; falls back to --model when absent")
    ap.add_argument("--cousin-rungs", default=None,
                    help="separate ladder for the cousin (default: same as the "
                         "creature's). The manager is 13%% of calls; serving it "
                         "from a rung that answers cleanly but uselessly "
                         "produces confident garbage instead of a visible "
                         "failure.")
    args = ap.parse_args()

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

    # 3072 for the creature, not 900. The think contract puts the ```bash block
    # LAST, so a truncated reply loses the entire action and the call is wasted
    # outright -- measured here 2026-09-11 at 2 of 10 cycles, and the parent
    # raised its own ceiling for exactly this reason. max_tokens is a cap, not
    # an allocation: the extra is only spent on replies that were being cut off.
    # The cousin emits a short verdict block and needs far less.
    spec = backends.load_spec(args.rungs)
    cousin_spec = backends.load_spec(args.cousin_rungs) or spec
    if spec:
        ask_creature = backends.from_spec(spec, journal=j)
        ask_cousin = backends.from_spec(cousin_spec, journal=j)
        served = " -> ".join(r.get("name", r.get("model", "?")) for r in spec)
    else:
        # No ladder configured. The local standin, and SAY SO -- a run that
        # silently falls back to a standin is a run whose numbers get quoted
        # later as if they came from the real rung.
        ask_creature = backends.ollama(args.model, num_predict=3072)
        ask_cousin = backends.ollama(args.model, num_predict=700)
        served = "%s (local standin -- no ladder configured)" % args.model

    # Prove both backends answer before a single record is written. A run that
    # cannot reach its models has nothing to report, and a journal full of
    # failures they never produced is worse than no journal.
    for ask, what in ((ask_creature, "creature"), (ask_cousin, "cousin")):
        ok, why = backends.preflight(ask, "%s via %s" % (what, served))
        if not ok:
            sys.stderr.write("REFUSED: %s\nNothing was recorded.\n" % why)
            return 3
    if not body.responds():
        sys.stderr.write("REFUSED: the body does not answer a probe.\n")
        return 3

    # The creature's identity is SERVED, never written into the managed file.
    # Conflating them meant the cousin could not write direction without
    # overwriting who the creature is.
    e = Engine(j, body, cousin_brief, ask_creature, ask_cousin,
               os.path.join(args.root, "context.md"),
               creature_brief=creature_brief)

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

    print("creature + cousin on %s, %d cycles, root=%s\n"
          % (served, args.cycles, args.root))
    t0 = time.time()
    for i in range(1, args.cycles + 1):
        c0 = time.time()
        try:
            r = e.run_cycle()
        except Exception as ex:
            import traceback
            j.append("error", where="cycle",
                     detail="%s: %s" % (type(ex).__name__, ex))
            print("  %2d  CYCLE RAISED %s: %s" % (i, type(ex).__name__, ex))
            traceback.print_exc()
            continue
        tools = len(os.listdir(os.path.join(body.mind, "tools", "own")))
        print("  %2d  %-13s exec=%-2s trig=%-11s verdict=%-8s tools=%-3s %4.0fs"
              % (i,
                 "substantive" if r.get("substantive") else (r.get("reason") or "-"),
                 r.get("executed", 0),
                 ",".join(r.get("triggers") or []) or "-",
                 r.get("verdict") or "-", tools, time.time() - c0))

    print("\n%d cycles in %.0fs" % (args.cycles, time.time() - t0))
    print("journal kinds: %s" % dict(j.kinds()))
    print("tools built  : %s" % sorted(
        os.listdir(os.path.join(body.mind, "tools", "own"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
