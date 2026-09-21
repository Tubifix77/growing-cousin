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

It exits 1 if any reply parses differently, prints how many and shows the
first few, with the old and new blocks side by side. **A non-zero exit is not
a veto** -- a parser fix is supposed to change something. It is the list of
what the change actually does, which is the thing nobody had before.

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


def scan(path, keep_text=False):
    """{reply key -> {n, digest, blocks?}} for every reply carrying raw text.

    Keyed on the timestamp, which is what the journal keys everything on. A
    reply with no `raw` is skipped rather than counted as empty: the fixtures
    drop `raw` on purpose, and counting those as "no blocks" would make a
    corpus of them look like a parser that stopped working.
    """
    out = {}
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or '"think"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") != "think":
                continue
            raw = r.get("raw")
            if not raw or raw == "[dropped from fixture]":
                continue
            blocks = think.parse_blocks(raw)
            rec = {"n": len(blocks), "digest": digest(blocks),
                   "chars": sum(len(b) for b in blocks)}
            if keep_text:
                rec["blocks"] = blocks
            out[repr(r.get("ts"))] = rec
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
    print("%d reply/replies carry raw text; %d parse to at least one block"
          % (len(now), sum(1 for v in now.values() if v["n"])))

    if a.save:
        with io.open(a.save, "w", encoding="utf-8", newline="\n") as f:
            json.dump({k: {"n": v["n"], "digest": v["digest"],
                           "chars": v["chars"]}
                       for k, v in now.items()}, f, indent=1, sort_keys=True)
        print("saved %s" % a.save)

    if not a.against:
        return 0

    with io.open(a.against, encoding="utf-8") as f:
        before = json.load(f)

    gone = [k for k in before if k not in now]
    new = [k for k in now if k not in before]
    diff = [k for k in now if k in before
            and (now[k]["digest"] != before[k]["digest"])]

    if gone or new:
        print("NOTE: %d reply/replies only in the baseline and %d only now -- "
              "the journal grew or was cut; only the %d shared replies are "
              "compared" % (len(gone), len(new), len(now) - len(new)))
    if not diff:
        print("SAME: every shared reply parses identically.")
        return 0

    print("DIFFERENT: %d of %d shared replies parse differently."
          % (diff and len(diff) or 0, len(now) - len(new)))
    for k in diff[:a.show]:
        b, n = before[k], now[k]
        print("-- ts %s: %d block(s)/%d chars -> %d block(s)/%d chars"
              % (k, b["n"], b["chars"], n["n"], n["chars"]))
        for i, blk in enumerate(n.get("blocks") or []):
            print("     now[%d]: %r" % (i, blk[:160]))
    if len(diff) > a.show:
        print("   ... and %d more" % (len(diff) - a.show))
    return 1


if __name__ == "__main__":
    sys.exit(main())
