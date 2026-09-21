#!/usr/bin/env python3
"""status.py -- collect the context, run the detectors, keep the edge log,
write the page.

Everything this writes lands in `<root>/monitor/`:

    status.md     the page, regenerated every run (pulled, so continuous)
    status.json   the same, for a program
    alarms.jsonl  one line per RAISE or CLEAR, never a line between
    state.json    the runner's memory: last states and when each began

It reads the journal, `quota.json`, the STOP file, `systemctl --user show`
and `git`; it writes nothing else, and the unit that runs it makes anything
else impossible (`deploy/cousin-monitor.service`). Nothing here reaches
either inhabitant.
"""
import io
import json
import os
import subprocess
import time

from . import derive, detectors

MON_DIR = "monitor"
STATUS_MD = "status.md"
STATUS_JSON = "status.json"
ALARMS = "alarms.jsonl"
STATE = "state.json"
ALARM_FILE = "ALARM"

# THREE OUTCOMES, NEVER TWO. Until 2026-09-15 the monitor exited 1 whenever an
# alarm needed a human, and the unit's own comment claimed that made
# `systemctl --user --failed` "say exactly when to look". It said no such
# thing: a unit sitting in `failed` is indistinguishable from one whose script
# crashed, so the signal answered "is something wrong?" with the same face for
# "the engine has a problem" and "your instrument is dead". Tue read it, at a
# glance, as *the monitor is not running* -- which is the correct reading of
# that signal, and the fifth time in this project a checker could not
# distinguish the thing it measures.
#
# So: 0 nothing needs a human, 1 the monitor RAN and something needs a human
# (the unit declares this a success -- see SuccessExitStatus in
# `deploy/cousin-monitor.service`), 2 the monitor itself broke, which is the
# only thing that may ever put the unit in `failed`.
EXIT_OK = 0
EXIT_ALARM = 1
EXIT_BROKEN = 2

ENGINE_UNIT = "cousin-engine.service"
UNITS = ("cousin-engine.service", "cousin-observer.service",
         "cousin-vitals.timer", "cousin-monitor.timer",
         # NOT ours, and read for exactly that reason: the free tier is
         # shared with it (CLAUDE.md §4), so its state is a condition of
         # every measurement taken here. Read-only, always -- §2.6 makes
         # writing to the sibling a hard boundary.
         detectors.SPINE_UNIT)

# The settled answers from CLAUDE.md §0, keyed by detector, so an alarm
# arrives with its runbook line and nobody re-derives the trap at 03:00.
RUNBOOK = {
    "engine_silent": "Check `systemctl --user status cousin-engine` and the tail "
                     "of live/engine.log. A flat think count with loop_waiting "
                     "climbing is WEATHER, but silence is not: waits are "
                     "journalled too.",
    "gave_up": "Read the last loop_end reason. Five consecutive failures or 600 "
               "waits; systemd retries 5x/30min then leaves it failed. Fix the "
               "cause, then `systemctl --user reset-failed cousin-engine` and start.",
    "unusable_verdicts": "Read finish / chars_before_strip / chars_stripped on the "
                         "UNKNOWN verdicts BEFORE touching a budget. The cousin "
                         "ladder rejects and falls through since 2026-09-13; if "
                         "one rung reasons past its budget the fix is per-rung.",
    "commands_lost": "Compare the creature's raw think against what ran. A tagged "
                     "marker with no parsed block is OUR parser losing work. After "
                     "any parser change, hunt for its cost within the hour.",
    "repeated_failure": "Twelve identical SyntaxErrors were the fence bug, not the "
                        "creature. Diff the raw think against the file on disk "
                        "before reading this as its bug. Never tell it (§2.4).",
    "want_retired_unacted": "The channel retired direction before its recipient "
                            "acted: see Engine.want_was_acted_on (17d8951).",
    "want_never_served": "record_want writes context.md; serve_context reads it. "
                         "Check the file and the wake's wants_served.",
    "served_context_contract": "Every tool must at least be NAMED on the page; the "
                               "full-entry limit (library.LIBRARY_LIMIT) may compact "
                               "the tail but never hide it. Read the last wake's "
                               "library_shown / library_named / library_total.",
    "want_repeated": "Read the last five wants and the probes behind their accepts. "
                     "A want the cousin cannot verify (bare probe) or whose answers "
                     "it cannot see (hidden tool) repeats forever; the fix is in the "
                     "framework's probe or listing, never in the creature. AND since "
                     "the cousin has hands (item 9): grep the probes' `cmd` for the "
                     "thing it keeps asking for. On 2026-09-17 `plan set-deadline` "
                     "existed and had never once been run by the cousin that asked "
                     "for deadlines four times -- it ran `plan` bare, accepted the "
                     "menu, and asked again. That half is the brief's (item 16).",
    "testimony_repeated": "The brief's own test for a form: the sentence would fit any "
                          "tool. Read the probes behind the identical verdicts -- if "
                          "they are bare calls to a menu, the cousin judged on nothing "
                          "it exercised, and the rule that lets it accept a usage "
                          "refusal was written for the harness's empty hands, not for "
                          "its own (PLAN item 16). Never edit a verdict (§2.2).",
    "window_reread": "This is the SYMPTOM that would reopen PLAN item 13 (the "
                     "output window), not proof of it. Read the raw "
                     "thinks: is it re-reading because it cannot see the whole "
                     "file, or for its own reasons? A cap changed without a "
                     "before/after across several windows, split by rung, is "
                     "superstition (§5).",
    "body_unrecoverable": "Stop the bleeding first -- that is not an intervention "
                          "(§1.2). Check whether the creature removed its own "
                          "$MIND; `LocalBody.respawn` does not rebuild the tree, "
                          "and nothing raises, so the loop will sit there. PLAN "
                          "item 15 is whether that should end the run.",
    "complaint_fidelity": "Read the verdict and its probe TOGETHER before concluding "
                          "the cousin was wrong -- the harness has invented faults "
                          "before, and `census.py --root live` prints both. Never "
                          "edit a verdict (§2.2): it is testimony, and rewriting it "
                          "makes this census meaningless.",
    "probe_stuck": "READ `picked_by` FIRST, and the alarm line now quotes it: "
                   "`least_probed` sitting on one tool is a chooser fault "
                   "(Engine.choose_target has had no default since "
                   "2026-09-15); `ran` means the CREATURE invoked it that "
                   "cycle and the chooser followed, which is not a fault at "
                   "all. This runbook used to say the opposite -- anything "
                   "but least_probed is a chooser fault -- and sent readers "
                   "hunting one that was not there.",
    "shared_tier_contested": "The sibling project shares this free tier "
                             "(CLAUDE.md §4), so its state is a condition of "
                             "every figure taken here. If this is ALARM, the "
                             "document and the machine disagree: either "
                             "correct §4 or stop the spine. Whether it RUNS "
                             "is Tue's standing decision and PLAN item 12 is "
                             "his call -- this reports, and never acts.",
    "cousin_starved": "The cousin's calls are failing where the creature's "
                      "are not, so this is NOT the free tier. Read the "
                      "`error` on a lost probe: on 2026-09-16 every one said "
                      "`unusable: no-block` because the command-choosing call "
                      "was asked through the ladder that demands a VERDICT "
                      "block. Check the predicate, the budget and the prompt "
                      "of the cousin's call before suspecting the rungs.",
    "tool_vanished": "A body/PATH fault, not the creature: the relative-root scar. "
                     "Check PathBody.run's PATH export and that the root is absolute.",
    "selfcheck": "A bound this deployment relies on does NOT hold. Read the "
                 "selfcheck record; the unit's sandbox needs PrivateUsers=yes to "
                 "do anything at all.",
    "journal_integrity": "Never repair the journal in place from here. Look at the "
                         "bad lines; a crash mid-append is the usual cause.",
    "deploy_regression": "One hour is one window; read the table in "
                         "live/monitor/regression/ and the raw thinks behind the "
                         "indicator that moved BEFORE reverting anything. A "
                         "correctness fault is fixed on sight; a tuning change "
                         "needs several windows, split by rung.",
    "deploy_regression_day": "The same table a DAY after the start, because the "
                             "hour is honest and short: on 2026-09-17 the read "
                             "caps cost the creature half its commands and the "
                             "hour after reported nothing moved, correctly, "
                             "since the cost needed its next whole-tool rewrite "
                             "to arrive. Read this one before believing the "
                             "hour's silence. Same rule after it: a correctness "
                             "fault is fixed on sight, a tuning change needs "
                             "several windows split by rung.",
}


# --------------------------------------------------------------- collect

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    return r if r.returncode == 0 else None


def systemd_show(unit, props):
    r = _run(["systemctl", "--user", "show", unit, "-p", ",".join(props)])
    if r is None:
        return None
    out = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out or None


def git_head(repo):
    r = _run(["git", "-C", repo, "rev-parse", "HEAD"])
    return r.stdout.strip() if r and r.stdout.strip() else None


def git_changed(repo):
    """A function `(a, b) -> [paths]` or None where it cannot be answered."""
    def changed(a, b):
        r = _run(["git", "-C", repo, "--no-optional-locks", "diff",
                  "--name-only", "%s..%s" % (a, b)])
        return None if r is None else [p for p in r.stdout.splitlines() if p]
    return changed


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def collect(root, repo=None, now=None):
    rows, complete, bad = derive.load(os.path.join(root, "journal.jsonl"))
    unit = systemd_show(ENGINE_UNIT, ["ActiveState", "SubState", "NRestarts",
                                      "ExecMainStartTimestamp", "Result"])
    ctx = detectors.Context(
        rows, now=now, unit=unit,
        repo_head=git_head(repo) if repo else None,
        repo_changed=git_changed(repo) if repo else None,
        quota=read_json(os.path.join(root, "quota.json")),
        stop_present=os.path.exists(os.path.join(root, "STOP")),
        complete=complete, bad=bad)
    ctx.root, ctx.repo = root, repo
    ctx.units = {u: systemd_show(u, ["ActiveState", "SubState", "LastTriggerUSec",
                                     "NextElapseUSecRealtime",
                                     "ExecMainStartTimestamp"]) for u in UNITS}
    # DERIVED FROM THE DOCTRINE FILE, never typed here. The whole point of
    # `shared_tier_contested` is that the document and the machine can
    # disagree; a constant in this file saying what the document says would
    # be a third thing to drift.
    ctx.doctrine_says_paused = doctrine_says_spine_paused(repo)
    return ctx


def doctrine_says_spine_paused(repo):
    """Does CLAUDE.md §4 currently claim the spine is paused?

    Deliberately a plain search for the sentence the file actually uses, and
    deliberately returning False when the file cannot be read: an unreadable
    document is not a claim, and inventing one would make the detector fire
    on a checkout that has no doctrine in it.
    """
    if not repo:
        return False
    try:
        with io.open(os.path.join(repo, "CLAUDE.md"), encoding="utf-8") as f:
            return "SPINE IS PAUSED" in f.read()
    except OSError:
        return False


# ----------------------------------------------------------------- edges

def edges(findings, prev_states, prev_since, now):
    """Compare against the last run. A line is written only when a name
    ENTERS or LEAVES ALARM; OK/INFO/CANNOT_TELL churn is not news."""
    states = {f.name: f.state for f in findings}
    since = {}
    changes = []
    for f in findings:
        was = prev_states.get(f.name)
        since[f.name] = prev_since.get(f.name, now) if was == f.state else now
        if f.state == detectors.ALARM and was != detectors.ALARM:
            changes.append({"ts": now, "name": f.name, "from": was or "(new)",
                            "to": f.state, "msg": f.msg, "evidence": f.evidence,
                            "human": f.human})
        elif was == detectors.ALARM and f.state != detectors.ALARM:
            changes.append({"ts": now, "name": f.name, "from": was,
                            "to": f.state, "msg": f.msg, "human": f.human})
    for name, was in prev_states.items():
        if name not in states and was == detectors.ALARM:
            changes.append({"ts": now, "name": name, "from": was, "to": "GONE",
                            "msg": "no longer reported", "human": True})
    return states, since, changes


# ------------------------------------------------------------------ data

class _Rows:
    """The one adapter the library renderer needs: `.read(kinds=...)`."""

    def __init__(self, rows):
        self.rows = rows

    def read(self, kinds=None, since_ts=None, limit=None):
        out = [r for r in self.rows if not kinds or r.get("kind") in kinds]
        return out[-limit:] if limit else out


def _windows(ctx):
    """The windows every figure is reported over, each naming its engine."""
    wins = [("last hour", ctx.now - 3600, None),
            ("last 6 hours", ctx.now - 6 * 3600, None)]
    if ctx.last_start is not None:
        wins.append(("since start %s" % derive.ts_str(float(ctx.last_start["ts"]), "%m-%d %H:%M"),
                     float(ctx.last_start["ts"]), None))
    out = []
    starts = derive.starts(ctx.rows)
    for label, lo, hi in wins:
        rows = derive.window(ctx.rows, lo, hi)
        before = [s for s in starts if float(s["ts"]) <= lo]
        inside = [s for s in starts if lo < float(s["ts"]) < (hi or float("inf"))]
        engines = sorted(set((s.get("engine") or "unknown")[:7]
                             for s in (before[-1:] + inside)))
        m = derive.measure(rows)
        m["label"] = label
        m["from"] = lo
        m["engines"] = engines or ["unknown"]
        out.append(m)
    return out


def _latest(ctx, kind, n=3):
    return [r for r in ctx.rows if r.get("kind") == kind][-n:]


def build_data(ctx, findings, since, changes):
    from kernel import library as librarymod
    hist = librarymod.use_history(_Rows(ctx.rows))
    record = []
    for name in sorted(ctx.library):
        rec = hist.get(name)
        record.append({"tool": name, "runs": (rec or {}).get("runs", 0),
                       "worked": (rec or {}).get("ok", 0),
                       "asked": (rec or {}).get("asked", 0),
                       "unqualified": (rec or {}).get("unqualified", 0),
                       "nonzero": (rec or {}).get("nonzero", 0),
                       "accepted": (rec or {}).get("accepted", 0),
                       "returned": (rec or {}).get("returned", 0),
                       "last_code": (rec or {}).get("last_code")})
    fam = derive.stems(ctx.library)
    # The headline metric reads the library on disk for its edges, so it is
    # given the creature's real tools directory rather than the journal's
    # idea of one.
    # The probes are read from the WHOLE file rather than from `ctx.rows`,
    # which is a tail: this metric is a span of days and a byte bound silently
    # shortens it. `complete` is passed too, so that if the file cannot be read
    # at all the answer degrades to CANNOT TELL instead of to a smaller number.
    jpath = os.path.join(ctx.root, "journal.jsonl")
    probes = derive.probe_history(jpath)
    surviving = derive.surviving_capability(
        ctx.rows,
        os.path.join(ctx.root, "body", "mind", "tools", "own"),
        now=getattr(ctx, "now", None),
        complete=ctx.complete, probes=probes,
        run_start=derive.first_ts(jpath) if probes is not None else None)
    last = ctx.rows[-1] if ctx.rows else None
    return {
        "generated": ctx.now,
        "journal": {"events": len(ctx.rows), "complete": ctx.complete,
                    "bad_lines": ctx.bad,
                    "last_event_ts": float(last["ts"]) if last else None,
                    "last_event_kind": last.get("kind") if last else None},
        "engine": {"running": (ctx.last_start or {}).get("engine"),
                   "dirty": (ctx.last_start or {}).get("dirty"),
                   "started": float(ctx.last_start["ts"]) if ctx.last_start else None,
                   "repo_head": ctx.repo_head,
                   "unit": ctx.unit, "stop_present": ctx.stop_present},
        "units": getattr(ctx, "units", {}),
        "findings": [dict(f.as_dict(), since=since.get(f.name)) for f in findings],
        "changes": changes,
        "windows": _windows(ctx),
        "quota": ctx.quota,
        "surviving": surviving,
        "library": {"tools": len(ctx.library),
                    "families": {s: len(v) for s, v in fam.items() if len(v) >= 3},
                    # §6.2's binding requirement: every metric split on the
                    # inheritance tag. None when the run inherited nothing,
                    # which is a fact rather than a gap -- see
                    # derive.provenance.
                    "provenance": derive.provenance(getattr(ctx, "root", None),
                                                    ctx.library),
                    "record": record},
        "latest": {
            "wants": [{"ts": r["ts"], "text": (r.get("text") or "")[:160]}
                      for r in _latest(ctx, "cousin_want")],
            "verdicts": [{"ts": r["ts"], "rung": r.get("rung"),
                          "verdict": r.get("verdict"), "error": r.get("error"),
                          "said": (r.get("to_creature") or "")[:160]}
                         for r in _latest(ctx, "cousin_verdict")],
            "skips": [{"ts": r["ts"], "reason": r.get("reason"), "lost": r.get("lost")}
                      for r in _latest(ctx, "exec_skip")],
            "tools_changed": [{"ts": r["ts"], "added": r.get("added"),
                               "removed": r.get("removed")}
                              for r in _latest(ctx, "tools_changed")],
            "selfcheck": ctx.last("selfcheck"),
            "wake": ctx.last("wake"),
        },
    }


# ---------------------------------------------------------------- render

def render_surviving(s):
    """`ARCHITECTURE.md` 12's headline, rendered so the three states survive
    the trip. The count of survivors is meaningless without the count of
    things that cannot be judged yet, so they are printed together or not at
    all."""
    out = []
    if not s:
        return out
    out.append("## Surviving capability (ARCHITECTURE 12's headline metric)")
    out.append("")
    out.append("*Tools that start, are invoked by something else, and are "
               "still invoked %d days later.* Run is %.1f days old."
               % (s["window_days"], s["run_days"]))
    out.append("")
    out.append("| survived | has not | cannot tell yet |")
    out.append("|---|---|---|")
    out.append("| **%d** | %d | %d |"
               % (s["surviving"], s["not_surviving"], s["cannot_tell"]))
    out.append("")
    out.append("Leading indicators, true before the window elapses: "
               "**%d** tool(s) their user has reached for more than once, and "
               "the widest first-to-last span so far is **%.1f days**."
               % (s.get("reused", 0), s.get("widest_span_days", 0.0)))
    out.append("")
    yes = [t for t in s["tools"] if t["surviving"] is True]
    if yes:
        out.append("Survived: " + ", ".join(
            "`%s` (named by %d, used %d times over %.1f days)"
            % (t["tool"], t["named_by"], t["runs"], t["span_days"])
            for t in sorted(yes, key=lambda t: -(t["span_days"] or 0))[:10]))
        out.append("")
    dead = [t for t in s["tools"] if t["started"] is False]
    if dead:
        out.append("Did not start when its user ran it: "
                   + ", ".join("`%s`" % t["tool"] for t in dead[:10]))
        out.append("")
    out.append("**Cannot tell:** %s." % (s["why_cannot_tell"] or
                                         "nothing -- every tool could be judged"))
    out.append("")
    out.append("_The middle bar is **someone other than the AUTHOR ran it**, "
               "which here means the cousin -- not `another tool names it`, "
               "because a tool called by its author's own other tools is still "
               "single-occupancy. Composition is shown beside it as context. "
               "And surviving this bar means its user kept coming back, which "
               "is NOT the same as doing what its header claims: that is the "
               "verdict's job, not this page's._")
    out.append("")
    return out


def _pct(num, den):
    v, note = derive.share(num, den)
    return "-" if v is None else "%.0f%% (%s)" % (100 * v, note)


def render_md(d):
    now = d["generated"]
    j, e = d["journal"], d["engine"]
    out = ["# Growing Cousin -- status", ""]
    out.append("generated %s local. Journal: %d events%s%s; last event `%s` %s ago."
               % (derive.ts_str(now), j["events"],
                  "" if j["complete"] else " (TAIL ONLY -- the file's start was not read)",
                  (", %d unparseable line(s)" % j["bad_lines"]) if j["bad_lines"] else "",
                  j["last_event_kind"],
                  derive.fmt_age(now - j["last_event_ts"]) if j["last_event_ts"] else "?"))
    unit = e.get("unit") or {}
    out.append("engine `%s`%s, started %s; repo HEAD `%s`; unit %s/%s, restarts %s%s."
               % ((e.get("running") or "unknown")[:7],
                  " **DIRTY TREE**" if e.get("dirty") else "",
                  derive.ts_str(e["started"], "%m-%d %H:%M") if e.get("started") else "?",
                  (e.get("repo_head") or "?")[:7],
                  unit.get("ActiveState", "?"), unit.get("SubState", "?"),
                  unit.get("NRestarts", "?"),
                  "; **STOP file present**" if e.get("stop_present") else ""))
    out.append("")

    fs = d["findings"]
    alarms = [f for f in fs if f["state"] == detectors.ALARM]
    cannot = [f for f in fs if f["state"] == detectors.CANNOT_TELL]
    infos = [f for f in fs if f["state"] == detectors.INFO]
    oks = [f for f in fs if f["state"] == detectors.OK]

    out.append("## Alarms (%d)" % len(alarms))
    out.append("")
    if not alarms:
        out.append("None. (%d OK, %d cannot tell, %d informational.)"
                   % (len(oks), len(cannot), len(infos)))
    for f in alarms:
        key = f["name"].split("[")[0]
        out.append("- **%s** -- %s  _(since %s%s)_"
                   % (f["name"], f["msg"],
                      derive.ts_str(f["since"], "%m-%d %H:%M") if f.get("since") else "?",
                      "" if f.get("human") else ", informational"))
        if f.get("scar"):
            out.append("  - scar: %s" % f["scar"])
        rb = RUNBOOK.get(key)
        if rb:
            out.append("  - runbook: %s" % rb)
    out.append("")
    if d["changes"]:
        out.append("### Changed this run")
        out.append("")
        for c in d["changes"]:
            out.append("- %s: %s -> **%s** -- %s" % (c["name"], c["from"], c["to"], c["msg"]))
        out.append("")
    if cannot:
        out.append("## Cannot tell (%d)" % len(cannot))
        out.append("")
        for f in cannot:
            out.append("- %s -- %s" % (f["name"], f["msg"]))
        out.append("")
    if infos:
        out.append("## Informational (%d)" % len(infos))
        out.append("")
        for f in infos:
            out.append("- %s -- %s" % (f["name"], f["msg"]))
        out.append("")

    # EACH reading its own section, in a fixed order, and only the ones that
    # actually have a table. Taking `reg[0]` broke the moment a second reading
    # existed: whichever the registry listed first won, and a pending one with
    # no table suppressed the other's section outright. A position in a list is
    # never a reason.
    by_name = {}
    for f in fs:
        if f["name"] in ("deploy_regression", "deploy_regression_day"):
            by_name[f["name"]] = f
    for nm, span in (("deploy_regression", "hour"),
                     ("deploy_regression_day", "day")):
        f = by_name.get(nm)
        ev = (f or {}).get("evidence", {}) or {}
        if not ev.get("table"):
            continue
        out.append("## Deploy regression (%s) -- engine `%s` against `%s`"
                   % (span, ev.get("engine"), ev.get("before_engine")))
        out.append("")
        out.append(f["msg"])
        out.append("")
        out.append("| indicator | %s before | %s after |" % (span, span))
        out.append("|---|---|---|")
        for label, b, a in ev["table"]:
            out.append("| %s | %s | %s |" % (label, b, a))
        out.append("")
        out.append("_Written once to `monitor/regression/`. One window is an "
                   "anecdote; a direction that survives several is a signal._")
        out.append("")

    out.append("## Ladder (weather, not fault)")
    out.append("")
    q = d.get("quota") or {}
    if q:
        out.append("| rung | last success | last fail | skipping until |")
        out.append("|---|---|---|---|")
        for rung, st in sorted(q.items()):
            st = st or {}
            until = (st.get("since") or 0) + (st.get("skip") or 0)
            out.append("| `%s` | %s | %s | %s |" % (
                rung,
                derive.ts_str(st.get("last_success"), "%m-%d %H:%M") if st.get("last_success") else "never",
                derive.ts_str(st.get("last_fail"), "%m-%d %H:%M") if st.get("last_fail") else "-",
                derive.ts_str(until, "%H:%M") if st.get("skip") and until > now else "-"))
    else:
        out.append("(no quota.json readable)")
    out.append("")

    out.append("## Counts, per window (every figure names its engine)")
    out.append("")
    hdr = ["", ] + ["%s (%s)" % (w["label"], "/".join(w["engines"])) for w in d["windows"]]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))

    def row(label, fn):
        out.append("| %s | %s |" % (label, " | ".join(str(fn(w)) for w in d["windows"])))
    row("wakes / thinks / commands", lambda w: "%d / %d / %d" % (w["wakes"], w["thinks"], w["commands"]))
    row("commands ok / failed", lambda w: "%d / %d" % (w["cmd_ok"], w["cmd_failed"]))
    row("commands LOST (skips)", lambda w: "%d  %s" % (w["commands_lost"], w["skips"] or ""))
    row("probes exited 0 / asked for args / exited non-zero (args its user "
        "chose) / unqualified / lost",
        lambda w: "%(worked)d / %(asked)d / %(nonzero)d / %(unqualified)d"
                  " / %(lost)d" % w["probes"])
    row("verdicts", lambda w: w["verdicts"])
    row("wants (distinct)", lambda w: "%d (%d)" % (w["wants"], w["wants_distinct"]))
    row("tool writes new / edit", lambda w: "%d / %d" % (w["tool_writes_new"], w["tool_writes_edit"]))
    row("tools added / removed", lambda w: "%d / %d" % (w["tools_added"], w["tools_removed"]))
    row("rungs declined (expected) / BROKEN", lambda w: "%d / %d" % (w["rung_declined"], w["rung_broken"]))
    row("waits / thinks deferred / visits deferred",
        lambda w: "%d / %d / %d" % (w["waits"], w["think_deferred"], w["visit_deferred"]))
    out.append("")
    out.append("### Verdicts by rung (an aggregate over rungs measures nothing)")
    out.append("")
    for w in d["windows"]:
        if not w["verdicts_by_rung"]:
            continue
        out.append("**%s**" % w["label"])
        out.append("")
        for rung, c in sorted(w["verdicts_by_rung"].items()):
            total = sum(c.values())
            out.append("- `%s`: %d -- ACCEPTED %d, RETURNED %d, UNKNOWN %d%s"
                       % (rung, total, c.get("ACCEPTED", 0), c.get("RETURNED", 0),
                          c.get("UNKNOWN", 0),
                          (" (%s)" % w["unknown_by_rung"].get(rung)) if w["unknown_by_rung"].get(rung) else ""))
        out.append("")
    out.append("### Thinks by rung and finish")
    out.append("")
    for w in d["windows"]:
        if w["thinks_by_rung_finish"]:
            out.append("- %s: %s" % (w["label"], ", ".join(
                "%s %d" % (k, n) for k, n in sorted(w["thinks_by_rung_finish"].items()))))
    out.append("")

    lib = d["library"]
    out.extend(render_surviving(d.get("surviving")))

    out.append("## Library (%d tools the journal knows of)" % lib["tools"])
    out.append("")
    # EVERY METRIC SPLIT ON THE TAG (§6.2). Stated in words either way,
    # because "nothing was inherited" and "nobody checked" must never render
    # the same.
    prov = lib.get("provenance")
    if prov is None:
        out.append("Provenance: **everything here was built in this run** --"
                   " no inherited library was seeded, so no count below is a"
                   " mixture.")
    else:
        out.append("Provenance: **%d of %d inherited** at t=0 from `%s`"
                   " (%d tagged); built here %d; of the inherited, %d"
                   " modified, %d repaired, %d broke, %d renamed, %d deleted."
                   % (prov.get("inherited", 0), lib["tools"],
                      prov.get("seeded_from") or "?",
                      prov.get("tagged_at_seed", 0), prov.get("built", 0),
                      prov.get("modified", 0), prov.get("repaired", 0),
                      prov.get("broke", 0), prov.get("renamed", 0),
                      prov.get("deleted", 0)))
        out.append("")
        out.append("**Split every rate below on that line before reading it**"
                   " -- an aggregate over an inherited library and a built one"
                   " measures neither.")
    out.append("")
    if lib["families"]:
        inh = (prov or {}).get("families_inherited") or {}
        out.append("Families of 3+: " + ", ".join(
            "`%s-*` x%d%s" % (s, n,
                              (" (%d inherited)" % inh[s]) if inh.get(s) else "")
            for s, n in sorted(lib["families"].items(), key=lambda x: -x[1])))
        out.append("")
    ran = [r for r in lib["record"] if r["runs"]]
    if ran:
        # "non-zero", not "FAILED": with arguments the cousin chose, the exit
        # code is a fact and the failure is a judgement -- the judgement is
        # in the last two columns, as the cousin actually gave it.
        out.append("| tool | runs by its user | exited 0 | asked for args | exited non-zero (args its user chose) | unqualified | accepted | returned | last exit |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for r in sorted(ran, key=lambda r: (-r["returned"], -r["nonzero"], -r["runs"], r["tool"])):
            out.append("| `%s` | %d | %d | %d | %s | %d | %d | %s | %s |" % (
                r["tool"], r["runs"], r["worked"], r["asked"],
                ("**%d**" % r["nonzero"]) if r["nonzero"] else "0", r["unqualified"],
                r["accepted"],
                ("**%d**" % r["returned"]) if r["returned"] else "0",
                r["last_code"]))
        never = [r["tool"] for r in lib["record"] if not r["runs"]]
        if never:
            out.append("")
            out.append("Never run by its user: " + ", ".join("`%s`" % n for n in never))
    out.append("")

    L = d["latest"]
    out.append("## Latest")
    out.append("")
    for w in L["wants"]:
        out.append("- want %s: %s" % (derive.ts_str(w["ts"], "%m-%d %H:%M"), w["text"]))
    for v in L["verdicts"]:
        out.append("- verdict %s: **%s** via `%s`%s -- %s" % (
            derive.ts_str(v["ts"], "%m-%d %H:%M"), v["verdict"], v.get("rung"),
            (" (%s)" % v["error"]) if v.get("error") else "", v["said"] or "(no message)"))
    for s in L["skips"]:
        out.append("- skip %s: %s%s" % (derive.ts_str(s["ts"], "%m-%d %H:%M"), s["reason"],
                                        " (COMMANDS LOST)" if s.get("lost") else ""))
    for t in L["tools_changed"]:
        out.append("- tools %s: +%s -%s" % (derive.ts_str(t["ts"], "%m-%d %H:%M"),
                                            t.get("added") or [], t.get("removed") or []))
    w = L.get("wake") or {}
    if w:
        out.append("- last wake %s: %s" % (derive.ts_str(w["ts"], "%m-%d %H:%M"),
                                          ", ".join("%s=%s" % (k, v) for k, v in sorted(w.items())
                                                    if k not in ("ts", "kind"))))
    sc = L.get("selfcheck") or {}
    if sc:
        out.append("- selfcheck %s: %s" % (derive.ts_str(sc["ts"], "%m-%d %H:%M"),
                                          ", ".join("%s=%s" % (k, v) for k, v in sorted(sc.items())
                                                    if k not in ("ts", "kind"))))
    out.append("")
    out.append("## Units")
    out.append("")
    for u, st in sorted((d.get("units") or {}).items()):
        if st is None:
            out.append("- %s: (not readable from here)" % u)
        else:
            out.append("- %s: %s/%s%s" % (u, st.get("ActiveState"), st.get("SubState"),
                                         (" last %s" % st.get("LastTriggerUSec")) if st.get("LastTriggerUSec") and st.get("LastTriggerUSec") != "n/a" else ""))
    out.append("")
    out.append("_Counts and ratios only; nothing here is a judgement. A ratio over "
               "fewer than %d events is labelled an anecdote. Written by "
               "`python3 -m monitor status`; never edit by hand._" % derive.SMALL_N)
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------- run

def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


REGRESSION_DIR = "regression"


def regression_report_path(mon, finding):
    ev = finding.evidence
    # The DAY reading writes beside the hour's rather than over it: two
    # readings of the same start are two pieces of evidence, and evidence that
    # overwrites evidence is not evidence (PLAN 21.3).
    suffix = "-day" if finding.name.endswith("_day") else ""
    return os.path.join(mon, REGRESSION_DIR, "%s-%s%s.md"
                        % (ev.get("engine", "unknown"),
                           derive.ts_str(ev["start_ts"], "%Y%m%d-%H%M"), suffix))


def write_regression_report(mon, finding):
    """The before/after table for one start, written ONCE and never
    rewritten -- the comparison is evidence about that hour, and evidence
    that changes when re-read is not evidence. Returns whether it wrote."""
    ev = finding.evidence
    # `span_complete` since 2026-09-21; `hour_complete` is still accepted
    # because a monitor reading an older journal's finding must not silently
    # stop writing reports. Two names, one meaning, and the old one is read
    # rather than assumed absent.
    if not (ev.get("span_complete") or ev.get("hour_complete")) or not ev.get("table"):
        return False
    path = regression_report_path(mon, finding)
    if os.path.exists(path):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["# Deploy regression -- engine `%s` started %s, against `%s`"
             % (ev.get("engine"), derive.ts_str(ev["start_ts"]), ev.get("before_engine")),
             "",
             "The hour after the start against the hour before it. Correctness "
             "indicators only -- the class that is wrong for any model. Floors "
             "are declared in `monitor/detectors.py` with the measurement behind "
             "each.", "",
             "**%s: %s**" % (finding.state, finding.msg), "",
             "| indicator | hour before (`%s`) | hour after (`%s`) |"
             % (ev.get("before_engine"), ev.get("engine")),
             "|---|---|---|"]
    for label, b, a in ev["table"]:
        lines.append("| %s | %s | %s |" % (label, b, a))
    lines += ["", "_One hour is one window and this engine is not deterministic. "
                  "A direction that survives several windows is a signal; this "
                  "file is a smoke alarm, and it is written once._", ""]
    write_atomic(path, "\n".join(lines))
    return True


def run_once(root, repo=None, now=None, write=True):
    """One pass. Returns `(markdown, data, exit_code)`; exit 1 means a human
    is needed."""
    ctx = collect(root, repo, now)
    findings = detectors.run_all(ctx)
    mon = os.path.join(root, MON_DIR)
    prev = read_json(os.path.join(mon, STATE)) or {}
    states, since, changes = edges(findings, prev.get("states", {}),
                                   prev.get("since", {}), ctx.now)
    data = build_data(ctx, findings, since, changes)
    md = render_md(data)
    human = detectors.alarms(findings)
    if write:
        os.makedirs(mon, exist_ok=True)
        # THE STANDING STATE, as a file whose PRESENCE is the signal. The edge
        # log says what changed and the page says everything; neither answers
        # "is anything wrong right now?" without being read. This does, to a
        # human glancing at `ls` and to any script, and it is removed the
        # moment the last alarm clears -- so a stale ALARM file cannot outlive
        # what it reports.
        alarm_path = os.path.join(mon, ALARM_FILE)
        if human:
            write_atomic(alarm_path, "".join(
                "%s: %s\n" % (f.name, f.msg) for f in human))
        elif os.path.exists(alarm_path):
            os.remove(alarm_path)
        if changes:
            with open(os.path.join(mon, ALARMS), "a", encoding="utf-8") as f:
                for c in changes:
                    f.write(json.dumps(c, ensure_ascii=False, default=str) + "\n")
        write_atomic(os.path.join(mon, STATE),
                     json.dumps({"states": states, "since": since,
                                 "last_run": ctx.now}, sort_keys=True))
        write_atomic(os.path.join(mon, STATUS_JSON),
                     json.dumps(data, ensure_ascii=False, default=str, indent=1))
        write_atomic(os.path.join(mon, STATUS_MD), md)
        for f in findings:
            if f.name in ("deploy_regression", "deploy_regression_day"):
                write_regression_report(mon, f)
    return md, data, (EXIT_ALARM if human else EXIT_OK)


def replay(rows, step=1, detector_set=None):
    """Run the detectors over a slice as if live, once per `step` rows, and
    return the raise/clear timeline. This is how a detector is proven against
    the hour its scar happened, and how a new one is checked for wolf-crying
    on a healthy hour."""
    prev_states, prev_since, timeline = {}, {}, []
    for i in range(1, len(rows) + 1, step):
        seen = rows[:i]
        ctx = detectors.Context(seen, now=float(seen[-1]["ts"]))
        findings = detectors.run_all(ctx, detector_set or detectors.ALL)
        prev_states, prev_since, changes = edges(findings, prev_states,
                                                 prev_since, ctx.now)
        timeline.extend(changes)
    return timeline
