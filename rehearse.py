#!/usr/bin/env python3
"""rehearse.py -- break it on purpose, somewhere safe.

Four paths in this engine are deployed, load-bearing, and have **never once
fired in production**: the supervisor giving up, the body being respawned, a
rung walled as needing a human, and the journal torn by a crash. `NRestarts`
has been 0 for the life of the project and `rung_broken` has been 0 with it.
So "it works" rested entirely on the gate -- and the gate structurally cannot
test half of it, because systemd owns the other half.

This manufactures each fault on a scratch root and keeps the journal, which
does two things at once:

1. **Proves the production-shaped chain**, unit and all: exit 5 ->
   `Restart=on-failure` -> `StartLimit` bounding the retries -> `failed` for
   real. No amount of in-process testing reaches that.
2. **Gives four detectors their first red.** `gave_up`, `engine_silent`,
   `journal_integrity` and `tool_vanished` have no proof from real data
   because the faults they watch for have never happened. *A test that has
   never been seen red is a guess* -- so the drills produce the data.

**It cannot touch the live run, and that is enforced twice.** The deployed
root is refused by name, and any root already holding a journal is refused
whatever it is called -- the second catches a live root that was moved or
renamed, which the first cannot. One guard is a guess.

    python3 rehearse.py tool-gone --scratch /tmp/drill
    python3 rehearse.py giveup   --scratch /tmp/drill   # Linux + systemd
    python3 rehearse.py all      --scratch /tmp/drill --emit-fixtures
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from kernel import backends                      # noqa: E402
from kernel import body as bodymod               # noqa: E402
from kernel.cycle import Engine                  # noqa: E402
from kernel.journal import Journal               # noqa: E402

FIXTURES = os.path.join(HERE, "tests", "fixtures", "journal")
FIXTURE_CAP = 240


class RefusedLiveRoot(Exception):
    """The target is, or looks like, a root something is living in."""


def may_use(root):
    """`(ok, why)`. Two independent guards, applied to the path AND EVERY
    ANCESTOR.

    **The ancestor walk is not thoroughness, it is a repair.** The first
    version tested only the path itself, and the first time this harness ran
    against `~/growing-cousin/live` it sailed through -- because `main()`
    appends the drill's name, so the target was `.../live/tool-gone`, which
    is neither named `live` nor holds a journal. It created a directory
    inside the running deployment. Nothing was damaged and the engine never
    noticed, but a guard that checks one literal is the shape §5 names most
    often, and here it was guarding the one thing that must not be touched.
    """
    p = os.path.realpath(os.path.expanduser(str(root)))
    cur = p
    while True:
        parts = [x for x in cur.replace("\\", "/").rstrip("/").split("/") if x]
        if len(parts) >= 2 and parts[-1] == "live" and parts[-2] == "growing-cousin":
            return False, ("%s is inside the deployed root %s -- a creature "
                           "lives there" % (p, cur))
        if os.path.exists(os.path.join(cur, "journal.jsonl")):
            return False, ("%s is inside %s, which already holds a journal, so "
                           "something has lived there; drills only ever run on "
                           "a root they made themselves" % (p, cur))
        parent = os.path.dirname(cur)
        if parent == cur:
            return True, p
        cur = parent


def scratch_root(root):
    """Prepare a root for a drill, or refuse. Refusing is the DEFAULT: a
    caller cannot opt out, because the caller is the one about to break
    things."""
    ok, why = may_use(root)
    if not ok:
        raise RefusedLiveRoot(why)
    os.makedirs(why, exist_ok=True)
    return why


# ------------------------------------------------------------------ fixtures

def scrub(rec):
    """The same scrubbing every fixture in this repo gets: think bodies out,
    long fields cut with a marker, every event and every other field kept."""
    r = dict(rec)
    if r.get("kind") == "think" and "raw" in r:
        r["raw_chars"] = len(r.get("raw") or "")
        r["raw"] = "[dropped from fixture]"
    for f in ("stdout", "stderr", "cmd", "to_creature", "tried", "outcome",
              "text", "detail", "raw"):
        v = r.get(f)
        if isinstance(v, str) and len(v) > FIXTURE_CAP and f != "raw":
            r[f] = v[:FIXTURE_CAP] + "…[fixture cut %d]" % (len(v) - FIXTURE_CAP)
    return r


def emit_fixture(name, journal_path, keep_bad=False):
    """Write `tests/fixtures/journal/0916-drill-<name>.jsonl`.

    `keep_bad` carries the torn line through verbatim: the torn-journal
    fixture is worthless if the fixture writer repairs it on the way out,
    which is exactly the shape of instrument this project keeps building by
    accident.
    """
    from monitor import pack
    os.makedirs(FIXTURES, exist_ok=True)
    out = os.path.join(FIXTURES, "0916-drill-%s.jsonl" % name)
    lines = []
    for raw in io.open(journal_path, encoding="utf-8", errors="replace"):
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        try:
            lines.append(json.dumps(scrub(json.loads(raw)), ensure_ascii=False))
        except ValueError:
            if keep_bad:
                lines.append(raw)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    hits = pack.scan_secrets([(out, out)])
    if hits:
        os.remove(out)
        raise SystemExit("REFUSED: %s" % pack.describe_hits(hits))
    print("  fixture %s (%d lines, %d bytes)"
          % (os.path.basename(out), len(lines), os.path.getsize(out)))
    return out


# -------------------------------------------------------------- in-process

ACCEPT = ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\noutcome: it worked\n"
          "to_creature: I used it and it did what it said.\n"
          "want: something further\nCOUSIN")


def _engine(root, replies, cousin_replies):
    j = Journal(os.path.join(root, "journal.jsonl"))
    b = bodymod.LocalBody(os.path.join(root, "body"))
    e = Engine(j, b, "BRIEF", backends.scripted(replies),
               backends.scripted(cousin_replies),
               os.path.join(root, "context.md"))
    e.write_context("# Your world\n\nBuild something.")
    return e, j, b


def drill_tool_gone(root):
    """A library tool that is not on PATH -- the 2026-09-12 relative-root
    scar, where every tool became `command not found` while the body reported
    healthy and 135 assertions stayed green. `LocalBody` puts nothing on
    PATH, so writing a tool and then calling it by name reproduces it exactly:
    the file is there, the journal knows it is a tool, and the shell cannot
    find it."""
    write = ("```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n"
             "# does: keeps the plan\\n# call: plan list\\necho ok\\n' "
             "> tools/own/plan && chmod +x tools/own/plan\n```")
    call = "```bash\nplan list\n```"
    e, j, b = _engine(root, [write, call], [ACCEPT])
    e.run_cycle()
    e.run_cycle()
    b.destroy()
    return j.path


def drill_torn(root):
    """A journal torn by a crash mid-append. The engine fsyncs every record,
    so a torn line means the process died inside one write -- which is what
    an abrupt shutdown looks like, and what nothing here has ever seen."""
    e, j, b = _engine(root, ["```bash\necho one\n```", "```bash\necho two\n```"],
                      [ACCEPT])
    e.run_cycle()
    e.run_cycle()
    b.destroy()
    full = io.open(j.path, encoding="utf-8").read()
    with io.open(j.path, "w", encoding="utf-8", newline="\n") as f:
        f.write(full)
        f.write('{"ts": %.1f, "kind": "exec_end", "exit_c'
                % (time.time() + 1))     # died here, mid-record
    return j.path


def drill_silence(root):
    """An engine that simply stops. There is no event for *nothing
    happening*, which is why `engine_silent` reads the clock rather than the
    journal -- and why it cannot be proven by replaying a journal against its
    own last timestamp."""
    e, j, b = _engine(root, ["```bash\necho alive\n```",
                             "```bash\necho still here\n```"], [ACCEPT])
    e.run_cycle()
    e.run_cycle()
    b.destroy()
    return j.path


# ------------------------------------------------------------------ systemd

UNIT = """[Unit]
Description=Growing Cousin GIVE-UP DRILL (throwaway; scratch root only)
StartLimitIntervalSec=120
StartLimitBurst=2

[Service]
Type=simple
WorkingDirectory={repo}
ExecStart=/usr/bin/python3 -u {repo}/run.py --forever --cycles 0 --pause 0 \\
    --root {root} --rungs {rungs}
Restart=on-failure
RestartSec=1
# NO PrivateUsers ON PURPOSE. The live unit has it and its selfcheck has
# therefore only ever PASSED; the disproven branch has never been seen in
# production shape. Here $HOME is writable, so `home_write_blocked` comes
# back False and the engine starts anyway -- which is the other half of the
# contract: a selfcheck records, it never vetoes.
StandardOutput=append:{root}/engine.log
StandardError=append:{root}/engine.log
"""

# A rung whose key file does not exist. `read_key` raises `no credential`,
# `classify_error` WALLs that, the ladder exhausts all-walled, and the
# supervisor counts a FAILURE rather than a wait. Five of those end the run.
# **Nothing is ever sent anywhere** -- the call dies before the request is
# built, so this drill touches no provider and spends no quota.
#
# `kind` is NOT optional here even though `from_spec` defaults it: the default
# is `ollama`, which takes no `base_url`, so omitting it died with a TypeError
# before a single journal record was written -- the drill failing in a way the
# drill could not report, which is the shape it exists to find elsewhere.
RUNGS = [{"name": "drill/no-such-credential",
          "kind": "openai_chat",
          "model": "gemma-4-31b-it",
          "base_url": "https://example.invalid/v1",
          "key_file": "/nonexistent/drill.key"}]


def _sysd(*args):
    return subprocess.run(["systemctl", "--user"] + list(args),
                          capture_output=True, text=True, timeout=30)


def _show(unit, prop):
    r = _sysd("show", unit, "-p", prop, "--value")
    return (r.stdout or "").strip()


def _sha(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def drill_giveup(root, live_root=None, wait_secs=120):
    """The chain systemd owns, end to end, under a real unit."""
    if os.name != "posix":
        raise SystemExit("the give-up drill needs systemd; run it on the laptop")
    live = live_root or os.path.expanduser("~/growing-cousin/live")
    # WHAT THE DRILL COULD DAMAGE, not what the engine is doing. The first
    # version hashed the live journal -- which the running engine appends to
    # every few seconds, so it could never come back unchanged and the check
    # reported a breach on every run. A checker that cannot distinguish the
    # thing it measures. The drill's only possible damage is CREATING
    # something in there, which is exactly what it did before the guard was
    # fixed, so the entry set is the thing to watch.
    def entries():
        try:
            return sorted(os.listdir(live))
        except OSError:
            return None
    before = entries()

    rungs = os.path.join(root, "rungs.drill.json")
    with io.open(rungs, "w", encoding="utf-8", newline="\n") as f:
        json.dump(RUNGS, f, indent=1)
    unit_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(unit_dir, exist_ok=True)
    name = "cousin-giveup-drill.service"
    unit_path = os.path.join(unit_dir, name)
    with io.open(unit_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(UNIT.format(repo=HERE, root=root, rungs=rungs))
    _sysd("daemon-reload")
    _sysd("reset-failed", name)
    _sysd("start", name)

    deadline = time.time() + wait_secs
    state = "unknown"
    while time.time() < deadline:
        state = _show(name, "ActiveState")
        if state in ("failed",):
            break
        time.sleep(2)

    ev = {"unit": name,
          "exit_code": int(_show(name, "ExecMainStatus") or -1),
          "n_restarts": int(_show(name, "NRestarts") or 0),
          "final_state": state,
          "result": _show(name, "Result")}
    rows = []
    jpath = os.path.join(root, "journal.jsonl")
    if not os.path.exists(jpath):
        # The drill itself failed before the engine wrote anything. Say so
        # with the log rather than raising: a harness that dies while
        # reporting is the fault it was built to catch.
        ev["drill_failed"] = "no journal was written; see %s/engine.log" % root
        return jpath, ev
    for raw in io.open(jpath, encoding="utf-8", errors="replace"):
        try:
            rows.append(json.loads(raw))
        except ValueError:
            pass
    from collections import Counter
    ev["kinds"] = dict(Counter(r.get("kind") for r in rows))
    ends = [r for r in rows if r.get("kind") == "loop_end"]
    ev["loop_end_fault"] = bool(ends and ends[-1].get("fault"))
    ends_reason = ends[-1].get("reason") if ends else None
    ev["loop_end_reason"] = ends_reason
    sc = [r for r in rows if r.get("kind") == "selfcheck"]
    ev["selfcheck_home_write_blocked"] = (sc[-1].get("home_write_blocked")
                                          if sc else None)
    ev["live_unchanged"] = (entries() == before)
    ev["live_entries"] = before

    _sysd("stop", name)
    _sysd("reset-failed", name)
    try:
        os.remove(unit_path)
    except OSError:
        pass
    _sysd("daemon-reload")
    return jpath, ev


FABRICATE = ("<<<COUSIN\nverdict: ACCEPTED\ntried: I ran plan\n"
             "outcome: it exited with code 0 and printed the plan\n"
             "to_creature: plan works -- it exited with code 0 when I ran it.\n"
             "want: a way to sort what it prints\nCOUSIN")


def drill_fabricate(root):
    """A verdict describing an event that did not happen.

    This is the fault the whole design exists to prevent, committed by the
    agent meant to catch it -- and it has never occurred: 159 real verdicts
    in run 2 produced **zero** HIGH census findings. So `complaint_fidelity`
    was the one detector with no proof it fires on anything the kernel
    actually wrote, and a detector proven only on rows a test made up is a
    guess about its own plumbing.

    The cousin here claims a clean exit for a tool the probe could not run at
    all. Nothing is faked downstream: the kernel writes the probe, the kernel
    writes the verdict, and the census reads what the kernel wrote.
    """
    write = ("```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n"
             "# does: keeps the plan\\n# call: plan list\\necho ok\\n' "
             "> tools/own/plan && chmod +x tools/own/plan\n```")
    e, j, b = _engine(root, [write, "```bash\necho nothing\n```"], [FABRICATE])
    e.run_cycle()
    b.destroy()
    return j.path


IN_PROCESS = {"tool-gone": drill_tool_gone, "torn": drill_torn,
              "silence": drill_silence, "fabricate": drill_fabricate}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("drill", choices=sorted(IN_PROCESS) + ["giveup", "all"])
    ap.add_argument("--scratch", required=True,
                    help="a directory the drill may destroy; never a live root")
    ap.add_argument("--emit-fixtures", action="store_true")
    ap.add_argument("--live-root", default=None,
                    help="the root to prove UNTOUCHED (default ~/growing-cousin/live)")
    args = ap.parse_args(argv)

    names = sorted(IN_PROCESS) + ["giveup"] if args.drill == "all" else [args.drill]
    rc = 0
    for name in names:
        base = os.path.join(args.scratch, name)
        if os.path.isdir(base):
            shutil.rmtree(base, ignore_errors=True)
        try:
            root = scratch_root(base)
        except RefusedLiveRoot as e:
            sys.stderr.write("REFUSED: %s\n" % e)
            return 3
        print("== drill %s -> %s" % (name, root))
        if name == "giveup":
            if os.name != "posix":
                print("  skipped: needs systemd")
                continue
            jpath, ev = drill_giveup(root, args.live_root)
            print("  " + json.dumps(ev, sort_keys=True))
            if args.emit_fixtures:
                os.makedirs(FIXTURES, exist_ok=True)
                out = os.path.join(FIXTURES, "0916-drill-giveup.evidence.json")
                with io.open(out, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(ev, f, indent=1, sort_keys=True)
                print("  evidence %s" % os.path.basename(out))
                emit_fixture(name, jpath)
            if ev["exit_code"] != 5 or ev["final_state"] != "failed":
                rc = 1
        else:
            jpath = IN_PROCESS[name](root)
            if args.emit_fixtures:
                emit_fixture(name, jpath, keep_bad=(name == "torn"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
