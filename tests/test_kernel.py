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

from kernel import backends, body as bodymod, cousin, think, triggers
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
               test_command_reaches_disk_intact, test_setup_classifier, test_parse_blocks, test_no_block_classifier,
               test_triggers, test_cousin_parse, test_cousin_visit_journals,
               test_cycle_no_command, test_cycle_executes_and_journals,
               test_cycle_done_claim_triggers_cousin, test_refusal_is_delivered_once,
               test_accept_does_not_block, test_context_is_served_not_assembled,
               test_memory_reaches_the_context,
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
