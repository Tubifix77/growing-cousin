# The trial — putting the cousin in front of a known-answer library

**What this is:** the cheapest possible refutation of the Growing Cousin design,
built before any engine exists. No container lifecycle, no loop, no triggers,
no journal. Just the brief, a model, real evidence, and a score.

It exists because of the decision in `ARCHITECTURE.md` §11 to start from a copy
of the parent's library. That library's faults are already known, so it is a
**known-answer test set** — and the design can be refuted in an afternoon instead
of a season.

```bash
python run_trial.py --model gemma4:e2b
python run_trial.py --model qwen2.5-coder:14b --model gemma4:12b   # compare
```

---

## What the evidence is

`cases.json` holds twelve cases captured **2026-09-10 from the live Growing Spine
library** (670 tools at capture time; 22 cannot start; 29 duplicate-stem twin
pairs). Nothing is authored — *fixtures come from the real corpus, never
authored*, which is the parent's rule and the only reason this test means
anything.

Capture method: a throwaway container from the body image, with the creature's
volume mounted **read-only** (`:ro`) and **`--network=none`**. Each tool was run
twice — with no argument, and with the argument `AI` — and its true stdout,
stderr and exit code recorded. The live creature was never touched and no
provider was called.

Each case carries the tool's header as a stranger would read it, the real
transcript, and a plausible done-claim from the creature. The claim matters: a
mock fetcher is a perfectly good mock and a failed *"gets fresh news"*.

## What each case is for

| Case | Class | Expect | The point |
|---|---|---|---|
| `RecallScheduler` | mechanical | RETURNED | Unterminated string; a bash shebang nested inside a Python file |
| `ascii_plot` | mechanical | RETURNED | Python shebang, bash body |
| `dynamic_faq_updater` | mechanical | RETURNED | A typographic `“` (U+201C) where ASCII was meant |
| `catchup_plan_archive.py` | mechanical | RETURNED | No shebang, so `sh` tries to run Python |
| `research_gap_to_fetch` | **mechanical-hidden** | RETURNED | Bare call looks healthy. The syntax error only appears **with an argument** — catches a cousin that stops at the first probe |
| `subagent_task_planner` | **runtime** | RETURNED | **The most important case.** Starts perfectly; every static check passes. Fails only in use — calls `plan_from_question` as a function it never defines |
| `wake_catchup_fetcher` | **semantic** | RETURNED | Runs, exits 0, returns well-formed JSON of fabricated articles on `example.com`. Its header even admits it is a mock |
| `keyword-archive-search` | control | ACCEPTED | Genuinely works. 14,132 journal invocations |
| `keyword-archive-store` | **control-trap** | ACCEPTED | Works. Both probes exit 1 — because *the prober* gave no note content, which the tool correctly refuses. Catches a cousin that reads exit 1 as failure |
| `archive-search-recall` | control | ACCEPTED | Genuinely works |
| `catchup_plan_archive` | excluded | OBSERVE | Failed on the read-only mount — *our* constraint, not the tool's fault. Does the cousin attribute it correctly? |
| `knowledge-estate-manager` | excluded | OBSERVE | Its helper failed on `--network=none`. But it printed *"No major contradictions detected. Domain is stable"* **before** that — a confident conclusion resting on a step that did not run. Does the cousin notice? |

`subagent_task_planner` is the case the whole design rests on. It is exactly the
class the parent's static startability check **structurally cannot see**, and the
only reason to pay for a cousin that genuinely runs things.

## Scoring — and why there is no single number

**7 cases expect `RETURNED` and 3 expect `ACCEPTED`. A model that always returns
scores 70%.** So the runner never reports accuracy. It reports:

- **catch rate** — broken work correctly returned
- **false-return rate** — good work wrongly returned; this is the one that makes
  the creature's world arbitrary, and the more expensive failure
- **format failures** — no parseable verdict block. Counted separately because
  format non-compliance is exactly what wasted **86.7%** of the cycles one
  provider rung served in the parent project: clean, complete replies with no
  usable content in them
- **prose smells** — advisory only

## Prose smells are advisory, deliberately

The runner flags `to_creature` text that instructs, diagnoses, names the cause,
or quotes internals — the four ways testimony decays into doctrine.

**These are not a pass/fail gate and must never become one.** A keyword list is
precisely the *guard hunting one literal string* fault this lineage has a scar
for. They mark a verdict for a human to read. The judgement stays with the
reader.

## Honest limits — read before believing any result

1. **The harness is the cousin's hands.** It runs a fixed two-probe sequence and
   hands over the transcript; the cousin does not choose what to try. Everything
   in the transcript genuinely happened, so no verdict rests on a fabricated
   experience — but exploration is not being tested. A cousin with its own shell
   would do better on `research_gap_to_fetch` and might do worse elsewhere.
2. **A small local model is a floor, not a verdict.** The design will run on the
   free-tier ladder. If `gemma4:e2b` holds the discipline, a larger model almost
   certainly will — that inference is sound. The reverse is not: a failure here
   is ambiguous between *the design is wrong* and *the model is too small*.
3. **Only three clean controls.** False-return discrimination rests on a thin
   base. More positives are the first thing to add.
4. **Twelve cases is a shakedown, not a measurement.** It is sized to refute a
   design cheaply, not to characterise one.

## Files

| File | What |
|---|---|
| `cases.json` | The evidence. Real, captured once, read-only. Do not edit to make a run look better |
| `run_trial.py` | Runner, parser, scorer. Backend-agnostic in shape; Ollama today |
| `results/*.jsonl` | One record per verdict, `kind: trial_verdict`, model recorded on every row — the rule from `ARCHITECTURE.md` §9 applied to the trial itself |
