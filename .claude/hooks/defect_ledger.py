#!/usr/bin/env python3
"""defect_ledger.py -- a Stop hook that refuses the silent third option.

The behaviour it exists to catch, named by Tue 2026-09-12 and earned the hard
way the day before: I find a real defect, I REPORT it clearly, and then I change
the subject. Naming a problem feels like handling a problem. Nothing stops me,
because nothing was watching.

**It does not forbid the defect. It forbids the silence.** That distinction is
the whole design, and it is not a nicety -- a rule of the shape "never stop
while a known bug exists" makes KNOWING expensive, so the report gets softer
instead of the bug getting fixed. Growing Cousin has a scar for exactly this:
*any field that gives a shortfall a comfortable home will be used to avoid
refusing.* A locked door is such a field. A required disposition is not.

So a turn that names a defect must end in one of two states:

  FIXED    -- proved by an actual Edit/Write/NotebookEdit in the same turn, or
              a task spawned for it. Evidence, not a claim. "I fixed it" is
              testimony; the tool call is the event. That asymmetry is lifted
              straight from census.py, which checks the cousin the same way.
  DEFERRED -- a line beginning `DEFERRED:` saying what and why.

Deferral is cheap ON PURPOSE. One line, no argument, no permission needed. If
deferring were expensive this would just be the locked door again wearing a
different hat.

Fails OPEN on any error: a tripwire that wedges the session is worse than no
tripwire. But every decision is logged, because *a channel nothing asserts is a
channel that can be dead while everything is green* -- so `--report` can show
what it has actually been doing rather than what it was meant to do.
"""
import json
import os
import re
import sys
import time

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defect-ledger.log")

# Signals for "I am telling you something is wrong" -- deliberately narrow.
# A broad list fires on every mention of the word `bug` and gets switched off in
# a week, which is the real failure mode for a hook like this.
DEFECT_PATTERNS = [
    r"\b(haven'?t|have not|did not|didn'?t)\s+fix",
    r"\bnot\s+fixed\b",
    r"\bleft\s+(it\s+|them\s+)?unfixed\b",
    r"\bstill\s+(broken|failing|fails|wrong|stale|unfixed)\b",
    r"\b(remains?|stays?)\s+broken\b",
    r"\breal\s+(defect|bug|problem)\b",
    r"\bknown\s+(bug|defect|issue)\b",
    r"\b(needs|need)\s+(fixing|to\s+be\s+fixed)\b",
    r"\bshould\s+be\s+fixed\b",
    r"\b(is|are|now|gone)\s+stale\b",
    r"\bdoes\s*n[o']?t\s+work\b",
    r"\bis\s+broken\b",
    r"\bfix\s+(this|that|it)\s+later\b",
]

# A disposition that is not a code change: one line, stated plainly.
DEFER_RE = re.compile(r"^\s*DEFERRED\s*:", re.M)

# Tool calls that constitute EVIDENCE of a fix, as opposed to a claim of one.
FIX_TOOLS = {"Edit", "Write", "NotebookEdit", "mcp__ccd_session__spawn_task"}

BLOCK_MESSAGE = """A defect was named in this turn and neither disposition was recorded.

You wrote something matching: %s

Before ending the turn, do ONE of:
  - fix it now (an actual edit in this turn is what clears this), or
  - write a line starting with `DEFERRED:` naming what is being left and why.

Deferring is fine and costs one line. Reporting a defect and changing the
subject is the thing this blocks -- naming a problem is not handling one."""


def log(verdict, detail=""):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                      verdict, detail.replace("\n", " ")[:300]))
    except Exception:
        pass


def turn_content(transcript_path):
    """Assistant text and tool names since the last real user message.

    A tool_result is delivered as a `user` record, so a naive "last user line"
    scan lands mid-turn and sees almost nothing. That is the bug this function
    exists to not have.
    """
    rows = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue

    start = 0
    for i, r in enumerate(rows):
        if r.get("type") != "user":
            continue
        content = (r.get("message") or {}).get("content")
        if isinstance(content, str):
            start = i + 1
        elif isinstance(content, list):
            if not any(isinstance(c, dict) and c.get("type") == "tool_result"
                       for c in content):
                start = i + 1

    text_parts, tools = [], set()
    for r in rows[start:]:
        if r.get("type") != "assistant":
            continue
        content = (r.get("message") or {}).get("content")
        if isinstance(content, str):
            text_parts.append(content)
            continue
        for c in content or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text":
                text_parts.append(c.get("text") or "")
            elif c.get("type") == "tool_use":
                tools.add(c.get("name") or "")
    return "\n".join(text_parts), tools


def check(text, tools):
    """Returns the matched phrase when the turn must be blocked, else None."""
    if tools & FIX_TOOLS:
        return None
    if DEFER_RE.search(text):
        return None
    for pat in DEFECT_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0)
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        log("PASS", "unreadable stdin (failing open)")
        return 0

    if payload.get("stop_hook_active"):
        log("PASS", "stop_hook_active -- not re-blocking")
        return 0

    path = payload.get("transcript_path")
    if not path or not os.path.exists(path):
        log("PASS", "no transcript (failing open)")
        return 0

    text, tools = turn_content(path)
    hit = check(text, tools)
    if not hit:
        log("PASS", "tools=%s" % ",".join(sorted(t for t in tools if t)))
        return 0

    log("BLOCK", hit)
    print(json.dumps({"decision": "block", "reason": BLOCK_MESSAGE % hit}))
    return 0


if __name__ == "__main__":
    if "--report" in sys.argv:
        # What has it ACTUALLY done? Not what it was meant to do.
        try:
            rows = [l.split("\t") for l in
                    open(LOG, encoding="utf-8").read().strip().split("\n") if l]
        except Exception:
            print("no log yet at %s" % LOG)
            sys.exit(0)
        blocks = [r for r in rows if len(r) > 1 and r[1] == "BLOCK"]
        print("defect-ledger: %d decisions, %d blocks" % (len(rows), len(blocks)))
        for r in blocks[-15:]:
            print("  %s  %s" % (r[0], r[2] if len(r) > 2 else ""))
        sys.exit(0)
    try:
        sys.exit(main())
    except Exception as e:
        log("PASS", "hook crashed, failing open: %s" % e)
        sys.exit(0)
