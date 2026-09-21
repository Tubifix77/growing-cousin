#!/usr/bin/env python3
"""journal.py -- the ground truth neither agent may edit.

Two rules carried from the parent, both earned:

**One kind per event, with structured fields.** The parent journals all five
done-gate refusals as kind `"error"` with an English prefix, and then
string-matches them back out. Reconstructing "what has this creature been blocked
on" therefore means grepping prose inside a kind that also carries real errors.
A `Counter` over kinds must be able to answer "what has been happening" without
reading a single sentence of English.

**Keyed on epoch `ts`, never a date string.** `grep '2026-09-11' journal.jsonl`
returns coincidental hits and reads exactly like a quiet day.
"""
import json
import os
import re
import time

# Caps are named constants shared by writer and reader, never literals at the
# call site. The parent's scar: two caps in series are a producer and a checker,
# and raising only one is a silent no-op.
# THE JOURNAL IS THE EVIDENCE, so it must never keep LESS than a consumer is
# allowed to show. 2026-09-13: it did, and the effect was invisible for a day.
#
# `Engine.HISTORY_OUTPUT_CHARS` was raised 700 -> 2400 on 2026-09-12 to stop the
# creature being shown a tool cut mid-token. The measurement behind it was real
# (its tools are 706-3157 bytes) and the change did NOTHING, because `exec_end`
# had already cut stdout to 1200 before the history ever saw it. The knob that
# was tuned was not the knob that acts.
#
# That is the parent's *truncation caps in series* -- which CLAUDE.md §3 lists
# among the scars that "do not transfer" because "this engine does not have
# those failure modes". It has them.
#
# Cost, measured 18:17-18:57 the same day: `plan` had grown to 4022 bytes. The
# creature ran `cat tools/own/plan` six times in fifteen minutes, was shown
# 1200 characters each time, and never built the thing its cousin had asked
# for. From outside that reads as a creature going in circles. It was the
# framework showing it a third of its own tool.
#
# `test_a_cap_downstream_never_exceeds_the_cap_upstream` holds the invariant so
# the next raise cannot be silently swallowed again.
# 8000, from 2400, on 2026-09-17 -- and this time the measurement is the
# creature's own words. `plan` had reached 6,119 bytes; between 08:00 and
# 10:00 the creature ran `cat tools/own/plan` TWENTY times, was shown ~2,400
# characters each time with 2,970-3,743 withheld, and 12 of its 24 thinks in
# that window talk about the cut. It was trying to add exactly the deadline
# feature its cousin had asked for four times over. PLAN item 13 had said "not
# doing, and here is the symptom that would reopen it"; the symptom fired
# four times in twenty hours (`window_reread`), and reading the raw thinks
# answered its own question: not for its own reasons -- it cannot see the
# file. That is the 2026-09-13 wall again at a larger size, and a cap that
# hides 60% of the tool its author is editing is a correctness fault, not a
# tuning.
#
# SIZED TO THE LIBRARY, not guessed: 29 of 60 tools exceeded 2,400 bytes; the
# largest is 7,223 (`subagent-orchestrator`), then `plan` at 6,119. 8,000 shows
# every tool the creature has whole, with room for the next edit.
EXEC_STDOUT_CHARS = 8000
EXEC_STDERR_CHARS = 600
EXEC_CMD_CHARS = 800

# A marker always reports the TOTAL characters not shown. A later cut may only
# INCREASE that number, never replace it with its own -- the parent showed
# "+40 chars cut" where 3,319 were withheld, which is worse than no marker,
# because a small number reads as reassurance.
# The marker names WHO cut, not just how much. Reporting the size alone is not
# enough and this engine has now paid for that:
#
# 2026-09-12, the sixth and worst instance of the framework damaging the
# creature's work. The creature ran `cat plan; cat log-read`; the pair produced
# ~4.5k chars and this cap kept 1200, so `plan` appeared to end mid-file and
# `log-read` never appeared at all. The creature read the old marker --
# "+3332 chars cut; window 1200" -- concluded *"It's clearly truncated. The
# tool is broken."*, and then REWROTE BOTH TOOLS SHORTER: plan 99->92 lines,
# log-read 46->29. It mutilated a working library to fit a display limit it had
# no way to attribute.
#
# The parent's invariant was "a marker reports the TOTAL withheld". True, and
# insufficient: a reader who cannot tell OUR cut from the content ending
# concludes the content ended.
_MARK = "…[%d chars withheld by the log, not missing from the output; window %d]"

# One pattern, read by `marker_total` and by `capped` itself. Two regexes for
# one marker is a producer and a checker sharing a literal, which is the shape
# this file already carries a scar about.
_MARK_RE = re.compile(
    r"\u2026?\[(\d+) chars withheld by the log[^\]]*window (\d+)\]$")


def capped(text, limit, already_cut=0):
    """Cut to `limit`, announcing the TOTAL withheld including earlier cuts,
    and saying plainly that the cut is the LOG's and not the content's.

    **IT READS ITS OWN MARKER, rather than relying on the caller to pass
    `already_cut`.** Until 2026-09-21 the invariant held only when the caller
    remembered, and the one caller that nests cuts for real -- `recent_block`,
    re-cutting an `exec_end.stdout` that the journal had already capped --
    never did. Measured over the live journal the same day: **74 of 652 marked
    outputs came out understated, the worst telling the creature 146
    characters were withheld when the truth was 6,114.**

    That is the marker lying in the direction that reads as reassurance, and
    this engine has already paid for the other direction: on 2026-09-12 the
    creature read a marker, concluded its tool was broken, and rewrote two
    working tools shorter. `test_marker_invariant` was green the whole time
    because it passes `already_cut` by hand -- *a test suite proves what it
    asserts and nothing more.*
    """
    text = "" if text is None else str(text)
    # Absorb any marker this text already carries: strip it, and carry its
    # total forward. The marker sits at the very end, so a second cut would
    # otherwise remove the large number and replace it with a small one.
    m = _MARK_RE.search(text)
    if m:
        already_cut += int(m.group(1))
        text = text[:m.start()]
    if len(text) <= limit:
        # A CUT THAT REMOVES NOTHING REMOVES NOTHING. This used to fall through
        # to the line-boundary trim whenever an earlier loss was being carried,
        # and drop the last line of text that fitted -- unreachable in
        # production only because nobody passed `already_cut`, which is exactly
        # why it survived to be found by reading.
        kept = text
    else:
        kept = text[:limit]
        # Prefer a LINE BOUNDARY. A cut through the middle of
        # `print(line.strip())` looks exactly like corruption -- the creature
        # read one as a bug in its own tool and rewrote the tool. A cut between
        # lines reads as an excerpt, which is what it is. Only when a line
        # survives: never gut the text to find one.
        nl = kept.rfind("\n")
        if nl > limit // 2:
            kept = kept[:nl]
    withheld = (len(text) - len(kept)) + already_cut
    if withheld <= 0:
        return kept
    return kept + (_MARK % (withheld, limit))


def marker_total(text):
    """Read back the withheld count a marker claims. Used to prove the
    invariant holds across nested cuts rather than trusting that it does."""
    m = _MARK_RE.search(text or "")
    return int(m.group(1)) if m else 0


class Journal:
    def __init__(self, path):
        self.path = path
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    def append(self, kind, **fields):
        """One record, one line, one kind. Fields are structured, never prose
        carrying data a reader will have to parse back out."""
        rec = {"ts": time.time(), "kind": kind}
        rec.update(fields)
        line = json.dumps(rec, ensure_ascii=False)
        assert "\n" not in line, "one record per line"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return rec

    def read(self, kinds=None, since_ts=None, limit=None):
        out = []
        if not os.path.exists(self.path):
            return out
        with open(self.path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if kinds and r.get("kind") not in kinds:
                    continue
                if since_ts and float(r.get("ts", 0)) < since_ts:
                    continue
                out.append(r)
        return out[-limit:] if limit else out

    def kinds(self):
        """Every kind present, with counts. The parent's rule: for any event you
        suspect is uncountable, enumerate kinds FIRST and grep strings second."""
        from collections import Counter
        return Counter(r.get("kind") for r in self.read())
