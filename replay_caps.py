"""What would the creature have SEEN, over the real 17-hour read loop, under
each cap setting? Deterministic -- no model, no luck, real journal.

This is the measurement last night got wrong. It swept HISTORY_TOTAL_CHARS
with the per-output window pinned at 8,000, so every row paid the same clipped
price and the answer was "a bigger box buys nothing". Here all three caps move
together, as they do in the engine.

THREE HONESTIES, each of which the first draft would have got wrong:

1. Historical stdout is stored at whatever EXEC_STDOUT_CHARS was in force when
   it was written -- 8,000 plus a marker. Replaying that straight would flatter
   the NEW arm, because a real 12,042-char `cat` eats more of a 24,000 budget
   than a stored 8,000 one does. So where a command is a read of a tool we
   still have, the TRUE file content is substituted before any cap is applied,
   and the new arm pays full price.

2. "Commands visible" is counted off the RENDERED block by its own quote
   prefix, never by grepping the journal for a word. A substring match of
   `cat`/`plan` against a comment line is how the local A/B reported a read
   that never happened.

3. The renderer is not reimplemented here. `recent_block` reads its rows
   through the journal, so the JOURNAL is what gets substituted and the real
   rendering path runs untouched -- a reimplementation would be a checker
   agreeing with the producer by eye.
"""
import io
import json
import os
import sys
import time

ROOT = sys.argv[1] if len(sys.argv) > 1 else "live"
REPO = sys.argv[2] if len(sys.argv) > 2 else "."
sys.path.insert(0, REPO)

from kernel.cycle import Engine                     # noqa: E402
from kernel import journal as journalmod            # noqa: E402

TOOLS = os.path.join(ROOT, "body", "mind", "tools", "own")

ARMS = [("OLD   8k /  8k / 12k", 8000, 8000, 12000),
        ("NEW  16k / 16k / 24k", 16000, 16000, 24000),
        ("      16k / 16k / 32k", 16000, 16000, 32000),
        ("      16k / 16k / 40k", 16000, 16000, 40000),
        ("      16k / 16k / 48k", 16000, 16000, 48000),
        ("      16k / 16k / 64k", 16000, 16000, 64000)]

# The window the read loop actually ran in: previous deploy to the daily check.
T0 = time.mktime(time.strptime("2026-09-23 00:30", "%Y-%m-%d %H:%M"))
T1 = time.mktime(time.strptime("2026-09-23 17:52", "%Y-%m-%d %H:%M"))


class FakeJournal(object):
    rows = []

    def read(self, kinds=None, limit=None):
        rs = [r for r in self.rows if r.get("kind") in (kinds or [])]
        return rs[-limit:] if limit else rs


def true_output(cmd, stored):
    """Undo the storage cap where the real file is still on disk."""
    if "withheld by the log" not in (stored or ""):
        return stored
    if not ("cat " in (cmd or "") or "head " in (cmd or "")):
        return stored
    try:
        names = sorted(os.listdir(TOOLS), key=len, reverse=True)
    except OSError:
        return stored
    for name in names:
        if name and name in cmd:
            try:
                return io.open(os.path.join(TOOLS, name), encoding="utf-8",
                               errors="replace").read()
            except OSError:
                return stored
    return stored


def main():
    recs = [json.loads(l) for l in
            io.open(os.path.join(ROOT, "journal.jsonl"), encoding="utf-8")
            if l.strip()]
    window = [r for r in recs if T0 <= r["ts"] <= T1]

    last_cmd, restored = None, 0
    for r in window:
        if r.get("kind") == "exec_start":
            last_cmd = r.get("cmd") or ""
        elif r.get("kind") == "exec_end":
            t = true_output(last_cmd, r.get("stdout"))
            if t != r.get("stdout"):
                restored += 1
                r["stdout"] = t

    wakes = [i for i, r in enumerate(window) if r.get("kind") == "wake"]
    print("window 2026-09-23 00:30-17:52: %d records, %d wakes, "
          "%d clipped reads restored to their true content"
          % (len(window), len(wakes), restored))
    print()

    for label, exec_out, hist_out, hist_total in ARMS:
        journalmod.EXEC_STDOUT_CHARS = exec_out

        class Arm(Engine):
            HISTORY_OUTPUT_CHARS = hist_out
            HISTORY_TOTAL_CHARS = hist_total

        e = Arm.__new__(Arm)
        e.j = FakeJournal()
        visible, evicted, whole, blocks = [], 0, 0, []
        for i in wakes:
            shaped = []
            for r in window[max(0, i - 60):i]:
                if r.get("kind") == "exec_end":
                    r = dict(r)
                    r["stdout"] = journalmod.capped(r.get("stdout"), exec_out)
                shaped.append(r)
            e.j.rows = shaped
            block = e.recent_block()
            n = block.count("\n" + Arm.HISTORY_QUOTE + "$ ")
            visible.append(n)
            blocks.append(len(block))
            if n <= 1:
                evicted += 1
            if "withheld by the log" not in block:
                whole += 1

        nz = sorted(v for v in visible if v)
        print(label)
        print("   commands visible per wake:   median %d, max %d"
              % (nz[len(nz) // 2] if nz else 0, max(visible or [0])))
        print("   wakes with <=1 command left: %d of %d  (%.0f%%)"
              % (evicted, len(wakes), 100.0 * evicted / max(1, len(wakes))))
        print("   wakes shown an UNCUT transcript: %d of %d  (%.0f%%)"
              % (whole, len(wakes), 100.0 * whole / max(1, len(wakes))))
        b = sorted(blocks)
        print("   block chars  mean %d | median %d | p90 %d | max %d"
              % (sum(b) / max(1, len(b)), b[len(b) // 2],
                 b[int(len(b) * 0.9)], b[-1]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
