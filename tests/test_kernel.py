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
import shutil
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
        "tools_changed": {"added": ["grep_tool"], "removed": []},
        "rung_declined": {"rung": "gemini", "reason": "quota (429)",
                          "expected": True},
        "rung_broken": {"rung": "groq", "reason": "credential rejected",
                        "expected": False},
        "think_deferred": {"where": "think", "detail": "LadderExhausted"},
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
    check("raw: an unreadable verdict is recorded as UNKNOWN",
          rec.get("verdict") == cousin.UNKNOWN and rec.get("error") == "no-block",
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
    check("library column: and carries the exit code it really saw",
          "exited 0" in out2, out2)

    j.append("cousin_probe", tool="taskprio", exit_code=1,
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
    j.append("cousin_probe", tool="archive", exit_code=127, stdout="",
             stderr="not found")

    out = library.render(own, j)
    check("library column: a tool its user could not run is STILL listed",
          "archive" in out and "exited 127" in out, out)
    check("library column: and is still a tool as far as the kernel is concerned",
          "archive" in triggers.list_tools(own), triggers.list_tools(own))


def main():
    t0 = time.time()
    for fn in (test_the_creature_is_shown_its_own_library_every_wake,
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
