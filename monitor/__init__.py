"""monitor -- what the engine is doing, written where a reader who was not
present can see it.

Built 2026-09-15 after a session in which the journal held the facts for
every fault and nobody derived a signal from them: fourteen unusable verdicts
read as weather for four hours, the same SyntaxError twelve times over nine
hours, a want channel discarding direction, a give-up that exited 0. The
observer is a window for a desk; this is a file for the helper on the other
end of an ssh session, and for the next session that has to re-derive nothing.

Five layers, and this package is the middle three:

    RECORD   the journal (kernel)        -- facts, one kind per event
    DERIVE   monitor/derive.py           -- counts and ratios, split by rung
    DETECT   monitor/detectors.py        -- one detector per scar, three states
    PRESENT  monitor/render.py           -- status.md, status.json, alarms.jsonl
    PROVE    tests/fixtures/journal/     -- real slices where each scar happened

Rules, each paid for elsewhere in this repo or in the spine's:

- **Read-only over everything but its own directory.** It never writes the
  journal, the context or the creature's tools, and nothing it produces is
  shown to either inhabitant (CLAUDE.md §2.4). Its audience is us.
- **Three states, never two.** OK, ALARM, or CANNOT TELL. A detector with
  too few events says so; it does not say OK.
- **Floors are declared with the measurement behind them, never learned.**
  A floor that follows a collapse downward never fires -- the spine's
  ratchet disease.
- **Edge-triggered.** `alarms.jsonl` gets a line when a state changes and
  nothing between; the status page is regenerated continuously because it
  is pulled, not pushed.
- **A stale number is never shown as live.** Every figure names the window
  it covers and the engine that produced it.
- **Every detector has a fixture where its scar really happened**, and the
  gate asserts it fires there and stays quiet on a healthy hour. A test
  never seen red is a guess.
"""
