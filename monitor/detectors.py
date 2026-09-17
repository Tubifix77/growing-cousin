#!/usr/bin/env python3
"""detectors.py -- one detector per scar, three states, declared floors.

Each detector is a function of a `Context` returning `Finding`s. A finding is
OK, ALARM, CANNOT_TELL or INFO -- never a bare boolean, because a detector
that cannot see enough events must SAY so rather than report OK (CLAUDE.md
§5: a checker that cannot distinguish the thing it measures reports a
clean-looking wrong number, never an error).

`human=True` on an ALARM means somebody has to look; the runner's exit code
follows only those, so `systemctl --user --failed` stays meaningful (the
spine's lesson: a blanket "any !! fails" cries wolf permanently).

Every floor here is DECLARED, with the measurement behind it in the comment.
A floor learned from the data it watches follows a collapse downward and
never fires -- the spine's ratchet disease.

Every detector has a fixture in `tests/fixtures/journal/` cut from the live
journal where its scar actually happened, and the gate asserts it fires there
at or before the moment a human noticed, and stays quiet on a healthy hour.
"""
import collections
import os
import re
import time

from . import derive

OK, ALARM, CANNOT_TELL, INFO = "OK", "ALARM", "CANNOT_TELL", "INFO"

# ---------------------------------------------------------------- floors

# An active engine writes SOMETHING every few minutes: a cycle is 30-120s, a
# wait is 150s and is itself journalled. Fifteen minutes is six waits of
# silence. Measured over run 2: the longest gap between two consecutive
# events while the engine was up was 5 minutes.
SILENT_MINUTES = 15

# Per rung, over its last 8 verdicts in the last 24h. 2026-09-13 15:40-17:40:
# gemini produced 14 UNKNOWN in a row; the fourth arrived at 16:22 and the
# fault was read as weather until ~19:40. At n<4 nothing is said.
UNUSABLE_LAST_N = 8
UNUSABLE_SHARE = 0.5
UNUSABLE_MIN_N = 4
UNUSABLE_LOOKBACK_H = 24

# Over the last 20 thinks per rung. Run 2 baseline on gemini: 52 of 758
# thinks finished on `length` (6.9%) and 26 lost their command (3.4%). The
# floor is twice the length share; a creature losing one command in six is
# a budget or parser fault, not weather.
LOST_LAST_N = 20
LOST_SHARE = 0.15
LOST_MIN_N = 10

# The same failure signature from the same tool, three times, with the tool
# rewritten in between. 2026-09-13 19:50-22:20: fifteen identical
# `SyntaxError: unterminated string literal` across as many rewrites of
# `subagent-orchestrator`, all cut by our parser; the third was at 20:00.
REPEAT_N = 3
REPEAT_WINDOW_H = 6

RECENT_H = 6


class Finding:
    def __init__(self, name, state, msg, evidence=None, human=True, scar=""):
        self.name = name
        self.state = state
        self.msg = msg
        self.evidence = evidence or {}
        self.human = human
        self.scar = scar

    def as_dict(self):
        return {"name": self.name, "state": self.state, "msg": self.msg,
                "evidence": self.evidence, "human": self.human,
                "scar": self.scar}

    def __repr__(self):
        return "Finding(%s %s: %s)" % (self.name, self.state, self.msg)


class Context:
    """Everything a detector may look at. Built once per run by status.py;
    built from a fixture by the replay."""

    def __init__(self, rows, now=None, unit=None, repo_head=None,
                 repo_changed=None, quota=None, stop_present=False,
                 complete=True, bad=0):
        self.rows = rows
        self.now = time.time() if now is None else float(now)
        self.unit = unit                  # dict from systemctl, or None
        self.repo_head = repo_head        # sha of the checkout, or None
        self.repo_changed = repo_changed  # fn(a, b) -> paths, or None
        self.quota = quota                # dict from quota.json, or None
        self.stop_present = stop_present
        self.complete = complete
        self.bad = bad
        self.library = derive.library_from_journal(rows)
        st = derive.starts(rows)
        self.last_start = st[-1] if st else None

    def recent(self, hours):
        return derive.window(self.rows, self.now - hours * 3600, self.now + 1)

    def last(self, kind):
        for r in reversed(self.rows):
            if r.get("kind") == kind:
                return r
        return None


def _ts(r):
    return float(r.get("ts", 0))


# ------------------------------------------------------------- detectors

def engine_silent(ctx):
    """No journal event for SILENT_MINUTES while the unit is not stopped on
    purpose. A hang looks like nothing; this is the something."""
    if not ctx.rows:
        return Finding("engine_silent", CANNOT_TELL, "no journal rows at all")
    age = ctx.now - _ts(ctx.rows[-1])
    state = (ctx.unit or {}).get("ActiveState")
    if ctx.stop_present and state in (None, "inactive", "failed"):
        return Finding("engine_silent", INFO,
                       "stopped by request: STOP file present, unit %s, last "
                       "event %s ago" % (state or "unknown", derive.fmt_age(age)),
                       human=False)
    if age > SILENT_MINUTES * 60:
        return Finding("engine_silent", ALARM,
                       "no journal event for %s (floor %dm); unit %s"
                       % (derive.fmt_age(age), SILENT_MINUTES, state or "unknown"),
                       {"last_event_ts": _ts(ctx.rows[-1]), "unit": ctx.unit},
                       scar="a give-up that exited 0 lay there until someone looked")
    return Finding("engine_silent", OK, "last event %s ago" % derive.fmt_age(age))


def gave_up(ctx):
    """The supervisor abandoned the run and nothing started after it. Reads
    the FLAG on `loop_end`, never the reason prose (forever.py's rule)."""
    if (ctx.unit or {}).get("ActiveState") == "failed":
        return Finding("gave_up", ALARM, "unit is in `failed` (StartLimit hit "
                       "or a crash systemd would not retry): %s"
                       % (ctx.unit or {}).get("Result", "?"), {"unit": ctx.unit},
                       scar="giving up is not finishing")
    end = ctx.last("loop_end")
    if end is None:
        return Finding("gave_up", OK, "no loop_end in the tail")
    later = [r for r in ctx.rows if _ts(r) > _ts(end)
             and r.get("kind") in ("engine_start", "loop_start")]
    if later:
        return Finding("gave_up", OK, "last loop_end was followed by a start")
    if "fault" not in end:
        return Finding("gave_up", CANNOT_TELL,
                       "the last loop_end carries no `fault` flag (engine "
                       "older than 43eb8af); reason: %s" % end.get("reason"))
    if end.get("fault"):
        return Finding("gave_up", ALARM, "the loop GAVE UP at %s (%s) and no "
                       "start followed" % (derive.ts_str(_ts(end)), end.get("reason")),
                       {"loop_end_ts": _ts(end)}, scar="giving up is not finishing")
    return Finding("gave_up", INFO if not ctx.stop_present else OK,
                   "the loop ended without fault at %s (%s)"
                   % (derive.ts_str(_ts(end)), end.get("reason")), human=False)


def unusable_verdicts(ctx):
    """Per rung: the UNKNOWN share of its last UNUSABLE_LAST_N verdicts.
    2026-09-13, fourteen in a row read as weather for four hours while the
    fields said finish=length / 94% reasoning the whole time."""
    out = []
    recent = ctx.recent(UNUSABLE_LOOKBACK_H)
    by_rung = collections.defaultdict(list)
    for v in recent:
        if v.get("kind") == "cousin_verdict":
            by_rung[v.get("rung") or "(none)"].append(v)
    for rung, vs in sorted(by_rung.items()):
        last = vs[-UNUSABLE_LAST_N:]
        n = len(last)
        unk = [v for v in last if v.get("verdict") == "UNKNOWN"]
        name = "unusable_verdicts[%s]" % rung
        if n < UNUSABLE_MIN_N:
            out.append(Finding(name, CANNOT_TELL,
                               "%d verdict%s in %dh; need %d to say anything"
                               % (n, "" if n == 1 else "s", UNUSABLE_LOOKBACK_H,
                                  UNUSABLE_MIN_N), human=False))
            continue
        causes = collections.Counter(str(v.get("error") or "?")[:40] for v in unk)
        if len(unk) >= UNUSABLE_SHARE * n:
            out.append(Finding(name, ALARM,
                               "%d of the last %d verdicts from %s were UNKNOWN: %s"
                               % (len(unk), n, rung, dict(causes)),
                               {"last_ts": _ts(last[-1]), "causes": dict(causes)},
                               scar="a reply is not automatically an answer"))
        else:
            out.append(Finding(name, OK, "%d of last %d UNKNOWN" % (len(unk), n)))
    if not out:
        out.append(Finding("unusable_verdicts", CANNOT_TELL,
                           "no verdicts in the last %dh" % UNUSABLE_LOOKBACK_H,
                           human=False))
    return out


def commands_lost(ctx):
    """Two findings. `commands_lost_parser`: any `unclosed_fence` in the last
    hour -- a tagged marker present and no block parsed means the framework
    dropped work (the 2026-09-14 anchor regression, caught in 40 minutes by
    a hand-run watch). `commands_lost[rung]`: the lost share of the last 20
    thinks per rung against a declared floor."""
    out = []
    hour = ctx.recent(1)
    uf = [r for r in hour if r.get("kind") == "exec_skip"
          and r.get("reason") == "unclosed_fence"]
    if uf:
        out.append(Finding("commands_lost_parser", ALARM,
                           "%d reply(ies) in the last hour had a ```bash marker "
                           "and no parsed block -- commands were LOST by the "
                           "parser, not absent" % len(uf),
                           {"ts": [_ts(r) for r in uf]},
                           scar="the fence that ate nine hours"))
    else:
        out.append(Finding("commands_lost_parser", OK,
                           "no unclosed_fence in the last hour"))
    # Pair each skip with the think just before it (same cycle, same code path).
    recent = ctx.recent(RECENT_H)
    per_rung = collections.defaultdict(list)     # rung -> [lost bools]
    think = None
    for r in recent:
        k = r.get("kind")
        if k == "think":
            think = r
            per_rung[r.get("rung") or "(none)"].append(False)
        elif k == "exec_skip" and think is not None and r.get("lost"):
            per_rung[think.get("rung") or "(none)"][-1] = True
    for rung, flags in sorted(per_rung.items()):
        last = flags[-LOST_LAST_N:]
        n, lost = len(last), sum(1 for f in last if f)
        name = "commands_lost[%s]" % rung
        if n < LOST_MIN_N:
            out.append(Finding(name, CANNOT_TELL, "%d thinks; need %d"
                               % (n, LOST_MIN_N), human=False))
        elif lost >= LOST_SHARE * n:
            out.append(Finding(name, ALARM,
                               "%d of the last %d thinks from %s lost their "
                               "command (floor %.0f%%)" % (lost, n, rung,
                                                           100 * LOST_SHARE),
                               {"lost": lost, "n": n},
                               scar="truncation cuts the block the contract puts last"))
        else:
            out.append(Finding(name, OK, "%d of last %d lost" % (lost, n)))
    return out


def repeated_failure(ctx):
    """The same failure signature from the same tool REPEAT_N times with the
    tool rewritten in between. That shape -- the creature fixes it, we break
    it again the same way -- is the framework manufacturing work and billing
    the creature (twelve instances in CLAUDE.md). It reports to US; the
    creature is never told (§2.4)."""
    recent = ctx.recent(REPEAT_WINDOW_H)
    groups = collections.defaultdict(list)       # (tool, sig) -> [ts]
    writes = collections.defaultdict(list)       # tool -> [ts]
    for r in recent:
        if r.get("kind") == "exec_start":
            for t in derive.tools_written(r.get("cmd")):
                writes[t].append(_ts(r))
        elif r.get("kind") == "trigger_fired" and r.get("type") == "TOOL_WRITE":
            for t in r.get("tools") or []:
                writes[t].append(_ts(r))
    for start, end in derive.paired_execs(recent):
        code = end.get("exit_code")
        if code in (0, None):
            continue
        sig = derive.failure_signature(end.get("stderr"))
        if not sig:
            continue
        tool = None
        m = derive.TOOL_PATH_RE.search(end.get("stderr") or "")
        if m and not m.group(1).endswith(".bak"):
            tool = m.group(1)
        elif start is not None:
            named = derive.commands_named(start.get("cmd")) & ctx.library
            tool = sorted(named)[0] if named else None
        if tool is None:
            continue
        groups[(tool, sig)].append(_ts(end))
    out = []
    for (tool, sig), tss in sorted(groups.items()):
        if len(tss) < REPEAT_N:
            continue
        between = [w for w in writes.get(tool, []) if tss[0] < w < tss[-1]]
        if not between:
            continue
        out.append(Finding("repeated_failure[%s]" % tool, ALARM,
                           "%s failed the same way %d times across %d rewrite(s) "
                           "in %dh: %s -- ask whether the framework is cutting "
                           "it before reading it as the creature's bug"
                           % (tool, len(tss), len(between), REPEAT_WINDOW_H, sig),
                           {"first_ts": tss[0], "third_ts": tss[REPEAT_N - 1],
                            "last_ts": tss[-1], "n": len(tss),
                            "rewrites": len(between), "signature": sig},
                           scar="the fence that ate nine hours"))
    if not out:
        out.append(Finding("repeated_failure", OK,
                           "no tool failing identically across rewrites in %dh"
                           % REPEAT_WINDOW_H))
    return out


def want_retired_unacted(ctx):
    """A want retired (not superseded) with no TOOL_WRITE since it was
    issued: direction discarded before its recipient built anything.
    Measured 2026-09-14 over run 2 and fixed in 17d8951; this is the
    assertion that it stays fixed."""
    recent = ctx.recent(RECENT_H)
    wants = [r for r in ctx.rows if r.get("kind") == "cousin_want"]
    writes = [_ts(r) for r in ctx.rows
              if r.get("kind") == "trigger_fired" and r.get("type") == "TOOL_WRITE"]
    unacted, unknown = [], 0
    for r in recent:
        if r.get("kind") != "want_retired" or r.get("because") == "superseded":
            continue
        before = [w for w in wants if _ts(w) < _ts(r)]
        if not before:
            unknown += 1
            continue
        w = before[-1]
        if not any(_ts(w) < t < _ts(r) for t in writes):
            unacted.append(r)
    if unacted:
        return Finding("want_retired_unacted", ALARM,
                       "%d want(s) retired in %dh without the creature writing "
                       "a tool since they were issued" % (len(unacted), RECENT_H),
                       {"ts": [_ts(r) for r in unacted],
                        "texts": [(r.get("texts") or [""])[0][:80] for r in unacted]},
                       scar="a channel with no completion signal")
    if unknown and not unacted:
        return Finding("want_retired_unacted", CANNOT_TELL,
                       "%d retirement(s) whose want is older than the tail" % unknown,
                       human=False)
    return Finding("want_retired_unacted", OK,
                   "every retirement in %dh followed a tool write" % RECENT_H)


def want_never_served(ctx):
    """A want issued and the next wake served zero wants. Needs the
    `wants_served` field (from 43eb8af); before that it cannot tell."""
    recent = ctx.recent(RECENT_H)
    wakes = [r for r in ctx.rows if r.get("kind") == "wake"]
    unserved, untestable, checked = [], 0, 0
    for w in recent:
        if w.get("kind") != "cousin_want":
            continue
        nxt = [k for k in wakes if _ts(k) > _ts(w)]
        if not nxt:
            continue                     # no wake yet: nothing to judge
        k = nxt[0]
        if "wants_served" not in k:
            untestable += 1
            continue
        checked += 1
        if not k.get("wants_served"):
            unserved.append(w)
    if unserved:
        return Finding("want_never_served", ALARM,
                       "%d want(s) were followed by a wake that served NO want"
                       % len(unserved), {"ts": [_ts(w) for w in unserved]},
                       scar="a channel nothing asserts can be dead while green")
    if not checked:
        return Finding("want_never_served", CANNOT_TELL,
                       "no want in %dh followed by a wake that records what it "
                       "served%s" % (RECENT_H, " (%d predate 43eb8af)" % untestable
                                     if untestable else ""), human=False)
    return Finding("want_never_served", OK,
                   "%d want(s) reached the next wake" % checked)


def served_context_contract(ctx):
    """What the last wake HELD against what should exist. The library limit
    is the live case: LIBRARY_LIMIT tools are listed and the library was at
    38 on 2026-09-14 -- a tool past the limit exists and is never shown to
    either inhabitant."""
    w = ctx.last("wake")
    if w is None:
        return Finding("served_context_contract", CANNOT_TELL, "no wake in the tail")
    if "library_total" not in w:
        return Finding("served_context_contract", CANNOT_TELL,
                       "the last wake predates 43eb8af and records only its length",
                       human=False)
    shown, total = w.get("library_shown") or 0, w.get("library_total") or 0
    if total == 0 and ctx.library:
        return Finding("served_context_contract", ALARM,
                       "the last wake served an EMPTY library while the journal "
                       "knows %d tools" % len(ctx.library),
                       {"wake_ts": _ts(w), "journal_library": len(ctx.library)},
                       scar="the builder's library gap survived a day")
    named = w.get("library_named")
    if named is None:
        # An engine older than the names-only tail: past the limit WAS hidden.
        if shown < total:
            return Finding("served_context_contract", ALARM,
                           "%d of %d tools are beyond the listing limit and are "
                           "shown to NOBODY" % (total - shown, total),
                           {"shown": shown, "total": total},
                           scar="a bound nobody chose, obeyed forever")
    elif named < total:
        return Finding("served_context_contract", ALARM,
                       "%d of %d tools are not even NAMED on the page"
                       % (total - named, total), {"named": named, "total": total},
                       scar="a bound nobody chose, obeyed forever")
    elif shown < total:
        return Finding("served_context_contract", INFO,
                       "%d of %d tools are past the full-entry limit and shown by "
                       "name and purpose only" % (total - shown, total),
                       {"shown": shown, "total": total}, human=False)
    return Finding("served_context_contract", OK,
                   "last wake served %d/%d tools, %s want(s), window %s"
                   % (shown, total, w.get("wants_served"), w.get("window")))


# ------------------------------------------------- the loop closed on nothing

# The same want issued three of the last five times. Run 2, 2026-09-15: one
# want six times in eighteen hours, each behind an ACCEPT of a usage line the
# cousin could not get past, while the creature built five different tools to
# answer it. A direction channel that repeats itself is a loop closed on
# nothing, whatever the verdicts say.
WANT_REPEAT_LAST_N, WANT_REPEAT_MIN = 5, 3
# The same tool probed five of the last eight visits that were NOT about a
# tool just written. 2026-09-15: `view-subtask-logs` 28 of 30 -- and on
# 2026-09-13 `plan` 30 times -- because the chooser defaulted to the
# alphabetically last name. Probes on TOOL_WRITE visits are excluded: a tool
# rewritten five times is legitimately probed five times.
PROBE_STUCK_LAST_N, PROBE_STUCK_MIN = 8, 5


def _norm(text):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", (text or "").lower())).strip()


def want_repeated(ctx):
    """A want restating itself is the run-1 failure mode returning: nothing
    the creature builds discharges it, because the cousin cannot verify what
    it asks for (a bare probe) or cannot see what was built (a hidden tool)."""
    wants = [r for r in ctx.recent(24) if r.get("kind") == "cousin_want"]
    last = wants[-WANT_REPEAT_LAST_N:]
    if len(last) < WANT_REPEAT_MIN:
        return Finding("want_repeated", CANNOT_TELL,
                       "%d want(s) in 24h; need %d" % (len(last), WANT_REPEAT_MIN),
                       human=False)
    counts = collections.Counter(_norm(r.get("text")) for r in last)
    text, n = counts.most_common(1)[0]
    if n >= WANT_REPEAT_MIN:
        hits = [r for r in last if _norm(r.get("text")) == text]
        return Finding("want_repeated", ALARM,
                       "the same want %d of the last %d times -- \"%s\" -- the "
                       "loop is closed on nothing: the cousin cannot verify the "
                       "capability it asks for, or cannot see what was built"
                       % (n, len(last), (hits[-1].get("text") or "")[:90]),
                       {"n": n, "of": len(last), "first_ts": _ts(hits[0]),
                        "last_ts": _ts(hits[-1]), "text": hits[-1].get("text")},
                       scar="a channel with no completion signal is re-served forever")
    return Finding("want_repeated", OK, "%d distinct of the last %d wants"
                   % (len(counts), len(last)))


def probe_stuck(ctx):
    """The cousin sent to the same tool again and again on visits that were
    not about a tool just written.

    **WHOSE fault that is depends on `picked_by`, and this detector used to
    answer before it looked.** Its message hard-coded *"a chooser fault in
    the framework, not a fact about the tool"* onto every alarm, and its
    runbook sent the reader hunting one. Found live on 2026-09-16 by a
    verifier reading the page: the standing alarm said exactly that while
    carrying `picked_by: {'ran': 5, 'least_probed': 1}` -- `ran` means the
    CREATURE invoked that tool itself that cycle and the chooser followed it.
    The framework chose nothing. The detector's own recorded evidence refuted
    its own conclusion, on the page, for hours.

    That is the retired `pick_target` scar inverted: there a position in a
    sorted list was an unstated reason; here the reason IS recorded and the
    message ignored it. **A constant nobody chose, obeyed forever** -- the
    first fault this project's doctrine names, committed inside the
    instrument built to catch it.

    So the message is now derived from the `hows` it already computes:
    `least_probed` sitting on one tool is a framework fault, `ran` is the
    creature working on one tool and not a fault at all, and an unrecorded
    mixture says so rather than guessing.
    """
    recent = ctx.recent(24)
    trig, probes = None, []
    for r in recent:
        k = r.get("kind")
        if k == "trigger_fired":
            trig = r.get("type")
        elif k == "cousin_probe":
            how = r.get("picked_by")
            about_a_write = (how in ("new", "written")) if how else (trig == "TOOL_WRITE")
            if not about_a_write:
                probes.append(r)
    last = probes[-PROBE_STUCK_LAST_N:]
    if len(last) < PROBE_STUCK_MIN:
        return Finding("probe_stuck", CANNOT_TELL,
                       "%d probe(s) in 24h not about a fresh write; need %d"
                       % (len(last), PROBE_STUCK_MIN), human=False)
    counts = collections.Counter(r.get("tool") for r in last)
    tool, n = counts.most_common(1)[0]
    if n >= PROBE_STUCK_MIN:
        hows = collections.Counter(r.get("picked_by") or "(unrecorded)" for r in last
                                   if r.get("tool") == tool)
        top, top_n = hows.most_common(1)[0]
        if top == "ran":
            why = ("the CREATURE ran it in %d of those cycles and the chooser "
                   "followed -- so this is the creature working on one tool, "
                   "NOT a framework fault. Read it before changing anything "
                   "in the chooser" % top_n)
            scar = "a checker that cannot distinguish the thing it measures"
        elif top in ("least_probed", "unknown_outcome"):
            why = ("the framework walked the library to it %d times, which "
                   "`least_probed` should not do -- a chooser fault, not a "
                   "fact about the tool" % top_n)
            scar = "the framework manufactures work and the creature is billed"
        else:
            why = ("picked by %s -- who chose cannot be read off this, so "
                   "read `cousin_probe.picked_by` on these probes before "
                   "concluding whose fault it is" % top)
            scar = "a checker that cannot distinguish the thing it measures"
        return Finding("probe_stuck", ALARM,
                       "its user was sent to `%s` on %d of the last %d visits not "
                       "about a fresh write (picked by: %s) -- %s"
                       % (tool, n, len(last), dict(hows), why),
                       {"tool": tool, "n": n, "of": len(last), "hows": dict(hows),
                        "picked_mostly_by": top, "last_ts": _ts(last[-1])},
                       scar=scar)
    return Finding("probe_stuck", OK, "%d tools across the last %d such probes"
                   % (len(counts), len(last)))


def tool_vanished(ctx):
    """exit 127 on a name the journal knows as a tool: a body/PATH fault
    (the relative-root scar), NOT the creature's `Goal:`-as-a-command
    confusion. Keyed on the exit code -- the box speaks Danish."""
    recent = ctx.recent(RECENT_H)
    gone = collections.Counter()
    for start, end in derive.paired_execs(recent):
        if end.get("exit_code") != 127 or start is None:
            continue
        for n in derive.commands_named(start.get("cmd")) & ctx.library:
            gone[n] += 1
    if gone:
        return Finding("tool_vanished", ALARM,
                       "library tools returned `command not found` (exit 127): %s"
                       % dict(gone), {"tools": dict(gone)},
                       scar="a relative root made every tool vanish while the "
                            "body reported healthy")
    return Finding("tool_vanished", OK, "no library tool exited 127 in %dh" % RECENT_H)


def selfcheck_disproven(ctx):
    """The start-up effect tests, read back. A False is a bound this
    deployment relies on that does NOT hold; None is one that could not be
    tested here."""
    start = ctx.last("engine_start")
    sc = ctx.last("selfcheck")
    if start is None:
        return Finding("selfcheck", CANNOT_TELL,
                       "no engine_start in the tail: the engine predates 43eb8af",
                       human=False)
    if sc is None or _ts(sc) < _ts(start):
        return Finding("selfcheck", CANNOT_TELL,
                       "no selfcheck since the last start at %s"
                       % derive.ts_str(_ts(start)))
    bad = sorted(k for k, v in sc.items() if v is False)
    if bad:
        return Finding("selfcheck", ALARM, "DISPROVEN at start: %s" % ", ".join(bad),
                       {"selfcheck": {k: v for k, v in sc.items() if k != "ts"}},
                       scar="a setting present, parsed and live can still do nothing")
    unproven = sc.get("unproven") or []
    return Finding("selfcheck", OK, "nothing disproven at %s%s"
                   % (derive.ts_str(_ts(sc)),
                      (" (untestable here: %s)" % ", ".join(unproven)) if unproven else ""))


# What the ENGINE process imports or reads at start (deploy/README.md's
# restart table). The monitor's own unit and the docs are not on this list:
# changing them owes the engine nothing, and a restart_owed that fires on a
# README edit is a wolf-crier.
CODE_PATHS = ("kernel/", "run.py", "hands/", "deploy/cousin-engine.service",
              "CREATURE-PROMPT.md", "MANAGER-PROMPT.md")


def restart_owed(ctx):
    """Is the running engine the checkout? Docs-only changes owe nothing;
    code changes owe a restart -- the question answered by hand every hour
    on 2026-09-14."""
    if ctx.last_start is None or ctx.repo_head is None:
        return Finding("restart_owed", CANNOT_TELL,
                       "no start record or no git here", human=False)
    running = ctx.last_start.get("engine") or "unknown"
    if running == "unknown":
        return Finding("restart_owed", CANNOT_TELL,
                       "the running engine did not record its commit (older "
                       "than 43eb8af); repo is at %s" % ctx.repo_head[:7], human=False)
    if running == ctx.repo_head:
        return Finding("restart_owed", OK, "running the checkout, %s%s"
                       % (running[:7], " (DIRTY TREE)" if ctx.last_start.get("dirty") else ""),
                       human=False)
    changed = ctx.repo_changed(running, ctx.repo_head) if ctx.repo_changed else None
    if changed is None:
        return Finding("restart_owed", INFO, "running %s, repo at %s; could not "
                       "diff" % (running[:7], ctx.repo_head[:7]), human=False)
    code = [p for p in changed if p.startswith(CODE_PATHS) or p in CODE_PATHS]
    if code:
        return Finding("restart_owed", INFO,
                       "RESTART OWED: running %s, repo at %s, code changed: %s"
                       % (running[:7], ctx.repo_head[:7], ", ".join(code[:8])),
                       {"changed": changed}, human=False)
    return Finding("restart_owed", INFO,
                   "running %s, repo at %s: docs-only since, no restart owed"
                   % (running[:7], ctx.repo_head[:7]), human=False)


def ladder_dry(ctx):
    """Weather, labelled as weather. All rungs skipping at once is the free
    tier working as designed; the duration is worth a line, never an alarm
    -- CLAUDE.md §0: never restart to clear it."""
    q = ctx.quota
    if not isinstance(q, dict) or not q:
        return Finding("ladder_dry", CANNOT_TELL, "no quota state readable", human=False)
    dry, since = [], []
    for rung, st in sorted(q.items()):
        st = st or {}
        until = (st.get("since") or 0) + (st.get("skip") or 0)
        if st.get("skip") and until > ctx.now:
            dry.append("%s (until %s)" % (rung, derive.ts_str(until, "%H:%M")))
            since.append(st.get("since") or ctx.now)
    if len(dry) == len(q):
        return Finding("ladder_dry", INFO,
                       "WEATHER: every rung is dry, for %s -- expected on a free "
                       "tier; do not restart" % derive.fmt_age(ctx.now - max(since)),
                       {"dry": dry}, human=False)
    if dry:
        return Finding("ladder_dry", INFO, "dry: %s" % "; ".join(dry), human=False)
    return Finding("ladder_dry", OK, "no rung is skipping")


def journal_integrity(ctx):
    """Lines that did not parse, timestamps running backwards, a tail that
    does not reach the file's start. Reported, never repaired: a monitor that
    rewrites the evidence is not a monitor."""
    back = sum(1 for a, b in zip(ctx.rows, ctx.rows[1:]) if _ts(b) < _ts(a) - 1)
    bits = []
    if ctx.bad > 1:
        return Finding("journal_integrity", ALARM, "%d unparseable line(s)"
                       % ctx.bad, {"bad": ctx.bad, "backwards": back},
                       scar="store the raw evidence")
    if ctx.bad == 1:
        bits.append("1 unparseable line (may be the one being written)")
    if back:
        bits.append("%d timestamp(s) ran backwards" % back)
    if not ctx.complete:
        bits.append("tail only: figures 'since start' may be cut")
    if bits:
        return Finding("journal_integrity", INFO, "; ".join(bits), human=False)
    return Finding("journal_integrity", OK, "%d rows parse, in order" % len(ctx.rows))



# DECLARED FLOORS, never learned. Four hours is long enough that a quiet
# afternoon does not fire it and short enough that fifteen hours cannot
# pass again; three probes is the fewest that can distinguish "always"
# from "twice".
COUSIN_STARVED_H = 4
COUSIN_STARVED_MIN = 3


def cousin_starved(ctx):
    """Probes reaching nobody while the CREATURE is served on the same rungs.

    **The asymmetry is the whole signal.** A dry free tier starves both
    inhabitants together -- that is weather, and `ladder_dry` already says so.
    One agent being served while the other never is cannot be weather: it is
    something about how that agent's call is made.

    Written 2026-09-16 after exactly that went unseen for fifteen hours. The
    cousin's command-choosing call was asked through the ladder that rejects
    any reply without a VERDICT block, so every correct answer walled a rung
    and every probe was lost: **112 probes, 112 lost, 0 verdicts -- and 112
    creature thinks in the same window on the same rungs.** Both numbers were
    on the page, in adjacent rows, and nothing put them side by side.

    Three states, and the middle one matters: with no probes at all this says
    CANNOT TELL rather than OK, because a cousin that is never summoned looks
    identical to one that is summoned and always fails -- and the second is
    the fault this exists for.
    """
    recent = ctx.recent(COUSIN_STARVED_H)
    probes = [r for r in recent if r.get("kind") == "cousin_probe"]
    thinks = [r for r in recent if r.get("kind") == "think"]
    if len(probes) < COUSIN_STARVED_MIN:
        return Finding("cousin_starved", CANNOT_TELL,
                       "%d probe(s) in %dh; need %d to tell a starved cousin "
                       "from a quiet one" % (len(probes), COUSIN_STARVED_H,
                                             COUSIN_STARVED_MIN),
                       human=False)
    lost = [p for p in probes if p.get("exit_code") is None]
    if len(lost) < len(probes):
        return Finding("cousin_starved", OK,
                       "%d of %d probes reached the tool" %
                       (len(probes) - len(lost), len(probes)),
                       {"probes": len(probes), "lost": len(lost)})
    if not thinks:
        # Everything is starved. That IS the weather, and `ladder_dry` owns it.
        return Finding("cousin_starved", INFO,
                       "every probe lost (%d) and the creature was not served "
                       "either -- the tier is dry for both, which is weather"
                       % len(lost), {"probes": len(probes), "thinks": 0},
                       human=False)
    return Finding(
        "cousin_starved", ALARM,
        "EVERY probe reached nobody (%d of %d in %dh) while the creature was "
        "served %d times on the same rungs. A dry tier starves both; one "
        "agent served and the other never is something about how the "
        "cousin's call is MADE -- its ladder's usability predicate, its "
        "budget, its prompt -- not about the free tier"
        % (len(lost), len(probes), COUSIN_STARVED_H, len(thinks)),
        {"probes": len(probes), "lost": len(lost), "thinks": len(thinks),
         "last_error": (lost[-1].get("error") or "")[:200]},
        scar="a second caller inherited the first one's contract")

# THE SAME TESTIMONY, VERDICT AFTER VERDICT. The brief's own test for a
# report that is really a form: "if your sentence would still make sense with
# another tool's name dropped into it, you have written a form and not a
# report, and it tells the creature nothing." Found live 2026-09-17: four
# consecutive ACCEPTs of `plan` carried the identical sentence -- *I ran
# `plan` and got the usage menu. I can now see how to manage my goals and
# tasks in one place* -- while the want they carried ("assign deadlines")
# repeated four times and the feature it asked for, already built, was never
# once run. The cousin was judging on a menu it had chosen to summon.
TESTIMONY_LAST_N = 5
TESTIMONY_MIN = 3


def testimony_repeated(ctx):
    """The cousin saying the same thing about every visit is the cousin
    judging on nothing it exercised. Visibility, never a gate; the judgement
    itself is the brief's (PLAN item 16)."""
    vs = [r for r in ctx.recent(24) if r.get("kind") == "cousin_verdict"
          and r.get("verdict") in ("ACCEPTED", "RETURNED")]
    last = vs[-TESTIMONY_LAST_N:]
    if len(last) < TESTIMONY_MIN:
        return Finding("testimony_repeated", CANNOT_TELL,
                       "%d verdict(s) in 24h; need %d to tell a form from a report"
                       % (len(last), TESTIMONY_MIN), human=False)

    def norm(t):
        return " ".join((t or "").lower().split())
    counts = collections.Counter(norm(v.get("to_creature")) for v in last)
    text, n = counts.most_common(1)[0]
    if text and n >= TESTIMONY_MIN:
        tools = sorted({v.get("tool") or "?" for v in last if norm(v.get("to_creature")) == text})
        return Finding(
            "testimony_repeated", ALARM,
            "the same testimony on %d of the last %d verdicts (about %s) -- \"%s\" -- "
            "a report that could be about any visit is a form, not a report (the "
            "brief's own test), and a cousin that says the same thing every time "
            "has exercised nothing. Read the probes behind them: a bare call to a "
            "menu means the feature it keeps asking for was never tried"
            % (n, len(last), ", ".join("`%s`" % t for t in tools), text[:120]),
            {"n": n, "of": len(last), "text": text[:300], "tools": tools},
            scar="any field that gives a shortfall a comfortable home will be used")
    return Finding("testimony_repeated", OK,
                   "%d distinct testimonies across the last %d verdicts"
                   % (len(counts), len(last)), human=False)


# The sibling project's unit. Named here rather than in the caller so the
# detector and the unit list cannot drift apart.
SPINE_UNIT = "growing-spine.service"


def shared_tier_contested(ctx):
    """Is the sibling project running, and does the doctrine still say what is
    true? CLAUDE.md §4: the two projects share one free tier, so the spine's
    state is a CONDITION OF MEASUREMENT here -- *numbers taken while spine is
    paused are NOT comparable to numbers taken before it, in either direction.*

    **This exists because the pause silently ended and nothing noticed for 27
    hours.** Tue stopped the spine 2026-09-13 13:47. It was started again
    2026-09-15 00:12:11, four minutes after its own flatline tripwire
    reported `THINK:!!NONE in 6h`, and ran from then on -- through the whole
    first day of this monitor, through the evening read of 2026-09-15 18:52
    whose figures went into §7, and through the opening of item 9.5's
    measurement window. `CLAUDE.md` §4 said PAUSED the entire time. Found
    2026-09-16 by an independent verifier who ran `systemctl` instead of
    reading the file.

    Nothing in this monitor mentioned the spine and no test guarded item 12,
    which is exactly §5's *a channel nothing asserts is a channel that can be
    dead while everything is green* -- here applied not to a feature but to a
    standing decision. **A decision recorded and then unwatched is
    indistinguishable from one forgotten.**

    It REPORTS and never acts. Whether the spine runs is Tue's standing
    decision (§4) and PLAN item 12 is explicit that restarting it is his
    call; by symmetry so is stopping it. What this owes him is that the state
    and the document cannot disagree without someone being told.
    """
    unit = (getattr(ctx, "units", {}) or {}).get(SPINE_UNIT)
    if not unit:
        return Finding("shared_tier_contested", CANNOT_TELL,
                       "the spine's unit was not read on this pass", human=False)
    active = (unit.get("ActiveState") or "").strip()
    if not active:
        return Finding("shared_tier_contested", CANNOT_TELL,
                       "`systemctl show %s` answered nothing -- on a box "
                       "without the sibling installed this is the right "
                       "answer, and it is not 'paused'" % SPINE_UNIT,
                       human=False)
    running = active == "active"
    says_paused = bool(getattr(ctx, "doctrine_says_paused", False))
    since = (unit.get("ExecMainStartTimestamp") or "").strip() or "?"
    if running and says_paused:
        return Finding(
            "shared_tier_contested", ALARM,
            "THE SPINE IS RUNNING and CLAUDE.md §4 still says it is PAUSED "
            "(started %s). The free tier is shared, so every figure taken "
            "since then was measured against a tier this engine does NOT "
            "have to itself -- including any open measurement window. Fix "
            "the document or stop the spine; the two must not disagree" % since,
            {"unit": unit, "doctrine_says_paused": True, "since": since},
            scar="a channel nothing asserts can be dead while everything is green")
    if running:
        return Finding(
            "shared_tier_contested", INFO,
            "the spine is running (since %s) and the doctrine says so -- "
            "every rate from this window is measured against a SHARED tier "
            "and is not comparable to one taken while it was paused" % since,
            {"unit": unit, "since": since}, human=False)
    return Finding("shared_tier_contested", OK,
                   "the spine is %s; this engine has the free tier to itself"
                   % active, {"unit": unit}, human=False)


def twin_pressure(ctx):
    """Stem families with three or more members. Visibility on the frozen
    question (CLAUDE.md §5, 2026-09-14) -- shown, never judged here."""
    fam = derive.stems(ctx.library)
    big = {s: len(v) for s, v in fam.items() if len(v) >= 3}
    if not ctx.library:
        return Finding("twin_pressure", CANNOT_TELL, "no library in the tail", human=False)
    return Finding("twin_pressure", INFO,
                   "%d tools; families of 3+: %s" % (
                       len(ctx.library),
                       ", ".join("%s-* x%d" % (s, n) for s, n in
                                 sorted(big.items(), key=lambda x: -x[1])) or "none"),
                   {"families": big, "tools": len(ctx.library)}, human=False)


# --------------------------------------------------- deploy regression

# The hour after a start against the hour before it. One hour is ONE window
# and this engine is not deterministic (CLAUDE.md §5), so this is a smoke
# alarm for CORRECTNESS indicators -- the class that is wrong for any model
# -- never a verdict on tuning. The habit it automates: 2026-09-14, twice in
# one evening, a parser change had a cost that a hand-run watch found within
# the hour; without the watch each would have been another nine-hour silence.
REGRESSION_WINDOW_S = 3600
REGRESSION_MIN_WAKES = 5
# Declared floors. Lost-command share: run 2's gemini baseline is 3.4%, so
# 10% AND at least doubled. Failed commands: the creature's own errors run
# 20-30% on a normal hour (exit 1/2 while it debugs), so 30% AND doubled.
# UNKNOWN verdicts: half or more of at least four, where before it was under
# a quarter. Probe failures: half of at least five real (qualified) probes,
# and doubled.
REG_LOST_SHARE, REG_FAILED_SHARE = 0.10, 0.30
REG_UNKNOWN_SHARE, REG_UNKNOWN_BEFORE = 0.50, 0.25
REG_PROBE_FAILED_SHARE, REG_PROBE_MIN = 0.50, 5


def _share_str(v, n):
    return "-" if v is None else "%.0f%% (n=%d)" % (100 * v, n)


def regression_table(before, after):
    """Rows of `(indicator, before, after)` as strings, and the list of
    indicators that crossed a floor. Pure; the caller decides what to do."""
    mb, ma = derive.measure(before), derive.measure(after)
    rows, worse = [], []

    def sh(m, num, den):
        v, _ = derive.share(m[num], m[den])
        return v

    ufb = mb["skips"].get("unclosed_fence|lost", 0)
    ufa = ma["skips"].get("unclosed_fence|lost", 0)
    rows.append(("unclosed_fence (parser dropped work)", str(ufb), str(ufa)))
    if ufa and not ufb:
        worse.append("unclosed_fence appeared: %d" % ufa)

    lb, la = sh(mb, "commands_lost", "thinks"), sh(ma, "commands_lost", "thinks")
    rows.append(("commands lost / thinks", _share_str(lb, mb["thinks"]),
                 _share_str(la, ma["thinks"])))
    if (la is not None and ma["thinks"] >= LOST_MIN_N and la >= REG_LOST_SHARE
            and (lb is None or la >= 2 * lb)):
        worse.append("lost-command share %s -> %s" % (_share_str(lb, mb["thinks"]),
                                                     _share_str(la, ma["thinks"])))

    fb, fa = sh(mb, "cmd_failed", "commands"), sh(ma, "cmd_failed", "commands")
    rows.append(("commands failed / commands", _share_str(fb, mb["commands"]),
                 _share_str(fa, ma["commands"])))
    if (fa is not None and ma["commands"] >= 10 and fa >= REG_FAILED_SHARE
            and (fb is None or fa >= 2 * fb)):
        worse.append("failed-command share %s -> %s"
                     % (_share_str(fb, mb["commands"]), _share_str(fa, ma["commands"])))

    def unknown(m):
        u = sum(c.get("UNKNOWN", 0) for c in m["verdicts_by_rung"].values())
        v, _ = derive.share(u, m["verdicts"])
        return v
    ub, ua = unknown(mb), unknown(ma)
    rows.append(("UNKNOWN / verdicts (all rungs; split in the page)",
                 _share_str(ub, mb["verdicts"]), _share_str(ua, ma["verdicts"])))
    if (ua is not None and ma["verdicts"] >= UNUSABLE_MIN_N and ua >= REG_UNKNOWN_SHARE
            and (ub is None or ub < REG_UNKNOWN_BEFORE)):
        worse.append("UNKNOWN verdict share %s -> %s"
                     % (_share_str(ub, mb["verdicts"]), _share_str(ua, ma["verdicts"])))

    def pnonzero(m):
        # A regression indicator, not a verdict on the tools: a JUMP in the
        # non-zero share across a deploy is a smoke alarm whatever the cause.
        p = m["probes"]
        n = p["worked"] + p["asked"] + p["nonzero"]
        v, _ = derive.share(p["nonzero"], n)
        return v, n
    (pb, nb), (pa, na) = pnonzero(mb), pnonzero(ma)
    rows.append(("probes exited non-zero / qualified probes", _share_str(pb, nb), _share_str(pa, na)))
    if (pa is not None and na >= REG_PROBE_MIN and pa >= REG_PROBE_FAILED_SHARE
            and (pb is None or pa >= 2 * pb)):
        worse.append("probe non-zero share %s -> %s" % (_share_str(pb, nb), _share_str(pa, na)))

    for label, key in (("wakes", "wakes"), ("thinks", "thinks"), ("commands", "commands"),
                       ("verdicts", "verdicts"), ("wants", "wants"),
                       ("tool writes", "tool_writes"), ("rungs declined", "rung_declined"),
                       ("waits", "waits")):
        rows.append((label, str(mb[key]), str(ma[key])))
    return rows, worse, mb, ma


def deploy_regression(ctx):
    """The hour after the last start against the hour before it, on the
    correctness indicators. Pending until the hour is up; CANNOT_TELL with
    too few cycles on either side; ALARM when a declared floor is crossed;
    INFO otherwise -- and the comparison is written to a file once either
    way, because the table is worth having even when it says nothing moved."""
    start = ctx.last_start
    if start is None:
        return Finding("deploy_regression", CANNOT_TELL, "no start record in the tail",
                       human=False)
    t0 = float(start["ts"])
    sha = (start.get("engine") or "unknown")[:7]
    prev = [s for s in derive.starts(ctx.rows) if float(s["ts"]) < t0]
    prev_sha = (prev[-1].get("engine") or "unknown")[:7] if prev else "unknown"
    ev = {"start_ts": t0, "engine": sha, "before_engine": prev_sha}
    if ctx.now - t0 < REGRESSION_WINDOW_S:
        return Finding("deploy_regression", INFO,
                       "engine %s started %s ago; its first hour is compared "
                       "against the hour before at %s"
                       % (sha, derive.fmt_age(ctx.now - t0),
                          derive.ts_str(t0 + REGRESSION_WINDOW_S, "%H:%M")),
                       ev, human=False)
    before = derive.window(ctx.rows, t0 - REGRESSION_WINDOW_S, t0)
    after = derive.window(ctx.rows, t0, t0 + REGRESSION_WINDOW_S)
    wb = sum(1 for r in before if r.get("kind") == "wake")
    wa = sum(1 for r in after if r.get("kind") == "wake")
    ev["hour_complete"] = True
    if wb < REGRESSION_MIN_WAKES or wa < REGRESSION_MIN_WAKES:
        return Finding("deploy_regression", CANNOT_TELL,
                       "engine %s: too few cycles to compare -- %d wakes in the "
                       "hour before, %d in the hour after (need %d each)"
                       % (sha, wb, wa, REGRESSION_MIN_WAKES), ev, human=False)
    table, worse, mb, ma = regression_table(before, after)
    ev.update({"table": table, "worse": worse, "wakes_before": wb, "wakes_after": wa})
    if worse:
        return Finding("deploy_regression", ALARM,
                       "engine %s vs %s, first hour against the hour before: WORSE "
                       "on %s" % (sha, prev_sha, "; ".join(worse)), ev,
                       scar="after changing a parser the creature speaks through, "
                            "hunt for the cost within the hour")
    return Finding("deploy_regression", INFO,
                   "engine %s vs %s: no correctness indicator crossed its floor in "
                   "the first hour (%d wakes before / %d after)" % (sha, prev_sha, wb, wa),
                   ev, human=False)


# The 2026-09-13 waste pattern, exactly: `plan` had grown to 4,022 bytes, the
# creature ran `cat tools/own/plan` SIX times in FIFTEEN MINUTES, was shown
# 1,200 characters each time, and built nothing.
#
# **Density, not a six-hour count.** The first version asked for four reads
# anywhere in six hours and fired on a control fixture where the creature
# read one tool four times across the whole window -- which is a creature
# consulting a file, not one trapped in front of it. Four inside an hour is
# the shape that cost a day; four spread over six is ordinary work.
REREAD_MIN = 4
REREAD_SPAN_SECS = 3600
READ_TOOL_RE = re.compile(
    r"\b(?:cat|head|tail|less|more|sed\s+-n|python3?\s+-c[^\n]*open)\b[^\n|;]*?"
    r"(?:tools/own/|/mind/tools/own/|\$MIND/tools/own/)([A-Za-z0-9_.\-]+)")


def window_reread(ctx):
    """Is the creature reading one of its tools over and over without
    changing it?

    PLAN item 13 is a decision NOT to grow the 2,400-character output window,
    on the rule *don't fix what has no symptom*. This is the symptom, so that
    the decision is watched rather than merely recorded.

    It is not proof the window is too small -- a creature can reread a file
    for its own reasons -- which is why it reports the pattern and names the
    measurement that would settle it, rather than announcing a cause.
    """
    recent = ctx.recent(RECENT_H)
    reads, writes = collections.defaultdict(list), collections.defaultdict(list)
    for r in recent:
        if r.get("kind") == "exec_start":
            cmd = r.get("cmd") or ""
            for m in READ_TOOL_RE.finditer(cmd):
                reads[m.group(1)].append(_ts(r))
            for t in derive.tools_written(cmd):
                writes[t].append(_ts(r))
        elif r.get("kind") == "trigger_fired" and r.get("type") == "TOOL_WRITE":
            for t in r.get("tools") or []:
                writes[t].append(_ts(r))
    stuck = {}
    for tool, when in reads.items():
        if len(when) < REREAD_MIN:
            continue
        # Only the reads since the last time it CHANGED the thing. Reading a
        # tool you are actively rewriting is how anyone edits.
        last_write = max(writes.get(tool) or [0])
        after = sorted(t for t in when if t > last_write)
        # The densest run: how many of those fall inside one hour of each
        # other. A sliding window, because the fault is being STUCK, and a
        # total over six hours cannot tell stuck from thorough.
        worst = 0
        for i, t0 in enumerate(after):
            n = sum(1 for t in after[i:] if t - t0 <= REREAD_SPAN_SECS)
            worst = max(worst, n)
        if worst >= REREAD_MIN:
            stuck[tool] = worst
    if stuck:
        worst = max(stuck, key=lambda k: stuck[k])
        return Finding("window_reread", ALARM,
                       "the creature read `%s` %d times within an hour without "
                       "changing it (%s) -- the 2026-09-13 shape, where it read one tool "
                       "six times through a 1,200-character window and built "
                       "nothing. Measure the window before tuning it: a cap is "
                       "a guess until a before/after says otherwise"
                       % (worst, stuck[worst], dict(stuck)),
                       {"tools": stuck, "window_hours": RECENT_H},
                       scar="two caps in series, and the one that was tuned was "
                            "not the one that acts")
    return Finding("window_reread", OK,
                   "no tool reread %d+ times inside an hour without being "
                   "changed, in %dh" % (REREAD_MIN, RECENT_H))


def creature_said(ctx):
    """Has the creature written to the human, and has anyone looked?

    PLAN item 14.3. `hands/say` appends to `<mind>/outbox.md`, and when it
    shipped **nothing read that file** -- no detector, no page, no document.
    A channel whose far end nobody reads is the *dead channel* scar with a
    politer face: the creature would be writing letters into a drawer.

    Reports rather than alarms. The creature speaking is not a fault, and a
    message that has been there a while is a fact about the human, not the
    engine -- so this is INFO however old it is, and the page is where it
    shows up.
    """
    root = getattr(ctx, "root", None)
    if not root:
        return Finding("creature_said", CANNOT_TELL, "no root to read",
                       human=False)
    path = os.path.join(root, "body", "mind", "outbox.md")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
    except OSError:
        return Finding("creature_said", OK, "nothing in the outbox")
    if not text:
        return Finding("creature_said", OK, "nothing in the outbox")
    blocks = [b.strip() for b in text.split("--- ") if b.strip()]
    last = blocks[-1].replace("\n", " ") if blocks else text[:120]
    return Finding("creature_said", INFO,
                   "the creature has written %d message(s) to you; the last "
                   "is: %s" % (len(blocks), last[:160]),
                   {"messages": len(blocks), "path": path}, human=False)


def body_unrecoverable(ctx):
    """The body stopped answering and could not be brought back.

    Found 2026-09-16 by the body drill. `LocalBody.respawn` sets its alive
    flag and re-probes; it does not rebuild the tree. So when the creature
    removes its own `$MIND` -- which its shell can do, and `$MIND` is handed
    to it on purpose -- the respawn returns False, `run_cycle` records
    `error where=body` and skips the rest of the cycle, and then does the
    same on the NEXT cycle, and every cycle after. Nothing raises, so the
    supervisor never counts a failure, so nothing gives up and nothing
    restarts: the engine keeps producing events, which means `engine_silent`
    stays quiet too. An engine can sit like that indefinitely looking busy.

    Whether a body that cannot be respawned should END the run is a design
    question (PLAN item 15), not something to settle at midnight -- so this
    makes it visible, which is the response §4 allows without asking.
    """
    recent = ctx.recent(RECENT_H)
    failed = [r for r in recent
              if r.get("kind") == "body_respawn" and not r.get("ok")]
    body_errors = [r for r in recent if r.get("kind") == "error"
                   and r.get("where") == "body"]
    if failed:
        return Finding("body_unrecoverable", ALARM,
                       "the body stopped answering and could NOT be respawned "
                       "%d time(s) in %dh -- nothing raises on this, so the "
                       "loop will keep going and neither `gave_up` nor "
                       "`engine_silent` will fire"
                       % (len(failed), RECENT_H),
                       {"ts": [_ts(r) for r in failed],
                        "body_errors": len(body_errors)},
                       scar="if a hand had to intervene, the kernel was missing "
                            "a bound")
    if len(body_errors) >= 3:
        return Finding("body_unrecoverable", ALARM,
                       "%d cycles in %dh ended on a body error -- the body is "
                       "not coming back" % (len(body_errors), RECENT_H),
                       {"n": len(body_errors)},
                       scar="if a hand had to intervene, the kernel was missing "
                            "a bound")
    respawned = [r for r in recent
                 if r.get("kind") == "body_respawn" and r.get("ok")]
    if respawned:
        return Finding("body_unrecoverable", INFO,
                       "the body was respawned %d time(s) in %dh and came back"
                       % (len(respawned), RECENT_H), human=False)
    return Finding("body_unrecoverable", OK,
                   "the body has not needed respawning in %dh" % RECENT_H)


# ------------------------------------------------- is the manager honest?

# The census is cheap and the window is generous: a fabricated complaint is
# rare, and an old one is still worth seeing because nothing else will ever
# report it.
CENSUS_LOOKBACK_H = 24


def complaint_fidelity(ctx):
    """Does the cousin's testimony describe events the kernel recorded?

    `census.py` has existed since 2026-09-12 as the answer to CLAUDE.md
    §6.1 -- *nothing else checks the manager* -- and **nothing ever ran it on
    a schedule.** It reported when a human typed it, which is the dead-channel
    scar in a new costume: a channel nothing routes to is dead however
    carefully it was built. This routes to it.

    The rules stay in `census.check`. Re-stating them here would be a producer
    and a checker each carrying their own copy, which is how `wants()` and the
    context writer drifted in one afternoon.

    **A HIGH is the only thing that reaches a human**, because a HIGH is a
    verdict describing an event that did not happen -- the exact fault this
    design exists to prevent, committed by the agent meant to catch it. LOW
    and MED are worth reading and are not worth waking anyone for: "never
    names the tool it ran" is a style, not a lie.

    Like the census itself, this REPORTS and never gates. A census that can
    block a cycle is a second judge with no judge of its own.

    **What it inherits, stated rather than discovered later.** An independent
    verification on 2026-09-16 constructed both halves:

    - *False negatives.* Census's exit-code regex matches `exit[ed with] N`
      and nothing else, so *"returned 3"* and *"exit status 3"* pass; and
      nothing compares claimed OUTPUT against recorded stdout. A cousin that
      accepts a bare usage line while describing an invocation it never made
      -- the live shape of 2026-09-15 -- reads as OK here.
    - *False positives.* The crash words are hunted as literals with no
      negation handling, so *"ran with no traceback and no crash"* trips
      HIGH. Zero HIGH findings exist in 159 real verdicts, so this has never
      fired in anger, but the runbook line carries the caution for when it
      does: read the verdict and its probe together before believing it.

    Both belong to `census.check`, not here, and fixing them changes the only
    instrument that watches the manager -- so it needs its own before/after
    rather than a patch smuggled in behind a wiring change.
    """
    import sys as _sys
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if here not in _sys.path:
        _sys.path.insert(0, here)
    try:
        import census
    except Exception as e:                      # noqa: BLE001 -- reported
        return Finding("complaint_fidelity", CANNOT_TELL,
                       "census is not importable: %s: %s" % (type(e).__name__, e))
    # Paired over the WHOLE tail and filtered afterwards. Pairing inside the
    # window alone would orphan any verdict whose probe fell just outside it
    # and report "judged work it was never shown running" about a probe that
    # is simply older than the window -- a checker manufacturing its own
    # finding, which is this project's most expensive shape.
    lo = ctx.now - CENSUS_LOOKBACK_H * 3600
    pairs = [(p, v) for p, v in census.pair_up(ctx.rows) if _ts(v) >= lo]
    # **A PAIR WITH NO PROBE IS NOT A PAIR.** `pair_up` emits `(None, verdict)`
    # for a verdict it could not match, so testing `if not pairs` asked "were
    # there any verdicts", not "was anything actually checked" -- and a window
    # of UNKNOWN verdicts with no probe ever written came back OK, *"none
    # contradicting the record"*, which is precisely the clean bill this
    # branch exists to refuse. Found 2026-09-16 by the independent verifier,
    # who constructed the case rather than reading the code.
    probed = [(p, v) for p, v in pairs if p is not None]
    if not probed:
        return Finding("complaint_fidelity", CANNOT_TELL,
                       "no verdict in %dh had a recorded probe (%d verdict(s) "
                       "seen, none with one) -- that is not a clean bill, it "
                       "means the instrument has never run"
                       % (CENSUS_LOOKBACK_H, len(pairs)), human=False)
    hits = []
    for probe, v in pairs:
        for sev, text in census.check(probe, v):
            hits.append({"severity": sev, "tool": (probe or {}).get("tool"),
                         "finding": text, "ts": _ts(v),
                         "said": (v.get("to_creature") or "")[:120]})
    # COUNT VERDICTS, NOT FINDINGS. One verdict trips two census rules
    # routinely -- a claimed exit code and the word "crashed" travel together
    # in the natural phrasing -- and formatting a count of findings into
    # "%d of %d verdicts" printed `2 of 1 verdicts` on the status page: a
    # clean-looking wrong number rather than an error, which is the oldest
    # fault in this file's §5.
    def verdicts(rows):
        return len(set(h["ts"] for h in rows))
    high = [h for h in hits if h["severity"] == "HIGH"]
    if high:
        h = high[-1]
        return Finding("complaint_fidelity", ALARM,
                       "%d of %d verdicts in %dh describe something the kernel "
                       "did not record -- latest, on `%s`: [HIGH] %s"
                       % (verdicts(high), len(probed), CENSUS_LOOKBACK_H,
                          h["tool"], h["finding"]),
                       {"checked": len(probed), "high": verdicts(high),
                        "hits": hits[-8:]},
                       scar="a fabricated complaint is the fault this design "
                            "exists to prevent, by the agent meant to catch it")
    if hits:
        return Finding("complaint_fidelity", INFO,
                       "%d of %d verdicts in %dh carry a minor discrepancy (%s); "
                       "none describes an event that did not happen"
                       % (verdicts(hits), len(probed), CENSUS_LOOKBACK_H,
                          ", ".join(sorted(set(h["severity"] for h in hits)))),
                       {"checked": len(probed), "hits": hits[-8:]}, human=False)
    # `probed`, NOT `pairs`. The ALARM and INFO branches were corrected to
    # count only verdicts that were actually checkable; this one still
    # counted the probe-less ones as clean -- 1.4's fault surviving in the
    # branch next door, found by the same verifier one pass later.
    unchecked = len(pairs) - len(probed)
    return Finding("complaint_fidelity", OK,
                   "%d verdict(s) in %dh checked against their probe, none "
                   "contradicting the record%s -- evidence of no detected "
                   "fabrication, never evidence of honesty"
                   % (len(probed), CENSUS_LOOKBACK_H,
                      ("; %d had no probe and were not checked" % unchecked)
                      if unchecked else ""))


ALL = (engine_silent, gave_up, unusable_verdicts, commands_lost,
       repeated_failure, want_retired_unacted, want_never_served,
       served_context_contract, tool_vanished, selfcheck_disproven,
       restart_owed, ladder_dry, journal_integrity, twin_pressure,
       deploy_regression, want_repeated, probe_stuck, complaint_fidelity,
       body_unrecoverable, window_reread, creature_said,
       shared_tier_contested, cousin_starved, testimony_repeated)


def run_all(ctx, detectors=ALL):
    """Every detector, every time. One that raises is itself a finding --
    a monitor that dies quietly on one bad record is the fault it watches."""
    out = []
    for d in detectors:
        try:
            got = d(ctx)
        except Exception as e:           # noqa: BLE001 -- reported, not hidden
            out.append(Finding(d.__name__, CANNOT_TELL,
                               "detector raised %s: %s" % (type(e).__name__, e)))
            continue
        out.extend(got if isinstance(got, list) else [got])
    return out


def alarms(findings, human_only=True):
    return [f for f in findings
            if f.state == ALARM and (f.human or not human_only)]
