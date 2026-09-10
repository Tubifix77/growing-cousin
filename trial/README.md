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

## First results — 2026-09-10

| model | cases | MECH | SEMANTIC | false-ret | fmt-fail | avg |
|---|---|---|---|---|---|---|
| `gemma4:e2b` (5.1B) | 12 | 6/6 | **0/1** | 2/3 | 0/10 | 4.4s |
| `gemma-4-E4B-heretic` (7.5B) | 12 | 6/6 | **1/1** | 1/3 | 0/10 | 10.0s |
| `gemma4:12b` (11.9B, `think=false`) | 12 | 6/6 | **1/1** | 1/3 | 0/10 | 4.2s |

**Semantic judgment appears between 5.1B and 7.5B.** That was the ambiguity the
trial existed to settle — is the brief wrong, or the model too small — and it
resolves toward the model. Below the threshold you get a free static scan with
extra steps; above it you get a mock caught by naming `example.com` without ever
saying "mock", the `NameError` no startability check can see, and in one run a
tool caught reporting *"Domain is stable"* after its analysis step had failed.

**Format compliance was never the problem.** 0 failures in 30 scored calls
across three models, on a contract that asks for a fenced block read from the
end of the reply.

### `gemma4:12b` returned nothing at all, and the obvious fix was wrong

Every case came back empty. Not malformed — **empty**, with `done_reason:
length` and `eval_count: 900`. It opened a reasoning block, never closed it, and
spent its whole allowance. Raising the budget does not help:

| setting | done_reason | tokens | reply |
|---|---|---|---|
| `num_predict=900` | length | 900 | 0 chars |
| `num_predict=3000` | length | 3000 | **0 chars** |
| **`think=false`** | **stop** | **216** | **903 chars, valid verdict** |

**Budget is not the binding constraint; unbounded reasoning is.** This matters
beyond Ollama: the parent project lists "a larger `max_tokens`" as one of three
remedies for a rung that wastes 86.7% of the cycles it serves. For this failure
mode that remedy only makes the waste larger.

And structurally: a model that spends everything and returns nothing still
registers a **successful call**. Nothing walls the rung, nothing below it is
reached, and the manager is silently absent rather than visibly broken. The
kernel must classify an empty-but-complete reply as a failure, never an answer.

### All three models return `keyword-archive-store`, and that is evidence about the case

Not one model accepted it. When every model disagrees with the label, suspect
the label. The tool tells the caller exactly what was missing — and **this
harness gives the cousin no way to supply it.** The case is unfair as built.

The invariant is therefore not "distinguish a correct refusal from a failure".
It is **a user who has been told what was missing has not finished trying** —
and that cannot be tested until the cousin has its own shell. Left in place,
labelled, unfixed, because deleting a case that contradicts you is how a test
set stops being worth anything.

### Faults found, all in the instruments

Four, and every one produced a clean-looking wrong number rather than an error:

1. **Results written only at the end of a run.** A killed run lost eight real
   verdicts. Rows are appended and fsynced per case now.
2. **`raw_len` stored, raw reply discarded.** Made *said nothing*, *cut off*,
   and *answered elsewhere* indistinguishable — three faults, three fixes, one
   label.
3. **`compare.py` took the latest run per model**, reporting a one-case smoke
   test as a clean score. Then, fixed to take the *most rows*, it tied 12–12 and
   picked the run where every reply was empty. "Most complete" has to be defined
   by what the rows are **for**: usable verdicts first.
4. **An intermittent mute refusal** — right judgment, empty message — which did
   not reproduce on a rerun. Worse than a consistent one: it passes tests and
   fails in production. Now `MUTE-REFUSAL`, and a bound the kernel must hold.

## Files

| File | What |
|---|---|
| `cases.json` | The evidence. Real, captured once, read-only. Do not edit to make a run look better |
| `run_trial.py` | Runner, parser, scorer. Backend-agnostic in shape; Ollama today |
| `results/*.jsonl` | One record per verdict, `kind: trial_verdict`, model recorded on every row — the rule from `ARCHITECTURE.md` §9 applied to the trial itself |
