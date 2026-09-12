#!/usr/bin/env python3
"""The gate for the Stop hook. Run it before trusting the hook at all.

`A channel nothing asserts is a channel that can be dead while everything is
green.` That scar cost Growing Cousin its entire direction mechanism for the
life of the kernel, with a 99/99 green gate sitting over it. A tripwire is
exactly such a channel: it is silent when working AND silent when broken.

So this asserts BOTH directions. A hook that blocks everything passes the
"does it fire" test and is worthless -- the same control the library A/B needed.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "defect_ledger.py")

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print("%s %s %s" % ("PASS" if cond else "FAIL", name, "" if cond else extra))


def transcript(turns):
    """turns: list of ("user"|"text"|"tool", payload)."""
    fd, path = tempfile.mkstemp(suffix=".jsonl", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for kind, payload in turns:
            if kind == "user":
                row = {"type": "user",
                       "message": {"role": "user", "content": payload}}
            elif kind == "tool_result":
                row = {"type": "user", "message": {"role": "user", "content": [
                    {"type": "tool_result", "content": payload}]}}
            elif kind == "text":
                row = {"type": "assistant", "message": {"role": "assistant",
                       "content": [{"type": "text", "text": payload}]}}
            else:
                row = {"type": "assistant", "message": {"role": "assistant",
                       "content": [{"type": "tool_use", "name": payload,
                                    "input": {}}]}}
            f.write(json.dumps(row) + "\n")
    return path


def run(turns, stop_hook_active=False):
    path = transcript(turns)
    try:
        payload = json.dumps({"transcript_path": path,
                              "stop_hook_active": stop_hook_active,
                              "session_id": "test"})
        p = subprocess.run([sys.executable, HOOK], input=payload,
                           capture_output=True, text=True, timeout=30)
        out = (p.stdout or "").strip()
        blocked = False
        if out:
            try:
                blocked = json.loads(out).get("decision") == "block"
            except Exception:
                blocked = False
        return blocked, p.returncode, out
    finally:
        os.unlink(path)


REPORTED = ("text", "The gate is 115/115. But step 3 found a real defect I "
                    "haven't fixed: the cousin accepts twins. Moving on to docs.")

# --- it fires on the actual behaviour it was built for -------------------
blocked, code, out = run([("user", "finish the project"), REPORTED])
check("fires on report-then-move-on", blocked, out[:200])
check("a blocking hook still exits 0", code == 0, "exit %d" % code)

# --- and it does NOT fire on the ways work legitimately ends -------------
blocked, _, _ = run([("user", "fix the twins"),
                     ("text", "There is a real defect here: the cousin accepts "
                              "twins. Fixing it now."),
                     ("tool", "Edit"),
                     ("text", "Fixed, gate green.")])
check("silent when the defect was actually fixed in-turn", not blocked)

blocked, _, _ = run([("user", "status?"),
                     ("text", "README is now stale.\n\nDEFERRED: README rewrite "
                              "-- needs the long run's numbers first.")])
check("silent when explicitly deferred", not blocked)

blocked, _, _ = run([("user", "what is 2+2"), ("text", "Four.")])
check("silent on ordinary work naming no defect", not blocked)

blocked, _, _ = run([("user", "explain the design"),
                     ("text", "The cousin judges whether a tool works for a "
                              "second user. The gate is 115/115 green.")])
check("silent on prose that merely discusses quality", not blocked)

# --- the loop guard ------------------------------------------------------
blocked, _, _ = run([("user", "go"), REPORTED], stop_hook_active=True)
check("never re-blocks once already blocking (no infinite loop)", not blocked)

# --- tool_result records must not be mistaken for a new user turn --------
blocked, _, _ = run([("user", "finish it"), REPORTED,
                     ("tool", "Bash"), ("tool_result", "ok")])
check("a tool_result does not hide the earlier defect report", blocked,
      "turn boundary detected at the wrong record")

# --- failing open --------------------------------------------------------
p = subprocess.run([sys.executable, HOOK], input="not json",
                   capture_output=True, text=True, timeout=30)
check("garbage stdin fails OPEN, never wedges the session",
      p.returncode == 0 and "block" not in (p.stdout or ""), p.stdout[:120])

p = subprocess.run([sys.executable, HOOK],
                   input=json.dumps({"transcript_path": "/nope/missing.jsonl"}),
                   capture_output=True, text=True, timeout=30)
check("missing transcript fails OPEN", p.returncode == 0
      and "block" not in (p.stdout or ""), p.stdout[:120])

print("\n%d/%d green" % (len(PASS), len(PASS) + len(FAIL)))
print("ALL TESTS PASS" if not FAIL else "FAILURES: %s" % FAIL)
sys.exit(1 if FAIL else 0)
