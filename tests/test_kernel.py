#!/usr/bin/env python3
"""test_kernel.py -- the gate.

Run it to a FILE, never a pipe: a pipe once swallowed `sys.exit(1)` in the
parent and let an ungated commit ship. Check the literal string
`ALL TESTS PASS`, not just the exit code.

    python tests/test_kernel.py > /tmp/k.out 2>&1; echo "GATE=$?"
    tail -1 /tmp/k.out

Every test asserts a CONTRACT, never a mechanism. A mechanism test goes red when
you improve the mechanism, and -- worse -- defends the fault: the parent had a
test asserting a trap phrase AS A REQUIREMENT.
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import (backends, body as bodymod, cousin, forever, think,
                    triggers)
from kernel.cycle import Engine
from kernel.journal import (EXEC_STDOUT_CHARS, Journal, capped, marker_total)

PASS = []
FAIL = []


def check(name, cond, extra=""):
    if cond:
        PASS.append(name)
        print("PASS %s" % name)
    else:
        FAIL.append((name, extra))
        print("FAIL %s %s" % (name, extra))


def tmpdir():
    d = tempfile.mkdtemp(prefix="cousin-test-")
    return d


# --------------------------------------------------------------- journal

def test_journal():
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    j.append("wake", context_chars=10)
    j.append("think", chars=50, model="m")
    j.append("exec_end", exit_code=0, stdout="hi")
    lines = open(j.path, encoding="utf-8").read().strip().split("\n")
    check("journal: one record per line", len(lines) == 3, "got %d" % len(lines))
    check("journal: kinds are countable without reading prose",
          dict(j.kinds()) == {"wake": 1, "think": 1, "exec_end": 1},
          str(dict(j.kinds())))
    check("journal: keyed on epoch ts not a date string",
          all(isinstance(r["ts"], float) for r in j.read()))
    check("journal: filter by kind", len(j.read(kinds=["think"])) == 1)

    # A record containing a newline must not be able to break the format.
    j.append("exec_end", stdout="line one\nline two")
    lines = open(j.path, encoding="utf-8").read().strip().split("\n")
    check("journal: embedded newline cannot split a record", len(lines) == 4,
          "got %d" % len(lines))
    shutil.rmtree(d, ignore_errors=True)


def test_marker_invariant():
    """A marker reports the TOTAL withheld. A later cut may only INCREASE that
    number, never replace it with its own -- the parent showed '+40 chars cut'
    where 3,319 were withheld."""
    body_text = "x" * 5000
    once = capped(body_text, 1200)
    check("caps: marker appears when text is cut", marker_total(once) > 0)
    check("caps: marker reports the real loss",
          marker_total(once) == 5000 - 1200,
          "claims %d,真 %d" % (marker_total(once), 5000 - 1200))

    # Nest a second cut over the first and prove the number does not shrink.
    first_loss = marker_total(once)
    twice = capped(once, 300, already_cut=first_loss)
    check("caps: a later cut never REPLACES the earlier loss with its own",
          marker_total(twice) >= first_loss,
          "outer claims %d, inner had %d" % (marker_total(twice), first_loss))
    check("caps: short text is untouched", capped("abc", 100) == "abc")

    # Sweep the boundary: a cut can land anywhere, so sweep rather than
    # picking cases by hand -- the parent found a real bug this way.
    bad = []
    for n in range(1195, 1210):
        t = capped("y" * n, 1200)
        if len(t) > n and marker_total(t) == 0:
            bad.append(n)
        if n > 1200 and marker_total(t) != n - 1200:
            bad.append(n)
    check("caps: boundary sweep 1195-1209 has no lying marker", not bad, str(bad))


# ------------------------------------------------------------------ body

def test_body():
    b = bodymod.LocalBody()
    check("body: liveness is proved by DOING", b.responds())
    r = b.run("echo hello")
    check("body: a command's stdout comes back", "hello" in r.stdout)
    r = b.run("exit 3")
    check("body: exit code is preserved", r.code == 3, "got %d" % r.code)
    r = b.run("sleep 5", timeout=1)
    check("body: exec has a timeout and it BINDS", r.code == 124, "got %d" % r.code)

    b.kill()
    check("body: a dead body does not claim to respond", not b.responds())
    r = b.run("echo nope")
    check("body: infrastructure failure has EMPTY stdout", r.stdout == "",
          repr(r.stdout))
    check("body: infrastructure failure is marked as setup, not as the command",
          r.setup_failed)
    check("body: respawn brings it back", b.respawn())
    b.destroy()


def test_command_reaches_disk_intact():
    """What the creature writes is what must land on disk.

    2026-09-11, the most expensive fault of the build: `bash -c "<cmd>"` lost
    `$MIND` out of a QUOTED heredoc -- `<< 'EOF'`, which by definition does not
    expand. The creature's tool was written with `os.path.expandvars("")` and a
    hole in its own comment, died on every run, and the cousin reported that
    honestly six times. **The framework damaged the work and then the creature
    was blamed for it** -- the one failure this whole design exists to prevent.

    Fixed by writing the command to a script instead of passing it as argv.
    This test is the only thing standing between that fix and a silent return.
    """
    b = bodymod.LocalBody()
    cmd = "\n".join([
        "cat << 'EOF' > tools/own/probe",
        "#!/usr/bin/env python3",
        "# does: keeps $MIND/data/plan.txt",
        'P = os.path.expandvars("$MIND")',
        "EOF"])
    b.run(cmd)
    got = open(os.path.join(b.mind, "tools", "own", "probe"),
               encoding="utf-8").read()
    check("body: a QUOTED heredoc is not expanded on the way to disk",
          got.count("$MIND") == 2, "found %d of 2" % got.count("$MIND"))
    check("body: the creature's text arrives byte-for-byte",
          'os.path.expandvars("$MIND")' in got, got[:120])

    r = b.run('echo "[$MIND]"')
    check("body: and $MIND actually resolves at runtime",
          r.code == 0 and "[" in r.stdout and r.stdout.strip() != "[]",
          repr(r.stdout)[:80])

    # Special characters the creature will certainly use one day.
    tricky = "\n".join([
        "cat << 'EOF' > tools/own/chars",
        "$HOME `date` \"q\" 'a' $(id)",
        "EOF"])
    b.run(tricky)
    got2 = open(os.path.join(b.mind, "tools", "own", "chars"),
                encoding="utf-8").read()
    check("body: backticks and $(...) survive a quoted heredoc too",
          "`date`" in got2 and "$(id)" in got2, repr(got2)[:110])
    b.destroy()


def test_observer_describes_every_kind_it_can_see():
    """The GUI's real logic is turning structured fields back into a sentence.

    Our journal stores FIELDS, not prose -- that is what makes the state
    derivable (CLAUDE.md 6.1) and what makes a Counter over kinds meaningful.
    The cost is that something must render them, and a renderer that silently
    drops a kind is a blind spot in the only window onto a running system.
    """
    import observer

    samples = {
        "wake": {"context_chars": 900},
        "think": {"model": "gemma-4-31b-it", "chars": 3097, "finish": "stop"},
        "exec_start": {"cmd": "ls tools/own"},
        "exec_end": {"exit_code": 0, "stdout": "a\nb", "stderr": ""},
        "exec_skip": {"reason": "no_command", "lost": False},
        "trigger_fired": {"type": "TOOL_WRITE", "tools": ["fetcher"]},
        "cousin_probe": {"tool": "fetcher", "exit_code": 1, "stderr": "boom"},
        "cousin_verdict": {"verdict": "RETURNED", "model": "gemma-4-31b-it",
                           "to_creature": "it could not find the file"},
        "cousin_want": {"text": "a date filter"},
        "cousin_noticed": {"text": "the disk is nearly full"},
        "context_written": {"wants": 3},
        "tools_changed": {"added": ["grep_tool"], "removed": []},
        "rung_error": {"rung": "gemini", "reason": "quota (429)"},
        "rung_fell_through": {"served_by": "local", "past": "gemini(next)"},
        "loop_start": {"pause": 30, "max_cycles": None},
        "loop_end": {"cycles": 12, "reason": "asked to stop", "seconds": 900.0},
        "error": {"where": "cycle", "detail": "RuntimeError: x"},
    }
    bad = []
    for kind, fields in samples.items():
        e = dict(fields); e["kind"] = kind; e["ts"] = time.time()
        try:
            got = observer.describe(e)
        except Exception as ex:
            bad.append("%s raised %s" % (kind, ex))
            continue
        if not got or not got.strip():
            bad.append("%s rendered empty" % kind)
    check("observer: every journal kind renders to something readable",
          not bad, str(bad))

    # Every kind the KERNEL can write must have a colour, or the one event that
    # matters is the one that looks like everything else.
    written = set(samples) | {"body_respawn", "body_unresponsive",
                              "cousin_unusable"}
    missing = sorted(k for k in written if k not in observer.KIND_COLORS)
    check("observer: every kind the kernel writes has its own colour",
          not missing, str(missing))

    # An UNKNOWN kind must still be shown. The parent's scar is a default
    # branch that hid what it could not name.
    got = observer.describe({"kind": "something_new", "ts": 0, "detail": "hi"})
    check("observer: an unrecognised kind is shown, never swallowed",
          "hi" in got, repr(got))

    # HTML escaping: a creature writes its own text, so it reaches this window
    # as untrusted content.
    html = observer.line_html({"kind": "exec_start", "ts": 0,
                               "cmd": "echo '<script>x</script>'"})
    check("observer: creature text cannot inject markup into the window",
          "<script>" not in html and "&lt;script&gt;" in html, html[:160])


def test_observer_shell_assembles():
    """The renderers being right does not prove the window builds.

    Run headless via QT_QPA_PLATFORM=offscreen. If PyQt6 is absent this SKIPS
    and says so -- a skip printed as a pass is how a suite starts lying, and
    this repo already has a scar about checkers that cannot distinguish what
    they measure.
    """
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("SKIP observer shell: PyQt6 not installed "
              "(engine does not need it; the observer is only a window)")
        return

    import observer

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    j.append("wake", context_chars=10)
    j.append("cousin_verdict", verdict="RETURNED", model="m",
             to_creature="it needed a URL")
    os.makedirs(os.path.join(d, "body", "mind", "tools", "own"))
    with open(os.path.join(d, "context.md"), "w", encoding="utf-8") as f:
        f.write("1. a date filter\n")

    rc = observer.main(d, selftest=True)
    check("observer: the window assembles and ticks against real files",
          rc == 0, "rc=%s" % rc)


def test_observer_vitals_are_derived():
    import observer

    rows = [
        {"kind": "wake", "ts": 100},
        {"kind": "think", "ts": 101, "model": "gemma-4-31b-it"},
        {"kind": "cousin_verdict", "ts": 102, "verdict": "ACCEPTED"},
        {"kind": "wake", "ts": 200},
        {"kind": "cousin_verdict", "ts": 201, "verdict": "RETURNED"},
    ]
    v = observer.vitals(rows, ["a", "b"], False, now=260)
    check("observer: cycles are counted from wakes", v["cycles"] == 2, str(v))
    check("observer: verdicts are split accepted/returned",
          "1 accepted / 1 returned" in v["verdicts"], str(v))
    check("observer: it names the rung actually serving",
          v["serving"] == "gemma-4-31b-it", str(v))
    check("observer: the library size is shown", v["tools"] == 2, str(v))
    check("observer: a pending stop is visible BEFORE the run ends",
          observer.vitals(rows, [], True, now=260)["stopping"] is True)
    check("observer: an idle run shows its age, not a frozen clock",
          v["last_event"] == "59s", v["last_event"])

    empty = observer.vitals([], [], False, now=1)
    check("observer: an empty journal reports zero, not a crash",
          empty["cycles"] == 0 and empty["serving"] == "?", str(empty))


def test_forever_stops_when_asked():
    """A loop that can only be stopped with `kill` is not deployable.

    Killing mid-cycle throws away the cycle in flight, and on a box shared with
    the spine it is the blunt instrument that hits the wrong process.
    """
    d = tmpdir()
    stop = os.path.join(d, "STOP")
    j = Journal(os.path.join(d, "journal.jsonl"))

    seen = {"n": 0}
    present = {"stop": False}

    def one():
        seen["n"] += 1
        if seen["n"] == 3:
            present["stop"] = True     # someone touches the file mid-run

    sup = forever.Supervisor(one, stop, journal=j, pause=0,
                             sleep=lambda _s: None,
                             exists=lambda p: present["stop"])
    ran, reason = sup.loop(max_cycles=50)
    check("forever: the stop file ends the loop", ran == 3, "ran %d" % ran)
    check("forever: and it finishes the cycle it is in, never mid-cycle",
          reason == "asked to stop", reason)
    check("forever: the loop's start and end are journalled",
          len(j.read(kinds=["loop_start"])) == 1
          and len(j.read(kinds=["loop_end"])) == 1)

    # A stop request must survive a restart, or systemd quietly undoes it.
    sup2 = forever.Supervisor(one, stop, journal=j, pause=0,
                              sleep=lambda _s: None, exists=lambda p: True)
    refused = False
    try:
        sup2.loop(max_cycles=1)
    except forever.StopRequested:
        refused = True
    check("forever: a loop refuses to start while a stop request stands",
          refused, "it started anyway")
    shutil.rmtree(d, ignore_errors=True)


def test_forever_does_not_spin_on_failure():
    """A crash loop here is billed to the SPINE -- it shares these accounts.

    So failures back off geometrically and a run of them ends the loop, rather
    than hammering a rate limit forever with nobody watching.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    slept = []

    def always_fails():
        raise RuntimeError("upstream is down")

    sup = forever.Supervisor(always_fails, os.path.join(d, "STOP"), journal=j,
                             pause=10, max_consecutive_failures=4,
                             sleep=slept.append, exists=lambda p: False)
    ran, reason = sup.loop(max_cycles=100)
    check("forever: a persistent fault ends the loop instead of spinning",
          "consecutive failures" in reason, reason)
    check("forever: it gives up quickly, not after a hundred attempts",
          ran <= 4, "ran %d" % ran)
    check("forever: each failure is journalled with its cause",
          len(j.read(kinds=["loop_error"])) >= 3)
    check("forever: the wait GROWS between failures, it does not stay flat",
          len(slept) >= 2 and slept[-1] > slept[0], str(slept))
    check("forever: and the wait is capped, not doubled to infinity",
          all(x <= forever.BACKOFF_CAP_SECS for x in slept), str(slept))

    # A cycle that fails once and then works must not poison the count.
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("one bad call")

    sup2 = forever.Supervisor(flaky, os.path.join(d, "STOP"), journal=j,
                              pause=0, max_consecutive_failures=3,
                              sleep=lambda _s: None, exists=lambda p: False)
    ran2, reason2 = sup2.loop(max_cycles=6)
    check("forever: a single failure does not end the loop",
          "consecutive" not in reason2, reason2)
    check("forever: recovery resets the failure count",
          state["n"] >= 5, "only %d attempts" % state["n"])
    shutil.rmtree(d, ignore_errors=True)


def test_forever_paces_its_cycles():
    """The free tier is rate-limited and the ladder answers a 429 by stepping
    DOWN, not by waiting. Without a pause a fast local fallback would drive the
    remote rungs straight back into their limits."""
    d = tmpdir()
    slept = []
    sup = forever.Supervisor(lambda: None, os.path.join(d, "STOP"),
                             pause=30, sleep=slept.append,
                             exists=lambda p: False)
    ran, reason = sup.loop(max_cycles=3)
    check("forever: it waits between cycles", slept and slept[0] == 30, str(slept))
    check("forever: it does not wait after the last cycle",
          len(slept) == ran - 1, "ran %d, slept %d" % (ran, len(slept)))
    check("forever: a bounded run reports why it ended",
          reason == "reached 3 cycles", reason)
    shutil.rmtree(d, ignore_errors=True)


def test_a_relative_root_still_runs_the_creatures_tools():
    """A tool the creature wrote must be runnable BY NAME, however the run was
    started.

    2026-09-12, found by a live run and not by any test: started with
    `--root live`, the body put RELATIVE entries on PATH. Commands run with
    cwd=mind, so those entries resolved against the mind directory and pointed
    nowhere -- every tool became `command not found` while the body still
    reported healthy and every other assertion stayed green.

    The cousin then filed 13 consecutive honest RETURNED verdicts saying the
    command was not found, and the creature did the rational thing: it rebuilt
    the same tool three ways (fetcher.py, fetcher, fetcher_wrapper.sh). Read
    from the outside that looks exactly like a creature producing twins. It was
    the framework breaking the work and the creature being billed for it.

    The duplicate-stem twins were a SYMPTOM. The lesson generalises past this
    bug: before believing a behavioural finding about either agent, check that
    the harness was not producing it.
    """
    import run as runmod

    d = tmpdir()
    cwd = os.getcwd()
    try:
        os.chdir(d)
        # Deliberately relative -- this is the shape that broke.
        b = runmod.PathBody(os.path.join("nest", "body"))
        b.bin = runmod.install_hands(b)

        check("body: a relative root is normalised to an absolute one",
              os.path.isabs(b.root) and os.path.isabs(b.mind),
              "root=%r mind=%r" % (b.root, b.mind))

        b.run("\n".join([
            "cat << 'SH' > tools/own/greeter",
            "#!/bin/sh",
            "# does: says hello",
            "echo hello-from-tool",
            "SH",
            "chmod +x tools/own/greeter"]))

        r = b.run("greeter")
        check("body: the creature's own tool is found BY NAME, not 127",
              r.code != 127, "exit %d, stderr %r" % (r.code, r.stderr[:120]))
        check("body: and it actually produces its output",
              "hello-from-tool" in r.stdout, repr(r.stdout[:120]))

        # The hands are the same promise: the brief tells the creature they are
        # on PATH, and a prompt that promises what the body does not provide is
        # a contract violation the creature pays for.
        r2 = b.run("remember probe-key probe-value")
        check("body: the hands are on PATH from a relative root too",
              r2.code != 127, "exit %d, stderr %r" % (r2.code, r2.stderr[:120]))
        b.destroy()
    finally:
        os.chdir(cwd)
        shutil.rmtree(d, ignore_errors=True)


def test_a_tool_name_is_never_shell_source():
    """The creature names its own files, so a tool name is untrusted input.

    2026-09-12, first run on the real rung: a file briefly named "`." appeared
    in tools/own, the probe interpolated it raw, and bash died with "unexpected
    EOF while looking for matching `". The cousin then reported a syntax error
    the creature's tool never had -- the framework inventing a fault and the
    creature being billed for it, for the third time in this shape.

    The sharper edge is that an unquoted name does not merely break, it RUNS.
    """
    b = bodymod.LocalBody()
    own = os.path.join(b.mind, "tools", "own")
    canary = os.path.join(b.mind, "PWNED")

    # A name that DOES execute when it reaches the shell unquoted. The canary is
    # RELATIVE because commands run with cwd=mind -- an absolute Windows path
    # here made `touch` fail for its own reasons, so the assertion passed
    # whether or not the quoting existed. A checker that cannot distinguish the
    # thing it measures reports a clean-looking wrong number; this test was one
    # until it was checked against the unfixed code.
    hostile = "$(touch PWNED)"
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    e = Engine(j, b, "brief", None, None, os.path.join(d, "context.md"))

    e.evidence(hostile, [])
    check("probe: a tool name that looks like a command does NOT execute",
          not os.path.exists(canary),
          "a filename ran as shell and created %s" % canary)

    # And a name with unbalanced shell syntax must not crash the probe with a
    # syntax error the creature never caused.
    claim, header, transcript, library = e.evidence("`.", [])
    check("probe: an unbalanced name does not produce a shell syntax error",
          "unexpected EOF" not in transcript, transcript[:160])

    # An ordinary name must pass through the quoting UNCHANGED, or every probe
    # starts invoking something subtly different from what the creature built.
    # (That the name then resolves on PATH is asserted by the relative-root
    # test; here the contract is that quoting alters nothing it should not.)
    import shlex
    plain = [shlex.quote(n) == n for n in
             ("fetcher", "grep_tool", "plan.py", "read-file", "t_1")]
    check("probe: quoting leaves an ordinary tool name byte-identical",
          all(plain), str(plain))

    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_backup_is_not_a_tool():
    """The library is what the creature BUILT, not what is in the directory.

    2026-09-12, from the first run on the real rung: `tool-edit` -- one of OUR
    hands -- keeps a `.bak` beside every tool it edits. The kernel counted it,
    fired TOOL_WRITE for `plan.bak`, spent a cousin visit judging a backup file
    and handed the creature a refusal about it. The manager is ~13% of all
    calls and that budget is the whole economic argument for this design;
    spending it on our own droppings also bills the creature for them.
    """
    d = tmpdir()
    own = os.path.join(d, "tools", "own")
    os.makedirs(own)
    for name in ("plan", "plan.bak", "grep_tool", "grep_tool~",
                 ".hidden", "notes.tmp", "patch.orig"):
        with open(os.path.join(own, name), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho x\n")

    got = triggers.list_tools(own)
    check("library: a .bak is not a tool", "plan.bak" not in got, str(got))
    check("library: nor an editor leftover or a dotfile",
          not any(n in got for n in ("grep_tool~", ".hidden", "notes.tmp",
                                     "patch.orig")), str(got))
    check("library: the real tools are all still there",
          got == ["grep_tool", "plan"], str(got))

    # And the trigger must not fire for one, or the cousin is summoned to judge
    # a backup -- the exact waste this was found doing.
    fired = triggers.detect([("tool-edit plan", 0)], ["plan"],
                            triggers.list_tools(own), 0, 0)
    new_named = [t for t, f in fired if f.get("tools")]
    check("library: a backup appearing does not summon the cousin as a new tool",
          not any("plan.bak" in (f.get("tools") or []) for _, f in fired),
          str(fired))
    shutil.rmtree(d, ignore_errors=True)


def test_setup_classifier():
    """ONE classifier, shared by producer and checker. The parent's rule: a
    producer and a checker that share a literal will drift."""
    check("body: OCI breakage is recognised",
          bodymod.exec_setup_failure("", "OCI runtime exec failed: procReady not received", 128))
    check("body: setns breakage is recognised",
          bodymod.exec_setup_failure("error executing setns", "", 128))
    check("body: an ordinary failure is NOT infrastructure",
          not bodymod.exec_setup_failure("", "python: command not found", 127))
    check("body: success is not infrastructure failure",
          not bodymod.exec_setup_failure("all good", "", 0))


# ----------------------------------------------------------------- think

def test_parse_blocks():
    check("think: one bash block is found",
          think.parse_blocks("talk\n```bash\nls\n```\n") == ["ls"])
    check("think: several blocks keep their order",
          think.parse_blocks("```bash\na\n```\ntext\n```bash\nb\n```") == ["a", "b"])
    check("think: an empty block is not a command",
          think.parse_blocks("```bash\n\n```") == [])
    check("think: prose alone yields nothing", think.parse_blocks("no code") == [])


def test_no_block_classifier():
    """Five different reasons, five different fixes. Collapsing them is how a
    budget problem looked like a quality problem for months."""
    r, _ = think.classify_no_blocks("I will not run anything.", "stop", 40)
    check("think: a complete reply with no command is named as such",
          r == "no_command", r)
    r, _ = think.classify_no_blocks("here is the plan ```bash\nls", "stop", 40)
    check("think: an unclosed fence means commands were LOST",
          r == "unclosed_fence", r)
    r, _ = think.classify_no_blocks("thinking about it", "length", 900)
    check("think: hitting the ceiling means commands were LOST",
          r == "truncated", r)
    r, d = think.classify_no_blocks("", "length", 900)
    check("think: an EMPTY reply that spent its budget is its own reason",
          r == "budget_spent", r)
    check("think: budget_spent says how much was spent", "900" in d, d)
    r, _ = think.classify_no_blocks("", "stop", 0)
    check("think: an empty reply that spent nothing is a different reason",
          r == "empty_reply", r)
    check("think: lost and absent are not the same thing",
          think.commands_were_lost("truncated")
          and think.commands_were_lost("budget_spent")
          and not think.commands_were_lost("no_command"))


# -------------------------------------------------------------- triggers

def test_triggers():
    done = [("remember current-phase done", 0)]
    fired = triggers.detect(done, [], [], 0, 0)
    check("trigger: a done-mark fires DONE_CLAIM",
          [t for t, _ in fired] == ["DONE_CLAIM"], str(fired))

    fired = triggers.detect([("echo hi", 0)], ["a"], ["a", "b"], 0, 0)
    check("trigger: a new tool file fires TOOL_WRITE",
          ("TOOL_WRITE", {"tools": ["b"]}) in fired, str(fired))

    fired = triggers.detect([("cat tools/own/a", 0)], ["a"], ["a"], 0, 0)
    check("trigger: READING a tool is not writing one",
          not fired, str(fired))

    fired = triggers.detect([("tool-edit a", 0)], ["a"], ["a"], 0, 0)
    check("trigger: an edit through the proper door still fires",
          [t for t, _ in fired] == ["TOOL_WRITE"], str(fired))

    fired = triggers.detect([("echo x", 0)], ["a"], ["a"], 0, triggers.STALL_CYCLES)
    check("trigger: a stall fires when nothing changes",
          [t for t, _ in fired] == ["STALL"], str(fired))

    fired = triggers.detect([("echo x", 0)], ["a"], ["a"],
                            triggers.HEARTBEAT_CYCLES, 0)
    check("trigger: a heartbeat fires when the cousin has not visited",
          [t for t, _ in fired] == ["HEARTBEAT"], str(fired))

    fired = triggers.detect(done, ["a"], ["a", "b"], 99, 99)
    check("trigger: a done-claim outranks everything else",
          fired[0][0] == "DONE_CLAIM", str(fired))


# --------------------------------------------------------------- cousin

GOOD = """thinking out loud, this might be ACCEPTED
<<<COUSIN
verdict: RETURNED
COUSIN
actually, my final answer:
<<<COUSIN
verdict: ACCEPTED
tried: ran the tool
outcome: three records
to_creature: |
  I ran it and got three records back.
want: a date filter
noticed: two records contradict each other
COUSIN"""


def test_cousin_parse():
    v = cousin.parse(GOOD)
    check("cousin: the LAST block wins, not the first mentioned verdict",
          v.verdict == cousin.ACCEPTED, v.verdict)
    check("cousin: testimony is captured",
          v.to_creature == "I ran it and got three records back.", repr(v.to_creature))
    check("cousin: want is captured", v.want == "a date filter", v.want)
    check("cousin: noticed is captured",
          v.noticed.startswith("two records"), v.noticed)
    check("cousin: an accept does not block the done-mark", not v.blocks_done)

    v = cousin.parse("no block here at all")
    check("cousin: an unreadable reply is UNKNOWN, never a verdict",
          v.verdict == cousin.UNKNOWN, v.verdict)
    check("cousin: UNKNOWN gates nothing", not v.blocks_done and not v.deliverable)

    v = cousin.parse("<<<COUSIN\nverdict: RETURNED\nto_creature:\nCOUSIN")
    check("cousin: a RETURNED with no message is NOT deliverable",
          not v.deliverable, v.to_creature)
    check("cousin: a mute refusal is flagged", v.error == "mute-refusal", v.error)
    check("cousin: a mute refusal blocks nothing", not v.blocks_done)

    v = cousin.parse("<<<COUSIN\nverdict: RETURNED\nto_creature: it crashed\nCOUSIN")
    check("cousin: a RETURNED with testimony DOES block the done-mark",
          v.blocks_done)


def test_cousin_visit_journals():
    d = tmpdir()
    j = Journal(os.path.join(d, "j.jsonl"))
    ask = backends.scripted([GOOD])
    v = cousin.visit(ask, "BRIEF", "claim", "header", "transcript",
                     journal=j, trigger="DONE_CLAIM")
    kinds = dict(j.kinds())
    check("cousin: a verdict is journalled under its OWN kind",
          kinds.get("cousin_verdict") == 1, str(kinds))
    check("cousin: noticed gets its own kind so it can be counted",
          kinds.get("cousin_noticed") == 1, str(kinds))
    check("cousin: want gets its own kind", kinds.get("cousin_want") == 1, str(kinds))
    rec = j.read(kinds=["cousin_verdict"])[0]
    check("cousin: the verdict record carries structured fields, not prose",
          rec.get("verdict") == "ACCEPTED" and rec.get("trigger") == "DONE_CLAIM",
          str(rec))
    check("cousin: visit returns the parsed verdict", v.verdict == "ACCEPTED")

    def boom(_p):
        raise RuntimeError("provider down")
    v = cousin.visit(boom, "B", "c", "h", "t", journal=j, trigger="HEARTBEAT")
    check("cousin: a provider failure is UNKNOWN, never a refusal",
          v.verdict == cousin.UNKNOWN and not v.blocks_done, v.verdict)
    shutil.rmtree(d, ignore_errors=True)


# ------------------------------------------------------------ engine E2E

def build_engine(creature_replies, cousin_replies, d=None):
    d = d or tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = bodymod.LocalBody(os.path.join(d, "body"))
    e = Engine(j, b, "BRIEF", backends.scripted(creature_replies),
               backends.scripted(cousin_replies),
               os.path.join(d, "context.md"))
    e.write_context("# Your world\n\nBuild something.")
    return e, j, b, d


ACCEPT_REPLY = ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\n"
                "outcome: worked\nto_creature: I used it and it worked.\n"
                "want: a date filter\nCOUSIN")
RETURN_REPLY = ("<<<COUSIN\nverdict: RETURNED\ntried: ran it\n"
                "outcome: crashed\nto_creature: I ran it and it stopped with an "
                "error before printing anything.\nCOUSIN")


def test_cycle_no_command():
    e, j, b, d = build_engine(["I am thinking, no commands yet."], [])
    r = e.run_cycle()
    check("e2e: a cycle with no command is not substantive", not r["substantive"])
    check("e2e: the reason is recorded as no_command", r["reason"] == "no_command", r["reason"])
    check("e2e: exec_skip is journalled with a reason field",
          j.read(kinds=["exec_skip"])[0].get("reason") == "no_command")
    check("e2e: no cousin visit without a trigger",
          dict(j.kinds()).get("cousin_verdict") is None)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_cycle_executes_and_journals():
    e, j, b, d = build_engine(["```bash\necho hello\n```"], [])
    r = e.run_cycle()
    check("e2e: a cycle with a command is substantive", r["substantive"])
    check("e2e: the command ran once", r["executed"] == 1, str(r))
    ee = j.read(kinds=["exec_end"])[0]
    check("e2e: stdout is journalled", "hello" in ee.get("stdout", ""), str(ee))
    check("e2e: exit code is journalled as a FIELD", ee.get("exit_code") == 0)
    ks = dict(j.kinds())
    check("e2e: the cycle's kinds are all distinct and countable",
          {"wake", "think", "exec_start", "exec_end"} <= set(ks), str(ks))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_cycle_done_claim_triggers_cousin():
    creature = ["```bash\necho 'print(1)' > tools/own/newtool\n```\n"
                "```bash\nremember current-phase done\n```"]
    e, j, b, d = build_engine(creature, [RETURN_REPLY])
    r = e.run_cycle()
    check("e2e: a done-claim fires the cousin",
          "DONE_CLAIM" in r["triggers"], str(r["triggers"]))
    check("e2e: the cousin's verdict comes back", r["verdict"] == "RETURNED", str(r))
    check("e2e: a trigger is journalled under its own kind",
          dict(j.kinds()).get("trigger_fired", 0) >= 1)
    check("e2e: a RETURNED verdict is held for the creature",
          bool(e.done_blocked), repr(e.done_blocked))
    ctx = e.serve_context()
    check("e2e: the refusal reaches the NEXT context",
          "could not use it" in ctx and "stopped with an error" in ctx, ctx[:120])
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_refusal_is_delivered_once():
    creature = ["```bash\nremember current-phase done\n```",
                "```bash\necho second\n```"]
    e, j, b, d = build_engine(creature, [RETURN_REPLY, ACCEPT_REPLY])
    e.run_cycle()
    first = e.serve_context()
    e.run_cycle()
    second = e.serve_context()
    check("e2e: a refusal is surfaced once, not every cycle",
          "could not use it" in first and "could not use it" not in second,
          "first=%r second=%r" % (first[:40], second[:40]))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_accept_does_not_block():
    e, j, b, d = build_engine(["```bash\nremember current-phase done\n```"],
                              [ACCEPT_REPLY])
    r = e.run_cycle()
    check("e2e: an ACCEPTED verdict does not hold anything back",
          r["verdict"] == "ACCEPTED" and not e.done_blocked)
    check("e2e: an accepted want is journalled",
          dict(j.kinds()).get("cousin_want") == 1)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_context_is_served_not_assembled():
    """The curated text is the cousin's and is served UNCHANGED. Facts about
    what just happened are the kernel's and are appended.

    2026-09-11: the first version of this test asserted 'byte for byte' against
    a FRESH engine -- no memory, no journal -- so the only case it ever
    exercised was the one where there is nothing to append. It passed for the
    wrong reason, and went on passing after the behaviour changed. A fixture
    that cannot exhibit the fault is not a test.
    """
    e, j, b, d = build_engine(["```bash\necho first\n```", "no commands"], [])
    e.write_context("EXACTLY THIS")
    check("e2e: with nothing to report, only the curated text is served",
          e.serve_context() == "EXACTLY THIS", repr(e.serve_context()))

    e.run_cycle()          # now there IS history
    ctx = e.serve_context()
    check("e2e: the curated text survives verbatim once there is history",
          "EXACTLY THIS" in ctx, ctx[-60:])
    check("e2e: and what just ran is served with it",
          "echo first" in ctx, ctx[:200])
    check("e2e: with the result, not just the command",
          "exit 0" in ctx and "first" in ctx, ctx[:200])

    seen = {}

    def spy(c):
        seen["ctx"] = c
        return "nothing", {"done_reason": "stop"}
    e.ask_creature = spy
    e.run_cycle()
    check("e2e: the creature receives exactly what serve_context built",
          seen.get("ctx") and "EXACTLY THIS" in seen["ctx"]
          and "echo first" in seen["ctx"], repr(seen.get("ctx"))[:90])

    # The whole point: two consecutive wakes must not look identical, or a
    # deterministic creature repeats itself forever.
    e.ask_creature = backends.scripted(["```bash\necho second\n```"])
    before = e.serve_context()
    e.run_cycle()
    check("e2e: consecutive wakes differ once something has happened",
          e.serve_context() != before,
          "context was byte-identical across a cycle")
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_memory_reaches_the_context():
    """The prompt promises memory is shown each cycle. A promise the context
    does not keep is a contract violation, not a detail."""
    e, j, b, d = build_engine(["```bash\nmkdir -p state && printf '%s' "
                               "'{\"current-phase\": \"code\"}' > state/memory.json\n```"],
                              [])
    e.write_context("BASE")
    e.run_cycle()
    ctx = e.serve_context()
    check("e2e: what was remembered is shown back",
          "current-phase" in ctx and "code" in ctx, ctx[:160])
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_want_reaches_the_creature():
    """DIRECTION. The cousin asking for the next capability is what replaces the
    three parent guards that AIM rather than refuse.

    2026-09-12: wants were journalled and went nowhere -- `write_context` was
    called once at seed and never again, so "the manager writes the context" was
    aspirational and the creature was only ever told what it got wrong. No test
    asserted it, so a green gate sat over a dead channel.
    """
    def acc(w):
        return "\n".join([
            "<<<COUSIN", "verdict: ACCEPTED", "tried: ran it",
            "outcome: fine", "to_creature: I used it and it worked.",
            "want: %s" % w, "COUSIN"])
    done = "\n".join(["```bash", "remember current-phase done", "```"])
    e, j, b, d = build_engine([done] * 4,
                              [acc("a date filter"), acc("a tag filter"),
                               acc("a size limit"), acc("a date filter")])
    e.creature_brief = "WHO YOU ARE"

    e.run_cycle()
    check("want: an accepted want reaches the served context",
          "a date filter" in e.serve_context(), e.serve_context()[:120])
    check("want: and is journalled under its own kind",
          dict(j.kinds()).get("context_written") == 1)

    e.run_cycle(); e.run_cycle(); e.run_cycle()
    w = e.wants()
    check("want: the newest is first", w and w[0] == "a date filter", str(w))
    check("want: the managed context is BOUNDED, not an append-only log",
          len(w) <= 3, "%d kept" % len(w))
    check("want: a repeated want is not duplicated", len(set(w)) == len(w), str(w))
    check("want: the creature's identity is still served alongside it",
          "WHO YOU ARE" in e.serve_context())
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_strip_reasoning():
    """gemma-4-31b-it -- the rung carrying 87-93% of the parent's traffic --
    puts <thought> inside `content`. Unstripped it reaches parse_bash_blocks
    and the verdict parser alike."""
    t = backends.strip_reasoning
    check("reasoning: a closed block is removed",
          t("<thought>hmm</thought>ANSWER").strip() == "ANSWER",
          repr(t("<thought>hmm</thought>ANSWER")))
    check("reasoning: <think> and <reasoning> too",
          t("<think>a</think>X<reasoning>b</reasoning>Y").strip() == "XY",
          repr(t("<think>a</think>X<reasoning>b</reasoning>Y")))
    check("reasoning: an UNCLOSED block swallows the rest -- it is not an answer",
          t("<thought>never closed and on and on").strip() == "",
          repr(t("<thought>never closed and on and on")))
    check("reasoning: text with no block is byte-for-byte untouched",
          t("plain reply") == "plain reply")
    check("reasoning: empty in, empty out", t("") == "")

    # The one that matters. A creature writing a tool that HANDLES these tags
    # must get its bytes to disk intact -- the framework damaging the work and
    # the creature being blamed is the failure this project exists to prevent.
    fenced = """Here it is.
```bash
cat << 'SH' > tools/own/detag
#!/usr/bin/env python3
# does: strips <thought> blocks from a reply
MARK = '<thought>'
SH
```
Done."""
    got = t(fenced)
    check("reasoning: a fenced block is NEVER stripped, even naming the tags",
          got == fenced, repr(got[:150]))

    mixed = """<thought>plan</thought>
```bash
echo '<think>'
```
tail"""
    got2 = t(mixed)
    check("reasoning: strips prose but spares the fence in the same reply",
          "plan" not in got2 and "<think>" in got2 and "tail" in got2,
          repr(got2))


def test_classify_error_never_raises():
    """The parent's classify_error had a default branch that RAISED, so one
    unrecognised error took down the ladder instead of stepping past a rung."""
    class H(Exception):
        def __init__(self, code): self.code = code

    got = {}
    for code in (401, 403, 429, 402, 500, 503, 404, 418):
        got[code] = backends.classify_error(H(code))[0]
    check("ladder: a rejected credential walls that rung",
          got[401] == backends.WALL and got[403] == backends.WALL, str(got))
    check("ladder: quota steps to the next rung, it does not wall",
          got[429] == backends.NEXT and got[402] == backends.NEXT, str(got))
    check("ladder: a transient upstream is retried",
          got[500] == backends.RETRY and got[503] == backends.RETRY, str(got))
    check("ladder: an UNRECOGNISED error steps to the next rung, never raises",
          got[418] == backends.NEXT and got[404] == backends.NEXT, str(got))

    disp, reason = backends.classify_error(ValueError("something new"))
    check("ladder: an unknown exception type still classifies",
          disp == backends.NEXT, disp)
    check("ladder: and it announces itself WITH ITS TEXT",
          "something new" in reason, reason)


def test_ladder_routes_and_records():
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class H(Exception):
        def __init__(self, code): self.code = code

    calls = []

    def dead(_p):
        calls.append("dead")
        raise H(429)

    def alive(_p):
        calls.append("alive")
        return "hello", {"model": "m2", "done_reason": "stop"}

    ask = backends.ladder([("top", dead), ("second", alive)], journal=j)
    text, meta = ask("x")
    check("ladder: a refusing rung falls through to the next", text == "hello")
    check("ladder: the reply records WHICH rung served it",
          meta.get("rung") == "second", str(meta))
    check("ladder: falling through is journalled, not silent",
          len(j.read(kinds=["rung_fell_through"])) == 1)
    check("ladder: the rung error is journalled with its reason",
          len(j.read(kinds=["rung_error"])) == 1)

    # A walled rung is not retried for the rest of the session.
    def badkey(_p):
        calls.append("badkey")
        raise H(401)

    ask2 = backends.ladder([("bad", badkey), ("second", alive)], journal=j)
    ask2("x"); before = calls.count("badkey")
    ask2("x")
    check("ladder: a walled rung is never tried again this session",
          calls.count("badkey") == before, "tried %d times" % calls.count("badkey"))

    def always(_p):
        raise H(429)

    try:
        backends.ladder([("a", always)])("x")
        exhausted = False
    except backends.LadderExhausted:
        exhausted = True
    check("ladder: every rung refusing raises LadderExhausted, not a fake reply",
          exhausted)

    v = cousin.visit(backends.ladder([("a", always)]), "brief", "c", "h", "t")
    check("ladder: an exhausted ladder reaches the cousin as UNKNOWN, never a verdict",
          v.verdict == cousin.UNKNOWN and not v.deliverable, v.verdict)
    shutil.rmtree(d, ignore_errors=True)


def test_resume_is_derived_from_the_journal():
    """A killed run must not restart as if nothing happened.

    Derived, never saved: a savegame written beside the journal is a second
    account of the same facts, and the two drift precisely when a run dies
    between the cycle and the save -- which is when a savegame is meant to
    help. Same reasoning as the manager's derived state (CLAUDE.md 6.1).
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))

    check("resume: an empty journal restores nothing and claims nothing",
          e.resume() == 0 and e.cycles_since_visit == 0
          and e.cycles_since_change == 0 and e.done_blocked is None)

    # Three quiet cycles: both counters must reach 3, not 2. Counting at wakes
    # instead of at cycle CLOSE loses the last one -- the cycle a resume most
    # needs, because it is the one nearest the crash.
    for _ in range(3):
        j.append("wake", context_chars=1)
    check("resume: three quiet cycles count as three, not two",
          e.resume() == 3 and e.cycles_since_visit == 3
          and e.cycles_since_change == 3,
          "visit=%d change=%d" % (e.cycles_since_visit, e.cycles_since_change))

    # A visit ANSWERS what summoned it, so it clears both counters.
    j.append("wake", context_chars=1)
    j.append("cousin_verdict", verdict="ACCEPTED", to_creature="fine")
    e.resume()
    check("resume: a visit clears both counters, so a STALL cannot re-fire",
          e.cycles_since_visit == 0 and e.cycles_since_change == 0,
          "visit=%d change=%d" % (e.cycles_since_visit, e.cycles_since_change))

    # A tool change clears only the stall counter.
    j.append("wake", context_chars=1)
    j.append("tools_changed", added=["t"], removed=[])
    e.resume()
    check("resume: a tool change clears the stall counter but not the visit one",
          e.cycles_since_change == 0 and e.cycles_since_visit == 1,
          "visit=%d change=%d" % (e.cycles_since_visit, e.cycles_since_change))

    # A DELETION is why tools_changed is journalled at all: it moves the
    # counter and fires no trigger, so it cannot be inferred from TOOL_WRITE.
    j.append("wake", context_chars=1)
    j.append("wake", context_chars=1)
    j.append("tools_changed", added=[], removed=["t"])
    e.resume()
    check("resume: a DELETION counts as a change, though no trigger fires",
          e.cycles_since_change == 0, "change=%d" % e.cycles_since_change)

    # An unread refusal must survive the crash, or the creature is never told.
    j.append("wake", context_chars=1)
    j.append("cousin_verdict", verdict="RETURNED", to_creature="it needs a URL")
    e.resume()
    check("resume: a refusal the creature has not read yet survives a restart",
          e.done_blocked == "it needs a URL", repr(e.done_blocked))
    check("resume: and it is served in the very next context",
          "it needs a URL" in e.serve_context())

    # The next wake consumes it. Otherwise the creature is told twice, which is
    # the nag the surface-on-change rule exists to prevent.
    j.append("wake", context_chars=1)
    e.resume()
    check("resume: once a cycle has begun, the refusal is not re-delivered",
          e.done_blocked is None, repr(e.done_blocked))

    # A mute refusal was never deliverable, so it must not come back as one.
    j.append("wake", context_chars=1)
    j.append("cousin_verdict", verdict="RETURNED", to_creature="")
    e.resume()
    check("resume: a refusal with no reason is not resurrected either",
          e.done_blocked is None, repr(e.done_blocked))
    shutil.rmtree(d, ignore_errors=True)


def test_resume_matches_a_live_run():
    """The derivation must agree with the engine that produced the journal.

    Asserting the replay against ITSELF would pass while both were wrong. The
    only honest check is: run real cycles, then rebuild from the log and
    compare against the engine's own in-memory counters.
    """
    writes = """```bash
cat << 'SH' > tools/own/thing
#!/bin/sh
echo hi
SH
chmod +x tools/own/thing
```"""
    quiet = "Nothing to do this cycle."
    e, j, b, d = build_engine([writes, quiet, quiet], [ACCEPT_REPLY])
    for _ in range(3):
        e.run_cycle()

    live = (e.cycles_since_visit, e.cycles_since_change,
            (e.done_blocked or "").strip())

    fresh = Engine(j, b, "brief", None, None, e.context_path)
    fresh.resume()
    rebuilt = (fresh.cycles_since_visit, fresh.cycles_since_change,
               (fresh.done_blocked or "").strip())

    check("resume: the rebuilt state matches the engine that wrote the journal",
          live == rebuilt, "live=%s rebuilt=%s" % (live, rebuilt))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_cousin_sees_the_library():
    """The cousin's third test is "is this new, or the fifth variant?" -- and
    for the whole life of the kernel it was asked that while being shown ONE
    tool and never the library.

    2026-09-12, measured over 40 live cycles: four greps and two readers,
    including two duplicate-stem twins, every one accepted. A comparison is not
    a judgement you can prompt your way to when neither side is on the page.
    """
    writes = """```bash
cat << 'SH' > tools/own/newthing
#!/bin/sh
echo hi
SH
chmod +x tools/own/newthing
```"""
    e, j, b, d = build_engine([writes], [ACCEPT_REPLY])
    own = os.path.join(b.mind, "tools", "own")
    with open(os.path.join(own, "older"), "w", encoding="utf-8") as f:
        f.write("""#!/bin/sh
# does: searches a file for a term
echo old
""")

    seen = {}

    def spy(prompt):
        seen["p"] = prompt
        return ACCEPT_REPLY, {"model": "spy", "done_reason": "stop"}
    e.ask_cousin = spy
    e.run_cycle()

    p = seen.get("p", "")
    check("library: the cousin is shown what already existed",
          "older" in p, p[-400:] if p else "(no prompt captured)")
    check("library: with each tool's own stated purpose, not just its name",
          "searches a file for a term" in p, p[-400:] if p else "")
    check("library: the tool under judgement is not listed as its own sibling",
          p.count("newthing") >= 1 and "- newthing" not in p, "listed itself")


def test_cousin_probe_is_recorded():
    """What the cousin actually ran, as fact. Without it nothing can check
    whether its testimony describes an event that happened."""
    writes_a_tool = "\n".join([
        "```bash",
        "cat << 'SH' > tools/own/t",
        "#!/bin/sh",
        "echo hi",
        "SH",
        "chmod +x tools/own/t",
        "```"])
    e, j, b, d = build_engine([writes_a_tool], [ACCEPT_REPLY])
    e.run_cycle()
    probes = j.read(kinds=["cousin_probe"])
    check("probe: the cousin's own attempt is journalled", len(probes) == 1,
          str(dict(j.kinds())))
    if probes:
        check("probe: it records WHICH tool and the real exit code",
              probes[0].get("tool") == "t" and probes[0].get("exit_code") is not None,
              str(probes[0]))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_census_catches_a_fabricated_verdict():
    """The census must fire on testimony that contradicts the record, and must
    NOT fire on testimony that matches it."""
    import census
    honest = {"kind": "cousin_verdict", "verdict": "RETURNED",
              "tried": "ran t", "outcome": "exit 1",
              "to_creature": "I ran t and it exited with an error."}
    probe = {"kind": "cousin_probe", "tool": "t", "exit_code": 1,
             "stdout": "", "stderr": "boom"}
    check("census: honest testimony produces no finding",
          not census.check(probe, honest), str(census.check(probe, honest)))

    lying = dict(honest, outcome="exit 0", to_creature="I ran t, exit 0, fine.")
    f = census.check(probe, lying)
    check("census: a claimed exit code that never happened is HIGH",
          any(s == "HIGH" for s, _ in f), str(f))

    crash = dict(honest, to_creature="I ran t and it crashed with a traceback.")
    f2 = census.check({"kind": "cousin_probe", "tool": "t", "exit_code": 0,
                       "stdout": "all good", "stderr": ""}, crash)
    check("census: describing a crash over a clean exit is HIGH",
          any(s == "HIGH" for s, _ in f2), str(f2))

    f3 = census.check(None, honest)
    check("census: a verdict with NO probe is HIGH, never silently clean",
          any(s == "HIGH" for s, _ in f3), str(f3))

    mute = {"kind": "cousin_verdict", "verdict": "RETURNED", "to_creature": ""}
    check("census: a refusal with no reason is caught",
          any(s == "HIGH" for s, _ in census.check(probe, mute)))


def test_dead_body_does_not_become_creature_output():
    e, j, b, d = build_engine(["```bash\necho hi\n```"], [])
    # Not merely dead -- UNREVIVABLE. A body that only died is recoverable and
    # `ensure_body` is supposed to recover it; the contract under test is what
    # happens when it cannot be brought back at all, which is the case the
    # parent actually hit for three and a half hours.
    b.can_respawn = False
    b.kill()
    r = e.run_cycle()
    check("e2e: a dead body yields no executed work", not r["substantive"], str(r))
    check("e2e: the outage is journalled as a body problem, not a command result",
          dict(j.kinds()).get("body_unresponsive", 0) >= 1, str(dict(j.kinds())))
    check("e2e: nothing was recorded as exec_end",
          dict(j.kinds()).get("exec_end") is None)
    shutil.rmtree(d, ignore_errors=True)


def test_mute_refusal_never_delivered():
    mute = "<<<COUSIN\nverdict: RETURNED\nto_creature:\nCOUSIN"
    e, j, b, d = build_engine(["```bash\nremember current-phase done\n```"], [mute])
    e.run_cycle()
    check("e2e: a refusal with no reason is never handed to the creature",
          not e.done_blocked, repr(e.done_blocked))
    check("e2e: and it does not silently vanish from the record",
          j.read(kinds=["cousin_verdict"])[0].get("error") == "mute-refusal")
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_cousin_unusable_gates_nothing():
    e, j, b, d = build_engine(["```bash\nremember current-phase done\n```"],
                              ["total nonsense, no block"])
    r = e.run_cycle()
    check("e2e: an unreadable cousin reply gates nothing",
          r["verdict"] == "UNKNOWN" and not e.done_blocked, str(r))
    check("e2e: the unusable verdict is recorded so it can be counted",
          dict(j.kinds()).get("cousin_unusable") == 1, str(dict(j.kinds())))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_budget_spent_is_not_silence():
    def spender(_ctx):
        return "", {"done_reason": "length", "completion_tokens": 900}
    e, j, b, d = build_engine([], [])
    e.ask_creature = spender
    r = e.run_cycle()
    check("e2e: an empty reply that spent its budget is not 'proposed nothing'",
          r["reason"] == "budget_spent", r["reason"])
    rec = j.read(kinds=["exec_skip"])[0]
    check("e2e: and it is marked as LOST work, not absent work", rec.get("lost") is True)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_multi_cycle_stability():
    """Ten cycles with no trigger must eventually visit on the heartbeat, and
    must not visit twice for the same quiet stretch."""
    creature = ["```bash\necho tick\n```"] * (triggers.HEARTBEAT_CYCLES + 2)
    e, j, b, d = build_engine(creature, [ACCEPT_REPLY] * 3)
    visits = 0
    for _ in range(triggers.HEARTBEAT_CYCLES + 2):
        r = e.run_cycle()
        if r.get("verdict"):
            visits += 1
    check("e2e: a quiet creature is still visited", visits >= 1, "visits=%d" % visits)
    check("e2e: but not on every quiet cycle", visits <= 3, "visits=%d" % visits)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


# ------------------------------------------------------------- live model

def test_live_model():
    """Optional: the real judge. Skipped, never failed, when Ollama is absent --
    an instrument that cannot run must say UNKNOWN, never FAULTY."""
    model = os.environ.get("COUSIN_MODEL", "gemma4:12b")
    ask = backends.ollama(model, num_predict=700)
    ok, why = backends.preflight(ask, "ollama/%s" % model)
    if not ok:
        print("SKIP live model (%s)" % why)
        return
    brief_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "MANAGER-PROMPT.md")
    brief = open(brief_path, encoding="utf-8").read()
    v = cousin.visit(
        ask, brief,
        "I finished plot_csv. Give it a two-column CSV and it draws a bar chart.",
        "#!/usr/bin/env python3\n# tool: plot_csv\n# call: plot_csv <csv>",
        "$ plot_csv data.csv\nexit 1\n  File \"plot_csv\", line 7\n    set -euo "
        "pipefail\nSyntaxError: invalid syntax")
    check("live: the real model returns a usable verdict",
          v.verdict in (cousin.ACCEPTED, cousin.RETURNED),
          "%s err=%s" % (v.verdict, v.error))
    check("live: a tool that cannot start is RETURNED",
          v.verdict == cousin.RETURNED, v.verdict)
    check("live: the refusal carries testimony",
          bool(v.to_creature.strip()) and v.deliverable, repr(v.to_creature)[:90])


def main():
    t0 = time.time()
    for fn in (test_journal, test_marker_invariant, test_body,
               test_command_reaches_disk_intact,
               test_observer_describes_every_kind_it_can_see,
               test_observer_shell_assembles,
               test_observer_vitals_are_derived,
               test_forever_stops_when_asked,
               test_forever_does_not_spin_on_failure,
               test_forever_paces_its_cycles,
               test_a_relative_root_still_runs_the_creatures_tools,
               test_a_tool_name_is_never_shell_source,
               test_a_backup_is_not_a_tool,
               test_setup_classifier, test_parse_blocks, test_no_block_classifier,
               test_triggers, test_cousin_parse, test_cousin_visit_journals,
               test_cycle_no_command, test_cycle_executes_and_journals,
               test_cycle_done_claim_triggers_cousin, test_refusal_is_delivered_once,
               test_accept_does_not_block, test_context_is_served_not_assembled,
               test_memory_reaches_the_context,
               test_want_reaches_the_creature, test_strip_reasoning,
               test_classify_error_never_raises, test_ladder_routes_and_records,
               test_resume_is_derived_from_the_journal,
               test_resume_matches_a_live_run,
               test_cousin_sees_the_library,
               test_cousin_probe_is_recorded,
               test_census_catches_a_fabricated_verdict,
               test_dead_body_does_not_become_creature_output,
               test_mute_refusal_never_delivered, test_cousin_unusable_gates_nothing,
               test_budget_spent_is_not_silence, test_multi_cycle_stability,
               test_live_model):
        try:
            fn()
        except Exception as e:
            import traceback
            FAIL.append((fn.__name__, "%s: %s" % (type(e).__name__, e)))
            print("FAIL %s raised %s: %s" % (fn.__name__, type(e).__name__, e))
            traceback.print_exc()

    total = len(PASS) + len(FAIL)
    print("\n%d/%d green (%.1f%%) in %.1fs"
          % (len(PASS), total, 100.0 * len(PASS) / max(1, total), time.time() - t0))
    if FAIL:
        print("\nFAILURES:")
        for n, x in FAIL:
            print("  %-58s %s" % (n, x))
        return 1
    print("ALL TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
