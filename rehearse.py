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
        leaf = parts[-1] if parts else ""
        if len(parts) >= 2 and leaf == "live" and parts[-2] == "growing-cousin":
            return False, ("%s is inside the deployed root %s -- a creature "
                           "lives there" % (p, cur))
        # §2.6 IS A BOUNDARY, NOT A HEURISTIC. *Never touch Growing Spine from
        # this repo.* It was allowed outright until 2026-09-16, when a
        # verifier tried it: the harness would have created and then removed
        # directories inside the sibling project without a murmur.
        if leaf == "growing-spine":
            return False, ("%s is inside %s -- CLAUDE.md §2.6 makes the "
                           "sibling project a hard boundary" % (p, cur))
        # A CHECKOUT IS SOMEBODY'S WORKING TREE. `~/growing-cousin` is the
        # live unit's WorkingDirectory and passed every earlier guard,
        # because it is not named `live` and holds no journal.
        if os.path.isdir(os.path.join(cur, ".git")):
            return False, ("%s is inside the git checkout %s -- drills do not "
                           "run in anybody's working tree" % (p, cur))
        if os.path.exists(os.path.join(cur, "journal.jsonl")):
            return False, ("%s is inside %s, which already holds a journal, so "
                           "something has lived there; drills only ever run on "
                           "a root they made themselves" % (p, cur))
        parent = os.path.dirname(cur)
        if parent == cur:
            return True, p
        cur = parent


def live_snapshot(live, digest=False):
    """Every path under the live root, relative and sorted, or None if there
    is no such root. With `digest`, the bytes of every file too.

    **Against a RUNNING engine, byte-identity is not a property anything can
    assert, and claiming it would be a checker that cannot distinguish the
    thing it measures.** The engine appends to the journal every few seconds
    and the creature rewrites its own tools; everything under the live root
    is its churn by definition. So the default is the strongest claim that
    can actually hold while the deployment runs: no path was CREATED or
    REMOVED, recursively, so a deletion three levels inside `tools/own` shows
    up. PLAN 6.7 said "byte-identical" for a while and a verifier was right
    to call that unbacked.

    `digest=True` is for a root NOTHING is writing -- the simulated live root
    in the gate, or the real one with the engine stopped. There byte-identity
    IS decidable, and the gate asserts it, because that is the case where a
    modification-in-place would otherwise pass unseen.
    """
    live = os.path.realpath(os.path.expanduser(str(live)))
    if not os.path.isdir(live):
        return None
    out = {} if digest else []
    for dp, dn, fn in os.walk(live):
        for n in list(dn) + list(fn):
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, live)
            if not digest:
                out.append(rel)
                continue
            if os.path.isfile(p) and not os.path.islink(p):
                h = hashlib.sha1()
                try:
                    with io.open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    out[rel] = h.hexdigest()
                except OSError as e:
                    out[rel] = "unreadable: %s" % e.__class__.__name__
            else:
                out[rel] = "(dir)" if os.path.isdir(p) else "(link)"
    return out if digest else sorted(out)


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
    before = live_snapshot(live)

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
    # A MISSING ROOT IS NOT AN UNCHANGED ONE. The first version swallowed the
    # error and returned None on both sides, so `None == None` reported
    # success having measured nothing -- and `--live-root` is a path a caller
    # can get wrong.
    ev["live_unchanged"] = bool(before) and live_snapshot(live) == before
    ev["live_paths_watched"] = len(before or ())

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


def drill_body(root):
    """The body dying under the creature, mid-cycle.

    `ensure_body` runs before every block and respawns a body that will not
    answer -- and in run 2 it never once had to: neither `body_unresponsive`
    nor `body_respawn` appears anywhere in the journal. So the one piece of
    machinery standing between a dead body and a creature being handed
    infrastructure failure shaped like its own output has never run outside
    the gate.

    Killed the way it could really die: the creature's own shell removes the
    mind it is standing in. That is not a contrived poke at a private flag --
    an unconstrained shell can do this, `$MIND` is handed to it on purpose,
    and the next block then finds nowhere to write its script.
    """
    kill = '```bash\nrm -rf "$MIND"\n```'
    after = "```bash\necho after the body died\n```"
    e, j, b = _engine(root, ["%s\n\n%s" % (kill, after)], [ACCEPT])
    e.run_cycle()
    b.destroy()
    return j.path


# --------------------------------------------------------------- the body

IMAGE = "growing-cousin-body"
CONTAINER = "growing-cousin-drill-body"


def _docker(*args, **kw):
    return subprocess.run(["docker"] + list(args), capture_output=True,
                          text=True, timeout=kw.get("timeout", 300))


def drill_docker(root, live_root=None, keys_dir=None):
    """Prove the creature's world before it becomes the creature's world.

    Every check here is an EFFECT run from inside the body, not a directive
    read back off a config -- the rule §5 earned twice in one evening, when
    a unit carrying three sandbox directives turned out to be enforcing none
    of them. And the capability checks matter as much as the containment
    ones: *a sandbox that breaks the run is discovered at 03:00 by nobody*,
    so this refuses to report success unless python3, bash, `requests`, our
    hands, the creature's own tools and a real tool it wrote all still work.
    """
    if os.name != "posix":
        raise SystemExit("the docker drill needs docker; run it on the laptop")
    live = live_root or os.path.expanduser("~/growing-cousin/live")
    keys = keys_dir or os.path.expanduser("~/keys")
    home = os.path.expanduser("~")
    mind = os.path.join(root, "body", "mind")
    own = os.path.join(mind, "tools", "own")
    os.makedirs(own, exist_ok=True)
    os.makedirs(os.path.join(mind, "data"), exist_ok=True)

    # Our hands, installed the same way the live body installs them.
    import run as runmod

    class _Shell(object):
        pass
    shell = _Shell()
    shell.root = os.path.join(root, "body")
    bindir = runmod.install_hands(shell)

    # THE CREATURE'S REAL TOOLS, copied read-only out of the live mind. A body
    # proven against tools a test wrote proves nothing about the 46 it will
    # actually have to run.
    live_own = os.path.join(live, "body", "mind", "tools", "own")
    copied = []
    if os.path.isdir(live_own):
        for n in sorted(os.listdir(live_own)):
            src = os.path.join(live_own, n)
            if os.path.isfile(src) and not n.endswith(".bak"):
                shutil.copy2(src, os.path.join(own, n))
                copied.append(n)

    ev = {"image": IMAGE, "container": CONTAINER, "tools_copied": len(copied)}
    b = _docker("build", "-t", IMAGE, "-f",
                os.path.join(HERE, "deploy", "Dockerfile"),
                os.path.join(HERE, "deploy"))
    ev["image_built"] = (b.returncode == 0)
    if b.returncode != 0:
        ev["build_error"] = (b.stderr or "")[-400:]
        return ev
    _docker("rm", "-f", CONTAINER)
    uid = "%d:%d" % (os.getuid(), os.getgid())
    r = _docker("run", "-d", "--init", "--name", CONTAINER, "--user", uid,
                "--memory", "1g", "--pids-limit", "256",
                "-v", "%s:%s" % (mind, bodymod.DockerBody.MIND),
                "-v", "%s:%s:ro" % (bindir, bodymod.DockerBody.HANDS),
                IMAGE, "sleep", "infinity")
    ev["container_started"] = (r.returncode == 0)
    if r.returncode != 0:
        ev["run_error"] = (r.stderr or "")[-400:]
        return ev

    body = bodymod.DockerBody(CONTAINER, image=IMAGE, mind=mind)
    try:
        ev["body_answers"] = body.responds()

        def yes(cmd):
            out = body.run(cmd, timeout=60)
            return out.code == 0

        def no(cmd):
            out = body.run(cmd, timeout=60)
            return out.code != 0

        # CONTAINMENT -- each one a thing the creature's shell could do today.
        ev["keys_unreadable"] = no("cat %s/*.key" % keys)
        ev["host_home_invisible"] = no("ls %s" % home)
        ev["spine_invisible"] = no("ls %s/growing-spine" % home)
        ev["engine_repo_invisible"] = no("ls %s/run.py" % HERE)
        # CAPABILITY -- each one a thing 46 tools need.
        ev["mind_writable"] = yes("touch .drill-canary && rm -f .drill-canary")
        ev["hands_on_path"] = yes("command -v tool-edit >/dev/null")
        ev["own_tools_on_path"] = (
            yes("command -v %s >/dev/null" % copied[0]) if copied else None)
        ev["python3"] = yes("python3 -c 'import sys; sys.exit(0)'")
        ev["bash"] = yes("bash -c 'exit 0'")
        ev["requests"] = yes("python3 -c 'import requests'")
        ev["mind_is_the_cwd"] = yes("test \"$PWD\" = %s"
                                    % bodymod.DockerBody.MIND)
        # A tool the creature really wrote, chosen because its own run record
        # says it exits 0 when called bare.
        for candidate in ("path", "json-pretty", "plan-list-goals", "archive-list"):
            if candidate in copied:
                out = body.run(candidate, timeout=60)
                ev["real_tool_ran"] = (out.code == 0)
                ev["real_tool"] = candidate
                break
        else:
            ev["real_tool_ran"] = None
        # THE RESPAWN, PROVEN THE ONLY WAY THAT MEANS ANYTHING (PLAN 15.3):
        # by DESTROYING the container and requiring it back with the
        # creature's world intact. The first version called `respawn()` on a
        # running container -- a `docker restart` no-op -- and reported it as
        # evidence, which a verifier called a mock proving a mock.
        body.recreate = lambda: _docker(
            "run", "-d", "--init", "--name", CONTAINER, "--user", uid,
            "--memory", "1g", "--pids-limit", "256",
            "-v", "%s:%s" % (mind, bodymod.DockerBody.MIND),
            "-v", "%s:%s:ro" % (bindir, bodymod.DockerBody.HANDS),
            IMAGE, "sleep", "infinity")
        before_tools = sorted(os.listdir(own))
        _docker("rm", "-f", CONTAINER)
        ev["container_really_gone"] = (
            _docker("inspect", "-f", "{{.State.Running}}",
                    CONTAINER).returncode != 0)
        ev["respawn_works"] = body.respawn()
        ev["tools_survived_respawn"] = (sorted(os.listdir(own)) == before_tools
                                        and bool(before_tools))
        ev["real_tool_ran_after_respawn"] = (
            body.run(ev.get("real_tool") or "true", timeout=60).code == 0
            if ev.get("real_tool") else None)
    finally:
        _docker("rm", "-f", CONTAINER)

    # THE OTHER HALF OF THE ASYMMETRY: the engine still holds what the
    # creature no longer can. Deliberately not a live call -- a preflight
    # would make this hostage to free-tier weather.
    from kernel import backends as _b
    specs = []
    # BESIDE THE LIVE ROOT, not beside this file. The ladder specs are
    # gitignored by design -- they name a `key_file` outside the repo -- so a
    # scratch clone has none, and looking next to `HERE` reported "0
    # credentials checked, engine holds none": an alarming-looking figure
    # produced entirely by where the drill went looking.
    for base in (os.path.dirname(os.path.abspath(live)), HERE):
        for name in ("rungs.local.json", "rungs.cousin.local.json"):
            spec = _b.load_spec(os.path.join(base, name)) or []
            specs.extend(r.get("key_file") for r in spec if r.get("key_file"))
        if specs:
            break
    specs = sorted(set(specs))
    ok = True
    for kf in specs:
        try:
            _b.read_key(kf)
        except Exception:
            ok = False
    ev["credentials_checked"] = len(specs)
    ev["engine_holds_credentials"] = bool(specs) and ok
    return ev


IN_PROCESS = {"tool-gone": drill_tool_gone, "torn": drill_torn,
              "silence": drill_silence, "fabricate": drill_fabricate,
              "body": drill_body}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("drill",
                    choices=sorted(IN_PROCESS) + ["giveup", "docker", "all"])
    ap.add_argument("--scratch", required=True,
                    help="a directory the drill may destroy; never a live root")
    ap.add_argument("--emit-fixtures", action="store_true")
    ap.add_argument("--live-root", default=None,
                    help="the root to prove UNTOUCHED (default ~/growing-cousin/live)")
    args = ap.parse_args(argv)

    names = (sorted(IN_PROCESS) + ["giveup", "docker"]
             if args.drill == "all" else [args.drill])
    rc = 0
    # ASK BEFORE DESTROYING. Every path is cleared first, as a set, and only
    # after every one of them has been allowed -- because the first version
    # cleared each target and *then* checked it, so running against a live
    # root printed `REFUSED` having already rmtree'd a subtree of it,
    # including a file under `tools/own`. A guard that runs after the
    # destruction is a comment.
    bases = [os.path.join(args.scratch, n) for n in names]
    for base in bases:
        try:
            scratch_root(base)
        except RefusedLiveRoot as e:
            sys.stderr.write("REFUSED, nothing touched: %s\n" % e)
            return 3
    # THE BASELINE COMES FIRST. It used to be taken after the loop below,
    # so the harness's own first destructive act -- clearing last run's
    # workspaces -- happened OUTSIDE the window that watches the live root.
    # The ancestor guard above makes that safe today, which is exactly the
    # argument that retires a check; the ordering is still backwards, and
    # this file's guard is on its third version precisely because each
    # version was written against the failure the last one had just shown.
    #
    # EVERY drill, not just the one that happened to look. 6.7 says the live
    # root is unchanged before and after; checking it inside a single drill
    # left the other four unwatched.
    live_root = args.live_root or os.path.expanduser("~/growing-cousin/live")
    live_before = live_snapshot(live_root)

    for base in bases:
        if os.path.isdir(base):
            shutil.rmtree(base, ignore_errors=True)

    for name in names:
        base = os.path.join(args.scratch, name)
        try:
            root = scratch_root(base)
        except RefusedLiveRoot as e:
            sys.stderr.write("REFUSED: %s\n" % e)
            return 3
        print("== drill %s -> %s" % (name, root))
        if name == "docker":
            if os.name != "posix":
                print("  skipped: needs docker")
                continue
            ev = drill_docker(root, args.live_root)
            print("  " + json.dumps(ev, sort_keys=True))
            if args.emit_fixtures:
                os.makedirs(FIXTURES, exist_ok=True)
                out = os.path.join(FIXTURES, "0916-drill-docker.evidence.json")
                with io.open(out, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(ev, f, indent=1, sort_keys=True)
                print("  evidence %s" % os.path.basename(out))
            if not all(ev.get(k) for k in ("keys_unreadable", "mind_writable",
                                           "python3", "requests",
                                           "own_tools_on_path")):
                rc = 1
        elif name == "giveup":
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

    if live_before is None:
        sys.stderr.write("could not watch %s, so nothing here proves the live "
                         "run was untouched\n" % live_root)
        rc = rc or 1
    else:
        after = live_snapshot(live_root)
        added = sorted(set(after or ()) - set(live_before))
        gone = sorted(set(live_before) - set(after or ()))
        if added or gone:
            sys.stderr.write("THE LIVE ROOT CHANGED: added=%s removed=%s\n"
                             % (added[:8], gone[:8]))
            rc = 1
        else:
            print("live root unchanged: %d paths watched under %s"
                  % (len(live_before), live_root))
    return rc


if __name__ == "__main__":
    sys.exit(main())
