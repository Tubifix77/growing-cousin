#!/usr/bin/env python3
"""replay_parser.py -- score a parser change against the replies it will meet.

**Why this exists, dated 2026-09-21.** The parser the creature speaks through
has now been changed four times in this project's life, and three of those
changes had a cost that was found afterwards:

- 2026-09-13, the tag made optional: the framework ran a bare fence the
  creature had used to QUOTE a tool's output, and the creature read the
  manufactured failure out of its own transcript and built a false belief
  about its user.
- 2026-09-14, both fence ends anchored: a real command was dropped within
  forty minutes because an opener sat mid-line.
- 2026-09-21, `\\r?$` added to the closing fence as insurance against CRLF:
  **0 replies in run 2 contained CRLF, and 9 replies parsed differently.** In
  one, two valid commands became a single block containing a literal fence.
  Reverted the same night, by a verifier's replay rather than by the gate.

The gate cannot catch this class. It asserts shapes somebody thought of, and
the whole difficulty is the shapes nobody thought of. The corpus that can
catch it is the run's own replies -- which live only on the laptop, because
`raw` is raw model output and this repository is public (CLAUDE.md §0).

So the discipline is a command rather than an intention:

    # BEFORE the change
    python3 replay_parser.py live/journal.jsonl --save /tmp/parse-before.json
    # ... change kernel/think.py ...
    python3 replay_parser.py live/journal.jsonl --against /tmp/parse-before.json

Exit codes, and they are the whole contract:

  0  every shared reply parses identically
  1  at least one parses differently -- **not a veto**, a parser fix is
     supposed to change something. It is the list of what the change does.
  2  **nothing could be compared** -- no baseline, or no reply in common.

**2 exists because of a verifier, 2026-09-21.** The first version printed
*SAME: every shared reply parses identically* and exited 0 when the overlap
was ZERO: a baseline saved before the journal was rotated, or `--against`
pointed at the wrong path, and the instrument built to stop "green whether
the code works or not" certified a comparison it never made.

What it scans: every reply carrying raw model text, which is **not only the
creature's**. `parse_blocks` also drives the cousin's shell
(`cousin.choose_invocation`, `cousin.unusable_invocation`), so
`cousin_probe.proposal` and `cousin_verdict.raw` are read too. They are ~10%
of the corpus today and the 2026-09-16 fifteen-hour outage was on that side.

What the baseline stores is a COUNT, a CHARACTER TOTAL and a DIGEST per
reply, never the blocks -- a baseline that carried block text would be a
copy of the run's raw output, which is the thing that may not leave the
laptop. So a difference prints the NEW blocks and the old/new shape; the old
text is in the old journal, not here.

Reads only. Writes only where `--save` says.
"""
import argparse
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kernel import think


def digest(blocks):
    h = hashlib.sha256()
    for b in blocks:
        h.update(b.encode("utf-8", "replace"))
        h.update(b"\x1e")
    return h.hexdigest()[:16]


#: Every journal field that carries raw model text `parse_blocks` will meet.
#: The creature's think is the bulk of it; the cousin's shell is the rest, and
#: the fifteen-hour outage of 2026-09-16 was on the cousin's side.
RAW_FIELDS = (("think", "raw"),
              ("cousin_probe", "proposal"),
              ("cousin_verdict", "raw"))

DROPPED = "[dropped from fixture]"


def scan(path, keep_text=False):
    """{reply key -> {n, chars, digest, blocks?}} for every raw reply.

    Keyed on kind and timestamp, which is what the journal keys everything on.
    A record whose text is absent is SKIPPED rather than counted as empty: the
    committed fixtures drop `raw` on purpose (raw model output, public repo),
    and counting those as "no blocks" would make a corpus of them look like a
    parser that stopped working.
    """
    out = {}
    wanted = {k for k, _f in RAW_FIELDS}
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Cheap pre-filter: it may only SKIP lines that certainly carry
            # none of these kinds. `json.dumps` writes `"kind": "think"`
            # verbatim, so a real record always contains its own kind string.
            if not any(('"%s"' % k) in line for k in wanted):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            kind = r.get("kind")
            field = dict(RAW_FIELDS).get(kind)
            if not field:
                continue
            raw = r.get(field)
            if not raw or raw == DROPPED:
                continue
            blocks = think.parse_blocks(raw)
            rec = {"n": len(blocks), "digest": digest(blocks),
                   "chars": sum(len(b) for b in blocks), "kind": kind}
            if keep_text:
                rec["blocks"] = blocks
            out["%s@%r" % (kind, r.get("ts"))] = rec
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("journal")
    ap.add_argument("--save", help="write the current parse to this file")
    ap.add_argument("--against", help="compare the current parse against this")
    ap.add_argument("--show", type=int, default=5,
                    help="how many differing replies to print in full")
    a = ap.parse_args()

    now = scan(a.journal, keep_text=bool(a.against))
    per = {}
    for v in now.values():
        per[v["kind"]] = per.get(v["kind"], 0) + 1
    print("%d reply/replies carry raw text (%s); %d parse to at least one block"
          % (len(now),
             ", ".join("%s %d" % (k, per[k]) for k in sorted(per)) or "none",
             sum(1 for v in now.values() if v["n"])))

    if a.save:
        with io.open(a.save, "w", encoding="utf-8", newline="\n") as f:
            json.dump({k: {"n": v["n"], "digest": v["digest"],
                           "chars": v["chars"]}
                       for k, v in now.items()}, f, indent=1, sort_keys=True)
        print("saved %s" % a.save)

    if not a.against:
        return 0

    try:
        with io.open(a.against, encoding="utf-8") as f:
            before = json.load(f)
    except (OSError, ValueError) as e:
        print("CANNOT COMPARE: %s could not be read (%s)" % (a.against, e))
        return 2

    gone = [k for k in before if k not in now]
    new = [k for k in now if k not in before]
    diff = [k for k in now if k in before
            and (now[k]["digest"] != before[k]["digest"])]

    shared = len(now) - len(new)
    if gone or new:
        print("NOTE: %d reply/replies only in the baseline and %d only now -- "
              "the journal grew or was cut; only the %d shared replies are "
              "compared" % (len(gone), len(new), shared))
    if shared <= 0:
        # NOT "SAME". A comparison of nothing is not a clean comparison, and
        # saying so was this tool certifying work it never did -- the exact
        # fault it exists to prevent, in itself, found by a verifier on the
        # night it was written.
        print("CANNOT COMPARE: no reply is in both the baseline and the "
              "journal. Nothing was checked -- this is NOT a clean result.")
        return 2
    if not diff:
        print("SAME: every shared reply parses identically.")
        return 0

    print("DIFFERENT: %d of %d shared replies parse differently."
          % (len(diff), shared))
    for k in diff[:a.show]:
        b, n = before[k], now[k]
        print("-- %s: %d block(s)/%d chars -> %d block(s)/%d chars"
              % (k, b["n"], b["chars"], n["n"], n["chars"]))
        for i, blk in enumerate(n.get("blocks") or []):
            print("     now[%d]: %r" % (i, blk[:160]))
    if len(diff) > a.show:
        print("   ... and %d more" % (len(diff) - a.show))
    return 1


if __name__ == "__main__":
    sys.exit(main())
