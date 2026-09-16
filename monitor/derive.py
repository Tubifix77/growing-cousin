#!/usr/bin/env python3
"""derive.py -- indicators from the journal. Counts and ratios of counts,
split by rung, and nothing that is a judgement.

Read-only. The journal is the evidence; this file only folds it. Anything a
detector or the status page says must be reproducible from these functions
and a slice of the journal, which is what `tests/fixtures/journal/` is for.
"""
import collections
import json
import os
import re
import time

# 24 MB of tail is roughly ten days at run 2's 2.5 MB/day. If the tail does
# not reach the start of the file the reader is TOLD (`complete=False`) --
# the spine's rule: a short baseline reported as fact is a wrong number with
# a clean face.
TAIL_BYTES = 24 * 1024 * 1024

# A ratio over fewer events than this is an anecdote and is labelled one.
SMALL_N = 10


def load(path, tail_bytes=TAIL_BYTES):
    """Rows from the END of the journal.

    Returns `(rows, complete, bad)`: whether the file's start was reached,
    and how many lines did not parse -- torn by a crash, or the one line the
    writer is mid-way through. Bad lines are counted, never silently dropped;
    `journal_integrity` reports the count.
    """
    rows, bad, complete = [], 0, True
    try:
        size = os.path.getsize(path)
    except OSError:
        return rows, True, 0
    with open(path, "rb") as f:
        if size > tail_bytes:
            f.seek(size - tail_bytes)
            f.readline()             # discard the partial first line
            complete = False
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                r = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                bad += 1
                continue
            if isinstance(r, dict) and "kind" in r:
                rows.append(r)
            else:
                bad += 1
    return rows, complete, bad


def load_fixture(path):
    """A whole fixture file, for replay. Same parser, no tail."""
    return load(path, tail_bytes=1 << 40)[0]


def window(rows, lo, hi=None):
    hi = float("inf") if hi is None else hi
    return [r for r in rows if lo <= float(r.get("ts", 0)) < hi]


def kinds(rows):
    return collections.Counter(r.get("kind") for r in rows)


def ts_str(ts, fmt="%Y-%m-%d %H:%M:%S"):
    if not ts:
        return "?"
    return time.strftime(fmt, time.localtime(float(ts)))


def fmt_age(secs):
    if secs is None:
        return "?"
    secs = max(0, int(secs))
    if secs < 90:
        return "%ds" % secs
    if secs < 5400:
        return "%dm" % (secs // 60)
    if secs < 172800:
        return "%.1fh" % (secs / 3600.0)
    return "%.1fd" % (secs / 86400.0)


def share(num, den, small=SMALL_N):
    """A ratio that says when it is an anecdote: `(value or None, note)`."""
    if not den:
        return None, "n=0"
    return float(num) / den, ("n=%d, anecdote" % den if den < small
                              else "n=%d" % den)


# ------------------------------------------------------------- the library

def library_from_journal(rows):
    """The set of tools the journal believes exist: a fold over
    `tools_changed`. Derived, so it can be wrong only where the journal is --
    and comparing it against what the kernel says it SERVED is the point."""
    tools = set()
    for r in rows:
        if r.get("kind") == "tools_changed":
            tools |= set(r.get("added") or [])
            tools -= set(r.get("removed") or [])
    return tools


def stems(names):
    """Name -> stem family, so `archive-*` x9 is visible as one number."""
    fam = collections.defaultdict(list)
    for n in sorted(names):
        stem = re.split(r"[-_.]", n, 1)[0].lower()
        fam[stem].append(n)
    return fam


# ------------------------------------------------------------ the commands

FIRST_WORD = re.compile(r"^\s*([A-Za-z0-9_.\-]+)", re.M)
TOOL_PATH_RE = re.compile(r"tools/own/([A-Za-z0-9_.\-]+)")
TOOL_HAND_RE = re.compile(r"\btool-(?:edit|new)\s+['\"]?([A-Za-z0-9_.\-]+)")
TOOL_REDIRECT_RE = re.compile(
    r"(?:>|>>|\btee\b)\s*['\"]?(?:/mind/|\$MIND/|\$\{MIND\}/)?tools/own/"
    r"([A-Za-z0-9_.\-]+)")


def commands_named(cmd):
    """The first word of every line of a block -- what the creature invoked.
    Locale-independent, which matters: the laptop's bash says *kommando ikke
    fundet*, so nothing here ever matches the English text of an error."""
    return set(m.group(1) for m in FIRST_WORD.finditer(cmd or ""))


def tools_written(cmd):
    """Which tools a command writes, through EITHER door: `tool-edit NAME` /
    `tool-new NAME`, or a redirect into `tools/own/NAME`. A count that reads
    only one door undersold the creature's output by half on 2026-09-14."""
    names = set(TOOL_HAND_RE.findall(cmd or ""))
    names |= set(TOOL_REDIRECT_RE.findall(cmd or ""))
    return set(n for n in names if not n.endswith((".bak", ".tmp")))


def paired_execs(rows):
    """`(exec_start, exec_end)` pairs, matched by adjacency and block number.
    The kernel writes them as a pair from one code path; order is the link."""
    out, start = [], None
    for r in rows:
        k = r.get("kind")
        if k == "exec_start":
            start = r
        elif k == "exec_end":
            if start is not None and start.get("block") == r.get("block"):
                out.append((start, r))
            else:
                out.append((None, r))
            start = None
    return out


def failure_signature(stderr):
    """The last non-empty stderr line, digits removed, so `line 69` and
    `line 65` are the SAME fault and a rewrite that moves the cut still
    matches. Empty when there is nothing to sign."""
    # The journal's own cut marker (`…[N chars withheld by the log…]`) and a
    # fixture's (`…[fixture cut N]`) are appended to the text, not part of
    # it; a signature that included them would differ per record.
    text = re.sub(r"…\[[^\]]*\]\s*$", "", stderr or "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    sig = re.sub(r"\d+", "#", lines[-1])
    sig = re.sub(r"\s+", " ", sig)
    return sig[:160]


# --------------------------------------------------------------- measures

def provenance(root, library):
    """Which of the library was INHERITED at t=0 and which the creature built.

    §6.2 chose to copy the parent's library as a known-answer test set, and
    made one requirement binding for the life of the project: every inherited
    tool tagged at t=0, and **every metric split on that tag**. The tagging
    was built (`seed_run.py`) and then nothing read it -- a verifier found
    `split_on_tag` had exactly one consumer in the whole repo, its own test.
    On the day run 3 starts, every count on this page would have described a
    library that is mostly somebody else's work as though the creature had
    made it, and no test would have noticed. That is §5's *a channel nothing
    asserts is a channel that can be dead while everything is green*,
    pre-installed for a run that has not happened yet.

    Returns None when the root carries no tag -- which is TODAY, because run
    2 began from nothing. That is a real answer and the page says it in
    words. Returning zeros would be worse than saying nothing: a reader
    cannot tell `0 inherited because none was` from `0 inherited because
    nobody looked`.
    """
    if not root:
        return None
    try:
        import seed_run
    except Exception:
        return None
    doc = seed_run.load_tag(root)
    if not doc:
        return None
    own = os.path.join(root, "body", "mind", "tools", "own")
    by_name, deleted = seed_run.classify_on_tag(root, own)
    if not by_name and not deleted:
        return None
    counts = seed_run.split_on_tag(root, own)
    inherited_now = sorted(n for n, r in by_name.items() if r["origin"])
    out = dict(counts)
    out["seeded_from"] = doc.get("source")
    out["tagged_at_seed"] = len(doc.get("tools") or {})
    out["inherited_now"] = inherited_now
    out["deleted_names"] = deleted
    # Split the thing the project actually turns on: a family of three where
    # two came from the parent is not the same finding as three built here.
    fam = stems(set(library) if library else set(by_name))
    out["families_inherited"] = {
        s: len([n for n in v if (by_name.get(n) or {}).get("origin")])
        for s, v in fam.items() if len(v) >= 3}
    return out


def probe_record(rows):
    """worked / asked-for-arguments / failed / unqualified over `cousin_probe`
    -- the same three the library shows, plus the honest fourth for probes
    written before `bare` was recorded, which CANNOT be classified and must
    not be counted as failures (that misreading is CLAUDE.md §5's top scar)."""
    rec = {"worked": 0, "asked": 0, "failed": 0, "unqualified": 0,
           "lost": 0}
    for r in rows:
        if r.get("kind") != "cousin_probe":
            continue
        if r.get("exit_code") is None:
            # The ladder never answered when the cousin was asked what to
            # type, so the tool was never reached. Its own bucket: a dry free
            # tier counted as `failed` is this page telling its reader the
            # creature's floor is broken.
            rec["lost"] += 1
        elif r.get("exit_code") == 0:
            rec["worked"] += 1
        elif "bare" not in r:
            rec["unqualified"] += 1
        elif r.get("bare"):
            rec["asked"] += 1
        else:
            rec["failed"] += 1
    return rec


def measure(rows):
    """Everything is a COUNT or a ratio of counts. No judgements live here.
    Rates are split by rung; the unsplit accept rate is deliberately absent
    (vitals.py, 2026-09-13: an aggregate over a heterogeneous ladder measures
    nothing)."""
    k = kinds(rows)
    thinks = [r for r in rows if r.get("kind") == "think"]
    by_rf = collections.Counter(
        (r.get("rung") or "(none)", r.get("finish") or "?") for r in thinks)
    execs = [r for r in rows if r.get("kind") == "exec_end"]
    exits = collections.Counter(r.get("exit_code") for r in execs)
    skips = collections.Counter(
        (r.get("reason") or "?", bool(r.get("lost")))
        for r in rows if r.get("kind") == "exec_skip")
    verdicts = [r for r in rows if r.get("kind") == "cousin_verdict"]
    v_by_rung = collections.defaultdict(collections.Counter)
    unknown_why = collections.defaultdict(collections.Counter)
    for v in verdicts:
        rung = v.get("rung") or "(none)"
        v_by_rung[rung][v.get("verdict") or "?"] += 1
        if v.get("verdict") == "UNKNOWN":
            unknown_why[rung][str(v.get("error") or "?")[:40]] += 1
    wants = [r.get("text") or "" for r in rows if r.get("kind") == "cousin_want"]
    writes = [r for r in rows
              if r.get("kind") == "trigger_fired" and r.get("type") == "TOOL_WRITE"]
    added = removed = 0
    for r in rows:
        if r.get("kind") == "tools_changed":
            added += len(r.get("added") or [])
            removed += len(r.get("removed") or [])
    return {
        "events": len(rows),
        "wakes": k.get("wake", 0),
        "thinks": len(thinks),
        "thinks_by_rung_finish": {"%s|%s" % rf: n for rf, n in sorted(by_rf.items())},
        "commands": len(execs),
        "cmd_ok": exits.get(0, 0),
        "cmd_failed": sum(n for c, n in exits.items() if c not in (0, None)),
        "exit_codes": {str(c): n for c, n in sorted(exits.items(), key=lambda x: str(x[0]))},
        "skips": {"%s|%s" % (reason, "lost" if lost else "kept"): n
                  for (reason, lost), n in sorted(skips.items())},
        "commands_lost": sum(n for (_r, lost), n in skips.items() if lost),
        "probes": probe_record(rows),
        "verdicts": len(verdicts),
        "verdicts_by_rung": {r: dict(c) for r, c in sorted(v_by_rung.items())},
        "unknown_by_rung": {r: dict(c) for r, c in sorted(unknown_why.items())},
        "wants": len(wants),
        "wants_distinct": len(set(wants)),
        "tool_writes": len(writes),
        "tool_writes_new": sum(1 for w in writes if w.get("tools")),
        "tool_writes_edit": sum(1 for w in writes if not w.get("tools")),
        "tools_added": added,
        "tools_removed": removed,
        "rung_declined": k.get("rung_declined", 0),
        "rung_broken": k.get("rung_broken", 0),
        "rung_error": k.get("rung_error", 0),
        "waits": k.get("loop_waiting", 0),
        "think_deferred": k.get("think_deferred", 0),
        "visit_deferred": k.get("visit_deferred", 0),
        "visit_unanswered": k.get("visit_unanswered", 0),
    }


def starts(rows):
    """Every process start the journal records. `engine_start` carries the
    commit (from 43eb8af); before that only `loop_start` exists and the
    engine is `unknown` -- said, never guessed."""
    out = []
    for r in rows:
        if r.get("kind") == "engine_start":
            out.append(r)
        elif r.get("kind") == "loop_start":
            if out and out[-1].get("kind") == "engine_start" \
                    and float(r["ts"]) - float(out[-1]["ts"]) < 600:
                continue      # the same start, seen from the supervisor
            out.append(dict(r, engine="unknown"))
    return out
