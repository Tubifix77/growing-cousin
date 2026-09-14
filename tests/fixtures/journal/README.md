# Journal fixtures — where the scars happened

Slices of the **live run‑2 journal**, cut on the laptop 2026‑09‑15 00:25 CEST
from `live/journal.jsonl`, so that every detector in `monitor/detectors.py`
can be proven against the hour its scar actually occurred rather than against
a story about it. *A test that has never been seen red is a guess* — these are
real reds.

| file | window (CEST) | what happened | detector proven |
|---|---|---|---|
| `0913-gemini-unusable-and-want-unacted` | 09‑13 15:15 → 17:43 | fourteen `UNKNOWN` verdicts in a row from `gemini/gemma-4-31b-it`, read as weather until ~19:40; a want issued 15:49 and retired 17:42 with **no tool write** between | `unusable_verdicts`, `want_retired_unacted` |
| `0913-fence-syntaxerror` | 09‑13 19:44 → 20:05 | the first four of fifteen identical `SyntaxError: unterminated string literal` across rewrites of `subagent-orchestrator` — our parser cutting the file, the creature billed for it | `repeated_failure` |
| `0914-opener-regression` | 09‑14 21:30 → 21:40 | the anchored opener dropping a real command as `unclosed_fence`, forty minutes after the fence fix | `commands_lost_parser` |
| `0914-healthy-hour` | 09‑14 22:00 → 23:00 | nothing wrong: the control every detector must stay quiet on | all (no human alarm) |

**Scrubbing, stated so nobody mistakes it for the journal:** `think.raw` is
replaced by `[dropped from fixture]` with its length kept as `raw_chars`; any
other text field longer than 240 characters is cut at 240 with a
`…[fixture cut N]` marker. Every event is kept, in order, with every other
field intact. Secret‑scanned before commit: 0 key‑shaped strings.

**A fixture is never edited to make a test pass.** If a detector fails on
one, the detector is wrong or the scar is misunderstood — either way the
fixture is the evidence and the test is the claim.

Replay one by hand:

```bash
python3 -m monitor replay tests/fixtures/journal/0913-fence-syntaxerror.jsonl
```
