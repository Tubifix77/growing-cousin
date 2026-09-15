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
import collections
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel import (backends, body as bodymod, cousin, forever, library,
                    think, triggers)
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


def test_a_marker_says_whose_cut_it_is():
    """Reporting the SIZE of a cut is not enough; it must name the cutter.

    2026-09-12, the sixth and worst instance of the framework damaging the
    creature's work. It ran `cat plan; cat log-read`; the pair produced ~4.5k
    chars, the journal kept 1200, so `plan` appeared to end mid-file and
    `log-read` never appeared at all. It read the marker, concluded *"It's
    clearly truncated. The tool is broken."*, and REWROTE BOTH TOOLS SHORTER --
    plan 99->92 lines, log-read 46->29. It mutilated a working library to fit a
    display limit it had no way to attribute.

    The parent's invariant -- a marker reports the TOTAL withheld -- is true
    and insufficient. A reader who cannot tell OUR cut from the content ending
    concludes the content ended.
    """
    mark = capped("y" * 5000, 1200)
    check("marker: it still reports the true total",
          marker_total(mark) == 3800, marker_total(mark))
    tail = mark[-140:]
    check("marker: it says the LOG withheld this, not the command",
          "log" in tail.lower() and "withheld" in tail.lower(), tail)
    check("marker: and that the output itself was NOT missing anything",
          "not missing" in tail.lower(), tail)

    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))
    j.append("exec_start", cmd="cat tools/own/plan")
    j.append("exec_end", exit_code=0, stdout="z" * 9000, stderr="")
    hist = e.recent_block()
    check("marker: the CONTEXT cap names itself too",
          "withheld by the log" in hist, hist[-220:])
    check("marker: and still says the output itself was not missing anything",
          "not missing from the output" in hist, hist[-220:])
    shutil.rmtree(d, ignore_errors=True)


def test_history_never_cuts_mid_line():
    """A cut through the middle of a token looks like corruption. A cut between
    lines looks like an excerpt, which is what it is.

    2026-09-12: HISTORY_OUTPUT_CHARS was 700, a constant chosen with no
    evidence. The creature's tools measure 706-3157 bytes, so it cut nearly
    every `cat` of a tool mid-file -- `log-read` landed on `print(line.str`,
    six characters short. The creature reported *"the previous log-read had a
    bug: print(line.str. It was truncated"* and rewrote the tool. It was
    reading our display as its own code.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))

    NL = chr(10)
    src = NL.join("line %03d some content here" % i for i in range(400))
    j.append("exec_start", cmd="cat tools/own/thing")
    j.append("exec_end", exit_code=0, stdout=src, stderr="")
    hist = e.recent_block()

    body = [ln for ln in hist.split(NL) if ln.startswith("| line ")]
    # Every line is whole. The LAST one carries the marker appended to it, so
    # strip that before judging -- the point is that no line of CONTENT is cut
    # through the middle, not that a marker never touches one.
    content = [ln.split("…[")[0] for ln in body]
    check("history: a cut output still shows whole lines of content",
          all(ln.endswith("content here") for ln in content),
          [ln for ln in content if not ln.endswith("content here")][:2])
    check("history: and it cut somewhere, so this is not a vacuous pass",
          "withheld by the log" in hist and len(body) < 400,
          "%d lines of 400" % len(body))

    # The real case that caused it: a tool just over the old 700 limit must now
    # arrive whole.
    j2 = Journal(os.path.join(d, "j2.jsonl"))
    e2 = Engine(j2, Stub(), "brief", None, None, os.path.join(d, "c2.md"))
    tool = ("#!/usr/bin/env python3" + NL
            + ("# padding padding padding" + NL) * 25
            + "    for line in log_lines:" + NL
            + "        print(line.strip())" + NL)
    j2.append("exec_start", cmd="cat tools/own/log-read")
    j2.append("exec_end", exit_code=0, stdout=tool, stderr="")
    h2 = e2.recent_block()
    check("history: a tool the size of the real one is shown COMPLETE",
          "print(line.strip())" in h2 and "withheld" not in h2,
          "%d bytes of tool, history %d" % (len(tool), len(h2)))
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
    # Carry the EVIDENCE, not just the boolean. This assertion failed three
    # times in Windows gate runs (2026-09-12) and reported nothing but its own
    # name, so three diagnoses started from zero. An assertion that cannot say
    # what it saw is the top scar in miniature.
    probe = b.run("echo alive", timeout=15)
    check("body: liveness is proved by DOING",
          (not probe.setup_failed) and probe.code == 0 and "alive" in probe.stdout,
          "code=%r setup_failed=%r stdout=%r stderr=%r root=%r"
          % (probe.code, probe.setup_failed, probe.stdout[:80],
             probe.stderr[:160], b.root))
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
        "want_retired": {"count": 2, "because": "answered by a RETURNED with "
                         "no new want", "texts": ["a date filter", "a tag"]},
        "tools_changed": {"added": ["grep_tool"], "removed": []},
        "rung_declined": {"rung": "gemini", "reason": "quota (429)",
                          "expected": True},
        "rung_broken": {"rung": "groq", "reason": "credential rejected",
                        "expected": False},
        "think_deferred": {"where": "think", "detail": "LadderExhausted"},
        "rung_fell_through": {"served_by": "local", "past": "gemini(next)"},
        "loop_start": {"pause": 30, "max_cycles": None},
        "loop_end": {"cycles": 12, "reason": "asked to stop", "seconds": 900.0,
                     "fault": False},
        "error": {"where": "cycle", "detail": "RuntimeError: x"},
        "engine_start": {"engine": "aad203f" * 6, "dirty": False,
                         "python": "3.11.2", "caps": {"exec_stdout": 2400},
                         "rungs": ["gemini", "groq"]},
        "selfcheck": {"body_answers": True, "home_write_blocked": True,
                      "spine_unreadable": True, "hand_on_path": True,
                      "python3_on_path": True, "caps_ordered": True,
                      "unproven": [], "ok": True},
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


def test_vitals_never_aggregates_across_rungs():
    """The instrument that makes a change measurable instead of asserted.

    Tue, 2026-09-13: this framework is not deterministic. A change that looks
    like an improvement on one observation may be noise, may be a regression
    the next hour would show, and may be specific to whichever model answered.
    Five context changes were made in four hours, each declared good from one
    window, none compared against a baseline.

    So the one thing this file must never do is let an accept rate be read
    across rungs -- an accept from `gemma-4-31b-it` and one from
    `gpt-oss-120b` are different instruments, and their average measures
    neither.
    """
    import vitals

    rows = [
        {"kind": "wake", "ts": 1}, {"kind": "think", "ts": 2},
        {"kind": "exec_start", "ts": 3, "cmd": "ls"},
        {"kind": "exec_end", "ts": 4, "exit_code": 0},
        {"kind": "exec_start", "ts": 5, "cmd": "ls"},
        {"kind": "exec_end", "ts": 6, "exit_code": 2},
        {"kind": "cousin_verdict", "ts": 7, "verdict": "ACCEPTED", "rung": "A"},
        {"kind": "cousin_verdict", "ts": 8, "verdict": "UNKNOWN", "rung": "B",
         "error": "no-block"},
        {"kind": "cousin_verdict", "ts": 9, "verdict": "UNKNOWN",
         "error": "LadderExhausted: nothing answered"},
        {"kind": "cousin_want", "ts": 10, "text": "a date filter"},
        {"kind": "cousin_want", "ts": 11, "text": "a date filter"},
    ]
    m = vitals.measure(rows)
    check("vitals: verdicts are split by rung", set(m["by_rung"]) == {"A", "B", "(none)"},
          str(m["by_rung"]))
    check("vitals: a rung's accepts are not pooled with another's",
          m["by_rung"]["A"] == {"ACCEPTED": 1}
          and m["by_rung"]["B"] == {"UNKNOWN": 1}, str(m["by_rung"]))
    check("vitals: unknown causes are kept apart, not merged into one number",
          m["unknown_why"].get("no-block") == 1
          and m["unknown_why"].get("LadderExhausted") == 1, str(m["unknown_why"]))
    check("vitals: a repeated command shows in the distinct rate",
          abs(m["cmd_distinct_rate"] - 0.5) < 0.01, m["cmd_distinct_rate"])
    check("vitals: a repeated want shows in the want distinct rate",
          abs(m["want_distinct_rate"] - 0.5) < 0.01, m["want_distinct_rate"])
    check("vitals: the command failure rate is a ratio of real counts",
          abs(m["cmd_fail_rate"] - 0.5) < 0.01, m["cmd_fail_rate"])

    # The rendered report must not offer an overall accept rate to quote.
    text = vitals.fmt(m, "t")
    check("vitals: the report refuses to print a single pooled accept rate",
          "BY RUNG" in text, text[:200])

    # A comparison states DIRECTIONS and no score. A score is what invites
    # declaring a change good because one number moved.
    cmp_text = vitals.compare(m, m)
    check("vitals: a comparison warns that one window is an anecdote",
          "not deterministic" in cmp_text, cmp_text[-200:])
    check("vitals: and it produces no overall score to be quoted",
          "score" not in cmp_text.lower(), cmp_text[:200])

    check("vitals: an empty journal measures zero rather than dividing by it",
          vitals.measure([])["cmd_fail_rate"] == 0.0)


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


def test_observer_stop_button_states():
    """A stop REQUEST and a stopped engine are different, and the one control
    this window offers must not conflate them.

    The request is honoured at the END of the current cycle, which on a slow
    rung is minutes. A button that says "stopped" while the engine is still
    working is how someone reaches for kill -- and killing mid-cycle throws
    away the work the graceful stop exists to protect.
    """
    import observer as obs

    check("stopbtn: running when the unit is up and no stop is pending",
          obs.engine_state(False, True) == obs.RUNNING)
    check("stopbtn: STOPPING is its own state, not 'stopped'",
          obs.engine_state(True, True) == obs.STOPPING)
    check("stopbtn: stopped once the unit is gone",
          obs.engine_state(False, False) == obs.STOPPED
          and obs.engine_state(True, False) == obs.STOPPED)

    label, enabled, tip = obs.engine_button(obs.RUNNING)
    check("stopbtn: offers to stop while running", "Stop" in label and enabled)

    label, enabled, tip = obs.engine_button(obs.STOPPING)
    check("stopbtn: while stopping it is DISABLED, so no second click",
          not enabled, label)
    check("stopbtn: and it says the wait is the cycle finishing",
          "cycle" in label.lower() or "cycle" in tip.lower(), label + " / " + tip)

    label, enabled, tip = obs.engine_button(obs.STOPPED)
    check("stopbtn: offers to start once stopped", "Start" in label and enabled)
    check("stopbtn: and says the stop file must be cleared, which it does",
          "STOP" in tip, tip)


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


def test_expected_refusals_are_not_called_errors():
    """On a free tier, a rung with nothing to give is the WEATHER.

    Tue, 2026-09-13: "we completely expect half our calls to llm api's will
    return nothing... calling it rung_error and error is confusing, and this
    might confuse you or another llm inspecting the log into thinking its an
    issue to fix and not ignore."

    That is the truncation-marker scar in a new place: a label that makes the
    reader conclude the wrong thing. The reader here is a future session, and
    the cost is a night spent fixing the weather.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = bodymod.LocalBody(root=os.path.join(d, "body"))

    def unreachable(_p):
        raise backends.LadderExhausted("no rung answered", all_walled=False)

    e = Engine(j, b, "brief", unreachable, unreachable,
               os.path.join(d, "context.md"))
    try:
        e.run_cycle()
    except backends.LadderExhausted:
        pass
    kinds = dict(j.kinds())
    check("weather: an unreachable ladder is DEFERRED, not an error",
          kinds.get("think_deferred") == 1 and not kinds.get("error"),
          str(kinds))

    # A genuine fault must still be loud, or the rename buries real problems.
    def broken(_p):
        raise RuntimeError("something is actually wrong")

    j2 = Journal(os.path.join(d, "j2.jsonl"))
    b2 = bodymod.LocalBody(root=os.path.join(d, "body2"))
    e2 = Engine(j2, b2, "brief", broken, broken, os.path.join(d, "c2.md"))
    try:
        e2.run_cycle()
    except RuntimeError:
        pass
    k2 = dict(j2.kinds())
    check("weather: a REAL fault is still called an error",
          k2.get("error") == 1 and not k2.get("think_deferred"), str(k2))

    # And at the rung level: a credential the provider refuses needs a human,
    # so it must not hide among the expected refusals.
    class H(Exception):
        def __init__(self, code):
            self.code = code

    j3 = Journal(os.path.join(d, "j3.jsonl"))
    try:
        backends.ladder([("bad", lambda _p: (_ for _ in ()).throw(H(401)))],
                        journal=j3, sleep=lambda _s: None)("x")
    except backends.LadderExhausted:
        pass
    k3 = dict(j3.kinds())
    check("weather: a rejected credential is BROKEN, not merely declined",
          k3.get("rung_broken") == 1 and not k3.get("rung_declined"), str(k3))
    check("weather: and it is flagged as needing a human",
          j3.read(kinds=["rung_broken"])[0].get("expected") is False)

    b.destroy(); b2.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_same_rung_is_never_knocked_twice_without_a_gap():
    """Retrying a provider milliseconds after it refuses gets you flagged.

    Tue, 2026-09-13: "if you trigger the same say milliseconds after rejection
    some llm providers might flag you as bot run." The retry loop did exactly
    that -- a RETRY disposition re-attempted the SAME rung with no gap at all.
    Being flagged costs the account, and the account is shared with the spine,
    so the cost lands on the sibling project.
    """
    class H(Exception):
        def __init__(self, code):
            self.code = code

    slept = []

    def flaky(_p):
        raise H(500)          # RETRY: same rung, second attempt

    def alive(_p):
        return "ok", {"model": "m", "done_reason": "stop"}

    ask = backends.ladder([("a", flaky), ("b", alive)], sleep=slept.append)
    _t, meta = ask("x")
    check("gap: a second attempt on the SAME rung waits first",
          slept and slept[0] >= 1, str(slept))
    check("gap: and it still falls through to the next rung", meta["rung"] == "b")

    # Stepping to a DIFFERENT provider needs no gap -- that is the point of a
    # ladder, and pausing there would waste the fall-through.
    slept2 = []

    def quota_dead(_p):
        raise H(429)          # NEXT: step on immediately

    ask2 = backends.ladder([("a", quota_dead), ("b", alive)], sleep=slept2.append)
    ask2("x")
    check("gap: stepping to a DIFFERENT rung is immediate, no wasted wait",
          slept2 == [], str(slept2))


def test_a_spent_rung_is_remembered_not_rediscovered():
    """Asking a rung we already know is spent costs the SIBLING a request.

    CLAUDE.md 4 requires the ladder to be quota-polite because the free tier is
    shared with the spine. It was not: every call re-probed every rung.
    Measured in run 2's first 26 minutes -- 15 of 29 rung failures were repeat
    429s against rungs already known spent, about 35 wasted requests an hour.

    Idea taken from the spine's keychain/quota_state.py (read 2026-09-13,
    rewritten here -- 2.6 permits reading that source and forbids sharing
    files with it).
    """
    from kernel import quota

    class H(Exception):
        def __init__(self, code):
            self.code = code

    calls = collections.Counter()

    def quota_dead(_p):
        calls["dead"] += 1
        raise H(429)

    def transient(_p):
        calls["flaky"] += 1
        raise H(500)

    def alive(_p):
        calls["alive"] += 1
        return "ok", {"model": "m", "done_reason": "stop"}

    st = {}
    ask = backends.ladder([("dead", quota_dead), ("flaky", transient),
                           ("alive", alive)], quota_state=st, sleep=lambda _s: None)
    ask("x"); ask("x"); ask("x")

    # **The record must NOT change the ladder.** Tue, 2026-09-13: the framework
    # tries the best rung, then the next, deterministically, every time -- and
    # the models are unaware which rung worked. These numbers exist so a HUMAN
    # can see whether a rung has gone permanently stale. A skip would also fail
    # in the direction that costs most: a rung that recovered stays unused
    # until a timer says otherwise.
    check("quota: a spent rung is STILL TRIED -- the record does not gate",
          calls["dead"] == 3, "asked %d times, expected 3" % calls["dead"])
    check("quota: the order stays deterministic, best rung first every time",
          calls["alive"] == 3, calls["alive"])
    check("quota: and the exhaustion is recorded for a human to read",
          quota.is_spent(st, "dead"), str(st))

    # THE distinction that matters for the RECORD: a 500 is transient and says
    # nothing about budget, so it must not look like a spent rung on a chart.
    check("quota: a transient failure is not recorded as spent",
          not quota.is_spent(st, "flaky"), str(st.get("flaky")))

    # Spent is not dead: the mark expires so the rung is retried, not condemned.
    now = time.time()
    st2 = quota.record_exhaustion({}, "r", now=now)
    check("quota: spent now", quota.is_spent(st2, "r", now=now))
    check("quota: and tried again once the window passes",
          not quota.is_spent(st2, "r", now=now + quota.FIRST_SKIP_SECS + 1))

    # A success clears it and KEEPS how long the dark period was -- the only
    # evidence there is for how long these windows really last.
    quota.record_success(st2, "r", now=now + 120)
    check("quota: success clears the mark", not quota.is_spent(st2, "r"))
    check("quota: and measures the outage rather than guessing it",
          abs(st2["r"]["last_recovery_secs"] - 120) < 1,
          st2["r"].get("last_recovery_secs"))

    # Repeated failures widen the window; the first failure time is kept so a
    # long outage does not later report as a short one.
    st3 = quota.record_exhaustion({}, "r", now=now)
    since = st3["r"]["since"]
    quota.record_exhaustion(st3, "r", now=now + 10)
    check("quota: a second failure widens the skip",
          st3["r"]["skip"] > quota.FIRST_SKIP_SECS, st3["r"]["skip"])
    check("quota: but the dark period still starts at the FIRST failure",
          st3["r"]["since"] == since, st3["r"]["since"])

    # A corrupt or missing state file must not stop the engine.
    d = tmpdir()
    bad = os.path.join(d, "q.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{not json")
    check("quota: a corrupt state file loads as empty rather than raising",
          quota.load(bad) == {})
    quota.save(bad, {"r": {"since": 1}})
    check("quota: and state survives a restart", quota.load(bad).get("r"))
    shutil.rmtree(d, ignore_errors=True)


def test_the_cousin_is_never_sent_to_a_tool_that_does_not_exist():
    """A guessed name may be garbage; believing it invents a complaint.

    2026-09-13, run 2, minutes after a clean reset: pick_target parsed the
    token after a write pattern and returned a single backtick. The cousin was
    sent to use a tool named `` ` ``, got `command not found`, and filed an
    honest RETURNED -- which reached the creature as *"I tried to run the tool
    you finished, but the system told me the command was not found"*, about a
    tool it had never made.

    The framework manufactured a complaint against the creature. shlex.quote
    had already made that probe SAFE; safe is not the same as real.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))

    # A command whose write-pattern is followed by junk, and a library that
    # does NOT contain that junk.
    executed = [("cat << 'EOF' > tools/own/`  weird", 0)]
    got = e.pick_target(executed, ["plan", "archive"], ["plan", "archive"])
    check("target: a guessed name that is not in the library is refused",
          got != "`", repr(got))
    check("target: and it falls back to a tool that really exists",
          got in ("plan", "archive"), repr(got))

    # A guess that IS real must still be honoured -- the guard must not make
    # the fallback useless.
    got2 = e.pick_target([("tool-edit plan", 0)], ["plan", "archive"],
                         ["plan", "archive"])
    check("target: a guess that names a real tool is still used",
          got2 == "plan", repr(got2))

    # A genuinely new tool always wins, guess or no guess.
    got3 = e.pick_target([("tool-edit plan", 0)], ["plan", "fresh"], ["plan"])
    check("target: a newly created tool takes precedence",
          got3 == "fresh", repr(got3))

    # An empty library cannot name a target at all.
    check("target: nothing to judge when the library is empty",
          e.pick_target([("x", 0)], [], []) == "")
    shutil.rmtree(d, ignore_errors=True)


def test_the_two_agents_share_one_queue():
    """An unreachable cousin stops the cycle, exactly as an unreachable
    creature does. They wait for each other.

    Tue's call, 2026-09-13, and the reason the first run was thrown away rather
    than patched. Over 546 cycles, 39 of 98 visits never happened -- and the
    cycle walked on each time as though the work had been looked at. The
    creature marked something done, nothing reviewed it, and it was told
    nothing at all: `done_blocked` is only set by a RETURNED, so an unreachable
    cousin produced SILENCE, which from the creature's side is indistinguish-
    able from "it was looked at and there was nothing to say".

    A trajectory built against feedback that silently went missing cannot be
    repaired afterwards, which is why the run was archived and reset.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = bodymod.LocalBody(root=os.path.join(d, "body"))

    def unreachable(_p):
        raise backends.LadderExhausted("no rung answered", all_walled=False)

    done = """```bash
remember current-phase done
```"""
    e = Engine(j, b, "brief",
               lambda _p: (done, {"model": "m", "done_reason": "stop"}),
               unreachable, os.path.join(d, "context.md"))

    raised = None
    try:
        e.run_cycle()
    except Exception as ex:
        raised = ex
    check("one queue: an unreachable cousin STOPS the cycle rather than "
          "letting it walk on unjudged",
          isinstance(raised, backends.LadderExhausted), repr(raised))
    check("one queue: the deferral is journalled, so a lost review is countable",
          len(j.read(kinds=["visit_deferred"])) == 1, str(dict(j.kinds())))
    check("one queue: and no verdict is invented for a visit that never happened",
          not j.read(kinds=["cousin_verdict"]), str(dict(j.kinds())))

    # The supervisor must treat it exactly as it treats an unreachable
    # creature: wait, do not spend the failure budget.
    check("one queue: the supervisor calls it a WAIT, the same as for a think",
          forever.default_is_wait(raised), repr(raised))

    # A cousin that DID run and answered badly is a different thing: it gates
    # nothing, says UNKNOWN, and the cycle completes.
    j2 = Journal(os.path.join(d, "ran.jsonl"))
    b2 = bodymod.LocalBody(root=os.path.join(d, "body2"))
    e2 = Engine(j2, b2, "brief",
                lambda _p: (done, {"model": "m", "done_reason": "stop"}),
                lambda _p: ("no verdict block here at all",
                            {"model": "m", "done_reason": "stop"}),
                os.path.join(d, "c2.md"))
    r2 = e2.run_cycle()
    check("one queue: a cousin that RAN and answered badly still completes the "
          "cycle as UNKNOWN",
          r2.get("verdict") == cousin.UNKNOWN, str(r2))
    check("one queue: and that one is recorded as a verdict, because it happened",
          len(j2.read(kinds=["cousin_verdict"])) == 1, str(dict(j2.kinds())))

    b.destroy(); b2.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_visit_that_never_happened_does_not_consume_its_trigger():
    """Deferred is not the same as lost.

    2026-09-13, Tue asked whether the ping-pong simply stops when gemini runs
    out. The queue for the CREATURE exists -- the supervisor waits and retries.
    The gap was on the cousin's side: the counters that summoned a visit were
    cleared unconditionally, so when no rung could be reached the trigger was
    consumed and that work was never judged, not later, not when quota
    returned.

    The contradiction was already in the file. One scar says a visit is the
    ANSWER to whatever summoned it, so it clears the counters. `visit_cousin`
    says an instrument that cannot run says UNKNOWN. UNKNOWN is explicitly not
    an answer, and the reset took the wrong side.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = bodymod.LocalBody(root=os.path.join(d, "body"))

    writes = """```bash
cat << 'SH' > tools/own/newthing
#!/bin/sh
echo hi
SH
chmod +x tools/own/newthing
```"""

    def creature(_p):
        return writes, {"model": "m", "done_reason": "stop"}

    # A cousin that RAN and answered badly. (An UNREACHABLE cousin is a
    # different case and now stops the cycle entirely -- see
    # test_the_two_agents_share_one_queue.)
    def answered_badly(_p):
        return "I have opinions but no verdict block", {"model": "m",
                                                        "done_reason": "stop"}

    unreachable = answered_badly
    e = Engine(j, b, "brief", creature, answered_badly,
               os.path.join(d, "context.md"))
    e.cycles_since_visit = 7
    e.cycles_since_change = 5
    r = e.run_cycle()

    check("unanswered: the trigger did fire, so this is not a vacuous test",
          r.get("triggers"), str(r))
    check("unanswered: the verdict is UNKNOWN, never invented",
          r.get("verdict") == cousin.UNKNOWN, r.get("verdict"))
    check("unanswered: the visit counter is NOT cleared by a visit that could "
          "not happen",
          e.cycles_since_visit > 7, e.cycles_since_visit)
    # The STALL counter legitimately reset above, because a tool really was
    # written -- the library changed, so "nothing is moving" is false. Isolate
    # it with a cycle that triggers WITHOUT changing anything.
    j3 = Journal(os.path.join(d, "stall.jsonl"))
    b3 = bodymod.LocalBody(root=os.path.join(d, "body3"))
    done = """```bash
remember current-phase done
```"""
    e3 = Engine(j3, b3, "brief",
                lambda _p: (done, {"model": "m", "done_reason": "stop"}),
                unreachable, os.path.join(d, "c3.md"))
    e3.cycles_since_visit = 7
    e3.cycles_since_change = 5
    r3 = e3.run_cycle()
    check("unanswered: a trigger fired without the library changing",
          r3.get("triggers"), str(r3))
    check("unanswered: neither counter is cleared when nothing changed AND the "
          "cousin could not be reached",
          e3.cycles_since_visit > 7 and e3.cycles_since_change >= 5,
          "%d/%d" % (e3.cycles_since_visit, e3.cycles_since_change))
    b3.destroy()
    check("unanswered: the lost visit is journalled so it can be counted",
          len(j.read(kinds=["visit_unanswered"])) == 1,
          str(dict(j.kinds())))

    # The opposite case must still hold, or the nag scar returns: a visit that
    # DID answer clears what summoned it.
    j2 = Journal(os.path.join(d, "answered.jsonl"))
    b2 = bodymod.LocalBody(root=os.path.join(d, "body2"))
    e2 = Engine(j2, b2, "brief", creature,
                lambda _p: (ACCEPT_REPLY, {"model": "m", "done_reason": "stop"}),
                os.path.join(d, "c2.md"))
    e2.cycles_since_visit = 7
    e2.cycles_since_change = 5
    e2.run_cycle()
    check("unanswered: a visit that DID answer still clears its counters",
          e2.cycles_since_visit == 0 and e2.cycles_since_change == 0,
          "%d/%d" % (e2.cycles_since_visit, e2.cycles_since_change))

    b.destroy(); b2.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_an_exhausted_ladder_reaches_the_supervisor():
    """END TO END: ladder -> run_cycle -> Supervisor. Assert the ROUTE.

    2026-09-12, caught on the laptop minutes before the first overnight run.
    run_cycle caught the think exception and returned `think_failed`, so the
    supervisor saw a SUCCESSFUL cycle and started the next one two seconds
    later -- measured at 174s then 2s. Every bound built for this case (the
    wait, the backoff, the failure ceiling) was unreachable, and a night of it
    would have hammered rungs the spine also depends on.

    Each piece was individually green. The ROUTE between them was dead -- the
    `want` channel scar exactly, so this asserts the route and not the pieces.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = bodymod.LocalBody(root=os.path.join(d, "body"))

    def exhausted(_prompt):
        raise backends.LadderExhausted("no rung answered", all_walled=False)

    e = Engine(j, b, "brief", exhausted, exhausted,
               os.path.join(d, "context.md"))

    raised = None
    try:
        e.run_cycle()
    except Exception as ex:
        raised = ex
    check("route: run_cycle does not swallow an exhausted ladder",
          isinstance(raised, backends.LadderExhausted),
          "run_cycle returned %r instead of raising" % (raised,))
    # Journalled as DEFERRED rather than error: on a free tier a ladder with
    # nothing to give is the weather, and calling it an error sends the next
    # reader -- human or model -- hunting for a bug that is not there.
    check("route: and it still journals the deferral before re-raising",
          len(j.read(kinds=["think_deferred"])) == 1, str(dict(j.kinds())))

    # Now the whole route: the supervisor must WAIT, not spin.
    slept = []
    sup = forever.Supervisor(e.run_cycle, os.path.join(d, "STOP"), journal=j,
                             pause=5, wait_base=60, wait_cap=3600,
                             max_consecutive_waits=4,
                             sleep=slept.append, exists=lambda p: False)
    ran, reason = sup.loop(max_cycles=10)
    check("route: a dead ladder makes the loop WAIT rather than spin",
          slept and min(slept) >= 60,
          "waits were %s -- the pacing never applied" % slept[:5])
    check("route: it is recorded as waiting, not as a cycle that ran",
          ran == 0 and len(j.read(kinds=["loop_waiting"])) >= 2,
          "ran=%d waits=%d" % (ran, len(j.read(kinds=["loop_waiting"]))))
    check("route: and it gives up eventually instead of waiting forever",
          "waits" in reason, reason)

    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_preflight_is_advisory_for_an_unattended_run():
    """Refusing to start is right when someone is watching, and wrong overnight.

    2026-09-12, the first start on the laptop: gemini hung, the timeout fired,
    openrouter was at its quota, and the run refused before writing a single
    record. For a bounded run that is correct -- a journal full of failures the
    model never produced is worse than no journal. For an unattended one it
    means a transient hiccup at 22:00 costs the entire night, and the free tier
    is unreliable BY DEFINITION: that is the condition this engine lives in,
    not an exception to it.
    """
    import run as runmod

    check("preflight: a bounded run still REFUSES when no rung answers",
          "return 3" in io.open("run.py", encoding="utf-8").read(),
          "the refusal path is gone entirely")

    # The behavioural contract, without reaching a model: the supervisor must
    # treat an unreachable ladder as a WAIT, which is what lets --forever
    # survive the start that just failed.
    dead = backends.ladder([("only", lambda _p: (_ for _ in ()).throw(
        backends.LadderExhausted("nothing answered", all_walled=False)))], sleep=lambda _s: None)
    raised = None
    try:
        dead("hello")
    except Exception as e:
        raised = e
    check("preflight: an unreachable ladder surfaces as LadderExhausted",
          isinstance(raised, backends.LadderExhausted), repr(raised))
    check("preflight: and the supervisor calls that a wait, not a fault",
          forever.default_is_wait(raised), repr(raised))

    ok, why = backends.preflight(dead, "creature")
    check("preflight: it reports the failure rather than raising through",
          ok is False and "creature" in why, repr(why))


def test_a_quota_wall_is_not_a_fault():
    """An overnight run must survive a rate limit, and die on a bad key.

    On the deployed laptop there is NO local rung to fall to, so when both
    remote rungs are quota'd the ladder raises. Counting that as a failure
    would end the loop after ~15 minutes of backoff and waste the night --
    free-tier windows reset on a clock, so waiting is the correct move.

    The opposite case must still end it: waiting cannot fix a rejected
    credential, and a loop that waits politely forever on a broken key looks
    exactly like one that is working.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    slept = []

    def quota_walled():
        raise backends.LadderExhausted("all rungs 429", all_walled=False)

    sup = forever.Supervisor(quota_walled, os.path.join(d, "STOP"), journal=j,
                             pause=0, max_consecutive_failures=3,
                             wait_base=60, wait_cap=3600, max_consecutive_waits=5,
                             sleep=slept.append, exists=lambda p: False)
    ran, reason = sup.loop(max_cycles=6)
    check("wait: a quota wall does NOT spend the failure budget",
          "consecutive failures" not in reason, reason)
    check("wait: waiting is journalled distinctly from failing",
          len(j.read(kinds=["loop_waiting"])) >= 3
          and not j.read(kinds=["loop_error"]),
          str(dict(j.kinds())))
    check("wait: a permanently unavailable rung eventually gives up and says so",
          "after" in reason and "waits" in reason, reason)
    # FLAT, not growing. Tue, 2026-09-13: retry the whole ladder every two or
    # three minutes. The thing being waited on returns on a CLOCK, so a
    # widening gap can only miss the reset -- an hour-long backoff leaves the
    # engine idle through a window that already opened.
    check("wait: it waits in MINUTES, at a FLAT cadence",
          slept and all(x == slept[0] for x in slept) and slept[0] >= 60,
          str(slept[:6]))
    check("wait: the wait is capped at an hour, not doubled forever",
          all(x <= 3600 for x in slept), str(slept[:6]))
    check("wait: a wait is not counted as a cycle that ran",
          ran == 0, "counted %d cycles in which nothing happened" % ran)

    # A rejected credential is the opposite case and must END the loop.
    def creds_rejected():
        raise backends.LadderExhausted("every rung walled", all_walled=True)

    j2 = Journal(os.path.join(d, "j2.jsonl"))
    sup2 = forever.Supervisor(creds_rejected, os.path.join(d, "STOP"),
                              journal=j2, pause=0, max_consecutive_failures=3,
                              sleep=lambda _s: None, exists=lambda p: False)
    ran2, reason2 = sup2.loop(max_cycles=50)
    check("wait: every rung REJECTING us ends the loop instead of waiting",
          "consecutive failures" in reason2, reason2)
    check("wait: and that is recorded as an error, not as waiting",
          j2.read(kinds=["loop_error"]) and not j2.read(kinds=["loop_waiting"]),
          str(dict(j2.kinds())))

    # The classifier itself, directly: an ordinary bug is never a wait.
    check("wait: an ordinary exception is a fault, never a wait",
          not forever.default_is_wait(RuntimeError("a real bug")))
    check("wait: a quota exhaustion IS a wait",
          forever.default_is_wait(
              backends.LadderExhausted("429", all_walled=False)))
    shutil.rmtree(d, ignore_errors=True)


def test_ladder_reports_why_it_was_exhausted():
    """The supervisor can only tell waiting from failing if the ladder says
    which happened."""
    class H(Exception):
        def __init__(self, code): self.code = code

    def quota(_p):
        raise H(429)

    def badkey(_p):
        raise H(401)

    try:
        backends.ladder([("a", quota), ("b", quota)], sleep=lambda _s: None)("x")
    except backends.LadderExhausted as e:
        check("ladder: rungs that were merely rate-limited are not 'walled'",
              e.all_walled is False, str(e))

    try:
        backends.ladder([("a", badkey), ("b", badkey)], sleep=lambda _s: None)("x")
    except backends.LadderExhausted as e:
        check("ladder: every rung rejecting the credential IS walled",
              e.all_walled is True, str(e))

    try:
        backends.ladder([("a", badkey), ("b", quota)], sleep=lambda _s: None)("x")
    except backends.LadderExhausted as e:
        check("ladder: one good rung merely rate-limited means WAIT, not die",
              e.all_walled is False, str(e))


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


def test_temperature_is_configurable_and_defaults_to_zero():
    """A measurement wants temperature 0; a life does not.

    At 0 the same context produces the same decision forever, so a creature
    that reaches a repeating state can never leave it. Watched twice on this
    engine: `ls -R tools/own/` for six consecutive cycles (2026-09-11) and
    `cat plan; cat log-read` for twelve (2026-09-12) -- replies of 31-65
    chars, every one finish=stop, nothing truncated and nothing built.

    The default stays 0 so the trial keeps measuring the same brief the same
    way. The deployed CREATURE is configured above it.
    """
    sent = {}

    class FakeResp:
        def __init__(self, payload):
            self._p = payload
        def read(self):
            return json.dumps(self._p).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        sent["body"] = json.loads(req.data.decode())
        return FakeResp({"choices": [{"message": {"content": "ok"},
                                      "finish_reason": "stop"}],
                         "usage": {"completion_tokens": 1}})

    real = backends.urllib.request.urlopen
    backends.urllib.request.urlopen = fake_urlopen
    try:
        os.environ["COUSIN_FAKE_KEY"] = "x"
        backends.openai_chat("m", "https://x/v1", key_env="COUSIN_FAKE_KEY")("hi")
        check("temperature: defaults to 0, so the trial keeps measuring one brief",
              sent["body"].get("temperature") == 0, str(sent["body"])[:120])

        backends.openai_chat("m", "https://x/v1", key_env="COUSIN_FAKE_KEY",
                             temperature=0.4)("hi")
        check("temperature: and a LIFE can be configured off the fixed point",
              sent["body"].get("temperature") == 0.4, str(sent["body"])[:120])
        check("temperature: it travels in the request, not just the signature",
              "temperature" in sent["body"])
    finally:
        backends.urllib.request.urlopen = real
        os.environ.pop("COUSIN_FAKE_KEY", None)

    # And it must survive the spec, or the deployed ladder cannot set it.
    ask = backends.from_spec([{"name": "n", "kind": "openai_chat", "model": "m",
                               "base_url": "https://x/v1",
                               "key_env": "NOPE", "temperature": 0.4}])
    check("temperature: a rung spec accepts it", callable(ask))


def test_classify_error_never_raises():
    """The parent's classify_error had a default branch that RAISED, so one
    unrecognised error took down the ladder instead of stepping past a rung."""
    class H(Exception):
        def __init__(self, code): self.code = code

    got = {}
    for code in (401, 403, 429, 402, 500, 503, 404, 418):
        got[code] = backends.classify_error(H(code))[0]
    check("ladder: a rejected credential walls that rung",
          got[401] == backends.WALL, str(got))
    # 403 must NOT wall: Cloudflare-fronted rungs answer 403 to a request their
    # WAF dislikes, which has nothing to do with the credential. Walling on it
    # permanently lost a working rung, 2026-09-12.
    check("ladder: a 403 steps to the next rung, it does not condemn the rung",
          got[403] == backends.NEXT, str(got))
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

    ask = backends.ladder([("top", dead), ("second", alive)], journal=j, sleep=lambda _s: None)
    text, meta = ask("x")
    check("ladder: a refusing rung falls through to the next", text == "hello")
    check("ladder: the reply records WHICH rung served it",
          meta.get("rung") == "second", str(meta))
    # And the rung must survive into the JOURNAL, not just the meta dict. With
    # a heterogeneous ladder, a verdict served by a rung the brief was never
    # measured on is a different instrument, and an accept rate read later
    # would silently mix them.
    j2 = Journal(os.path.join(d, "rungrec.jsonl"))
    cousin.visit(lambda _p: (ACCEPT_REPLY, {"model": "m2", "rung": "second",
                                            "done_reason": "stop"}),
                 "brief", "c", "h", "t", journal=j2)
    rec = j2.read(kinds=["cousin_verdict"])[0]
    check("ladder: the serving rung is journalled with the verdict",
          rec.get("rung") == "second", str(rec)[:160])
    check("ladder: falling through is journalled, not silent",
          len(j.read(kinds=["rung_fell_through"])) == 1)
    check("ladder: a declined rung is journalled with its reason",
          len(j.read(kinds=["rung_declined"])) == 1)
    # DECLINED, not error. On a free tier half the calls are expected to return
    # nothing, so "error" asserts something false -- it misleads a human and it
    # misleads the next model inspecting the log into fixing the weather.
    check("ladder: an expected refusal is NOT called an error",
          not j.read(kinds=["rung_error"])
          and j.read(kinds=["rung_declined"])[0].get("expected") is True,
          str(dict(j.kinds())))

    # EVERY failure is counted, not just the first of its kind. Announcing once
    # was right for noise and wrong for measurement: it made the journal show
    # WHICH rungs fail and never HOW OFTEN, so a rung that failed twice and one
    # that failed two hundred times looked identical -- and "how much of the
    # night went to quota" could not be answered from the record.
    j3 = Journal(os.path.join(d, "counts.jsonl"))

    # A TRANSIENT failure, deliberately: a 429 now marks the rung spent and it
    # is skipped, so it cannot fail three times. Counting and skipping are
    # separate properties and this asserts the first without the second.
    def always_500(_p):
        raise H(500)

    ask3 = backends.ladder([("only", always_500)], journal=j3, sleep=lambda _s: None)
    for _ in range(3):
        try:
            ask3("x")
        except backends.LadderExhausted:
            pass
    errs = j3.read(kinds=["rung_declined"])
    # SIX, not three: a 500 is RETRY, so each of the three calls attempts twice.
    # Every ATTEMPT is a real request and every one is counted -- that is the
    # point, since the old announce-once recorded exactly one of them.
    check("ladder: every rung failure is counted, not only the first of its kind",
          len(errs) == 6, "journalled %d of 6 (3 calls x 2 attempts)" % len(errs))
    check("ladder: and the first still carries the full reason, so a tally is "
          "distinguishable from an announcement",
          errs[0].get("first") is True and errs[-1].get("first") is False,
          str([e.get("first") for e in errs]))

    # A walled rung is not retried for the rest of the session.
    def badkey(_p):
        calls.append("badkey")
        raise H(401)

    ask2 = backends.ladder([("bad", badkey), ("second", alive)], journal=j, sleep=lambda _s: None)
    ask2("x"); before = calls.count("badkey")
    ask2("x")
    check("ladder: a walled rung is never tried again this session",
          calls.count("badkey") == before, "tried %d times" % calls.count("badkey"))

    def always(_p):
        raise H(429)

    try:
        backends.ladder([("a", always)], sleep=lambda _s: None)("x")
        exhausted = False
    except backends.LadderExhausted:
        exhausted = True
    check("ladder: every rung refusing raises LadderExhausted, not a fake reply",
          exhausted)

    # An exhausted ladder must NOT become a verdict. It used to return UNKNOWN
    # and let the cycle walk on unjudged; it now propagates so the whole cycle
    # defers and the two agents share one queue (2026-09-13).
    raised = None
    try:
        cousin.visit(backends.ladder([("a", always)], sleep=lambda _s: None), "brief", "c", "h", "t")
    except Exception as ex:
        raised = ex
    check("ladder: an exhausted ladder propagates rather than becoming a verdict",
          isinstance(raised, backends.LadderExhausted), repr(raised))
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


def test_history_can_never_parse_as_a_command():
    """THE contract for the history block: what the creature is SHOWN must
    never look like something to run.

    2026-09-12, measured on the laptop. The command was fenced and its output
    was not, so past output sat exactly where an emitted command goes. The
    creature ran `log-read`, was shown the log lines that way, and on the next
    wake emitted them AS A COMMAND -- nine times in a row, exit 127 each, a
    degenerate loop it had no way to see the edge of. The framework produced
    that behaviour and the creature would have worn it.

    So this asserts the property, not the formatting: run the rendered history
    through the SAME parser the kernel uses on a reply, and require nothing
    comes back. A formatting test would go green on a different mistake.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))

    # Output engineered to break a naive renderer: a fence, a $ line, and a
    # bash block of its own -- all things a tool can legitimately print.
    nasty = "\n".join([
        "```bash", "rm -rf /", "```",
        "$ echo this is output, not a command",
        "[2026-09-12 19:39:55 UTC] a log line"])
    j.append("exec_start", cmd="log-read -n 10")
    j.append("exec_end", exit_code=0, stdout=nasty, stderr="")
    j.append("exec_start", cmd="cat tools/own/ask")
    j.append("exec_end", exit_code=0, stdout="#!/usr/bin/env python3\nimport os",
             stderr="bash: boom")

    hist = e.recent_block()
    check("history: the rendered history contains NO fence at all",
          "```" not in hist.replace("`" + "`" + "`bash", "@@@").replace("@@@", "")
          or hist.count("```") == 0,
          "fences present: %d" % hist.count("```"))
    check("history: and the kernel's own parser finds nothing to run in it",
          think.parse_blocks(hist) == [],
          "parsed %r" % (think.parse_blocks(hist)[:1],))
    check("history: every line is marked as transcript",
          all(ln.startswith("|") or not ln.strip() or ln.startswith("#")
              or ln.startswith("(") or ln.startswith("**")
              for ln in hist.split("\n")),
          [ln for ln in hist.split("\n")
           if ln.strip() and not ln.startswith(("|", "#", "(", "**"))][:2])

    check("history: the command is still legible in it",
          "log-read -n 10" in hist and "cat tools/own/ask" in hist)
    # Command, exit and OUTPUT must be told apart INSIDE the transcript, not
    # only from the reply. They shared one prefix, and 7 of 27 commands in a
    # live hour exited 2 or 127 because the creature re-emitted tool output as
    # a command: `=== CURRENT CONTEXT ===`, `[PLAN] Goal: Write report`.
    check("history: output is delimited from the command that produced it",
          "what it printed back" in hist and "end of what it printed" in hist,
          hist[:400])
    check("history: and stderr is labelled as stderr, not as more output",
          "printed to stderr" in hist, hist[-300:])
    check("history: the header warns that output is not a command",
          "not commands" in hist or "are OUTPUT" in hist, hist[:400])
    check("history: so is the exit code and the output",
          "exit 0" in hist and "a log line" in hist)
    check("history: stderr survives too", "boom" in hist, hist[-200:])

    # A tool that prints a novel's worth of text must not become the context.
    j2 = Journal(os.path.join(d, "big.jsonl"))
    e2 = Engine(j2, Stub(), "brief", None, None, os.path.join(d, "c2.md"))
    j2.append("exec_start", cmd="cat huge")
    j2.append("exec_end", exit_code=0, stdout="x" * 40000, stderr="")
    big = e2.recent_block()
    check("history: a huge output is capped again for the CONTEXT",
          len(big) < 8000, "history was %d chars" % len(big))
    # The warning must SURVIVE the truncation. It was being replaced by the
    # "older lines dropped" header, so it vanished exactly when the transcript
    # was longest -- which is when the creature started re-running its own
    # output. A safety note that disappears under load is not one.
    check("history: the output-is-not-a-command warning survives truncation",
          "not commands" in big or "are OUTPUT" in big, big[:300])
    check("history: and the truncation still announces itself",
          "Older lines dropped" in big or "withheld by the log" in big,
          big[:300])
    check("history: and the cut announces itself",
          "withheld by the log" in big, big[-120:])
    shutil.rmtree(d, ignore_errors=True)


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
# call: older <term> <file>
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
    # And HOW it is called. The does-line says what a tool is for; the
    # call-line says what it can be ASKED to do. Without the second, a tool
    # with sub-commands is indistinguishable from one without -- 2026-09-13 the
    # cousin asked three times, in three wordings, for a capability `plan
    # add-step` already had, and all three restatements stood in the creature's
    # direction at once.
    check("library: and HOW each one is called, so an existing capability is "
          "visible rather than requested again",
          "used as: older <term> <file>" in p, p[-400:] if p else "")
    check("library: the tool under judgement is not listed as its own sibling",
          p.count("newthing") >= 1 and "- newthing" not in p, "listed itself")


def test_an_unreadable_verdict_keeps_its_evidence():
    """When a verdict cannot be read, the REPLY must survive.

    2026-09-12, a 7-hour live run: seven UNKNOWN verdicts, every one
    `no-block`. The cause -- the reply being truncated before the block, which
    the contract puts LAST -- was diagnosable only because `finish=length`
    happened to be journalled. The reply itself was thrown away, so the next
    such run would have started the same diagnosis from nothing.

    A summary cannot be re-interrogated when the summary is what is wrong.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    long_reply = "I thought about it at some length. " * 80   # no verdict block
    cousin.visit(lambda _p: (long_reply, {"model": "m", "rung": "r",
                                          "done_reason": "length"}),
                 "brief", "c", "h", "t", journal=j)
    rec = j.read(kinds=["cousin_verdict"])[0]
    # The label is the one this fixture's own cause deserves. It asserted
    # `no-block` until 2026-09-13, which is the imprecision the docstring above
    # had already described in words: this reply was CUT OFF, not withheld.
    check("raw: an unreadable verdict is recorded as UNKNOWN, and says it was cut",
          rec.get("verdict") == cousin.UNKNOWN
          and rec.get("error") == "truncated-before-block",
          str(rec)[:140])
    check("raw: and the reply itself is KEPT, not summarised away",
          "I thought about it" in (rec.get("raw") or ""), str(rec.get("raw"))[:80])
    check("raw: with the true length, so a cap cannot hide how big it was",
          rec.get("raw_chars") == len(long_reply),
          "%s vs %s" % (rec.get("raw_chars"), len(long_reply)))
    check("raw: the stored copy is CAPPED -- a runaway reply is the case this "
          "fires on, and the journal must not inherit its size",
          len(rec.get("raw") or "") <= 1200, len(rec.get("raw") or ""))

    # The case that actually happened: the model talked itself out of
    # answering. An empty reply and a reply that was ALL reasoning arrive
    # identical unless the stripping is measured -- and they have different
    # fixes, so the difference has to survive into the journal.
    j3 = Journal(os.path.join(d, "stripped.jsonl"))
    cousin.visit(lambda _p: ("", {"model": "m", "rung": "r",
                                  "done_reason": "length",
                                  "chars_before_strip": 8000,
                                  "chars_stripped": 8000}),
                 "brief", "c", "h", "t", journal=j3)
    r3 = j3.read(kinds=["cousin_verdict"])[0]
    check("raw: an all-reasoning reply is distinguishable from an empty one",
          r3.get("raw_chars") == 0 and r3.get("chars_before_strip") == 8000,
          str({k: r3.get(k) for k in ("raw_chars", "chars_before_strip",
                                      "chars_stripped")}))
    check("raw: and the amount stripped is recorded, not inferred",
          r3.get("chars_stripped") == 8000, r3.get("chars_stripped"))

    # RECOVERY. Stripping an unclosed reasoning block is right in general and
    # catastrophic in one case: when the answer was INSIDE the block the model
    # never closed. Cleaning must never destroy the thing it exists to uncover.
    buried = ("<thought>I should check whether it runs. It did. "
              + ACCEPT_REPLY + " and I never closed this thought")
    j4 = Journal(os.path.join(d, "recover.jsonl"))
    v4 = cousin.visit(lambda _p: ("", {"model": "m", "rung": "r",
                                       "done_reason": "length",
                                       "chars_before_strip": len(buried),
                                       "chars_stripped": len(buried),
                                       "raw_text": buried}),
                      "brief", "c", "h", "t", journal=j4)
    check("recover: a verdict buried in an unclosed thought is NOT lost",
          v4.verdict == cousin.ACCEPTED, "%s / %s" % (v4.verdict, v4.error))
    check("recover: and it is marked as recovered, not passed off as clean",
          getattr(v4, "recovered_from_reasoning", False) is True)

    # It must never INVENT one. A reply with no verdict stays UNKNOWN however
    # much reasoning it contains.
    j5 = Journal(os.path.join(d, "norecover.jsonl"))
    v5 = cousin.visit(lambda _p: ("", {"model": "m", "rung": "r",
                                       "done_reason": "length",
                                       "raw_text": "<thought>" + "musing " * 400}),
                      "brief", "c", "h", "t", journal=j5)
    check("recover: reasoning with no verdict in it stays UNKNOWN",
          v5.verdict == cousin.UNKNOWN, v5.verdict)

    # A readable verdict carries no raw copy: the evidence is the verdict.
    j2 = Journal(os.path.join(d, "ok.jsonl"))
    cousin.visit(lambda _p: (ACCEPT_REPLY, {"model": "m", "done_reason": "stop"}),
                 "brief", "c", "h", "t", journal=j2)
    rec2 = j2.read(kinds=["cousin_verdict"])[0]
    check("raw: a verdict that parsed does not duplicate its own reply",
          "raw" not in rec2, str(rec2)[:120])
    shutil.rmtree(d, ignore_errors=True)


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
    if os.environ.get("COUSIN_NO_LOCAL_MODEL"):
        # Probing loads a 12B model into VRAM. Set this when the GPU is wanted
        # for something else -- the gate should never be a reason not to run it.
        print("SKIP live model (COUSIN_NO_LOCAL_MODEL is set; VRAM left alone)")
        return
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


def _write_tool(own, name, does="", call="", body="echo hi"):
    os.makedirs(own, exist_ok=True)
    lines = ["#!/bin/sh"]
    if does:
        lines.append("# does: " + does)
    if call:
        lines.append("# call: " + call)
    lines.append(body)
    with open(os.path.join(own, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def test_the_creature_is_shown_its_own_library_every_wake():
    """It was asked not to build the fifth variant while never shown the four.

    The cousin's library gap was found 2026-09-12 and fixed; the SAME gap
    aimed at the builder survived it, because the fix was written as "the
    judge needs both sides of a comparison" rather than "both inhabitants need
    to see the library". 2026-09-13 Tue named it from the other end -- MCP and
    skills re-present a tool's frontmatter on every load, and a creature that
    is told its tools are on PATH and never told WHICH is being handed a
    promise the context does not keep.

    Every wake, not on a trigger: this is state, not news.
    """
    e, j, b, d = build_engine(["thinking, no commands"], [])
    own = os.path.join(b.mind, "tools", "own")
    _write_tool(own, "plan", does="tracks what to do next",
                call="plan goal|add|list|done")

    seen = {}

    def spy(prompt):
        seen["p"] = prompt
        return "thinking, no commands", {"model": "spy", "done_reason": "stop"}
    e.ask_creature = spy
    e.run_cycle()

    p = seen.get("p", "")
    check("creature library: it is shown the tools it has built",
          "plan" in p, p[-300:] if p else "(no prompt captured)")
    check("creature library: with each tool's stated purpose",
          "tracks what to do next" in p, p[-300:] if p else "")
    check("creature library: and how each one is called",
          "used as: plan goal|add|list|done" in p, p[-300:] if p else "")


def test_the_creatures_shell_does_not_inherit_the_engines_secrets():
    """The body ran untrusted input with the engine's whole environment.

    Found 2026-09-13 by an outside review of the public repo, and confirmed the
    same evening on the live laptop: a creature-style command run from the
    body's own directory read `~/keys/*.key` and listed the spine's directory,
    `config.yaml` included. `LocalBody`'s own docstring says it is "not a
    sandbox... for running OUR fixtures, never untrusted input" -- and the
    input in production is bash written by free-tier third-party models.

    An ALLOW-LIST, because a deny-list has to be updated every time a new
    secret-shaped variable appears and it will not be.

    This test does NOT claim the body is sandboxed. The key files stay readable
    by anything running as this user; only `DockerBody` or systemd
    `LoadCredential=`+`InaccessiblePaths=` closes that.
    """
    d = tmpdir()
    b = bodymod.LocalBody(os.path.join(d, "body"))
    os.environ["SPINE_API_KEY_CANARY"] = "sk-do-not-leak-me"
    try:
        r = b.run('echo "[$SPINE_API_KEY_CANARY]"; echo "home=$HOME"')
        check("env: a secret in the engine's environment does not reach the "
              "creature's shell",
              "do-not-leak-me" not in r.stdout, repr(r.stdout)[:120])
        check("env: HOME points into the body, so `~` is the creature's own tree",
              os.path.realpath(b.root) in os.path.realpath(
                  r.stdout.split("home=", 1)[-1].strip() or "/nowhere"),
              r.stdout)
        # It must still be a WORKING shell: stripping the environment is only
        # correct if the creature can still run things.
        ok = b.run("echo alive && which bash >/dev/null && echo hasbash")
        check("env: and the shell still works with the stripped environment",
              ok.code == 0 and "alive" in ok.stdout and "hasbash" in ok.stdout,
              "%s %r" % (ok.code, ok.stdout[:80]))
        keep = bodymod.CHILD_ENV_KEEP
        check("env: the allow-list carries PATH, or nothing is runnable",
              "PATH" in keep, keep)
        check("env: and carries no secret-shaped name",
              not [k for k in keep
                   if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET",
                                                   "PASS", "CRED"))], keep)
    finally:
        os.environ.pop("SPINE_API_KEY_CANARY", None)
        b.destroy()
        shutil.rmtree(d, ignore_errors=True)


def test_every_defined_test_is_registered():
    """A hand-maintained list in `main()` is a classic way a written test never
    runs. Raised by an outside review of the public repo on 2026-09-13 as
    unverified. It was in fact clean at 70/70 -- which is exactly why it earns
    an assertion rather than a one-off grep: nothing was stopping the next one
    from being forgotten.

    Both of this test's own first drafts were the fault it exists to catch.
    One split on the literal strings "def main(" and the totals line, which
    appear in this function's own source, so it split ITSELF, read a
    16-character body and declared all 70 tests unregistered. The other reached
    the file through a bash heredoc, where the word-boundary escape became a
    literal backspace byte and the pattern matched nothing at all. Both
    reported a confident wrong answer rather than an error.
    """
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    defined = set(re.findall(r"^def (test_[a-z0-9_]+)[(]", src, re.M))
    check("registry: the file defines tests at all, or this proves nothing",
          len(defined) > 40, len(defined))

    # ANCHORED TO COLUMN 0, so the literals inside this very function cannot
    # be mistaken for the runner.
    start = re.search(r"^def main[(]", src, re.M)
    check("registry: the runner is findable", bool(start))
    rest = src[start.end():] if start else ""
    end = re.search(r"^    total = ", rest, re.M)
    body = rest[:end.start()] if end else rest
    check("registry: and its list is non-empty, or this proves nothing",
          len(body) > 500, len(body))

    registered = set(re.findall(r"(test_[a-z0-9_]+)", body))
    missing = sorted(defined - registered)
    check("registry: every defined test is in the runner's list", not missing,
          missing)
    check("registry: and the runner names no test that does not exist",
          not sorted(registered - defined), sorted(registered - defined))


def test_giving_up_is_distinguishable_from_stopping():
    """Finishing and abandoning both exited 0, so nothing ever restarted it.

    2026-09-13. `forever` gives up after 5 consecutive failures or 600 waits;
    `run.py` printed the reason and returned 0; the unit says
    `Restart=on-failure`, which only fires on a non-zero exit. So the engine
    could abandon the run at 03:00, report success, and lie there until a human
    looked. At a ten-minute check that costs ten minutes. At a daily check it
    costs the night and the data -- which is what made it worth finding before
    the cadence was lengthened, not after.

    A FLAG rather than a parsed reason string: the reason is prose for a human,
    and a caller deciding by matching it is a checker agreeing with a producer
    by eye. That exact shape broke `wants()` earlier the same day.
    """
    d = tmpdir()
    stop = os.path.join(d, "STOP")

    # 1. Asked to stop: finished its job.
    def one():
        open(stop, "w").close()      # ask to stop, from inside the cycle
    s = forever.Supervisor(one, stop, sleep=lambda _x: None)
    s.loop(max_cycles=5)
    check("giveup: being asked to stop is NOT a fault", not s.ended_in_fault)

    # 2. Reached its ceiling: also finished its job.
    s2 = forever.Supervisor(lambda: None, os.path.join(d, "nope"),
                            sleep=lambda _x: None)
    ran, why = s2.loop(max_cycles=3)
    check("giveup: reaching the cycle ceiling is NOT a fault",
          not s2.ended_in_fault and ran == 3, "%s %s" % (ran, why))

    # 3. A run of failures: abandoned it.
    def boom():
        raise RuntimeError("the body is gone")
    s3 = forever.Supervisor(boom, os.path.join(d, "nope"),
                            sleep=lambda _x: None,
                            is_wait=lambda _e: False)
    ran3, why3 = s3.loop(max_cycles=50)
    check("giveup: a run of failures IS a fault, so systemd restarts it",
          s3.ended_in_fault and "consecutive failures" in why3, why3)

    # 4. Nothing to talk to, forever: also abandoned it. Waiting is correct
    #    behaviour; waiting for a day and then quitting is not a success.
    s4 = forever.Supervisor(boom, os.path.join(d, "nope"),
                            sleep=lambda _x: None,
                            is_wait=lambda _e: True,
                            max_consecutive_waits=3)
    ran4, why4 = s4.loop(max_cycles=50)
    check("giveup: exhausting the wait budget IS a fault",
          s4.ended_in_fault and "no rung available" in why4, why4)

    shutil.rmtree(d, ignore_errors=True)


def test_the_engine_unit_runs_the_creature_in_a_container():
    """PLAN item 7, the part that decides whether any of it is real.

    2026-09-16: the unit was edited to `--body docker`, the edit was then
    overwritten by a stale copy during a file shuffle, and the change was
    committed and deployed with the creature still on `LocalBody` -- keys
    readable, exactly as before. **Nothing in the gate noticed**, because
    every unit assertion was about restart bounds and sandboxing and none
    about which body the engine actually runs.

    A setting that is present, parsed and live can still do nothing; so can
    one that was never there at all. This asserts the body the unit selects,
    which is the only thing that makes item 7 true of the deployment rather
    than of the repository.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = io.open(os.path.join(here, "deploy", "cousin-engine.service"),
                   encoding="utf-8").read()
    # Wrapped ExecStart lines end in a backslash; flatten before matching.
    flat = re.sub(r"\\\s*\n\s*", " ", unit)
    execs = [l for l in flat.splitlines() if l.startswith("ExecStart=")]
    check("unit: it runs the engine", len(execs) == 1, execs)
    check("unit: and puts the creature in a CONTAINER, which is the whole of "
          "item 7 -- without this the keys are readable and nothing says so",
          "--body docker" in execs[0], execs[0][:200])
    pre = [l for l in flat.splitlines() if l.startswith("ExecStartPre=")]
    check("unit: the image is built before the engine needs it",
          any("docker build" in l for l in pre), pre)
    check("unit: and a failed build warns rather than blocking a start, since "
          "the previous image is usually still good",
          any(l.startswith("ExecStartPre=-") and "docker build" in l
              for l in pre), pre)
    # ...but an advisory step that can NEVER succeed is worse than no step.
    # buildx stamps an activity file under DOCKER_CONFIG, and
    # `ProtectHome=read-only` makes the default `~/.docker` unwritable, so the
    # build failed on every start while the `-` hid it.
    cfg = [l for l in flat.splitlines() if l.startswith("Environment=DOCKER_CONFIG=")]
    rw = [l.split("=", 1)[1] for l in flat.splitlines()
          if l.startswith("ReadWritePaths=")]
    check("unit: docker's config dir is redirected somewhere it can write",
          len(cfg) == 1, cfg)
    check("unit: and that somewhere is inside a path the unit may write to",
          cfg and any(cfg[0].split("=", 2)[2].startswith(p) for p in rw),
          "%s vs %s" % (cfg, rw))
    check("unit: the stale comment claiming the keys are open is gone",
          "The key files are NOT closed by this" not in unit, "")


def test_the_unit_bounds_its_own_restarting():
    """Restarting on failure without a bound is the crash loop that exiting 0
    was guarding against. systemd bounds it; we do not hand-roll it."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = open(os.path.join(repo, "deploy", "cousin-engine.service"),
                encoding="utf-8").read()
    check("unit: restarts only on failure, never always",
          "Restart=on-failure" in unit and "Restart=always" not in unit)

    # PrivateUsers=yes is what makes the rest of the sandbox real. Verified by
    # EFFECT on the laptop 2026-09-13: without it, a user unit carrying
    # ProtectSystem=strict + ProtectHome=read-only wrote a file into $HOME, so
    # every filesystem protection in this unit had been inert since it was
    # written. This asserts the line is present; only the laptop can prove it
    # works, and that check is in the commit body and CLAUDE.md §5.
    directives = [l.strip() for l in unit.splitlines()
                  if l.strip() and not l.strip().startswith("#")]
    for need in ("PrivateUsers=yes", "ProtectSystem=strict",
                 "ProtectHome=read-only", "NoNewPrivileges=true"):
        check("unit: %s" % need, need in directives, need)
    check("unit: the spine is made invisible, not merely read-only",
          any(d.startswith("InaccessiblePaths=") and "growing-spine" in d
              for d in directives),
          [d for d in directives if d.startswith("Inaccessible")])
    # IN THE SECTION WHERE THEY WORK. The first version of this test asserted
    # only that the strings appeared somewhere in the file, and passed happily
    # over both directives sitting in [Service], where systemd ignores them --
    # read back off the running unit as `StartLimitIntervalUSec=10s` while the
    # file said 1800. A checker that cannot distinguish the thing it measures
    # reports a clean-looking pass, never an error; this is the fourth time
    # that shape has been the finding here.
    # DIRECTIVES, not text. Scanning for the string alone matched the word
    # inside these very comments -- the third literal-matching slip in one
    # test, and the same shape as the fault it was written to catch.
    section, in_unit, in_service = None, {}, {}
    for line in unit.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line
        elif line.startswith("StartLimit"):
            k, _, v = line.partition("=")
            (in_unit if section == "[Unit]" else in_service)[k] = v
    check("unit: the restarting is BOUNDED, or a persistent fault respawns "
          "forever on a free tier the spine also pays for",
          "StartLimitBurst" in in_unit and "StartLimitIntervalSec" in in_unit,
          [l for l in unit.splitlines() if "StartLimit" in l])
    check("unit: and the bound is a real window, not systemd's 10s default",
          int(in_unit.get("StartLimitIntervalSec", "0")) >= 600,
          in_unit.get("StartLimitIntervalSec"))
    check("unit: StartLimit* is NOT left in [Service], where it is ignored",
          not in_service, in_service)


def test_a_cap_downstream_never_exceeds_the_cap_upstream():
    """Two caps in series, and only the smaller one is real.

    2026-09-13. `HISTORY_OUTPUT_CHARS` was raised 700 -> 2400 the day before,
    against a real measurement -- the creature's tools are 706-3157 bytes and
    it was being shown them cut mid-token. The raise did nothing: `exec_end`
    had already cut stdout to 1200 on the way into the journal, so the context
    could not show what had never been stored.

    Measured cost: `plan` reached 4022 bytes, and the creature ran `cat
    tools/own/plan` six times in fifteen minutes, shown 1200 characters each
    time, never building what its cousin had asked for. From outside that is a
    creature going in circles; it was the framework showing it a third of its
    own tool.

    This is the parent's *truncation caps in series*, which CLAUDE.md §3 lists
    among the failure modes this engine does not have.
    """
    check("caps: the journal keeps at least what the context may show",
          EXEC_STDOUT_CHARS >= Engine.HISTORY_OUTPUT_CHARS,
          "journal %d < history %d" % (EXEC_STDOUT_CHARS,
                                       Engine.HISTORY_OUTPUT_CHARS))

    # And the behaviour, not just the arithmetic: a big output must survive
    # the journal and reach the served context at the HISTORY cap.
    big = "".join("line %04d padding padding padding\n" % i for i in range(120))
    check("caps: the fixture is larger than both caps, or it proves nothing",
          len(big) > Engine.HISTORY_OUTPUT_CHARS > 0, len(big))

    writes = "```bash\nprintf '%s'\n```" % "x"
    e, j, b, d = build_engine([writes], [])
    j.append("exec_start", cmd="cat tools/own/plan")
    j.append("exec_end", cmd="cat tools/own/plan", exit_code=0,
             stdout=capped(big, EXEC_STDOUT_CHARS), stderr="")
    stored = j.read(kinds=["exec_end"])[-1].get("stdout") or ""
    check("caps: the journal stored the full history window, not a third of it",
          len(stored) >= Engine.HISTORY_OUTPUT_CHARS,
          "%d stored vs %d showable" % (len(stored),
                                        Engine.HISTORY_OUTPUT_CHARS))
    shown = e.recent_block()
    check("caps: and the creature is shown far more than one screen of its tool",
          shown.count("line ") > 40, shown.count("line "))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_reply_with_no_verdict_falls_through_to_the_next_rung():
    """A reply is not automatically an answer.

    Growing Spine reached this first. Its `keychain/provider.py` returns a
    reasoning-only completion as an ERROR -- "deliberation is not an answer...
    so the keychain hops to the next window instead of handing musings to a
    parser that will scan them" -- and records the cost of not doing it: of 60
    exec_skip cycles, 21 ended on an unclosed fence, work "proposed and
    destroyed by the budget" while the journal said none was proposed.

    Measured here 2026-09-13, 15:40-18:00: gemini served the cousin 14 times
    and produced 0 usable verdicts, every one cut at `finish=length` after
    spending 94% of its budget on reasoning. groq went 2 for 2. The ladder
    banked all 14 as successes and never fell through.

    This project had already written that down: such a call "registers as a
    SUCCESS, so nothing walls the rung and nothing below it is ever reached".
    """
    good = ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\noutcome: fine\n"
            "to_creature: it worked.\nwant: a date filter\nCOUSIN")
    musing = "I have thought about this at considerable length and then stopped"

    def rung(name, text, meta):
        return (name, lambda _p: (text, dict(meta)))

    j = Journal(os.path.join(tmpdir(), "journal.jsonl"))
    ask = backends.ladder(
        [rung("talker", musing, {"done_reason": "length",
                                 "chars_before_strip": 8407,
                                 "chars_stripped": 7935}),
         rung("answerer", good, {"done_reason": "stop"})],
        journal=j, reject=cousin.unusable_reply, sleep=lambda _s: None)

    text, meta = ask("judge this")
    check("fallthrough: the rung that could not answer is passed over",
          meta.get("rung") == "answerer", meta.get("rung"))
    check("fallthrough: and the usable verdict is what comes back",
          "ACCEPTED" in text, text[:60])
    declined = [r for r in j.read(kinds=["rung_declined"])]
    check("fallthrough: the pass-over is journalled with WHY, as expected "
          "weather rather than a broken rung",
          declined and "unusable" in (declined[0].get("reason") or "")
          and declined[0].get("expected") is True,
          declined[0] if declined else "(none)")

    # THE DISCRIMINATION: the creature's ladder passes no predicate, and a
    # think with no command must still be a real answer there.
    j2 = Journal(os.path.join(tmpdir(), "journal.jsonl"))
    ask2 = backends.ladder([rung("talker", musing, {"done_reason": "stop"}),
                            rung("answerer", good, {"done_reason": "stop"})],
                           journal=j2, sleep=lambda _s: None)
    t2, m2 = ask2("think")
    check("fallthrough: with NO predicate the first rung still serves -- a "
          "creature that only looked around has answered",
          m2.get("rung") == "talker" and t2 == musing, m2.get("rung"))

    # And a reply whose block is hidden by reasoning-stripping is NOT rejected:
    # `visit` recovers it, so rejecting it would throw away a real verdict.
    hidden = cousin.unusable_reply("", {"raw_text": good, "done_reason": "stop"})
    check("fallthrough: a verdict hidden inside reasoning is not thrown away",
          hidden is None, hidden)


def test_an_unreadable_verdict_says_which_of_three_things_went_wrong():
    """One label for three faults is how a broken channel reads as weather.

    2026-09-13, live: 14 of 16 verdicts came back `no-block`. I read that as
    "the model declined to answer", called it expected on a free tier, and left
    it frozen under the tuning rule while the engine produced nothing for two
    hours. The fields had said otherwise the whole time --
    `chars_before_strip=8407`, `chars_stripped=7935`, `finish=length`: the
    model wrote 8,400 characters, 94% of them reasoning, and was cut off before
    the block the contract puts LAST.

    The think side has kept these apart since the kernel's first week. This is
    the same discrimination on the cousin side.
    """
    w = cousin.why_unreadable

    check("unreadable: a COMPLETE reply with no block is the model's own choice",
          w("stop", 900, 0) == "no-block", w("stop", 900, 0))
    check("unreadable: cut off with little reasoning is TRUNCATION, not silence",
          w("length", 4000, 100) == "truncated-before-block",
          w("length", 4000, 100))
    check("unreadable: cut off after mostly reasoning is its own fault, "
          "because raising the budget does not fix it",
          w("length", 8407, 7935) == "reasoning-ate-the-budget",
          w("length", 8407, 7935))
    check("unreadable: unknown finish falls back to no-block, never to a guess",
          w(None, None, None) == "no-block", w(None, None, None))

    # End to end: the label must survive into the journal, or the next reader
    # is back to reading a summary that cannot be re-interrogated.
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    long_reply = "I reasoned about this at length. " * 20   # no verdict block
    cousin.visit(lambda _p: (long_reply, {"model": "m", "rung": "r",
                                          "done_reason": "length",
                                          "chars_before_strip": 8407,
                                          "chars_stripped": 7935}),
                 "brief", "c", "h", "t", journal=j)
    rec = j.read(kinds=["cousin_verdict"])[0]
    check("unreadable: the journal carries the distinguishing label",
          rec.get("error") == "reasoning-ate-the-budget", rec.get("error"))
    check("unreadable: and still keeps the evidence behind it",
          rec.get("chars_stripped") == 7935 and rec.get("finish") == "length",
          {k: rec.get(k) for k in ("chars_stripped", "finish")})
    shutil.rmtree(d, ignore_errors=True)


def test_a_fence_inside_the_code_does_not_close_the_block():
    """The framework cut the creature's command at a backtick run in its source.

    `FENCE_RE` closed on ANY run of three backticks, non-greedy. Measured
    2026-09-13/14 on the live run: the creature wrote `subagent-orchestrator`,
    whose job is stripping markdown fences off an LLM reply, so its source
    contains a startswith() against a fence literal. That inner run closed the
    bash block early, the heredoc never terminated, and the file landed cut
    mid-string -- "SyntaxError: unterminated string literal", line 68.

    **Twelve SyntaxErrors across twelve rewrites over nine hours.** Each time
    the creature read a syntax error in its own file and rewrote the tool; each
    time we cut it at the same character. It could not see the cut: the
    transcript shows what RAN, and what ran was the truncated command.

    A tool that manipulates fences is exactly the tool this made impossible to
    write, which is why it went round twelve times instead of being noticed.
    """
    F = chr(96) * 3
    reply = (
        "I will write the tool.\n\n"
        + F + "bash\n"
        "cat > tools/own/orch <<'EOF'\n"
        "def strip(text):\n"
        '    if text.startswith("' + F + '"):\n'
        "        text = text[3:]\n"
        "    return text\n"
        "EOF\n"
        "chmod +x tools/own/orch\n"
        + F + "\n")

    blocks = think.parse_blocks(reply)
    check("fence: exactly one command block, not a fragment of one",
          len(blocks) == 1, len(blocks))
    check("fence: the heredoc SURVIVES to its terminator",
          blocks and "EOF" in blocks[0], repr(blocks[0][-60:]) if blocks else None)
    check("fence: and the command after it survives too",
          blocks and blocks[0].rstrip().endswith("chmod +x tools/own/orch"),
          repr(blocks[0][-40:]) if blocks else None)
    check("fence: the fence literal the creature was writing is intact",
          blocks and ('startswith("' + F + '")') in blocks[0],
          "the literal was cut")

    # THE REGRESSION THIS TEST DID NOT HAVE, caught live 40 minutes after the
    # anchor shipped. The model closed a reasoning tag and opened the block on
    # the SAME LINE, so an anchored OPENER never matched and the creature's one
    # command was dropped -- the framework discarding work, by a fix meant to
    # stop the framework discarding work. Only the CLOSING fence is anchored.
    glued = ("thinking out loud</thought>" + F + "bash\n"
             'cat "$MIND/tools/own/plan"\n' + F + "\n")
    check("fence: a block opened mid-line still runs",
          think.parse_blocks(glued) == ['cat "$MIND/tools/own/plan"'],
          think.parse_blocks(glued))

    # Two real blocks must still be two, or the anchor has made it greedy.
    two = (F + "bash\nls\n" + F + "\n\ntext\n\n" + F + "bash\npwd\n" + F + "\n")
    check("fence: two blocks are still two, not one greedy run",
          think.parse_blocks(two) == ["ls", "pwd"], think.parse_blocks(two))

    # An unclosed fence is still LOST work, counted on LINE-START runs so that
    # a fence inside a string is not mistaken for an unbalanced block.
    reason, _ = think.classify_no_blocks("text\n\n" + F + "bash\nls\n")
    check("fence: a genuinely unclosed block is still reported as LOST",
          reason == "unclosed_fence" and think.commands_were_lost(reason), reason)
    balanced = 'print("' + F + '")\n'
    check("fence: a fence inside a line is NOT an unclosed block",
          think.classify_no_blocks(balanced)[0] != "unclosed_fence",
          think.classify_no_blocks(balanced)[0])


def test_a_usage_refusal_is_not_counted_as_a_failure():
    """The run-record was reporting a healthy library as a broken one.

    2026-09-14, measured over 153 probes: 39 exited 0, **97 were the tool
    correctly refusing incomplete input**, and only about 12 were real
    failures. `evidence()` invokes every tool BARE, with no arguments, so a
    tool whose own call-line says it takes some can never exit 0 -- and the
    brief tells the cousin in as many words that a tool which refuses
    incomplete input and says what it needs has done its job.

    The display I had shipped two hours earlier counted all 114 non-zero exits
    as failures, so `plan` read as "1 worked and 30 failed" when thirty of
    those were it correctly asking for an argument. I then read a creature
    "building storeys on a broken floor" out of a number the harness
    manufactures, and wrote it into doctrine and two prompts.

    That is the project's own scar, top of §5: **before believing a
    behavioural finding about either agent, prove the harness was not
    producing it.** The framework already knew -- `evidence()` computes
    `needs_args` and even tells the cousin "I called it with NO ARGUMENTS" --
    it simply never wrote it down.
    """
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "needy", does="does a thing", call="needy <id>")
    _write_tool(own, "broken", does="does a thing")
    j = Journal(os.path.join(d, "journal.jsonl"))

    # A tool that asked for its argument, thirty times, plus one real run.
    j.append("cousin_probe", tool="needy", exit_code=0, bare=False,
             stdout="ok", stderr="")
    for _ in range(3):
        j.append("cousin_probe", tool="needy", exit_code=2, bare=True,
                 stdout="", stderr="usage: needy <id>")
    # A tool that really failed, called the only way it can be called.
    for _ in range(2):
        j.append("cousin_probe", tool="broken", exit_code=1, bare=False,
                 stdout="", stderr="Traceback ...")

    hist = library.use_history(j)
    check("bare: an argument-refusal is counted separately, not as a failure",
          hist["needy"]["asked"] == 3 and hist["needy"]["ok"] == 1,
          hist.get("needy"))
    check("bare: a real failure is still a failure",
          hist["broken"]["ok"] == 0 and hist["broken"].get("asked", 0) == 0,
          hist.get("broken"))

    out = library.render(own, j)
    needy_line = [l for l in out.splitlines() if "asked for arguments" in l]
    check("bare: the tool that always asked is NOT reported as failing",
          needy_line and "FAILED" not in needy_line[0], needy_line)
    check("bare: and the one that really fails still says NEVER WORKED",
          "NEVER WORKED" in out, out)

    # THE DISCRIMINATION: without the bare flag the two are indistinguishable,
    # which is exactly the state that produced the wrong reading.
    j2 = Journal(os.path.join(d, "j2.jsonl"))
    for _ in range(3):
        j2.append("cousin_probe", tool="needy", exit_code=2,
                  stdout="", stderr="usage: needy <id>")
    h2 = library.use_history(j2)["needy"]
    check("bare: with no flag recorded, a refusal cannot be told from a "
          "failure -- which is why the flag has to be written at probe time, "
          "not guessed later",
          h2.get("asked", 0) == 0, h2)
    # And the record SAYS it cannot tell, rather than calling it a failure:
    # every probe of the first day and a half predates the flag, and a
    # display that counted them as failures would show both inhabitants a
    # broken library that was never measured to be one.
    check("bare: a probe recorded before the flag is UNQUALIFIED, never a failure",
          h2.get("unqualified", 0) == 3, h2)
    out2 = library.render(own, j2)
    check("bare: and the listing says the outcome is unknown, not FAILED",
          "unknown outcome" in out2 and "FAILED" not in out2
          and "NEVER WORKED" not in out2, out2)

    shutil.rmtree(d, ignore_errors=True)


def test_the_creature_is_told_to_repair_rather_than_delete_or_panic():
    """Making the failures visible created a second risk, named by Tue before
    it bit: twelve tools now read "NEVER WORKED" in the same context.

    Two wrong readings were available and neither was ruled out. Delete the red
    ones -- which throws away everything already understood about the problem,
    so the replacement meets the same wall from the same standing start. Or fix
    all twelve now -- which is a dozen jobs due at once and is how a cycle
    dissolves into thrash.

    The want channel already serialises REQUESTS: the brief forbids asking for
    the thing you were promised, so a broken tool produces a refusal about that
    one tool, as the cousin actually walks into it. What was missing was the
    creature's posture toward the CATALOGUE, which is the framework speaking
    and shows every failure at once.

    Stating a working posture is not telling the creature about its own bugs
    (§2.4) -- that rule is about diagnosing a specific fault for it, which
    nothing here does.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brief = io.open(os.path.join(root, "CREATURE-PROMPT.md"),
                    encoding="utf-8").read()
    low = brief.lower()
    check("creature: a failing tool is unfinished work, not rubbish",
          "unfinished, not rubbish" in low, "not stated")
    check("creature: and deleting it is named as the loss it is",
          "throws away everything you already understood" in low, "not stated")
    check("creature: repair is ONE AT A TIME, so a red catalogue is not a "
          "dozen jobs due this cycle",
          "repair one at a time" in low and "map, not a queue" in low,
          "not stated")
    check("creature: and the one to repair is the one its user walked into",
          "actually in your cousin" in low, "not stated")
    check("creature: build the floor before the next storey",
          "not the next storey" in low, "not stated")
    # The escape hatch: consolidation is still allowed, or the anti-delete rule
    # would forbid the one good removal this creature has ever made.
    check("creature: folding a tool into another and removing the dead one is "
          "still permitted",
          "genuinely been replaced" in low, "not stated")


def test_a_tool_that_never_worked_says_so_to_both_inhabitants():
    """A broken floor was being shown to both agents as a sound one.

    Until 2026-09-14 the library line read "its user ran this 31 times; the
    last run exited 1" -- true, and useless. A tool that has NEVER ONCE worked
    rendered identically to one that works and failed once. Measured live the
    same day: `plan` returned 0 on its first probe and non-zero on the thirty
    after it; `integrate-subagent-orchestrator-with-plan` had failed eight
    times and succeeded twice and read as "the last run exited 0". Across the
    run, 39 of 148 probes exited 0.

    That is this project's oldest fault -- a display that cannot distinguish
    the thing it measures -- committed inside the column built to make exactly
    this visible, which is why the assertion is on the RECORD and not on the
    wording.

    The brief's second test now leans on this evidence, so the evidence has to
    arrive: a rule cannot reason about what the harness never put on the page
    (§5, the library scar).
    """
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "floor", does="stores the things")
    _write_tool(own, "storey", does="reads what floor stored")
    j = Journal(os.path.join(d, "journal.jsonl"))

    # `bare=False`: called properly and failed. A probe without the flag is
    # UNQUALIFIED, not a failure -- see test_a_usage_refusal_is_not_counted.
    for code in (2, 2, 2):
        j.append("cousin_probe", tool="floor", exit_code=code, bare=False,
                 stdout="", stderr="boom")
    for code in (0, 1):
        j.append("cousin_probe", tool="storey", exit_code=code, bare=False,
                 stdout="ok", stderr="")

    out = library.render(own, j)
    check("floor: a tool that never worked is not shown as merely 'last failed'",
          "NEVER WORKED" in out, out)
    # FAILED is capitalised since 2026-09-14: it now means a real failure,
    # not a tool that was called bare and asked for its arguments.
    check("floor: and the mixed one reports BOTH halves of its record",
          "1 worked and 1 FAILED" in out, out)
    check("floor: a clean record still reads as clean",
          "NEVER WORKED" not in out.split("- storey")[1], out)

    hist = library.use_history(j)
    check("floor: the record counts successes, not just attempts",
          hist["floor"]["runs"] == 3 and hist["floor"]["ok"] == 0,
          hist.get("floor"))

    # The evidence must reach the CREATURE too -- it is the one that would
    # otherwise keep building storeys on it.
    e, j2, b, d2 = build_engine(["thinking"], [])
    own2 = os.path.join(b.mind, "tools", "own")
    _write_tool(own2, "floor", does="stores the things")
    for _ in range(3):
        j2.append("cousin_probe", tool="floor", exit_code=2, bare=False,
                  stdout="", stderr="boom")
    check("floor: the creature is shown it every wake, not just the cousin",
          "NEVER WORKED" in e.serve_context(), e.serve_context()[-400:])
    b.destroy(); shutil.rmtree(d2, ignore_errors=True)
    shutil.rmtree(d, ignore_errors=True)


def test_the_brief_tests_whether_the_handover_could_be_completed():
    """The guardrail is prose, because in this engine guardrails are prose.

    Growing Spine would have built this as a framework gate. Here the 99% that
    was Python is the cousin's brief, so the rule against accepting a storey
    built on a floor that fails belongs in the brief -- and per §1 a change to
    it is a behaviour change that needs a test that fails without it.

    This asserts the invariant is STATED and that its escape hatch is stated
    with it: a rule that could refuse everything downstream of one broken tool
    would stall the creature completely, which is the "right in isolation,
    harmful in company" scar.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    brief = io.open(os.path.join(root, "MANAGER-PROMPT.md"),
                    encoding="utf-8").read()
    tests = brief.split("## The five tests", 1)[1].split("## How you speak", 1)[0]
    check("brief: the second test asks whether the handover could be COMPLETED, "
          "not only whether the tool starts",
          "help you" in tests and "leans on" in tests, tests[:200])
    check("brief: it is framed as the cousin's own experience, never a "
          "diagnosis of the creature's code",
          "not a diagnosis" in tests, tests[:200])
    check("brief: and it carries its own limit, so one broken tool cannot "
          "refuse everything downstream of it",
          "did its job" in tests, tests[:200])


def test_a_want_survives_until_the_creature_has_had_a_turn():
    """Direction was being discarded before its recipient ever saw it.

    Measured 2026-09-14 over twenty hours on one unmodified build: **50 wants
    issued, 29 retired with no tool written in between.** The first version of
    the discharge rule retired a want on the next ANSWERED VISIT, whatever
    that visit was about. The objection was written into its own docstring
    when it shipped and chosen against; with n=50 it stopped being an
    objection and became the behaviour.

    The original fault is still fixed: a want that stands forever is re-served
    every wake and the creature re-runs the same commands at it. But *acted
    on* is the honest test for that, not *answered*.
    """
    acc = ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\noutcome: fine\n"
           "to_creature: it worked.\nwant: a date filter\nCOUSIN")
    ret = ("<<<COUSIN\nverdict: RETURNED\ntried: ran it\noutcome: crashed\n"
           "to_creature: it stopped with an error.\nCOUSIN")
    done = "```bash\nremember current-phase done\n```"
    build = ("```bash\ncat << 'SH' > tools/own/thing\n#!/bin/sh\n"
             "# does: a thing\necho hi\nSH\nchmod +x tools/own/thing\n```")

    # 1. THE REGRESSION: want issued, creature never writes anything, a later
    #    visit answers about something else. The want must SURVIVE.
    e, j, b, d = build_engine([done, done], [acc("") if False else acc, ret])
    e.run_cycle()
    check("want: it stands once issued", e.wants() == ["a date filter"],
          str(e.wants()))
    e.run_cycle()
    check("want: an answered visit does NOT discharge a want the creature "
          "never had a turn at",
          e.wants() == ["a date filter"], str(e.wants()))
    check("want: and nothing is journalled as discharged",
          dict(j.kinds()).get("want_retired") is None, dict(j.kinds()))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)

    # 2. Once the creature HAS built something, the want is spent and an
    #    answered visit clears it -- which is the original fault, still fixed.
    e, j, b, d = build_engine([done, build, done], [acc, ret, ret])
    e.run_cycle()                      # want issued
    e.run_cycle()                      # creature writes a tool
    check("want: acting on it is recorded", e.want_was_acted_on(),
          "no TOOL_WRITE seen")
    e.run_cycle()                      # answered visit, nothing new asked
    check("want: a want the creature has built against IS discharged",
          e.wants() == [], str(e.wants()))
    rec = j.read(kinds=["want_retired"])[-1]
    check("want: and the record says it was acted on first",
          "acted on" in (rec.get("because") or ""), rec.get("because"))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)

    # 3. Supersession is untouched: a newer want replaces the old one whether
    #    or not the creature ever acted, because the cousin has moved on.
    e, j, b, d = build_engine([done, done], [acc, acc2()])
    e.run_cycle(); e.run_cycle()
    check("want: a NEWER want still replaces the old one, acted on or not",
          e.wants() == ["a tag filter"], str(e.wants()))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def acc2():
    return ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\noutcome: fine\n"
            "to_creature: it worked.\nwant: a tag filter\nCOUSIN")


def test_a_want_is_discharged_by_the_visit_that_answers_it():
    """A want had no completion signal and was re-served forever.

    2026-09-13: it was written into the managed context and stayed until three
    NEWER wants pushed it out -- and new wants only arrive on an accept. So
    between accepts the creature was handed the same direction every wake with
    no way to mark it done, and it spent a run of cycles re-running `plan goal
    / plan add / plan list` against a standing "add a task to the plan".

    The trigger scar one level up: *a trigger that does not reset its own
    counter fires forever*. A visit is the ANSWER to what summoned it, and now
    to what was standing when it arrived.
    """
    def acc(w):
        return ("<<<COUSIN\nverdict: ACCEPTED\ntried: ran it\noutcome: fine\n"
                "to_creature: I used it and it worked.\nwant: %s\nCOUSIN" % w)
    ret = ("<<<COUSIN\nverdict: RETURNED\ntried: ran it\noutcome: crashed\n"
           "to_creature: it stopped with an error before printing anything.\n"
           "COUSIN")
    unusable = "I thought about this at length but never said anything usable."

    done = "```bash\nremember current-phase done\n```"

    # 1. An accept replaces what was standing rather than stacking on it.
    e, j, b, d = build_engine([done] * 2, [acc("a date filter"),
                                           acc("a tag filter")])
    e.run_cycle()
    check("want: the first want stands", e.wants() == ["a date filter"],
          str(e.wants()))
    e.run_cycle()
    check("want: a newer want REPLACES the old one, never stacks",
          e.wants() == ["a tag filter"], str(e.wants()))
    check("want: and the discharge is journalled under its own kind",
          dict(j.kinds()).get("want_retired") == 1, dict(j.kinds()))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)

    # 2. CORRECTED 2026-09-14. This asserted that a RETURNED discharges
    #    whatever was standing, full stop -- and that was the shipped
    #    behaviour until 50 wants had been issued and 29 of them retired with
    #    the creature never having written a thing. A visit answers the TOOL
    #    it was sent to; it does not answer a request nobody acted on.
    #
    #    So a RETURNED now discharges only a want the creature has already
    #    had a turn at. The build step below is what makes that true, and
    #    removing it is the red-proof for the whole change.
    build = ("```bash\ncat << 'SH' > tools/own/thing\n#!/bin/sh\n"
             "# does: a thing\necho hi\nSH\nchmod +x tools/own/thing\n```")
    e, j, b, d = build_engine([done, build, done],
                              [acc("a date filter"), ret, ret])
    e.run_cycle(); e.run_cycle(); e.run_cycle()
    check("want: a RETURNED discharges a want that was acted on",
          e.wants() == [], str(e.wants()))
    rec = j.read(kinds=["want_retired"])[-1]
    check("want: the discharge says WHY, not just that it happened",
          "RETURNED" in (rec.get("because") or ""), rec.get("because"))
    check("want: and keeps the text, so a discarded direction is recoverable",
          rec.get("texts") == ["a date filter"], rec.get("texts"))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)

    # 3. THE DISCRIMINATION: a visit that produced nothing usable is not an
    #    answer. Retiring on it would let a bad reply silently erase the only
    #    direction the creature has -- an UNKNOWN gates nothing, here too.
    e, j, b, d = build_engine([done] * 2, [acc("a date filter"), unusable])
    e.run_cycle(); e.run_cycle()
    check("want: an UNANSWERED visit retires nothing -- nobody spoke",
          e.wants() == ["a date filter"], str(e.wants()))
    check("want: and nothing is journalled as discharged",
          dict(j.kinds()).get("want_retired") is None, dict(j.kinds()))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_quoted_text_in_a_bare_fence_is_not_a_command():
    """An untagged fence is not an action, and running one invents work.

    2026-09-13, from the first raw think reply this journal ever kept. The
    creature quoted a tool's OUTPUT in a bare fence while reasoning about it,
    and the framework ran it. Exit 2. In the NEXT reply it read that
    manufactured failure out of its own transcript and concluded *"This
    happened because the cousin probably copied the output of a tool and tried
    to run it as a script"* -- a false belief about the other agent,
    manufactured by us and delivered as evidence.

    `CREATURE-PROMPT.md` says it twice: commands are ```bash blocks, and the
    prompt's own tool-header example is a BARE fence that is plainly not one.
    The creature was following its contract. The parser was not.
    """
    live = (
        "```\n"
        "Tasks sorted by priority (Goal: Organize weekly research tasks):\n"
        "1. [10] (Index 1) Implement a memory archive\n"
        "```\n"
        "It seems to be working.\n\n"
        "Let's examine the tool.\n\n"
        "```bash\ncat tools/own/prioritize\n```")

    blocks = think.parse_blocks(live)
    check("fence: quoted output in a bare fence is not run",
          all("Tasks sorted by priority" not in b for b in blocks), blocks)
    check("fence: the tagged block in the same reply still is",
          blocks == ["cat tools/own/prioritize"], blocks)

    # The prompt TEACHES a bare fence, so this is not a hypothetical shape.
    header = "```\n#!/usr/bin/env python3\n# tool: x\n# does: y\n```"
    check("fence: the prompt's own tool-header example is not a command",
          think.parse_blocks(header) == [], think.parse_blocks(header))

    check("fence: ```sh still counts, the tag is required not the word bash",
          think.parse_blocks("```sh\nls\n```") == ["ls"])

    # A reply that used to run and now does not must SAY so. A change that
    # silently stops doing something looks exactly like a model that stopped
    # asking for it.
    reason, detail = think.classify_no_blocks(header)
    check("fence: an untagged-only reply gets its own reason, not no_command",
          reason == "untagged_fence", reason)
    check("fence: and that is not counted as commands LOST",
          not think.commands_were_lost(reason), reason)


def test_a_think_keeps_the_reply_that_produced_it():
    """The counterpart of `test_an_unreadable_verdict_keeps_its_evidence`.

    2026-09-13, live: a cycle ran three command blocks, two of which were the
    creature's own transcript pasted back into a fence -- `| exit 0` sent to
    bash. Which agent produced that decides everything. A framework extracting
    commands the creature never fenced is the worst fault this design has; a
    creature copying its own context is ordinary confusion nobody may touch.

    The journal held `chars` and `finish` and nothing else, so the question was
    answerable only by reading `FENCE_RE` in the source -- which is not an
    answer the next reader can reproduce from the log. A summary cannot be
    re-interrogated when the summary is what is wrong.
    """
    reply = ("Looking at my library.\n\n```bash\nls -l tools/own/\n```\n"
             "and then the thing I pasted by mistake\n\n```bash\n| exit 0\n```")
    e, j, b, d = build_engine([reply], [])
    e.run_cycle()

    rec = j.read(kinds=["think"])[0]
    check("think evidence: the reply itself survives the cycle",
          "| exit 0" in (rec.get("raw") or ""), sorted(rec.keys()))
    check("think evidence: enough of it to see which blocks were fenced",
          rec.get("raw", "").count("```") >= 4, repr(rec.get("raw"))[:160])
    check("think evidence: the summary fields are kept too, not replaced",
          rec.get("chars") == len(reply), rec.get("chars"))


def test_library_marks_a_tool_its_user_has_never_run():
    """The tested/untested column, decided 2026-09-13 (Tue).

    Placement matters more than the string: the cousin RUNS the test, and
    nothing ENFORCES it. A cousin that could withhold a tool would be a second
    builder (CLAUDE.md §2.3) and a second judge with no judge of its own. So
    the framework records who ran what and shows it; neither agent gets a
    gate.
    """
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "taskprio", does="orders tasks")
    j = Journal(os.path.join(d, "journal.jsonl"))

    out = library.render(own, j)
    check("library column: an untouched tool says so plainly",
          "NEVER run" in out, out)

    j.append("cousin_probe", tool="taskprio", exit_code=0,
             stdout="ok", stderr="")
    out2 = library.render(own, j)
    check("library column: once its user runs it, that replaces never-run",
          "NEVER run" not in out2 and "ran this once" in out2, out2)
    # Updated 2026-09-14 with the record change: a single clean run now reads
    # as "it worked", which carries the same fact as "exited 0" and survives
    # the case this assertion could not see -- a tool that has run many times
    # and never once succeeded.
    check("library column: and reports that the run actually succeeded",
          "it worked" in out2 and "NEVER WORKED" not in out2, out2)

    j.append("cousin_probe", tool="taskprio", exit_code=1, bare=False,
             stdout="", stderr="boom")
    out3 = library.render(own, j)
    check("library column: the LAST run is what is reported, not the best one",
          "exited 1" in out3 and "ran this 2 times" in out3, out3)


def test_library_counts_only_its_users_runs():
    """The discrimination test, and the reason this file is worth having.

    The creature runs its own tools constantly while writing them. Counting
    that would mark every tool exercised the moment it existed -- a column
    that reports a clean-looking wrong number rather than an error, which is
    the oldest scar in CLAUDE.md §5 and one I have now written four times.

    Verified red before green: with `exec_end` included in `use_history` the
    first assertion fails, which is what makes the second one mean anything.
    """
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "fetch", does="gets a page")
    j = Journal(os.path.join(d, "journal.jsonl"))

    # The creature running its own tool, twice, successfully.
    j.append("exec_start", cmd="fetch http://x")
    j.append("exec_end", cmd="fetch http://x", exit_code=0)
    j.append("exec_end", cmd="fetch http://y", exit_code=0)

    out = library.render(own, j)
    check("library column: the author running its own tool is NOT a test of it",
          "NEVER run" in out, out)

    j.append("cousin_probe", tool="fetch", exit_code=0, stdout="", stderr="")
    check("library column: its user running it IS",
          "NEVER run" not in library.render(own, j), library.render(own, j))


def test_library_never_withholds_a_tool_that_failed():
    """Visibility, never a gate.

    A failing verdict must not remove a tool from the library or from PATH.
    If it could, the cousin would hold a write path into the creature's world
    without ever touching a file, and a bad model day would wall working work
    the creature could not route around.
    """
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "archive", does="stores a note")
    j = Journal(os.path.join(d, "journal.jsonl"))
    j.append("cousin_probe", tool="archive", exit_code=127, bare=False,
             stdout="", stderr="not found")

    out = library.render(own, j)
    check("library column: a tool its user could not run is STILL listed",
          "archive" in out and "exited 127" in out, out)
    check("library column: and is still a tool as far as the kernel is concerned",
          "archive" in triggers.list_tools(own), triggers.list_tools(own))


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _docs():
    root = _repo_root()
    out = {}
    # PLAN.md carries status too, so it is held to the same rule. A fourth
    # document with its own number is exactly how this drifted before.
    for name in ("README.md", "CLAUDE.md", "ARCHITECTURE.md", "PLAN.md"):
        p = os.path.join(root, name)
        if os.path.exists(p):
            out[name] = io.open(p, encoding="utf-8").read()
    return out


def _doc_head(text):
    """The CURRENT-tense part of a document. Everything after the first
    "Previous state" heading is a dated record of what was true then, and a
    rule applied to history rewrites history."""
    return text.split("### Previous state", 1)[0]


def _open_question(n):
    """One numbered item out of CLAUDE.md §6, by its number."""
    docs = _docs()
    txt = docs.get("CLAUDE.md", "")
    if "## 6. Open questions" not in txt:
        return ""
    txt = txt.split("## 6. Open questions", 1)[1].split("\n## 7.", 1)[0]
    parts = re.split(r"^(\d+)\. ", txt, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        if parts[i] == str(n):
            return parts[i + 1]
    return ""


def _paragraphs(text):
    """Blank-line-separated blocks with their wrapping flattened. Markdown
    wraps prose at 79 columns, so a line-based check reads a sentence as
    fragments and passes on where the break happened to fall -- which is how
    the first version of the check below passed by accident."""
    return [re.sub(r"\s+", " ", p).strip()
            for p in re.split(r"\n\s*\n", text) if p.strip()]


def test_the_chat_channel_is_a_scheduled_intention():
    """PLAN item 2. It has sat in every "not built" list since 2026-09-11
    without ever being decided either way, which is the difference §4 draws
    between a hold with a named trigger and inaction in the costume of
    caution. Tue, 2026-09-16: it stays.

    **This check was rebuilt after an independent verification broke its
    first version three ways** -- rewriting the commitment to "remains an open
    question; nobody has decided", restating the absence with synonyms the
    blacklist did not carry, and renumbering the plan so the cross-reference
    pointed at a different item -- each time with a fully green gate. A
    blacklist of phrases defends the phrases. What is asserted now is an
    INVARIANT: every current-tense mention commits, and the number it cites
    really is the chat channel's item on the board.

    History is left alone: the "Previous state" sections record that it did
    not exist then, and that remains true of then.
    """
    docs = _docs()
    plan = docs.get("PLAN.md", "")
    check("chat: the board exists to be cross-referenced", bool(plan.strip()),
          "(no PLAN.md -- it must be committed, or a fresh clone fails here)")
    want = ("wanted", "stays", "scheduled", "will be built")
    uncommitted, cited = [], set()
    for name, text in docs.items():
        if name == "PLAN.md":
            continue
        for p in _paragraphs(_doc_head(text)):
            low = p.lower()
            if "chat channel" not in low:
                continue
            m = re.search(r"item (\d+)", low)
            if not (any(w in low for w in want) and m):
                uncommitted.append("%s: %s" % (name, p[:110]))
            elif m:
                cited.add(int(m.group(1)))
    check("chat: every current-tense mention of it commits -- a want-word and "
          "the item that carries it", not uncommitted, str(uncommitted)[:300])
    check("chat: and at least one document says so where a maintainer reads",
          bool(cited), "no current-tense mention cites an item at all")
    for n in sorted(cited):
        m = re.search(r"^###\s*%d\.\s*(.+)$" % n, plan, re.M)
        check("chat: the item the docs cite (%d) really is the chat channel's "
              "on the board" % n,
              m is not None and "chat channel" in m.group(1).lower(),
              m.group(1) if m else "(PLAN has no item %d)" % n)
    reason = [p for name, text in docs.items()
              for p in _paragraphs(_doc_head(text))
              if "chat channel" in p.lower() and "measur" in p.lower()
              and ("surface" in p.lower() or "context" in p.lower())]
    check("chat: the REASON for the slot is recorded, not just the slot -- it "
          "adds a surface to the creature's context and must not arrive "
          "mid-measurement", bool(reason), "no document gives the reason")


def test_the_inherited_library_is_recorded_as_not_executed():
    """PLAN item 3. §6.2 says "Decided 2026-09-10: copy". Run 2 started from
    nothing, so the doctrine claims a thing that never happened -- and the
    refutation path it was chosen for, a known-answer test set, was never
    taken. Either execute it or say plainly that it was not."""
    q = _open_question(2)
    check("inherited: §6.2 exists to be judged", bool(q.strip()), q[:80])
    low = q.lower()
    check("inherited: it records that the decision was NOT executed",
          "not executed" in low or "never executed" in low, q[:300])
    check("inherited: and binds it to run 3, with a number rather than 'later'",
          "run 3" in low, q[:300])
    # The tagging requirement is asserted on the BOARD, not here: §6.2 has
    # carried the words "tagging every inherited tool" since 2026-09-10, so a
    # check for them in §6.2 was green before this work and could never have
    # been seen red -- a tautology, found by an independent verification.
    plan = _docs().get("PLAN.md", "")
    item11 = re.search(r"^###\s*11\.[^\n]*\n(.*?)(?=^###\s|\Z)", plan,
                       re.M | re.S)
    body = re.sub(r"\s+", " ", item11.group(1)).lower() if item11 else ""
    check("inherited: the run that will execute it carries the tagging "
          "requirement, or the run measures a mixture and reports one number",
          "tag" in body and ("t=0" in body or "split" in body),
          body[:200] or "(PLAN has no item 11)")
    check("inherited: and ARCHITECTURE agrees rather than still calling it the "
          "plan of record -- two documents disagreeing about what happened is "
          "the 2026-09-13 review's finding",
          "never done" in _docs().get("ARCHITECTURE.md", "").lower(),
          "ARCHITECTURE §11 does not record that it was never done")


def test_the_cousins_audit_has_a_named_trigger():
    """PLAN item 4. §6.4 ended "No named trigger yet -- this needs one", and
    §4 is explicit that a hold without a named trigger is inaction wearing
    caution's clothes."""
    q = _open_question(4)
    check("audit: §6.4 exists to be judged", bool(q.strip()), q[:80])
    low = q.lower()
    check("audit: the placeholder is gone", "no named trigger yet" not in low,
          q[:300])
    check("audit: a trigger is named, and it is the one that makes an audit "
          "mean anything -- the cousin being able to invoke tools with "
          "arguments", "item 9" in low and "argument" in low, q[:300])


def test_the_evidence_tarballs_home_is_recorded():
    """PLAN item 5. Tue, 2026-09-16: the tarball stays on the laptop; the
    repo carries the hashed manifest. §0 hedged it as still open."""
    head = _doc_head(_docs().get("CLAUDE.md", ""))
    check("tarball: §0 no longer defers the decision",
          "beyond the laptop is tue's decision" not in head.lower(), "")
    check("tarball: and says plainly where it lives",
          re.search(r"tarball[^.]{0,120}stays on the laptop", head, re.I | re.S)
          is not None, "")
    # BOTH documents, because the criterion names both: an operator meets
    # `deploy/README.md`, never §0.
    dep = io.open(os.path.join(_repo_root(), "deploy", "README.md"),
                  encoding="utf-8").read()
    check("tarball: and the operator's document says it too",
          re.search(r"tarball[^.]{0,160}stays on the laptop", dep, re.I | re.S)
          is not None, "deploy/README.md does not say where a pack lives")
    # GIT ITSELF, not a pattern I typed. The old check grepped .gitignore for
    # the literal line, which says nothing about whether git would actually
    # refuse the file -- a producer and a checker each holding their own copy.
    root = _repo_root()

    def ignored(rel):
        try:
            r = subprocess.run(["git", "-C", root, "check-ignore", "-q", rel],
                               capture_output=True, timeout=15)
            return r.returncode == 0
        except Exception:
            return None
    tar = ignored("evidence/run-2-20260915-0054.tar.gz")
    man = ignored("evidence/run-2-20260915-0054.manifest.json")
    if tar is None:
        check("tarball: git could not be asked -- unproven, not assumed", False,
              "no git here")
    else:
        check("tarball: git itself refuses a pack tarball under evidence/", tar)
        check("tarball: and does NOT refuse the manifest, which is the whole "
              "point of committing one", man is False, man)


def test_no_document_hard_codes_the_gate_count():
    """Four documents once carried four different gate counts, all wrong.

    At one HEAD on 2026-09-13: ARCHITECTURE said 90/90 and "nothing deployed",
    CLAUDE.md said 242/242, README said 340/340, and the gate was at 348 -- the
    README having been "repaired" 21 minutes earlier. Found by an outside
    review. A count in prose is a constant nobody chose, obeyed forever, which
    is the first fault this project's own doctrine names.

    **This is a smoke alarm, not a proof.** It flags a CURRENT-tense gate count
    in a status position, and deliberately does not flag: dated history, a
    "Previous state" section, or the trial's own scores, which are evidence
    rather than status. The first version of it flagged all three and produced
    fourteen false alarms -- a checker that cannot distinguish the thing it
    measures, for the fifth time in two days, so it is worth saying plainly
    what this one does NOT catch.
    """
    pat = re.compile(r"\b(\d{2,4})\s*/\s*\1\b")
    for name, text in _docs().items():
        # History lives after the first "Previous state" heading; a count there
        # is a record of what was true then.
        head = text.split("### Previous state", 1)[0]
        for line in head.splitlines():
            m = pat.search(line)
            if not m or "gate" not in line.lower():
                continue
            if int(m.group(1)) < 20:        # trial scores, hook self-tests
                continue
            low = line.lower()
            # NO blockquote exemption: the status blocks in these documents
            # ARE blockquotes, so exempting them let a hard-coded "348/348"
            # straight through on the first red-proof. Past tense and a date
            # are what mark evidence; a quote marker marks nothing.
            past = (" was " in low or "used to" in low or "2026-" in line)
            check("docs: %s states a live gate count (%s) -- run the gate "
                  "instead" % (name, m.group(0)), past, line.strip()[:110])


def test_the_module_list_matches_the_kernel():
    """CLAUDE.md and README said "eight modules" over a kernel of ten.

    Cheap to assert, and it is the shape this project keeps paying for: a
    checker that distinguishes beats a sentence that was true once.
    """
    root = _repo_root()
    mods = sorted(f[:-3] for f in os.listdir(os.path.join(root, "kernel"))
                  if f.endswith(".py") and f != "__init__.py")
    check("kernel: there are modules to check at all", len(mods) >= 5, mods)

    words = {8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
    right = words.get(len(mods))
    for name, text in _docs().items():
        for line in text.splitlines():
            low = line.lower()
            if "modules" not in low:
                continue
            wrong = [w for n, w in words.items()
                     if w in low and n != len(mods)]
            check("docs: %s counts the kernel's modules correctly "
                  "(%d = %s)" % (name, len(mods), right),
                  not wrong, line.strip()[:110])


def test_the_journal_names_the_engine_that_wrote_it():
    """Every production figure must name its run -- and the journal could not.

    2026-09-14: `loop_start` carried `pause` and `max_cycles`. The engine was
    restarted twenty-three times during run 2, and the only way to say which
    code produced a given hour was to line up systemd's start times against
    `git log` by hand. A window that cannot name its instrument is a number
    that gets quoted later as the real rung's -- the fault CLAUDE.md §0 exists
    to prevent, one level down.
    """
    import run as runmod
    from kernel import cycle as cyclemod
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ident = runmod.engine_identity(repo, spec=[{"name": "a"}, {"model": "m"}],
                                   cousin_spec=[{"name": "c"}])
    sha = ident["engine"]
    check("identity: the engine is a commit, or says it cannot tell",
          sha == "unknown" or re.fullmatch(r"[0-9a-f]{40}", sha) is not None,
          sha)
    check("identity: dirty is True, False or None -- never a guess",
          ident["dirty"] in (True, False, None), repr(ident["dirty"]))
    caps = ident["caps"]
    check("identity: every cap the kernel enforces is named, from the constants",
          caps["exec_stdout"] == EXEC_STDOUT_CHARS
          and caps["history_output"] == Engine.HISTORY_OUTPUT_CHARS
          and caps["think_raw"] == cyclemod.THINK_RAW_CHARS, str(caps))
    check("identity: rungs are named by name, falling back to model",
          ident["rungs"] == ["a", "m"] and ident["cousin_rungs"] == ["c"],
          str(ident))
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))
    runmod.record_engine_start(j, ident, root=d, pause=30, forever=True)
    rec = j.read(kinds=["engine_start"])
    check("identity: engine_start is its own kind with structured fields",
          len(rec) == 1 and rec[0].get("engine") == sha
          and rec[0].get("caps") == caps and rec[0].get("root") == d
          and rec[0].get("forever") is True, str(rec)[:240])
    shutil.rmtree(d, ignore_errors=True)


def test_a_wake_records_what_was_served():
    """A promise the context does not keep is invisible unless the journal
    says what the context HELD.

    The builder's library gap survived a day (CLAUDE.md §5) and the want
    channel was dead for the life of the kernel with a green gate over it,
    because `wake` recorded one number: how long the context was. Length
    cannot say whether the library was on the page or whether a standing want
    reached the creature. These are facts about what the kernel served,
    gathered where it served them -- never recomputed by a reader, which
    would be a second account of the same event, and two accounts drift.
    """
    e, j, b, d = build_engine(["thinking, no commands", "thinking again"], [])
    own = os.path.join(b.mind, "tools", "own")
    e.run_cycle()
    w0 = j.read(kinds=["wake"])[-1]
    check("served: an empty library is recorded as zero shown, zero total",
          w0.get("library_shown") == 0 and w0.get("library_total") == 0, str(w0))
    check("served: no standing want is recorded as zero served",
          w0.get("wants_served") == 0, str(w0))
    _write_tool(own, "plan", does="tracks what to do next", call="plan list")
    e.record_want("a way to see yesterday's tasks")
    e.run_cycle()
    w = j.read(kinds=["wake"])[-1]
    check("served: the wake says how many tools were on the page",
          w.get("library_shown") == 1 and w.get("library_total") == 1, str(w))
    check("served: and that the standing want reached the creature",
          w.get("wants_served") == 1, str(w))
    check("served: and which output window the history was cut to",
          w.get("window") == Engine.HISTORY_OUTPUT_CHARS, str(w))
    check("served: the length is still there for the observer",
          (w.get("context_chars") or 0) > 0, str(w))
    b.destroy()
    shutil.rmtree(d, ignore_errors=True)


def test_the_selfcheck_proves_effects_and_never_vetoes():
    """A directive read back off a unit proves it was PARSED, never that it
    WORKS (CLAUDE.md §5, twice in one evening). So the engine tests the
    effects it depends on at every start, through the same shell the creature
    gets, and RECORDS the result. It does not refuse to start on one: a
    preflight that vetoes on a check is the scar one entry up. Three answers
    per effect, never two -- proven, DISPROVEN, or not testable here.
    """
    import run as runmod
    d = tmpdir()
    home = os.path.join(d, "home")
    os.makedirs(home)
    j = Journal(os.path.join(d, "journal.jsonl"))
    b = runmod.PathBody(os.path.join(d, "body"))
    b.bin = runmod.install_hands(b)
    out = runmod.selfcheck(b, journal=j, home=home)
    keys = {"body_answers", "home_write_blocked", "spine_unreadable",
            "hand_on_path", "python3_on_path", "caps_ordered", "ok",
            "unproven"}
    check("selfcheck: every effect has a field", keys <= set(out), str(out))
    check("selfcheck: an unsandboxed dev box is reported as UNPROTECTED, not "
          "as fine", out.get("home_write_blocked") is False, str(out))
    check("selfcheck: it leaves no canary behind",
          not os.path.exists(os.path.join(home, runmod.SELFCHECK_CANARY)))
    check("selfcheck: a spine that is not here is 'cannot tell', never "
          "'protected'", out.get("spine_unreadable") is None, str(out))
    check("selfcheck: our hands are on the creature's PATH",
          out.get("hand_on_path") is True, str(out))
    check("selfcheck: the caps are ordered journal >= history",
          out.get("caps_ordered") is True, str(out))
    check("selfcheck: ok means nothing was DISPROVEN, so an open home is not ok",
          out.get("ok") is False, str(out))
    rec = j.read(kinds=["selfcheck"])
    check("selfcheck: recorded under its own kind, with the verdict as a field",
          len(rec) == 1 and rec[0].get("ok") is False
          and rec[0].get("home_write_blocked") is False, str(rec)[:200])
    # THE KEY FILES, which is the whole of PLAN item 7. `child_env` closed the
    # engine's environment variables in September and said plainly that the
    # FILES stayed readable by anything running as this uid. A `LocalBody`
    # therefore reads them, and the selfcheck must say so at every start
    # rather than leaving the gap to be remembered.
    keys = os.path.join(d, "keys")
    os.makedirs(keys)
    with open(os.path.join(keys, "provider.key"), "w", encoding="utf-8") as f:
        f.write("sk-not-a-real-credential\n")
    withkeys = runmod.selfcheck(b, journal=None, home=home, keys_dir=keys)
    check("selfcheck: a LocalBody CAN read the engine's keys, and the record "
          "says so instead of implying otherwise",
          withkeys.get("keys_unreadable") is False, str(withkeys))
    check("selfcheck: which means `ok` is False while that is true",
          withkeys.get("ok") is False, str(withkeys))
    nokeys = runmod.selfcheck(b, journal=None, home=home,
                              keys_dir=os.path.join(d, "no-keys-here"))
    check("selfcheck: and where there are no key files it is 'cannot tell', "
          "never 'safe'", nokeys.get("keys_unreadable") is None, str(nokeys))

    # A sibling that CAN be read is a breach, reported as one -- not skipped.
    os.makedirs(os.path.join(home, "growing-spine"))
    out2 = runmod.selfcheck(b, journal=None, home=home)
    check("selfcheck: a readable sibling is reported as a breach",
          out2.get("spine_unreadable") is False, str(out2))
    # A body that does not answer is a recorded fact, never a crash.
    b._alive = False
    out3 = runmod.selfcheck(b, journal=j, home=home)
    check("selfcheck: a dead body is recorded, and the rest is 'cannot tell'",
          out3.get("body_answers") is False and out3.get("ok") is False
          and out3.get("hand_on_path") is None, str(out3))
    check("selfcheck: nothing tested a dead body left in the journal as proven",
          len(j.read(kinds=["selfcheck"])) == 2)
    shutil.rmtree(d, ignore_errors=True)


def test_loop_end_says_whether_it_gave_up():
    """The flag the supervisor keeps goes into the journal beside the prose,
    so a reader tells a stop from a give-up without parsing the reason string
    -- the rule `ended_in_fault` was created under, applied to the record."""
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    def boom():
        raise RuntimeError("gone")
    s = forever.Supervisor(boom, os.path.join(d, "nope"), journal=j,
                           sleep=lambda _x: None, is_wait=lambda _e: False)
    s.loop(max_cycles=50)
    end = j.read(kinds=["loop_end"])[-1]
    check("loop_end: a give-up is journalled as fault=True",
          end.get("fault") is True, str(end))
    j2 = Journal(os.path.join(d, "j2.jsonl"))
    s2 = forever.Supervisor(lambda: None, os.path.join(d, "nope"), journal=j2,
                            sleep=lambda _x: None)
    s2.loop(max_cycles=2)
    end2 = j2.read(kinds=["loop_end"])[-1]
    check("loop_end: finishing is journalled as fault=False",
          end2.get("fault") is False, str(end2))
    shutil.rmtree(d, ignore_errors=True)


FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "journal")


def _fixture(name):
    from monitor import derive
    rows = derive.load_fixture(os.path.join(FIXTURES, name + ".jsonl"))
    assert rows, "fixture %s is empty or missing" % name
    return rows


def _first_raise(timeline, prefix):
    for c in timeline:
        if c["name"].startswith(prefix) and c["to"] == "ALARM":
            return c
    return None


def test_monitor_detectors_fire_where_the_scars_happened():
    """Each detector replayed over the real journal slice where its scar
    occurred, asserting it fires no later than the moment a human could
    first have known -- and no earlier, because a detector that fires on two
    events is a wolf-crier nobody reads. Then the control: a healthy hour
    must raise nothing a human has to look at.
    """
    from monitor import derive, detectors, status as monstatus

    # A. 2026-09-13: gemini served 14 UNKNOWN in a row; read as weather for
    #    four hours. The fourth arrived 16:22. Same slice: a want retired at
    #    17:42 with no tool write since it was issued. And `plan`, probed 22
    #    times -- the chooser's alphabetical default, found 2026-09-15.
    rows = _fixture("0913-gemini-unusable-and-want-unacted")
    tl = monstatus.replay(rows, step=1)
    stuck = _first_raise(tl, "probe_stuck")
    check("replay: probe_stuck names `plan` on 09-13 -- the chooser, not the tool",
          stuck is not None and stuck["evidence"].get("tool") == "plan", str(stuck)[:200])
    unk = [r for r in rows if r["kind"] == "cousin_verdict"
           and (r.get("rung") or "").startswith("gemini")
           and r.get("verdict") == "UNKNOWN"]
    hit = _first_raise(tl, "unusable_verdicts[gemini")
    check("replay: unusable_verdicts fires on gemini's run of UNKNOWNs",
          hit is not None, str([c["name"] for c in tl])[:300])
    check("replay: no later than the FOURTH unknown (16:22; noticed ~19:40)",
          hit is not None and hit["ts"] <= float(unk[3]["ts"]) + 1,
          hit and "%.0fs after" % (hit["ts"] - float(unk[3]["ts"])))
    check("replay: and not before it -- n<4 is 'cannot tell', never an alarm",
          hit is not None and hit["ts"] >= float(unk[3]["ts"]) - 1,
          hit and "%.0fs before" % (float(unk[3]["ts"]) - hit["ts"]))
    ret = [r for r in rows if r["kind"] == "want_retired"
           and r.get("because") != "superseded"]
    hit2 = _first_raise(tl, "want_retired_unacted")
    check("replay: want_retired_unacted fires on the want discarded unacted",
          hit2 is not None and ret and abs(hit2["ts"] - float(ret[0]["ts"])) <= 1,
          str(hit2)[:200])

    # B. 2026-09-13: fifteen identical SyntaxErrors across rewrites of
    #    subagent-orchestrator, all our parser's cut. Third at 20:00; the
    #    twelfth was noticed at 04:35.
    rows = _fixture("0913-fence-syntaxerror")
    tl = monstatus.replay(rows, step=1)
    se = [r for r in rows if r["kind"] == "exec_end"
          and "SyntaxError" in (r.get("stderr") or "")]
    hit = _first_raise(tl, "repeated_failure[subagent-orchestrator]")
    check("replay: repeated_failure fires on the THIRD identical SyntaxError "
          "across rewrites", hit is not None and len(se) >= 3
          and abs(hit["ts"] - float(se[2]["ts"])) <= 1,
          str(hit)[:200] if hit else str([c["name"] for c in tl])[:200])
    check("replay: and not on the second -- two failures is a creature debugging",
          hit is not None and hit["ts"] > float(se[1]["ts"]), str(hit)[:120])

    # C. 2026-09-14: the anchored opener dropped a real command 40 minutes
    #    after the fence fix.
    rows = _fixture("0914-opener-regression")
    tl = monstatus.replay(rows, step=1)
    uf = [r for r in rows if r["kind"] == "exec_skip"
          and r.get("reason") == "unclosed_fence"]
    hit = _first_raise(tl, "commands_lost_parser")
    check("replay: commands_lost_parser fires the moment a tagged fence "
          "yields no block", hit is not None and uf
          and abs(hit["ts"] - float(uf[0]["ts"])) <= 1, str(hit)[:200])

    # D. The control -- for every detector but one. Cut as a healthy hour on
    #    2026-09-14; on 2026-09-15 it turned out to carry the chooser fault
    #    (`view-subtask-logs` probed 5 of 5, all bare). A control is a
    #    control only for the detectors that are quiet on it, and the one
    #    that is not must say so rather than be excused.
    rows = _fixture("0914-healthy-hour")
    tl = monstatus.replay(rows, step=1)
    raised = [c for c in tl if c["to"] == "ALARM" and c.get("human")
              and c["name"] != "probe_stuck"]
    check("replay: the control hour raises NOTHING else a human must look at",
          not raised, str([(c["name"], c["msg"][:60]) for c in raised])[:400])
    stuck = _first_raise(tl, "probe_stuck")
    check("replay: and the fault that WAS live in it is named -- view-subtask-logs, "
          "5 of 5, the chooser's default",
          stuck is not None and stuck["evidence"].get("tool") == "view-subtask-logs",
          str(stuck)[:200])

    # E. 2026-09-15: the same want six times behind ACCEPTs of a usage line
    #    the cousin could not get past; view-subtask-logs probed 28 of 30
    #    non-write visits. Eighteen hours before anyone looked.
    rows = _fixture("0915-want-loop")
    tl = monstatus.replay(rows, step=1)
    same = [r for r in rows if r["kind"] == "cousin_want"
            and "multiple parent task ids" in (r.get("text") or "").lower()]
    hit = _first_raise(tl, "want_repeated")
    check("replay: want_repeated fires on the THIRD identical want (16:34; it ran "
          "to six)", hit is not None and len(same) >= 3
          and abs(hit["ts"] - float(same[2]["ts"])) <= 1,
          str(hit)[:200] if hit else str([c["name"] for c in tl])[:200])
    view = [r for r in rows if r["kind"] == "cousin_probe"
            and r.get("tool") == "view-subtask-logs"]
    hit2 = _first_raise(tl, "probe_stuck")
    check("replay: probe_stuck fires on view-subtask-logs once it is 5 of the last "
          "8 non-write probes", hit2 is not None
          and hit2["evidence"].get("tool") == "view-subtask-logs", str(hit2)[:200])
    check("replay: and not before the fifth such probe",
          hit2 is not None and len(view) >= 5
          and hit2["ts"] >= float(view[4]["ts"]) - 1,
          hit2 and derive.ts_str(hit2["ts"]))
    hidden = _first_raise(tl, "served_context_contract")
    check("replay: the seven tools past the listing limit are alarmed on the real "
          "slice (07:00 on 09-15)", hidden is not None and "NOBODY" in hidden["msg"],
          str(hidden)[:200])

    # Three states, never silence -- checked on the control hour.
    healthy = _fixture("0914-healthy-hour")
    ctx = detectors.Context(healthy, now=float(healthy[-1]["ts"]))
    fs = detectors.run_all(ctx)
    check("replay: every detector reports a state on the control -- none is "
          "silent", len(fs) >= len(detectors.ALL)
          and all(f.state in (detectors.OK, detectors.ALARM, detectors.INFO,
                              detectors.CANNOT_TELL) for f in fs),
          str([(f.name, f.state) for f in fs])[:300])
    check("replay: what it cannot know it SAYS it cannot know (pre-43eb8af "
          "fields)", any(f.state == detectors.CANNOT_TELL
                          and f.name == "served_context_contract" for f in fs),
          str([(f.name, f.state) for f in fs if f.name == "served_context_contract"]))


def _tree_digest(root, skip):
    import hashlib
    out = {}
    for dp, dn, fn in os.walk(root):
        if os.path.abspath(dp).startswith(os.path.abspath(skip)):
            continue
        for n in fn:
            p = os.path.join(dp, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha1(f.read()).hexdigest()
    return out


def _monitor_root(fixture, d):
    root = os.path.join(d, "live")
    own = os.path.join(root, "body", "mind", "tools", "own")
    os.makedirs(own)
    shutil.copy(os.path.join(FIXTURES, fixture + ".jsonl"),
                os.path.join(root, "journal.jsonl"))
    with open(os.path.join(root, "context.md"), "w", encoding="utf-8") as f:
        f.write("## asked\n\n1. a thing\n")
    with open(os.path.join(root, "quota.json"), "w", encoding="utf-8") as f:
        f.write('{"gemini/x": {"last_success": 1}}')
    with open(os.path.join(own, "plan"), "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n# does: x\necho hi\n")
    return root


def test_monitor_writes_only_its_own_directory():
    """An observation surface that can alter the evidence is part of the
    system under test. The monitor may write `live/monitor/` and nothing
    else -- asserted here on the code, and made impossible by the unit."""
    from monitor import status as monstatus
    d = tmpdir()
    root = _monitor_root("0914-healthy-hour", d)
    rows = _fixture("0914-healthy-hour")
    mon = os.path.join(root, "monitor")
    before = _tree_digest(root, mon)
    md, data, rc = monstatus.run_once(root, repo=None, now=float(rows[-1]["ts"]))
    after = _tree_digest(root, mon)
    check("monitor: nothing outside live/monitor changed", before == after,
          str(set(before.items()) ^ set(after.items()))[:300])
    have = set(os.listdir(mon)) if os.path.isdir(mon) else set()
    check("monitor: status.md, status.json and state.json were written",
          {"status.md", "status.json", "state.json"} <= have, str(have))
    # The control hour carries ONE real fault (the chooser sat on
    # view-subtask-logs, found 2026-09-15), so the run exits 1 for that and
    # for nothing else.
    human = [f["name"] for f in data["findings"]
             if f["state"] == "ALARM" and f.get("human")]
    check("monitor: the control hour exits 1 for the chooser fault it carries, "
          "and for nothing else", rc == 1 and human == ["probe_stuck"], (rc, human))
    check("monitor: the page says the engine is UNKNOWN when the journal "
          "never said (pre-43eb8af), rather than guessing",
          "unknown" in md.split("## Alarms")[0], md[:400])
    check("monitor: every counts window names its engine",
          all("engines" in w and w["engines"] for w in data["windows"]),
          str([w.get("engines") for w in data["windows"]]))
    check("monitor: the library record uses the kernel's own classification "
          "(unqualified is a column, not a failure)",
          all("unqualified" in r for r in data["library"]["record"]),
          str(data["library"]["record"][:2]))
    shutil.rmtree(d, ignore_errors=True)


def test_monitor_alarms_are_edge_triggered():
    """A line on RAISE and a line on CLEAR, nothing between -- the parent's
    *surface on a change of state, never continuously*, applied to us. A
    monitor that writes the same alarm every five minutes trains its reader
    to skip it."""
    from monitor import status as monstatus
    d = tmpdir()
    root = _monitor_root("0914-opener-regression", d)
    rows = _fixture("0914-opener-regression")
    now = float(rows[-1]["ts"])
    alarms = os.path.join(root, "monitor", "alarms.jsonl")

    def lines():
        if not os.path.exists(alarms):
            return []
        return [json.loads(l) for l in open(alarms, encoding="utf-8") if l.strip()]

    md, data, rc = monstatus.run_once(root, repo=None, now=now)
    first = [l for l in lines() if l["name"] == "commands_lost_parser"]
    check("edge: the parser alarm is RAISED once, with its evidence",
          len(first) == 1 and first[0]["to"] == "ALARM" and first[0]["evidence"],
          str(first)[:200])
    check("edge: and a raised alarm makes the run exit 1",
          rc == monstatus.EXIT_ALARM, rc)
    # THE STANDING STATE, beside the edges. The log says what CHANGED and the
    # page says everything; neither answers "is anything wrong right now?"
    # without being read.
    alarm_file = os.path.join(root, "monitor", monstatus.ALARM_FILE)
    check("edge: a standing alarm is a FILE whose presence is the signal",
          os.path.exists(alarm_file)
          and "commands_lost_parser" in open(alarm_file, encoding="utf-8").read(),
          os.path.exists(alarm_file))
    monstatus.run_once(root, repo=None, now=now + 60)
    monstatus.run_once(root, repo=None, now=now + 120)
    check("edge: two more runs with the alarm still standing write NOTHING",
          len([l for l in lines() if l["name"] == "commands_lost_parser"]) == 1,
          str(lines())[:300])
    monstatus.run_once(root, repo=None, now=now + 2 * 3600)
    cl = [l for l in lines() if l["name"] == "commands_lost_parser"]
    check("edge: when the hour passes the alarm is CLEARED, once",
          len(cl) == 2 and cl[1]["from"] == "ALARM" and cl[1]["to"] != "ALARM",
          str(cl)[:300])
    # Two hours on, the parser alarm has cleared -- and the journal is now two
    # hours stale, so `engine_silent` correctly stands in its place. The file
    # is the STANDING SET, never a history: it must have dropped the one and
    # picked up the other.
    standing = open(alarm_file, encoding="utf-8").read() if os.path.exists(alarm_file) else ""
    check("edge: a cleared alarm leaves the ALARM file, and a newly standing "
          "one enters it", "commands_lost_parser" not in standing
          and "engine_silent" in standing, standing[:200])

    # And when nothing stands at all, the file is REMOVED rather than left to
    # go stale -- proven by a transition, not by never having created one.
    # Both halves of the pair go, not just the probes: a verdict left without
    # its probe is a cousin judging work it was never shown running, which
    # `complaint_fidelity` is right to raise. Removing only the probes would
    # have made this a test of a fixture nobody could produce.
    rows2 = [r for r in _fixture("0914-healthy-hour")
             if r["kind"] not in ("cousin_probe", "cousin_verdict")]
    d2 = tmpdir()
    root2 = _monitor_root("0914-healthy-hour", d2)
    quiet = os.path.join(root2, "monitor", monstatus.ALARM_FILE)
    _md, _data, rc2 = monstatus.run_once(root2, repo=None,
                                         now=float(_fixture("0914-healthy-hour")[-1]["ts"]))
    check("edge: the control hour's chooser fault creates the file",
          os.path.exists(quiet) and rc2 == monstatus.EXIT_ALARM, rc2)
    with open(os.path.join(root2, "journal.jsonl"), "w", encoding="utf-8") as f:
        for r in rows2:
            f.write(json.dumps(r) + "\n")
    _md, data3, rc3 = monstatus.run_once(root2, repo=None, now=float(rows2[-1]["ts"]))
    check("edge: and once nothing needs a human the file is REMOVED, and the "
          "run exits clean", not os.path.exists(quiet) and rc3 == monstatus.EXIT_OK,
          [f["name"] for f in data3["findings"]
           if f["state"] == "ALARM" and f.get("human")])
    shutil.rmtree(d2, ignore_errors=True)
    st = json.load(open(os.path.join(root, "monitor", "state.json"), encoding="utf-8"))
    check("edge: the state remembers since-when, per finding",
          "since" in st and "commands_lost_parser" in st["since"], str(st)[:200])
    shutil.rmtree(d, ignore_errors=True)


def test_the_brief_can_be_scored_against_cases_it_never_saw():
    """PLAN item 8. §0 has said since 2026-09-14 that the brief is FROZEN
    until there is a way to score a change against held-out cases, *"which
    `trial/` could carry and currently does not"*. Every case in `cases.json`
    and `repair-cases.json` was used to WRITE the brief, so a score on them
    measures how well it remembers its own training.
    """
    root = _repo_root()
    trial = os.path.join(root, "trial")
    sys.path.insert(0, trial)
    import make_heldout
    import score_brief

    def cases_of(name):
        p = os.path.join(trial, name)
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8") as f:
            doc = json.load(f)
        return doc.get("cases") if isinstance(doc, dict) else doc

    held = cases_of("heldout-cases.json")
    check("heldout: the set exists", held is not None, "no heldout-cases.json")
    if held is None:
        return
    check("heldout: and it has both kinds -- broken work to catch and good "
          "work that must NOT be refused",
          {c["expect"] for c in held} == {"RETURNED", "ACCEPTED"},
          sorted({c["expect"] for c in held}))

    # THE POINT OF THE WHOLE SET: none of it taught the brief. The first run
    # of the generator produced three tools that are in `cases.json` --
    # RecallScheduler, ascii_plot, dynamic_faq_updater -- which would have
    # been the 2026-09-10 leak with the direction reversed, and would have
    # read as a strong score.
    taught = make_heldout.already_taught(
        [os.path.join(trial, n) for n in ("cases.json", "repair-cases.json",
                                          "cases-v1-bare-probe.json")])
    overlap = sorted({c["name"] for c in held} & taught)
    check("heldout: NOT ONE case is in the set the brief was written against",
          not overlap, str(overlap))
    check("heldout: and the exclusion is a real filter, not an empty set",
          len(taught) > 8, len(taught))

    # The leak check that already refuses a brief naming a case under test
    # must cover this set too, or it protects only the old one.
    import run_trial
    brief = io.open(os.path.join(root, "MANAGER-PROMPT.md"),
                    encoding="utf-8").read()
    names = {c["name"] for c in held}
    leaks = sorted(n for n in names
                   if re.search(r"(?<![\w.-])" + re.escape(n) + r"(?![\w-])", brief))
    check("heldout: the brief names none of them", not leaks, str(leaks))
    check("heldout: and the leak checker is the shared one, not a second copy",
          callable(getattr(run_trial, "assert_brief_names_no_case", None)))

    # DETECTION AND CORRECTION TRAVEL TOGETHER, and when correction cannot be
    # measured the runner must say so rather than print detection alone.
    repair = cases_of("heldout-repair-cases.json")
    check("heldout: the correction half exists as a file, even while empty",
          repair is not None, "no heldout-repair-cases.json")

    # A RATE IS ONLY A RATE IF THE JUDGE ANSWERED. The first baseline attempt
    # printed `caught 0/8` when all sixteen calls had returned HTTP 429.
    dead = {"n": 16, "caught": 0, "of_broken": 8, "falsely_returned": 0,
            "of_good": 8, "unreadable": 16, "answered": 0, "call_errors": 16,
            "call_error_kinds": ["HTTPError"]}
    ok, line = score_brief.detection_line(dead)
    check("heldout: a run the judge never answered is NOT a score",
          not ok and "never answered" in line, line)
    check("heldout: and it says so measures the RUNG, not the brief",
          "rung" in line, line)
    live = dict(dead, unreadable=0, answered=16, caught=7, falsely_returned=1,
                call_errors=0, call_error_kinds=[])
    ok2, line2 = score_brief.detection_line(live)
    check("heldout: a run that DID answer is scored",
          ok2 and "caught 7/8" in line2, line2)
    part = dict(live, unreadable=4, answered=12)
    ok3, line3 = score_brief.detection_line(part)
    check("heldout: and a partly-answered run says how much it is missing "
          "rather than hiding it",
          ok3 and "unreadable" in line3, line3)


def test_the_docker_body_carries_the_contract_the_creature_is_promised():
    """PLAN item 7, the half that needs no docker.

    `DockerBody` has been "written but never exercised" since the design, and
    reading it shows why that mattered: it runs `docker exec <container> sh -c`
    with no working directory and no PATH. The creature's prompt promises its
    tools are on PATH and its hands are callable by name, and `PathBody`
    keeps that promise by overriding `run`. A body that does not is the
    relative-root scar waiting to happen again -- every tool
    `command not found`, the body reporting healthy, the creature billed.
    """
    b = bodymod.DockerBody("cousin-test-container", mind="/host/mind")
    cmd = b.compose("plan list")
    check("docker: the command runs in the mind, not the image's workdir",
          "cd " in cmd and bodymod.DockerBody.MIND in cmd, cmd[:200])
    check("docker: the creature's own tools are on PATH",
          "tools/own" in cmd, cmd[:200])
    check("docker: and so are our hands",
          bodymod.DockerBody.HANDS in cmd, cmd[:200])
    check("docker: $MIND resolves inside the container, never to a host path",
          "/host/mind" not in cmd, cmd[:200])
    check("docker: the creature's command is still the last thing in it",
          cmd.rstrip().endswith("plan list"), cmd[-60:])
    argv = b.argv("echo hi")
    check("docker: it is exec'd in the container, not on the host",
          argv[:2] == ["docker", "exec"] and "cousin-test-container" in argv,
          argv[:4])
    check("docker: no host environment is handed in -- docker exec passes "
          "none by default, and nothing here adds any",
          not any(a == "-e" or a.startswith("--env") for a in argv), argv)


def test_the_docker_drill_proves_the_keys_are_out_of_reach():
    """PLAN item 7.1-7.3. The creature's shell has shared a uid with the
    engine's key files since deployment; `child_env` closed the variables in
    September and said plainly that the FILES stayed readable by anything
    running as this user. This is the other half, and it is proven by effect
    from inside the body rather than by reading a directive -- the rule §5
    earned twice in one evening.

    The evidence is produced by `rehearse.py docker` on the laptop, where
    docker exists, and committed. This asserts what it must say.
    """
    path = os.path.join(FIXTURES, "0916-drill-docker.evidence.json")
    if not os.path.exists(path):
        check("docker drill: its evidence was recorded", False, path)
        return
    ev = json.load(io.open(path, encoding="utf-8"))
    must = [
        ("keys_unreadable", "the engine's key files cannot be read from inside"),
        ("host_home_invisible", "the host home is not in the body at all"),
        ("spine_invisible", "the sibling project is unreachable (§2.6)"),
        ("mind_writable", "the creature can still build -- a sandbox that "
                          "breaks the run is found at 03:00 by nobody"),
        ("hands_on_path", "our hands are callable by name"),
        ("own_tools_on_path", "and so are the creature's own"),
        ("python3", "python3 is there, or 63 of its tools die"),
        ("bash", "bash is there, or the other 7 do"),
        ("requests", "requests is importable, or the tools that fetch die"),
        ("real_tool_ran", "a tool the creature actually wrote runs in it"),
    ]
    for key, why in must:
        check("docker drill: %s" % why, ev.get(key) is True,
              "%s=%r" % (key, ev.get(key)))
    # NOT a live preflight: that would make this assertion hostage to free-tier
    # weather, and a test that goes red because a rung was busy teaches its
    # reader to ignore it. The property at stake is the asymmetry -- the engine
    # holds the credentials, the creature cannot reach them -- and that is
    # deterministic.
    check("docker drill: the engine still holds every credential the creature "
          "can no longer reach", ev.get("engine_holds_credentials") is True,
          ev.get("engine_holds_credentials"))
    check("docker drill: and it says which keys it checked, so the asymmetry "
          "is countable rather than asserted",
          isinstance(ev.get("credentials_checked"), int)
          and ev["credentials_checked"] > 0, ev.get("credentials_checked"))


def test_a_ladder_with_every_rung_walled_never_reads_as_a_wait():
    """Found by the give-up drill, 2026-09-16, which is what it is for.

    `default_is_wait` says it plainly: *"a rejected credential is not a wait,
    because waiting cannot fix it and a loop that waits politely forever on a
    broken key looks exactly like one that is working."* The ladder walls a
    rung by adding it to a set and skipping it on every later call -- so the
    SECOND time everything is walled, nothing is tried, `tried` is empty, and
    `all_walled=bool(tried) and ...` came out **False**. The supervisor then
    treated a permanently broken credential as weather and waited: 600 waits
    at 150s is twenty-five hours of an engine looking healthy while nothing
    could ever answer it.

    The first call was honest; every call after it lied. That is worse than
    being wrong once, because the symptom appears only after the failure has
    already been correctly diagnosed and then forgotten.
    """
    def dead(_prompt):
        raise RuntimeError("no credential: /nonexistent.key is empty")

    ask = backends.ladder([("only-rung", dead)], retries=1,
                          sleep=lambda _s: None)
    seen = []
    for _ in range(3):
        try:
            ask("hello")
        except backends.LadderExhausted as e:
            seen.append(e)
    check("walled: every attempt is exhausted", len(seen) == 3, len(seen))
    check("walled: the FIRST exhaustion says every rung was walled",
          seen[0].all_walled, seen[0])
    check("walled: and so does every one after it, when the rung is skipped "
          "because it was already walled", all(e.all_walled for e in seen),
          [e.all_walled for e in seen])
    check("walled: so the supervisor counts these as FAILURES, never waits -- "
          "waiting cannot fix a rejected credential",
          not any(forever.default_is_wait(e) for e in seen),
          [forever.default_is_wait(e) for e in seen])
    # And the opposite case must not be swept up with it: a rung that merely
    # declined is still weather, and the loop must still wait it out.
    def busy(_prompt):
        e = RuntimeError("quota")
        e.code = 429
        raise e

    ask2 = backends.ladder([("busy-rung", busy)], retries=1,
                           sleep=lambda _s: None)
    try:
        ask2("hello")
    except backends.LadderExhausted as e2:
        check("walled: a rung that DECLINED is still a wait, not a fault",
              not e2.all_walled and forever.default_is_wait(e2), e2)


def test_the_rehearsal_cannot_touch_the_live_run():
    """PLAN item 6.1/6.7. A harness whose whole purpose is breaking things
    must be structurally unable to break the thing that is running. Two
    independent guards, because one guard is a guess: the deployed root is
    refused by name, and ANY root that already holds a journal is refused
    whatever it is called -- the second catches a live root moved or renamed,
    which the first cannot."""
    import rehearse
    d = tmpdir()
    live = os.path.join(d, "growing-cousin", "live")
    os.makedirs(live)
    ok, why = rehearse.may_use(live)
    check("rehearse: the deployed root is refused by name", not ok, why)
    other = os.path.join(d, "somewhere-else")
    os.makedirs(other)
    with open(os.path.join(other, "journal.jsonl"), "w", encoding="utf-8") as f:
        f.write('{"ts": 1, "kind": "wake"}\n')
    ok2, why2 = rehearse.may_use(other)
    check("rehearse: and so is any root that already holds a journal, "
          "whatever it is called", not ok2, why2)
    # THE REGRESSION THIS GUARD DID NOT HAVE, and the first run found it: the
    # runner appends the drill's name to the path it is given, so a target of
    # `<live>` becomes `<live>/tool-gone` -- neither named `live` nor holding
    # a journal. It created a directory inside the running deployment. A guard
    # keyed on one literal, guarding the one thing that must not be touched.
    inside = os.path.join(live, "tool-gone")
    ok_in, why_in = rehearse.may_use(inside)
    check("rehearse: a path INSIDE the deployed root is refused too",
          not ok_in, why_in)
    ok_in2, why_in2 = rehearse.may_use(os.path.join(other, "sub", "deeper"))
    check("rehearse: and so is anything under a root that holds a journal",
          not ok_in2, why_in2)
    fresh = os.path.join(d, "scratch")
    ok3, _why3 = rehearse.may_use(fresh)
    check("rehearse: a fresh scratch root is allowed", ok3, _why3)
    # The refusal must be the DEFAULT, not something a caller opts into.
    try:
        rehearse.scratch_root(live)
        refused = False
    except rehearse.RefusedLiveRoot:
        refused = True
    check("rehearse: preparing a refused root raises rather than returning "
          "something usable", refused)

    # A REPOSITORY IS SOMEBODY'S WORKING TREE. `~/growing-cousin` is the live
    # unit's WorkingDirectory and was allowed outright; so was
    # `~/growing-spine`, which §2.6 makes a hard boundary -- *never touch
    # Growing Spine from this repo*. Found 2026-09-16 by an independent
    # verifier who tried the paths rather than the ones the guard was written
    # against.
    repo = os.path.join(d, "growing-cousin")
    os.makedirs(os.path.join(repo, ".git"))
    ok_repo, why_repo = rehearse.may_use(repo)
    check("rehearse: a checkout is refused -- it is somebody's working tree",
          not ok_repo, why_repo)
    ok_sub, _ = rehearse.may_use(os.path.join(repo, "scratch"))
    check("rehearse: and so is anything under one", not ok_sub, "")
    spine = os.path.join(d, "growing-spine")
    os.makedirs(spine)
    ok_spine, why_spine = rehearse.may_use(os.path.join(spine, "anything"))
    check("rehearse: the sibling project is refused by NAME, whatever is in "
          "it -- §2.6 is a boundary, not a heuristic", not ok_spine, why_spine)

    # THE DANGEROUS ONE: the harness deleted its target before asking whether
    # it was allowed to have one. It printed REFUSED *after* rmtree'ing a
    # subtree of a live root, including a file under `tools/own`.
    victim = os.path.join(live, "tool-gone")
    os.makedirs(os.path.join(victim, "tools", "own"))
    precious = os.path.join(victim, "tools", "own", "plan")
    with open(precious, "w", encoding="utf-8") as f:
        f.write("the creature's work\n")
    rc = rehearse.main(["tool-gone", "--scratch", live])
    check("rehearse: running against a live root exits non-zero", rc != 0, rc)
    check("rehearse: AND NOTHING WAS DELETED -- the guard runs before the "
          "harness clears its workspace, not after",
          os.path.exists(precious), "the drill destroyed %s" % precious)


def test_the_drills_give_the_unproven_detectors_their_red():
    """PLAN item 6.6. Four detectors have never fired on real data because
    the faults they watch for have never happened in production: the engine
    has never gone silent, never given up, never torn its journal, never lost
    a tool off PATH. *A test that has never been seen red is a guess*, so the
    drills manufacture each fault on a scratch root and keep the journal.

    The fixtures are produced by `rehearse.py` on the laptop and committed;
    this asserts what they must contain, so a drill that stops reproducing
    its fault fails here rather than passing quietly.
    """
    from monitor import derive, detectors, status as monstatus

    def load(drill):
        path = os.path.join(FIXTURES, "0916-drill-%s.jsonl" % drill)
        if not os.path.exists(path):
            check("drill %s: its fixture exists" % drill, False, path)
            return None
        return derive.load(path, tail_bytes=1 << 40)

    # Three are visible IN the journal, so replaying it proves them. The
    # fabricated verdict is here because `complaint_fidelity` was otherwise
    # the one detector whose ALARM had only ever been seen on rows a test
    # made up -- 159 real verdicts produced zero HIGH findings, which is good
    # news about the cousin and no news at all about the instrument.
    for drill, detector in (("tool-gone", "tool_vanished"), ("giveup", "gave_up"),
                            ("fabricate", "complaint_fidelity")):
        got = load(drill)
        if not got:
            continue
        rows, _complete, _bad = got
        tl = monstatus.replay(rows, step=1)
        hit = _first_raise(tl, detector)
        check("drill %s: `%s` fires on the fault it had never been able to see"
              % (drill, detector), hit is not None,
              str(sorted(set(c["name"] for c in tl)))[:200])
        ctx = detectors.Context(rows, now=float(rows[-1]["ts"]))
        fs = detectors.run_all(ctx)
        check("drill %s: and no detector raises on a journal full of faults"
              % drill, all(f.state != detectors.CANNOT_TELL or "raised" not in f.msg
                           for f in fs),
              str([f.msg for f in fs if "raised" in f.msg])[:200])

    # THE TORN JOURNAL cannot be carried by any loader that returns rows: the
    # fault IS a line that does not parse, so a fixture read normally has
    # already lost it. Only the load's own bad-count still holds it -- which
    # is exactly why `journal_integrity` reads that rather than the rows.
    got = load("torn")
    if got:
        rows, complete, bad = got
        check("drill torn: the fixture still carries the torn line, rather "
              "than a loader having quietly repaired it", bad >= 1, bad)
        f = detectors.journal_integrity(
            detectors.Context(rows, now=float(rows[-1]["ts"]),
                              complete=complete, bad=bad))
        check("drill torn: `journal_integrity` reports it",
              f.state in (detectors.ALARM, detectors.INFO), "%s %s" % (f.state, f.msg))
        check("drill torn: and it REPORTS rather than repairing -- a monitor "
              "that rewrites the evidence is not a monitor",
              "repair" not in f.msg.lower(), f.msg)

    # THE BODY DYING UNDER THE CREATURE. `ensure_body` respawns a body that
    # will not answer, and in run 2 it never once had to: neither kind appears
    # in the whole journal. There is no detector for this -- it is a bound,
    # not a judgement -- so what must be true is that the kernel SAW it and
    # said so in its own two kinds, and that the creature was never handed the
    # failure shaped like its own output.
    got = load("body")
    if got:
        rows, _c, _b = got
        kinds = [r.get("kind") for r in rows]
        check("drill body: the kernel noticed the body had stopped answering",
              "body_unresponsive" in kinds, kinds)
        check("drill body: and recorded the respawn attempt and its outcome",
              any(r.get("kind") == "body_respawn" and "ok" in r for r in rows),
              [r for r in rows if r.get("kind") == "body_respawn"])
        ends = [r for r in rows if r.get("kind") == "exec_end"]
        check("drill body: infrastructure failure is NEVER recorded as the "
              "creature's own command output",
              all("body is down" not in (r.get("stderr") or "") for r in ends),
              [r.get("stderr") for r in ends])
        # AND the thing the drill found: the respawn does not rebuild the
        # tree, so it comes back False and nothing raises. Visible now
        # (PLAN item 15 is whether it should end the run).
        f = detectors.body_unrecoverable(
            detectors.Context(rows, now=float(rows[-1]["ts"])))
        check("drill body: a body that could not be brought back reaches a "
              "human, because nothing else in the loop will",
              f.state == detectors.ALARM and f.human, "%s %s" % (f.state, f.msg))

    # AN ENGINE THAT STOPPED has no event for it. `engine_silent` reads the
    # clock, so replaying a journal against its own last timestamp can never
    # show it -- the age is zero at every step by construction. It is proven
    # the way the monitor meets it: at a later wall-clock now.
    got = load("silence")
    if got:
        rows, _c, _b = got
        last = float(rows[-1]["ts"])
        quiet = detectors.engine_silent(detectors.Context(rows, now=last + 60))
        check("drill silence: a minute after the last event, nothing is wrong",
              quiet.state == detectors.OK, "%s %s" % (quiet.state, quiet.msg))
        gone = detectors.engine_silent(
            detectors.Context(rows, now=last + (detectors.SILENT_MINUTES + 5) * 60))
        check("drill silence: past the floor, `engine_silent` fires",
              gone.state == detectors.ALARM, "%s %s" % (gone.state, gone.msg))
        stopped = detectors.engine_silent(
            detectors.Context(rows, now=last + 3600, stop_present=True,
                              unit={"ActiveState": "inactive"}))
        check("drill silence: but a deliberate stop is not an alarm -- the "
              "STOP file is the documented way to stop it",
              stopped.state == detectors.INFO and not stopped.human,
              "%s %s" % (stopped.state, stopped.msg))


def test_the_giveup_drill_proves_the_chain_systemd_owns():
    """PLAN item 6.2/6.4. `run.py` exits 5 when the supervisor gives up so
    that `Restart=on-failure` can fire -- a chain the gate structurally
    cannot test, because systemd is half of it. The drill runs the real
    `run.py` under a real throwaway unit and records what happened; this
    asserts the recorded evidence says what it must.

    The trigger needs no network: a rung whose key file is absent raises
    `no credential`, which `classify_error` WALLs, so the ladder exhausts
    all-walled, the supervisor counts failures rather than waits, and five
    of them end the run.
    """
    path = os.path.join(FIXTURES, "0916-drill-giveup.evidence.json")
    if not os.path.exists(path):
        check("giveup drill: its evidence was recorded", False, path)
        return
    ev = json.load(io.open(path, encoding="utf-8"))
    check("giveup drill: the run exited 5 -- giving up is not finishing",
          ev.get("exit_code") == 5, ev.get("exit_code"))
    check("giveup drill: systemd restarted it rather than leaving it dead",
          (ev.get("n_restarts") or 0) >= 1, ev.get("n_restarts"))
    check("giveup drill: and the restarting was BOUNDED -- it ends in `failed` "
          "for real instead of respawning forever",
          ev.get("final_state") == "failed", ev.get("final_state"))
    kinds = ev.get("kinds") or {}
    check("giveup drill: a walled rung is journalled as needing a human, not "
          "as weather", (kinds.get("rung_broken") or 0) > 0, kinds)
    check("giveup drill: and the loop recorded that it gave up, as a FLAG",
          ev.get("loop_end_fault") is True, ev.get("loop_end_fault"))
    # Says what it measures: the live root's file TREE, recursively. It used
    # to say "byte-identical" while comparing a directory listing -- an
    # assertion whose message misdescribed its own check.
    check("giveup drill: no path under the live root was created or removed",
          ev.get("live_unchanged") is True, ev.get("live_unchanged"))
    check("giveup drill: and it really watched something, rather than finding "
          "no root and calling that unchanged",
          (ev.get("live_paths_watched") or 0) > 0,
          ev.get("live_paths_watched"))
    check("giveup drill: the unit it ran under carried no sandbox, so the "
          "selfcheck could record a DISPROVEN bound rather than only ever "
          "passing", ev.get("selfcheck_home_write_blocked") is False,
          ev.get("selfcheck_home_write_blocked"))


def test_the_census_runs_by_itself():
    """PLAN item 1. `census.py` is the only thing that checks the manager --
    CLAUDE.md §6.1's oldest open item, built 2026-09-12 -- and nothing has
    ever invoked it on a schedule. It ran when a human typed it, which is
    the *dead channel* scar in a new costume: an instrument that exists and
    is never called is not an instrument.

    A fabricated complaint is the exact fault this whole design exists to
    prevent, committed by the agent meant to catch it, so it is the one
    finding that must reach a human by itself.
    """
    from monitor import detectors, status as monstatus
    names = [d.__name__ for d in detectors.ALL]
    check("census: the complaint-fidelity check runs with every other detector",
          "complaint_fidelity" in names, names)
    now = time.time()

    def finding(rows):
        return detectors.complaint_fidelity(detectors.Context(rows, now=now))

    # A verdict describing an event the kernel did not record.
    fab = finding([
        {"ts": now - 300, "kind": "cousin_probe", "tool": "plan",
         "exit_code": 0, "bare": False, "stdout": "ok", "stderr": ""},
        {"ts": now - 290, "kind": "cousin_verdict", "verdict": "RETURNED",
         "rung": "r", "tried": "I ran plan", "outcome": "it crashed",
         "to_creature": "plan exited with code 3 and printed nothing"}])
    check("census: a verdict claiming an exit its probe never produced is an "
          "ALARM", fab.state == detectors.ALARM, "%s %s" % (fab.state, fab.msg))
    check("census: and it needs a human -- a fabricated complaint is the fault "
          "the design exists to prevent", fab.human, fab.msg)
    check("census: which names the tool the testimony was about",
          "plan" in fab.msg or "plan" in str(fab.evidence), fab.msg)
    check("census: the severity comes from census itself, not a second copy of "
          "its rules", "HIGH" in fab.msg or "HIGH" in str(fab.evidence), fab.msg)

    # Testimony that matches the record -- including a usage refusal, which
    # the brief counts as the tool working.
    ok = finding([
        {"ts": now - 300, "kind": "cousin_probe", "tool": "plan",
         "exit_code": 2, "bare": True, "stdout": "", "stderr": "usage: plan <cmd>"},
        {"ts": now - 290, "kind": "cousin_verdict", "verdict": "ACCEPTED",
         "rung": "r", "tried": "I ran plan with no arguments",
         "outcome": "it asked me for a command",
         "to_creature": "I ran plan and it told me what it needs."}])
    check("census: testimony that matches the record is OK",
          ok.state == detectors.OK, "%s %s" % (ok.state, ok.msg))

    # Nothing to check is NOT a clean bill.
    empty = finding([{"ts": now - 60, "kind": "wake", "context_chars": 10}])
    check("census: no verdict with a recorded probe is CANNOT_TELL, never OK "
          "-- it means the instrument has never run",
          empty.state == detectors.CANNOT_TELL, "%s %s" % (empty.state, empty.msg))

    # VERDICTS WITH NO PROBE AT ALL. `census.pair_up` emits `(None, verdict)`,
    # so "no pair" and "no verdict" are not the same question -- and asking
    # the wrong one gave a clean bill to a run whose probes were never
    # journalled. Constructed by an independent verifier, 2026-09-16.
    orphans = finding([
        {"ts": now - 300, "kind": "cousin_verdict", "verdict": "UNKNOWN",
         "rung": "r", "error": "no-block"},
        {"ts": now - 200, "kind": "cousin_verdict", "verdict": "UNKNOWN",
         "rung": "r", "error": "no-block"}])
    check("census: verdicts with no probe EVER recorded is CANNOT_TELL, not a "
          "clean bill", orphans.state == detectors.CANNOT_TELL,
          "%s %s" % (orphans.state, orphans.msg))

    # ONE probed verdict beside three unprobed ones must not report four as
    # clean. The CANNOT_TELL branch was fixed first and this one was missed --
    # the same fault surviving in the branch next door.
    mixed = finding([
        {"ts": now - 400, "kind": "cousin_probe", "tool": "plan",
         "exit_code": 0, "bare": False, "stdout": "ok", "stderr": ""},
        {"ts": now - 390, "kind": "cousin_verdict", "verdict": "ACCEPTED",
         "rung": "r", "tried": "I ran plan", "outcome": "it worked",
         "to_creature": "plan did what it says."},
        {"ts": now - 300, "kind": "cousin_verdict", "verdict": "UNKNOWN",
         "rung": "r", "error": "no-block"},
        {"ts": now - 200, "kind": "cousin_verdict", "verdict": "UNKNOWN",
         "rung": "r", "error": "no-block"}])
    check("census: the OK line counts what was CHECKED, not what was seen",
          mixed.state == detectors.OK
          and re.search(r"\b1 verdict\(s\) in \d+h checked", mixed.msg)
          is not None, mixed.msg)
    check("census: and says plainly how many it could not check",
          "2 had no probe" in mixed.msg, mixed.msg)

    # And one verdict tripping two census rules is still ONE verdict.
    two = finding([
        {"ts": now - 300, "kind": "cousin_probe", "tool": "plan",
         "exit_code": 0, "bare": False, "stdout": "ok", "stderr": ""},
        {"ts": now - 290, "kind": "cousin_verdict", "verdict": "RETURNED",
         "rung": "r", "tried": "I ran plan", "outcome": "it crashed",
         "to_creature": "plan exited with code 3 and then crashed"}])
    check("census: the count on the page is of VERDICTS, so one verdict "
          "breaking two rules never reads as '2 of 1'",
          re.search(r"\b1 of 1 verdicts\b", two.msg) is not None, two.msg)

    check("census: the page carries its runbook line",
          "complaint_fidelity" in monstatus.RUNBOOK, sorted(monstatus.RUNBOOK))


def test_a_broken_monitor_does_not_report_as_a_finding():
    """An instrument that fails must not speak in the voice of the thing it
    watches.

    2026-09-15: the monitor exited 1 whenever a finding needed a human, and
    the unit left that in `failed` -- indistinguishable from a crashed script.
    Tue read `cousin-monitor.service failed` as *the monitor is not running*,
    which is the correct reading of that signal and not what it meant. Three
    outcomes now, never two, and the unit declares 1 a success so that
    `failed` means exactly one thing: go fix the monitor.
    """
    from monitor import __main__ as monmain, status as monstatus
    codes = (monstatus.EXIT_OK, monstatus.EXIT_ALARM, monstatus.EXIT_BROKEN)
    check("exit: nothing-needed, a finding, and a broken monitor are three "
          "different codes", len(set(codes)) == 3, codes)
    d = tmpdir()
    root = _monitor_root("0914-healthy-hour", d)
    real = monstatus.run_once

    def boom(*_a, **_k):
        raise RuntimeError("the monitor itself is broken")
    err = io.StringIO()
    keep = sys.stderr
    try:
        monstatus.run_once = boom
        sys.stderr = err
        rc = monmain.main(["status", "--root", root, "--no-write"])
    finally:
        monstatus.run_once = real
        sys.stderr = keep
    check("exit: a monitor that raises exits BROKEN, never the alarm code",
          rc == monstatus.EXIT_BROKEN, rc)
    check("exit: and it says so, rather than leaving a traceback to be read as "
          "a finding about the engine",
          "MONITOR failed" in err.getvalue() and "not a finding" in err.getvalue(),
          err.getvalue()[-200:])
    shutil.rmtree(d, ignore_errors=True)


def test_monitor_page_names_its_engine_and_windows():
    """Every figure names its run and its engine (CLAUDE.md §0) -- the page
    included, or the next reader quotes an hour for the wrong commit."""
    from monitor import status as monstatus
    d = tmpdir()
    root = _monitor_root("0914-healthy-hour", d)
    rows = _fixture("0914-healthy-hour")
    start = {"ts": float(rows[0]["ts"]) - 1, "kind": "engine_start",
             "engine": "abcdef0123456789abcdef0123456789abcdef01", "dirty": False,
             "rungs": ["r"]}
    with open(os.path.join(root, "journal.jsonl"), "w", encoding="utf-8") as f:
        for r in [start] + rows:
            f.write(json.dumps(r) + "\n")
    md, data, rc = monstatus.run_once(root, repo=None, now=float(rows[-1]["ts"]))
    check("page: the running engine's commit is on the first lines",
          "abcdef0" in md.split("## Alarms")[0], md[:400])
    labels = [w["label"] for w in data["windows"]]
    check("page: a 'since start' window exists once a start is known",
          any(l.startswith("since start") for l in labels), labels)
    check("page: and that window names the engine that produced it",
          any("abcdef0" in w["engines"] for w in data["windows"]
              if w["label"].startswith("since start")),
          str([(w["label"], w["engines"]) for w in data["windows"]]))
    check("page: restart_owed cannot tell without a repo and SAYS so",
          any(f["name"] == "restart_owed" and f["state"] == "CANNOT_TELL"
              for f in data["findings"]),
          str([f for f in data["findings"] if f["name"] == "restart_owed"]))
    check("page: the unsplit accept rate is nowhere on it",
          "accept rate" not in md.lower(), "")
    shutil.rmtree(d, ignore_errors=True)


def test_deploy_regression_compares_the_hour_after_a_start():
    """The habit automated: after a change ships, the hour after is held
    against the hour before on the correctness indicators, and the table is
    written ONCE. 2026-09-14 a hand-run watch found two parser costs within
    the hour; without it each would have been another nine-hour silence."""
    from monitor import detectors, status as monstatus
    rows = _fixture("0914-healthy-hour")
    t0 = float(rows[-1]["ts"]) + 30
    start = {"ts": t0, "kind": "engine_start", "engine": "b" * 40, "dirty": False,
             "rungs": ["r"]}
    shift = t0 - float(rows[0]["ts"]) + 5
    after = [dict(r, ts=float(r["ts"]) + shift) for r in rows]

    def journal(d, extra):
        root = _monitor_root("0914-healthy-hour", d)
        allrows = sorted(rows + [start] + after + extra, key=lambda r: float(r["ts"]))
        with open(os.path.join(root, "journal.jsonl"), "w", encoding="utf-8") as f:
            for r in allrows:
                f.write(json.dumps(r) + "\n")
        return root

    # Pending: the hour is not up.
    d = tmpdir()
    root = journal(d, [])
    md, data, rc = monstatus.run_once(root, repo=None, now=t0 + 600)
    f = [x for x in data["findings"] if x["name"] == "deploy_regression"][0]
    check("regression: before the hour is up it says WHEN it will compare",
          f["state"] == "INFO" and "compared" in f["msg"], f["msg"])
    check("regression: and writes no report yet",
          not os.path.isdir(os.path.join(root, "monitor", "regression")), "")

    # Control: the same hour twice -> nothing crossed, report written once.
    md, data, rc = monstatus.run_once(root, repo=None, now=t0 + 3660)
    f = [x for x in data["findings"] if x["name"] == "deploy_regression"][0]
    check("regression: an identical hour crosses no floor", f["state"] == "INFO"
          and "no correctness indicator" in f["msg"], f["msg"])
    regdir = os.path.join(root, "monitor", "regression")
    files = os.listdir(regdir) if os.path.isdir(regdir) else []
    check("regression: the comparison is written even when nothing moved",
          len(files) == 1 and files[0].startswith("bbbbbbb-"), files)
    check("regression: and names both engines in the page",
          "## Deploy regression -- engine `bbbbbbb` against `unknown`" in md, md[:200])
    monstatus.run_once(root, repo=None, now=t0 + 3700)
    check("regression: a second run does not rewrite it",
          len(os.listdir(regdir)) == 1, os.listdir(regdir))
    shutil.rmtree(d, ignore_errors=True)

    # The parser fault appears in the hour after: three tagged fences with no
    # block. That is the 2026-09-14 anchor regression's exact shape.
    d = tmpdir()
    faults = [{"ts": t0 + 600 * (i + 1), "kind": "exec_skip", "reason": "unclosed_fence",
               "lost": True, "detail": "marker present, no block"} for i in range(3)]
    root = journal(d, faults)
    md, data, rc = monstatus.run_once(root, repo=None, now=t0 + 3660)
    f = [x for x in data["findings"] if x["name"] == "deploy_regression"][0]
    check("regression: unclosed_fence appearing where there was none is WORSE",
          f["state"] == "ALARM" and "unclosed_fence" in f["msg"], f["msg"])
    check("regression: a regression needs a human, so the run exits 1", rc == 1, rc)
    rep = open(os.path.join(root, "monitor", "regression",
                            os.listdir(os.path.join(root, "monitor", "regression"))[0]),
               encoding="utf-8").read()
    check("regression: the report carries the table and the verdict",
          "| unclosed_fence" in rep and "ALARM" in rep, rep[:300])
    shutil.rmtree(d, ignore_errors=True)

    # Too few cycles on one side is CANNOT TELL, never OK.
    ctx = detectors.Context([start] + after[:6], now=t0 + 3660)
    f = detectors.deploy_regression(ctx)
    check("regression: too few cycles is 'cannot tell', not a clean bill",
          f.state == detectors.CANNOT_TELL and "too few" in f.msg, f.msg)


def test_the_evidence_pack_is_hashed_and_refuses_secrets():
    """No figure in §7 was checkable by anyone not present, for two days
    after an outside review said so. A pack is the journal and its
    instruments with a manifest that hashes every file, so a quoted number
    can be traced to bytes. And it REFUSES to exist if anything key-shaped
    is inside -- the repo is public and the creature can `cat` a key file."""
    from monitor import pack
    d = tmpdir()
    root = _monitor_root("0914-healthy-hour", d)
    os.makedirs(os.path.join(root, "monitor", "regression"))
    with open(os.path.join(root, "monitor", "regression", "x.md"), "w") as f:
        f.write("# a report\n")
    out = os.path.join(d, "evidence")
    tar_path, man_path, man = pack.build(root, out, "run-t", repo_head="abc",
                                         now=float(_fixture("0914-healthy-hour")[-1]["ts"]))
    check("pack: tarball and manifest are written side by side",
          os.path.isfile(tar_path) and os.path.isfile(man_path), (tar_path, man_path))
    paths = {f["path"] for f in man["files"]}
    check("pack: the journal, the tools and the regression reports are inside",
          {"journal.jsonl", "context.md", "quota.json", "body/mind/tools/own/plan",
           "monitor/regression/x.md"} <= paths, sorted(paths))
    check("pack: every file carries a sha256 and the manifest counts the kinds",
          all(len(f["sha256"]) == 64 for f in man["files"])
          and man["journal"]["kinds"].get("wake") == 19, str(man["journal"])[:200])
    check("pack: the manifest hashes the tarball itself",
          len(man.get("tarball_sha256", "")) == 64, man.get("tarball_sha256"))
    check("pack: verify finds nothing wrong with a fresh pack",
          pack.verify(tar_path, man_path) == [], pack.verify(tar_path, man_path))
    # Tamper with the manifest: a changed hash must be caught.
    m2 = json.load(open(man_path, encoding="utf-8"))
    m2["files"][0]["sha256"] = "0" * 64
    json.dump(m2, open(man_path, "w", encoding="utf-8"))
    check("pack: a manifest that lies is caught by verify",
          any("differs" in p for p in pack.verify(tar_path, man_path)),
          pack.verify(tar_path, man_path))
    # THE FALSE POSITIVE THAT REFUSED THE FIRST LIVE PACK: 216 "keys" that
    # were the creature's tool `subta|sk-log-filter-by-parent`, plus hashes.
    # A checker that cannot tell a tool name from a credential is CLAUDE.md
    # §5's oldest fault, here in the tool meant to keep credentials out of a
    # public repo. Tool names, hex hashes and ordinary prose must pass.
    own = os.path.join(root, "body", "mind", "tools", "own")
    with open(os.path.join(own, "subtask-log-filter-by-parent"), "w") as f:
        f.write("#!/usr/bin/env python3\n# does: subtask-log-filter-by-parent-task-id "
                "filters the subtask-log-filter-by-parent output\n"
                "print('%s')\n" % ("a" * 20 + "0123456789abcdef" * 4))
    out2 = os.path.join(d, "evidence2")
    try:
        pack.build(root, out2, "run-v", now=2.0)
        ok = True
    except pack.PackRefused as e:
        ok = False
        why = str(e)
    check("pack: a tool named subtask-log-filter-by-parent is NOT a key",
          ok, "" if ok else why[:200])
    check("pack: and a 64-hex hash is a hash, not a key",
          not pack.scan_secrets([("h", os.path.join(own, "subtask-log-filter-by-parent"))]),
          pack.scan_secrets([("h", os.path.join(own, "subtask-log-filter-by-parent"))]))

    # A key-shaped string anywhere in the evidence refuses the whole pack --
    # each provider shape this engine uses, at a word boundary.
    os.makedirs(os.path.join(root, "body", "mind", "data"), exist_ok=True)
    before = set(os.listdir(out))
    for shape in ("AIza" + "Q" * 35, "gsk_" + "Ab1" * 8, "sk-" + "Zy9" * 8,
                  "sk-proj-" + "Q7" * 12, "hf_" + "Kx3" * 8):
        with open(os.path.join(root, "body", "mind", "data", "notes.txt"), "w") as f:
            f.write("found this: %s in a file\n" % shape)
        try:
            pack.build(root, out, "run-u", now=1.0)
            refused = False
        except pack.PackRefused as e:
            refused = "by shape" in str(e)
        check("pack: a %s… key refuses the pack, and the message names the shape"
              % shape[:4], refused, shape[:12])
    check("pack: and nothing was written by any refused attempt",
          set(os.listdir(out)) == before, sorted(set(os.listdir(out)) - before))
    shutil.rmtree(d, ignore_errors=True)


def test_the_probe_never_defaults_to_the_last_name():
    """`tools_after[-1]` sent the cousin to the alphabetically LAST tool on
    every visit that was not about a fresh write. Measured over run 2
    (2026-09-15): `plan` 30 times on 09-13, `view-subtask-logs` 28 of 30
    non-write visits in eighteen hours -- each ACCEPTED on its usage line,
    each followed by the same want, six times, and five different tools built
    to answer it. The framework manufactured the day's twins.

    There is no default now. The reason is a recorded fact (`picked_by`), and
    with nothing else to go on successive visits WALK the library.
    """
    d = tmpdir()
    j = Journal(os.path.join(d, "journal.jsonl"))

    class Stub:
        mind = d
    e = Engine(j, Stub(), "brief", None, None, os.path.join(d, "context.md"))
    lib = ["archive", "plan", "view-subtask-logs"]
    got = e.choose_target([("plan list", 0), ("echo done", 0)], lib, lib)
    check("target: a library tool the creature invoked is chosen, with the reason",
          got == ("plan", "ran"), got)
    got = e.choose_target([("python3 tools/own/archive query x", 0)], lib, lib)
    check("target: a tool named by its path counts as invoked",
          got == ("archive", "ran"), got)
    seen = []
    for _ in range(3):
        name, how = e.choose_target([("echo nothing", 0)], lib, lib)
        seen.append((name, how))
        j.append("cousin_probe", tool=name, exit_code=2, bare=True, picked_by=how)
    check("target: with nothing to go on the reason is least_probed",
          all(h == "least_probed" for _n, h in seen), seen)
    check("target: three such visits reach three different tools -- it walks, "
          "it does not sit", len({n for n, _h in seen}) == 3, seen)
    check("target: the alphabetically last tool is reached by rotation, never "
          "first by position", seen[0][0] != "view-subtask-logs", seen)
    check("target: pick_target still answers with the name",
          e.pick_target([("plan list", 0)], lib, lib) == "plan")
    check("target: a new tool still wins",
          e.choose_target([("plan list", 0)], lib + ["fresh"], lib) == ("fresh", "new"))
    check("target: a written tool beats one merely run",
          e.choose_target([("plan list", 0), ("tool-edit archive", 0)], lib, lib)
          == ("archive", "written"))
    shutil.rmtree(d, ignore_errors=True)


def test_no_tool_is_ever_hidden_from_the_listing():
    """The limit bounds the FULL entries, never the names. 2026-09-15 07:00:
    the library crossed 40 and the seven tools past the alphabetical cut --
    every tool the creature built that day to answer one want -- were shown
    to nobody, so it built a sixth. A bound on context size degrades the
    listing; it never hides from it."""
    e, j, b, d = build_engine(["thinking, no commands"], [])
    own = os.path.join(b.mind, "tools", "own")
    names = ["tool-%02d" % i for i in range(45)]
    for n in names:
        _write_tool(own, n, does="does %s" % n, call="%s <x>" % n)
    out = library.render(own, j)
    check("listing: every tool is named, past the limit too",
          all(("- %s" % n) in out for n in names), out[-400:])
    head, _sep, tail = out.partition("Also here, by name and purpose only")
    check("listing: the first %d carry their full record" % library.LIBRARY_LIMIT,
          head.count("used as:") == library.LIBRARY_LIMIT, head.count("used as:"))
    check("listing: the rest carry name and purpose, one line each, no run record",
          _sep and "used as:" not in tail and "does tool-44" in tail
          and "(5 more" in tail, tail[:300])
    e.run_cycle()
    w = j.read(kinds=["wake"])[-1]
    check("served: the wake says how many were named, shown in full, and exist",
          w.get("library_named") == 45 and w.get("library_shown") == 40
          and w.get("library_total") == 45, str(w))
    b.destroy()
    shutil.rmtree(d, ignore_errors=True)


def test_the_monitor_unit_is_read_only_over_the_evidence():
    """The unit is what makes 'writes only its own directory' impossible to
    violate rather than merely untested. Directives are asserted by SECTION
    and by VALUE, because a StartLimit in the wrong section once passed a
    test that only looked for the string (CLAUDE.md §5)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = open(os.path.join(here, "deploy", "cousin-monitor.service"),
                encoding="utf-8").read()
    timer = open(os.path.join(here, "deploy", "cousin-monitor.timer"),
                 encoding="utf-8").read()
    sections, cur = {}, None
    for line in unit.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s
            sections.setdefault(cur, [])
        elif s and not s.startswith("#") and cur:
            sections[cur].append(s)
    svc = sections.get("[Service]", [])
    check("unit: PrivateUsers=yes is in [Service], or nothing below it works",
          "PrivateUsers=yes" in svc, svc)
    check("unit: home is read-only and the system strict",
          "ProtectHome=read-only" in svc and "ProtectSystem=strict" in svc, svc)
    rw = [l for l in svc if l.startswith("ReadWritePaths=")]
    check("unit: the ONLY writable path is live/monitor",
          rw and all(l.endswith("/live/monitor") for l in rw), rw)
    check("unit: the spine is unreachable from it",
          any(l.startswith("InaccessiblePaths=") and "growing-spine" in l
              for l in svc), svc)
    check("unit: it runs the monitor's status command, read-only flags none",
          any(l.startswith("ExecStart=") and "-m monitor status" in l for l in svc),
          svc)
    # FROM THE MODULE, never typed: a producer and a checker that each carry
    # their own copy of a number drift, and this pair decides whether a
    # `failed` unit means "the engine needs you" or "the monitor is dead".
    from monitor import status as monstatus
    check("unit: the alarm exit code is declared a SUCCESS, so `failed` means "
          "the monitor itself broke and nothing else",
          "SuccessExitStatus=%d" % monstatus.EXIT_ALARM in svc, svc)
    check("unit: the mkdir runs OUTSIDE the sandbox (+), or the read-only live/ "
          "refuses it", any(l.startswith("ExecStartPre=+") for l in svc), svc)
    check("timer: every five minutes, persistent",
          "OnUnitActiveSec=5min" in timer and "Persistent=true" in timer, timer)


def main():
    t0 = time.time()
    for fn in (test_monitor_detectors_fire_where_the_scars_happened,
               test_monitor_writes_only_its_own_directory,
               test_monitor_alarms_are_edge_triggered,
               test_the_brief_can_be_scored_against_cases_it_never_saw,
               test_the_docker_body_carries_the_contract_the_creature_is_promised,
               test_the_docker_drill_proves_the_keys_are_out_of_reach,
               test_a_ladder_with_every_rung_walled_never_reads_as_a_wait,
               test_the_rehearsal_cannot_touch_the_live_run,
               test_the_drills_give_the_unproven_detectors_their_red,
               test_the_giveup_drill_proves_the_chain_systemd_owns,
               test_the_census_runs_by_itself,
               test_the_chat_channel_is_a_scheduled_intention,
               test_the_inherited_library_is_recorded_as_not_executed,
               test_the_cousins_audit_has_a_named_trigger,
               test_the_evidence_tarballs_home_is_recorded,
               test_a_broken_monitor_does_not_report_as_a_finding,
               test_monitor_page_names_its_engine_and_windows,
               test_the_monitor_unit_is_read_only_over_the_evidence,
               test_the_probe_never_defaults_to_the_last_name,
               test_no_tool_is_ever_hidden_from_the_listing,
               test_deploy_regression_compares_the_hour_after_a_start,
               test_the_evidence_pack_is_hashed_and_refuses_secrets,
               test_the_journal_names_the_engine_that_wrote_it,
               test_a_wake_records_what_was_served,
               test_the_selfcheck_proves_effects_and_never_vetoes,
               test_loop_end_says_whether_it_gave_up,
               test_a_fence_inside_the_code_does_not_close_the_block,
               test_a_usage_refusal_is_not_counted_as_a_failure,
               test_the_creature_is_told_to_repair_rather_than_delete_or_panic,
               test_a_tool_that_never_worked_says_so_to_both_inhabitants,
               test_the_brief_tests_whether_the_handover_could_be_completed,
               test_a_want_survives_until_the_creature_has_had_a_turn,
               test_no_document_hard_codes_the_gate_count,
               test_the_module_list_matches_the_kernel,
               test_the_creatures_shell_does_not_inherit_the_engines_secrets,
               test_every_defined_test_is_registered,
               test_giving_up_is_distinguishable_from_stopping,
               test_the_engine_unit_runs_the_creature_in_a_container,
               test_the_unit_bounds_its_own_restarting,
               test_a_cap_downstream_never_exceeds_the_cap_upstream,
               test_a_reply_with_no_verdict_falls_through_to_the_next_rung,
               test_an_unreadable_verdict_says_which_of_three_things_went_wrong,
               test_a_want_is_discharged_by_the_visit_that_answers_it,
               test_quoted_text_in_a_bare_fence_is_not_a_command,
               test_the_creature_is_shown_its_own_library_every_wake,
               test_a_think_keeps_the_reply_that_produced_it,
               test_library_marks_a_tool_its_user_has_never_run,
               test_library_counts_only_its_users_runs,
               test_library_never_withholds_a_tool_that_failed,
               test_journal, test_history_never_cuts_mid_line,
               test_a_marker_says_whose_cut_it_is,
               test_marker_invariant, test_body,
               test_command_reaches_disk_intact,
               test_observer_describes_every_kind_it_can_see,
               test_vitals_never_aggregates_across_rungs,
               test_observer_shell_assembles,
               test_observer_stop_button_states,
               test_observer_vitals_are_derived,
               test_forever_stops_when_asked,
               test_forever_does_not_spin_on_failure,
               test_expected_refusals_are_not_called_errors,
               test_the_same_rung_is_never_knocked_twice_without_a_gap,
               test_a_spent_rung_is_remembered_not_rediscovered,
               test_the_cousin_is_never_sent_to_a_tool_that_does_not_exist,
               test_the_two_agents_share_one_queue,
               test_a_visit_that_never_happened_does_not_consume_its_trigger,
               test_an_exhausted_ladder_reaches_the_supervisor,
               test_preflight_is_advisory_for_an_unattended_run,
               test_a_quota_wall_is_not_a_fault,
               test_ladder_reports_why_it_was_exhausted,
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
               test_temperature_is_configurable_and_defaults_to_zero,
               test_classify_error_never_raises, test_ladder_routes_and_records,
               test_resume_is_derived_from_the_journal,
               test_resume_matches_a_live_run,
               test_history_can_never_parse_as_a_command,
               test_cousin_sees_the_library,
               test_an_unreadable_verdict_keeps_its_evidence,
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
