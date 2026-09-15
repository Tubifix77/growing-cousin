#!/usr/bin/env python3
"""make_heldout.py -- a case set the brief has never been measured against.

PLAN item 8. `CLAUDE.md` §0 has said since 2026-09-14 that the brief is FROZEN
until *"there is a way to score a brief change against held-out cases, which
`trial/` could carry and currently does not"*. Every case in `cases.json` and
`repair-cases.json` was used to WRITE the brief -- four rules were earned from
what the judge said on those twelve -- so a score on them measures how well the
brief remembers its own training, which is the one thing nobody needs to know.

**Both halves are labelled by evidence, not by opinion**, because the labels
are the whole value and this project has already deleted one measurement for
resting on a label somebody chose (`trial/README.md`, the leak).

**RETURNED cases come from the parent's library, statically.** §6.2 chose it as
a known-answer test set precisely because it holds *"23 tools that cannot
start"*, and a tool that cannot start is a fact rather than a judgement: the
interpreter says so. A handover of one is a refusal in any brief worth having.

  **Nothing of the parent's is ever RUN.** `CLAUDE.md` §2.6 -- reading its
  source is allowed and has twice changed this design; touching it never is.
  Its tools would write into its creature's world. So the check is
  `compile()` for python and `bash -n` for shell, which reads and executes
  nothing.

**ACCEPTED cases come from our own production journal**, where a probe really
ran a tool and it really exited 0 with output. That transcript is not a story
about a tool working; it is the record of one working.

    python3 trial/make_heldout.py --out trial/heldout-cases.json
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER_LINES = 6
# Enough to judge, short enough that the case set stays readable. The live
# transcripts are already capped by the journal.
TRANSCRIPT_CHARS = 1200


def header_of(path, lines=HEADER_LINES):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[:lines]).rstrip()
    except OSError:
        return ""


# ONE implementation of "does this file start", shared with `seed_run.py`,
# which needs the identical judgement to decide whether an inherited tool was
# REPAIRED. Two copies of a rule drift and no test notices -- the fault this
# repo has paid for in `wants()`, in the caps, and in the census.
sys.path.insert(0, os.path.dirname(HERE))
from seed_run import why_it_cannot_start          # noqa: E402


def already_taught(paths):
    """Every tool name the brief was WRITTEN against.

    The first run of this generator produced `RecallScheduler`, `ascii_plot`
    and `dynamic_faq_updater` -- three of eight -- and every one of them is in
    `cases.json`. They are not held out from anything: four of the brief's
    rules were earned by reading what a judge said about those very tools. A
    held-out set that quietly re-uses the training set is the 2026-09-10 leak
    with the direction reversed, and it would have read as a strong score.
    """
    seen = set()
    for p in paths:
        try:
            with io.open(p, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            continue
        for c in (doc.get("cases") if isinstance(doc, dict) else doc) or []:
            n = (c.get("name") or "").strip()
            if n:
                seen.add(n)
                seen.add(n.replace(".py", ""))
                seen.add(n.split(".")[0])
    return seen


def cannot_start_cases(own, limit, exclude=()):
    """Every tool whose interpreter refuses it, newest-looking first."""
    out = []
    try:
        names = sorted(os.listdir(own))
    except OSError:
        return out
    for n in names:
        p = os.path.join(own, n)
        if not os.path.isfile(p) or n.startswith(".") or n.endswith((".bak", ".orig")):
            continue
        if n in exclude or n.split(".")[0] in exclude:
            continue
        why = why_it_cannot_start(p)
        if not why:
            continue
        head = header_of(p)
        if not head:
            continue
        out.append({
            "name": n,
            "class": "MECH",
            "expect": "RETURNED",
            "why": "the interpreter refuses the file, so it cannot run for "
                   "anyone: %s" % why,
            "claim": "I finished %s." % n,
            "header": head,
            "transcript": "$ %s\nexit 1\nTraceback (most recent call last):\n"
                          "  File \"%s\"\n%s" % (n, n, why),
        })
        if len(out) >= limit:
            break
    return out


def ran_clean_cases(journal, own_dirs, limit, exclude=()):
    """Probes from our own journal where the tool really ran and produced
    output. The FALSE-REFUSAL control: a brief that refuses these is refusing
    work that demonstrably did what it said."""
    rows = []
    try:
        for line in io.open(journal, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("{") and '"cousin_probe"' in line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        return []
    seen, out = set(), []
    for r in reversed(rows):
        name = (r.get("tool") or "").strip()
        stdout = (r.get("stdout") or "").strip()
        if (not name or name in seen or r.get("exit_code") != 0
                or len(stdout) < 12):
            continue
        if name in exclude or name.split(".")[0] in exclude:
            continue
        head = ""
        for d in own_dirs:
            head = head or header_of(os.path.join(d, name))
        if not head:
            continue
        seen.add(name)
        out.append({
            "name": name,
            "class": "SEMANTIC",
            "expect": "ACCEPTED",
            "why": "its user really ran it and it exited 0 with output; "
                   "refusing this refuses work that demonstrably ran",
            "claim": "I finished %s." % name,
            "header": head,
            "transcript": ("$ %s\nexit 0\n%s" % (name, stdout))[:TRANSCRIPT_CHARS],
        })
        if len(out) >= limit:
            break
    return out


def repaired_cases(journal, own_dirs, limit, exclude=()):
    """Tools that REALLY failed for the cousin and later really worked.

    *Detection asks can you tell good work from bad; correction asks can you
    tell a real repair from one that only looks like one* -- and a detection
    number without a correction number beside it is the 2026-09-11 scar, where
    99.1%% detection sat on top of a total failure at correction.

    **Today this returns nothing, and that is a finding rather than a gap.**
    Over the whole of run 2 the journal holds ZERO probes that failed with
    `bare=False`: since the flag was added every non-zero probe has been a
    tool correctly refusing incomplete input. Nothing has broken for its user,
    so nothing has been repaired for its user, so there is no evidence from
    which to label a correction case. Inventing one would put my own repair in
    the answer key.

    The generator is wired anyway, so the day a real failure is followed by a
    real success this fills by itself instead of waiting to be remembered.
    """
    rows = []
    try:
        for line in io.open(journal, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("{") and '"cousin_probe"' in line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        return []
    by = {}
    for r in rows:
        by.setdefault((r.get("tool") or "").strip(), []).append(r)
    out = []
    for name, rs in sorted(by.items()):
        if not name or name in exclude:
            continue
        rs.sort(key=lambda r: r.get("ts", 0))
        broke = next((r for r in rs if r.get("exit_code") not in (0, None)
                      and r.get("bare") is False), None)
        if not broke:
            continue
        fixed = next((r for r in rs if r.get("exit_code") == 0
                      and r.get("ts", 0) > broke.get("ts", 0)
                      and (r.get("stdout") or "").strip()), None)
        if not fixed:
            continue
        head = ""
        for d in own_dirs:
            head = head or header_of(os.path.join(d, name))
        if not head:
            continue
        out.append({
            "name": name, "class": "REPAIR", "expect": "ACCEPTED",
            "why": "it really failed for its user and later really worked: "
                   "exit %s then exit 0 with output" % broke.get("exit_code"),
            "claim": "I fixed %s." % name, "header": head,
            "transcript": ("$ %s\nexit 0\n%s"
                           % (name, (fixed.get("stdout") or "").strip()))[:TRANSCRIPT_CHARS],
        })
        if len(out) >= limit:
            break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spine-mind",
                    default=os.path.expanduser("~/growing-spine-mind"),
                    help="READ-ONLY. Nothing here is ever executed (§2.6).")
    ap.add_argument("--journal",
                    default=os.path.expanduser("~/growing-cousin/live/journal.jsonl"))
    ap.add_argument("--own",
                    default=os.path.expanduser(
                        "~/growing-cousin/live/body/mind/tools/own"))
    ap.add_argument("--returned", type=int, default=8)
    ap.add_argument("--accepted", type=int, default=8)
    ap.add_argument("--out", default=os.path.join(HERE, "heldout-cases.json"))
    ap.add_argument("--repair-out",
                    default=os.path.join(HERE, "heldout-repair-cases.json"))
    args = ap.parse_args(argv)

    taught = already_taught([os.path.join(HERE, "cases.json"),
                             os.path.join(HERE, "repair-cases.json"),
                             os.path.join(HERE, "cases-v1-bare-probe.json")])
    bad = cannot_start_cases(os.path.join(args.spine_mind, "tools", "own"),
                             args.returned, exclude=taught)
    good = ran_clean_cases(args.journal, [args.own], args.accepted,
                           exclude=taught)
    cases = bad + good
    overlap = sorted({c["name"] for c in cases} & taught)
    if overlap:
        sys.stderr.write("REFUSED: %d case(s) are in the training set: %s\n"
                         % (len(overlap), ", ".join(overlap)))
        return 3
    if not cases:
        sys.stderr.write("no cases could be captured\n")
        return 2

    doc = {
        "_about": "HELD OUT. No rule in MANAGER-PROMPT.md was written against "
                  "any case in here, and no case in here was looked at while "
                  "writing one. That is the whole point: cases.json and "
                  "repair-cases.json taught the brief, so a score on them "
                  "measures recall of its own training.",
        "_labels": "Evidence, not opinion. RETURNED = the interpreter refuses "
                   "the file, established by compile()/`bash -n`, which reads "
                   "and runs nothing. ACCEPTED = our own journal records the "
                   "cousin running it to exit 0 with output.",
        "_boundary": "The parent's tools are READ, never executed -- CLAUDE.md "
                     "§2.6. Running one would write into its creature's world.",
        "_captured": {"spine_mind": args.spine_mind, "journal": args.journal,
                      "excluded_as_already_taught": len(taught)},
        "_scoring": "Detection and correction are reported together, always. "
                    "A detection number without a correction number beside it "
                    "is the 2026-09-11 scar (99.1%% detection sitting on top "
                    "of a total failure at correction).",
        "cases": cases,
    }
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)

    repairs = repaired_cases(args.journal, [args.own], args.accepted,
                             exclude=taught)
    rdoc = {
        "_about": "The CORRECTION half of the held-out set: tools that really "
                  "failed for the cousin and later really worked.",
        "_why_empty": "Zero probes in run 2 failed with bare=False -- every "
                      "non-zero probe since the flag was added is a tool "
                      "correctly refusing incomplete input. Nothing has broken "
                      "for its user, so nothing has been repaired for its user, "
                      "and a correction case invented here would put the "
                      "author's own repair in the answer key. The generator is "
                      "wired; this fills itself the day a real failure is "
                      "followed by a real success."
                      if not repairs else "",
        "cases": repairs,
    }
    with io.open(args.repair_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rdoc, f, indent=1, ensure_ascii=False)
    print("%d correction case(s) -> %s" % (len(repairs), args.repair_out))
    print("%d cases -> %s  (%d cannot-start / %d ran-clean)"
          % (len(cases), args.out, len(bad), len(good)))
    for c in cases:
        print("   %-8s %-34s %s" % (c["expect"], c["name"][:34], c["why"][:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
