#!/usr/bin/env python3
"""triggers.py -- when the cousin is called. Mechanical, never the creature's
say-so about its own state.

If the creature declares its own milestone, the false-completion problem
reappears one level up: the parent measured **139 false-completion blocks in a
single window**. It claims done constantly. So a trigger is something the kernel
OBSERVES -- a done-mark command in the executed list, a new file in `tools/own/`,
a count of quiet cycles -- never something the creature asserts.

Each trigger is journalled under its own kind with structured fields, so a
`Counter` can answer "what fired and how often" without reading prose.
"""
import os
import re

DONE_MARK_RE = re.compile(r"\bremember\s+current-phase\s+[\"']?done[\"']?", re.I)

# A write INTO tools/own, not a read OF it. Blocking on `cat tool` would be a
# gate nobody could satisfy.
TOOL_WRITE_RE = re.compile(
    r"(?:>|>>|\btee\b)\s*['\"]?(?:/mind/)?tools/own/|"
    r"\btool-new\b|\btool-edit\b")

STALL_CYCLES = 12
HEARTBEAT_CYCLES = 20   # the parent's RETRO_INTERVAL: its retro already IS this


def detect(executed, tools_before, tools_after, cycles_since_visit,
           cycles_since_change):
    """Return a list of (trigger_type, fields). Order is significance, not time:
    a done-claim outranks a write, which outranks a stall."""
    fired = []
    cmds = [c for c, _ in executed]

    if any(DONE_MARK_RE.search(c) for c in cmds):
        fired.append(("DONE_CLAIM", {"commands": len(cmds)}))

    new_tools = sorted(set(tools_after) - set(tools_before))
    if new_tools:
        fired.append(("TOOL_WRITE", {"tools": new_tools}))
    elif any(TOOL_WRITE_RE.search(c) for c in cmds):
        # Written through the proper door but not a new NAME -- an edit.
        fired.append(("TOOL_WRITE", {"tools": [], "edit": True}))

    if not fired and cycles_since_change >= STALL_CYCLES:
        fired.append(("STALL", {"cycles": cycles_since_change}))

    if not fired and cycles_since_visit >= HEARTBEAT_CYCLES:
        fired.append(("HEARTBEAT", {"cycles": cycles_since_visit}))

    return fired


def list_tools(tools_dir):
    """Names only. The isfile check lives here so callers cannot forget it."""
    try:
        return sorted(n for n in os.listdir(tools_dir)
                      if os.path.isfile(os.path.join(tools_dir, n)))
    except OSError:
        return []
