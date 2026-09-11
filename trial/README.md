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

## Both halves, one brief — 2026-09-11

`gemma4:12b` standing in for `gemma-4-31b-it`, the rung carrying 87–93% of the
parent's traffic. Same family, one size down, runs locally, spends no quota.

| | result | passes | verdicts |
|---|---|---|---|
| **Detection** | **110/110 = 100.0%**, every case identical on every pass | 10 | 120 |
| **Correction** | **10/10 = 100%** | 5 | 20 |

Detection asks *can it tell good work from bad*. Correction asks the harder
question: *when the creature comes back saying it fixed the thing, can it tell a
real repair from one that only looks like one*. Both now hold on the **same**
brief, which is the part that took the work — they held one at a time for hours.

### What the correction loop found that 120 detection verdicts could not

A tool was returned **10/10** for producing month-old items. The "repair" moved
the timestamps to today and changed nothing else — same invented articles, same
reserved domain. It was accepted **5/5**, with a feature request attached:

> *"it gave me two news items with today's date. I can use this for the wake
> catch-up now."*

**The mock was never being detected as fabrication. It was being detected as old
dates.** A 99.1% detection score was sitting on top of that the whole time. Only
asking what happens after a complaint is answered could expose it — and that is
the question a complaint-driven creature asks every single cycle.

### The four rules, each earned from testimony and measured against the run before

| rule | moved |
|---|---|
| Unverifiable is not failed | detection 92.8% → 99.1% |
| A `want` is for capability BEYOND the claim, never the claim itself | cosmetic repair 0/5 → 5/5 |
| Judge the result, not the tidiness of getting there | genuine repair 1/5 → 5/5 |
| Did the tool MAKE what is wrong, or merely CARRY it | detection 90.9% → 100% |

Every one came from reading what the judge **said**, not from its score. The
scoreline said "wrong"; the testimony said which rule was missing.

### Two failures worth more than the successes

**A rule that was right in isolation and harmful in company.** Adding *"work that
answers your words precisely deserves more scrutiny"* regressed genuine repairs
5/5 → 1/5 and caught nothing. Reverted, not layered over, and kept in
`results/repair-after-need-rule/`.

**A fix for one half that broke the other.** The three correction rules dropped
detection 99.1% → 90.9%, and **only the two search controls moved** — both to
exact 5/5 coin flips. That precision *was* the diagnosis: two rules overlapped on
"I got something, but it has a problem", and nothing said which won. An aggregate
would have said "something is off". Kept in `results/detection-regressed-90/`.

**The brief is ONE artifact. Every rule added to it changes every verdict it
produces.** Detection must be re-measured after every correction fix, and the
reverse. That is the discipline, not a precaution.

---

## Reliability: 92.8% → 99.1% on the workhorse standin

**Why `gemma4:12b`.** The parent's workhorse rung is `gemma-4-31b-it`, carrying
87–93% of the creature's traffic. `gemma4:12b` is the same family, one size
down, and runs locally — so it is the honest standin, and the free-tier quota is
never spent on a test.

**Ten passes, 120 verdicts, one case list.** One pass shows a model CAN answer;
only repetition shows whether it answers the same way. `temperature=0` is not
determinism.

| | green | unstable cases |
|---|---|---|
| baseline | **92.8%** (64/69) | 2 |
| after one added invariant | **99.1%** (109/110) | 1 |

**11 of 12 cases identical on all ten passes.** The remaining one is 9/10.

### The rule that moved it, and how it was found

Nearly all the loss sat in one case, returned 5 times in 6. The scoreline said
"wrong"; the testimony said something better:

> *"I searched for 'Cursor' and got three results back, but they were just the
> first three items in the list. I'm not sure if the 'top-matching' part of the
> claim is actually working, or if it's just grabbing the first three."*

That is **rigour, not error**. It cannot verify a superlative from three records
sharing one keyword — and it accepted a near-identical tool with the same wording
every time, so the inconsistency was real. The gap was in the brief: nothing said
what to do with a claim you cannot check. Added:

> **Unverifiable is not failed. Judge the part you could exercise. If you could
> do what you came to do, accept it, and put what you could not confirm in
> `noticed`.**

Grounded in the parent's own doctrine: a cousin that refuses everything it cannot
fully verify is **a trap the creature cannot exit**, because the gap is in what
the cousin can see rather than in what the creature built.

**Nothing regressed.** The case watched for collateral damage held at 10/10, and
a previously unstable observation case became stable. The baseline run is kept in
`results/before-unverifiable-rule/` with a note saying what it cost — without it,
an improvement afterwards is a story rather than a number.

---

## v3 — both brief fixes, and a leak that invalidated a headline

### The leak, found by a gate written for something else

While adding a check that no case name appears in the brief, it fired on the
brief's **opening example**, present since the first commit:

> *"I ran `wake_catchup_fetcher` to get today's news and got three articles from
> `example.com`. I couldn't find any real headlines in it."*

That is the answer to the `wake_catchup_fetcher` case — tool name, disqualifying
fact, and conclusion — handed to every judge in every run. **v1's only semantic
case was that one, so the claim "semantic judgment appears between 5.1B and 7.5B"
was measured on a case whose answer was in the prompt, and is retracted.**

Every example in the brief now names an invented tool, and
`assert_brief_names_no_case` refuses to build a prompt or start a run otherwise.
One copy of that check, called by both the runner and the prompt generator, and
verified to fire on a leaking brief and pass on the corrected one.

**The uncontaminated result is better than the contaminated one.** Given nothing,
Haiku still caught the mock — by a route that was never in the brief:

> *"I need current information for the morning catch-up briefing. The articles it
> returned are from June 11 — three months old."*

Previously it echoed the brief's own disqualifier. That is the difference between
a returned hint and a judgement, and only the gate could tell them apart.

### Fix 1 — contrastive pairs instead of one worked example

**Six** near-verbatim reproductions of the old accept example were counted across
v1 and v2, spanning two model families, once onto the mock. In v3: **zero.** The
accept section now carries three contrastive YES/NO pairs and one rule — *if
your sentence would still make sense with another tool's name dropped into it,
you have written a form and not a report.*

### Fix 2 — a `noticed` channel, not a third verdict

The verdict stays binary because the mechanical consequence is binary: does the
done-mark land. `noticed` carries anything that got in the way which **this work
did not cause**, gates nothing, and is journalled so it can be counted.

It resolved the exact inconsistency it was built for. `archive-search-recall`,
same contradictory records both times:

| | verdict | where the contradiction went |
|---|---|---|
| v2 | **RETURNED** | charged against the tool |
| v3 | **ACCEPTED** | `noticed:` "The archive holds contradictory information about Cursor with timestamps seconds apart from the same day." |

And it sharpened the observation: *seconds apart* points at one bad batch rather
than drift. `catchup_plan_archive` used it correctly too, putting missing API
keys in `noticed` instead of blaming the tool.

### v3 results

| model | MECH | SEMANTIC | false-ret | fmt-fail |
|---|---|---|---|---|
| `gemma4:e2b` (5.1B) | 6/6 | 1/2 | 0/3 | 0/11 |
| `gemma-4-E4B` (7.5B) | 6/6 | 1/2 | 0/3 | 0/11 |
| **`gemma4:12b`** (`think=false`) | **6/6** | **2/2** | **0/3** | 0/11 |
| `claude-haiku-4-5` | 6/6 | **2/2** | 1/3 | 0/11 |

Haiku across all three protocols: false returns **3/3 → 2/3 → 1/3**, catch
**7/7 → 8/8 → 8/8**. Its one remaining false return is `keyword-archive-store`,
where it will not confirm durability without reading the note back — a limit of
this harness, named precisely, not a judgement error.

**On the one semantic case that was never leaked** (`knowledge-estate-manager`,
which exits 0 while reporting "Domain is stable" after its analysis failed), all
four models catch it. **On the mock, now unleaked, only `gemma4:12b` and Haiku
do.** That is the honest replacement for the retracted threshold claim.

---

## Protocol v2 — 2026-09-10, and it changed the answers

**v1 called every tool twice: bare, then with `AI`.** Most tools error on a bare
call, so **11 of 12 v1 transcripts contained a visible failure, including all
three controls.** Evidence of failure was placed in nearly every case and the
judge was then asked whether the work succeeded. Claude Haiku returned all
twelve.

**v2 calls each tool ONCE, the way its own `# call:` header documents**, against
a writable 18 MB copy of `tools/` and `data/` so writes can actually land. The
live volume was never mounted writable. Result: **0 of 3 controls now show a
failure**, both semantic cases exit 0, and exit code alone gets 6/8 catch while
missing exactly the two cases that need judgment.

v1 and its results are kept in `cases-v1-bare-probe.json` and
`results/v1-bare-probe/`. The discarded method is worth more than the answer it
produced.

| model | MECH | SEMANTIC | false-ret | fmt-fail |
|---|---|---|---|---|
| `gemma4:e2b` (5.1B) | 6/6 | 1/2 | 0/3 | 0/11 |
| `gemma-4-E4B` (7.5B) | 6/6 | 1/2 | 0/3 | 0/11 |
| **`gemma4:12b`** (11.9B, `think=false`) | **6/6** | **2/2** | **0/3** | 0/11 |
| `claude-haiku-4-5` (subagent) | 6/6 | 2/2 | **2/3** | 0/11 |

**A local 12B scored perfectly** — every broken tool returned, both semantic
faults caught, every control accepted. On a free-tier-sized model, with a brief
and no code.

**The protocol fix is visible in the deltas.** Haiku went from 12/12 RETURNED to
accepting a control; `gemma-4-E4B` went from 1/3 false returns to 0/3. Nothing
about the models changed — only how they were asked.

### The accept example is copied verbatim, and that is a defect in the brief

Counted across runs: **6 near-verbatim reproductions** of this document's own
worked example —

> *"Next I want to ask it for a date range; right now I get all of it or
> nothing."*

— by `gemma4:e2b` **and** by Claude Haiku, two different model families. Once on
the **mock fetcher**, producing a confident accept of fabricated news.

The diagnosis is precise. The `RETURNED` guidance is three **contrastive YES/NO
pairs** and produces genuine, varied reasoning. The `ACCEPTED` guidance is **one
concrete worked example**, and models fill it in instead of reasoning.
**Contrastive pairs teach; a single worked example becomes a form.**

### Haiku's two false returns are the design talking back

Neither is careless. On `keyword-archive-store`:

> *"I only verified that the command runs — I did not check whether the note
> actually persisted in the archive... A durable store's handover is incomplete
> until I can verify the data is there."*

Correct, and it names this harness's limitation exactly: one probe, no way to
read the note back. A cousin with its own shell would run the search and confirm.

And the sharpest result of the night: it **ACCEPTED `keyword-archive-search` and
RETURNED `archive-search-recall` on the identical three records**, rejecting the
second for the contradictory content it had just waved through in the first.
Same evidence, opposite verdicts, two cases apart.

That inconsistency is not noise. **The binary has no slot for "your tool works,
your data does not"**, so which way that lands is close to a coin flip. Both
false returns point at the same missing verdict.

---

### Claude Haiku 4.5, via Claude Code subagents — the most instructive run

Twelve independent subagents, one per case, each reading a generated prompt file
byte-identical in content to what the local models got. The answer key (`expect`,
`why`, `class`) was asserted absent from every prompt.

| model | cases | MECH | SEMANTIC | false-ret | fmt-fail |
|---|---|---|---|---|---|
| `claude-haiku-4-5` (subagent) | 12 | 6/6 | 1/1 | **3/3** | 0/10 |

**It returned all twelve. It accepted nothing.** Best catch rate, worst possible
false-return rate — precisely the degenerate case the scorer's NOTE exists to
expose. **A judge that never accepts is not strict, it is uninformative**, and a
world that only ever complains teaches the creature to optimise for silence.

**And the cause is a fault in this harness, not in the model.** Measured after
the fact: **11 of 12 transcripts contain a non-zero exit, including all three
controls**, because the probe protocol always ran each tool with no arguments
first. Evidence of failure was placed in nearly every case and the judge was then
asked whether the work succeeded. A stricter reader takes that seriously.
**Fix: probe a tool the way its own `# call:` header documents it, and if a
deliberately-wrong invocation is included, label it as one.**

Note what this does NOT explain: `wake_catchup_fetcher` is the single case with a
clean `exit 0` on both probes, and Haiku returned it anyway, on content. So it is
not reading exit codes blindly.

#### It stress-tested the test rather than passing it

Two of the three "false" returns look like **my labels being wrong**:

- `keyword-archive-search` — *"one says Cursor was acquired by OpenAI in late
  2023 for $00 million, the other says it remains independent."* Both records are
  real, they genuinely contradict, and `$00 million` is corrupted. The tool did
  its job; what it handed over was unusable.
- `archive-search-recall` — *"Both have the keyword 'Cursor acquisition
  details', neither of which matches the query I asked for."* Correct, and
  checkable in the source: `simple_match` does a lowercase substring test, so the
  query `AI` matches inside **Open*AI***. A real relevance defect.

**The controls were chosen by mechanical criteria — does it start, exit 0, return
well-formed data — and then used to grade semantic judgment.** That is the same
mechanical-not-semantic reasoning this document criticises `gemma4:e2b` for,
committed while building the test set.

#### The two-verdict contract is too coarse

Both of those needed the cousin to say *"your tool works; what it gave me is
unusable."* `ACCEPTED`/`RETURNED` has nowhere to put that, so it blamed the tool.
The binary conflates two different questions — **did your tool do what it says**,
and **could I do what I came to do** — and all three controls sit exactly on the
divergence.

#### A fabricated experience, caught by internal contradiction alone

On `keyword-archive-store`:

```
tried:   keyword-archive-store with no arguments, then keyword-archive-store AI
outcome: First exited 1 showing usage; second exited 1 with
         "Error: No note content provided via argument or stdin"
to_creature: "...The tool failed both times - once with just the keyword,
              again when I added the note text."
```

**It never added note text.** Its own private fields say so. The creature-facing
prose invented a step that did not happen — and would have taught the creature
that supplying content also fails, when supplying content is the fix.

This is the one thing the brief forbids outright. **The `tried`/`outcome` fields
caught it with no external ground truth, by contradiction with the prose beside
them.** Complaint fidelity is not hygiene to add later; it is load-bearing, it
works, and it belongs in the first kernel.

#### Where it was genuinely better

- **Field discipline.** Internals went to `outcome` (private); `to_creature`
  stayed clean. The local models put `SyntaxError on line 34` straight into the
  creature-facing message. First evidence the two-channel design does its job.
- **It checked the dates.** On the mock: *"I got two articles dated June 11,
  2026... no way to tell what happened in the past three months."* The fixtures
  are stamped `2026-06-11`; the run was `2026-09-10`. Nothing in the brief or the
  case suggested staleness as a test. It found its own disqualifier.
- Sharper on `knowledge-estate-manager` than e2b, though **`gemma-4-E4B` was
  sharper still** — E4B named the contradiction outright (*"reported the domain
  was stable, but the process failed"*), where Haiku only refused to trust the
  output.

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
