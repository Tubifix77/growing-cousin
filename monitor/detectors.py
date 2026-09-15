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
    not about a tool just written: a chooser fault, never the creature's.
    Uses `picked_by` where the probe recorded it, the trigger before it
    otherwise."""
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
        return Finding("probe_stuck", ALARM,
                       "its user was sent to `%s` on %d of the last %d visits not "
                       "about a fresh write (picked by: %s) -- a chooser fault in "
                       "the framework, not a fact about the tool"
                       % (tool, n, len(last), dict(hows)),
                       {"tool": tool, "n": n, "of": len(last),
                        "last_ts": _ts(last[-1])},
                       scar="the framework manufactures work and the creature is billed")
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

    def pfail(m):
        p = m["probes"]
        n = p["worked"] + p["asked"] + p["failed"]
        v, _ = derive.share(p["failed"], n)
        return v, n
    (pb, nb), (pa, na) = pfail(mb), pfail(ma)
    rows.append(("probes FAILED / qualified probes", _share_str(pb, nb), _share_str(pa, na)))
    if (pa is not None and na >= REG_PROBE_MIN and pa >= REG_PROBE_FAILED_SHARE
            and (pb is None or pa >= 2 * pb)):
        worse.append("probe failure share %s -> %s" % (_share_str(pb, nb), _share_str(pa, na)))

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


ALL = (engine_silent, gave_up, unusable_verdicts, commands_lost,
       repeated_failure, want_retired_unacted, want_never_served,
       served_context_contract, tool_vanished, selfcheck_disproven,
       restart_owed, ladder_dry, journal_integrity, twin_pressure,
       deploy_regression, want_repeated, probe_stuck)


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
