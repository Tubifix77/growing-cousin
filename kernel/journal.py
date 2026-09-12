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
import time

# Caps are named constants shared by writer and reader, never literals at the
# call site. The parent's scar: two caps in series are a producer and a checker,
# and raising only one is a silent no-op.
EXEC_STDOUT_CHARS = 1200
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


def capped(text, limit, already_cut=0):
    """Cut to `limit`, announcing the TOTAL withheld including earlier cuts,
    and saying plainly that the cut is the LOG's and not the content's."""
    text = "" if text is None else str(text)
    if len(text) <= limit and not already_cut:
        return text
    kept = text[:limit]
    # Prefer a LINE BOUNDARY. A cut through the middle of `print(line.strip())`
    # looks exactly like corruption -- the creature read one as a bug in its own
    # tool and rewrote the tool. A cut between lines reads as an excerpt, which
    # is what it is. Only when a line survives: never gut the text to find one.
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
    import re
    m = re.search(r"\[(\d+) chars withheld by the log[^\]]*window (\d+)\]$",
                  text or "")
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
