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
| `0914-healthy-hour` | 09‑14 22:00 → 23:00 | cut as the control, and **every detector written since has found something in it**: the chooser fault (`view-subtask-logs` probed 5 of 5, bare) on 09‑15, and a tool read four times inside an hour without being changed on 09‑16. It is a control for the detectors that stay quiet on it and evidence for the two that do not. It is kept as a real slice rather than trimmed until it looks clean | all but two quiet; `probe_stuck`, `window_reread` |
| `0915-want-loop` | 09‑15 14:00 → 19:00 | the same want six times behind ACCEPTs of a bare usage line; `view-subtask-logs` probed on 28 of 30 non‑write visits because `pick_target` defaulted to the alphabetically last tool; five tools built to answer one want, all past the listing limit and invisible | `want_repeated`, `probe_stuck` |

**Scrubbing, stated so nobody mistakes it for the journal:** `think.raw` is
replaced by `[dropped from fixture]` with its length kept as `raw_chars`; any
other text field longer than 240 characters is cut at 240 with a
`…[fixture cut N]` marker. Every event is kept, in order, with every other
field intact. Secret‑scanned before commit: 0 key‑shaped strings.

**A fixture is never edited to make a test pass.** If a detector fails on
one, the detector is wrong or the scar is misunderstood — either way the
fixture is the evidence and the test is the claim.

## The drill fixtures (`0916-drill-*`), and where they come from

The five slices above are **cut from production**: real hours of the real
journal, in which the scar really happened. The ones below are not. They are
**manufactured**, by `rehearse.py` on the laptop, because the faults they
carry have never occurred in production -- the engine has never gone silent,
never given up, never torn its journal, never lost a tool off PATH -- and
*a test that has never been seen red is a guess*.

A verifier asked where they came from and this file had no answer, which for
the file whose entire job is provenance is the fault it exists to prevent.

| file | made by | what it holds |
|---|---|---|
| `0916-drill-tool-gone.jsonl` | `rehearse.py tool-gone` | a tool removed from PATH under a live creature |
| `0916-drill-silence.jsonl` | `rehearse.py silence` | a journal whose last event is older than the floor while the unit is active |
| `0916-drill-torn.jsonl` | `rehearse.py torn` | a journal with a half-written final line, as a kill mid-append leaves it |
| `0916-drill-body.jsonl` | `rehearse.py body` | a body that stops answering and cannot be respawned |
| `0916-drill-fabricate.jsonl` | `rehearse.py fabricate` | a verdict testifying to an exit code no probe ever produced |
| `0916-drill-giveup.{jsonl,evidence.json}` | `rehearse.py giveup` | the supervisor abandoning a run, and systemd's half of that chain |
| `0916-drill-docker.evidence.json` | `rehearse.py docker` | the container destroyed and required back, with the keys unreachable from inside |

**Count deliberately not written here.** The line above said "six" while the table had seven rows and the directory held 8 files -- a stale count in the file whose only job is provenance, one commit after it was rebuilt for exactly that. A count in prose is a constant nobody chose; count the directory.

All produced 2026-09-16 on the laptop against scratch roots under `/tmp`,
never against `live/`; the harness watches the live root across every drill
and refuses any path inside a deployment, a git checkout or the sibling
project. Regenerate with `--emit-fixtures`. Same scrubbing as above, same
secret scan.

**What the gate does with them, stated exactly, because the test's own
docstring overclaimed it for a day:** it re-runs the DETECTORS against these
recordings. It does not re-run the drills -- they need docker, systemd and a
scratch filesystem, none of which belong in a suite that must pass on a
laptop in nine seconds. So a regression in `rehearse.py` itself is NOT caught
here; it is caught by running the drills, which is a thing a human does
before believing a path works.

Replay one by hand:

```bash
python3 -m monitor replay tests/fixtures/journal/0913-fence-syntaxerror.jsonl
```
