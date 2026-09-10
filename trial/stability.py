#!/usr/bin/env python3
"""stability.py -- does the judge answer the SAME WAY twice?

    python stability.py                     # newest multi-rep run
    python stability.py --file results/x.jsonl

One pass over a case set shows whether a model CAN answer. Only repetition shows
whether it answers consistently, and consistency is the property a manager needs:
a creature whose work is accepted on Monday and returned on Tuesday for identical
output learns that the world is arbitrary, which is the exact failure the brief
exists to prevent.

**temperature=0 is not determinism.** Measured 2026-09-10: an intermittent mute
refusal -- correct verdict, empty message -- appeared once and was gone on the
rerun. A fault that shows up in one pass of twelve will show up in production and
pass every single-pass test you write.

Reported per case, never as one number. A 92% aggregate hides whether one case is
a coin flip or every case is slightly noisy, and those need different fixes.
"""
import argparse
import glob
import io
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")


def load(path=None):
    if path:
        return path, [json.loads(l) for l in io.open(path, encoding="utf-8") if l.strip()]
    best, rows_best = None, []
    for p in sorted(glob.glob(os.path.join(RESULTS, "*.jsonl"))):
        rows = [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]
        if not rows:
            continue
        if len({r.get("rep") for r in rows}) > 1 and len(rows) > len(rows_best):
            best, rows_best = p, rows
    return best, rows_best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    args = ap.parse_args()
    path, rows = load(args.file)
    if not rows:
        print("no multi-rep run found in %s" % RESULTS)
        return

    reps = sorted({r.get("rep") for r in rows})
    by_case = defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(r)

    print("run   : %s" % os.path.basename(path))
    print("model : %s" % rows[0].get("model"))
    print("passes: %d   rows: %d\n" % (len(reps), len(rows)))

    print("%-27s %-9s %-6s %-7s %s" % ("case", "expect", "green", "stable", "verdicts seen"))
    print("-" * 88)

    scored_green = scored_total = 0
    unstable, wrong = [], []
    for name in sorted(by_case):
        rs = by_case[name]
        exp = rs[0]["expect"]
        seen = Counter((r.get("verdict") or ("FORMAT-FAIL" if r["mark"] == "FORMAT-FAIL" else "-"))
                       for r in rs)
        stable = len(seen) == 1
        if exp == "OBSERVE":
            green = "-"
        else:
            g = sum(1 for r in rs if r["verdict"] == exp)
            scored_green += g
            scored_total += len(rs)
            green = "%d/%d" % (g, len(rs))
            if g < len(rs):
                wrong.append((name, exp, dict(seen)))
        if not stable:
            unstable.append((name, dict(seen)))
        print("%-27s %-9s %-6s %-7s %s" % (
            name[:27], exp, green, "yes" if stable else "NO",
            ", ".join("%s x%d" % (k, v) for k, v in seen.most_common())))

    pct = (100.0 * scored_green / scored_total) if scored_total else 0.0
    print("\nGREEN (scored cases only): %d/%d = %.1f%%" % (scored_green, scored_total, pct))
    print("target for this repo: 99%")

    if unstable:
        print("\nUNSTABLE -- same input, different answer across passes:")
        for n, seen in unstable:
            print("  %-27s %s" % (n, seen))
        print("  These are the ones to fix first. An unstable case is not a wrong")
        print("  answer, it is a coin flip, and averaging hides it.")
    else:
        print("\nEvery case answered identically on every pass.")

    if wrong:
        print("\nWRONG (stable or not) -- disagrees with the label:")
        for n, exp, seen in wrong:
            print("  %-27s expected %-9s got %s" % (n, exp, seen))
        print("  Before fixing the brief, ask whether the LABEL is right:")
        print("  when every judge disagrees with a label, suspect the label.")

    mutes = [r for r in rows if r.get("verdict") == "RETURNED"
             and not (r.get("to_creature") or "").strip()]
    if mutes:
        print("\nMUTE REFUSALS: %d of %d RETURNED verdicts carried no message."
              % (len(mutes), sum(1 for r in rows if r.get("verdict") == "RETURNED")))
        print("  A refusal with no reason is the arbitrary world the brief exists")
        print("  to prevent. The kernel must never deliver one.")

    errs = Counter(r.get("call_error") for r in rows if r.get("call_error"))
    if errs:
        print("\nCALL ERRORS (not the model's fault, not verdicts):")
        for e, n in errs.most_common(5):
            print("  x%-4d %s" % (n, str(e)[:90]))


if __name__ == "__main__":
    main()
