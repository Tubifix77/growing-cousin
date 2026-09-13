#!/usr/bin/env python3
"""vitals.py -- what the engine is actually doing, split by rung.

Built 2026-09-13 after Tue named the fault in how the previous night was
worked: **this framework is not deterministic, so a change that looks like an
improvement on one observation may be noise, may be a regression the next hour
would have shown, and may be specific to whichever model happened to answer.**

Three consequences, and they are why this file exists:

1. **A single observation is not a measurement.** Five context-rendering
   changes were made in four hours, each declared good from one window. None
   was compared against a baseline.
2. **You can oscillate forever.** Without a number, "better" is whatever was
   changed most recently, and the system may already be as good as this model
   gets.
3. **The ladder is heterogeneous.** An accept from `gemma-4-31b-it` and one
   from `gpt-oss-120b` are different instruments. An aggregate rate over both
   measures neither, so every rate here is SPLIT BY RUNG and the unsplit
   figure is deliberately not printed.

Read-only over the journal. Reports; never gates; changes nothing.

    python3 vitals.py live/journal.jsonl                 # whole run
    python3 vitals.py live/journal.jsonl --since 60      # last 60 minutes
    python3 vitals.py live/journal.jsonl --compare 90    # two 90-min windows
"""
import argparse
import collections
import json
import os
import sys
import time


def load(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def window(rows, start, end):
    return [r for r in rows if start <= r.get("ts", 0) < end]


def measure(rows):
    """Everything is a COUNT or a ratio of counts. No judgements live here."""
    k = collections.Counter(r.get("kind") for r in rows)
    verdicts = [r for r in rows if r.get("kind") == "cousin_verdict"]
    execs = [r for r in rows if r.get("kind") == "exec_end"]
    cmds = [(r.get("cmd") or "").strip()
            for r in rows if r.get("kind") == "exec_start"]

    by_rung = collections.defaultdict(collections.Counter)
    for v in verdicts:
        by_rung[v.get("rung") or "(none)"][v.get("verdict") or "?"] += 1

    unknown_why = collections.Counter()
    for v in verdicts:
        if v.get("verdict") == "UNKNOWN":
            e = str(v.get("error") or "?")
            unknown_why["LadderExhausted" if e.startswith("LadderExhausted")
                         else e] += 1

    exits = collections.Counter(r.get("exit_code") for r in execs)
    ok = exits.get(0, 0)
    bad = sum(n for c, n in exits.items() if c not in (0, None))

    wants = [r.get("text") or "" for r in rows if r.get("kind") == "cousin_want"]

    return {
        "cycles": k.get("wake", 0),
        "thinks": k.get("think", 0),
        "waits": k.get("loop_waiting", 0),
        # EXPECTED vs FAULT, kept apart. On a free tier a declined rung is the
        # normal case; pooling it with real faults makes a healthy engine look
        # broken and sends the next reader hunting for a bug that is weather.
        "rung_declined": k.get("rung_declined", 0),
        "rung_broken": k.get("rung_broken", 0),
        "think_deferred": k.get("think_deferred", 0),
        "commands": len(execs),
        "cmd_ok": ok,
        "cmd_failed": bad,
        "cmd_fail_rate": (float(bad) / len(execs)) if execs else 0.0,
        # A creature repeating itself is the failure mode that costs a whole
        # night silently: every cycle looks busy and nothing moves.
        "cmd_distinct_rate": (float(len(set(cmds))) / len(cmds)) if cmds else 0.0,
        "verdicts": len(verdicts),
        "by_rung": {r: dict(c) for r, c in by_rung.items()},
        "unknown_why": dict(unknown_why),
        "tools_changed": k.get("tools_changed", 0),
        "wants": wants,
        "want_distinct_rate": (float(len(set(wants))) / len(wants)) if wants else 0.0,
        "recovered": sum(1 for v in verdicts if v.get("recovered_from_reasoning")),
    }


def fmt(m, title):
    out = ["== %s ==" % title,
           "cycles %-5d thinks %-5d waits %-4d tools changed %d"
           % (m["cycles"], m["thinks"], m["waits"], m["tools_changed"]),
           "commands %-4d  ok %-4d  failed %-4d  fail-rate %.0f%%  distinct %.0f%%"
           % (m["commands"], m["cmd_ok"], m["cmd_failed"],
              100 * m["cmd_fail_rate"], 100 * m["cmd_distinct_rate"]),
           "verdicts %d   recovered-from-reasoning %d"
           % (m["verdicts"], m["recovered"]),
           "rungs declined %d (expected)   BROKEN %d (needs a human)   "
           "thinks deferred %d"
           % (m["rung_declined"], m["rung_broken"], m["think_deferred"])]
    if m["by_rung"]:
        out.append("verdicts BY RUNG (an aggregate over rungs measures nothing):")
        for rung, counts in sorted(m["by_rung"].items()):
            total = sum(counts.values())
            acc = counts.get("ACCEPTED", 0)
            out.append("   %-30s %-3d  accepted %-3d (%.0f%%)  %s"
                       % (rung, total, acc, 100.0 * acc / total if total else 0,
                          ", ".join("%s %d" % (a, b) for a, b in sorted(counts.items())
                                    if a != "ACCEPTED") or "-"))
    if m["unknown_why"]:
        out.append("unknown verdicts, by cause: %s" % m["unknown_why"])
    if m["wants"]:
        out.append("wants %d, distinct %.0f%%:"
                   % (len(m["wants"]), 100 * m["want_distinct_rate"]))
        for w in m["wants"]:
            out.append("   - %s" % w[:90])
    return "\n".join(out)


ARROWS = {True: "better", False: "worse"}


def compare(a, b):
    """Two windows side by side. NO verdict on which is better overall.

    Direction is printed per metric and nothing is aggregated into a score: a
    score would invite exactly the mistake this file was written against --
    declaring a change good because one number moved.
    """
    rows = [("cycles", "cycles", None),
            ("commands", "commands", None),
            ("cmd_fail_rate", "command fail-rate", False),
            ("cmd_distinct_rate", "command distinct-rate", True),
            ("verdicts", "verdicts", None),
            ("want_distinct_rate", "want distinct-rate", True),
            ("waits", "waits", None)]
    out = ["== earlier window vs later window ==",
           "%-24s %12s %12s   %s" % ("", "earlier", "later", "")]
    for key, label, higher_is_better in rows:
        x, y = a[key], b[key]
        if isinstance(x, float):
            xs, ys = "%.0f%%" % (100 * x), "%.0f%%" % (100 * y)
        else:
            xs, ys = str(x), str(y)
        note = ""
        if higher_is_better is not None and x != y:
            note = ARROWS[(y > x) == higher_is_better]
        out.append("%-24s %12s %12s   %s" % (label, xs, ys, note))
    out.append("")
    out.append("Counts this small are not significant on their own. A direction "
               "that survives several windows is a signal; one window is an "
               "anecdote, and this engine is not deterministic.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journal", nargs="?", default="live/journal.jsonl")
    ap.add_argument("--since", type=float, default=None,
                    help="only the last N minutes")
    ap.add_argument("--compare", type=float, default=None,
                    help="compare the last N minutes against the N before them")
    ap.add_argument("--jsonl", type=float, default=None, metavar="MINUTES",
                    help="emit ONE json line covering the last N minutes, for "
                         "appending to a time series")
    args = ap.parse_args()

    if not os.path.exists(args.journal):
        sys.stderr.write("no journal at %s\n" % args.journal)
        return 2
    rows = load(args.journal)
    if not rows:
        sys.stderr.write("journal is empty\n")
        return 2
    now = time.time()

    if args.jsonl:
        # One line per sample, so a night becomes a SERIES rather than a
        # handful of glances. With a non-deterministic engine the series is
        # the only thing that can separate a trend from an anecdote, and it
        # has to be recorded continuously -- sampling only when someone looks
        # is how a quiet regression survives a whole night.
        sel = window(rows, now - args.jsonl * 60, now + 1)
        m = measure(sel)
        m.pop("wants", None)          # the texts live in the journal already
        m["ts"] = round(now, 1)
        m["window_min"] = args.jsonl
        print(json.dumps(m, sort_keys=True))
        return 0

    if args.compare:
        span = args.compare * 60
        earlier = window(rows, now - 2 * span, now - span)
        later = window(rows, now - span, now + 1)
        if not earlier or not later:
            sys.stderr.write("not enough journal to compare two %g-minute "
                             "windows\n" % args.compare)
            return 2
        print(compare(measure(earlier), measure(later)))
        return 0

    sel = rows if args.since is None else window(rows, now - args.since * 60,
                                                 now + 1)
    title = ("whole run, %d events" % len(sel) if args.since is None
             else "last %g minutes" % args.since)
    print(fmt(measure(sel), title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
