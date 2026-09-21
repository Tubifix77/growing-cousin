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
# A THIRD STATE, because this suite demands one of every detector it ships.
# `a container body needs a POSIX host` is not a defect in the code under
# test; it is a fact about the host running the suite, and reporting it as a
# failure is what made the Windows gate unreadable long after the real fault
# (PLAN 18.8) was fixed. Skips are printed loudly and counted in the final
# line, so a skip on the authority box -- where nothing should skip -- is
# visible rather than quiet.
CANNOT = []
_CAPS = {}


def host_missing(*caps):
    """Which of `caps` this HOST does not have. Empty tuple means run it."""
    missing = []
    for c in caps:
        if c not in _CAPS:
            _CAPS[c] = _detect(c)
        if not _CAPS[c]:
            missing.append({"posix": "a POSIX host",
                            "docker": "a docker daemon",
                            "posix_python": "a POSIX python3 the body's shell "
                                            "can run"}.get(c, c))
    return missing


def _detect(cap):
    if cap == "posix":
        return hasattr(os, "getuid")
    if cap == "docker":
        return bool(shutil.which("docker"))
    if cap == "posix_python":
        # ASK THE SHELL, never assume -- the same rule `_probe_prefix` learned
        # the hard way. On Windows `python3` is usually the Store stub, which
        # prints an advert and exits non-zero, and every hand is a python
        # script with a `#!` line.
        d = tempfile.mkdtemp(prefix="cousin-cap-")
        try:
            b = bodymod.LocalBody(os.path.join(d, "body"))
            r = b.run("python3 -c 'print(1)'", timeout=30)
            return r.code == 0 and "1" in (r.stdout or "")
        except Exception:
            return False
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return False


def cannot_run(name, why):
    CANNOT.append((name, why))
    print("SKIP %s -- needs %s" % (name, why))


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


def test_the_history_does_not_shrink_a_marker_it_re_cuts():
    """The second cut is real, and it is not the test's -- it is the history's.

    `exec_end.stdout` is stored as `capped(stdout, EXEC_STDOUT_CHARS)`, so a
    long output is stored at the cap PLUS a marker. `render_history` then calls
    `capped` on that stored text again with the same limit, which is smaller
    than what it was handed. Until 2026-09-21 the second cut reported only what
    IT removed: measured over the live journal, **74 of 652 marked outputs,
    worst case telling the creature 146 characters were withheld when the truth
    was 6,114.**

    `test_marker_invariant` was green throughout, because it passes
    `already_cut` by hand and the one real caller never did. *A test suite
    proves what it asserts and nothing more.*

    Why this is not cosmetic: on 2026-09-12 this creature read a marker saying
    3,332 characters were cut, concluded *"It's clearly truncated. The tool is
    broken."*, and rewrote two working tools shorter. A marker understating the
    loss by six thousand characters is the same instrument lying in the other
    direction -- and a small number where a large one belongs reads as
    reassurance.
    """
    e, j, b, d = build_engine([], [])
    long_out = "\n".join("line %04d %s" % (i, "z" * 60) for i in range(900))
    stored = capped(long_out, EXEC_STDOUT_CHARS)
    truth = marker_total(stored)
    check("history: the stored record already carries a real loss",
          truth > 1000, truth)
    check("history: and it is longer than the history's own window, so the "
          "history MUST cut it again",
          len(stored) > e.HISTORY_OUTPUT_CHARS,
          (len(stored), e.HISTORY_OUTPUT_CHARS))

    j.append("exec_start", cmd="cat big")
    j.append("exec_end", exit_code=0, stdout=stored, stderr="")
    h = e.recent_block(cycles=2)

    shown = 0
    for ln in h.split("\n"):
        t = marker_total(ln.replace(e.HISTORY_QUOTE, "", 1).rstrip())
        if t:
            shown = max(shown, t)
    check("history: a marker survives the second cut at all", shown > 0,
          h[-400:])
    check("history: and it reports the TOTAL withheld, never only its own "
          "share", shown >= truth,
          "history says %d, the truth is %d" % (shown, truth))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_cut_that_removes_nothing_removes_nothing():
    """`capped` trimmed to a line boundary even when the text already fitted,
    so long as some earlier loss was being carried: it reported that loss
    honestly and then quietly dropped the last line of text that fitted.

    Found 2026-09-21 by reading the function rather than by any failure --
    `already_cut` was never passed by a real caller, which is exactly why the
    branch could survive.
    """
    # The branch needs a text that FITS and whose last newline is past half
    # the window -- otherwise the line-boundary trim is never reached and the
    # test proves nothing. Sweep the shape rather than picking one case.
    limit = 1000
    bad = []
    for tail in (1, 5, 40, 120):
        text = ("x" * (limit - tail - 60)) + "\n" + ("y" * tail)
        out = capped(text, limit, already_cut=7)
        if not out.startswith(text):
            bad.append((tail, len(text), len(out)))
    check("caps: text that fits is returned WHOLE even while an earlier loss "
          "is being carried -- a cut that removes nothing removes nothing",
          not bad, bad)
    check("caps: and the earlier loss is still reported rather than dropped",
          marker_total(capped("short", limit, already_cut=7)) == 7,
          marker_total(capped("short", limit, already_cut=7)))


def test_a_reply_with_no_text_at_all_is_not_an_answer():
    """The two ladders need DIFFERENT predicates and both need one.

    The cousin's rejects a reply with no verdict block. The creature's passed
    none, deliberately and correctly: *a think with no command is a real
    answer*, and rejecting one would wall a rung for thinking out loud.

    **But a reply with no text at all is not a think.** This project wrote that
    down on 2026-09-10, about a different rung, and never applied it here:

    > An empty reply that consumed its whole budget is a FAILURE, never an
    > answer... such a call registers as a SUCCESS, so nothing walls the rung
    > and nothing below it is ever reached -- the manager is silently absent
    > rather than visibly broken.

    So the engine contradicted itself across two files: `classify_no_blocks`
    called the same reply `budget_spent` and put it in LOST, while the ladder
    banked it as the answer and never tried the rung below. Measured over run
    2 on 2026-09-21: **9 of 1,967 thinks came back with no text at all** --
    seven gemini at `finish=length`, two groq at `finish=stop`, which is the
    reasoning-only shape the spine's provider has handled since 2026-08. Nine
    cycles, each thrown away with a working rung sitting underneath.

    The predicate belongs to the QUESTION, not to the agent -- so this one
    rejects EMPTINESS and nothing else. A reply with text and no command is
    still an answer, and that is asserted here rather than left to be trusted.
    """
    from kernel.think import unusable_think

    check("empty: a reply with text and NO COMMAND is still a real answer",
          unusable_think("I looked and there is nothing to do today.", {})
          is None)
    check("empty: text that is only whitespace is not text",
          unusable_think("   \n  ", {}) is not None)
    check("empty: nothing at all, having spent the whole budget, is a failure",
          unusable_think("", {"done_reason": "length"}) is not None)
    check("empty: and it says WHICH emptiness, because the two have "
          "different fixes",
          unusable_think("", {"done_reason": "length"})
          != unusable_think("", {"done_reason": "stop"}),
          (unusable_think("", {"done_reason": "length"}),
           unusable_think("", {"done_reason": "stop"})))
    check("empty: a reply that was ALL reasoning and nothing else is named as "
          "that, not as silence",
          "reasoning" in (unusable_think("", {"chars_before_strip": 4000,
                                              "chars_stripped": 4000}) or ""),
          unusable_think("", {"chars_before_strip": 4000,
                              "chars_stripped": 4000}))

    # AND THE LADDER HOPS ON IT. The predicate existing is not the fix; the
    # creature's ladder being given it is.
    calls = []

    def dead(prompt):
        calls.append("dead")
        return "", {"done_reason": "length"}

    def alive(prompt):
        calls.append("alive")
        return "I will look at the plan.", {"done_reason": "stop"}

    ask = backends.ladder([("dead", dead), ("alive", alive)],
                          reject=unusable_think, sleep=lambda s: None)
    text, meta = ask("go")
    check("empty: the ladder steps past a rung that returned nothing",
          calls == ["dead", "alive"] and meta.get("rung") == "alive",
          (calls, meta.get("rung")))
    check("empty: and returns the reply that actually said something",
          "plan" in text, text)


def test_a_tools_own_words_cannot_declare_the_body_dead():
    """`exec_setup_failure` decides whether the creature RAN something or
    whether the framework failed to start it, and it decides by looking for
    phrases anywhere in stdout and stderr. **"is not running" is ordinary
    English.** A tool reporting `worker is not running` and exiting 0 would
    have had its output thrown away, its exit code relabelled as a broken
    body, and -- for a cousin probe -- its verdict never asked for.

    Read against the spine's version of the same function, which asks
    `if code == 0: return False` first and says why: *125-128 are also
    legitimate exit codes for a command that really did run*. Ours did not.
    Measured over the live journal 2026-09-21 before changing anything: **0
    hits in 2,929 records**, so this is a latent hazard and not a live
    defect, and it is recorded as such.

    The same guard is what makes it safe to add the marker this engine is
    actually exposed to. It runs with `--pids-limit 256`, so a fork storm
    gets `resource temporarily unavailable` from docker -- the command never
    started, and without the marker that diagnostic reaches the cousin shaped
    exactly like the tool's own output. That is §2.5 with the framework as
    author, and the spine paid three and a half hours of silent outage for
    the lesson.
    """
    check("body: a command that SUCCEEDED did not fail to start, whatever it "
          "printed",
          not bodymod.exec_setup_failure("the worker is not running", "", 0))
    check("body: nor when the phrase is on stderr",
          not bodymod.exec_setup_failure("", "container not found in registry", 0))
    check("body: a real OCI failure is still a broken body",
          bodymod.exec_setup_failure("", "OCI runtime exec failed: ...", 126))
    check("body: and a fork storm hitting the pids limit is the body, not the "
          "tool -- this engine runs with --pids-limit 256",
          bodymod.exec_setup_failure(
              "", "OCI runtime exec failed: fork/exec: resource temporarily "
                  "unavailable", 126))
    check("body: a tool that exits non-zero for its own reasons is NOT a "
          "broken body",
          not bodymod.exec_setup_failure("usage: plan <cmd>", "", 2))


def test_the_parser_under_adversarial_replies():
    """Synthetic edge cases through the real parser, 2026-09-21.

    Read beside `executive/parser.py` in Growing Spine, which is 25 lines to
    our 160. The difference is entirely scar tissue, and this asserts the
    shape of each scar rather than trusting the comment above it.

    Where an answer here is deliberately different from the spine's, the
    reason is stated. Where it is a KNOWN GAP with no live occurrences, that
    is stated too, with the measurement and the date, because a gap nobody
    wrote down is one the next session rediscovers from scratch.
    """
    F = "```"
    P = think.parse_blocks

    check("edge: the ordinary case still works", P(F + "bash\nls\n" + F) == ["ls"])
    check("edge: `sh` is accepted as well as `bash`",
          P(F + "sh\nls\n" + F) == ["ls"])
    check("edge: trailing spaces after the tag do not hide a command",
          P(F + "bash   \nls\n" + F) == ["ls"])
    check("edge: an opener mid-line still opens -- the 09-14 asymmetry, which "
          "cost a real command forty minutes after the fix that caused it",
          P("...</thought>" + F + "bash\nls\n" + F) == ["ls"])
    check("edge: a closing fence that does NOT start its own line cannot "
          "close a block", P(F + "bash\nls\n   " + F) == [])
    check("edge: an empty block is not a command", P(F + "bash\n\n" + F) == [])
    check("edge: nor a block of whitespace", P(F + "bash\n   \n" + F) == [])
    check("edge: an untagged fence is never executed -- the creature is told "
          "to mark its actions and quoted text is not made executable by "
          "sitting between backticks",
          P(F + "\nrm -rf /\n" + F) == [])
    check("edge: neither is ```python, which is 1,256 of the column-0 fences "
          "in this run", P(F + "python\nprint(1)\n" + F) == [])

    # CRLF IS A KNOWN GAP AND STAYS ONE, and the story of why is the most
    # expensive thing in this test. The spine's parser accepts CRLF; ours does
    # not, because `[ \t]*` after the tag matches no carriage return. Measured
    # over the live journal 2026-09-21: **0 replies of 1,926 contain CRLF.**
    #
    # A fix was written, shipped and REVERTED the same night. It added `\r?`
    # at both ends; the closing end became `^```\r?$`, and `$` under re.M
    # means the fence must now END its line. An independent verifier replayed
    # it over every raw reply in run 2: **9 parsed differently**, the block
    # swallowing more each time. The measured risk was 0 and the measured cost
    # was 9.
    #
    # *Trigger to revisit: the first reply that actually contains CRLF.*
    check("edge: a CRLF reply is NOT parsed, and that is the recorded state "
          "rather than an oversight",
          P(F + "bash\r\nls\r\n" + F) == [])
    check("edge: and it is LOST rather than silently absent, which is the "
          "only reason the gap is tolerable",
          think.classify_no_blocks(F + "bash\r\nls\r\n" + F)[0]
          == "unclosed_fence")

    # THE THREE SHAPES THE REVERT PROTECTS. Each is what the `\r?$` version
    # got wrong, asserted here so the next attempt cannot ship without meeting
    # them. They are cheap, and none of them was in the suite before.
    check("edge: a closing fence with trailing whitespace still closes -- the "
          "opener tolerates it, so the closer must, and trailing whitespace "
          "is ordinary model output",
          P(F + "bash\nls\n" + F + "  ") == ["ls"])
    check("edge: and with trailing whitespace before a newline",
          P(F + "bash\nls\n" + F + "  \nmore prose") == ["ls"])
    swallow = P("\n".join([
        F + "bash", "remember current-phase done",
        F + "</thought>" + F + "bash", "remember current-phase done", F]))
    check("edge: two commands separated by a mid-line opener stay TWO -- this "
          "exact shape is one of the nine the reverted change broke, where "
          "they became one block carrying a literal fence",
          swallow == ["remember current-phase done"] * 2, swallow)

    # DUPLICATES. The spine de-duplicates identical blocks inside one reply and
    # says why: running the same thing N times is pure waste. We deliberately
    # do NOT, and the reason is this project's division of labour: deciding
    # that a repeated command was not meant twice is a judgement about intent,
    # and the framework holds bounds, not judgement. The creature sees both
    # runs in its own transcript and can act on that; we would be silently
    # dropping work it asked for. Measured 2026-09-21 before deciding: 26 of
    # 1,927 replies repeat a block, almost all of them `cat`.
    check("edge: a block written twice runs twice, on purpose",
          P(F + "bash\na\n" + F + "\n" + F + "bash\na\n" + F)
          == ["a", "a"])

    # KNOWN GAP, recorded rather than patched at three in the morning. A fence
    # at column 0 INSIDE a heredoc body still closes the block, so a tool whose
    # source contains one would land cut -- the 2026-09-14 scar's remaining
    # half. Measured the same day over every uncut reply in run 2: **0 real
    # occurrences in 1,588.** The five the first pass found were all the
    # creature quoting its own `| `-prefixed transcript, and the 192 the pass
    # before that found were the journal's own 800-character cap on `cmd`.
    # Trigger to act: the first real one, or any SyntaxError in a tool whose
    # source contains a column-0 fence.
    cut = P(F + "bash\ncat > t <<'EOF'\n" + F + "\nEOF\n" + F)
    check("edge: the heredoc gap is where it is believed to be, so a fix can "
          "be recognised as one", cut == ["cat > t <<'EOF'"], cut)

    # CLASSIFICATION. Three emptinesses and three fixes, which is the whole
    # reason this module is not five lines.
    cl = lambda t, f=None: think.classify_no_blocks(t, f)[0]
    check("edge: nothing at all, with the ceiling hit, is the budget",
          cl("", "length") == "budget_spent")
    check("edge: nothing at all, complete, is an empty reply",
          cl("", "stop") == "empty_reply")
    check("edge: text that hit the ceiling is TRUNCATED, never 'no command'",
          cl("I was about to", "length") == "truncated")
    check("edge: a tagged marker with no parsed block is work LOST",
          cl("see " + F + "bash and then nothing") == "unclosed_fence")
    check("edge: a fence with no tag is its own answer, not silence",
          cl(F + "\nx\n" + F) == "untagged_fence")
    check("edge: and only the three that LOST work count as lost",
          [think.commands_were_lost(x) for x in
           ("budget_spent", "truncated", "unclosed_fence", "untagged_fence",
            "no_command", "empty_reply")]
          == [True, True, True, False, False, False])


def test_a_command_the_shell_cannot_be_given_is_not_a_broken_body():
    """A NUL byte in a command makes `subprocess` raise ValueError before the
    process exists. That left by the generic handler as `setup_failed=True`,
    exit 128 -- so the framework would have declared the BODY broken, respawned
    it, and (on the cousin's side) thrown the probe away as LOST, all because
    of a byte in the creature's own text.

    A fabricated infrastructure failure, authored by us, out of the creature's
    words: §2.5 from the inside. Never observed live -- a model has to work to
    emit a NUL through JSON -- and fixed because the cost of being wrong is a
    body respawn and a discarded visit, while the fix is one branch.
    """
    d = tempfile.mkdtemp()
    b = bodymod.DockerBody("growing-cousin-no-such", image="x", mind=d)
    r = b.run("echo one\x00two")
    check("nul: the body is not blamed", not r.setup_failed, r)
    check("nul: it is reported as the command being unrunnable",
          r.code != 0 and "null" in (r.stderr or "").lower(), (r.code, r.stderr))
    check("nul: and stdout stays empty, so nothing reaches the creature "
          "shaped like its own output", r.stdout == "", r.stdout)
    shutil.rmtree(d, ignore_errors=True)


def test_the_headline_metric_does_not_shrink_when_the_page_reads_a_tail():
    """`derive.load` reads the last `TAIL_BYTES` of the journal, not the whole
    file, and says so with `complete=False`. Every other figure on the page is
    a count over a recent window, so a tail costs them nothing.

    **The headline metric is not a count over a window. It is a SPAN OF DAYS**
    -- first use to last use, against a seven-day bar -- so the moment the
    journal outgrows the tail, the early half of every span silently
    disappears and tools that HAD survived start reporting that they had not.
    The number would go down, and the reason would be ours.

    Measured 2026-09-21: the journal is 14.6 MB and grows about 1.8 MB a day
    against a 24 MB tail, so **the crossing is around 2026-09-26** -- days
    after the metric's first real week closes on the 25th. Found by reading
    `load` and `surviving_capability` next to each other rather than by any
    failure, which is the only way this class is ever found: the answer stays
    clean-looking and only the meaning changes.

    Two things are asserted, in this order, because the second is the one that
    matters: the metric must be ABLE to see the whole history, and when it
    cannot it must say CANNOT TELL rather than report a loss.
    """
    from monitor import derive
    d = tmpdir()
    own = os.path.join(d, "tools", "own")
    os.makedirs(own)
    _write_tool(own, "old-faithful", does="the one that survived",
                call="old-faithful")
    jp = os.path.join(d, "journal.jsonl")
    j = Journal(jp)
    DAY = 86400.0
    T0 = 1_700_000_000.0
    # Its user reached for it on day 0 and again on day 9: a survivor by any
    # reading of the bar.
    for t in (T0, T0 + 9 * DAY):
        j.append("cousin_probe", tool="old-faithful", exit_code=0, bare=False,
                 cmd="old-faithful")
    rows = j.read()
    for i, r in enumerate(rows):
        r["ts"] = T0 if i == 0 else T0 + 9 * DAY
    now = T0 + 10 * DAY

    whole = derive.surviving_capability(rows, own, now=now)
    check("tail: with the whole journal the tool has survived",
          whole["surviving"] == 1, whole["surviving"])

    # Now the tail: the early probe is simply not in `rows` any more, and the
    # reader is told only that the file's start was not reached.
    tail = [r for r in rows if r["ts"] > T0 + DAY]
    cut = derive.surviving_capability(tail, own, now=now, complete=False)
    check("tail: a tail must NEVER report a tool as not-surviving on evidence "
          "that was cut away -- it is CANNOT TELL or it is nothing",
          cut["not_surviving"] == 0, cut)
    check("tail: and the page is told why, in words, rather than being handed "
          "a smaller number",
          "tail" in (cut.get("why_cannot_tell") or "").lower(),
          cut.get("why_cannot_tell"))

    # And the way out of cannot-tell: the metric may read the probes itself,
    # since a single-kind scan of the whole file is cheap and the span is the
    # whole subject.
    probes = derive.probe_history(jp)
    check("tail: the probes can be read from the file whatever its size",
          probes is not None and len(probes) == 2,
          None if probes is None else len(probes))
    for i, r in enumerate(probes or []):
        r["ts"] = T0 if i == 0 else T0 + 9 * DAY
    full = derive.surviving_capability(tail, own, now=now, complete=False,
                                       probes=probes, run_start=T0)
    check("tail: given them, the answer is the same as with the whole journal",
          full["surviving"] == 1 and full["not_surviving"] == 0, full)
    check("tail: and the run's age is the RUN's, not the tail's",
          abs(full["run_days"] - 10.0) < 0.1, full["run_days"])
    shutil.rmtree(d, ignore_errors=True)


def test_a_parser_change_can_be_replayed_before_it_ships():
    """The gate asserts shapes somebody thought of. **A parser change's cost
    is always in the shapes nobody thought of** -- three of the four changes
    ever made to this parser had one, and every one was found afterwards.

    The corpus that could catch it is the run's own replies, and those live
    only on the laptop: `raw` is raw model output and this repository is
    public. So the discipline is a command rather than an intention, and this
    asserts the command works -- including on a fixture whose `raw` was
    deliberately dropped, which must read as *no reply here* and never as *a
    parser that stopped working*.
    """
    import replay_parser

    d = tmpdir()
    jp = os.path.join(d, "j.jsonl")
    j = Journal(jp)
    F = "```"
    j.append("think", chars=10, finish="stop",
             raw=F + "bash\nls\n" + F)
    # The exact shape one of the nine live differences had: a closer
    # sharing its line with the next opener. Any change that stops
    # treating it as a closer swallows two commands into one.
    j.append("think", chars=10, finish="stop",
             raw="\n".join([F + "bash", "remember a",
                             F + "</thought>" + F + "bash",
                             "remember b", F]))
    j.append("think", chars=10, finish="stop", raw="just thinking out loud")
    j.append("think", chars=10, finish="stop", raw="[dropped from fixture]")
    j.append("exec_start", cmd="ls")

    # THE COUSIN'S SHELL IS PART OF THE CORPUS. `parse_blocks` also drives
    # `cousin.choose_invocation`, so a parser change meets those replies too
    # -- and the fifteen-hour outage of 2026-09-16 was on that side.
    j.append("cousin_probe", tool="plan", exit_code=0, bare=False,
             cmd="plan list", stdout="ok", stderr="",
             proposal="I would run ```bash\nplan list\n```")
    j.append("cousin_verdict", verdict="ACCEPTED", tool="plan",
             raw="<<<COUSIN\nverdict: ACCEPTED\nCOUSIN")

    seen = replay_parser.scan(jp)
    check("replay: it reads the replies that have text and skips the ones "
          "whose raw was dropped for the public repo", len(seen) == 5, seen)
    kinds = sorted({v["kind"] for v in seen.values()})
    check("replay: and it reads the COUSIN's replies, not only the "
          "creature's -- the parser serves both",
          kinds == ["cousin_probe", "cousin_verdict", "think"], kinds)

    base = os.path.join(d, "before.json")
    argv0 = list(sys.argv)
    try:
        sys.argv = ["replay_parser.py", jp, "--save", base]
        check("replay: saving a baseline succeeds", replay_parser.main() == 0)
        check("replay: and the baseline is on disk", os.path.exists(base))

        sys.argv = ["replay_parser.py", jp, "--against", base]
        check("replay: an unchanged parser compares clean",
              replay_parser.main() == 0)

        # NOTHING IN COMMON IS NOT "SAME". A baseline from a rotated journal,
        # or a wrong --against path, used to print "every shared reply parses
        # identically" and exit 0 having compared nothing -- this instrument
        # committing the fault it exists to prevent. Found by a verifier the
        # night it was written.
        empty = os.path.join(d, "stale.json")
        with io.open(empty, "w", encoding="utf-8") as f:
            f.write('{"think@1.0": {"n": 1, "digest": "x", "chars": 1}}')
        sys.argv = ["replay_parser.py", jp, "--against", empty]
        check("replay: a baseline with no reply in common CANNOT COMPARE, "
              "and says so instead of certifying a comparison it never made",
              replay_parser.main() == 2)
        missing = os.path.join(d, "nope.json")
        sys.argv = ["replay_parser.py", jp, "--against", missing]
        check("replay: and an unreadable baseline is the same answer",
              replay_parser.main() == 2)

        # Now change the parser under it, exactly as a real change would, and
        # prove the replay NOTICES.
        before_re = think.FENCE_RE
        try:
            think.FENCE_RE = re.compile(
                r"```(?:bash|sh)[ \t]*\n(.*?)^```\r?$", re.S | re.M)
            sys.argv = ["replay_parser.py", jp, "--against", base]
            check("replay: a parser change that alters a real reply is "
                  "REPORTED, which is the whole point -- the 2026-09-21 "
                  "revert happened because a verifier ran this by hand and "
                  "nothing else would have", replay_parser.main() == 1)
        finally:
            think.FENCE_RE = before_re
    finally:
        # RESTORED, because `observer.main` reads `sys.argv[1]` as its root
        # when none is passed. The first version of this test left a path to
        # a deleted temp directory there, and only the order of the
        # registration list kept it from mattering -- which is a position in
        # a list being a reason, the 2026-09-15 scar.
        sys.argv = argv0
    check("replay: and the module-level parser is the one the rest of the "
          "suite will use", think.FENCE_RE.pattern == before_re.pattern)
    shutil.rmtree(d, ignore_errors=True)


def test_the_block_level_trim_says_how_much_it_dropped():
    """The verifier's finding, 2026-09-21, an hour after the commit that said
    the marker invariant now held without the caller remembering.

    It held for the per-output cut. `recent_block` then bounds the WHOLE
    transcript with `block[-HISTORY_TOTAL_CHARS:]` and announces it with
    *(Older lines dropped; this is the most recent part.)* -- **no number at
    all.** Demonstrated at that commit with two capped outputs in one cycle:
    4,727 characters vanished, including a whole `$ cat big0` line and the
    first 65 lines of its output, while both surviving markers still claimed
    exactly 55,948.

    So the per-output marker now understates by whatever the block trim took,
    which is the identical fault one level up -- and the new test could not
    see it, because it used a single output and the block trim never fired.
    *A test suite proves what it asserts and nothing more*, for the sixth
    time, inside the commit that said it for the fifth.
    """
    e, j, b, d = build_engine([], [])
    for i in range(6):
        j.append("exec_start", cmd="cat big%d" % i)
        j.append("exec_end", exit_code=0, stderr="",
                 stdout=capped("\n".join("out %d line %04d %s" % (i, k, "z" * 60)
                                          for k in range(900)),
                               EXEC_STDOUT_CHARS))
    # The drop is COMPUTED, not eyeballed: render once with the bound lifted
    # and once with it in force, and the difference is what the reader is owed.
    # The first draft of this check asked `any(ch.isdigit())` over a transcript
    # full of `big0` and `line 0001`, which is green whatever the notice says
    # -- the tautology this suite has a scar about, written while fixing the
    # fault it is about.
    real = e.HISTORY_TOTAL_CHARS
    try:
        e.HISTORY_TOTAL_CHARS = 10 ** 9
        whole = e.recent_block(cycles=6)
    finally:
        e.HISTORY_TOTAL_CHARS = real
    h = e.recent_block(cycles=6)
    check("trim: this transcript really is long enough to be trimmed",
          len(whole) > real and len(h) <= real + 900, (len(whole), len(h), real))
    check("trim: the reader is told a cut happened", "dropped" in h.lower(),
          h[:200])
    dropped = len(whole) - len(h)
    # READ THE NOTICE, not the transcript. The first version of this built
    # 1,800 numeric strings around the expected drop and asked whether ANY of
    # them appeared anywhere in `h` -- and `h` is full of numbers, including
    # the per-output markers this check is about. A verifier swept the fixture
    # size and found a value where a notice carrying NO NUMBER AT ALL passed,
    # satisfied by a marker's own figure. One constant away from a tautology,
    # in the check written to replace a tautology.
    m = re.search(r"Older lines dropped: (\d+) characters", h)
    check("trim: the notice carries a number at all -- a notice with none is "
          "the marker fault one level up, and the per-output markers "
          "understate by exactly this much while it is missing",
          m is not None, h[:300])
    said = int(m.group(1)) if m else -1
    check("trim: and it is the real drop, to within the header and the "
          "notice itself", abs(said - dropped) < 900, (said, dropped))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_creatures_ladder_really_is_given_the_emptiness_predicate():
    """The verifier's finding: reverting `run.py` alone left the whole gate
    green. `test_a_reply_with_no_text_at_all_is_not_an_answer` builds its own
    ladder and asserts the predicate works -- which says nothing about whether
    the engine's ladder was given it.

    **That is the 2026-09-16 shape exactly**: a feature inert in production for
    fifteen hours with a green gate, because every test used a scripted
    backend and nothing drove the real construction.

    So the construction moved into `run.build_ladders`, and this drives THAT,
    through the real `backends.from_spec`, with a scripted rung kind
    registered for the duration. No literal is matched and no source is read:
    the ladders are built the way the engine builds them and then watched.
    """
    import run as runmod

    calls = []

    def scripted(replies=None, **kw):
        seq = list(replies or [])

        def ask(prompt):
            calls.append(kw.get("tag"))
            return seq.pop(0) if seq else ("", {"done_reason": "stop"})
        return ask

    backends.KINDS["scripted"] = scripted
    try:
        spec = [{"name": "silent", "kind": "scripted", "tag": "silent",
                 "replies": [("", {"done_reason": "length"})]},
                {"name": "speaks", "kind": "scripted", "tag": "speaks",
                 "replies": [("I read the plan and there is nothing to do.",
                              {"done_reason": "stop"})]}]
        cspec = [{"name": "silent", "kind": "scripted", "tag": "c-silent",
                  "replies": [("<<<COUSIN\nverdict: ACCEPTED\n"
                               "to_creature: fine\nCOUSIN",
                               {"done_reason": "stop"})]}]
        ask_creature, ask_cousin, ask_invoke = runmod.build_ladders(spec, cspec)

        calls[:] = []
        text, meta = ask_creature("go")
        check("wiring: the ENGINE's creature ladder steps past a rung that "
              "returned nothing -- not a ladder a test built",
              calls == ["silent", "speaks"] and meta.get("rung") == "speaks",
              (calls, meta.get("rung")))
        check("wiring: and it keeps a reply that has text and no command, "
              "which must never be rejected", "nothing to do" in text, text)

        # THE OTHER TWO LADDERS, BY WHAT THEY DO. The first version of this
        # asserted `ask_cousin is not ask_invoke`, which is True under every
        # possible implementation -- `from_spec` returns a fresh closure every
        # call -- and a source grep for two literals in `run.py`. A verifier
        # then CROSSED the two predicates inside `build_ladders` and the whole
        # gate stayed green. That crossing is byte-for-byte the 2026-09-16
        # outage: the invocation asked through the verdict's predicate, every
        # correct answer judged unusable, every rung walled, 112 probes lost
        # in fifteen hours.
        calls[:] = []
        v, _m = ask_cousin("judge")
        check("wiring: the cousin's VERDICT ladder accepts a verdict block",
              "ACCEPTED" in v, v)

        # An INVOCATION reply: a bash block and no verdict. For the verdict
        # ladder that is a failure; for the invocation ladder it is the
        # answer. Each must be asked through its own contract.
        inv = [{"name": "proposes", "kind": "scripted", "tag": "inv",
                "replies": [("I would run it like this:\n```bash\n"
                             "plan list\n```", {"done_reason": "stop"})]}]
        _c, ladder_v, ladder_i = runmod.build_ladders(spec, inv)
        got = None
        try:
            ladder_v("judge")
        except backends.LadderExhausted as e:
            got = e
        check("wiring: through the VERDICT ladder an invocation reply is "
              "unusable -- that is the contract, and it is what makes "
              "crossing the two fatal",
              got is not None, "the verdict ladder accepted a bash block")
        text2, _m2 = ladder_i("what would you run")
        check("wiring: through the INVOCATION ladder the same reply is the "
              "ANSWER, and the two cannot be swapped without this going red",
              "plan list" in text2, text2)
    finally:
        backends.KINDS.pop("scripted", None)


def test_the_census_has_no_opinion_about_testimony_that_does_not_exist():
    """`census.check` scored an UNKNOWN verdict for *never naming the tool it
    ran*. An UNKNOWN is the cousin saying nothing readable -- the ladder went
    dry, or the reply was cut before the block -- so there is no testimony to
    be unfaithful.

    Measured over run 2 on 2026-09-21: **207 verdicts, 0 HIGH, 21 LOW -- and
    19 of the 21 were UNKNOWNs.** The census was inflating its own finding
    count tenfold with the one thing it cannot have an opinion about. The
    `probe is None` branch three lines above already drew this line.

    That matters more than its size, because this is the ONLY thing that
    checks the manager (§6.1), and an instrument whose findings are 90% noise
    is one a reader learns to skim.
    """
    import census

    probe = {"tool": "plan", "exit_code": 2, "stdout": "usage: plan", "stderr": ""}
    quiet = census.check(probe, {"verdict": "UNKNOWN", "tried": "",
                                 "outcome": "", "to_creature": ""})
    check("census: an UNKNOWN names no tool because it says NOTHING, and that "
          "is not a fidelity finding", quiet == [], quiet)

    spoke = census.check(probe, {"verdict": "RETURNED", "tried": "I ran it",
                                 "outcome": "it asked for an argument",
                                 "to_creature": "say what you need"})
    check("census: a verdict that DOES speak and never names its tool is "
          "still flagged", any(s == "LOW" for s, _t in spoke), spoke)

    named = census.check(probe, {"verdict": "RETURNED", "tried": "plan list",
                                 "outcome": "usage", "to_creature": "needs args"})
    check("census: and naming it clears the finding", named == [], named)

    # The HIGH cases are what this file exists for, and none of them moved.
    fab = census.check(probe, {"verdict": "RETURNED", "tried": "plan",
                               "outcome": "it exited 0 and worked",
                               "to_creature": "fine"})
    check("census: a claimed exit code the probe never produced is still HIGH",
          any(s == "HIGH" for s, _t in fab), fab)
    mute = census.check(probe, {"verdict": "RETURNED", "tried": "plan",
                                "outcome": "x", "to_creature": "  "})
    check("census: a refusal with no reason is still HIGH",
          any(s == "HIGH" for s, _t in mute), mute)
    none_probe = census.check(None, {"verdict": "ACCEPTED", "tried": "",
                                     "outcome": "", "to_creature": "ok"})
    check("census: a verdict with no recorded probe at all is still HIGH",
          any(s == "HIGH" for s, _t in none_probe), none_probe)
    unknown_none = census.check(None, {"verdict": "UNKNOWN", "tried": "",
                                       "outcome": "", "to_creature": ""})
    check("census: but an UNKNOWN with no probe is nothing happening twice",
          unknown_none == [], unknown_none)


def test_the_census_catches_the_plainest_way_to_claim_an_exit_code():
    """**The only guard on the manager could not match "exited 0".**

    `census.check`'s pattern was `exit(?:ed with)?` -- so *exit 0*, *exit code
    0* and *exited with 0* were caught, and **"exited 0" was not.** That is
    the plainest phrasing of the one thing this file exists to catch, and
    §6.1 says this file is the only thing that checks the manager at all.

    **It had been blind for eight days, and it was hiding two real
    fabrications.** Both are reproduced below from the live journal, verbatim,
    because a scar with a fixture cannot recur quietly:

    - the probe ran `plan` BARE, exit 1, printing its usage menu. The cousin
      said *"plan list exited 0 with no tasks listed... I ran `plan list` and
      received an empty list"*. It never ran `plan list`.
    - the probe ran `subagent-orchestrator` BARE, exit 2, an argparse usage
      error on stderr and nothing on stdout. The cousin said
      *"subagent-orchestrator run \"demo\" printed the string \"demo\"...
      and exited 0"*. That invocation never happened and that output never
      existed.

    Both were ACCEPTED. §2.5: *never let the manager claim an experience it
    did not have -- a fabricated complaint is the exact fault this design
    exists to prevent, committed by the agent meant to catch it.*

    And the shape is the 2026-09-10 scar returning: *a guard hunting one
    literal, in the instrument built to police literals.* Widened only as far
    as the evidence supports -- over run 2's 189 checkable verdicts the old
    pattern finds 0 and the new one finds exactly these 2, both confirmed by
    reading the probe, because a guard that INVENTS a complaint about the
    manager is the same fault pointed the other way.
    """
    import census

    plan_bare = {"tool": "plan", "exit_code": 1, "stderr": "",
                 "stdout": "Usage: plan <command> [args]\nCommands:\n"
                           "  goal <text>  Set the overall goal"}
    fabricated = {"verdict": "ACCEPTED",
                  "tried": "plan list exited 0 with no tasks listed "
                           "(empty output)",
                  "outcome": "I ran `plan list` and received an empty list, "
                             "which is the correct behavior when the task "
                             "store is empty.",
                  "to_creature": "next I want to be able to add a task"}
    got = census.check(plan_bare, fabricated)
    check("census: 'exited 0' against a probe that exited 1 is a HIGH",
          any(s == "HIGH" and "exit" in t for s, t in got), got)

    orch = {"tool": "subagent-orchestrator", "exit_code": 2, "stdout": "",
            "stderr": "usage: subagent-orchestrator [-h] {run} ...\n"
                      "subagent-orchestrator: error: the following arguments "
                      "are required: command"}
    invented = {"verdict": "ACCEPTED",
                "tried": 'subagent-orchestrator run "demo" printed the string '
                         '"demo" (echoed the task description) and exited 0',
                "outcome": "I invoked it and it echoed back the task "
                           "description, as the stub promises.",
                "to_creature": "the tool runs and returns the expected output"}
    got2 = census.check(orch, invented)
    check("census: and so is the second one, which invented both the "
          "invocation and its output",
          any(s == "HIGH" and "exit" in t for s, t in got2), got2)

    # THE OTHER PHRASINGS STILL WORK, and an honest verdict is still clean --
    # widening a guard that can accuse the manager needs both halves.
    for phrase in ("it exited 0", "exit 0", "exit code 0", "exited with 0",
                   "exited with code 0"):
        v = {"verdict": "RETURNED", "tried": "plan", "outcome": phrase,
             "to_creature": "not what I needed"}
        check("census: '%s' is read as a claim about the exit code" % phrase,
              any(s == "HIGH" for s, _t in census.check(plan_bare, v)), phrase)
    honest = {"verdict": "RETURNED", "tried": "plan",
              "outcome": "plan exited 1 and printed its usage menu",
              "to_creature": "it needs a subcommand"}
    check("census: a verdict that reports the exit code correctly is clean",
          census.check(plan_bare, honest) == [],
          census.check(plan_bare, honest))
    nonum = {"verdict": "RETURNED", "tried": "plan",
             "outcome": "it printed a usage menu and did not do what I asked",
             "to_creature": "needs a subcommand"}
    check("census: and one that names no number at all is not accused of "
          "naming the wrong one", census.check(plan_bare, nonum) == [],
          census.check(plan_bare, nonum))


def test_a_rung_that_answers_and_says_nothing_is_not_a_quota_refusal():
    """The change that made this necessary is in the same commit as this.

    The creature's ladder now rejects a reply with no text. Before that, such
    a reply was banked and surfaced as `commands LOST / budget_spent`, which
    `commands_lost` watches. After it, the reply never reaches `run_cycle` at
    all -- it becomes a `rung_declined` with `expected=True`, which is what a
    429 looks like, and the page shows both as one number: *rungs declined
    (expected)*. **A rung returning nothing on every call would have read as
    ordinary weather.**

    A verifier found that before it was ever deployed. So the record carries
    the distinction (`unusable`) and this detector reads it -- a field nothing
    reads is the dead-channel scar, and this project has paid for that one
    too.
    """
    from monitor import detectors as det

    def ctx(rows):
        return det.Context(rows, now=2000.0)

    def decline(rung, unusable, ts):
        return {"kind": "rung_declined", "ts": ts, "rung": rung,
                "expected": True, "unusable": unusable,
                "reason": ("answered but unusable: budget spent"
                           if unusable else "quota or rate limit (HTTP 429)")}

    quiet = [decline("a", False, 1000.0 + i) for i in range(40)]
    f = [x for x in det.replies_unusable(ctx(quiet))]
    check("unusable: a ladder that only ever met quota is OK",
          all(x.state == det.OK for x in f), [(x.name, x.state) for x in f])

    few = quiet + [decline("a", True, 1500.0 + i) for i in range(2)]
    f2 = [x for x in det.replies_unusable(ctx(few)) if "[" in x.name]
    check("unusable: two of them is not enough to say anything, and it says "
          "CANNOT TELL rather than OK",
          f2 and all(x.state == det.CANNOT_TELL for x in f2),
          [(x.name, x.state) for x in f2])

    many = ([decline("a", True, 1500.0 + i) for i in range(12)]
            + [decline("a", False, 1400.0 + i) for i in range(4)])
    f3 = [x for x in det.replies_unusable(ctx(many)) if "[" in x.name]
    check("unusable: a rung whose declines are mostly ANSWERS we could not "
          "use is an ALARM, not weather",
          f3 and any(x.state == det.ALARM for x in f3),
          [(x.name, x.state, x.msg) for x in f3])
    check("unusable: and the alarm says which rung and why",
          any("a" in x.msg and "budget" in x.msg for x in f3),
          [x.msg for x in f3])

    mixed = ([decline("a", True, 1500.0 + i) for i in range(10)]
             + [decline("a", False, 1400.0 + i) for i in range(90)])
    f4 = [x for x in det.replies_unusable(ctx(mixed)) if "[" in x.name]
    check("unusable: a handful against a wall of real quota is informational, "
          "because on a free tier quota IS the weather",
          f4 and all(x.state == det.INFO for x in f4),
          [(x.name, x.state) for x in f4])

    # AND THE PAGE CARRIES A RUNBOOK LINE, because a finding without one is a
    # puzzle handed to whoever is awake at three in the morning.
    from monitor import status as monstatus
    check("unusable: the finding has a runbook line",
          "replies_unusable" in monstatus.RUNBOOK,
          sorted(monstatus.RUNBOOK)[:5])


def test_the_has_not_survived_column_cannot_be_read_as_a_cull_list():
    """The page printed the COUNT of tools that had not survived and nothing
    else about them, so the column read as dead weight. Measured on the live
    library 2026-09-21: **all 29 of them had been run at least twice**, the
    list included `view-subtask-logs` at 64 runs and `subagent-orchestrator`
    at 44, and `archive` -- named by 29 other tools -- was on it because its
    first-to-last span was 6.76 days against a 7-day bar.

    So the bar is about WHEN ITS USER LAST CAME BACK, not about how much a
    tool is used, and the page never said so. Tue, the same evening: *if we
    delete unused tools completely, with no memory they existed and were
    never used, they would just be made again.* The first step away from that
    is not deleting something on the strength of a number whose meaning was
    never printed.
    """
    from monitor import status as monstatus

    DAY = 86400.0
    T0 = 1_700_000_000.0
    s = {"window_days": 7, "run_days": 9.0, "surviving": 0,
         "not_surviving": 2, "cannot_tell": 0, "reused": 2,
         "widest_span_days": 2.2, "why_cannot_tell": "",
         "edges": {}, "tools": [
             {"tool": "worked-hard", "started": True, "named_by": 3,
              "first_use": T0, "last_use": T0 + 2 * DAY, "span_days": 2.0,
              "surviving": False, "runs": 64},
             {"tool": "touched-once", "started": True, "named_by": 0,
              "first_use": T0, "last_use": T0, "span_days": 0.0,
              "surviving": False, "runs": 2}]}
    page = "\n".join(monstatus.render_surviving(s))

    check("cull: the tools that did not survive are NAMED, not just counted",
          "worked-hard" in page and "touched-once" in page, page[:300])
    check("cull: and each carries its RUN COUNT, so a tool run 64 times "
          "cannot be mistaken for one nobody used",
          "64 run" in page, page[:400])
    check("cull: the page says what the bar actually tests",
          "last time its user came back" in page.lower(), page[:400])
    check("cull: and says in as many words that it is not a cull list",
          "cull list" in page.lower(), page[:400])


def test_the_library_remembers_what_left_it():
    """**Tue, 2026-09-21:** *"if we delete unused tools completely with no
    memory they existed and was never used, they would just be made again...
    when a new program is proposed, look at the graveyard first, then decide
    the chance you would use it, then if it makes sense for your goal."*

    `CREATURE-PROMPT.md` line 26 already carries the rule -- *do not rebuild
    what you own* -- and tells the creature to run `ls tools/own/` when it is
    unsure. **`ls` shows what exists now.** A tool the creature built, its
    user never came back to, and it then removed, leaves no trace in anything
    either inhabitant is shown: measured 2026-09-21, the 11,617-character
    library block carried **zero** removed names and no `removed`/`retired`
    language at all.

    So this is the 2026-09-12 shape exactly, and that scar says what to do
    about it: *before adding a rule, check whether the evidence that rule
    needs is actually on the page.* The rule was already right then too; the
    library simply was not being shown, and showing it moved the judgement
    5/5. **The fix is evidence, not a new instruction.**

    Facts only, and that line matters: name, when it left, how many times its
    USER ran it before it went, and where its words survive now. What that
    means -- consolidated, abandoned, worth rebuilding -- is the creature's to
    decide, because *a scan gathers a fact and then decides what to say about
    it, and only the first half is framework*.
    """
    d = tmpdir()
    own = os.path.join(d, "tools", "own")
    os.makedirs(own)
    j = Journal(os.path.join(d, "journal.jsonl"))

    _write_tool(own, "plan", does="keeps the plan", call="plan list",
                body="echo 'set-goal and clear-goal live here now'")
    _write_tool(own, "fetch", does="gets a url", call="fetch <url>")

    j.append("tools_changed", added=["plan", "fetch", "plan-set-goal",
                                     "taskprio", "gone-and-back"], removed=[])
    # its user ran it three times before it went
    for _i in range(3):
        j.append("cousin_probe", tool="plan-set-goal", exit_code=0,
                 bare=False, cmd="plan-set-goal x")
    j.append("cousin_probe", tool="taskprio", exit_code=2, bare=True,
             cmd="taskprio")
    j.append("tools_changed", added=[], removed=["plan-set-goal", "taskprio"])
    j.append("tools_changed", added=[], removed=["gone-and-back"])
    j.append("tools_changed", added=["gone-and-back"], removed=[])

    g = library.graveyard(j, own)
    names = [row["tool"] for row in g]
    check("graveyard: it holds what left the library",
          "plan-set-goal" in names and "taskprio" in names, names)
    check("graveyard: and NOT something that came back -- a tool in the "
          "library is not in the graveyard", "gone-and-back" not in names,
          names)
    check("graveyard: nor anything still live", "plan" not in names, names)

    row = [r for r in g if r["tool"] == "plan-set-goal"][0]
    check("graveyard: it carries how many times ITS USER ran it, which is the "
          "whole question -- was this ever wanted", row["runs"] == 3, row)
    check("graveyard: and when it left", row.get("removed_ts"), row)
    check("graveyard: and where its words survive now, as a FACT rather than "
          "a conclusion about whether it was consolidated",
          "plan" in (row.get("words_survive_in") or []), row)
    bare = [r for r in g if r["tool"] == "taskprio"][0]
    check("graveyard: a tool whose user only ever called it bare is counted "
          "honestly -- one probe, and the listing does not call that a use",
          bare["runs"] == 1 and bare.get("asked") == 1, bare)

    # AND IT REACHES THE PAGE BOTH INHABITANTS SEE.
    block = library.render(own, j)
    check("graveyard: the served library carries it", "plan-set-goal" in block,
          block[-600:])
    check("graveyard: with the run count beside the name",
          "3" in block.split("plan-set-goal")[1][:120], block[-600:])
    check("graveyard: and says plainly what the section is for",
          "built and removed" in block.lower() or "no longer" in block.lower(),
          block[-600:])

    # BOUNDED. An unbounded graveyard is the wake-cost failure class arriving
    # by a new door, and this block is already 42% of a wake.
    j2 = Journal(os.path.join(d, "j2.jsonl"))
    j2.append("tools_changed", added=["t%d" % i for i in range(40)], removed=[])
    j2.append("tools_changed", added=[], removed=["t%d" % i for i in range(40)])
    g2 = library.graveyard(j2, own)
    check("graveyard: it is bounded", len(g2) <= library.GRAVEYARD_LIMIT,
          len(g2))
    b2 = library.render(own, j2)
    check("graveyard: and a bound DEGRADES rather than hides -- it says how "
          "many it is not showing", "more" in b2.lower(), b2[-400:])

    # NO REMOVALS, NO SECTION: an empty heading every wake is noise the
    # creature learns to skip, which is the surface-on-a-change rule.
    j3 = Journal(os.path.join(d, "j3.jsonl"))
    j3.append("tools_changed", added=["plan"], removed=[])
    b3 = library.render(own, j3)
    check("graveyard: a library that has lost nothing says nothing about it",
          "removed" not in b3.lower(), b3[-300:])
    # A BACKUP IS NOT A LIBRARY MEMBER, alive or dead. `.testbak` was written
    # by the creature on 2026-09-14 and counted as a tool for its whole life,
    # then offered back on 2026-09-21 as a capability it had removed.
    j4 = Journal(os.path.join(d, "j4.jsonl"))
    j4.append("tools_changed", added=["plan", "plan.testbak", "plan.bak"],
              removed=[])
    j4.append("tools_changed", added=[],
              removed=["plan.testbak", "plan.bak"])
    g4 = [r["tool"] for r in library.graveyard(j4, own)]
    check("graveyard: a backup never enters it, whatever the creature named "
          "it -- `.bak` was caught and `.testbak` was not", g4 == [], g4)
    b4 = library.render(own, j4)
    check("graveyard: and the COUNT agrees with the list -- a bound that says "
          "'1 more, older' about a backup it will never show teaches a reader "
          "to distrust both", "more, older" not in b4, b4[-300:])
    open(os.path.join(own, "plan.testbak"), "w").write("#!/bin/sh\n")
    check("graveyard: and a backup on disk is not a tool either",
          "plan.testbak" not in triggers.list_tools(own),
          triggers.list_tools(own))
    os.unlink(os.path.join(own, "plan.testbak"))

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
        cannot_run("the observer's shell",
                   "PyQt6 (the engine does not need it; the observer is "
                   "only a window)")
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
    # Against the constant, not a literal: 8000 was a literal that happened
    # to be above the 6,000 total of the day; the total is 12,000 now.
    check("history: a huge output is capped again for the CONTEXT",
          len(big) < Engine.HISTORY_TOTAL_CHARS + 1200,
          "history was %d chars against a total of %d"
          % (len(big), Engine.HISTORY_TOTAL_CHARS))
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
        cannot_run("the live model", "COUSIN_NO_LOCAL_MODEL unset (it is set; VRAM left alone)")
        return
    model = os.environ.get("COUSIN_MODEL", "gemma4:12b")
    ask = backends.ollama(model, num_predict=700)
    ok, why = backends.preflight(ask, "ollama/%s" % model)
    if not ok:
        cannot_run("the live model", why)
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
        # `pwd -P` on both sides, inside the one shell that has to agree
        # with itself. cwd is the mind, so `..` is the body root.
        r = b.run('echo "[$SPINE_API_KEY_CANARY]"; echo "home=$HOME"; '
                  'echo "root=$(cd .. && pwd -P)"; '
                  'echo "home_is=$(cd "$HOME" 2>/dev/null && pwd -P)"')
        check("env: a secret in the engine's environment does not reach the "
              "creature's shell",
              "do-not-leak-me" not in r.stdout, repr(r.stdout)[:120])
        # ASKED OF THE SHELL, never compared as strings. Two attempts at a
        # normaliser failed for the same reason: Git bash maps the Windows
        # temp directory to `/tmp`, so the same directory has two spellings
        # and neither side is wrong. `pwd -P` on both sides inside one shell
        # has nothing to translate and nothing to assume.
        got = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
        check("env: HOME points into the body, so `~` is the creature's own tree",
              bool(got.get("home_is")) and got.get("home_is") == got.get("root"),
              {k: got.get(k) for k in ("home", "home_is", "root")})
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
    # PLAN item 9: the cousin runs the tool with arguments it chooses. Without
    # this flag the deployment keeps probing BARE, which is the thing that
    # produced 63 probes of one tool and the same want six times -- and the
    # repo would say otherwise while the engine carried on as before, which
    # is how `--body docker` shipped inert for twenty minutes.
    check("unit: the cousin is given its own shell, or it is still a user "
          "who can only call things bare",
          "--cousin-shell" in execs[0], execs[0][:220])


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
    # Sized FROM the cap, so a raise cannot leave this proving nothing: it was
    # 120 fixed lines (~4,200 chars), which stopped exceeding the cap the day
    # the cap moved to 8,000 (2026-09-17) -- a fixture that quietly fell under
    # the thing it was meant to overflow.
    lines = Engine.HISTORY_OUTPUT_CHARS // 30 + 40
    big = "".join("line %04d padding padding padding\n" % i for i in range(lines))
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


def test_the_window_shows_the_creature_its_largest_tool_whole():
    """PLAN item 13, reopened by the trigger it named for itself.

    2026-09-17, 08:00-10:00: `plan` at 6,119 bytes, the caps at 2,400, and
    the creature ran `cat tools/own/plan` TWENTY times -- shown ~2,400
    characters each time, 2,970-3,743 withheld -- while trying to add the
    deadline feature its cousin had asked for four times. Twelve of its
    twenty-four thinks in that window talk about the cut. `window_reread`
    fired four times in twenty hours. Item 13's own text said: read the raw
    thinks, is it re-reading because it cannot see the whole file, or for its
    own reasons? It cannot see the file.

    The invariant this asserts is not a number. It is that the caps are sized
    to the library the creature actually has: every tool it has built must
    fit through the journal AND the served context, or the framework is
    hiding a tool from its author -- the 2026-09-13 wall at a new size.
    Measured on the laptop: 29 of 60 tools exceeded the old cap; the largest
    is 7,223 bytes.
    """
    largest_known = 7223                      # subagent-orchestrator, 2026-09-17
    check("window: the journal keeps a tool the size of the largest one built",
          EXEC_STDOUT_CHARS >= largest_known,
          "journal cap %d < largest tool %d" % (EXEC_STDOUT_CHARS, largest_known))
    check("window: and the served context shows it whole",
          Engine.HISTORY_OUTPUT_CHARS >= largest_known,
          "context cap %d < largest tool %d" % (Engine.HISTORY_OUTPUT_CHARS, largest_known))
    check("window: the block bound leaves room for one whole read plus its "
          "command and result lines, or the third cap in the series swallows "
          "the other two", Engine.HISTORY_TOTAL_CHARS >= Engine.HISTORY_OUTPUT_CHARS + 1000,
          (Engine.HISTORY_TOTAL_CHARS, Engine.HISTORY_OUTPUT_CHARS))
    # BEHAVIOUR, not arithmetic: a tool of the largest real size, read once,
    # arrives in the creature's history without a single character withheld.
    src = "".join("line %04d of a tool as large as the largest one built\n" % i
                  for i in range(largest_known // 52 + 1))
    check("window: the fixture is at least as large as the largest real tool",
          len(src) >= largest_known, len(src))
    e, j, b, d = build_engine(["thinking"], [])
    j.append("exec_start", cmd="cat tools/own/big")
    j.append("exec_end", exit_code=0, stdout=capped(src, EXEC_STDOUT_CHARS), stderr="")
    hist = e.recent_block()
    check("window: the creature is shown ALL of it -- nothing withheld by the log",
          "withheld" not in hist and "line %04d" % (largest_known // 52) in hist,
          hist[-300:])
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_same_testimony_every_visit_is_reported_as_a_form():
    """The brief's own test for a form -- "if your sentence would still make
    sense with another tool's name dropped into it, you have written a form
    and not a report" -- had no instrument. 2026-09-17: four consecutive
    ACCEPTs of `plan` carried the identical sentence, the want they carried
    repeated four times, and the feature it asked for, already built, had
    never been run by the cousin that asked. Visibility only: the judgement
    is the brief's (PLAN item 16), and §2.2 forbids touching a verdict.
    """
    from monitor import detectors as det
    now = 1789600000.0

    def ctx_of(texts, tools=None):
        rows = []
        for i, t in enumerate(texts):
            rows.append({"ts": now - 3600 + i, "kind": "cousin_verdict",
                         "verdict": "ACCEPTED", "to_creature": t,
                         "tool": (tools or ["plan"] * len(texts))[i]})
        return det.Context(rows, now=now)

    same = "I ran `plan` and got the usage menu. I can now see how to manage my goals."
    f = det.testimony_repeated(ctx_of([same, same, "I set a baseline and read it back.", same]))
    check("testimony: the same sentence three of the last five times is an ALARM",
          f.state == det.ALARM, (f.state, f.msg[:90]))
    check("testimony: and it names the brief's own test",
          "form, not a report" in f.msg, f.msg[:160])
    check("testimony: and points at the probes, where the cause is",
          "probes" in f.msg, f.msg[-160:])
    f2 = det.testimony_repeated(ctx_of(["I linked task 3 to entry 36 and it showed the link.",
                                        "I exported the plan and got entry 37.",
                                        "I cleared the baseline and recall showed nothing."]))
    check("testimony: distinct reports are OK", f2.state == det.OK, (f2.state, f2.msg[:80]))
    f3 = det.testimony_repeated(ctx_of([same, same]))
    check("testimony: two verdicts cannot tell a form from a report -- CANNOT "
          "TELL, never OK", f3.state == det.CANNOT_TELL, (f3.state, f3.msg[:80]))
    # Whitespace and case are not different testimony.
    f4 = det.testimony_repeated(ctx_of([same, same.upper(), "  " + same + "  "]))
    check("testimony: case and spacing do not make a form into three reports",
          f4.state == det.ALARM, (f4.state, f4.msg[:80]))
    check("testimony: it is registered, or the page never says it",
          det.testimony_repeated in det.ALL)


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
    # "never exited 0 for them" since 2026-09-16 -- a fact. "NEVER WORKED"
    # was a judgement the framework stopped being able to make once the cousin
    # chose the arguments; see `library.status`.
    check("bare: and the one that never exited 0 says so, as a fact",
          "never exited 0 for them" in out, out)

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
    check("floor: a tool that never exited 0 is not shown as merely 'last failed'",
          "never exited 0 for them" in out, out)
    # Facts, not adjectives, since 2026-09-16: "exited non-zero" is what the
    # framework knows; whether that was a failure is the cousin's verdict,
    # which the same line now reports beside it.
    check("floor: and the mixed one reports BOTH halves of its record",
          "1 exited 0 and 1 exited non-zero" in out, out)
    check("floor: a clean record still reads as clean",
          "never exited 0" not in out.split("- storey")[1], out)

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
          "never exited 0 for them" in e.serve_context(), e.serve_context()[-400:])
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


def test_every_hand_the_creature_has_is_one_it_has_been_told_about():
    """PLAN item 14.5, which is the one criterion of item 14 that is NOT met.

    `hands/say` exists, is on the creature's PATH, and is in its container --
    and `CREATURE-PROMPT.md` does not mention it. The prompt names `remember`,
    `recall`, `tool-new` and `tool-edit`, and tells the creature to list
    `tools/own/`, which is its OWN work and not where its hands live. So the
    channel is one-way in practice: a human can speak to it, and the reply
    path is a hand nobody introduced.

    **That is deliberate and it is recorded**: `CREATURE-PROMPT.md` is frozen,
    a prompt change is a behaviour change needing a before/after, and item 14
    exists last precisely because a new surface arriving mid-measurement makes
    every number on either side incomparable. The trigger is to add it in the
    same change that unfreezes the brief.

    **What was missing is an instrument.** Item 13 earned its detector on the
    argument that *a decision recorded and then unwatched is indistinguishable
    from one forgotten*; 14.5 is the same shape and was prose only, which a
    verifier pointed out. So the gap is now an exception with a name: the
    lists must agree EXCEPT for what `TOLD_LATER` holds, so adding a hand
    silently goes red, and the day `say` is introduced the entry must be
    deleted or this goes red then instead. The gap cannot be forgotten in
    either direction, which is all a deferral has to promise.
    """
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hands_dir = os.path.join(repo, "hands")
    prompt = io.open(os.path.join(repo, "CREATURE-PROMPT.md"),
                     encoding="utf-8").read()
    hands = sorted(n for n in os.listdir(hands_dir)
                   if os.path.isfile(os.path.join(hands_dir, n))
                   and not n.startswith(".") and not n.endswith((".bak", ".md")))
    check("hands: the creature has hands at all, or this proves nothing",
          len(hands) >= 4, hands)

    # The single recorded exception, with the reason it is one.
    TOLD_LATER = {"say": "PLAN 14.5 -- lands with the brief's unfreeze, "
                         "because a new surface mid-measurement makes the "
                         "numbers on either side incomparable"}
    # A hand is "named" if it appears in backticks, WITH OR WITHOUT its
    # arguments: the prompt writes `tool-edit <name>`, and the first draft of
    # this check hunted the exact literal `tool-edit` and reported it
    # unmentioned -- a guard keyed on one literal string, in the test written
    # to stop a hand going unmentioned. Third time that shape has appeared in
    # this file.
    unmentioned = [h for h in hands
                   if not re.search(r"`%s(?=[ `])" % re.escape(h), prompt)]
    check("hands: every hand is either named in the creature's prompt or "
          "recorded as deliberately withheld -- never merely absent",
          set(unmentioned) <= set(TOLD_LATER), sorted(unmentioned))
    check("hands: and every withheld hand still EXISTS, so the exception "
          "cannot outlive the thing it excuses",
          set(TOLD_LATER) <= set(hands), sorted(set(TOLD_LATER) - set(hands)))
    for h in sorted(set(TOLD_LATER) & set(unmentioned)):
        check("hands: `%s` is withheld on purpose: %s" % (h, TOLD_LATER[h]),
              True)


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


def test_a_starved_cousin_is_told_apart_from_a_dry_tier():
    """The asymmetry nobody was watching, and it cost fifteen hours.

    On 2026-09-16 the cousin's command-choosing call was asked through the
    ladder that rejects any reply without a VERDICT block, so every correct
    answer walled a rung: **112 probes, 112 lost, 0 verdicts -- and 112
    creature thinks in the same window, on the same rungs.** Both numbers
    were on the status page, in adjacent rows, and nothing put them side by
    side. `ladder_dry` said INFO the whole time, correctly, because the tier
    WAS thin -- and that is exactly why a second signal was needed: thin for
    everyone is weather, thin for one agent is a bug in how that agent is
    asked.

    Three states, and the middle one is the load-bearing one: with too few
    probes this says CANNOT TELL, never OK, because a cousin that is never
    summoned looks identical to one that is summoned and always fails, and
    the second is the fault this exists for. *Cannot tell is not permission.*
    """
    from monitor import detectors as det
    now = 1789576576.0

    def ctx_of(n_probes, n_lost, n_thinks, hours_ago=1.0):
        rows = []
        ts = now - hours_ago * 3600
        for i in range(n_probes):
            rows.append({"ts": ts + i, "kind": "cousin_probe", "tool": "plan",
                         "exit_code": (None if i < n_lost else 0),
                         "chosen_by": ("ladder_dry" if i < n_lost else "cousin"),
                         "error": "LadderExhausted: unusable: no-block"})
        for i in range(n_thinks):
            rows.append({"ts": ts + i, "kind": "think", "rung": "gemini"})
        c = det.Context(sorted(rows, key=lambda r: r["ts"]), now=now)
        return c

    f = det.cousin_starved(ctx_of(10, 10, 12))
    check("starved: every probe lost while the creature is served is an ALARM",
          f.state == det.ALARM, (f.state, f.msg[:90]))
    check("starved: and it says plainly this is NOT the free tier",
          "not about the free tier" in f.msg, f.msg[-80:])
    check("starved: a human is told", f.human is True, f.human)
    check("starved: the evidence carries the error, so the runbook has "
          "something to read", "no-block" in (f.evidence.get("last_error") or ""),
          f.evidence)

    f2 = det.cousin_starved(ctx_of(10, 10, 0))
    check("starved: both starved together is weather, not a fault -- that is "
          "`ladder_dry`'s job and this one stands down",
          f2.state == det.INFO, (f2.state, f2.msg[:90]))

    f3 = det.cousin_starved(ctx_of(10, 4, 12))
    check("starved: probes that reach the tool clear it",
          f3.state == det.OK, (f3.state, f3.msg[:90]))

    f4 = det.cousin_starved(ctx_of(1, 1, 12))
    check("starved: too few probes is CANNOT TELL, never OK -- a cousin never "
          "summoned reads like one summoned and always failing",
          f4.state == det.CANNOT_TELL, (f4.state, f4.msg[:90]))

    # OLD ENOUGH TO BE OUT OF THE WINDOW is not a finding.
    f5 = det.cousin_starved(ctx_of(10, 10, 12, hours_ago=48))
    check("starved: and it looks at a window rather than at all of history",
          f5.state == det.CANNOT_TELL, (f5.state, f5.msg[:90]))


def test_the_shared_tier_is_watched_and_the_doctrine_cannot_drift_from_it():
    """PLAN item 12, and the reason it needed an instrument rather than a line.

    CLAUDE.md §4 has said **SPINE IS PAUSED as of 2026-09-13 13:50** since the
    day Tue stopped it. The spine was started again on 2026-09-15 00:12:11 --
    four minutes after its own flatline tripwire reported `THINK:!!NONE in
    6h` -- and ran from then on. Through the whole first day of this monitor.
    Through the evening read of 2026-09-15 18:52 whose figures went into §7.
    Through the opening of item 9.5's measurement window. **Twenty-seven
    hours, and the document said the opposite the entire time.**

    Nothing here mentioned the spine and no test guarded item 12. It was
    found by a verifier who ran `systemctl` instead of reading the file --
    the same way the last four findings were found, and the reason §5 says a
    document asserting the state of a running system is the scar about
    settings that are present, parsed and doing nothing.

    The free tier is SHARED (§4), so the spine's state is not background: it
    is a condition of every figure this project produces, and *numbers taken
    while spine is paused are NOT comparable to numbers taken before it, in
    either direction.* A standing decision that nobody watches is
    indistinguishable from one forgotten -- the argument item 13 earned its
    detector on, applied to a decision rather than to a constant.

    It REPORTS and never acts: whether the spine runs is Tue's (§4, PLAN 12).
    """
    from monitor import detectors as det, status as monstatus

    def finding(active, says_paused, unit_present=True):
        ctx = det.Context([{"ts": time.time(), "kind": "wake"}])
        ctx.units = ({det.SPINE_UNIT: {"ActiveState": active,
                                       "ExecMainStartTimestamp": "Tue 00:12"}}
                     if unit_present else {})
        ctx.doctrine_says_paused = says_paused
        return det.shared_tier_contested(ctx)

    f = finding("active", True)
    check("spine: running while the doctrine says paused is an ALARM",
          f.state == det.ALARM, (f.state, f.msg[:80]))
    check("spine: and the alarm says which way to resolve it",
          "Fix the document or stop the spine" in f.msg, f.msg[:160])
    check("spine: a human is told -- this is not a quiet INFO line",
          f.human is True, f.human)

    f2 = finding("active", False)
    check("spine: running WITH the doctrine agreeing is not an alarm",
          f2.state == det.INFO, (f2.state, f2.msg[:80]))
    check("spine: but it still says the tier is shared, because a rate from "
          "this window is not comparable to one taken alone",
          "SHARED" in f2.msg, f2.msg[:120])

    f3 = finding("inactive", True)
    check("spine: stopped is OK, whatever the document says",
          f3.state == det.OK, (f3.state, f3.msg[:80]))

    f4 = finding("", True, unit_present=False)
    check("spine: and a box where the sibling is not installed says CANNOT "
          "TELL -- never 'paused', which is a different fact",
          f4.state == det.CANNOT_TELL, (f4.state, f4.msg[:80]))

    # THE CLAIM IS READ FROM THE DOCUMENT, not typed into the monitor. A
    # constant here repeating what §4 says would be a third thing to drift,
    # which is the fault this whole detector exists for.
    d = tmpdir()
    a, b, c = (os.path.join(d, x) for x in ("says", "silent", "empty"))
    os.makedirs(a), os.makedirs(b), os.makedirs(c)
    with io.open(os.path.join(a, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("- **SPINE IS PAUSED as of 2026-09-13 13:50 CEST** (Tue)\n")
    with io.open(os.path.join(b, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("- the spine runs beside this engine and always has\n")
    check("spine: the doctrine's claim is READ from CLAUDE.md",
          monstatus.doctrine_says_spine_paused(a) is True, a)
    check("spine: a file that does not claim it does not produce the claim",
          monstatus.doctrine_says_spine_paused(b) is False, b)
    check("spine: and a checkout with no doctrine makes no claim at all, "
          "rather than defaulting to one",
          monstatus.doctrine_says_spine_paused(c) is False, c)
    shutil.rmtree(d, ignore_errors=True)


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


def test_no_live_root_is_tracked_by_git_whatever_it_is_called():
    """80 files of run 1's archived live root went to the PUBLIC repo in
    `221b978`, 2026-09-16 -- journal, engine log, context, the creature's
    tools -- through an unscoped `git add -A`. Zero key-shaped strings, so no
    credential left; but raw model output on a public repo is the exact thing
    the evidence-pack rule was written to prevent (*"a pack holds raw model
    output and this repo is public"*).

    `.gitignore` guarded the PATH `live/`. The archive sat at the repo root
    under a different name, so the guard saw nothing -- a checker keyed on
    one literal, in the file that decides what leaves the machine. Found by
    a Windows checkout refusing a filename that ended in a dot.

    So the invariant is stated about CONTENT, not about a directory name: no
    tracked path may look like a live root. A journal is the one file every
    live root has and nothing else in the repo does; the creature's world
    (`body/mind`) is the one tree the creature writes and we never do.
    Fixture journals live under `tests/fixtures/journal/` and are scrubbed
    before commit, which is why that prefix -- and only that one -- is
    allowed through.
    """
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(["git", "-C", repo, "ls-files", "-z"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        check("tracked: this is a git checkout, or the assertion means nothing",
              False, r.stderr[:120])
        return
    tracked = [p for p in r.stdout.split("\0") if p]
    check("tracked: the listing is non-empty, or this proves nothing",
          len(tracked) > 100, len(tracked))

    def is_fixture(p):
        return p.startswith("tests/fixtures/")

    journals = [p for p in tracked
                if p.endswith("journal.jsonl") and not is_fixture(p)]
    check("tracked: no production journal is committed, under any name",
          not journals, journals[:5])
    worlds = [p for p in tracked if "/body/mind/" in p or p.startswith("body/mind/")]
    check("tracked: no creature's world is committed -- it is its, and it is "
          "raw model output", not worlds, worlds[:5])
    archives = [p for p in tracked if p.split("/")[0].startswith(("archive-", "live"))]
    check("tracked: nothing at the root named like a live root or its archive",
          not archives, sorted({p.split("/")[0] for p in archives}))
    logs = [p for p in tracked if p.endswith(("engine.log", "vitals.jsonl", "/STOP"))
            and not is_fixture(p)]
    check("tracked: no engine log, vitals stream or STOP file from a run",
          not logs, logs[:5])


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


def test_the_journal_says_which_body_the_creature_ran_in():
    """A journal that cannot say whether the creature was CONTAINED.

    2026-09-16. `live/monitor/alarms.jsonl` recorded `DISPROVEN at start:
    keys_unreadable` and cleared it four minutes later at the next start. The
    question that matters -- was the creature running uncontained in those
    four minutes, and did it execute anything -- could not be answered from
    the journal at all. A verifier answered it with `git show` against the
    commit SHA in `engine_start`, reading the unit file out of that commit to
    see whether `--body docker` was present yet. (It was not; the engine was
    on `LocalBody`, and nothing happened to run in the window.)

    That is §5's newest systemd scar in the journal's own voice: *there is no
    directive to read back -- only an absence.* `engine_start` carried the
    commit, the caps and the rungs, and said nothing about the single fact the
    whole of PLAN item 7 turns on.

    Asked of the BODY OBJECT, never of the `--body` flag, because the flag is
    what was believed and the object is what runs -- the same distinction that
    let a stale unit ship `--body docker` while `LocalBody` was live.
    """
    import run as runmod
    d = tmpdir()
    root = os.path.join(d, "live")
    # `--forever` so an unreachable model is a warning rather than a refusal
    # (the run must get PAST preflight to record anything), `--cycles 1` so it
    # is still bounded, `--pause 0` so it does not sleep on the way out.
    runmod.main(["--forever", "--cycles", "1", "--pause", "0",
                 "--root", root, "--body", "local",
                 "--rungs", os.path.join(d, "no-such-rungs.json")])
    j = Journal(os.path.join(root, "journal.jsonl"))
    starts = j.read(kinds=["engine_start"])
    check("body: the run recorded a start at all", len(starts) == 1,
          len(starts))
    s = starts[-1] if starts else {}
    check("body: and it names the body the creature actually got",
          s.get("body") in ("PathBody", "LocalBody"), s.get("body"))
    check("body: and says whether that body CONFINES anything",
          s.get("contained") is False, s.get("contained"))
    # The field is the class's own answer, so a container records the
    # opposite without anything here being told about docker.
    check("body: taken from the body's own contract, not from the flag",
          bodymod.DockerBody.CONTAINED is True
          and bodymod.LocalBody.CONTAINED is False)
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
    known = ("probe_stuck", "window_reread")
    raised = [c for c in tl if c["to"] == "ALARM" and c.get("human")
              and c["name"] not in known]
    check("replay: the control hour raises NOTHING else a human must look at",
          not raised, str([(c["name"], c["msg"][:60]) for c in raised])[:400])
    stuck = _first_raise(tl, "probe_stuck")
    check("replay: and the fault that WAS live in it is named -- view-subtask-logs, "
          "5 of 5, the chooser's default",
          stuck is not None and stuck["evidence"].get("tool") == "view-subtask-logs",
          str(stuck)[:200])
    # The SECOND fault it turned out to carry. Cut as a healthy hour on
    # 2026-09-14, when neither detector existed; each new detector has found
    # something in it. That is what a control is for, and it is why it stays
    # a real slice rather than being trimmed until it looks clean.
    reread = _first_raise(tl, "window_reread")
    check("replay: and the one found later -- a tool read four times inside an "
          "hour without being changed",
          reread is not None and "plan" in reread["msg"], str(reread)[:200])

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
    check("monitor: the control hour exits 1 for the two faults it carries, "
          "and for nothing else",
          rc == 1 and sorted(human) == ["probe_stuck", "window_reread"],
          (rc, sorted(human)))
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
             if r["kind"] not in ("cousin_probe", "cousin_verdict")
             and "tools/own/" not in (r.get("cmd") or "")]
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


def _digest_dir(path):
    import hashlib
    out = {}
    for n in sorted(os.listdir(path)):
        p = os.path.join(path, n)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                out[n] = hashlib.sha1(f.read()).hexdigest()
    return out


def test_a_run_can_be_seeded_with_a_tagged_inheritance():
    """PLAN item 11. §6.2 decided on 2026-09-10 to copy the parent's library
    -- a known-answer test set that would refute the design in a week rather
    than months -- and runs 1 and 2 both began from nothing, so it has never
    been executed. The condition attached to it is the interesting part:
    *tagging every inherited tool at t=0 and splitting every metric on it,
    for the life of the project.*
    """
    import seed_run
    d = tmpdir()
    src = os.path.join(d, "parent-mind", "tools", "own")
    os.makedirs(src)
    # All python, so the start-check is `compile()` and the fixture means the
    # same thing on every box. A `#!/bin/sh` fixture made this depend on
    # `bash -n`, which misfires on the Windows development box and would have
    # made the whole case set read differently there than on the laptop.
    for n, body in (("good", "#!/usr/bin/env python3\nprint('ok')\n"),
                    ("fine", "#!/usr/bin/env python3\nprint('also ok')\n"),
                    ("broken", "#!/usr/bin/env python3\nprint('unclosed\n"),
                    ("skipme.bak", "#!/usr/bin/env python3\n")):
        with open(os.path.join(src, n), "w", encoding="utf-8") as f:
            f.write(body)
    root = os.path.join(d, "live")

    # IT ASKS BEFORE IT TOUCHES ANYTHING, and cannot-tell is not permission.
    # The genuine cannot-tell is systemctl being unreachable -- a unit that
    # merely does not exist reports a definite `inactive`, which is an answer.
    real = seed_run.engine_is_running
    try:
        seed_run.engine_is_running = lambda unit=None: None
        ok, why = seed_run.check_safe(root)
        seed_run.engine_is_running = lambda unit=None: True
        ok_live, why_live = seed_run.check_safe(root)
        seed_run.engine_is_running = lambda unit=None: False
        ok_dead, _ = seed_run.check_safe(root)
    finally:
        seed_run.engine_is_running = real
    check("seed: it refuses when it cannot establish whether anything is "
          "running -- cannot tell is not permission", not ok, why)
    check("seed: and refuses outright while the engine is ALIVE",
          not ok_live and "ACTIVE" in why_live, why_live)
    check("seed: a stopped engine is the one case it proceeds on", ok_dead)

    os.makedirs(root)
    with open(os.path.join(root, "journal.jsonl"), "w", encoding="utf-8") as f:
        f.write('{"ts": 1, "kind": "wake"}\n')
    moved = seed_run.archive_root(root, "run-t")
    check("seed: the old run is MOVED aside, never deleted -- a trajectory "
          "cannot be repaired retroactively",
          moved and os.path.exists(os.path.join(moved, "journal.jsonl")), moved)
    check("seed: and the root is free for the new one",
          not os.path.exists(root), root)

    own = os.path.join(root, "body", "mind", "tools", "own")
    tagged = seed_run.inherit_library(src, own)
    seed_run.write_tag(root, tagged, "parent-mind")
    check("seed: the library came across", sorted(os.listdir(own)) ==
          ["broken", "fine", "good"], sorted(os.listdir(own)))
    check("seed: backups are not tools and did not come with it",
          "skipme.bak" not in os.listdir(own), sorted(os.listdir(own)))
    doc = seed_run.load_tag(root)
    check("seed: every inherited tool is tagged at t=0, with its bytes",
          set(doc["tools"]) == {"good", "fine", "broken"}
          and all(len(v["sha"]) == 64 for v in doc["tools"].values()), doc)
    check("seed: and with whether it STARTED, because a later byte change is "
          "a fix or a breakage and the hash alone cannot say which",
          doc["tools"]["good"]["starts"] is True
          and doc["tools"]["broken"]["starts"] is False, doc["tools"])

    s0 = seed_run.split_on_tag(root, own)
    check("seed: at t=0 everything is inherited and nothing else",
          (s0["inherited"], s0["built"], s0["modified"], s0["deleted"])
          == (3, 0, 0, 0), s0)

    # EVERY CASE A VERIFIER FOUND WRONG, 2026-09-16. The first version keyed
    # the tag by NAME and consulted the hash only after a name match, so a
    # rename counted as BUILT -- while PLAN.md claimed a hash-based tag made
    # renames harmless -- `repaired` meant *modified* including *broken*, and
    # a deleted inheritance vanished from every count.
    os.rename(os.path.join(own, "good"), os.path.join(own, "good-v2"))
    with open(os.path.join(own, "ownwork"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\nprint('mine')\n")
    with open(os.path.join(own, "broken"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\nprint('fixed')\n")
    with open(os.path.join(own, "fine"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env python3\nprint('now broken\n")
    s1 = seed_run.split_on_tag(root, own)
    check("seed: a RENAME with identical bytes is still the inheritance, "
          "followed by hash rather than lost to the new name",
          s1["renamed"] == 1 and s1["inherited"] == 3, s1)
    check("seed: a tool the creature BUILT is counted apart", s1["built"] == 1, s1)
    check("seed: REPAIRED means what §6.2 chose this library for -- a tool "
          "that COULD NOT START and now starts", s1["repaired"] == 1, s1)
    check("seed: and a tool the creature BROKE is counted too, or the number "
          "could only ever move the flattering way", s1["broke"] == 1, s1)
    check("seed: both are modifications, and that is reported separately from "
          "which direction they went", s1["modified"] == 2, s1)

    os.remove(os.path.join(own, "broken"))
    s2 = seed_run.split_on_tag(root, own)
    check("seed: a DELETED inheritance is visible, rather than looking like "
          "one that was never there", s2["deleted"] == 1, s2)
    check("seed: and it stops being counted as present",
          s2["inherited"] == 2, s2)
    shutil.rmtree(d, ignore_errors=True)


def test_the_page_splits_the_library_on_the_inheritance_tag():
    """PLAN item 11.2, the half that was missing: *every metric split on that
    tag*, for the life of the project (§6.2).

    The tagging was real and its own test was honest -- a verifier broke
    `split_on_tag`'s rename branch and watched six assertions go red. What
    nothing checked was whether anything READ the tag. `split_on_tag` had
    exactly one consumer in the repo, its own test; no metric surface --
    neither the page, nor `vitals.py`, nor `census.py`, nor the library the
    inhabitants are shown -- opened `inherited.json` at all. On the day run 3
    starts, `tools added`, the library table and `twin_pressure` would each
    report one undifferentiated number for a library that is mostly the
    parent's work, and the gate would stay green. **That is a channel dead on
    arrival, installed in advance for a run that has not happened yet.**

    The two states are asserted separately, because the dangerous one is not
    the missing feature but the plausible zero: a page that prints
    `0 inherited` when nothing was inherited reads identically to one that
    prints it because nobody looked.
    """
    import seed_run
    from monitor import derive as derivemod, status as monstatus
    d = tmpdir()
    root = os.path.join(d, "live")
    own = os.path.join(root, "body", "mind", "tools", "own")
    parent = os.path.join(d, "parent-mind", "tools", "own")
    os.makedirs(own)
    os.makedirs(parent)

    def write(name, text, into=None):
        p = os.path.join(into or own, name)
        with io.open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    GOOD = "#!/usr/bin/env python3\n# does: a thing\nprint('ok')\n"
    BROKEN = "#!/usr/bin/env python3\n# does: a thing\ndef (\n"
    # The parent's library at t=0: one sound, one that cannot start, one that
    # will be renamed, one that will be thrown away. READ, never run (§2.6);
    # here it is our own fixture rather than the real sibling project.
    write("archive-keep", GOOD, parent)
    write("archive-fixme", BROKEN, parent)
    write("archive-rename", GOOD.replace("a thing", "another thing"), parent)
    write("archive-gone", GOOD.replace("a thing", "a third thing"), parent)
    tagged = seed_run.inherit_library(parent, own)
    seed_run.write_tag(root, tagged, parent)

    check("provenance: the run is tagged at t=0 at all, or nothing below "
          "means anything",
          (seed_run.load_tag(root) or {}).get("count") == 4,
          seed_run.load_tag(root))

    # ...and then the creature lives in it.
    write("archive-fixme", GOOD)                       # repaired: now starts
    os.rename(os.path.join(own, "archive-rename"),
              os.path.join(own, "archive-renamed"))    # same bytes, new name
    os.remove(os.path.join(own, "archive-gone"))       # thrown away
    write("archive-mine", GOOD.replace("a thing", "my own thing"))

    library = sorted(n for n in os.listdir(own))
    prov = derivemod.provenance(root, library)
    check("provenance: the page can see the tag at all", prov is not None,
          prov)
    prov = prov or {}
    check("provenance: it counts what came from the parent apart from what "
          "the creature built", (prov.get("inherited"), prov.get("built"))
          == (3, 1), prov)
    check("provenance: a REPAIR -- could not start, now starts -- is counted "
          "as the thing §6.2 chose this library for",
          prov.get("repaired") == 1 and prov.get("broke") == 0, prov)
    check("provenance: a rename is followed rather than counted as new work",
          prov.get("renamed") == 1, prov)
    check("provenance: and a discarded inheritance does not simply vanish",
          prov.get("deleted") == 1, prov)
    check("provenance: the family line splits too -- three `archive-*` where "
          "two came from the parent is not three built here",
          (prov.get("families_inherited") or {}).get("archive") == 3, prov)

    # AND THE READER SEES IT. A derivation nothing renders is the same dead
    # channel one level further on.
    page = monstatus.render_md(_prov_data(monstatus, derivemod, root, library))
    check("provenance: the page says how much of the library is inherited",
          "3 of 4 inherited" in page, [l for l in page.splitlines()
                                       if "rovenance" in l])
    check("provenance: and names where the inheritance came from, so a "
          "figure can be traced to the library it describes",
          "parent-mind" in page, [l for l in page.splitlines()
                                  if "rovenance" in l])
    check("provenance: and tells its reader to split every rate on it",
          "Split every rate below on that line" in page, "")

    # THE OTHER STATE, which is today: nothing inherited. It must be a
    # sentence, never a zero.
    bare_root = os.path.join(d, "live2")
    os.makedirs(os.path.join(bare_root, "body", "mind", "tools", "own"))
    check("provenance: a run that inherited nothing says so rather than "
          "reporting zeros", derivemod.provenance(bare_root, []) is None,
          derivemod.provenance(bare_root, []))
    page2 = monstatus.render_md(_prov_data(monstatus, derivemod, bare_root, []))
    check("provenance: and the page says it in words",
          "everything here was built in this run" in page2,
          [l for l in page2.splitlines() if "rovenance" in l])
    shutil.rmtree(d, ignore_errors=True)


def _prov_data(monstatus, derivemod, root, library):
    """The smallest real `build_data` shape the renderer needs, with a real
    Context so this exercises the wiring rather than a hand-built dict."""
    from monitor import detectors as det
    ctx = det.Context([], now=1789516000.0)
    ctx.root = root
    ctx.library = set(library)
    return monstatus.build_data(ctx, [], {}, [])


def test_the_cull_has_an_owner_and_a_trigger():
    """PLAN item 10. §4 draws the line between a hold with a named trigger
    and a date, and inaction in the costume of caution. The cull had neither
    owner nor trigger; now it has both, and the one thing that must never
    change is who does NOT get it."""
    plan = _docs().get("PLAN.md", "")
    item = re.search(r"^###\s*10\.[^\n]*\n(.*?)(?=^###\s|\Z)", plan, re.M | re.S)
    body = re.sub(r"\s+", " ", item.group(1)).lower() if item else ""
    check("cull: the board carries the decision", bool(body), "(no item 10)")
    check("cull: with a named trigger and a date",
          "trigger" in body and "2026-09-16" in body, body[:200])
    check("cull: and a condition that can actually be checked, not 'more "
          "information'", "forty-eight hours" in body or "48 hours" in body,
          body[:200])
    check("cull: the creature owns it", "creature owns" in body, body[:200])
    doc = _doc_head(_docs().get("CLAUDE.md", ""))
    check("cull: and the doctrine file says so where decisions live",
          "who may propose a cull" in doc.lower(), "")
    # THE PART THAT MUST NOT DRIFT: the cousin never gains a write path. That
    # is asserted BEHAVIOURALLY elsewhere, and the only honest thing THIS test
    # can add is whether those assertions still exist to be run -- a deferral
    # to a test somebody later deletes is a boundary nobody checks.
    #
    # TWO tautologies have now stood in this spot, and the shape is worth more
    # than the fix. The first was `"def sync_cousin_world" in src`: a grep for
    # a name the author had just written, green for an empty body. Its
    # replacement -- written in the commit whose message announced that three
    # tautologies had been removed -- was `not getattr(Engine,
    # "cousin_may_write", False)` against an attribute that has never existed
    # anywhere in this repo, so it read False and passed under every possible
    # implementation, including a `sync_cousin_world` that shares the
    # creature's directory outright. A verifier found each of them.
    # **A check that cannot go red is worse than no check**, because it
    # occupies the place where a real one would be looked for.
    relied_on = ("test_nothing_the_cousin_runs_can_change_the_creatures_tools",
                 "test_a_cousin_shell_is_refused_in_a_body_that_confines_"
                 "nothing")
    own_src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    for name in relied_on:
        check("cull: the boundary's real assertion `%s` is still here to run"
              % name,
              re.search(r"^def %s[(]" % re.escape(name), own_src, re.M)
              is not None, name)


def test_the_human_can_speak_to_the_creature_once():
    """PLAN item 14. Tue, 2026-09-16: the chat channel stays. It lands last
    because it adds a surface to the creature's context, and a new surface
    arriving mid-measurement makes every number on either side incomparable.

    Delivered ONCE. *Surface on a change of state, never continuously* --
    a creature learns to skip a voice that speaks every wake, which is how
    the STALL trigger nagged eleven times in twenty-two cycles and how a want
    with no completion signal was re-served forever.
    """
    # `say` is a python hand with a `#!` line; without a python3 the body's
    # shell can run, this measures the host and not the channel.
    lacks = host_missing("posix_python")
    if lacks:
        cannot_run("the human speaking to the creature", " and ".join(lacks))
        return
    e, j, b, d = build_engine(["thinking", "thinking again", "and again"], [])
    cdir, inbox, readlog = e.chat_paths()
    os.makedirs(cdir, exist_ok=True)
    with open(inbox, "w", encoding="utf-8") as f:
        f.write("The laptop will be off between 09:00 and 11:00.")

    seen = []

    def spy(prompt):
        seen.append(prompt)
        return "thinking", {"model": "spy", "done_reason": "stop"}
    e.ask_creature = spy
    e.run_cycle()
    check("chat: the message reaches the creature",
          "off between 09:00 and 11:00" in seen[-1], seen[-1][-200:])
    check("chat: and it is told who is speaking -- not its user",
          "keeps the machine running" in seen[-1], "")
    rec = j.read(kinds=["chat_delivered"])
    check("chat: delivery is journalled with the text",
          len(rec) == 1 and "09:00" in (rec[0].get("text") or ""), str(rec)[:200])
    w = j.read(kinds=["wake"])[-1]
    check("chat: and the wake records that it was served",
          w.get("chat_served") is True, str(w))

    e.run_cycle()
    check("chat: it is NOT served again -- a voice that speaks every wake is "
          "one the creature learns to skip",
          "off between 09:00 and 11:00" not in seen[-1], seen[-1][-200:])
    check("chat: but nothing was destroyed to achieve that",
          "09:00" in io.open(readlog, encoding="utf-8").read(), readlog)
    check("chat: and only one delivery was ever recorded",
          len(j.read(kinds=["chat_delivered"])) == 1)

    # AND THE OTHER DIRECTION. A human who can speak and never hear back is
    # issuing orders, not opening a channel.
    import run as runmod
    hb = runmod.PathBody(os.path.join(d, "hands-body"))
    hb.bin = runmod.install_hands(hb)
    check("chat: the creature is given a way to answer",
          os.path.exists(os.path.join(hb.bin, "say")), sorted(os.listdir(hb.bin)))
    r = hb.run('say "the plan tool needs a way to sort by date"')
    check("chat: which works", r.code == 0, "%s %s" % (r.code, r.stderr[:160]))
    out = os.path.join(hb.mind, "outbox.md")
    check("chat: and lands where a human will find it",
          os.path.exists(out) and "sort by date" in io.open(out, encoding="utf-8").read(),
          out)
    r2 = hb.run("say")
    check("chat: an empty message is refused rather than sent",
          r2.code != 0 and "usage" in (r2.stderr or "").lower(), r2.stderr[:160])

    # 14.4 -- EXACTLY ONE FILE, INSIDE THE CREATURE'S OWN TREE. Nothing
    # tested this when it shipped, which an independent verifier said plainly.
    import hashlib

    def tree(path):
        out = {}
        for dp, _dn, fn in os.walk(path):
            for n in fn:
                p = os.path.join(dp, n)
                try:
                    with open(p, "rb") as fh:
                        out[os.path.relpath(p, path)] = hashlib.sha1(
                            fh.read()).hexdigest()
                except OSError:
                    pass
        return out
    # WATCHED FROM ABOVE THE BODY, not from inside it. The first version
    # walked `hb.root`, and a verifier pointed out that the criterion says
    # *nothing else anywhere* while the check said *nothing else under the
    # body* -- `PathBody` puts HOME inside the body, so it caught a stray
    # `~/.say-leak`, and would have missed a write to an absolute path beside
    # it. Watching the whole scratch tree covers the body, its HOME, and
    # anything landing next to them.
    #
    # What stays unwatched, stated rather than implied: a write to an
    # arbitrary absolute path elsewhere on the machine. That is unbounded and
    # no walk can close it; what closes it is that `say` is nine lines of our
    # own code, appending to one path built from $MIND.
    before = tree(d)
    hb.run('say "a second message"')
    after = tree(d)
    # The body writes its own command script into the mind on every run, so
    # that is the harness and not `say`; everything else must be untouched.
    touched = sorted(k for k in set(before) | set(after)
                     if before.get(k) != after.get(k)
                     and ".cmd-" not in k)
    check("chat: saying something changes exactly one file, and it is the "
          "outbox", [t for t in touched] == [os.path.relpath(out, d)], touched)

    # 14.3 -- and somebody READS it. When `say` shipped, `outbox.md` was read
    # by no detector, no page and no document: a channel whose far end nobody
    # reads is the dead-channel scar with a politer face.
    from monitor import detectors as det
    # The detector reads `<root>/body/mind/outbox.md`, which is where the
    # deployment keeps it; lay the file out that way rather than pointing the
    # detector somewhere convenient.
    os.makedirs(os.path.join(d, "root", "body", "mind"), exist_ok=True)
    shutil.copy2(out, os.path.join(d, "root", "body", "mind", "outbox.md"))
    ctx = det.Context([{"ts": time.time(), "kind": "wake"}])
    ctx.root = os.path.join(d, "root")
    f = det.creature_said(ctx)
    check("chat: the monitor reports what the creature said, so the far end "
          "of the channel is read by something",
          f.state == det.INFO and "2 message" in f.msg and "second message" in f.msg,
          "%s %s" % (f.state, f.msg))
    empty = det.creature_said(det.Context([], now=time.time()))
    check("chat: and says nothing when there is nothing to say",
          empty.state in (det.OK, det.CANNOT_TELL), empty.msg)
    hb.destroy(); b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_respawn_may_recreate_a_container_and_never_a_mind():
    """PLAN item 15, decided 2026-09-16 -- and item 7 is what decided it.

    The body drill found that `LocalBody.respawn` sets a flag and re-probes
    without rebuilding the tree, so a creature that removes its own `$MIND`
    leaves the engine looping on `error where=body` forever with nothing
    raising. The three options were: raise (systemd restarts, and
    `LocalBody.__init__` silently rebuilds the creature's world EMPTY),
    rebuild on respawn (the same loss, quieter), or stop for a human.

    A container changes the question. The creature's world is a bind mount on
    the HOST; the container is a process with an interpreter in it. So the
    rule is about WHAT is being recreated, not about who does it:

        a respawn may recreate a CONTAINER, and must never recreate a MIND.
    """
    calls = []

    class Fake(bodymod.DockerBody):
        def __init__(self):
            bodymod.DockerBody.__init__(self, "c", mind="/host/mind")
            self.alive = False

        def responds(self):
            return self.alive

    # No way back supplied: it degrades to a restart and still invents nothing.
    b = Fake()
    b.recreate = None
    check("respawn: without a way back it reports failure rather than "
          "inventing a world", b.respawn() is False)

    b2 = Fake()

    def bring_back():
        calls.append(1)
        b2.alive = True
    b2.recreate = bring_back
    check("respawn: with one, a container that is GONE is rebuilt",
          b2.respawn() is True and len(calls) == 1, calls)

    # THE HALF THAT MUST NOT CHANGE: a LocalBody's body IS the creature's
    # world, so it still refuses, and `body_unrecoverable` still alarms.
    d = tmpdir()
    lb = bodymod.LocalBody(os.path.join(d, "body"))
    own = os.path.join(lb.mind, "tools", "own")
    os.makedirs(own, exist_ok=True)
    with open(os.path.join(own, "plan"), "w", encoding="utf-8") as f:
        f.write("the creature's work\n")
    shutil.rmtree(lb.mind, ignore_errors=True)
    check("respawn: a LocalBody whose mind is gone does NOT rebuild it -- an "
          "empty tree handed back as a recovery is §2.1 broken by the "
          "framework", lb.respawn() is False)
    check("respawn: and it does not quietly recreate the world either",
          not os.path.isdir(own), own)

    # THE WIRING, which is what actually changed: only the thing that knows
    # the mounts can hand a body a way back, so `ensure_container` supplies
    # one. Without this the decision is a docstring.
    import run as runmod
    if hasattr(os, "getuid"):
        class FakeHost(object):
            mind, bin = "/host/mind", "/host/bin"

        class R(object):
            returncode, stdout, stderr = 0, "true", ""
        import subprocess as _sp
        keep = _sp.run
        try:
            _sp.run = lambda *a, **k: R()
            got = runmod.ensure_container("c", "img", FakeHost())
        finally:
            _sp.run = keep
        check("respawn: the container body is handed a way back by whatever "
              "knows its mounts -- without that, the decision is a docstring",
              callable(getattr(got, "recreate", None)), got)
    shutil.rmtree(d, ignore_errors=True)


_PLAN_TOOL = ("```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n# does: keeps "
              "the plan\\n# call: plan list\\necho REAL-OUTPUT\\n' > tools/own/plan "
              "&& chmod +x tools/own/plan\n```")


def test_a_cousin_command_is_recorded_bare_only_when_it_carried_no_arguments():
    """`bare` is read off the command, never hard-coded.

    The shell path shipped with `bare=False` on every probe. So when the
    cousin -- told by its own prompt to *make up plausible inputs* -- ran
    `view-subtask-logs task-123` and the tool correctly answered *task-123
    not found* with exit 1, the library rendered *NEVER WORKED for them (1
    real failures)* to both inhabitants every wake. The 2026-09-14 misreading
    (thirty usage refusals read as thirty failures) rebuilt through the new
    door, and found live on the first evening the shell worked.

    The flag now means one thing whoever composed the command: the block was
    the tool's name and nothing else.
    """
    import run as runmod
    from kernel import cousin as cousinmod
    for invoke, expect in (("```bash\nplan\n```", True),
                           ("```bash\nplan list\n```", False)):
        e, j, b, d = build_engine([_PLAN_TOOL], [invoke, ACCEPT_REPLY])
        cb = runmod.PathBody(os.path.join(d, "cousin-body"))
        e.cousin_body = cb
        e.run_cycle()
        probe = (j.read(kinds=["cousin_probe"]) or [{}])[-1]
        check("bare-by-command: %r is recorded bare=%s" % (invoke.split("\n")[1], expect),
              probe.get("bare") is expect, (probe.get("cmd"), probe.get("bare")))
        b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)
    check("bare-by-command: a comment does not make a call bare or not",
          cousinmod.argless("# try it\nplan") is True)
    check("bare-by-command: a variable set and used is not a bare call",
          cousinmod.argless("X=plan\n$X list") is False)
    check("bare-by-command: nothing at all is bare -- there is no command to "
          "have carried arguments", cousinmod.argless("") is True)


def test_the_cousins_whole_block_runs_and_the_invocation_call_is_journalled():
    """Two silences in one probe.

    `choose_invocation` took the FIRST LINE of the cousin's block, so a cousin
    that set a variable and used it, or looked an ID up and then called the
    tool, had everything after line one dropped -- and was then handed a
    transcript of a command it did not issue and asked to judge on it. The
    framework manufacturing the cousin's own testimony.

    And the invocation is a MODEL call -- the second per visit since item 9
    -- whose rung, model, finish and full proposal were thrown away on the
    spot. The cost of the shell could not be split by rung, and a proposal
    cut by the budget could not be told from a short one. Store the raw
    evidence: the oldest scar in §5.
    """
    import run as runmod
    e, j, b, d = build_engine([_PLAN_TOOL],
                              ["Let me set it up first.\n```bash\nX=plan\n$X list\n```",
                               ACCEPT_REPLY])
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.cousin_body = cb
    e.run_cycle()
    probe = (j.read(kinds=["cousin_probe"]) or [{}])[-1]
    check("whole block: both lines of the cousin's block are what ran",
          "X=plan" in (probe.get("cmd") or "") and "$X list" in (probe.get("cmd") or ""),
          probe.get("cmd"))
    check("whole block: and it really ran as a block -- the second line used "
          "the first", "REAL-OUTPUT" in (probe.get("stdout") or ""),
          probe.get("stdout"))
    check("whole block: the proposal's shape is recorded",
          probe.get("proposal_lines") == 2, probe.get("proposal_lines"))
    check("invocation call: its model is on the probe",
          probe.get("invoke_model") == "scripted", probe.get("invoke_model"))
    check("invocation call: and how it finished",
          probe.get("invoke_finish") == "stop", probe.get("invoke_finish"))
    check("invocation call: and the cousin's full reply, so a cut proposal "
          "can be told from a short one",
          "Let me set it up first" in (probe.get("proposal") or ""),
          (probe.get("proposal") or "")[:80])
    b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_library_reports_outcomes_as_facts_and_its_users_verdicts():
    """The word FAILED left the library on 2026-09-16, and this is why.

    While the harness called every tool bare, a non-zero exit with the `bare`
    flag off meant one thing: called properly, and it broke. Once the cousin
    chooses the arguments the same exit means *the tool did not like what its
    user typed* -- which may be the tool working perfectly on an ID the user
    invented. The framework cannot tell; the cousin can, and does, in the
    verdict it gives two seconds later. So the line reports what the
    framework knows (exit codes) beside what the cousin said (accepted,
    returned), and asserts nothing it cannot know.
    """
    import kernel.library as librarymod
    import run as runmod
    d = tmpdir()
    own = os.path.join(d, "own")
    _write_tool(own, "viewer", does="views a task", call="viewer <id>")
    j = Journal(os.path.join(d, "journal.jsonl"))
    j.append("cousin_probe", tool="viewer", exit_code=1, bare=False,
             cmd="viewer task-123", stdout="", stderr="task-123 not found")
    j.append("cousin_verdict", tool="viewer", verdict="ACCEPTED", tried="ran it",
             outcome="it told me the id was wrong", to_creature="fine", want="")
    hist = librarymod.use_history(j)
    rec = hist.get("viewer") or {}
    check("facts: a non-zero exit with chosen arguments is counted as what it "
          "is", rec.get("nonzero") == 1 and rec.get("ok") == 0, rec)
    check("facts: and what its user SAID about it is counted beside it",
          rec.get("accepted") == 1 and rec.get("returned") == 0, rec)
    line = librarymod.status(rec)
    check("facts: the line never calls it a failure -- that is the cousin's "
          "word to use", "FAILED" not in line and "NEVER WORKED" not in line
          and "real failure" not in line, line)
    check("facts: it says what happened", "never exited 0 for them" in line
          and "exited non-zero with arguments its user chose" in line, line)
    check("facts: and what its user said", "accepted it once" in line, line)

    j.append("cousin_probe", tool="viewer", exit_code=0, bare=False,
             cmd="viewer task-1", stdout="ok", stderr="")
    j.append("cousin_verdict", tool="viewer", verdict="RETURNED", tried="ran it",
             outcome="wrong task", to_creature="it showed me the wrong one")
    line2 = librarymod.status(librarymod.use_history(j)["viewer"])
    check("facts: a mixed record reports both exits and both verdicts",
          "1 exited 0 and 1 exited non-zero" in line2
          and "accepted it once and returned it once" in line2, line2)

    # A verdict from before verdicts named their tool is not counted against
    # anything: it cannot be attributed, and guessing is the fault this file
    # is full of.
    j.append("cousin_verdict", verdict="RETURNED", tried="x", outcome="y",
             to_creature="z")
    rec3 = librarymod.use_history(j)["viewer"]
    check("facts: an unattributed verdict counts for no tool",
          rec3.get("returned") == 1, rec3)

    # END TO END: the engine puts the tool on the verdict it journals.
    e, j2, b, d2 = build_engine([_PLAN_TOOL], ["```bash\nplan list\n```", ACCEPT_REPLY])
    cb = runmod.PathBody(os.path.join(d2, "cousin-body"))
    e.cousin_body = cb
    e.run_cycle()
    v = (j2.read(kinds=["cousin_verdict"]) or [{}])[-1]
    check("facts: the engine journals WHICH tool a verdict was about",
          v.get("tool") == "plan", v)
    b.destroy(); cb.destroy(); shutil.rmtree(d2, ignore_errors=True)
    shutil.rmtree(d, ignore_errors=True)


def test_the_cousins_world_mirrors_the_creatures_and_carries_only_user_hands():
    """The copy that keeps §2.3 was two directories out of a world.

    `sync_cousin_world` copied `tools/own` and `data`. The creature's tools
    do not confine themselves to those: `compare-with-baseline` reads its
    baseline back with `recall`, which reads `state/memory.json`;
    `set-baseline` writes it with `remember`; others reach for files at the
    mind's root. And the cousin's body had NO hands at all -- right for
    `tool-edit` and `tool-new` (a user does not build) and `say` (the
    creature's voice to the human), wrong for `recall`, without which those
    tools fail in the cousin's shell for a reason that is ours. The cousin
    would report it faithfully and the creature would be billed: the
    relative-root scar, arriving through the copy meant to keep §2.3.

    A user's shell holds the creature's world as it is. `remember` in that
    shell writes to the copy, which the next visit throws away -- so the
    boundary is unchanged and asserted here by attack.
    """
    lacks = host_missing("posix", "posix_python")
    if lacks:
        cannot_run("the cousin's mirrored world and user hands",
                   " and ".join(lacks))
        return
    import json
    import run as runmod
    e, j, b, d = build_engine([""], [""])
    own = os.path.join(b.mind, "tools", "own")
    _write_tool(own, "plan", does="keeps the plan", call="plan list")
    os.makedirs(os.path.join(b.mind, "state"), exist_ok=True)
    mem = os.path.join(b.mind, "state", "memory.json")
    with io.open(mem, "w", encoding="utf-8") as f:
        json.dump({"baseline-parent-id": "p1"}, f)
    with io.open(os.path.join(b.mind, "notes.txt"), "w", encoding="utf-8") as f:
        f.write("a loose file at the root of the mind\n")
    with io.open(os.path.join(b.mind, "data", "plan.json"), "w", encoding="utf-8") as f:
        f.write("[]")
    with io.open(os.path.join(b.mind, ".cmd-999.sh"), "w", encoding="utf-8") as f:
        f.write("echo not part of any world\n")

    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    cb.bin = runmod.install_hands(cb, only=runmod.USER_HANDS)
    e.cousin_body = cb
    n = e.sync_cousin_world()
    check("mirror: the tools are there, and counted", n == 1, n)
    for rel in (("state", "memory.json"), ("notes.txt",), ("data", "plan.json")):
        check("mirror: %s is in the cousin's world" % "/".join(rel),
              os.path.exists(os.path.join(cb.mind, *rel)), rel)
    check("mirror: the body's own command scripts are not part of any world",
          not os.path.exists(os.path.join(cb.mind, ".cmd-999.sh")))

    r = cb.run("command -v recall >/dev/null && command -v remember >/dev/null "
               "&& ! command -v tool-edit >/dev/null && ! command -v tool-new "
               ">/dev/null && ! command -v say >/dev/null && echo USER-ONLY")
    check("hands: a user's hands and none of a builder's", "USER-ONLY" in r.stdout,
          (r.code, r.stdout, r.stderr[:120]))
    r2 = cb.run("recall baseline-parent-id")
    # THIS ASSERTION WAS REVERSED 2026-09-18 (PLAN item 20.1). It used to read
    # `check("recall reads the creature's memory as copied", "p1" in
    # r2.stdout)` -- correct for the semantics of the day it was written, and
    # wrong as a property: `state/memory.json` is the author's NOTES, and a
    # judge that can read the builder's own "verified: true" is not testing a
    # handover. What the 2026-09-16 scar actually required is the half kept
    # below: the hand must EXIST and ANSWER, because its ABSENCE is what made
    # the creature's tools die `command not found` in the cousin's shell for a
    # reason that was ours, and be billed for it.
    check("hands: recall RUNS in the cousin's shell -- a missing hand is how "
          "the creature got billed for our omission",
          r2.code == 0 and "not found" not in (r2.stderr or ""),
          (r2.code, r2.stdout, r2.stderr[:120]))
    check("hands: and it reads the COUSIN's notes, never the creature's",
          "p1" not in r2.stdout, (r2.code, r2.stdout, r2.stderr[:120]))

    # THE ATTACK: remember in the cousin's shell must change nothing the
    # creature will ever see. Since item 20.1 the cousin's OWN note DOES
    # survive to its next visit -- that is the point of it, and it is why the
    # assertion below is now three assertions instead of one. Weakening a
    # boundary test to let a change pass is a thing this file has a scar for,
    # so the boundary is stated more precisely rather than more loosely: the
    # creature's work is restored whole every visit, the creature's memory is
    # never touched, and the only thing that crosses a visit is the cousin's
    # own note, which the creature never reads.
    cb.run("remember baseline-parent-id HIJACKED")
    with io.open(mem, encoding="utf-8") as f:
        check("boundary: remember in the cousin's shell did not reach the "
              "creature's memory", json.load(f).get("baseline-parent-id") == "p1")
    e.sync_cousin_world()
    r3 = cb.run("recall baseline-parent-id")
    check("boundary: the cousin's own note survives to its next visit, which "
          "is item 20.1 -- it judges a builder it is told wakes and forgets",
          "HIJACKED" in r3.stdout, r3.stdout)
    check("boundary: and the creature's note is STILL not in its hands on a "
          "later visit", "p1" not in r3.stdout, r3.stdout)
    with io.open(mem, encoding="utf-8") as f:
        check("boundary: the creature's memory is untouched after the second "
              "visit too", json.load(f).get("baseline-parent-id") == "p1")
    check("boundary: and the creature's WORK is restored whole each visit -- "
          "notes are the only thing that crosses",
          os.path.exists(os.path.join(cb.mind, "data", "plan.json")))

    # `only=` is exact: a stray builder's hand in that bin is removed.
    stray = os.path.join(cb.root, "bin", "tool-edit")
    with io.open(stray, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\necho no\n")
    runmod.install_hands(cb, only=runmod.USER_HANDS)
    check("hands: a hand this body must not have is removed, whoever put it there",
          not os.path.exists(stray))

    # And the deployment mounts that bin into the cousin's container, read-only.
    class FakeHost(object):
        mind, bin = "/x/cousin/mind", "/x/cousin/bin"
    seen = {}

    class R(object):
        returncode, stdout, stderr = 0, "true", ""
    import subprocess as _sp
    keep = _sp.run

    def fake_run(argv, **_k):
        if argv[:2] == ["docker", "run"]:
            seen["argv"] = argv
        if argv[:2] == ["docker", "inspect"]:
            r = R(); r.returncode = 1; return r
        return R()
    try:
        _sp.run = fake_run
        runmod.ensure_container("c", "img", FakeHost())
    finally:
        _sp.run = keep
    argv = seen.get("argv") or []
    check("hands: the container gets the user hands mounted, read-only",
          any(a == "/x/cousin/bin:%s:ro" % bodymod.DockerBody.HANDS for a in argv),
          argv)
    b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_container_runs_the_shell_the_contract_names():
    """The prompt says ```bash, the parser requires the `bash` tag,
    `LocalBody` ran `bash <script>` -- and `DockerBody` ran `sh -c`, which
    on the image is dash. Item 7 changed the creature's interpreter without
    anyone deciding to. Measured 2026-09-16 over 307 commands since the
    container went live: zero dash-only failures and one bash-only
    construct, so the cost was nil. Fixed anyway: a promise the body does
    not keep is the relative-root scar's shape, and the next model may
    write `[[`.
    """
    b = bodymod.DockerBody("c", mind="/host/mind")
    argv = b.argv("echo hi")
    check("shell: the container runs the shell the contract names",
          argv[3:5] == ["bash", "-c"], argv[:5])
    check("shell: and the composed command is what that shell gets",
          argv[-1].rstrip().endswith("echo hi"), argv[-1][-40:])
    dockerfile = io.open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "deploy", "Dockerfile"), encoding="utf-8").read()
    check("shell: the image build proves bash is there, in daylight",
          "RUN bash -c" in dockerfile, "")


def test_the_pack_checks_the_real_keys_byte_for_byte():
    """Shapes are a guess about what a key looks like. 2026-09-16, twice in
    one day: a shape scan refused a live pack on 216 tool names, and a
    hand-rolled one reported the creature's memory held a credential -- it
    was `subtask-log-filter` again. Meanwhile the decisive check, *is any
    real key in these bytes*, had never been run. The pack runs it now, and
    the manifest says how many keys were checked so "0 key-shaped strings" is
    never mistaken for "0 keys".
    """
    from monitor import pack
    d = tmpdir()
    keys = os.path.join(d, "keys")
    os.makedirs(keys)
    # Short and hyphenated, so no SHAPE fires and only the byte-for-byte
    # check can see it -- otherwise this proves the old scan, not the new one.
    with io.open(os.path.join(keys, "a.key"), "w", encoding="utf-8") as f:
        f.write("real-key-Q7-1234-zz\n")
    root = os.path.join(d, "root")
    os.makedirs(root)
    with io.open(os.path.join(root, "journal.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": 1.0, "kind": "think",
                            "raw": "the creature printed real-key-Q7-1234-zz"}) + "\n")
    check("real keys: no shape fires on a short hyphenated key -- so what "
          "follows tests the decisive check and nothing else",
          not pack.scan_secrets(pack.candidates(root)))
    refused = None
    try:
        pack.build(root, os.path.join(d, "out"), "t", keys_dir=keys)
    except pack.PackRefused as e:
        refused = str(e)
    check("real keys: a real credential in the root refuses the pack",
          refused is not None and "REAL credential" in (refused or ""), refused)
    check("real keys: and nothing was written",
          not os.path.exists(os.path.join(d, "out")))

    with io.open(os.path.join(root, "journal.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": 1.0, "kind": "think", "raw": "clean"}) + "\n")
    _t, _m, man = pack.build(root, os.path.join(d, "out"), "t", keys_dir=keys)
    check("real keys: a clean root packs, and the manifest says how many keys "
          "it checked", "1 checked byte-for-byte" in man["secret_scan"]
          and "0 real keys" in man["secret_scan"], man["secret_scan"])
    _t2, _m2, man2 = pack.build(root, os.path.join(d, "out2"), "t",
                                keys_dir=os.path.join(d, "no-such-dir"))
    check("real keys: with no key files to check it SAYS so rather than "
          "claiming a check it did not make",
          "no key files were readable" in man2["secret_scan"], man2["secret_scan"])
    shutil.rmtree(d, ignore_errors=True)


def test_a_container_whose_mounts_drifted_is_recreated_not_reused():
    """`ensure_container` asked one question of an existing container -- is
    it running -- and reused it whatever it was mounted with. On 2026-09-16
    the cousin's container predated the user-hands mount and came back up
    after the deploy without `recall` on its PATH, while the code that had
    just shipped said the mount was there. A directive present in the code
    and absent from the running thing is §5's oldest systemd shape, and this
    is the container-flavoured instance.

    A container holds nothing -- the world is a bind mount on the host -- so
    recreating one when its mounts no longer match costs nothing and is the
    only honest response.
    """
    lacks = host_missing("posix")
    if lacks:
        cannot_run("container mount drift", " and ".join(lacks))
        return
    import json
    import subprocess as _sp
    import run as runmod

    class Host(object):
        mind, bin = os.path.abspath("x-mind"), os.path.abspath("x-bin")

    stale = json.dumps([{"Source": Host.mind, "Destination": bodymod.DockerBody.MIND,
                         "RW": True}])           # created before the hands mount
    current = json.dumps([{"Source": Host.mind, "Destination": bodymod.DockerBody.MIND,
                           "RW": True},
                          {"Source": Host.bin, "Destination": bodymod.DockerBody.HANDS,
                           "RW": False}])

    def drive(mounts_json):
        calls = []

        class R(object):
            def __init__(self, rc=0, out=""):
                self.returncode, self.stdout, self.stderr = rc, out, ""

        def fake_run(argv, **_k):
            calls.append(argv)
            if argv[:2] == ["docker", "inspect"] and "{{.State.Running}}" in argv:
                return R(0, "true\n")
            if argv[:2] == ["docker", "inspect"] and "{{json .Mounts}}" in argv:
                return R(0, mounts_json)
            return R(0, "true")
        keep = _sp.run
        try:
            _sp.run = fake_run
            runmod.ensure_container("c", "img", Host())
        finally:
            _sp.run = keep
        return calls

    calls = drive(stale)
    check("drift: a running container with the OLD mounts is removed",
          any(a[:3] == ["docker", "rm", "-f"] for a in calls), calls)
    runs = [a for a in calls if a[:2] == ["docker", "run"]]
    check("drift: and recreated", bool(runs), calls)
    check("drift: with the mount that was missing, read-only",
          runs and any(x == "%s:%s:ro" % (Host.bin, bodymod.DockerBody.HANDS)
                       for x in runs[0]), runs[0] if runs else calls)

    calls2 = drive(current)
    check("drift: a container whose mounts already match is left alone",
          not any(a[:3] == ["docker", "rm", "-f"] for a in calls2)
          and not any(a[:2] == ["docker", "run"] for a in calls2), calls2)

    # PLAN 18.4, the same shape one field over. A container is created FROM an
    # image and keeps it for life, so `docker build` can succeed, the tag can
    # move, and the body goes on running yesterday's Dockerfile while every
    # document says otherwise. The unit rebuilds on every start, so this drift
    # is guaranteed rather than unlikely.
    def drive_img(container_image, tag_image):
        calls = []

        class R(object):
            def __init__(self, rc=0, out=""):
                self.returncode, self.stdout, self.stderr = rc, out, ""

        def fake_run(argv, **_k):
            calls.append(argv)
            if argv[:2] == ["docker", "inspect"] and "{{.State.Running}}" in argv:
                return R(0, "true\n")
            if argv[:2] == ["docker", "inspect"] and "{{json .Mounts}}" in argv:
                return R(0, current)
            if argv[:2] == ["docker", "inspect"] and "{{.Image}}" in argv:
                return R(0, container_image) if container_image else R(1, "")
            if argv[:3] == ["docker", "image", "inspect"]:
                return R(0, tag_image) if tag_image else R(1, "")
            return R(0, "true")
        keep = _sp.run
        try:
            _sp.run = fake_run
            runmod.ensure_container("c", "img", Host())
        finally:
            _sp.run = keep
        return calls

    moved = drive_img("sha256:old\n", "sha256:new\n")
    check("drift: a container still running the image it was BUILT from is "
          "recreated when the tag has moved -- the unit rebuilds every start, "
          "so this is guaranteed rather than unlikely",
          any(a[:3] == ["docker", "rm", "-f"] for a in moved)
          and any(a[:2] == ["docker", "run"] for a in moved), moved)
    same = drive_img("sha256:same\n", "sha256:same\n")
    check("drift: and left alone when the image is the one it holds",
          not any(a[:3] == ["docker", "rm", "-f"] for a in same), same)
    # CANNOT TELL, never a reason to act -- the mounts check earned this rule
    # and it applies to every field beside it.
    blind = drive_img(None, "sha256:new\n")
    check("drift: an unreadable image id does NOT recreate the container, "
          "because a daemon that cannot answer is not evidence that it drifted",
          not any(a[:3] == ["docker", "rm", "-f"] for a in blind), blind)
    blind2 = drive_img("sha256:old\n", None)
    check("drift: and neither does an unreadable tag",
          not any(a[:3] == ["docker", "rm", "-f"] for a in blind2), blind2)


def test_a_dead_cousin_body_is_a_lost_probe_never_a_transcript():
    """The creature's body is proven before every block (`ensure_body`); the
    cousin's never was. A cousin container that had died would return an OCI
    error with `setup_failed=True`, `evidence()` would read `.code` and
    `.stderr` off it as if a tool had run, and the cousin would then be asked
    to judge the creature's work on a transcript of our infrastructure
    failing. That is a fabricated complaint with the framework as its author
    -- the one outcome this design exists to prevent.

    So: the body is proven first, and if it cannot be brought back the probe
    is recorded as LOST (`exit_code=None`, its own `chosen_by`), no verdict is
    asked, and the cycle fails so the supervisor's bound acts.
    """
    import run as runmod
    from kernel import backends
    e, j, b, d = build_engine([_PLAN_TOOL], ["```bash\nplan list\n```", ACCEPT_REPLY])
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    cb.can_respawn = False
    cb.kill()
    e.cousin_body = cb
    raised = None
    try:
        e.run_cycle()
    except backends.LadderExhausted as ex:
        raised = ("wrong kind", ex)
    except Exception as ex:                      # noqa: BLE001 -- the point
        raised = ("failure", ex)
    check("dead body: the cycle FAILS rather than walking on",
          raised is not None and raised[0] == "failure", raised)
    probes = j.read(kinds=["cousin_probe"])
    p = probes[-1] if probes else {}
    check("dead body: the probe is recorded as lost, not as an exit code",
          p.get("exit_code") is None and p.get("chosen_by") == "cousin_body_down",
          p)
    check("dead body: and it still says what the cousin had wanted to run",
          p.get("cmd") == "plan list", p.get("cmd"))
    check("dead body: NO verdict was asked on an infrastructure failure",
          not j.read(kinds=["cousin_verdict"]), j.read(kinds=["cousin_verdict"]))
    rs = j.read(kinds=["body_respawn"])
    check("dead body: the respawn record says WHOSE body it was",
          rs and rs[-1].get("who") == "cousin" and rs[-1].get("ok") is False, rs)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_cousin_runs_the_tool_with_its_own_hands():
    """PLAN item 9. §4 gives *running the test* to the cousin, and the harness
    invoked every tool BARE -- so it owned a job it structurally could not do.
    Measured 2026-09-15: `view-subtask-logs` probed 63 times, accepted on its
    usage line, the same want asked six times. §5 has said *"untestable until
    the cousin has its own shell"* since 2026-09-10.

    The tempting repair is for the kernel to build a command from the
    `# call:` header. That is the wrong repair: it moves judgement back into
    the framework, which is the 99% this design deleted.
    """
    invoke = "```bash\nplan list\n```"
    e, j, b, d = build_engine(
        ["```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n# does: keeps the "
         "plan\\n# call: plan list\\necho REAL-OUTPUT\\n' > tools/own/plan && "
         "chmod +x tools/own/plan\n```"],
        [invoke, ACCEPT_REPLY])
    import run as runmod
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.cousin_body = cb
    own = os.path.join(b.mind, "tools", "own")
    e.run_cycle()

    probe = (j.read(kinds=["cousin_probe"]) or [{}])[-1]
    check("cousin hands: the tool was run with a command the COUSIN wrote",
          probe.get("cmd") == "plan list", probe)
    check("cousin hands: and the record says who chose it",
          probe.get("chosen_by") == "cousin", probe.get("chosen_by"))
    check("cousin hands: what it ran is journalled, not just which tool",
          "cmd" in probe and probe.get("stdout") is not None, sorted(probe))
    check("cousin hands: it really ran -- the tool's own output came back",
          "REAL-OUTPUT" in (probe.get("stdout") or ""), probe.get("stdout"))
    check("cousin hands: this is no longer a bare call",
          probe.get("bare") is False, probe.get("bare"))
    check("cousin hands: and it was given the creature's library to run "
          "against", (probe.get("library_copied") or 0) >= 1,
          probe.get("library_copied"))
    b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_cousin_shell_is_refused_in_a_body_that_confines_nothing():
    """PLAN item 9.4, rebuilt after an independent verifier took it apart.

    The claim was that the cousin's COPY of the library keeps §2.3
    structurally. A copy only holds if the body cannot reach past it -- and
    `LocalBody` is `bash <script>` with `cwd=mind`, where a working directory
    is a convenience, not a boundary. The verifier breached it six ways in
    minutes: `../..`, an absolute path, `$MIND/../..`, python instead of a
    redirect, deleting the creature's tool, and **adding one**, which makes
    the second user a second builder -- the one thing §2.3 forbids.

    So the repair is in two parts: prove the escape is real, and make the
    deployment refuse the configuration in which it is possible.
    """
    import run as runmod
    d = tmpdir()
    creature = bodymod.LocalBody(os.path.join(d, "creature"))
    own = os.path.join(creature.mind, "tools", "own")
    with open(os.path.join(own, "plan"), "w", encoding="utf-8") as f:
        f.write("the creature's work\n")
    cousin = runmod.PathBody(os.path.join(d, "cousin"))

    check("boundary: a body that confines nothing says so about itself, "
          "rather than leaving callers to know",
          bodymod.LocalBody.CONTAINED is False)
    check("boundary: and a container says the opposite",
          bodymod.DockerBody.CONTAINED is True)

    # The escape, from the cousin's body into the creature's tools. Only
    # meaningful where a shell actually runs; on a box whose bash is broken
    # the refusal below is still the assertion that matters.
    cousin.run('echo pwned > "%s/plan"' % own.replace("\\", "/"))
    with open(os.path.join(own, "plan"), encoding="utf-8") as f:
        got = f.read()
    # NEVER A BARE `True` INSIDE AN `if`. This used to be exactly that, so if
    # `LocalBody` ever stopped being breachable the assertion would DISAPPEAR
    # from the run rather than report -- the test going quieter, not redder,
    # about its own premise. A verifier found it. Now the premise is asserted
    # when it can be tested and stated when it cannot, and nothing vanishes.
    if cousin.responds():
        check("boundary: an unconfined body really can reach the creature's "
              "tools, so the copy alone is NOT the boundary",
              "pwned" in got, got[:80])
    else:
        check("boundary: the escape could not be attempted -- this body does "
              "not run commands here, so the refusal below carries the whole "
              "assertion", True, "body does not respond")

    # SO THE DEPLOYMENT REFUSES IT -- asked of the body, not of the flag.
    rc = runmod.main(["--cycles", "1", "--root", os.path.join(d, "live"),
                      "--cousin-shell", "--body", "local",
                      "--rungs", os.path.join(d, "no-such-rungs.json")])
    check("boundary: a cousin shell in a body that confines nothing is "
          "REFUSED, not documented as risky", rc == 3, rc)
    creature.destroy(); cousin.destroy()
    shutil.rmtree(d, ignore_errors=True)


def test_a_probe_that_ran_and_lost_its_verdict_is_finished_not_discarded():
    """PLAN item 18.7. A visit costs TWO model calls -- what to type, then
    what you think -- and on a dry free tier the second is the one that finds
    nothing. Measured 2026-09-19: **69 probes produced 12 verdicts**, with 45
    visits deferred. Twice the cousin composed `lib-deps plan` with its own
    stated reason, got exactly the fact it asked for, and had it thrown away.

    A deferred visit RE-RAISES, so its trigger is never cleared and fires
    again. Answering the orphaned probe on the next visit therefore answers
    the SAME question rather than swapping it for another, and costs one call
    instead of two.

    Nothing is queued: the orphan is derived from the journal, the rule the
    manager's whole state follows.
    """
    e, j, b, d = build_engine(["thinking"], [])
    own = os.path.join(b.mind, "tools", "own")
    _write_tool(own, "plan", does="keeps the plan", call="plan list")

    check("orphan: a journal with no probes has nothing to finish",
          e.orphan_probe() is None)

    j.append("cousin_probe", tool="plan", exit_code=1, bare=False,
             picked_by="ran", cmd="plan list", stdout="Usage: plan <cmd>",
             stderr="")
    o = e.orphan_probe()
    check("orphan: a probe that RAN and got no verdict is unfinished work",
          o is not None and o.get("tool") == "plan", o)

    j.append("cousin_verdict", verdict="ACCEPTED", tool="plan")
    check("orphan: once it has been judged there is nothing to finish",
          e.orphan_probe() is None)

    # A probe the ladder never reached has no experience to judge: exit_code
    # is None, and asking for a verdict on it would be asking the cousin to
    # judge a run that never happened -- §2.5, with the framework as author.
    j.append("cousin_probe", tool="plan", exit_code=None, bare=False,
             chosen_by="ladder_dry", cmd=None, stdout="", stderr="")
    check("orphan: a probe that never reached the tool is NOT unfinished "
          "work -- there is no experience to judge",
          e.orphan_probe() is None)

    # STALE IS DROPPED, not judged late. The library moves; a verdict about a
    # tool as it was six hours ago is testimony about a world that is gone.
    j.append("cousin_probe", tool="plan", exit_code=0, bare=False,
             cmd="plan list", stdout="ok", stderr="")
    rows = j.read(kinds=["cousin_probe"])
    check("orphan: a fresh one is picked up",
          e.orphan_probe() is not None)
    old_now = float(rows[-1]["ts"]) + e.ORPHAN_MAX_AGE_S + 60
    check("orphan: and an old one is dropped rather than judged late",
          e.orphan_probe(now=old_now) is None)

    # WHAT THE COUSIN IS SHOWN. Rebuilt from the journal, never re-run: the
    # experience being judged is the one that happened.
    claim, header, transcript, library = e.replay_evidence(
        j.read(kinds=["cousin_probe"])[-1])
    check("orphan: the transcript is the output it actually got",
          "$ plan list" in transcript and "exit 0" in transcript
          and "ok" in transcript, transcript[:200])
    check("orphan: and it is TOLD the run is not fresh, so a stale transcript "
          "cannot read as a live one",
          "ago" in transcript and "Nothing was re-run" in transcript,
          transcript[:200])
    check("orphan: it still gets the tool's own header and the library",
          "keeps the plan" in (header + library), (header[:80], library[:80]))
    check("orphan: and the claim names the tool", "plan" in claim, claim)
    # BOUNDED, or a dry spell starves the thing this was meant to feed.
    e2, j2, b2, d2 = build_engine(["thinking"], [])
    _write_tool(os.path.join(b2.mind, "tools", "own"), "plan",
                does="keeps the plan", call="plan list")
    j2.append("cousin_probe", tool="plan", exit_code=1, bare=False,
              cmd="plan list", stdout="Usage", stderr="")
    pts = float(j2.read(kinds=["cousin_probe"])[-1]["ts"])
    for i in range(e2.ORPHAN_MAX_TRIES - 1):
        check("orphan: still offered after %d attempt(s)" % i,
              e2.orphan_probe() is not None)
        j2.append("verdict_recovered", tool="plan", probe_ts=pts)
    check("orphan: offered on the last permitted attempt",
          e2.orphan_probe() is not None)
    j2.append("verdict_recovered", tool="plan", probe_ts=pts)
    check("orphan: and LET GO after that, so a long dry spell cannot keep the "
          "cousin from everything the creature built in the meantime",
          e2.orphan_probe() is None)
    b2.destroy(); shutil.rmtree(d2, ignore_errors=True)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_tool_the_creature_runs_every_cycle_stops_absorbing_every_visit():
    """PLAN item 18.6. `ran` is the right REASON -- a done-claim is about
    something the creature just ran -- and it was still a magnet, because the
    creature runs `plan` on most cycles and the rule took the most recent
    name. Measured over the first shell window: **54 of 88 probes chosen by
    `ran`**, `probe_stuck` firing on 5 of 8 visits to `plan`, and firing again
    on 2026-09-19 and 2026-09-20, which is the trigger this item named for
    itself.

    Same shape as the alphabetical fallback §5 records: not a wrong reason, a
    reason that always returns the same answer. The fix keeps the reason and
    changes which of several it picks -- the one its user knows least about,
    ties by recency, so the visit still concerns what just ran.
    """
    e, j, b, d = build_engine(["thinking"], [])
    own = os.path.join(b.mind, "tools", "own")
    for n in ("plan", "archive-graph-path"):
        _write_tool(own, n, does="does %s" % n, call="%s x" % n)
    tools = ["plan", "archive-graph-path"]

    # Its user has run `plan` many times with arguments it chose, and has
    # never once reached the other.
    for i in range(9):
        j.append("cousin_probe", tool="plan", exit_code=1, bare=False,
                 picked_by="ran", stdout="", stderr="")

    # One cycle, both tools invoked, `plan` last -- which is the live shape.
    executed = [("archive-graph-path 3", 0), ("plan list", 0)]
    name, how = e.choose_target(executed, tools, tools)
    check("magnet: the reason is still `ran`, because the visit IS about what "
          "the creature just ran", how == "ran", (name, how))
    check("magnet: but it goes to the one its user knows least about, not the "
          "hub it touches every cycle",
          name == "archive-graph-path", (name, how))

    # RECENCY STILL DECIDES when there is nothing to choose between them --
    # otherwise this would have swapped one fixed answer for another.
    e2, j2, b2, d2 = build_engine(["thinking"], [])
    own2 = os.path.join(b2.mind, "tools", "own")
    for n in ("alpha", "omega"):
        _write_tool(own2, n, does="does %s" % n, call="%s x" % n)
    both = ["alpha", "omega"]
    n2, h2 = e2.choose_target([("alpha 1", 0), ("omega 2", 0)], both, both)
    check("magnet: with nothing known about either, the most recent wins",
          (n2, h2) == ("omega", "ran"), (n2, h2))
    n3, h3 = e2.choose_target([("omega 2", 0), ("alpha 1", 0)], both, both)
    check("magnet: and it really is recency, not a name order",
          (n3, h3) == ("alpha", "ran"), (n3, h3))

    # A SINGLE tool it ran is still that tool -- no cleverness where there is
    # no choice to make.
    n4, h4 = e2.choose_target([("alpha 1", 0)], both, both)
    check("magnet: one tool run means one tool probed", (n4, h4) == ("alpha", "ran"),
          (n4, h4))
    b.destroy(); b2.destroy()
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(d2, ignore_errors=True)


def test_a_regression_that_takes_a_day_to_arrive_is_still_caught():
    """PLAN item 21.3. On 2026-09-17 the read caps were raised, the creature
    began rewriting whole tools, and `truncated|lost` went from 1% of thinks
    to 32% in a day and 53% by the third. `deploy_regression` compared the
    hour after against the hour before and reported *no correctness indicator
    crossed its floor* -- **truthfully**, because in that first hour nothing
    had. The cost needed the creature's next big edit to arrive.

    So the hour is not wrong, it is short. This is the same table and the same
    floors with a longer wait, registered as its own finding so the page and
    `alarms.jsonl` can carry both.
    """
    from monitor import detectors as det
    HOUR, DAY = 3600.0, 86400.0
    t0 = 1789000000.0

    def rows_for(lost_share_after, span):
        """A start at t0, `span` either side, clean before and `lost_share`
        of thinks losing their command after."""
        rows = [{"ts": t0 - span - 1, "kind": "engine_start", "engine": "old1234"}]
        n = 40
        for i in range(n):                      # the span BEFORE: all clean
            ts = t0 - span + (i + 1) * (span / (n + 2))
            rows += [{"ts": ts, "kind": "wake"},
                     {"ts": ts + 1, "kind": "think", "finish": "stop",
                      "rung": "r", "chars": 100},
                     {"ts": ts + 2, "kind": "exec_start", "cmd": "echo hi"},
                     {"ts": ts + 3, "kind": "exec_end", "exit_code": 0,
                      "stdout": "hi", "stderr": ""}]
        rows.append({"ts": t0, "kind": "engine_start", "engine": "new5678"})
        for i in range(n):                      # the span AFTER
            ts = t0 + (i + 1) * (span / (n + 2))
            rows += [{"ts": ts, "kind": "wake"},
                     {"ts": ts + 1, "kind": "think", "finish": "length",
                      "rung": "r", "chars": 8400}]
            if i < int(n * lost_share_after):
                rows.append({"ts": ts + 2, "kind": "exec_skip",
                             "why": "truncated", "lost": True})
            else:
                rows += [{"ts": ts + 2, "kind": "exec_start", "cmd": "echo hi"},
                         {"ts": ts + 3, "kind": "exec_end", "exit_code": 0,
                          "stdout": "hi", "stderr": ""}]
        return rows

    check("day: the detector exists and is registered, or the page never says it",
          callable(getattr(det, "deploy_regression_day", None))
          and getattr(det, "deploy_regression_day", None) in det.ALL)
    if not callable(getattr(det, "deploy_regression_day", None)):
        return

    # THE REAL SHAPE: nothing wrong in the first hour, half the commands gone
    # by the end of the day. The hour must stay quiet and the day must fire.
    day_rows = rows_for(0.5, DAY)
    quiet_hour = [r for r in day_rows
                  if abs(r["ts"] - t0) <= HOUR or r.get("kind") == "engine_start"]
    ctx_hour = det.Context(quiet_hour, now=t0 + HOUR + 60)
    ctx_day = det.Context(day_rows, now=t0 + DAY + 60)
    hour = det.deploy_regression(ctx_hour)
    day = det.deploy_regression_day(ctx_day)
    check("day: the DAY-long reading catches a regression that took a day to "
          "arrive", day.state == det.ALARM, (day.state, day.msg[:140]))
    check("day: and it names the lost-command share, which is what moved",
          "lost-command" in day.msg, day.msg[:200])
    check("day: it says which engine against which",
          "new5678" in day.msg and "old1234" in day.msg, day.msg[:120])

    # NOT A HAIR TRIGGER: a day that did not get worse says so.
    calm = det.deploy_regression_day(det.Context(rows_for(0.0, DAY), now=t0 + DAY + 60))
    check("day: a day where nothing crossed a floor is INFO, not an alarm",
          calm.state == det.INFO, (calm.state, calm.msg[:120]))

    # PENDING, not silent: before the day is up it says when it will answer.
    early = det.deploy_regression_day(det.Context(rows_for(0.5, DAY), now=t0 + HOUR))
    check("day: before the day has passed it is PENDING and says when",
          early.state == det.INFO and "compared against" in early.msg,
          (early.state, early.msg[:140]))

    # AND THE HOUR IS UNTOUCHED -- both are kept, neither substitutes.
    check("day: the hourly reading still exists and still answers",
          hour.state in (det.INFO, det.ALARM, det.CANNOT_TELL),
          (hour.state, hour.msg[:120]))


def test_the_body_runs_the_bash_it_means_and_not_windows_wsl_launcher():
    """PLAN item 18.8. The Windows gate stopped meaning anything on
    2026-09-17: 92 failures, twice, identical by name, every one a cascade
    from `LocalBody` spawning a bare `"bash"`. `subprocess` resolves that
    through CreateProcess, which searches `System32` BEFORE `PATH`, and
    `System32\\bash.exe` is the **WSL launcher** -- a different kernel with a
    different filesystem, handed a Windows `cwd` and a relative script name.

    This is the relative-root scar in a new costume: the body reports healthy
    while nothing it runs can see the world it was pointed at. The invariant
    is the same one -- **the body resolves the interpreter it promises, and
    says which one answered rather than leaving it to a search order nobody
    chose.**

    The POLICY is tested against a synthetic list rather than this machine's
    PATH, because a test that only passes on the box it was written on tells
    the next box nothing.
    """
    check("bash: the body has a stated policy for choosing its interpreter",
          callable(getattr(bodymod, "usable_bash", None))
          and callable(getattr(bodymod, "find_bash", None)))
    if not callable(getattr(bodymod, "usable_bash", None)):
        return
    win = "C:\\Windows\\System32\\bash.exe"
    git = "C:\\Program Files\\Git\\bin\\bash.exe"
    check("bash: the WSL launcher is refused even when it is first on PATH",
          bodymod.usable_bash([win, git]) == git, bodymod.usable_bash([win, git]))
    check("bash: and refused when it is the ONLY thing on PATH -- a body that "
          "cannot keep its promise says so rather than running a different "
          "kernel", bodymod.usable_bash([win]) is None, bodymod.usable_bash([win]))
    check("bash: SysWOW64 is the same trap",
          bodymod.usable_bash(["C:\\Windows\\SysWOW64\\bash.exe"]) is None)
    check("bash: a normal posix path is taken as-is",
          bodymod.usable_bash(["/bin/bash"]) == "/bin/bash")
    check("bash: empty and missing entries do not crash the policy",
          bodymod.usable_bash([None, "", git]) == git)

    # AND IT IS WHAT ACTUALLY RUNS. Resolving it and then not using it is the
    # `--body docker` scar: present in the code, absent from the running thing.
    found = bodymod.find_bash()
    check("bash: this machine has one the body will admit to", bool(found), found)
    if found:
        check("bash: and it is not the launcher", "system32" not in found.lower())
        d = tmpdir()
        b = bodymod.LocalBody(os.path.join(d, "body"))
        r = b.run("echo alive && [[ 1 == 1 ]] && echo bashism-ok")
        check("bash: the body runs a real bash -- `[[` is not POSIX sh, so this "
              "fails on dash and on a launcher that cannot see the script",
              r.code == 0 and "alive" in r.stdout and "bashism-ok" in r.stdout,
              (r.code, r.stdout[:120], r.stderr[:160]))
        check("bash: and the body will say which binary it used, so a wrong "
              "one is findable rather than inferred",
              getattr(b, "shell_path", None) == found,
              (getattr(b, "shell_path", None), found))
        b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_headline_metric_can_actually_be_computed():
    """PLAN item 20.2. `ARCHITECTURE.md` \u00a712 names what this project
    measures before anything else: *tools that start, are invoked by something
    else, and are still invoked a week later*, glossed as **surviving useful
    capability -- the thing the goal actually names**. It was written
    2026-09-10 and **has never once been computable here**, because the cousin
    got a wiped world and one nominated tool per visit.

    Three bars, and each has to be able to say CANNOT TELL:

    - **starts** -- the journal records the body running it. A probe that only
      ever exited 127 did not start; a tool the cousin never reached says
      nothing either way, and must not be counted as failing.
    - **invoked by something else** -- another tool names it in its source.
      That is composition, which is what the creature's own prompt asks for:
      *the toolkit is most alive when its LATER tools are built OUT OF its
      earlier ones*.
    - **still invoked a week later** -- its user reached for it again after the
      window. Before the window has elapsed the honest answer is NOT ZERO, it
      is *not yet*, and a metric that reports 0 while the run is four days old
      is the 2026-09-14 scar wearing a new hat.

    The edge scan is bounded and single-pass. The parent's version of this ran
    187,489 full-content regex scans per wake, took 28 seconds, got worse every
    time the creature succeeded, and was found because a human could hear the
    laptop fan.
    """
    from monitor import derive
    check("metric: the derivation exists at all",
          callable(getattr(derive, "surviving_capability", None)))
    if not callable(getattr(derive, "surviving_capability", None)):
        return
    d = tmpdir()
    own = os.path.join(d, "tools", "own")
    os.makedirs(own)

    def tool(name, text):
        with io.open(os.path.join(own, name), "w", encoding="utf-8") as f:
            f.write(text)

    tool("alpha", "#!/bin/sh\n# does: a\nbeta --go\n")
    tool("beta", "#!/bin/sh\n# does: b\necho b\n")
    tool("orphan", "#!/bin/sh\n# does: nobody names me\necho o\n")
    tool("deadstart", "#!/bin/sh\n# does: never starts\necho d\n")
    tool("nevertried", "#!/bin/sh\n# does: the cousin never reached it\necho n\n")

    T0, DAY = 1000000000.0, 86400.0

    def probe(name, ts, code):
        return {"ts": ts, "kind": "cousin_probe", "tool": name, "exit_code": code}

    rows = [{"ts": T0, "kind": "loop_start"},
            probe("beta", T0, 0), probe("beta", T0 + 8 * DAY, 0),
            probe("alpha", T0, 0),
            probe("orphan", T0, 0), probe("orphan", T0 + 8 * DAY, 0),
            probe("deadstart", T0, 127),
            {"ts": T0 + 10 * DAY, "kind": "wake"}]
    got = derive.surviving_capability(rows, own, now=T0 + 10 * DAY)
    by = {t["tool"]: t for t in got["tools"]}
    check("metric: every tool in the directory gets a row",
          sorted(by) == ["alpha", "beta", "deadstart", "nevertried", "orphan"],
          sorted(by))
    check("metric: a tool that starts and whose USER reached for it again "
          "after the window SURVIVES -- the one thing the goal names",
          by["beta"]["surviving"] is True, by["beta"])
    check("metric: composition is reported beside it, as context",
          by["beta"]["named_by"] == 1, by["beta"])
    # THE MIDDLE BAR IS NOT COMPOSITION, and getting this wrong would have
    # shipped a metric that fails every leaf tool its user depends on daily.
    # \u00a74: a single-occupancy fault survives *because the author is the
    # sole user*. A tool called by another of the author's own tools is still
    # single-occupancy -- the author wrote both -- so a wrapper stack does not
    # make a second party, and `orphan` survives on its user's repeat use.
    check("metric: a tool no other tool names still survives if its USER kept "
          "coming back -- composition is not a second party",
          by["orphan"]["surviving"] is True and by["orphan"]["named_by"] == 0,
          by["orphan"])
    check("metric: a tool whose only run exited 127 did not start",
          by["deadstart"]["started"] is False, by["deadstart"])
    check("metric: a tool the cousin never reached is CANNOT TELL, never a "
          "failure -- the harness's empty hands are not the tool's fault",
          by["nevertried"]["surviving"] is None
          and by["nevertried"]["started"] is None, by["nevertried"])
    check("metric: a tool last reached more than a window ago has not survived",
          by["alpha"]["surviving"] is False, by["alpha"])
    check("metric: and the leading indicators are there, so the page says "
          "something true before the window has elapsed",
          got["reused"] == 2 and got["widest_span_days"] >= 8.0,
          (got["reused"], got["widest_span_days"]))
    check("metric: the three states account for every tool",
          got["surviving"] + got["not_surviving"] + got["cannot_tell"]
          == len(got["tools"]),
          (got["surviving"], got["not_surviving"], got["cannot_tell"]))

    # THE YOUNG RUN. Before the window has elapsed the answer is *not yet*.
    young = [{"ts": T0, "kind": "loop_start"}, probe("beta", T0, 0),
             probe("alpha", T0, 0), {"ts": T0 + 3 * DAY, "kind": "wake"}]
    y = derive.surviving_capability(young, own, now=T0 + 3 * DAY)
    yby = {t["tool"]: t for t in y["tools"]}
    check("metric: inside the window nothing is called failed -- 'not yet' and "
          "'no' are different answers and this page has paid for conflating "
          "them", yby["beta"]["surviving"] is None, yby["beta"])
    check("metric: and it SAYS why, with the run's age in it",
          "3.0" in (y.get("why_cannot_tell") or "")
          and "7" in (y.get("why_cannot_tell") or ""), y.get("why_cannot_tell"))

    # BOUNDED. The parent's dependency scan went quadratic and cost 28s a wake.
    check("metric: the edge scan declares a ceiling rather than growing "
          "without one", isinstance(getattr(derive, "EDGE_SCAN_MAX", None), int))
    big = os.path.join(d, "big")
    os.makedirs(big)
    for i in range(derive.EDGE_SCAN_MAX + 1):
        with io.open(os.path.join(big, "t%04d" % i), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho %d\n" % i)
    over = derive.surviving_capability(rows, big, now=T0 + 10 * DAY)
    check("metric: over the ceiling it refuses to scan and says so, rather "
          "than quietly costing the monitor a minute",
          over["edges"] is None and "ceiling" in (over.get("why_cannot_tell") or "").lower(),
          over.get("why_cannot_tell"))
    check("metric: and with no library to read, every tool is CANNOT TELL "
          "rather than absent", over["cannot_tell"] == len(over["tools"]),
          (over["cannot_tell"], len(over["tools"])))

    # IT REACHES THE PAGE, or it is a derivation nobody reads -- the dead
    # `want` channel is this file's scar for exactly that.
    from monitor import status as statusmod
    check("metric: the page has a renderer for it, or it is a derivation "
          "nobody reads -- the dead `want` channel is this file's scar for "
          "exactly that",
          callable(getattr(statusmod, "render_surviving", None)))
    if callable(getattr(statusmod, "render_surviving", None)):
        NL = chr(10)
        md = NL.join(statusmod.render_surviving(got))
        check("metric: the section names the metric and its source",
              "surviving" in md.lower() and "12" in md, md[:300])
        check("metric: it prints the tools that cleared all three bars",
              "beta" in md, md[:400])
        check("metric: and it states what it cannot tell, every render",
              "cannot tell" in md.lower(), md[-400:])
        y_md = NL.join(statusmod.render_surviving(y))
        check("metric: on a young run the section says NOT YET rather than a "
              "zero that reads as a finding",
              "3.0" in y_md and "0 survived" not in y_md.lower(), y_md[:400])
    shutil.rmtree(d, ignore_errors=True)


def test_the_cousin_has_the_instruments_the_architecture_specified():
    """PLAN item 20.3, from `ARCHITECTURE.md` \u00a75: *a handful of small
    deterministic scripts -- startability, hollow-stub detection,
    duplicate-stem listing, dependency edges, store parse rates... they are
    tools, they live where tools live, and the cousin runs one when it wants to
    know something.* Specified 2026-09-10 and never built until 2026-09-18,
    found by Tue sending me back to the founding documents.

    **This is item 16's answer, and it is a script rather than a rule.** Tue
    asked that noticing a tool which serves nothing should rest with the
    cousin. The architecture had already said how: give it the instrument and
    let it look. A brief rule telling a judge to have an opinion about
    usefulness, with no way to gather the fact, is how the 2026-09-12 scar
    happened -- a judgement that requires a comparison gets made anyway when
    you show one side.

    **The creature must never get these** (\u00a72.4: never tell the creature
    about its own bugs). A hollow-stub detector aimed at its own library is
    precisely that, and the diagnosis is its work and its growth.

    **Each one must say what it did NOT check.** A detector has three states,
    never two; an instrument that reports a count with no honest qualifier is
    the display that counted usage refusals as failures.
    """
    import subprocess
    import run as runmod
    root = _repo_root()
    d = tmpdir()
    instr = os.path.join(root, "instruments")
    want = ["lib-deps", "lib-startable", "lib-stores", "lib-stubs", "lib-twins"]
    have = sorted(os.listdir(instr)) if os.path.isdir(instr) else []
    check("instruments: all five the architecture names exist",
          [n for n in want if n in have] == want, have)
    if [n for n in want if n in have] != want:
        shutil.rmtree(d, ignore_errors=True)
        return

    # A world with one planted fault of each kind.
    mind = os.path.join(d, "mind")
    own = os.path.join(mind, "tools", "own")
    data = os.path.join(mind, "data")
    os.makedirs(own); os.makedirs(data)

    def tool(name, text):
        with io.open(os.path.join(own, name), "w", encoding="utf-8") as f:
            f.write(text)

    tool("plan", "#!/usr/bin/env python3\n# does: keeps the plan\nprint('ok')\n")
    tool("plan-list", "#!/usr/bin/env python3\n# does: lists it\n"
                      "import subprocess\nsubprocess.run(['plan'])\n")
    tool("plan-broken", "#!/usr/bin/env python3\n# does: broken\ndef f(:\n")
    tool("noshebang", "# does: has no shebang\necho hi\n")
    tool("hollow", "#!/usr/bin/env python3\n# does: nothing yet\n"
                   "# not written yet\npass\n")
    tool("lonely", "#!/usr/bin/env python3\n# does: calls nobody\nprint(1)\n")
    with io.open(os.path.join(data, "archive.json"), "w", encoding="utf-8") as f:
        f.write('{"entries": [1, 2]}')
    with io.open(os.path.join(data, "torn.jsonl"), "w", encoding="utf-8") as f:
        f.write('{"a": 1}\nNOT JSON AT ALL\n{"a": 2}\n')

    before = _digest_dir(mind)
    env = dict(os.environ, MIND=mind)
    out = {}
    for n in want:
        r = subprocess.run([sys.executable, os.path.join(instr, n)],
                           capture_output=True, text=True, timeout=60, env=env)
        out[n] = r.stdout
        check("instruments: %s runs and exits 0" % n, r.returncode == 0,
              (r.returncode, (r.stderr or "")[:200]))

    check("instruments: startable names the tool that cannot parse",
          "plan-broken" in out["lib-startable"], out["lib-startable"][:300])
    check("instruments: startable names the tool with no shebang, which the "
          "shell cannot run whatever is inside it",
          "noshebang" in out["lib-startable"], out["lib-startable"][:300])
    check("instruments: startable does not accuse the tools that are fine",
          "WILL NOT START" not in out["lib-startable"].replace(
              "WILL NOT START", "", 2), out["lib-startable"][:300])
    check("instruments: stubs finds the hollow one",
          "hollow" in out["lib-stubs"], out["lib-stubs"][:300])
    check("instruments: twins groups the family and says who wraps whom",
          "plan-*" in out["lib-twins"] and "wraps" in out["lib-twins"],
          out["lib-twins"][:400])
    check("instruments: deps finds the tool nothing calls",
          "lonely" in out["lib-deps"], out["lib-deps"][:400])
    check("instruments: deps answers for ONE tool, which is the question "
          "before you judge it -- if this breaks, what else stops",
          "plan-list" in subprocess.run(
              [sys.executable, os.path.join(instr, "lib-deps"), "plan"],
              capture_output=True, text=True, timeout=60, env=env).stdout)
    check("instruments: stores reports the torn store as 2 of 3",
          "2/3" in out["lib-stores"], out["lib-stores"][:400])
    check("instruments: and does not call the intact one torn",
          "archive.json" in out["lib-stores"] and
          "DOES NOT PARSE" not in out["lib-stores"], out["lib-stores"][:400])

    # THREE STATES, NEVER TWO: each must say what it did not check.
    for n, phrase in (("lib-startable", "nothing was executed"),
                      ("lib-stubs", "NOT A VERDICT"),
                      ("lib-twins", "NOT DUPLICATION"),
                      ("lib-deps", "NAMING IS NOT CALLING"),
                      ("lib-stores", "NOT CORRECTNESS")):
        check("instruments: %s says what it did NOT check" % n,
              phrase in out[n], out[n][-200:])

    check("instruments: and not one of them wrote to the world it read",
          _digest_dir(mind) == before)

    # WHO GETS THEM. The cousin, never the builder.
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    names = runmod.instrument_names()
    cb.bin = runmod.install_hands(cb, only=runmod.USER_HANDS, keep=names)
    runmod.install_instruments(cb)
    got = sorted(os.listdir(os.path.join(cb.root, "bin")))
    check("instruments: the cousin has them", [n for n in want if n in got] == want, got)
    check("instruments: and still has a user's hands, and none of a builder's",
          "recall" in got and "remember" in got and "tool-edit" not in got
          and "tool-new" not in got, got)
    crb = runmod.PathBody(os.path.join(d, "creature-body"))
    runmod.install_hands(crb)
    cgot = sorted(os.listdir(os.path.join(crb.root, "bin")))
    check("instruments: the CREATURE does not -- a stub detector aimed at its "
          "own library is telling it about its own bugs (\u00a72.4)",
          not [n for n in want if n in cgot], cgot)
    shutil.rmtree(d, ignore_errors=True)


def test_the_cousin_gets_the_creatures_work_and_never_its_notes():
    """PLAN item 20.1, and it is the premise of the whole design.

    `MANAGER-PROMPT.md`: *"You are the person who needs its work and wasn't
    there when it was made."* Measured on the live deployment 2026-09-18,
    that was false. `sync_cousin_world` mirrors the creature's WHOLE mind,
    and the mind holds `state/memory.json` -- the author's own notes. The
    cousin's copy was byte-identical to the creature's, 25 keys, reading
    `archive-graph-clusters-done true`, `compare-subtask-logs-baseline-verified
    true`, `list-subtasks-verified = true`, `current-phase done`. The judge was
    holding the builder's answer key, and `recall` with no argument prints all
    of it: the cousin ran exactly that in two live probes.

    This is the 2026-09-10 trial scar in the production loop -- *the brief had
    been handing every judge the answer to that case*, retracted then as "not a
    measurement". A verdict taken while the author's "verified: true" is on the
    page is not a handover test either.

    **The invariant: the cousin is handed the creature's WORK, never its
    NOTES.** Tools and data are what a user receives. Memory is the author's
    head. The `.cmd-*` exclusion already had the instinct and stopped at the
    transcript; this is the notebook.

    **Not a regression of the 2026-09-16 scar** that put the whole mind in the
    copy. That fault was `recall` MISSING, so tools died `command not found`
    for a reason that was ours. The hand is still there and still works; its
    store is the cousin's own. A tool that only works because the author's
    memory holds a value is a single-occupancy fault, which is the exact class
    the second inhabitant exists to catch -- an empty store is the true
    condition of a stranger, not a broken world.

    **And the same file is the continuity fix.** The creature is told its user
    "wakes with no idea what changed while it slept" and "has no good way to
    plan across cycles", so four of the five starter-map categories are built
    for an agent with a memory. The cousin had none: its world was remade every
    visit and its `remember` wrote into the copy we discard. It asked for
    deadlines four times because it had no tomorrow to spend one in.
    """
    e, j, b, d = build_engine(["```bash\necho hi\n```"], [])
    import run as runmod
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.cousin_body = cb
    st = os.path.join(b.mind, "state")
    os.makedirs(st, exist_ok=True)
    notes = {"archive-graph-done": "true", "current-phase": "done",
             "how-plan-works": "pass --keyword to filter"}
    with io.open(os.path.join(st, "memory.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(notes))
    os.makedirs(os.path.join(b.mind, "data"), exist_ok=True)
    with io.open(os.path.join(b.mind, "data", "archive.json"), "w",
                 encoding="utf-8") as f:
        f.write('{"entries": [1]}')
    e.sync_cousin_world()
    cmem = os.path.join(cb.mind, "state", "memory.json")
    try:
        with io.open(cmem, encoding="utf-8") as f:
            got = json.load(f)
    except Exception:
        got = {}
    check("notes: the cousin IS handed the creature's work -- its data is "
          "there, or a tool fails for a reason that is ours",
          os.path.exists(os.path.join(cb.mind, "data", "archive.json")))
    check("notes: and is NOT handed the creature's notes -- a judge holding "
          "the author's 'verified: true' is not testing a handover",
          "archive-graph-done" not in got and "how-plan-works" not in got,
          sorted(got))
    check("notes: the framework has a way to keep what the cousin learned",
          callable(getattr(e, "harvest_cousin_memory", None)))
    if callable(getattr(e, "harvest_cousin_memory", None)):
        with io.open(cmem, "w", encoding="utf-8") as f:
            f.write(json.dumps({"tried-plan-bare":
                                "got the usage menu; try plan set-deadline"}))
        e.harvest_cousin_memory()
        e.sync_cousin_world()
        try:
            with io.open(cmem, encoding="utf-8") as f:
                got2 = json.load(f)
        except Exception:
            got2 = {}
        check("notes: what the cousin learned on one visit is there on the "
              "next -- it judges a builder it is told wakes and forgets, and "
              "until now the cousin was the one with no yesterday",
              got2.get("tried-plan-bare", "").startswith("got the usage menu"),
              sorted(got2))
        check("notes: and it still does not receive the notes on a later "
              "visit either", "archive-graph-done" not in got2, sorted(got2))
    with io.open(os.path.join(st, "memory.json"), encoding="utf-8") as f:
        cre = json.load(f)
    check("notes: the creature's own memory is untouched by any of it -- "
          "\u00a72.3 is unchanged and this buys continuity without buying a "
          "write path", cre == notes, sorted(cre))
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_nothing_the_cousin_runs_can_change_the_creatures_tools():
    """PLAN item 9.4, and §2.3: the manager is the second USER, never a second
    builder. With a shell it could write into `tools/own` -- a path into the
    creature's world without touching a file, which is the thing the parent
    project examined and rejected.

    **Structurally, not by a guard.** A guard keyed on a command pattern is
    the literal-hunting scar, and the input is bash written by a third-party
    model; it would be beaten by `>>`, by `tee`, by python, by a variable.
    The cousin instead never has the creature's files at all -- only a copy,
    remade before every visit, discarded with whatever it did to it.

    **The attack deliberately does NOT begin with `rm`.** The first version
    did, and an independent verifier showed that a SYMLINKED world passed it
    unchanged: `rm` removed the link instead of following it, so the test
    asserted a boundary whose loss it could not detect. A redirect straight
    through is what a shared or linked world would actually allow.

    **The digest is taken BEFORE the attack, and that cost a second cycle.**
    A verifier found the third version taking `before` and `after` on the
    same side of the visit -- both after `run_cycle()` -- so `before ==
    after` was true by construction and stayed green while the cousin's
    world was a SYMLINK to the creature's. It was proven dead by making
    exactly that breach and watching the assertion pass. The visit cannot
    simply be moved, because the write that summons it is the creature's
    own; so cycle one builds the tool and cycle two summons the cousin with
    a DONE_CLAIM, which touches no file. Now the only thing that can change
    `tools/own` between the two digests is the cousin.
    """
    hostile = "```bash\necho pwned > tools/own/plan && echo done\n```"
    benign = "```bash\nplan list\n```"
    done_claim = "```bash\nremember current-phase done\n```"
    e, j, b, d = build_engine(
        ["```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n# does: keeps the "
         "plan\\n# call: plan list\\necho REAL\\n' > tools/own/plan && chmod "
         "+x tools/own/plan\n```",
         done_claim],
        [benign, ACCEPT_REPLY, hostile, ACCEPT_REPLY])
    import run as runmod
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.cousin_body = cb
    own = os.path.join(b.mind, "tools", "own")
    # Cycle 1: the creature builds `plan`; its visit runs something harmless.
    e.run_cycle()
    before = _digest_dir(own)
    check("boundary: the creature's tool exists to be attacked",
          "plan" in before, sorted(before))
    # Cycle 2: a DONE_CLAIM summons the cousin without the creature writing
    # anything, so every byte that differs below is the cousin's doing.
    e.run_cycle()
    probe = (j.read(kinds=["cousin_probe"]) or [{}])[-1]
    check("boundary: the cousin's chosen command really ran",
          "done" in (probe.get("stdout") or ""), probe)
    after = _digest_dir(own)
    check("boundary: and the creature's tools are BYTE-IDENTICAL afterwards",
          before == after, "%s != %s" % (before, after))
    with open(os.path.join(own, "plan"), encoding="utf-8") as f:
        body_text = f.read()
    check("boundary: the file is the creature's, not the cousin's",
          "pwned" not in body_text, body_text[:120])
    # And the damage really happened -- to the copy, which is the point.
    copy = os.path.join(cb.mind, "tools", "own", "plan")
    check("boundary: the cousin's own copy WAS changed, so the attack was "
          "real and simply landed nowhere that matters",
          os.path.exists(copy)
          and "pwned" in io.open(copy, encoding="utf-8").read(),
          io.open(copy, encoding="utf-8").read()[:80] if os.path.exists(copy)
          else "(no copy)")
    b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_a_probe_the_ladder_never_answered_is_recorded_and_never_a_failure():
    """PLAN item 9, and the measurement it is supposed to produce.

    Item 9 made the cousin choose its own invocation, which turned the probe
    into a MODEL call. On a dry free tier that call raises -- and until
    2026-09-16 the exception left `evidence()` before anything was journalled,
    so the entire probe vanished. Found by a verifier reading the live journal,
    not by this suite: the cousin's world was copied at 02:02:08 with 49 tools
    in it, and the journal for that second holds the trigger, five
    `rung_declined`, and no `cousin_probe` at all.

    **Two faults, and the second is the expensive one.** The probe is lost, and
    the loss is INVISIBLE -- so the after-window of item 9.5 would under-count
    by however often the tier was dry (most of the time, on free rungs) and the
    shortfall would read as *the cousin probes less now*. The old bare path
    journalled the probe before asking anyone and could not lose one this way,
    so the before and after were not comparable in the worst direction.

    What must hold: the attempt is recorded, and NOTHING counts it as a run or
    a failure. `exit_code=None` is *cannot tell* -- the three-state rule, whose
    absence is the top scar in this file's doctrine. A dry ladder counted as a
    failure is the page telling its reader the creature's floor is broken.
    """
    import kernel.library as librarymod
    import monitor.derive as derivemod
    from kernel import backends

    def dry(_prompt):
        raise backends.LadderExhausted("no rung answered; tried gemini",
                                       all_walled=False)

    e, j, b, d = build_engine(
        ["```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n# does: keeps the "
         "plan\\n# call: plan list\\necho REAL\\n' > tools/own/plan && chmod "
         "+x tools/own/plan\n```"],
        [])
    import run as runmod
    cb = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.cousin_body = cb
    # BOTH, and the invocation one is the one that matters: since
    # 2026-09-16 the command-choosing call goes through its own ladder.
    e.ask_cousin = dry
    e.ask_cousin_invoke = dry
    try:
        e.run_cycle()
    except backends.LadderExhausted:
        pass          # the supervisor's business; the cycle defers as before

    probes = j.read(kinds=["cousin_probe"])
    check("lost probe: the attempt is in the journal at all", len(probes) == 1,
          len(probes))
    p = probes[-1] if probes else {}
    check("lost probe: recorded as reaching nobody",
          p.get("exit_code") is None and p.get("cmd") is None, p)
    check("lost probe: and says WHY, so it is not mistaken for a refusal",
          p.get("chosen_by") == "ladder_dry", p.get("chosen_by"))

    hist = librarymod.use_history(j)
    check("lost probe: the library does not tell either inhabitant their user "
          "ran this", not hist.get("plan", {}).get("runs"), hist)
    line = librarymod.status(hist.get("plan"))
    check("lost probe: so the line still reads NEVER RUN, not failed",
          "NEVER run" in line, line)

    rec = derivemod.probe_record(j.read())
    check("lost probe: the page counts it apart", rec.get("lost") == 1, rec)
    check("lost probe: and NOT as a failure -- a dry free tier is not a "
          "broken tool", rec.get("nonzero") == 0 and rec.get("worked") == 0,
          rec)
    b.destroy(); cb.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_choosing_what_to_run_is_not_judged_by_the_verdict_contract():
    """The cousin's shell never once worked in production, and the gate was
    green for every hour of it.

    Item 9 gave the cousin its own shell by adding a SECOND call -- *what
    would you like to run?* -- whose answer is a bash block. It was asked
    through `ask_cousin`, and that ladder is built with
    `cousin.unusable_reply`, which rejects any reply without a VERDICT block.
    So every model that answered the question correctly was judged unusable,
    each rung was walled in turn, the ladder exhausted, and the probe was
    lost.

    Measured on the live journal 2026-09-16, the fifteen hours after the
    shell went live: **112 probes, 112 of them lost, 0 verdicts, 0 wants** --
    while the creature thought 112 times against the same rungs, and
    `answered but unusable: no-block` appeared 98 times. The loop had been
    open the whole time.

    Two things made it findable at all, and both were built the night before:
    `chosen_by="ladder_dry"` (before that the probes vanished entirely and
    the page showed nothing), and `lost` as its own column beside
    worked/asked/failed. The instrument found the fault in the feature it was
    built to measure.

    **What must hold**: the two questions are judged by their own contracts.
    For a VERDICT, no block is a failure -- the contract requires one. For an
    INVOCATION, no block is an ANSWER, and `choose_invocation` says so: *a
    user who cannot think what to type has told you something about the
    tool.* Only a reply we never heard -- truncated, or all reasoning --
    rejects a rung.
    """
    from kernel import backends, cousin as cousinmod
    PROPOSAL = "I would run it like this:\n```bash\nplan list\n```"

    def rung(_prompt):
        return PROPOSAL, {"model": "m", "done_reason": "stop",
                          "completion_tokens": 20}

    # THE BUG, reproduced: the same reply, through the verdict ladder.
    verdict_ladder = backends.ladder([("a", rung), ("b", rung)],
                                     reject=cousinmod.unusable_reply)
    exhausted = None
    try:
        verdict_ladder("anything")
    except backends.LadderExhausted as e:
        exhausted = e
    check("invoke: a correct invocation reply exhausts the VERDICT ladder -- "
          "this is the fault, reproduced",
          exhausted is not None, "the verdict ladder accepted it")
    check("invoke: and it walls the rungs for answering correctly",
          "unusable" in str(exhausted or ""), str(exhausted)[:120])

    # THE FIX: the invocation's own contract.
    invoke_ladder = backends.ladder([("a", rung), ("b", rung)],
                                    reject=cousinmod.unusable_invocation)
    cmd, _meta = cousinmod.choose_invocation(invoke_ladder, "# call: plan list")
    check("invoke: through its own ladder the cousin's command arrives",
          cmd == "plan list", cmd)

    # NO BLOCK IS AN ANSWER HERE, and must not wall a rung: the design says a
    # user who cannot think what to type has told you something.
    def mute(_prompt):
        return ("I have read the header and I still do not know what this "
                "tool wants."), {"model": "m", "done_reason": "stop"}
    quiet = backends.ladder([("a", mute)], reject=cousinmod.unusable_invocation)
    # CAUGHT, so this reports rather than crashing the suite: with the
    # verdict's predicate here the ladder exhausts instead of returning, and
    # a red assertion says which of the two it was.
    try:
        cmd2, _m2 = cousinmod.choose_invocation(quiet, "# call: plan list")
        walled = None
    except backends.LadderExhausted as e:
        cmd2, walled = "(rung walled)", e
    check("invoke: proposing nothing is an ANSWER, not a dead rung",
          walled is None and cmd2 is None,
          "the rung was walled for saying it did not know: %s" % walled)
    check("invoke: and the framework substitutes nothing for it",
          cmd2 is None or walled is not None)

    # A REPLY WE NEVER HEARD still rejects, or a truncated rung looks healthy.
    def cut(_prompt):
        return "", {"model": "m", "done_reason": "length",
                    "chars_before_strip": 8000, "chars_stripped": 7900}
    cut_ladder = backends.ladder([("a", cut)], reject=cousinmod.unusable_invocation)
    died = None
    try:
        cut_ladder("anything")
    except backends.LadderExhausted as e:
        died = e
    check("invoke: but a reply that spent its budget and said nothing is "
          "still unusable -- silence we never heard is not an answer",
          died is not None, "a truncated rung was accepted")

    # THE DEPLOYMENT'S OWN WIRING is asserted by DRIVING it, in
    # `test_the_creatures_ladder_really_is_given_the_emptiness_predicate`.
    # What stood here was a grep of `run.py` for two literals -- a guard
    # hunting one literal, in the suite that carries that scar twice -- and a
    # verifier proved it worthless by crossing the two cousin predicates
    # inside `build_ladders` and watching the whole gate stay green.


def test_the_framework_never_invents_the_cousins_command():
    """PLAN item 9.2. When the cousin cannot think what to type, that is a
    fact about the tool and belongs in the transcript. A framework that
    substitutes a command here is answering the question it was asked to
    put -- and would be judging on the creature's behalf."""
    e, j, b, d = build_engine(
        ["```bash\nmkdir -p tools/own && printf '#!/bin/sh\\n# call: plan "
         "<id>\\necho hi\\n' > tools/own/plan && chmod +x tools/own/plan\n```"],
        ["I have no idea how to use this.", ACCEPT_REPLY])
    import run as runmod
    e.cousin_body = runmod.PathBody(os.path.join(d, "cousin-body"))
    e.run_cycle()
    probe = (j.read(kinds=["cousin_probe"]) or [{}])[-1]
    check("no invention: nothing was run in the cousin's name",
          probe.get("cmd") is None, probe.get("cmd"))
    check("no invention: and the record says the cousin proposed nothing",
          probe.get("chosen_by") == "cousin-proposed-nothing",
          probe.get("chosen_by"))
    check("no invention: the call-line was NOT turned into a command",
          "plan <id>" != probe.get("cmd"), probe.get("cmd"))
    e.cousin_body.destroy(); b.destroy(); shutil.rmtree(d, ignore_errors=True)


def test_the_trial_waits_out_a_rate_limit_instead_of_recording_a_failure():
    """PLAN item 8.4. The first held-out baseline collapsed after four cases:
    twelve rows of `FORMAT-FAIL` at 0.0s, which reads exactly like a brief
    that catches nothing. Every one was `HTTP 429`.

    `call_openai` treated 4xx as *ours to fix* and raised at once. But a 429
    is not ours to fix and it is not a fault: the kernel's own
    `classify_error` calls it `NEXT`, and §4 requires the ladder to be
    quota-polite because the tier is shared with the spine. A trial has no
    ladder to fall through to, so the polite move is to WAIT -- and the
    alternative is a results file full of failures the model never made,
    which `run_trial`'s own preflight docstring calls worse than no file.
    """
    import urllib.error
    trial = os.path.join(_repo_root(), "trial")
    if trial not in sys.path:
        sys.path.insert(0, trial)
    import run_trial
    calls = {"n": 0}
    slept = []

    class _Resp:
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"},
                                            "finish_reason": "stop"}],
                               "usage": {"completion_tokens": 1},
                               "model": "m"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(_req, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
        return _Resp()

    real_open, real_sleep = run_trial.urllib.request.urlopen, run_trial.time.sleep
    try:
        run_trial.urllib.request.urlopen = fake_urlopen
        run_trial.time.sleep = lambda s: slept.append(s)
        text, _secs, meta = run_trial.call_openai("m", "hi", "http://x",
                                                  api_key="k", max_tokens=8)
    finally:
        run_trial.urllib.request.urlopen = real_open
        run_trial.time.sleep = real_sleep
    check("trial: a rate limit is waited out, not recorded as a verdict",
          text == "ok" and calls["n"] == 3, (text, calls["n"]))
    check("trial: and it actually waited between attempts rather than "
          "hammering a provider that just refused",
          slept and all(s > 0 for s in slept), slept)
    check("trial: the attempt count is reported, so a rung that needs three "
          "tries every time cannot look healthy",
          meta.get("attempts") == 3, meta.get("attempts"))

    # A REAL client error still raises at once -- waiting cannot fix a bad key.
    def always_401(_req, timeout=None):
        raise urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
    try:
        run_trial.urllib.request.urlopen = always_401
        run_trial.time.sleep = lambda s: None
        try:
            run_trial.call_openai("m", "hi", "http://x", api_key="k")
            raised = False
        except urllib.error.HTTPError:
            raised = True
    finally:
        run_trial.urllib.request.urlopen = real_open
        run_trial.time.sleep = real_sleep
    check("trial: a rejected credential still fails fast -- waiting cannot "
          "fix it", raised)


def test_the_window_decision_is_watched_rather_than_just_recorded():
    """PLAN item 13. The 2,400-character window is deliberately NOT being
    grown -- *don't fix what has no symptom*. A decision recorded and then
    unwatched is indistinguishable from one forgotten, so the symptom that
    would reopen it has a detector: the creature reading one of its tools
    over and over without changing it, which is exactly what 2026-09-13
    looked like (`cat tools/own/plan` six times in fifteen minutes, shown
    1,200 characters each time, built nothing).
    """
    from monitor import detectors
    now = time.time()

    def rows(n, write_at=None, gap=60):
        out = []
        for i in range(n):
            out.append({"ts": now - 20000 + i * gap, "kind": "exec_start",
                        "cmd": "cat tools/own/plan"})
            out.append({"ts": now - 20000 + i * gap + 1, "kind": "exec_end",
                        "exit_code": 0, "stdout": "#!/bin/sh"})
            if write_at == i:
                out.append({"ts": now - 20000 + i * gap + 2, "kind": "trigger_fired",
                            "type": "TOOL_WRITE", "tools": ["plan"]})
        return out

    quiet = detectors.window_reread(detectors.Context(rows(3), now=now))
    check("window: three reads is not yet a pattern",
          quiet.state == detectors.OK, "%s %s" % (quiet.state, quiet.msg))
    stuck = detectors.window_reread(detectors.Context(rows(6), now=now))
    check("window: six reads with no change is the 2026-09-13 shape",
          stuck.state == detectors.ALARM and "plan" in stuck.msg,
          "%s %s" % (stuck.state, stuck.msg))
    check("window: and it refuses to announce a cause it has not measured",
          "Measure the window before tuning" in stuck.msg, stuck.msg)
    # DENSITY, NOT A TOTAL. Six reads spread over six hours is a creature
    # consulting a file; six inside fifteen minutes is one stuck in front of
    # it. The first version counted the six-hour total and fired on a control
    # fixture that was doing ordinary work.
    spread = detectors.window_reread(
        detectors.Context(rows(6, gap=5400), now=now))
    check("window: the same six reads spread over hours is NOT the fault",
          spread.state == detectors.OK, "%s %s" % (spread.state, spread.msg))
    # Reading a file you are actively rewriting is how anyone edits.
    editing = detectors.window_reread(
        detectors.Context(rows(6, write_at=4), now=now))
    check("window: reads are counted only since the last time it CHANGED the "
          "tool, so ordinary editing is not an alarm",
          editing.state == detectors.OK, "%s %s" % (editing.state, editing.msg))
    plan = _docs().get("PLAN.md", "")
    item13 = re.search(r"^###\s*13\.[^\n]*\n(.*?)(?=^###\s|\Z)", plan, re.M | re.S)
    body = re.sub(r"\s+", " ", item13.group(1)).lower() if item13 else ""
    check("window: the board records it as a decision, naming the detector "
          "that watches it", "window_reread" in body, body[:200])


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
    # PLAN 15.3, the only proof that means anything: the container is really
    # DESTROYED and really comes back, with the creature's world intact. The
    # first version called respawn() on a running container -- a no-op
    # `docker restart` -- and reported it as evidence.
    check("docker drill: the container was really gone before the respawn",
          ev.get("container_really_gone") is True,
          ev.get("container_really_gone"))
    check("docker drill: and it came back", ev.get("respawn_works") is True,
          ev.get("respawn_works"))
    # THROUGH THE DEPLOYMENT'S OWN CODE, not the drill's copy of it. The
    # drill used to hand-roll `docker run` with the mounts written out a
    # second time, and the gate's respawn test monkeypatches `subprocess.run`
    # to a canned success -- so a drift in `ensure_container`'s mounts (a
    # lost `:ro` on the hands, a wrong `-v`) was invisible to both, and the
    # boundary item 7 rests on is exactly those mounts.
    check("docker drill: the container was created by the deployment's own "
          "`ensure_container`, so a drift in its mounts fails here",
          ev.get("started_via") == "run.ensure_container",
          ev.get("started_via"))
    check("docker drill: and the way back was the one that function handed "
          "it, rather than one the drill invented",
          ev.get("recreate_is_the_deployments") is True,
          ev.get("recreate_is_the_deployments"))
    # A DRILL MUST NOT REBUILD PRODUCTION. It used the deployment's own image
    # tag and ran `docker build -t` on it, so a drill handed the live engine
    # an image nobody asked for at its next respawn -- through a channel
    # 6.7's live-root watch cannot see, because an image is not a file under
    # `live/`. The harness refuses live roots, checkouts and the sibling
    # project, and then overwrote production sideways.
    check("docker drill: it builds its OWN image, never the deployment's",
          ev.get("image_is_not_the_deployments") is True
          and ev.get("image") != ev.get("deployed_image"),
          (ev.get("image"), ev.get("deployed_image")))
    # THE MOUNT OPTIONS, BY EFFECT. Losing `:ro` on the hands or `--user`
    # would pass every capability check here and every assertion in the gate,
    # whose respawn test mocks `subprocess.run` outright.
    check("docker drill: our hands are read-only INSIDE the body -- protected "
          "scar tissue, a mount option rather than a convention",
          ev.get("hands_read_only") is True, ev.get("hands_read_only"))
    check("docker drill: and nothing in there runs as root, at the host's "
          "own uid so what the creature writes stays readable by the engine",
          ev.get("not_root") is True and ev.get("uid_matches_the_host") is True,
          (ev.get("not_root"), ev.get("uid_matches_the_host")))
    check("docker drill: with every one of the creature's tools still there "
          "-- a respawn that rebuilds a MIND is not a recovery",
          ev.get("tools_survived_respawn") is True,
          ev.get("tools_survived_respawn"))
    check("docker drill: and a tool it wrote still runs in the new container",
          ev.get("real_tool_ran_after_respawn") is True,
          ev.get("real_tool_ran_after_respawn"))


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
    # BYTE-IDENTICAL, and here that is a claim worth making: nothing is
    # writing this simulated root, so a modification in place cannot hide in
    # the engine's churn the way it can against the real deployment. PLAN 6.7
    # promised byte-identity while the instrument compared path NAMES only;
    # a verifier called that, and this is where the stronger claim holds.
    before = rehearse.live_snapshot(live, digest=True)
    rc = rehearse.main(["tool-gone", "--scratch", live])
    after = rehearse.live_snapshot(live, digest=True)
    check("rehearse: running against a live root exits non-zero", rc != 0, rc)
    check("rehearse: AND NOTHING WAS DELETED -- the guard runs before the "
          "harness clears its workspace, not after",
          os.path.exists(precious), "the drill destroyed %s" % precious)
    check("rehearse: nor MODIFIED -- every file under the root is "
          "byte-identical afterwards",
          before == after,
          sorted(set(before or {}) ^ set(after or {}))
          or [k for k in (before or {}) if after.get(k) != before[k]])
    with io.open(precious, encoding="utf-8") as f:
        check("rehearse: and the creature's file still says what it said",
              f.read() == "the creature's work\n", "")


def test_the_drills_give_the_unproven_detectors_their_red():
    """PLAN item 6.6. Four detectors have never fired on real data because
    the faults they watch for have never happened in production: the engine
    has never gone silent, never given up, never torn its journal, never lost
    a tool off PATH. *A test that has never been seen red is a guess*, so the
    drills manufacture each fault on a scratch root and keep the journal.

    The fixtures are produced by `rehearse.py` on the laptop and committed;
    this replays the DETECTORS against them and asserts each one fires.

    **What it does NOT do, corrected 2026-09-16 after a verifier read the
    claim against the code:** it does not re-run the drills. The fixtures are
    static recordings, so a regression in `rehearse.py` -- a drill that
    stopped reproducing its fault -- leaves this green. The sentence here
    used to say the opposite, which is a docstring making a claim the
    instrument does not keep, in a suite whose parent project named that
    exact fault. Re-running the drills needs docker, systemd and a scratch
    filesystem; it is a thing a human does before believing a path works,
    and `tests/fixtures/journal/README.md` says so where the fixtures live.
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

    # WHICH BOUNDS IT RAN UNDER. A verifier pointed out that the drill uses
    # 2 starts in 120s while the deployment allows 5 in 1800 -- so the
    # mechanism is proven and the production numbers are not, and nothing
    # said so. `n_restarts: 2` read as the live bound is a figure from a
    # standin quoted as the real rung's, which is the reporting fault this
    # project keeps a whole section of doctrine about.
    bounds = ev.get("bounds_used") or {}
    check("giveup drill: the evidence names the bounds it ran under",
          int(bounds.get("StartLimitBurst", 0)) > 0
          and int(bounds.get("StartLimitIntervalSec", 0)) > 0, bounds)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    unit = io.open(os.path.join(repo, "deploy", "cousin-engine.service"),
                   encoding="utf-8").read()
    deployed = dict((l.split("=", 1)[0], l.split("=", 1)[1].strip())
                    for l in unit.splitlines() if l.startswith("StartLimit"))
    check("giveup drill: and they are NOT the deployment's, stated rather "
          "than left for a reader to assume",
          int(deployed.get("StartLimitIntervalSec", 0))
          != int(bounds.get("StartLimitIntervalSec", 0)),
          (bounds, deployed))


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
          "## Deploy regression (hour) -- engine `bbbbbbb` against `unknown`" in md,
          md[:200])
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


def test_the_probe_goes_to_what_nobody_knows_not_to_what_was_called_least():
    """19 of 50 tools had never returned a clean run, and the chooser was
    walking AWAY from them.

    2026-09-16, from reading the whole library: nearly every one of those 19
    was a bare call -- the tool correctly refusing incomplete input -- not a
    failure. So their outcome was UNKNOWN, which is the one thing a second
    user is for. Meanwhile `least_probed` ranked on `runs`, and `runs` counts
    bare calls: `view-subtask-logs` had been reached for **54 times** without
    its user ever being able to pass an argument, so it read as the
    best-explored tool in the library while nothing at all was known about
    it. The chooser then preferred tools already proven to work.

    Same shape as the alphabetical fallback it replaced (§5, 2026-09-15): **a
    number that is not a reason, used as one.** There the number was a
    position in a sorted list; here it is a count that measures our effort
    instead of our knowledge.

    **This is the non-interventionist repair, and that matters.** Nothing is
    told to the creature and no tool of its is touched — §2.1 and §2.4. The
    fault was never in the creature's tools; it was in which tool the
    framework sent its user to, and the fix is in the framework. The response
    to a gap in what we know is to go and look, not to tell the creature to
    explain itself.
    """
    import kernel.library as librarymod
    e, j, b, d = build_engine([""], [""])
    # A tool reached for constantly and never once with arguments: 54 bare
    # probes, nothing learned. The real `view-subtask-logs`.
    for _ in range(54):
        j.append("cousin_probe", tool="view-subtask-logs", exit_code=2,
                 bare=True)
    # A tool already proven to work.
    j.append("cousin_probe", tool="plan", exit_code=0, bare=False)
    # A tool barely touched, and also unknown.
    for _ in range(2):
        j.append("cousin_probe", tool="archive-get", exit_code=2, bare=True)
    tools = ["archive-get", "plan", "view-subtask-logs"]

    name, how = e.choose_target([], tools, tools)
    check("chooser: it goes to a tool whose outcome nobody knows",
          how == "unknown_outcome", (name, how))
    check("chooser: and not to the one already proven to work",
          name != "plan", (name, how))
    check("chooser: among the unknown it takes the least-reached, so visits "
          "WALK rather than sitting on one entry",
          name == "archive-get", (name, how))

    # Once something is known, it stops being the target.
    j.append("cousin_probe", tool="archive-get", exit_code=0, bare=False)
    name2, how2 = e.choose_target([], tools, tools)
    check("chooser: a tool that has answered once is no longer unknown",
          name2 == "view-subtask-logs" and how2 == "unknown_outcome",
          (name2, how2))

    # And when everything is known it spreads on knowledge, not on calls --
    # the 54 bare calls must not make a tool look well understood.
    j.append("cousin_probe", tool="view-subtask-logs", exit_code=0, bare=False)
    name3, how3 = e.choose_target([], tools, tools)
    check("chooser: with nothing unknown left it spreads, and says so",
          how3 == "least_probed", (name3, how3))

    # THE DEFINITION ITSELF, in one place so a count and a display cannot
    # disagree about what "known" means.
    check("chooser: 54 bare calls are not knowledge",
          librarymod.qualified_runs({"runs": 54, "asked": 54}) == 0)
    check("chooser: a probe from before the flag existed is not knowledge "
          "either -- it cannot be classified at all",
          librarymod.qualified_runs({"runs": 3, "unqualified": 3}) == 0)
    check("chooser: a real failure IS knowledge -- it tells its user more "
          "than a usage line does",
          librarymod.qualified_runs({"runs": 2, "asked": 1}) == 1)
    b.destroy(); shutil.rmtree(d, ignore_errors=True)


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
    # `unknown_outcome`, not `least_probed`, and the difference is the point:
    # every probe here came back BARE, so after three visits nothing has been
    # learned about any of these tools. A reason that said "least probed"
    # would be describing our effort; this one describes our knowledge.
    check("target: while every probe comes back bare, nothing is known and "
          "the recorded reason says exactly that",
          all(h == "unknown_outcome" for _n, h in seen), seen)
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
               test_a_run_can_be_seeded_with_a_tagged_inheritance,
               test_the_page_splits_the_library_on_the_inheritance_tag,
               test_the_cull_has_an_owner_and_a_trigger,
               test_the_human_can_speak_to_the_creature_once,
               test_a_respawn_may_recreate_a_container_and_never_a_mind,
               test_a_cousin_command_is_recorded_bare_only_when_it_carried_no_arguments,
               test_the_cousins_whole_block_runs_and_the_invocation_call_is_journalled,
               test_the_library_reports_outcomes_as_facts_and_its_users_verdicts,
               test_the_cousins_world_mirrors_the_creatures_and_carries_only_user_hands,
               test_the_container_runs_the_shell_the_contract_names,
               test_the_pack_checks_the_real_keys_byte_for_byte,
               test_a_container_whose_mounts_drifted_is_recreated_not_reused,
               test_a_dead_cousin_body_is_a_lost_probe_never_a_transcript,
               test_the_cousin_runs_the_tool_with_its_own_hands,
               test_a_cousin_shell_is_refused_in_a_body_that_confines_nothing,
               test_nothing_the_cousin_runs_can_change_the_creatures_tools,
               test_a_probe_the_ladder_never_answered_is_recorded_and_never_a_failure,
               test_choosing_what_to_run_is_not_judged_by_the_verdict_contract,
               test_the_framework_never_invents_the_cousins_command,
               test_the_trial_waits_out_a_rate_limit_instead_of_recording_a_failure,
               test_the_window_decision_is_watched_rather_than_just_recorded,
               test_the_brief_can_be_scored_against_cases_it_never_saw,
               test_the_docker_body_carries_the_contract_the_creature_is_promised,
               test_the_docker_drill_proves_the_keys_are_out_of_reach,
               test_a_ladder_with_every_rung_walled_never_reads_as_a_wait,
               test_the_rehearsal_cannot_touch_the_live_run,
               test_the_drills_give_the_unproven_detectors_their_red,
               test_the_giveup_drill_proves_the_chain_systemd_owns,
               test_the_census_runs_by_itself,
               test_every_hand_the_creature_has_is_one_it_has_been_told_about,
               test_the_chat_channel_is_a_scheduled_intention,
               test_the_inherited_library_is_recorded_as_not_executed,
               test_a_starved_cousin_is_told_apart_from_a_dry_tier,
               test_the_window_shows_the_creature_its_largest_tool_whole,
               test_the_same_testimony_every_visit_is_reported_as_a_form,
               test_the_shared_tier_is_watched_and_the_doctrine_cannot_drift_from_it,
               test_the_cousins_audit_has_a_named_trigger,
               test_the_evidence_tarballs_home_is_recorded,
               test_a_broken_monitor_does_not_report_as_a_finding,
               test_monitor_page_names_its_engine_and_windows,
               test_the_monitor_unit_is_read_only_over_the_evidence,
               test_the_probe_goes_to_what_nobody_knows_not_to_what_was_called_least,
               test_the_probe_never_defaults_to_the_last_name,
               test_no_tool_is_ever_hidden_from_the_listing,
               test_deploy_regression_compares_the_hour_after_a_start,
               test_the_evidence_pack_is_hashed_and_refuses_secrets,
               test_the_journal_names_the_engine_that_wrote_it,
               test_the_journal_says_which_body_the_creature_ran_in,
               test_a_wake_records_what_was_served,
               test_the_selfcheck_proves_effects_and_never_vetoes,
               test_loop_end_says_whether_it_gave_up,
               test_a_fence_inside_the_code_does_not_close_the_block,
               test_a_usage_refusal_is_not_counted_as_a_failure,
               test_the_creature_is_told_to_repair_rather_than_delete_or_panic,
               test_a_tool_that_never_worked_says_so_to_both_inhabitants,
               test_the_brief_tests_whether_the_handover_could_be_completed,
               test_a_want_survives_until_the_creature_has_had_a_turn,
               test_no_live_root_is_tracked_by_git_whatever_it_is_called,
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
               test_the_library_remembers_what_left_it,
               test_the_has_not_survived_column_cannot_be_read_as_a_cull_list,
               test_a_rung_that_answers_and_says_nothing_is_not_a_quota_refusal,
               test_the_census_catches_the_plainest_way_to_claim_an_exit_code,
               test_the_census_has_no_opinion_about_testimony_that_does_not_exist,
               test_the_block_level_trim_says_how_much_it_dropped,
               test_the_creatures_ladder_really_is_given_the_emptiness_predicate,
               test_a_parser_change_can_be_replayed_before_it_ships,
               test_the_headline_metric_does_not_shrink_when_the_page_reads_a_tail,
               test_the_parser_under_adversarial_replies,
               test_a_command_the_shell_cannot_be_given_is_not_a_broken_body,
               test_a_tools_own_words_cannot_declare_the_body_dead,
               test_a_reply_with_no_text_at_all_is_not_an_answer,
               test_the_history_does_not_shrink_a_marker_it_re_cuts,
               test_a_cut_that_removes_nothing_removes_nothing,
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
               test_the_cousin_gets_the_creatures_work_and_never_its_notes,
               test_the_cousin_has_the_instruments_the_architecture_specified,
               test_the_headline_metric_can_actually_be_computed,
               test_the_body_runs_the_bash_it_means_and_not_windows_wsl_launcher,
               test_a_regression_that_takes_a_day_to_arrive_is_still_caught,
               test_the_tool_the_creature_runs_every_cycle_stops_absorbing_every_visit,
               test_a_probe_that_ran_and_lost_its_verdict_is_finished_not_discarded,
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
    print("\n%d/%d green (%.1f%%) in %.1fs%s"
          % (len(PASS), total, 100.0 * len(PASS) / max(1, total), time.time() - t0,
             ("  [%d test(s) COULD NOT RUN on this host]" % len(CANNOT))
             if CANNOT else ""))
    if CANNOT:
        # Loud, and above the failures, because a skip on the box that is the
        # authority means the authority just stopped checking something.
        print("\nCOULD NOT RUN HERE (not a pass and not a failure):")
        for n, why in CANNOT:
            print("  %-58s needs %s" % (n, why))
    if FAIL:
        print("\nFAILURES:")
        for n, x in FAIL:
            print("  %-58s %s" % (n, x))
        return 1
    print("ALL TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
