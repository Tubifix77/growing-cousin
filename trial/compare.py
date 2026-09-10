#!/usr/bin/env python3
"""compare.py -- read every stored run and put the models side by side.

Re-scoring is free: run_trial.py stores the parsed verdict AND the prose for each
case, so comparing models, or re-reading the testimony under a better definition
of a prose smell, never requires calling a model again.

    python compare.py                 # latest run per model
    python compare.py --all           # every run

The split that matters is MECHANICAL vs SEMANTIC, not the headline score. A free
deterministic scan already catches mechanical faults; semantic judgment is the
only thing a cousin is bought for. A model that scores well on the first and zero
on the second has not earned its calls.
"""
import argparse
import glob
import json
import io
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

MECHANICAL = {"mechanical", "mechanical-hidden", "runtime"}
SEMANTIC = {"semantic"}


def load(all_runs):
    by_model = defaultdict(list)
    for p in sorted(glob.glob(os.path.join(RESULTS, "*.jsonl"))):
        rows = [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]
        if not rows:
            continue
        by_model[rows[0]["model"]].append((p, rows))
    out = {}
    for m, runs in by_model.items():
        out[m] = runs if all_runs else [runs[-1]]
    return out


def score(rows):
    s = {r["case"]: r for r in rows}
    scored = [r for r in rows if r["expect"] != "OBSERVE"]
    mech = [r for r in scored if r["class"] in MECHANICAL]
    sem = [r for r in scored if r["class"] in SEMANTIC]
    ctrl = [r for r in scored if r["expect"] == "ACCEPTED"]
    return {
        "mech": (sum(r["verdict"] == "RETURNED" for r in mech), len(mech)),
        "sem": (sum(r["verdict"] == "RETURNED" for r in sem), len(sem)),
        "false_ret": (sum(r["verdict"] == "RETURNED" for r in ctrl), len(ctrl)),
        "fmt": (sum(r["mark"] == "FORMAT-FAIL" for r in scored), len(scored)),
        "secs": round(sum(r.get("seconds") or 0 for r in rows) / max(1, len(rows)), 1),
        "cases": s,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--case", help="print every model's testimony for one case")
    args = ap.parse_args()

    runs = load(args.all)
    if not runs:
        print("no runs in %s" % RESULTS)
        return

    if args.case:
        for m, rs in runs.items():
            for _, rows in rs:
                for r in rows:
                    if r["case"] == args.case:
                        print("=" * 74)
                        print("%s  ->  %s (expect %s)" % (m, r["verdict"], r["expect"]))
                        print("  " + (r.get("to_creature") or "(nothing)").replace("\n", "\n  "))
                        if r.get("want"):
                            print("  want: " + r["want"])
        return

    print("%-46s %-9s %-9s %-11s %-8s %s" % (
        "model", "MECH", "SEMANTIC", "false-ret", "fmt-fail", "avg s"))
    print("-" * 100)
    for m, rs in sorted(runs.items()):
        for path, rows in rs:
            s = score(rows)
            print("%-46s %-9s %-9s %-11s %-8s %s" % (
                m[:46],
                "%d/%d" % s["mech"], "%d/%d" % s["sem"],
                "%d/%d" % s["false_ret"], "%d/%d" % s["fmt"], s["secs"]))
    print("\nMECH      = mechanical + runtime faults correctly RETURNED (higher better)")
    print("SEMANTIC  = mock / fabricated-output faults correctly RETURNED (higher better)")
    print("false-ret = good tools wrongly RETURNED (LOWER better) -- the expensive failure")
    print("fmt-fail  = no parseable verdict block (lower better)")
    print("\nA free deterministic scan already gets MECH. SEMANTIC is what a cousin is for.")


if __name__ == "__main__":
    main()
