# PLAN.md — the board, with the test that says each one is done

Written 2026-09-16. Every open item this project knows about, in the order they
will be done, **one at a time**, each with acceptance criteria that can be
checked rather than asserted.

**Three hard rules, all earned:**

- **AN ITEM THAT NEEDS TUE CARRIES A QUESTION HE CAN ANSWER WITHOUT THIS
  FILE.** Tue, 2026-09-21: *"the list is vibe-coded as much as everything
  else, I have no idea what 19.5 means, and the gates and decisions about them
  are made by you or your predecessor before compaction, so to say it is mine
  is always a bit awkward."* He is right. 19.5 sat for four days labelled
  *Tue's, because it is his account*, and was never once put to him as a
  sentence. **Filing something under his name is not deferring to him; it is
  parking it.** So: no item is marked his without a plain-language question
  written out beside it -- no item number, no jargon, what is being asked and
  what each answer costs. If it cannot be written that way it is not his
  decision, it is mine, and the rule at the top of `CLAUDE.md` §0 already says
  to take it.

- **The test comes first and is seen RED before the fix exists.** *A test that
  has never been seen red is a guess* (`CLAUDE.md` §5, the `shlex.quote` scar).
- **An independent reader verifies each item against these criteria** — not
  the session that built it. A builder judging its own work knows what it
  meant, which is the whole reason the cousin exists (§4).

**Pacing:** one deployed change in flight at a time, each getting its
`deploy_regression` hour (`live/monitor/regression/`) before the next starts.
Doc updated in the same turn as the code (§5, *a defect named in a turn is
dispositioned in that turn*).

Status: `[ ]` not started · `[~]` in flight · `[x]` done and verified.

---

## WHERE THE BOARD STANDS — 2026-09-24

Tue, 2026-09-21: *"then lets get the board cleared."* It is, as far as work
can clear it. **Every heading that is not `[x]` is in the table below, and that is the whole list.** What is left is not work anybody can do tonight, and the distinction matters more than any count:

> **No number here, deliberately.** The first version of this sentence said *twenty of twenty-one*; the true figure was fifteen of twenty-one, and the table underneath it listed six open lines, so the paragraph contradicted itself. Found by a verifier, not here. `CLAUDE.md` §0 already refuses to write the gate's assertion count down for exactly this reason -- *a count in prose is a constant nobody chose, obeyed forever* -- and the rule was not applied to the board. It is now: the table IS the claim, and it can be checked against the file.

| still open | why, in one line | what would move it |
|---|---|---|
| **11** run 3 | Tue's call, and he made it: it waits for an empty board | this table reaching zero |
| **14.5** tell the creature `say` exists | **BUILT 2026-09-24, not deployed**: a served "Your hands" block, read from each installed hand's own header, announces `say` and every hand added later. The guard that held `say` as an exception now requires a header instead | deploy after `3a6a642`'s day-reading, 2026-09-25 ~17:47, with 21.2 |
| **16** the cousin notices a tool serves nothing | the rule can be drafted; scoring it spends the same tier the live run is on | 20.4, then score under item 8's discipline |
| **17.3** the deciding half | moves with 16 by construction | 16 |
| **20.4** the cousin carries ONE note and has not added a second | 59 harvests carry it, none empty since 09-19, and the last 40 all carried exactly one key — continuity proven, accumulation not | a week of 20.2, read beside the store's key count |
| **21.2** the rewrite wall | **HAND BUILT 2026-09-24, not deployed**: `tool-replace`, SEARCH/REPLACE, all-or-nothing, whole lines only. The read side landed on 09-24 as a WHOLE-PAGE budget after 40k wedged the engine (§5). Local rehearsal of whether a model USES the hand is written and has not run -- the GPU was taken | deploy with 14.5; rehearse on the Windows bench when its GPU is free |
| **22.1 / 22.2** | a fence inside a heredoc, and the cost of re-reading a journal that only grows | both named and dated in item 22 |
| **23.3** the creature is promised an LLM API its box may not have | 80 runs against `api.openai.com` with the literal `"default_key"` | a design decision, not a patch — see item 23 |
| **23.4 / 23.5** the same audit on the cousin's brief and the kernel's served text | **23.5 found two and fixed both in code, 2026-09-24**: the framework served a completion claim on 220 of 246 visits that had none, and the cousin could only note what it knew BEFORE seeing output. Scored on `gemma4:12b`: arm A (deployed) 24/24 caught, 9/24 falsely returned; arm C (the truthful framing) not yet run. **Staged OFF** behind `Engine.TRUTHFUL_VISITS`, proven byte-identical to the deployed prompt (15 of 15) while off, so it rides the creature-side deploy dormant. **23.4 read in full 2026-09-24**: seven presuppositions recorded, one hypothesis refuted, nothing changed | arm C, then a one-line commit flipping the switch, deployed in its OWN window |

## NEXT STEPS, IN ORDER — written 2026-09-24 evening

**Where things are.** Running on the laptop: `3a6a642` (the whole-page budget
that ended the 09-24 wedge). On GitHub and NOT on the laptop, on purpose:
everything from `c3f8c3d` on. Pulling is a deploy, so the order below is the
deploy order. Each step says who does it, what triggers it, and what has to be
true before the next one starts.

| # | step | who | trigger | done when |
|---|---|---|---|---|
| 1 | **Read `deploy_regression_day` for `3a6a642`** -- the first valid day of this week's read-side changes (the 09-23 night was lost to an outage, 09-24 to the wedge) | Claude, at the daily check | 2026-09-25 ~17:47 | the page shows reads of `plan` against writes, and `context_outgrew_rung` has stayed quiet. If it alarmed: stop and read §5's wedge scar before anything else |
| 2 | **Pull and deploy `HEAD`**: the hands block (announces `say` and `tool-replace`), the partial-edit hand, the `tool-edit` fix. The cousin-side change rides along DORMANT (`TRUTHFUL_VISITS = False`, byte-identical to today's prompt) | Claude, four separate commands | step 1 read | `selfcheck` all-true; the wake records `hands_served` equal to the installed hands; page under `CONTEXT_BUDGET_CHARS` |
| 3 | **Finish the local scoring on the Windows bench**: arm B (new text as a done-claim), arm C (truthful stall framing), and the `tool-replace` rehearsal on the real 12 KB `plan` | Claude, **when Tue says the PC is free** -- it needs ~8 GB of the card for ~30-60 min | Tue | arm C is not worse than arm A (24/24 caught, 9/24 falsely returned) on either half; the rehearsal shows whether a model given the hands block uses `tool-replace` and lands a change that still runs |
| 4 | **Read the creature-side deploy a day later** | Claude | step 2 + 24 h | did the creature use `tool-replace`; did writes of `plan` rise above 0; `truncated\|lost` unchanged |
| 5 | **Flip `TRUTHFUL_VISITS` to True** in a one-line commit and deploy it ALONE | Claude | step 3 clean AND step 4 read | a day-reading of its own. Decide from arm C whether the brief's *"what it just built"* sentence (23.4) must change first -- if so, that change is scored as its own arm |
| 6 | **Remove the switch and the legacy framing** | Claude | step 5 has run a clean week | the code path is gone and the gate still green |
| 7 | **Read the cousin's memory store** -- does it now hold more than the one key it has carried since 09-19 (20.4)? | Claude | a week after step 5 | a count of keys over time, beside what the cousin actually noted |
| 8a | **Stop the creature's thinks from trying Groq at all.** Its page (~14k tokens) can never fit Groq's 8,000 TPM, so every fall-through to it is a guaranteed `413`: ~350 requests a day to a SHARED account, **0 answered since 09-21**. A limiter, not a judgement: a rung is skipped for a request larger than that rung's recorded per-request ceiling | Claude | before 8b, in its own window | groq requests from creature thinks ~0; cousin calls to groq unchanged |
| 8b | ~~An `ask` hand aligned with the spine's, via a keyless relay~~ -- **SUPERSEDED by Tue the same evening, 2026-09-24**: *"this fake subagent running on the creatures own api is actually something to stop on both growing-spine and never implement here, and instead give it the truths: you cant have a real llm access, but you can use your own api to send an unbiased request if thats needed say for a test - and thats it really."* So: **no subagent orchestration, here or ever; the creature's prompt tells it the truth** (its tools have no LLM behind them). **One question open to Tue:** does *"an unbiased request, say for a test"* mean (a) a single stateless `ask` -- fresh model, no memory, described as exactly that and never as a subagent, key held by a relay outside the box -- or (b) no model call from its tools at all. Claude leans (a): an unbiased check needs a fresh context, and its own thinking carries its transcript | **Tue: (a) or (b)**; then Claude | after 8a | the prompt's starter map no longer names subagent orchestration; whatever it DOES promise is true inside the box (`selfcheck`-style, by effect) |
| 8c | **The spine side is Tue's, not this repo's** (§2.6 forbids touching it). Recommendation recorded for the spine: its framework `ask` is used from 124 of 929 tools, and 4 more call raw keys directly -- if the fake-subagent pattern is to stop there too, it is that project's change to make | Tue / a spine session | -- | -- |
| 9 | **16 / 17.3** the cousin noticing a tool serves nothing | Claude | step 7 | the rule drafted and scored under item 8's discipline |
| 10 | **11, run 3** | **Tue's gate** | this table reaching zero | -- |

**Standing, not scheduled:** 22.1 (a fence inside a heredoc) and 22.2 (journal
re-read cost) stay latent with their named triggers -- zero occurrences, and
this project has paid for fixing a zero-occurrence fault in the parser before.


**None of these is blocked on a decision that has not been taken, and none is
waiting on "more information"** — each names a trigger and a date, which is
CLAUDE.md §4's test for a real hold. **17.4 is not on the list because it is a
standing statement rather than a task**: framework debugging, tests and
doctrine stay with an agent that has the repo, the gate, and a verifier that
did not write the change.

---

## Phase 0 — clear the board (no engine restart)

### 1. `[x]` The complaint-fidelity census runs by itself

`census.py` is the only thing that checks the manager — `CLAUDE.md` §6.1's
oldest open item — and nothing has ever invoked it on a schedule. An
instrument that exists and is never run is the *dead channel* scar in a new
costume.

- **1.1** `complaint_fidelity` is in `monitor.detectors.ALL`.
- **1.2** A verdict claiming an exit code its probe never produced → **ALARM**,
  `human=True`, naming the tool and the claim.
- **1.3** Verdicts that match their probes → **OK**.
- **1.4** No probe/verdict pair at all → **CANNOT_TELL**, never OK. *"That is
  not a clean bill; it means the instrument has never run."*
- **1.5** The page carries a runbook line for it.
- **1.6** It derives from `census.check` rather than re-implementing the rules
  — one producer, one checker, no drift.
- **1.7** It reports and never gates: the monitor writes nothing outside
  `live/monitor/`, still asserted.

### 2. `[x]` The chat channel is a scheduled intention, not a silence

Tue, 2026-09-16: **it stays.** It has sat in every "not built" list since
2026-09-11 without ever being decided either way.

- **2.1** No document describes it as merely *not built*; each states it is
  wanted, and scheduled as item 14.
- **2.2** The reason for the slot is recorded: it adds a surface to the
  creature's context, so it must not land while phases 3–4 are measuring.

### 3. `[x]` The inherited library is recorded as NOT executed

§6.2 says *"Decided 2026-09-10: copy"*. Run 2 started from nothing. The
doctrine claims a thing that never happened, and the refutation path it was
chosen for — a known-answer test set — was never taken.

- **3.1** §6.2 states the decision was not executed and why.
- **3.2** It is bound to run 3 (item 11) with the tagging requirement intact.

### 4. `[x]` The cousin's audit has a named trigger

§6.4 currently ends *"No named trigger yet — this needs one."*

- **4.1** The trigger is stated: **when the cousin can invoke tools with
  arguments (item 9)**.
- **4.2** The reason is stated: an audit by an agent that can only run things
  bare is confident garbage by construction.

### 5. `[x]` The evidence tarball's home is recorded

Tue, 2026-09-16: **laptop only**; the hashed manifest is what the repo
carries.

- **5.1** `CLAUDE.md` §0 and `deploy/README.md` say so without hedging.
- **5.2** `.gitignore` keeps `evidence/*.tar.gz` out of the repo.

---

## Phase 1 — make the untriggered paths triggerable

### 6. `[x]` The fault-injection rehearsal

Eight board items in one build. These paths are deployed and have **never
once fired in production**, so "it works" rests entirely on the gate — and
the gate structurally cannot test the systemd half.

- **6.1** The rehearsal refuses to run against the live root. Asserted, not
  intended.
- **6.2** **Give-up drill:** the real `run.py` under a throwaway user unit,
  its wait budget exhausted → exit **5** → `Restart=on-failure` fires →
  `StartLimitBurst` bounds it → the unit ends in `failed` for real.
- **6.3** **Body drill:** the body killed mid-run → `body_respawn` in the
  scratch journal, and infrastructure failure never reaches the creature
  shaped like its own output.
- **6.4** **Walled-rung drill:** a rung that rejects credentials →
  `rung_broken` journalled, `expected=False`.
- **6.5** **Disproven-bound drill:** a unit missing `PrivateUsers=yes` →
  `selfcheck` records `home_write_blocked=False` and the engine still starts.
- **6.6** Each drill leaves a scrubbed fixture in `tests/fixtures/journal/`,
  and the gate asserts the matching detector fires on it: `gave_up`,
  `engine_silent`, `journal_integrity`, `tool_vanished`. These four have no
  red-proof from real data today.
- **6.7** No drill creates or removes a path anywhere under the live
  root, watched across the whole run rather than inside one drill, with
  the baseline taken before the harness's own first destructive act.
  **Byte-identity is deliberately NOT claimed against the running
  deployment**, and the earlier wording of this criterion did claim it:
  the engine appends to the journal every few seconds and the creature
  rewrites its own tools, so everything under that root is its churn by
  definition, and a checker promising bytes there would report a breach
  on every run -- the oldest scar in this project, in the instrument
  built to catch breaches. Where nothing is writing the root, bytes ARE
  decidable and are asserted: `live_snapshot(digest=True)`, and the gate
  drives a real drill at a simulated live root and requires every file
  under it unchanged to the byte. Corrected 2026-09-16 after a verifier
  found the prose promising more than the instrument delivered.

---

## Phase 2 — close the oldest security hole

### 7. `[x]` The creature's shell cannot read the engine's keys

Open since 2026-09-13 and named in §7 as Tue's. The child environment is
already an allow-list; the key **files** remain readable by anything running
as this uid.

- **7.1** From inside the live body: `cat ~/keys/*.key` fails.
- **7.2** The engine itself still reaches every rung — it reads those files
  per call.
- **7.3** The effects this deployment relies on are checked from inside the
  sandbox before it ships, and re-checked at every start.

  > **CORRECTED 2026-09-16.** This criterion used to list *six effects, as on
  > 2026-09-13*, two of which were **reads the repo** and **reaches both
  > providers**. Those were the `LocalBody` era's list, where the creature
  > could see the repo and where reaching a provider from inside the shell
  > was possible at all. Under the container both are deliberately FALSE --
  > the drill records `engine_repo_invisible: true`, which is the opposite of
  > what the criterion asked for, and reaching a provider from inside is
  > exactly what 7.1 forbids. A verifier read the board against the work and
  > found the board describing something that did not happen.
  >
  > Carrying a criterion forward across a design change is how a checklist
  > stops describing the system. What is actually proven is stronger and is
  > listed where it is measured rather than typed here: every boolean in
  > `tests/fixtures/journal/0916-drill-docker.evidence.json`, containment and
  > capability apart, including the mount options by effect
  > (`hands_read_only`, `not_root`, `uid_matches_the_host`); plus the set
  > `selfcheck` re-proves at every start, which records and never vetoes.
  >
  > **No count is written here on purpose.** The first draft of this
  > correction said "17 effects" from memory; the file holds 26. A count in
  > prose is a constant nobody chose, obeyed forever -- the first fault this
  > project's doctrine names, and the reason the gate count is not written
  > down either. Read the file.
- **7.4** Rehearsed under item 6 before it goes live. *A sandbox that breaks
  the run is discovered at 03:00 by nobody.*
- **7.5** `selfcheck` gains the assertion, so the bound is re-proved at every
  start rather than once.

---

## Phase 3 — unfreeze the brief

### 8. `[x]` Held-out cases, so a brief change can be scored

The unfreeze condition written in §0 and never built. Until it exists every
question about the cousin's **judgement** is unanswerable, and items 9 and 10
have no scoreboard.

- **8.1** A held-out case set, physically separate from the tuning set, that
  the current brief has never been measured against.
- **8.2** One runner reporting **detection and correction together** — never
  one without the other (§5, 2026-09-11).
- **8.3** `assert_brief_names_no_case` covers the held-out set too: a brief
  that names a case under test refuses to run.
- **8.4** A recorded baseline for the frozen brief, split by model.
- **8.5** §0's unfreeze condition is marked satisfied, with the instrument
  named.

> ## 8.4 — THE FIRST BASELINE, 2026-09-16 02:00
>
> `gemma-4-31b-it`, one rep, engine paused so the tier was not being shared
> with it, quota-polite waits (one case took six minutes of backoff):
>
> | | |
> |---|---|
> | **detection** | **caught 7 of 8** tools whose interpreter refuses them |
> | **false-return** | **5 of 8** tools that demonstrably ran were REFUSED |
> | unreadable | 2 of 16 — neither caught nor missed; that measures the rung |
> | correction | **NOT MEASURABLE**, and the runner says so rather than printing detection alone |
>
> **The detection half is strong and the false-return half is not**, and that
> asymmetry is the first thing this instrument was built to be able to see.
> §5 already records a rule that *"regressed genuine repairs 5/5 → 1/5 while
> catching nothing"* and was reverted rather than layered over; this is the
> same shape, now visible on cases the brief was never written against.
>
> **Two limits, stated before anyone quotes the number.** It is ONE pass on
> ONE model — the file's own rule is that a direction surviving several
> windows is a signal and one number moving is not. And the ACCEPTED label
> means *the cousin ran it and it exited 0 with output*, which is weaker than
> *it did what its header claims*: some of those five refusals may be right,
> and finding out means reading the five transcripts, not adjusting a rule.
>
> `trial/baselines/baseline-frozen_gemma-4-31b-it.json`.
>
> **Status 2026-09-16: 8.1–8.5 done.**
> `trial/heldout-cases.json` carries 16 cases — 8 parent tools whose
> interpreter refuses them (read statically; §2.6 forbids running one) and 8
> of our own tools the journal records running to exit 0 with output. None is
> in the training set, and the generator refuses to emit one that is.
> `trial/score_brief.py` runs both halves and cannot print detection alone.
>
> **The first baseline attempt returned sixteen `HTTP 429`s** — the free tier
> is shared with the live engine, and at 01:07 it had nothing to give. The
> scorer reported `caught 0/8` over those, which reads as a brief that catches
> nothing; that is now refused as NOT MEASURABLE, which was worth finding.
>
> **Trigger for 8.4: run it when the tier is quiet** — the engine paused, or
> a window where `ladder_dry` has been clear for an hour. The command is in
> `score_brief.py`'s docstring. Several reps, split by model, before any
> number here is treated as a baseline rather than an anecdote.

---

## Phase 4 — the boundary question

### 9. `[x]` The cousin gets its own shell  — DONE; 9.5 read 2026-09-21

> **9.5 CLOSED 2026-09-21, on the one figure the spine cannot move.** Bare
> probes went **93% before the shell to 8% in the window after it** (18 of 211
> with the old caps, 27 of 130 after), and the cousin composes real
> invocations: 96 of 179 probes with a recorded command are more than one
> command, and 54 capture the output of one into another. Rates are NOT
> compared across the window -- the caps changed inside it (item 13) and the
> spine went off and on -- which is why the bare SHARE, a property of what the
> cousin can do rather than of how often it got served, is the figure this
> item turns on.

Tue, 2026-09-16, choosing the direction. §4 assigns *running the test* to the
cousin, and the framework only ever invokes a tool **bare** — so the cousin
owns a job it structurally cannot do, and has produced two days of
accepts-on-a-usage-line. §5 has said *"untestable until the cousin has its own
shell"* since 2026-09-10.

- **9.1** The cousin has a body of its own, separate root from the creature's.
- **9.2** It chooses its own invocation. The framework never composes one from
  the `# call:` line — that would move judgement into the 99% we deleted.
- **9.3** What it actually ran is journalled, not just the tool name.
- **9.4** **§2.3 holds structurally, not by a guard keyed on a literal:**
  nothing the cousin runs can change the creature's `tools/own`. Proved by
  digest across a visit in which the cousin deliberately tries.
- **9.5** Measured against a recorded BEFORE window, split by rung.

> **Live 2026-09-16 01:42, engine `28c4eda`.** The cousin has its own
> container (`growing-cousin-body-user`), no hands, and an empty world until
> its first visit — the library is copied in per visit and discarded with
> whatever it did to it.
>
> **Corrected criterion.** 9.5 first said *"measured against item 8's
> baseline"*, and that was wrong: item 8 scores the BRIEF against fixed
> transcripts, so it cannot see a change in how the transcript is produced.
> Giving the cousin hands changes production, and production is where it must
> be read. Keeping the wrong instrument named would have been the
> *checker that cannot distinguish the thing it measures* in the plan itself.
>
> **THE BEFORE WINDOW, from the page at 01:16 (engine `a8c4e43`, bare
> probes):**
>
> | | |
> |---|---|
> | probes | 4 worked / 41 asked-for-arguments / 0 failed |
> | wants | 16, **11 distinct — one of them six times** |
> | standing alarms | `want_repeated`, `probe_stuck`, `window_reread` |
> | library | 46 tools; `archive-*` ×10, `plan-*` ×9, `subtask-*` ×6 |
>
> **What to read after:** the *asked-for-arguments* column should collapse —
> a probe that chose its own arguments is not a bare call — and
> `want_repeated` should clear if the repetition was the cousin being unable
> to verify what it asked for. If the want still repeats with the cousin
> holding real hands, that is the anti-twin JUDGEMENT question isolated at
> last (§5, 2026-09-14), and it is a brief matter needing item 8's scoreboard.
>
> Two things to watch, both costs of this change: it spends **two** cousin
> calls per visit instead of one, on a tier that is already thin; and the
> cousin now runs arbitrary bash of its own choosing, which is why it does so
> in a container with a copy.

> **THE BEFORE WINDOW, RE-CUT 2026-09-16 02:45 AND SPLIT BY RUNG**, because
> the table above is not. An aggregate over a heterogeneous ladder measures
> neither instrument (§0), and 9.5 asks for the split in as many words.
> Twelve hours of journal ending at the moment the shell went live:
>
> | | |
> |---|---|
> | probes | **38** — 34 bare (no arguments possible), 4 unflagged old-path; 5 exited 0 |
> | verdicts by rung | `gemini/gemma-4-31b-it` ACCEPTED 15, RETURNED 2 · `cloudflare/llama-3.3-70b` RETURNED 1 |
> | wants | 15, **8 distinct** |
>
> **THE FIRST HOUR OF THE SHELL IS DISCARDED, and why is the finding.**
> Between 01:42 and 02:47 the journal holds **9 triggers fired** (5
> `TOOL_WRITE`, 4 `DONE_CLAIM`) and **0 `cousin_probe`**. Nine visits were
> summoned and every one vanished without trace: choosing the invocation is a
> model call, every rung was at 429, and the exception left `evidence()`
> before anything was appended. So that hour cannot be compared with anything
> — its probe count is an undercount of unknown size — and it is thrown away
> out loud rather than folded into the after-window.
>
> Fixed the same night; a probe that reaches nobody is now recorded as
> `chosen_by="ladder_dry"` with `exit_code=None`, and no consumer counts it
> as a run or a failure.
>
> **AND THE WINDOW RESTARTS AGAIN WHEN THE SPINE IS BACK UP.** It must be
> taken spine-ON to be comparable with the spine-ON before-window (69 probes,
> 27 verdicts, 25.5 h). The 18:36-18:50 sliver was spine-on, the gap after it
> was not, and nothing happened in either — 0 probes — so nothing is lost by
> restarting the clock at the moment the spine returns.
>
> **CONFIRMED IN PRODUCTION 2026-09-16 18:5x — the cousin's shell works.**
> Seven probes in the first twenty minutes, six of them commands the cousin
> composed itself:
>
>     compare-against-baseline parent123 parent124     exit 0
>     list-parent-tasks                                exit 0
>     view-subtask-logs task-123                       exit 1
>     compare-subtask-logs-baseline parent123 base     exit 1
>
> `view-subtask-logs` had been called **54 times bare** and had never once
> returned anything but its usage line. It has now been run WITH an argument
> and exited 1. That single row is the first real knowledge this project has
> ever had about that tool, and it is what item 9 was for.
>
> **THE CHOOSER CHANGE OF THE SAME EVENING IS HELD, NOT SHIPPED.** `b7d5e96`
> makes the probe go to tools whose outcome nobody knows. It is committed,
> gated and red-proven — and it is NOT deployed, because it changes WHICH
> tool gets probed, which is the very thing this window measures. The
> before-window was taken with the old chooser; shipping a new one inside the
> after-window would mix two changes and leave neither attributable. §5's top
> scar, exactly.
>
> **Trigger to deploy it: when this window closes (2026-09-18).** Until then
> `restart_owed` will correctly say a restart is owed, and it is owed
> deliberately.
>
> **REOPENED AGAIN AT 2026-09-16 20:14:20 (engine `1d3ff99`), AND THIS TIME THE INSTRUMENT WAS READ FIRST.**
> Tue's review request found four faults in the shell path itself (§5,
> 2026-09-16 "read end to end"): `bare=False` hard-coded, so a rejected
> invented ID rendered as a real failure; a cousin world missing `state/`
> and the `recall`/`remember` hands two tools depend on; a container reused
> with stale mounts after the deploy that changed them; and a cousin body
> never proven before use, so its death would have become a verdict. The
> 18:36 and 20:06 windows measured a shell with those faults in it. The
> record from 2026-09-16 20:14:20 (engine `1d3ff99`) on is the first taken with the shell whole. Read it
> no sooner than 48 hours in, and read `lost` beside the exit columns.
>
> **The library line changed under both inhabitants in this window** — the
> word FAILED became exit codes beside verdicts. That is a context change
> and it is inside the window on purpose: the alternative was measuring a
> cousin against a display that told it a tool it had just used correctly
> had NEVER WORKED. The change is one-way and dated; nothing before it is
> comparable on the "what the library said" axis, and nothing needs to be.
>
 Reopened
> 2026-09-16 18:36:16, engine `9a90303`.** Fifteen hours produced **112
> probes, 112 of them lost, 0 verdicts, 0 wants** while the creature thought
> 112 times on the same rungs. The cousin's shell had never once worked: the
> command-choosing call was asked through the ladder that rejects any reply
> without a VERDICT block, so every model that answered correctly was judged
> unusable and every rung walled. See §5.
>
> **Item 9 was therefore not "live" between 01:42 and 18:36 in any sense that
> matters** — it was live and inert, which is the state this project's
> doctrine says is hardest to see. Read the after-window from 18:36 only.
>
> **THE AFTER-WINDOW STARTS 2026-09-16 03:19:13, ENGINE `fb3d18a`.** It was
> opened at 02:49 on `02d3460` and re-opened half an hour later rather than
> left to span two engines: §0's rule is that every figure names its
> instrument, and a window whose code changed inside it names two. Half an
> hour was the whole cost of keeping that clean. That start also reports
> `unproven: []` for the first time — `spine_unreadable` had been
> permanently null under the container because *hidden* and *absent* read
> identically, and now reads `True`.
>
> **Read it no sooner than 48 hours in**, and read `lost` beside `worked /
> asked / failed` on the page: on a tier this dry the lost count may be the
> largest number there, and a collapse in *asked-for-arguments* means nothing
> if the probes simply never happened.

> **AND BOTH WINDOWS ARE SPINE-ON — found 2026-09-16 03:05, see item 12.**
> The sibling project has been running since 2026-09-15 00:12, sharing this
> free tier, while §4 said it was paused. The after-window is entirely
> spine-on; the twelve-hour before-window above **straddles** the restart, so
> it mixes two tiers. §4 is explicit that numbers either side of that line
> are not comparable in either direction.
>
> **So the before-window is re-cut a second time, spine-on only** (2026-09-15
> 00:12 → 2026-09-16 01:42), and the twelve-hour figures above are kept for
> what they are: a mixture, labelled. If the spine-on slice is too thin to
> say anything, the honest answer is CANNOT TELL and a longer after-window —
> not a comparison across the line.
>
> **One correction to the table above**, from the same verifier: the four
> non-bare probes are described as *unflagged old-path*. They are flagged —
> `bare=False` on the old path meant the bare call was a COMPLETE call —
> so they belong on the worked side of the before-window rather than among
> the unclassifiable.

> **THE BEFORE-WINDOW THAT 9.5 IS ACTUALLY MEASURED AGAINST** — spine-on,
> so it matches the after-window's conditions. 2026-09-15 00:12 to
> 2026-09-16 01:42, **25.5 hours**, which is not thin:
>
> | | |
> |---|---|
> | probes | **69** — 64 bare, 8 exited 0 |
> | verdicts by rung | `gemini/gemma-4-31b-it` ACCEPTED 21, RETURNED 3 · `cloudflare/llama-3.3-70b` RETURNED 2 · `groq/gpt-oss-120b` ACCEPTED 1 |
> | wants | 22, **15 distinct** |
>
> **93% of those probes were bare.** That single number is what item 9 set
> out to change, and it is the one to read again after 48 hours — beside
> `lost`, because a collapse in bare probes means nothing if the probes
> stopped happening instead.

> **THE WINDOW CLOSED AT 23.3 HOURS (2026-09-17 19:31), when item 13's fix
> was deployed.** Engine `1d3ff99`, 0 restarts; spine OFF 20:14→23:56 then ON
> (Tue restarted it after the retraction) — so the first 3.7 h are on the
> other side of the spine line and the read below is taken over the whole
> window with that stated. 505 wakes / 257 thinks / 308 commands; 1,656 rung
> declines; 52 visits deferred.
>
> | | |
> |---|---|
> | probes | **88** — 66 composed by the cousin, 22 lost to a dry ladder and recorded; 33 exited 0, 33 non-zero, **18 bare (20%)** |
> | chosen because | the creature ran it **54**, unknown outcome 13, written 12, new 9 |
> | verdicts | **14** — 8 ACCEPTED, 6 RETURNED; gemini 13, cloudflare 1 |
> | wants | 8, **5 distinct — one of them four times** ("assign deadlines to tasks and list them by urgency") |
> | tools built | 9: `clear-baseline`, `get-baseline`, `plan-synthesize-completed`, `archive-link`, `archive-links`, `archive-graph-export`, `archive-graph-path`, `archive-graph-analyze`, `archive-graph-clusters` → library 60 |
>
> **9.5 is answered on the one figure the spine cannot move: bare probes went
> from 93% (64 of 69, the spine-on bare before-window) to 20% (18 of 88).**
> The cousin composes real invocations — lookups, setups, before/after checks
> — and the loop closed end to end at least twice. Rates are NOT compared:
> the before-window is spine-on and this one is mixed.
>
> **What the window found that the design did not expect, both on the board
> now:**
>
> 1. **The repeated want was two faults, one on each side.** The creature
>    could not read the 6 KB tool it was extending (item 13, above — fixed).
>    And the cousin ran `plan` BARE, accepted the usage menu with the identical
>    sentence four times running, and asked for deadlines again — while
>    `plan set-deadline` existed and it never once ran it. The brief's *"when
>    you called it wrong"* rule was written for the harness's empty hands;
>    with item 9 the hands are the cousin's, and accepting a menu it chose to
>    summon is accepting nothing. That is item 16's first concrete rule to
>    score. `testimony_repeated` now makes the form-not-report pattern
>    visible; the judgement stays the brief's.
> 2. **The `ran` reason is a hub magnet.** 54 of 88 probes were chosen
>    because the creature had just run the tool, and the creature runs `plan`
>    every cycle — `probe_stuck` fired once (5 of 8 visits to `plan`) and
>    cleared. Correct by design, costly in practice; item 18.
> 3. **Two calls per visit on a dry tier: 88 probes, 14 verdicts, 52
>    deferred.** The invocation call took the answer the verdict needed.
>    Item 18.
>
> **A new window opens at 2026-09-17 19:33:33 (engine `dd53e91`) on the new caps.** Item 9.5's question is
> answered; what this window measures is item 13's fix (does `window_reread`
> stay quiet on `plan`) and whether the deadline want gets discharged now that
> its author can read its own tool.
>
> **Restarted 2026-09-17 20:50 on `5ef847f` -- same code, new
> identity.** The history rewrite (item 19) rehashed every commit from
> `221b978` on, so the running engine's recorded `add6782` named a commit
> nobody could check out, and the page's `restart_owed` could no longer diff
> against it. Restarted so the identity on the page is a commit in the log.
> The caps are unchanged, so 19:33-20:50 is the same instrument
> under its old name (`add6782`, which the map renders as `dd53e91`); this
> window's clock is read from the restart. The journal also carries a
> start at 20:43 on the same commit marked DIRTY TREE: the two documents
> you are reading had been uploaded to the laptop a minute before that
> record was written, and nothing else; it ran one cycle on a dry tier
> and was stopped and started again on the clean tree. Three starts on
> one evening, each recorded, none of them a fault.
>
> **INTERIM READ AT 3.6 HOURS (2026-09-16 23:52), from a 10-minute watch Tue
> asked for and then stopped for the night.** Engine `1d3ff99` since 20:14,
> 0 restarts, spine OFF throughout. 65 wakes / 44 thinks / 54 commands; 204
> rung declines -- the tier was the limiting factor all evening.
>
> | | |
> |---|---|
> | probes | **17** -- 13 composed by the cousin, 4 lost to a dry ladder (recorded, not vanished); 12 exited 0, 1 exited non-zero, **2 bare** |
> | invocation rungs | groq 8, gemini 5 |
> | chosen because | unknown outcome 7, the creature ran it 5, written 3, new 2 |
> | tools reached | `clear-baseline` x7, `plan-import-subtasks` x3, `get-baseline` x2, and one each of `search-parent-tasks`, `set-baseline`, `fetch`, `plan-export-subtasks-filter`, `plan-link-archive` -- five of them never learned about before |
> | verdicts | **3**, all gemini: `set-baseline` ACCEPTED, `clear-baseline` ACCEPTED, `plan-link-archive` RETURNED |
> | wants | 2, distinct, both born of real use: clear the baseline; show the baseline |
> | tools built | 2, both answering a want: `clear-baseline`, `get-baseline` |
> | visits deferred | **10** -- the invocation call was served and the verdict call then found no rung |
>
> **What the shell changed, read against the spine-on bare before-window (69
> probes, 64 bare, 27 verdicts, 25.5 h):** bare probes went from 93% to 12%.
> Every cousin-composed block carried real arguments, and eight of them did a
> lookup or a setup first (list the tasks, take a keyword; export a list, then
> import it; set a baseline, clear it, read it back). The loop closed twice
> end to end -- want -> tool -> tested -> accepted -> next want -- and the one
> RETURNED was the brief's fifth test found by use: `list-parent-tasks` hands
> out `parent-A`, `plan-link-archive` wants an integer.
>
> **Two cautions, both binding.** (1) **These two windows are on opposite
> sides of the spine line** -- the before-window spine-on, this one spine-off
> since Tue stopped it at 18:50 -- so per-hour rates (probes 2.7 -> 4.7/h,
> verdicts 1.06 -> 0.83/h) are NOT comparable by §4's own rule and are not to
> be quoted as a before/after. The bare-probe share is the one figure the
> spine cannot move. (2) **Two calls per visit starves the judgement on a dry
> tier**: 17 probes, 3 verdicts, 10 deferred. The invocation call takes the
> answer the verdict needed. That is item 18's economics row, not a tick fix.
>
> **Still pending when the watch stopped:** the verdict on `get-baseline`,
> whose first version printed `not written yet` with exit 0 -- the stub the
> brief opens with. Whether the cousin catches it is the brief's own test.
> And `window_reread` re-entered ALARM at 23:50 (`compare-subtask-logs` read 4
> times in an hour, unchanged) -- item 13's symptom, for the morning.

### 10. `[x]` Who may propose a cull

Deliberately deferred until item 9 produces data: a library that is finally
*used properly* may consolidate itself — the creature has done it twice
unprompted.

- **10.1** A named trigger and a date, not a hold waiting on "more
  information" (§4).
- **10.2** Whatever the answer, the cousin never gains a write path into
  `tools/own` (§2.3).

> **DECIDED 2026-09-16: the creature owns the cull; the framework owns only
> the visibility; the cousin gets nothing.**
>
> §4's table already settles the principle — *ordering of the creature's own
> work* is the creature's, inside its world — and a cull is ordering its own
> work. The cousin must never acquire it: a manager that can retire a tool
> holds a write path into the creature's world without touching a file, which
> is precisely what the parent project examined and rejected. Since
> 2026-09-16 that is structural rather than promised: the cousin's shell is
> given a **copy** of the library, remade per visit, so there is nowhere for
> such a path to exist.
>
> **What the framework may add, and has not yet:** one line in the listing
> both inhabitants already see, giving the stem families (`archive-*` ×10).
> Nothing more — no gate, no score, no advice.
>
> **Trigger, named 2026-09-16: forty-eight hours after the cousin's shell
> goes live, if families of three or more are still growing and no tool has
> been removed.** Not before — the twins may be an artifact of a user who
> could only ever call things bare, and adding a surface now would change the
> creature's context in the same window as item 9 and make both unmeasurable.

---

## Phase 5 — settle

### 11. `[~]` Run 3  — GATED BEHIND AN EMPTY BOARD (Tue, 2026-09-21), and it is a THIRD experiment

> **Tue, 2026-09-21, two decisions in one sentence and both his.**
> *"It made so many tools on its own. Where would it branch, sitting in the
> parent's seat, and see them diverge, is a completely third experiment now.
> We need to iron out the baby issues here before we get there. I would as a
> minimum first do that when all not-fixed and not-implemented issues are
> gone."*
>
> **First: it is a different experiment from the one §6.2 chose in 2026-09-10.**
> That one wanted a known-answer library so the cousin's JUDGEMENT could be
> refuted in a week. This one wants a shared starting library so the two
> frameworks' OUTPUT can be watched diverging. Different designs, different
> lengths, different things held still. Pick one in advance and name it, or
> the run measures neither.
>
> **TUE'S DESIGN, IN HIS WORDS, 2026-09-21** -- and it is neither of the two
> experiments offered to him, it is the one this whole project was built to
> run:
>
> > *"I was thinking refutation, where I pause the parent, make the current
> > project there into a prompt where we start off the growing cousin too, so
> > a full sync of sorts of the growing cousin. Then we just leave both on
> > uninterrupted for a week and stop both brains at the exact same time and
> > compare. But the growing cousin with the parent's tools and job is in
> > itself a third instance of a spine, not the current growing cousin
> > written over."*
>
> Read as a design, that is: **one shared starting point (the parent's
> library AND the parent's current job, turned into the opening prompt), two
> engines, one week, nothing touched in between, both stopped at the same
> instant, then compared.** §4 has said since 2026-09-12 that same hardware,
> same network and same shared quota is *the only configuration in which the
> comparison means anything* -- this is that comparison, finally specified.
>
> **The constraint that is not negotiable and is his, stated first:** it is a
> **THIRD INSTANCE**, standing beside the current one. Run 2 is not reset, not
> overwritten and not seeded over. Its journal and its library are the
> evidence for everything in §7 and they survive intact.
>
> **What that costs, and it is mine to solve before this can run.** Three
> engines on one free tier is a third of a tier each, and the current pair
> already produces 12 verdicts in 37 hours. The clean answer is to **pause the
> current growing cousin for the comparison week**: run 2 keeps its journal and
> resumes afterwards, and the week is measured under exactly the two-way
> contention §4 describes. That is a pause, not a reset, and it is the only
> version of this I can see that does not measure a tier nobody runs.
>
> **What must be settled before it starts, none of it Tue's:** a third live
> root, unit and container set that cannot collide with the running pair;
> every inherited tool tagged at t=0 with every metric split on that tag
> (§6.2's standing requirement); how the parent's current job becomes an
> opening prompt without editing anything in `~/growing-spine` (§2.6 -- reading
> is allowed, writing never); and a way to stop two engines at the same
> instant, which `touch STOP` on each does not give, because each finishes its
> cycle in its own time.
>
> **Second: it is gated, not merely deferred.** The gate is every open item
> on this board except 11 itself, **and it is the table at the top of this
> file rather than a list repeated here.** A list was repeated here, and
> within a day it named 18.1-18.8 and 19.5 as open when all of them were
> `[x]` -- a gate that drifts is not a gate. None of the lines in that
> table can be closed by working tonight. **Run 3 is not a way out of a hard item**: it
> spends unattended days on a shared free tier, which is the one resource
> this project cannot make more of, and spending them on an engine still
> being repaired produces a run whose numbers span its own repairs. Run 2
> already is that.


- **11.1** Clean start on a framework that has stopped changing weekly.
- **11.2** Carries item 3's decision, with every inherited tool tagged at t=0
  and every metric split on that tag.
- **11.3** An evidence pack for run 2 is committed before it ends.

> **11.2 and 11.3 done 2026-09-16. 11.1 deliberately not taken, and the
> reason is 11.1 itself.**
>
> `seed_run.py` archives the old run rather than deleting it (the way run 1
> was on 2026-09-13 — a trajectory cannot be repaired retroactively), copies
> the parent's library read-only, and **tags every inherited tool with its
> bytes at t=0**. The tag is a file of hashes, not a naming convention, so
> the creature's first rename cannot silently break every metric split on it.
> `split_on_tag` then reports inherited / built / **repaired** — and repaired
> is the number §6.2 chose the parent's library for: *the parent moved
> `cannot_start` 32 → 23 over months; a cousin taking it to zero in a week
> would be a headline result.*
>
> It refuses to run while the engine is active, and treats a `systemctl` it
> cannot reach as **cannot tell**, which is not permission. It asks before it
> touches anything — the rehearsal harness taught that lesson on 2026-09-16
> by clearing a target and printing REFUSED afterwards.
>
> **11.3:** `evidence/run-2-20260916-0244.manifest.json`, 98 files,
> `monitor verify` passing, 0 key-shaped strings. The earlier pack of
> the same run was labelled `run-2-final` and **run 2 is not final** --
> it was cut at 01:31 and the journal kept growing, so a §7 figure
> quoted "from the final pack" would silently exclude everything after
> that. The manifest was honest about what it hashed; the filename was
> not, and a filename is what gets quoted. Both packs are kept: the
> mislabelled one is still true evidence of 01:31, and deleting
> evidence to tidy a name is worse than the name.
>
> **Why 11.1 is not met today:** the framework changed about a dozen times in
> the three hours before this was written. Resetting now would confound a
> clean library with a week of framework changes, which is the exact mistake
> §4 refused to make on 2026-09-14. **Trigger: forty-eight hours with no
> change to `kernel/` or `run.py`, and item 9's measurement window closed.**
> Then it is one command:
>
>     python3 seed_run.py --root ~/growing-cousin/live \
>         --inherit ~/growing-spine-mind --label run2 --yes

### 12. `[x]` Spine restarts — CLOSED 2026-09-21, overtaken and superseded

> The spine runs, the decision was mine rather than Tue's, it was retracted
> within the hour, and the state is now WATCHED by `shared_tier_contested`
> reading the unit against this file's own claim every five minutes rather
> than written down. A sentence was the thing that drifted for 27 hours; the
> detector is the fix. Nothing is left in this item that is not recorded in
> `CLAUDE.md` §4.

- **12.1** `systemctl --user enable --now growing-spine`.
- **12.2** §4's era note records the date, so no figure crosses it silently.

> **THE SPINE IS ALREADY RUNNING, and 12.2 — the criterion that exists so no
> figure crosses that line silently — FAILED.** Found 2026-09-16 03:05 by an
> independent verifier running `systemctl` rather than reading the board.
>
> It came back up **2026-09-15 00:12:11**, four minutes after its own
> flatline tripwire logged `THINK:!!NONE in 6h`, with a desktop session
> active. No timer did it and nothing here recorded a decision. It has been
> calling this engine's own rungs for 27 hours, and §4 said PAUSED
> throughout — so every figure from the monitor's first day, the §7 evening
> read of 2026-09-15 18:52, and the opening of item 9.5's window were all
> taken against a shared tier while the documents said otherwise.
>
> **12.1 was never run** — the unit is still `disabled`, so nobody enabled
> it. The board was therefore literally true and materially false, which is
> worse than being wrong, and is exactly what 12.2 was written to prevent.
>
> **What has been done:** §4 is corrected with the date and what it costs,
> and `shared_tier_contested` now reads the unit every five minutes and
> compares it against the claim in CLAUDE.md — the machine and the document
> can no longer disagree without somebody being told. **The instrument is
> the fix; the sentence was not.** No test guarded this item and no detector
> mentioned the spine, which is the channel that let 27 hours pass.
>
> **DECIDED, THEN RETRACTED THE SAME HOUR — the spine RUNS.** Tue asked why
> a tier we are not stressing should not be shared, and whether exclusivity
> was a metric being chased. Both halves landed. The premise *the cousin
> starves first* was never measured: over the 25.5 spine-ON hours it made 69
> probes and **27 verdicts**, 1.1 an hour. And the before-window is spine-ON,
> so a cleared-tier after-window is not comparable to it — stopping the spine
> broke the very comparison it was meant to protect. The shared tier is the
> designed condition, not an obstacle. Superseded reasoning follows.
>
> ~~**STOP IT while item 9's window is open.**~~ This entry
> previously called it Tue's; he corrected that the same day — he is the
> customer, not the architect, and an operational question filed as his is a
> question nobody answers. That filing is a large part of why it ran unpaused
> for 27 hours.
>
> The reasoning: the tier is shared, the cousin costs two calls per visit and
> starves first, and it is the agent under measurement; the comparison the
> spine exists for is already suspended and void on throughput; and stopping
> it restores Tue's own stated intent of 2026-09-13, which was undone by an
> accident rather than a decision.
>
> **Trigger to restart: item 9's after-window closed (48 h from 18:36) and
> item 8's baseline across several reps.**
>
> Blocked on EXECUTION only — the session sandbox refuses to stop another
> project's service, which is the right default. One command:
> `systemctl --user stop growing-spine`.
>
> **Tue's call, and the two options are one command each:**
>
>     systemctl --user stop growing-spine       # re-take the pause
>     systemctl --user enable --now growing-spine   # keep it, and mean it
>
> The rest of this entry is the reasoning as it stood before the discovery,
> kept because the argument is still the argument:
>
> §4 records that **Tue** paused the spine on 2026-09-13 13:50 CEST,
> deliberately, *to raise this engine's cadence*. Restarting it reverses a
> standing decision of his and halves the tier this engine has.
>
> It is also the wrong week. Item 8's sixteen-case baseline took over twenty
> minutes **with the engine paused** — the tier is that thin already — and
> item 9's whole measurement depends on the cousin getting calls. Restoring
> the spine now would confound the one measurement the last two days were
> spent building the instrument for.
>
> **Trigger: after item 9's measurement window closes and item 8.4 has a
> baseline with several reps.** Then it is one command, and §4's era note
> takes the date, because no figure may cross that line silently:
>
>     systemctl --user enable --now growing-spine

### 13. `[x]` The output window — was "explicitly NOT doing"; REOPENED BY ITS OWN TRIGGER AND DONE 2026-09-17

> **The symptom this item named fired, and reading the raw thinks answered
> its own question.** `window_reread` went to ALARM four times in twenty
> hours (23:50, 01:02, 09:09, ~18:00). Between 08:00 and 10:00 on 2026-09-17
> the creature ran `cat tools/own/plan` **twenty times** — `plan` at 6,119
> bytes against caps of 2,400, so ~2,400 shown and 2,970–3,743 withheld each
> time — while trying to add the deadline feature its cousin had asked for
> four times. **Twelve of its twenty-four thinks in that window talk about the
> cut.** Not for its own reasons: it could not see the file.
>
> The 2026-09-14 reading ("it edits 7 KB files freely, so the window is
> friction, not a wall") is corrected by this measurement. A cap that hides
> 60% of the tool its author is editing is a correctness fault.
>
> **Done, sized to the library rather than guessed:** 29 of 60 tools exceeded
> 2,400; the largest is 7,223 (`subagent-orchestrator`), then `plan`. Journal
> 8,000, context 8,000, block total 12,000 — all three together, or the
> caps-in-series scar swallows the raise; the gate asserts every built tool
> fits through all three and derives its fixtures from the constants. Engine
> `dd53e91`. Context cost: the history block may grow from ≤6,000 to ≤12,000
> chars per wake in the worst case; measured against a 6 KB tool read blind
> twenty times, that is cheap.
>
> **What to read next:** `window_reread` should stay OK on `plan`; if it
> fires again on a tool UNDER 8,000 bytes, the cause is not the window.

Original entry follows, kept because the reasoning was right until the
measurement said otherwise:


*Don't fix what has no symptom.* It stays on the board as a decision, not as
something forgotten.

- **13.1** Recorded as not-doing, with the symptom that would reopen it: the
  creature re-reading one tool across consecutive wakes without editing it.
- **13.2** A detector for that symptom, or a stated reason there is none.

> **Done 2026-09-16. The decision stands and is now WATCHED**, because a
> decision recorded and then unwatched is indistinguishable from one
> forgotten. `window_reread` fires when the creature reads one of its own
> tools four or more times without changing it — the 2026-09-13 shape, where
> it read `plan` six times in fifteen minutes through a 1,200-character window
> and built nothing. Reads are counted only since the last time it *changed*
> that tool, so ordinary editing is not an alarm.
>
> It reports the pattern and refuses to announce the cause: a creature may
> reread a file for its own reasons, and a cap changed without a before/after
> across several windows, split by rung, is superstition (§5). **If this
> fires, the next step is a measurement, not a bigger number.**

---

## After the plan

### 14. `[~]` The chat channel (item 2's build)  — 14.1–14.4 met and verified; 14.5 waits on a window, not on work

Slotted here because it adds a surface to the creature's context and must not
land while anything is being measured.

> **Criteria written 2026-09-16, AFTER the build — which is the wrong order
> and is recorded as such.** PLAN's own first rule is that the test comes
> first; this item shipped against a one-line brief with "acceptance criteria
> to be written when it starts" still in place, and an independent verifier
> was the one to point out that it therefore had no contract to be judged
> against. Written now so the thing that exists can be judged at all.

- **14.1** A message from the human reaches the creature, **once**, and is
  never re-served. *Surface on a change of state, never continuously.*
- **14.2** Clearing the inbox destroys nothing: the text is kept.
- **14.3** The creature can answer, and its answer lands somewhere a human
  will actually see — **not** in a file nothing reads.
- **14.4** `say` writes exactly one file, inside the creature's own tree, and
  nothing else anywhere.
- **14.5** The creature is TOLD the channel exists. Until then the channel is
  one-way in practice, and that is stated rather than assumed.

> **14.5 is NOT met, and the reason CHANGED on 2026-09-21 — which is worth
> saying rather than letting the old reason stand.** It used to be the freeze:
> `CREATURE-PROMPT.md` lists the built-in hands and was frozen until item 8.4
> had a baseline. **That baseline exists** (2026-09-16,
> `trial/baselines/baseline-frozen_gemma-4-31b-it.json`), so the freeze is no
> longer what holds it.
>
> **What holds it now is a measurement in flight.** On 2026-09-21 this
> project's headline metric started answering for the first time in its life
> (item 20.2: one tool has survived it, `plan`; the not-yet columns move
> by the hour and belong on the page rather than in a document).
> Its window is seven days. Adding a chat surface to the creature's context
> now would land in the middle of the first one, and §0's rule is that a new
> surface mid-measurement makes every number either side of it incomparable.
> A hand nobody mentioned is a hand nobody uses — the *dead channel* scar —
> so this is a cost being paid knowingly, not an oversight.
>
> **Trigger: 2026-09-25, when the metric has a full week behind it.** Add
> `say` to the prompt's hand list then, in one change, and read the metric
> either side of it as an experiment rather than as noise.

### 15. `[x]` Should a body that cannot be respawned end the run?

**Found by item 6's body drill, 2026-09-16 — a genuinely open design
question, not a bug with an obvious fix.** `LocalBody.respawn` sets its alive
flag and re-probes; it does not rebuild the tree. When the creature removes
its own `$MIND` — which its shell can do, and `$MIND` is handed to it on
purpose — the respawn returns False, `run_cycle` records `error where=body`
and skips the rest of the cycle, and repeats that forever. **Nothing raises**,
so the supervisor never counts a failure, so neither `gave_up` nor
`engine_silent` fires, and the engine sits there looking busy.

Visibility shipped immediately (`body_unrecoverable`), which §4 allows
without asking. The decision does not follow from it:

- **Raise, so the supervisor gives up and systemd restarts** — the process
  comes back and `LocalBody.__init__` recreates the tree, but the creature's
  library is gone and the framework will have silently rebuilt its world
  empty. That is the parent's worst failure mode wearing a recovery's
  clothes.
- **Rebuild on respawn** — the same data loss, one layer lower and quieter.
- **Stop and wait for a human** — honest, and the one option that does not
  destroy anything; it also means an overnight run can end at 03:00.

- **15.1** A decision recorded with its reason, not a patch.
- **15.2** Whatever is chosen, the creature's existing tools are never
  silently replaced by an empty tree (§2.1 — its tools are its world).
- **15.3** A drill proves the chosen behaviour end to end.

> **DECIDED 2026-09-16, and item 7 is what decided it.** The decision was
> living only in a code docstring until a verifier pointed out that the board
> carried no answer at all — and that the docstring answered a *different*
> question from the one asked.
>
> **The rule is about WHAT is recreated, not about who does it:**
>
> > **A respawn may recreate a CONTAINER, and must never recreate a MIND.**
>
> A container is a process with an interpreter in it; the creature's world is
> a bind mount on the host, so rebuilding one destroys nothing. A mind IS the
> creature's world: rebuilding it hands back an empty tree and calls that a
> recovery, which is §2.1 broken by the framework — the parent's worst
> failure mode wearing a recovery's clothes.
>
> **The question as asked — should a body that cannot be respawned END the
> run — is therefore answered NO for the deployment**, because the deployed
> body is a container and it can always be brought back. For `LocalBody` the
> gap stays open by choice: raising would make systemd restart and
> `LocalBody.__init__` would silently recreate the world empty, which is
> worse than looping. It is alarmed instead (`body_unrecoverable`), which is
> the response §4 allows without asking.
>
> **Trigger to reopen: the first time `body_unrecoverable` fires in
> production.** That would mean a container that could not be rebuilt, which
> is a different fault from the one this decision covers and deserves its own
> answer rather than this one stretched over it.

---

### 16. `[!]` The cousin, not us, notices when a tool serves nothing — HALF DELIVERED (20.3's instruments), and the RULE waits on 20.4

> **2026-09-18.** `MANAGER-PROMPT.md`'s section *Why this question and no
> other* tells the cousin in as many words that the mission is NOT its
> question: *not "is this good code", not "did it follow the rules"*, only
> did the handover work. A rule asking it to judge whether a tool furthers
> the mission has to change that section, which is frozen (§0) -- and it
> would be asking a judge with no job to measure usefulness against a
> purpose that does not exist in the system. The instinct below is right
> and stays. What it needs first is item 20.

**Tue, 2026-09-16, and it is the right instinct:** *"the reasoning if a tool
furthers the mission or is a circle jerk of bureaucracy should rest on the
cousin to pick up on and ask the creature for a better why or a way to
re-engineer the tool to further the cause."*

He is right that the judgement is misplaced. On 2026-09-16 **I** read the
library and concluded it was a bureaucracy administering its own paperwork
(§4). That is precisely the judgement §4's function table gives to the
**cousin** — *need statement: what I cannot do* — and a finding that only
exists because a human read fifty files is, by rule 2 of CLAUDE.md §1, not
fixed at all.

**But the rule cannot simply be added to the brief, because the cousin has
nothing to measure "furthers the mission" AGAINST.** Today it is told to be a
user of these tools and to judge whether they work for it. A user of a
task-tracker, asked only *does this work*, will ask for task-tracker features
forever — and that is exactly what 50 tools of plan/archive/subtask
bookkeeping are. The loop closes honestly and drifts, because nothing in it
points outward. Ask a judge with no job to rule on *is this useful* and you
get confident garbage, which is the failure §6.4 already names for audits.

So this item is **not** "add a rule". It is the open design question
underneath it:

- **16.1** The cousin is given something it is TRYING TO DO — a standing
  purpose beyond *exercise whatever was just built*. A user with a real job
  notices an unhelpful tool without being told to look for one.
- **16.2** The rule states a LACK, never a task (§4). *"I still cannot do X"*,
  never *"re-engineer this tool"* — the creature owns the shape of the
  solution or it is taking dictation, and that boundary is what makes this a
  second user rather than a second builder.
- **16.3** Scored against `trial/heldout-cases.json` before it ships: a
  DIRECTION across several reps, split by model, detection and correction
  reported together. The brief is ONE artifact and every rule changes every
  verdict it produces (§5, 2026-09-11).
- **16.4** A control: the change must not turn the cousin into a refuser.
  Held-out ACCEPTED cases stay accepted.
- **16.5 (added 2026-09-17, from the first shell window): the "when you
  called it wrong" rule is inverted by item 9.** It says a tool that refuses
  incomplete input has done its job — written for a harness that called
  everything bare. The cousin now chooses its arguments, and on 2026-09-17
  it ran `plan` bare four times, accepted the usage menu four times with the
  identical sentence, and asked for deadlines four times while
  `plan set-deadline` sat built and untried. The rule's condition should be
  *the harness gave you nothing*, never *you chose to type nothing* — a user
  with hands who summons a menu has not tested anything. First concrete rule
  to draft and score; `testimony_repeated` is its instrument on the page.

**SEQUENCING, and it is not optional.** This is a brief change, and item 9's
measurement window is open. Shipping it now confounds the one measurement two
days were spent building an instrument for — §5's top scar, five changes in
four hours with no baseline. Worse, `trial/` spends the same shared free tier
the live engine and the spine are on, so even SCORING it now perturbs the run
it would be scored against.

> **Order: draft the rule now (costs nothing), score it when item 9's window
> closes (2026-09-18), ship it with a before/after or not at all.**

**What is already true and needed no decision:** the framework half was fixed
2026-09-16 — the probe chooser now sends the cousin to tools whose outcome
nobody knows rather than to ones already proven, so the cousin gets the
evidence it needs to form this judgement at all. Visibility first, always;
the brief comes after.

---

### 17. `[~]` What of MY job belongs to the cousin — 17.1 and 17.2 done and confirmed in production; 17.3 moves with 16; 17.4 is a standing statement

**Tue, 2026-09-16:** *"a lot of what we two do here in this line should be
taken over by the cousin — either as an extension of its prompts or
skill-like workflows — or a separate subagent instance if all else fails and
it's too much for the cousin in one run."*

**The architecture said this on day one and I have been drifting from it:**
*"A scan gathers a fact and decides what to say about it; only the second
half is framework. Scans become scripts the cousin runs. The deleted 99% is
the apparatus around them — scheduling, caches, edge-trigger state files,
warning composition, surfacing rules — all of which exists because nobody was
there to decide."*

Read that against `monitor/`. I built a **timer** (scheduling), an
**alarms.jsonl** that only records state changes (edge-trigger state files),
findings that compose their own sentences (warning composition), and a page
ordered alarms-first (surfacing rules). Four for four. **I rebuilt the
deleted 99% on the outside of the system that deleted it.**

**But it is not all a mistake, and the line was already drawn here** (§8,
2026-09-10, Tue's instruction): the guard list had merged **two populations —
creature-facing guards, which the cousin replaces, and health tripwires,
which report outward and must not be.** That is the whole answer, and it
sorts my job cleanly:

| what I do | population | whose |
|---|---|---|
| is the engine alive, did it give up, is the journal torn, is a rung walled | health tripwire | **stays outward** — monitor + human |
| does the doctrine still match the machine (`shared_tier_contested`) | health tripwire | **stays outward** |
| is this tool a twin, does it serve anything, is the library a bureaucracy | creature-facing judgement | **the cousin's** (item 16) |
| reading the run record and saying what it means | scan + decision | **split**: the scan is a script the cousin runs; the deciding is its verdict |
| framework debugging, tests, commits, doctrine | neither | **not the cousin's at all** — see below |

**Three hard constraints, none of them opinions:**

- **Economics.** Every workflow step is a model call. `ARCHITECTURE.md` puts
  the manager at ~13% of calls and says that budget *is* the economic
  argument for this design. Item 9 already took the cousin from one call per
  visit to two. Measured 2026-09-16 on the real ladder: **1.1 verdicts an
  hour.** A five-step workflow is not a design change, it is a five-fold
  cost increase on the binding constraint, and it must be measured before it
  is committed to.
- **Containment.** §2.4: *never tell the creature about its own bugs.* The
  cousin speaks to the creature. A cousin that reads our diagnostics has a
  path from our fault-finding into the creature's world that touches no file
  — the same shape as §2.3's write path, one level up. Anything handed to
  the cousin must be evidence it could have gathered ITSELF by using the
  tools, never our analysis of it.
- **Capability floor.** The rungs that serve the cousin produced 0 usable
  verdicts in 14 calls on 2026-09-13, needed four brief rules to judge twelve
  cases, and on 2026-09-16 the brief's own baseline was **7 of 8 broken
  caught, 5 of 8 good falsely returned**. That is the instrument available.
  It can judge a tool it ran. It cannot read a 767-assertion suite or a diff.

**So the sequencing, and it is the same shape as every other item here:**

- **17.1 `[x]` DONE 2026-09-18, by item 20.3.** The library audit of
  2026-09-16 -- the one that produced a real finding -- is now five scripts in
  `instruments/`: `lib-startable`, `lib-stubs`, `lib-twins`, `lib-deps`,
  `lib-stores`. A script is not a model call and costs nothing. On their first
  run they found a shared store no reader can parse and a hub tool named by 37
  of 60 that no reading of that library had noticed.
- **17.2 `[x]` DONE 2026-09-18, and CONFIRMED IN PRODUCTION 2026-09-19.**
  They are installed into the cousin's bin and nowhere else -- the gate
  asserts the creature's bin never receives them, which is the containment
  rule above (§2.4: never tell the creature about its own bugs). The cousin
  ran `lib-deps plan` twice, unprompted, writing its own reason into the
  block. **Every instrument reports a FACT it could have gathered itself, and
  none of them carries our analysis**, which is the line that keeps this from
  becoming a path out of our fault-finding into the creature's world.
- **17.3** The DECIDING half moves with item 16, and only after it is scored.
- **17.4** The framework half — code, tests, doctrine — stays with an agent
  that has the repo, the gate and a verifier that did not write the change.
  Today that is Claude. **Evidence it is not yet automatable: five
  independent verification rounds on 2026-09-16 found real defects in my own
  work every single time**, including two tests that could not go red and a
  feature that was inert in production for fifteen hours. An autonomous
  engine-debugger needs that verification loop, not just the ability to write
  a patch.

> **Trigger: after item 16 is scored.** Moving the judgement before the judge
> has a job to measure against is item 16's mistake with more machinery.

---

### 18. `[x]` The cousin path reviewed end to end — and what stays open

Tue, 2026-09-16, on Fable 5.1: *"inspect everything for bugs and especially
the new additions to the cousin part — for architectural issues."* The
findings and fixes are in CLAUDE.md §5 (*read end to end*) and the commits
`3a4d567` onward; every new test was red against the code that shipped, and
the gate count is not written here for the reason §0 gives. What this item records is **what was seen and NOT
fixed**, with its reason and trigger, so it does not become a thing nobody
remembers:

- **18.1 `[x]` CLOSED 2026-09-21, and the premise was wrong.** *"The cousin
  does not obviously need it"* -- **measured, it does**: two probes ran
  `fetch https://example.com "Example Domain" ; archive-list`, which is the
  cousin testing the one tool in the whole library that reaches outside.
  `--network none` would have made that tool fail in the cousin's shell for a
  reason that is OURS, the cousin would have reported it faithfully, and the
  creature would have been billed -- the exact fault this project has now
  recorded sixteen times, and it would have hit the single outward-facing
  tool it owns.

  **So the trigger stands and now carries its cost.** The condition is
  unchanged (*the first time anything key-shaped or personal lands in `data/`
  or `state/`, which the pack's scan reports*), and the price of pulling it is
  recorded beside it: `fetch` stops working for its only user, so whoever
  pulls it must also decide what happens to the tool that needed it. Today the
  copy holds 0 real credentials, checked byte-for-byte.
- **18.2 `[x]` CLOSED 2026-09-21: measured, bounded, and deliberately not
  changed.** Item 9's window closed, which was the trigger. **The served
  context has gone from 7,758 characters at the start of run 2 to 38,024
  now**, across 3,977 wakes -- roughly five-fold, tracking the library.

  **It is bounded and it degrades rather than hiding**: 40 of 62 tools are
  shown as full entries and the remaining 22 by name and purpose, which is the
  rule §5 earned when an alphabetical cut hid seven tools from their own
  author. So this grows toward a ceiling, not without one.

  **Not changed, and the reason is the §5 split.** A listing bound is TUNING:
  every number in it is a behaviour under one model, and cutting it needs a
  before/after across several windows split by rung, not a judgement at
  01:00. It also collides with a standing decision of Tue's -- both
  inhabitants see the library every time, as state rather than news -- which
  is not mine to trade away for context. *Re-opening condition, and it is
  specific rather than a feeling: the creature losing commands to a FULL
  context (a rung refusing on input length, not output), which nothing has
  ever recorded here.*
- **18.3 `[x]` CLOSED 2026-09-21: it can, and it does.** The worry was that,
  told to make up plausible inputs, it would invent IDs and every tool would
  correctly refuse them. **Measured over 179 probes with a recorded command:
  96 of them are more than one command, and 54 capture the output of one into
  another.** It writes things like `parent_id=$(obtain-parent-task-id)` and
  then uses it, and `list-parent-tasks` first so it can pick a real keyword.

  That is the whole-block change of item 9 doing what it was built for, plus
  the instruments of 20.3 for questions about the library rather than about a
  record. **What remains is not discovery but judgement** -- whether it looks
  up the RIGHT thing, and whether it notices a tool that serves nothing -- and
  that is items 16 and 17, where it already sat.
- **18.4 `[x]` FIXED 2026-09-21. A rebuilt image is now adopted.**
  `ensure_container` compares the image the container was CREATED from against
  the id the tag points at today, and recreates on drift -- the same shape as
  the mount check beside it, which is what the item asked for. **Both ids or
  nothing**: an unreadable answer is CANNOT TELL and never a reason to destroy
  a container, the rule the mount check earned. Four assertions, including
  both blind cases.

  > **It was more certain than "unlikely".** The unit runs `docker build` on
  > every start, so the tag moves on every start; a container created once
  > would have gone on running the first Dockerfile it ever saw for the life
  > of the deployment, while `deploy/Dockerfile` in the repo said otherwise.
  > §5's oldest systemd shape for the third time: present in the code, absent
  > from the running thing.
- **18.5 `[x]` CLOSED 2026-09-21 as a decision, not a gap.** `deploy_regression`
  did not see the shell's fifteen silent hours and still would not: its floors
  are the creature's correctness indicators, and a cousin that has gone quiet
  is not one of them. **`cousin_starved` is the detector for that** and it
  fires in four hours rather than waiting for a deploy. Re-checked against
  `deploy_regression_day` (21.3): a day-long window does not help either,
  because nothing in `regression_table` alarms on *verdicts fell to zero* --
  by design, since a dry tier does exactly that and is weather. **Two
  instruments, two questions**; wiring the cousin's silence into the deploy
  comparison would give one face to *the deploy broke something* and *the tier
  is dry*, which is §5's oldest confusion.
- **18.6 `[x]` FIXED 2026-09-21, by its own trigger.** `probe_stuck` fired on
  `ran` twice more (09-19 23:54 and 09-20 14:57, both 5 of 8 visits to
  `plan`), which is exactly the condition this item named. `ran` stays the
  reason -- a done-claim IS about something the creature just ran -- and what
  changed is which one when it ran several: **the one its user knows least
  about, ties broken by recency**, so the hub the creature touches every cycle
  stops absorbing every visit. Same fault as the alphabetical fallback §5
  records: not a wrong reason, a reason that always returns the same answer.

  **Red-proven on the laptop against the previous commit's chooser**: with the
  old rule the test got `plan`, with the new one `archive-graph-path`. Five
  assertions, including that recency still decides when nothing is known about
  either, so one fixed answer was not swapped for another.
- **18.7 `[x]` FIXED 2026-09-21. A probe that ran and lost its judgement is
  finished, not discarded.** The visit costs two model calls -- what to type,
  then what you think -- and on a dry tier the second is the one that finds
  nothing. **A deferred visit RE-RAISES, so its trigger was never cleared and
  fires again**, which means answering the orphaned probe on the next visit
  answers the same question rather than swapping it for another, and costs
  ONE call instead of two.

  Nothing is queued: the orphan is DERIVED from the journal -- the most recent
  probe with a real exit code and no verdict after it -- which is the rule the
  manager's whole state follows (§6.1). The transcript is rebuilt rather than
  re-run, because the experience being judged is the one that happened, and
  **the cousin is told plainly that the run is not fresh**; a stale transcript
  that reads as live would be the fabricated-experience fault (§2.5) with the
  framework as author.

  **Two bounds, and the second was a trap I nearly shipped.** A probe older
  than six hours is dropped rather than judged late, because the library has
  moved and a verdict about a tool as it was is testimony about a world that
  is gone. And **at most three attempts**: unbounded, a long dry spell would
  re-offer the same orphan every visit until it aged out, and the cousin would
  never see anything the creature built in between -- a fix that starves the
  thing it was meant to feed. Red-proven, 14 assertions, including that a
  probe which never reached the tool is NOT unfinished work, since there is no
  experience to judge.

  ~~**18.7 (original) Two calls per visit starves the judgement on a dry tier. MEASURED
  AGAIN 2026-09-19 and it is worse than the first reading: since the
  instruments deployed, 69 probes produced 12 verdicts -- 17% -- with 45
  visits deferred.** And it now has a face: on 09-18 22:59 and 09-19 01:28 the
  cousin composed `lib-deps plan` with its own stated reason, got exactly the
  fact it wanted, and **both times every rung was at quota when the verdict was
  asked, so the visit was deferred and the work was discarded.** The cousin did
  the thing the design wants and the tier ate the result. Earlier reading: 88
  probes, 14 verdicts, 52 visits deferred in 23 hours.**~~ The
  invocation call is served and the verdict call then finds no rung. Not a
  tick fix and not a brief fix; a ladder economics question. *Trigger: item
  8's baseline across several reps, so a change to the verdict call's budget
  or the ladder's order can be read against something.*
- **18.8 `[x]` FIXED 2026-09-21. The Windows gate is alive again.**
  `LocalBody` now resolves the bash it promises instead of handing the name to
  a search order nobody chose, and **records which binary answered**
  (`shell_path`). `usable_bash` refuses anything whose parent directory is
  `System32` or `SysWOW64` -- Windows' WSL launcher, a different kernel with a
  different filesystem, handed a Windows `cwd` and a relative script name --
  and returns None rather than silently running it, so a host with no real
  bash gets an honest `setup_failed` naming `COUSIN_BASH` as the override.
  On this Windows box it resolves to Git's `usr/bin/bash.EXE` and runs `[[ ]]`,
  which is neither POSIX sh nor reachable by the launcher.

  > **THE WINDOWS GATE IS GREEN, 2026-09-21: 864/864 in 48 seconds**, with
  > three tests that say plainly they could not run here. The path from 92
  > failures took three fixes and the last two were only findable because the
  > first one worked: **92 -> 23** (the body ran the launcher) **-> 11** (the
  > path translator ASKED the launcher where Windows drives live, so every
  > PATH entry reached the real shell as `/mnt/c/...`) **-> 1** (the suite
  > reported a missing host capability as a failure) **-> 0**. The last one
  > was an assertion comparing `C:\Users\...\Temp\X` against `/tmp/X` as
  > strings; Git bash maps the Windows temp directory to `/tmp`, so both
  > spellings are right and the question had to be asked of the shell.
  >
  > **The laptop remains the authority** and nothing about that changes. What
  > changes is that a Windows run is now evidence rather than noise, and that
  > the suite counts what it could not check instead of printing all-green
  > over it -- the laptop had not been able to reach the local model for days
  > without once saying so.

  > **The gate caught a bug in this very fix, which is the part worth
  > keeping.** The first version asked `os.path.dirname` for the parent
  > directory. On Linux a backslash is not a separator, so a Windows path
  > inspected on Linux has no parent at all, the trap check never fired, and
  > the laptop went red on three assertions the moment it shipped. **A policy
  > about paths must read a path the same way on every platform that inspects
  > it**; it splits on both separators now. Then the repair itself was eaten
  > twice by a shell heredoc collapsing backslashes, which is the habit this
  > file already carries -- written from `chr(92)` in a scratchpad file in the
  > end, which is what that habit prescribes.

  ~~**18.8 (original) The Windows gate is dead, not flaky (2026-09-17, found by the
  verifier of item 19).**~~ `LocalBody` spawns bare `bash`; Windows'
  CreateProcess searches `System32` before `PATH`, so it gets the WSL
  launcher, the body is unresponsive on every spawn, and ~92 checks fail by
  cascade -- two runs, identical by name, `code=124` never. The laptop is the
  authority and was green the same evening, so nothing is wrong with the code
  under test; what is wrong is that a Windows run says nothing. *Trigger: the
  first time anyone needs the Windows gate to mean something.* The fix's
  shape: `LocalBody` resolves the bash it means to an absolute path -- a
  `PATH` scan that skips `System32` -- and the liveness probe records which
  binary answered. `shutil.which` alone may not be it if `System32` precedes
  Git's bin in `PATH`, which it usually does.

---

## Phase 5 — the public repo (added 2026-09-17)

### 19. `[x]` The archive that reached the public repo — CLOSED 2026-09-21

**What happened.** 2026-09-16 03:19, commit `221b978`: an unscoped
`git add -A` in a tree holding run 1's archived live root pushed **80 files**
-- journal, engine log, served context, the creature's tools -- to this
public repository. `.gitignore` guarded the name `live/`; the archive was
called `archive-contaminated-20260913-1244`. Found the same day by reading
the diff of the commit that shipped it; the habit is in CLAUDE.md §0.

- **19.1 `[x]` Nothing in it was a credential.** Byte-for-byte against the
  four real key files: 0 hits in the 80 pushed files, 0 in 213 live files.
  The regex that had reported one (`sk-` inside `subtask-`) was retracted.
  The check is the pack's now (`monitor/pack.py`: `real_keys`,
  `scan_real_keys`), so an evidence pack refuses to exist around a real key.
- **19.2 `[x]` Untracked, and ignored by CONTENT rather than by name.** The
  path left the index the same day (`a4c8f85`, pre-rewrite name);
  `.gitignore` gained `archive-*/`, `*-archive-*/`, `live-*/`; and
  `test_no_live_root_is_tracked_by_git_whatever_it_is_called` asserts that
  no tracked file is a live-root file whatever its directory is called --
  seen red against the tree that shipped.
- **19.3 `[x]` Purged from history, 2026-09-17 20:32.** Tue: *"do the purge
  if you find it prudent"*, then *"do it yourself"*. In order, each step
  refusing on the one before: a mirror of the whole repo on the laptop
  (`~/growing-cousin-backup-before-rewrite.git`, at `ef812dc`); a dry run on
  a throwaway clone (18 rehashed, 0 archive objects, gate green); then the
  real one -- `git filter-branch --index-filter 'git rm -r --cached ...'
  -- --all`, backup refs dropped, reflogs expired, `gc --prune=now`; **0
  objects naming the archive across all refs**, gate green, and only THEN
  the force-push. The map is committed beside this file:
  `evidence/history-rewrite-20260917.md`, 18 rows, `221b978` → `fb3d18a`
  through `ef812dc` → `ee5992d`. The engine was restarted afterwards so its
  recorded identity names a commit in the log (item 9's note).
- **19.4 `[x]` Checked from the outside, not from the tree that did it.** A
  fresh `git clone` from GitHub on the laptop: 150 commits, HEAD `5ef847f`,
  0 objects naming the archive. At the push the repository had 0 forks and
  0 pull requests (`gh api`), so there is no other copy to chase. What
  GitHub itself still holds is 19.5.
- **19.5 `[x]` DECIDED 2026-09-21: LEAVE THEM.** Asked in plain words at
  last and answered in one click. They are unreachable by browsing or
  cloning, they answer only to an exact 40-character address nobody holds,
  they contain no credential (checked byte-for-byte), and GitHub clears this
  kind of leftover on its own schedule. **This is closed by choice, not
  pending.** It sat on the board for four days labelled *Tue's* while never
  once being put to him in a sentence he could answer, which is the fault
  recorded at the end of this item.

  ~~**19.5 (original) GitHub's own copies -- Tue's, because it is his account and
  it is outward-facing.**~~ Minutes after the force-push, `gh api` still
  answered for `221b978`, `add6782` and `ef812dc` by SHA, and still served
  the archive directory under `221b978` (6 entries). Unreachable from every
  branch, so no clone can get them; reachable by URL until GitHub's garbage
  collection or a support request removes them. **The ask, when Tue wants
  it made:** GitHub Support → *"please remove cached views and run garbage
  collection for the unreachable commits `221b978`..`ef812dc` on
  Tubifix77/growing-cousin; history rewritten 2026-09-17; no credentials
  involved."* Not urgent by the same measure (0 keys, by bytes), which is
  why it can wait for him.

**What it is NOT.** Not a credential leak -- 0, by bytes. It is raw model
output and the creature's tools in a public place, which is exactly the rule
the tarball lives under (CLAUDE.md §0), and that rule now holds for the
history too. **Acceptance, checkable by anyone:** on a fresh clone,
`git rev-list --objects --all | grep -c archive-contaminated-20260913-1244`
prints 0; the map has one row per rehashed commit; and the page's
`restart_owed` line reads `running the checkout` or `docs-only since`, never
`could not diff`.

---

## Phase 7 — the creature's own wall (added 2026-09-20)

### 21. `[~]` A tool the creature cannot rewrite in one reply is a tool it can no longer change — 21.1 ANSWERED 2026-09-21 (53% lost -> 0%); 21.2 open with its trigger

**Measured 2026-09-20**, after Tue asked how the creature had fared and the
answer turned out to be *badly, for three days, because of me*. Full numbers
and the process failure are in `CLAUDE.md` §5; the short form:

- `CREATURE-PROMPT.md` gives exactly one way to change a tool: **`tool-edit
  <name>` with the COMPLETE new content on stdin.** The creature also uses
  `cat << EOF > $(which <tool>)`, which is the same idiom by hand.
- So **editing a tool costs at least as many output tokens as the tool is
  long**, plus whatever reasoning it does around the change.
- Its output budget was 3072 tokens, cutting at roughly 8,400 characters.
  `plan` is **9,182 bytes**. It had become uneditable, and the creature kept
  trying: **298 of 346 cut-off replies were a whole-tool rewrite**, and half
  of all its thinks lost their command.

**21.1 `[x]` The immediate reprieve, shipped 2026-09-20.** `num_predict`
3072 -> 8192 on every rung. The ladder is configuration, not code, so this is
not a commit; the backup is `~/rungs.local.json.bak-20260920`. **Acceptance,
and it is a measurement rather than an assertion:** `truncated|lost` as a
share of thinks returns toward the 1% it sat at before 2026-09-17.

> **ANSWERED 2026-09-21 17:52, and 21.1 is `[x]` on its own acceptance
> criterion.** Eighteen hours after the config loaded:
>
> | | thinks | `finish=length` | truncated **and lost** |
> |---|---|---|---|
> | the 24 hours BEFORE it | 175 | 102 | **93 (53%)** |
> | everything since | **90** | **0** | **0 (0%)** |
>
> Not *toward* the 1% it sat at before 2026-09-17 -- **below it.** The
> creature's replies still routinely rewrite whole tools; they now fit.
>
> **The automated reading was given up for this one, deliberately, and that
> is recorded rather than glossed.** `deploy_regression_day` for `c942d88`
> would have said the same thing at 09-22 01:41 with nobody having to
> remember to look, which is its whole virtue. It was traded for deploying
> the marker fix eight hours earlier, because that fault was measured biting
> **22 of 22** marked outputs. `CLAUDE.md` §0 carries the trade.
>
> **The earlier reading, kept because it was honest about being an
> anecdote:**

> **FIRST READING 2026-09-21 01:50, and it is an anecdote by this file's own
> rule.** The config was edited 09-20 23:36 and the first engine to load it
> started **23:38:48**. Since that second: **16 thinks, 0 finished on
> `length`, 0 commands lost.** The 102 length-finishes of 09-20, and the 16
> `truncated|lost` still showing in the page's six-hour column, are all from
> before it.
>
> **Do not read the page's alarm as a contradiction.** `commands_lost` is
> windowed by COUNT -- the last 20 thinks from a rung -- so it spans the
> restart and keeps firing until twenty new thinks have gone by. That is the
> detector working: a count window cannot know a config changed inside it,
> and the alternative -- resetting a detector when we deploy -- is how a
> monitor learns to agree with whoever last touched the machine.
>
> **Sixteen thinks is one window and one window is an anecdote** (§5, top).
> What settles 21.1 is `deploy_regression_day` for engine `c942d88`, due
> 09-22 01:41: a full day against the day before it, needing nobody to
> remember to look. The
before/after exists already and is unusually clean, because the regression had
a single known cause and a dated start.

**21.2 `[!]` THE WALL ARRIVED, ON THE READ SIDE, AND THIS ITEM'S TRIGGER
  WAS WATCHING THE WRONG NUMBER.** Fired 2026-09-23; see `CLAUDE.md` §5.

  The trigger said *the first tool over 15 KB, or `truncated|lost` crossing
  10%*. Both are the WRITE wall -- the reply budget, now ~25 KB since
  `num_predict` went to 8192 -- and neither has fired. **The READ wall is
  `HISTORY_TOTAL_CHARS`, 12,000, and `plan` crossed it at 12,058 bytes.**

  A single `cat tools/own/plan` costs more than the whole transcript budget,
  so the oldest-first trim drops **36,526 characters** and leaves **one**
  command visible -- the `cat` itself. Measured 09-22: **39 reads of `plan`,
  1 write.** The creature: *"The transcript was truncated."*

  ~~**Raising the bound is measured NOT to fix it**: 12,000 -> 24,000 takes
  the visible commands from 1 to 2, because each read costs ~8,000 whatever
  the bound is.~~

  **THAT SWEEP HELD THE WRONG CAP FIXED, corrected 2026-09-23 17:52.** A read
  costs ~8,000 because `HISTORY_OUTPUT_CHARS` cuts it at 8,000, not because
  `plan` is 12 KB -- so every row of that table paid the same clipped price
  and answered a question nobody had. The 2026-09-13 scar by name: *two caps
  in series, and the one that was tuned was not the one that acts.* The day
  the conclusion stood cost **74 reads of `plan`, 0 writes and 2 tools added
  in 17.3 hours**, against 37 / 1 / 14 the day before.

  **All three caps moved together on 2026-09-23** -- 16,000 / 16,000 /
  24,000, sized to a 90-tool library whose largest file is 12,058 bytes --
  and `test_one_output_cannot_evict_the_whole_transcript` holds the
  relationship as a property so the next oversized tool cannot restore it
  quietly. Deployed 18:14:28 as `44f53b5`.

  **AND 24,000 WAS HALF A FIX, corrected the same evening.** Replayed
  deterministically over the real window -- 360 wakes, the true 12,042-char
  `plan` substituted back so the new setting pays full price -- it fixed
  READING (uncut transcript **24% -> 86%**) and did not fix FORGETTING
  (wakes with <=1 command left **61% -> 56%**). 12,000/8,000 and
  24,000/16,000 are the same ratio, so the number of maximal outputs that
  fit never changed, and the guard shipped with it asserted a DIFFERENCE
  (`>= 4000`) where the property is a capacity. At 40,000 eviction goes to
  **27%**; 48k and 64k buy nothing. `HISTORY_TOTAL_CHARS` is 40,000 and the
  guard asserts two maximal outputs fit. Deployed 18:53:48 as `07cbd19`.
  `CLAUDE.md` §5 carries the table and the discarded method.

  **This does NOT close the item, and saying why is the point.** A window
  wide enough to read a 12 KB tool is not an idiom for editing one. The
  creature's only editing move is a whole-file rewrite, so `plan` still costs
  ~12 KB of reply to change one line, and the write wall is at ~25 KB: the
  cap raise postponed this item, it did not answer it. What it also did is
  remove the confound -- until today a rewrite failure could not be told
  apart from the creature never having seen the file whole.

  *Trigger, RE-CUT: it has fired, and the caps bought time rather than a fix.
  The hand lands after 2026-09-25, when 20.2's first full week closes,
  because it is a change to the creature's world and those do not land
  mid-measurement. Read `deploy_regression_day` for `44f53b5` (due 09-24
  18:14) first: the baseline is the table above, and what it must show is
  reads falling WITHOUT writes falling.*

  ~~**21.2 (original)** 
25 KB.** A library whose tools keep growing will hit it again, and the failure
is silent from inside: the creature sees its command not run and has no way to
learn that the reason was its own length. *Trigger: the first tool over 15 KB,
or `truncated|lost` crossing 10% of thinks again after 21.1 settles.*

**What NOT to do about it, stated now because each is tempting and each is a
scar in this file.** Do not tell the creature to write shorter tools -- that is
a mechanism, not an invariant, and it aims the fix at the creature for a bound
that is ours. Do not keep raising the budget on a shared free tier; §4 makes
that a rung's terms rather than a knob. And do not have the framework split
the write for it, which would be the framework editing `tools/own` through a
side door (§2.1). **The shape that fits the design is a partial-edit hand** --
the creature already has hands, and a hand that replaces a range rather than a
file costs output proportional to the CHANGE instead of to the tool. That is a
change to the creature's world, so it lands the way item 14 lands: not while
something is being measured.

**21.3 `[x]` DONE 2026-09-21. `deploy_regression_day`: the same table, the
same floors, a day's wait.** The hour was honest and short -- on 2026-09-17 it
compared the hour after the cap change against the hour before and reported
*no correctness indicator crossed its floor*, **correctly**, because the cost
needed the creature's next whole-tool rewrite to arrive. `truncated|lost` went
1% of thinks to 32% over the first day and 53% by the third. The floor that
would have caught it (`REG_LOST_SHARE`, 10% and at least double) already
existed; nothing was watching it a day out.

Both readings are kept and neither substitutes: the hour catches a parser that
breaks instantly, the day catches a cost that arrives with the next big edit.
Each writes its own report beside the other, because two readings of one start
are two pieces of evidence and evidence that overwrites evidence is not
evidence. Proven on a synthetic day where the hour is clean and half the
commands are gone by the end -- the hour stays quiet, the day alarms and names
the lost-command share.

> **Two faults of mine, both caught by the gate inside a minute.** Renaming
> `hour_complete` to `span_complete` stopped the report being written, because
> a consumer read it -- this project's own *when a field changes, every reader
> changes in the same commit*. And the page took `reg[0]`, so once a second
> reading existed, whichever the registry listed first won: the day's, still
> pending with no table, which suppressed the hour's section entirely. **A
> position in a list is never a reason** (§5, 2026-09-15), here in the
> renderer. Both sections are now rendered by name and labelled.

~~**21.3 (original) Why nobody noticed for three days, which is the more expensive
half.**~~ `commands_lost[gemini]` fired on 09-18 and kept firing. The page was
right, the detector was right, and the reader had moved on to other work.
`deploy_regression` compared the hour after the cap change against the hour
before and saw nothing, because the effect built over a day. *Trigger for a
fix, not a rule: `deploy_regression` gets a second reading at 24 hours as well
as at one hour.* A one-hour window cannot see a regression that arrives with
the creature's next big edit.

---

## Phase 6 — the root (added 2026-09-18)

### 20. `[~]` The cousin is SPECIFIED as an inhabitant and IMPLEMENTED as an inspector — 20.1-20.3 done; 20.4 open with a dated trigger

**Found 2026-09-17 in discussion, by reading the two prompts instead of the
journal.** Tue asked whether the board was treating symptoms rather than
something fundamental. It was, and this is the thing it was treating symptoms
of. Nothing in this item edits a frozen prompt.

`CREATURE-PROMPT.md` tells the creature exactly who it builds for: a cousin
that *"wakes with no idea what changed while it slept"*, *"loses track of what
it learned"*, *"has no good way to plan across cycles"*, and *"does everything
itself with no way to offload work"*. Four of the five starter-map categories
follow directly from that description.

**The cousin we built has none of those properties.** It does not sleep and
does not wake. It has no yesterday: `sync_cousin_world` gives it a fresh copy
of the creature's whole mind per visit, the copy is discarded with whatever it
did to it, and its `remember` hand writes into that copy. That was deliberate,
and it is how §2.3 stopped being a promise and became a fact. The cost was
never priced.

**So the creature builds memory, recall, planning and offloading for an agent
structurally incapable of using any of them**, and the cousin judges the result
with the only test available to something that has no work to do: did it run.

**What this explains, each previously filed as its own item:**

- **the same want four times** (16.5) -- a capability request from an agent
  with no tomorrow to spend it in can never be exercised, so it can never be
  discharged, so it repeats
- **the usage menu accepted four times** -- with no job to fail at, *it
  started* is the whole of the available evidence
- **the wrapper stacks** -- convenience is the only value a layer can add for
  a user who is never under load
- **item 8's correction half saying NOT MEASURABLE** -- a repair can only be
  judged against a job
- **item 16 contradicting the brief**, above

- **20.1 `[x]` DONE 2026-09-18. The cousin gets continuity of its own, §2.3
  untouched -- and it turned out to be hiding something worse.** Reading the
  mechanism to build the store found that the cousin's `state/memory.json` was
  **byte-identical to the creature's**: the judge held the builder's notes,
  including `compare-subtask-logs-baseline-verified true` and `current-phase
  done`, and had printed all 25 keys in two live probes with a bare `recall`.
  **Invariant now: the cousin is handed the creature's WORK, never its NOTES.**
  One change closes both -- the creature's notes never enter the cousin's
  world, and what the cousin itself remembers is kept beside that world
  (`cousin-memory.json`, outside every container mount) and reinstalled each
  visit. **Red-proven first** on the laptop: the new test failed on exactly the
  two properties, printing the creature's keys as evidence. Two older
  assertions were REVERSED rather than deleted, one of which had encoded the
  leak as desired behaviour since 2026-09-16; the boundary test is now three
  assertions where it was one, because weakening a boundary test to let a
  change pass is a scar in §5. Gate 841 green. **What this does not do:** give
  the cousin anything to remember ABOUT. That is 20.2.
> **20.2 AND 20.3 WERE REWRITTEN 2026-09-18, because the founding documents
> had already answered them and I had asked Tue the wrong question.** He sent
> me back to `README.md` and `ARCHITECTURE.md`. Both are explicit: the cousin
> is not to have work of its own. *"Success is framed as a handover -- but the
> tool STAYS HOME. The cousin does not take it away. The creature bears the
> cost of handover quality and keeps the benefit"* (§4). A cousin with its own
> mission is a second creature, and the asymmetry the design rests on is gone.
> The discarded version of 20.2 asked for *"work that spans visits, whose
> outcome can be checked"*, and 20.3 asked Tue to choose that work. Neither
> was the design's question. Kept here because the wrong version is the
> instructive part: I was reasoning from CLAUDE.md, which is the maintenance
> log, instead of from the two documents that say what this is.

- **20.2 `[x]` DONE 2026-09-19. The headline metric is computable, and it
  says NOT YET rather than zero.** `monitor/derive.surviving_capability` plus
  a page section; red-proven before it existed; gate 885. **First live
  reading, 2026-09-19 14:58, run 6.1 days old: 0 survived / 0 have not / 58
  cannot be judged yet**, because the window is 7 days and the run is younger
  than it. The leading indicators, which ARE true today: **49 of 58 tools have
  been reached more than once by their user, and the widest first-to-last span
  is 6.0 days.** The metric starts answering tomorrow, which is the first time
  this project can answer the question it says it asks first.

  > **AND IT DID, 2026-09-21 01:42, on a run 7.5 days old: one tool has
  > survived it.** That tool is **`plan` -- named by 12 others, reached by
  > its user 107 times across 7.4 days.**
  >
  > **The other two columns are not quoted here, and that is a correction.**
  > They read 4 and 58 at 01:42 and 7 and 56 at 02:37 the same night,
  > because a tool's window closes on its own clock. A verifier caught this
  > document quoting a 46-minute-old pair as though it were a result. Read
  > them off `live/monitor/status.md`, which regenerates every five minutes
  > and names the engine that produced them.
  >
  > **One is not a score and must not be quoted as one.** It is the first
  > non-empty answer to the question `ARCHITECTURE.md` §12 says this project
  > asks before any other, and the honest reading is *the metric works and the
  > run is barely old enough to use it*. The number that will mean something
  > is the same three columns a week from now, when most of the 58 have closed
  > their windows -- and it counts capability that SURVIVED, so it can go down
  > as well as up.
  >
  > **What it does not say:** that `plan` does what its header claims. This
  > page measures that its user kept coming back; whether the handover worked
  > is the verdict's job, and `plan` carries 10 accepts against 6 returns.

  > **THE MIDDLE BAR WAS READ WRONG FIRST, and the correction is the
  > interesting part.** *"Invoked by something else"* -- I built it as
  > *another TOOL names it*, i.e. composition, and the first render said 44
  > tools had failed that bar. Wrong, by §4 of the same document: a
  > single-occupancy fault is *a defect that survives only because the author
  > is the sole user*, and **a tool called by another of the author's own
  > tools is still single-occupancy, because the author wrote both.** A
  > wrapper stack does not make a second party. The bar is *someone other than
  > the AUTHOR ran it*, which in this design is the cousin. Composition stays
  > on the page as context, because it is worth knowing, but it no longer
  > fails a leaf tool its user reaches for daily. Caught by reading the output
  > and disbelieving it, before the commit.

  > **The edge scan carries a stated ceiling** (`EDGE_SCAN_MAX`, 400) and
  > reads each file once against one compiled alternation. The parent's
  > version of this ran 187,489 full-content regex scans per wake, took 28
  > seconds, got worse every time the creature succeeded, and was found
  > because a human could hear the laptop fan.

  Original entry follows, because its reasoning is what produced the item:

- **20.2 (original) A visit is a WAKE, not an inspection -- so that §12's headline
  metric can exist at all.** `ARCHITECTURE.md` §12 names what this project
  measures first: **"tools that start, are invoked by something else, and are
  still invoked a week later"**, glossed as *surviving useful capability -- the
  thing the goal actually names*. That needs no external purpose. It needs the
  same user reaching for the same tool across days. Our cousin gets a wiped
  world and one nominated tool per visit, so **the number this project says is
  its headline has never once been computable.** With 20.1 shipped the cousin
  can carry what it learned; what remains is that a visit lets it reach for
  whatever it needs, not only the tool under test. **Acceptance:** for a tool
  the cousin chose itself, the journal shows first use, re-use on a later day,
  and the metric computed from probes rather than asserted.
- **20.3 `[x]` DONE 2026-09-18. Built the cousin's instruments, which
  `ARCHITECTURE.md` §5 specified on 2026-09-10 and nobody wrote for eight
  days.** `instruments/` holds five: `lib-startable`, `lib-stubs`,
  `lib-twins`, `lib-deps`, `lib-stores`. They go into the cousin's bin only
  (§2.4: a hollow-stub detector aimed at the creature's own library is telling
  it about its own bugs), the invocation template says they exist, each says
  what it did NOT check, and the gate proves the creature's bin never receives
  them. Red-proven first. Nothing schedules them.

  > **They found four things on their first run against the real library, which
  > is the same pattern every instrument here has shown on its first day.**
  > `subtask_logs_test.json` **does not parse at all** -- a shared store no
  > reader can read, which is the fifth single-occupancy fault the README lists
  > and the fifth brief test, and nothing in this project could see it before
  > today. A tool called `path` is **named by 37 of 60 tools** and had never
  > appeared in any reading of this library: the real hub is not `archive` or
  > `plan`. `clear-baseline` and `get-baseline` are orphans that neither call
  > nor are called. And 60 of 60 tools parse, which retires the last of the
  > "broken floor" readings for good.
  >
  > **None of this is a verdict and the framework must not make one.** The
  > facts are the cousin's to use when it wants them; §2.3's dividing line is
  > that a scan gathers a fact and then decides what to say about it, and only
  > the second half was ever framework.

- ~~**20.3 `[ ]` Build the cousin's instruments, which `ARCHITECTURE.md` §5
  specifies and nobody built.**~~ *"A handful of small deterministic scripts --
  startability, hollow-stub detection, duplicate-stem listing, dependency
  edges, store parse rates... They are tools, they live where tools live, and
  the cousin runs one when it wants to know something."* **This is the answer
  to item 16**, and it is a script rather than a brief rule: Tue asked that
  noticing a tool which serves nothing should rest with the cousin, and the
  architecture had already said how -- give it the instrument and let it look,
  rather than adding a rule telling it to have an opinion. **Acceptance:** the
  scripts exist where the cousin can run them, the cousin is told they are
  there (the invocation template, which is kernel text, not the frozen brief),
  the journal records a visit where it ran one unprompted.

  > **CONFIRMED IN PRODUCTION 2026-09-19.** The cousin ran `lib-deps plan`
  > twice, unprompted, and wrote its own reason into the block: *"See what
  > other tools the `plan` command depends on (helps understand its
  > requirements)"*. It got back that `plan` is named by nine tools and that
  > if it breaks those nine may too. That is §5's instrument doing exactly
  > what §5 said it would, on a library its user cannot otherwise see whole.
  > **Both visits were then deferred with every rung at quota** (item 18.7),
  > so neither reached a verdict. The instrument works; the economics around
  > it do not.

- **20.4 `[~]` THE COUSIN USES ITS CONTINUITY. Measured 2026-09-21, and it
  refutes what this item said for two days.** A verifier read the journal
  instead of this file:

  | | |
  |---|---|
  | `cousin_memory` harvests since the fix | 127 |
  | empty (`kept=0`) | 74, all of them **before 09-19 20:35** |
  | carrying a note (`kept=1`) | **53, and not one empty since** |
  | what it carries | `baseline-parent-id: 100` |

  **Its first note has survived 31 hours and 53 visits.** It is exactly what
  continuity is for -- an ID it needs between visits and would otherwise have
  to re-derive -- and it is the cousin, unprompted, using a store nothing
  tells it to use beyond one line in the template.

  ~~**20.4 (original) The cousin has continuity now and does not use it.** Confirmed
  in production 2026-09-19: **68 harvests since the fix, every one empty.**
  The likely cause is structural rather than a wording problem: its only
  shell is the INVOCATION call, which happens *before* it sees the output and
  before it forms a judgement. At the moment it learns something worth keeping
  -- writing the verdict -- it has no hands.~~ **That reasoning was good and
  the conclusion was wrong**, and the way it went wrong is this file's oldest
  habit: it was written on 09-19 from a window that ended at 09-19 20:32,
  three minutes before the first note was kept, and then quoted for two days
  as a standing fact. *Where a number can be generated, generate it.*

  **What is still open is a smaller and better question: it writes ONE note
  and has not added a second in 31 hours.** One key is continuity; it is not
  yet accumulation. *Trigger: when 20.2's metric has a full week, read the
  store's key count beside it -- a second key is the signal that the cousin
  has something to accumulate ABOUT, which is what 20.2 was always for.*

**Do not start 16, 17, 18.6 or 18.7 before this** -- each tunes a loop that is
not carrying anything. Recorded as a dependency and not a deletion, because
the reasoning in all four is good once there is load.

**The control nobody has ever moved.** The starter map is a variable. It has
been identical in both projects since the parent wrote it, so the library's
shape has never once been measured against a different instruction. Changing
it is a real experiment with a real before and after -- but `CREATURE-PROMPT.md`
is frozen (§0), it must be scored under item 8's discipline (a direction across
several reps, split by rung, detection and correction together), and it must
not move in the same window as 20.1 or neither is readable.

---

## Phase 8 — the line-by-line pass (added 2026-09-21)

### 22. `[x]` Read this framework against the spine's counterpart, one file at a time

**Tue, 2026-09-21, going to bed:** *"run a synthetic test on the code
afterwards testing a few edgecases going through line by line of the code in
the little framework we have compared to the growing-spine counterpart."*

Read side by side, reading only (§2.6): `kernel/journal.py` against
`executive/journal.py`; `kernel/think.py` against `executive/parser.py`, which
is 25 lines to our 160 and the difference is entirely scar tissue;
`kernel/backends.py` and `kernel/quota.py` against `keychain/`;
`kernel/body.py` against `executive/sandbox.py`; `kernel/forever.py` against
the loop's supervisor; then `monitor/derive.py` against nothing, because the
spine has no equivalent.

**EIGHT DEFECTS, each red-proven before its fix existed -- and the sixth was
mine, shipped in the middle of the pass, and found by the verifier rather
than by me:**

| | what | live? |
|---|---|---|
| `6bfd54d` | a marker understating a loss by 6,114 characters | **74 of 652** |
| `6bfd54d` | the creature's ladder banking a reply with no text as an answer | **9 of 1,967** |
| `6bfd54d` | a tool's own English able to declare the body dead | 0 of 2,929 |
| `6bfd54d` | a NUL byte in a command blamed on the body | never |
| `85a52fe` | the headline metric measured out of a window of BYTES | **due 09-26** |
| **`6bfd54d`, reverted in `1b04e82`** | **my own CRLF "insurance" changing how nine real replies parse** | **9 of 1,931** |
| `1b04e82` | the block-level trim dropping 4,727 characters with no number | live |
| `1b04e82` | the creature's predicate unasserted -- reverting `run.py` alone left the gate green | n/a |

**The sixth is the one to learn from and it is in §5 in full.** I measured
that 0 of 1,926 replies contained CRLF, wrote *insurance rather than a
repair* in the comment, and shipped `\r?` at both fence ends. `$` under
`re.M` makes a fence have to END its line, so a closer sharing its line with
the next opener stopped closing: two valid commands became one block carrying
a literal fence. **Measured risk 0, measured cost 9.** Reverted the same
night and proven identical to `5516eaf` across all 1,931 raw replies.

`replay_parser.py` is what replaces *be more careful*: save a baseline,
change the parser, compare, read what moved. It reports the nine against
`6bfd54d` and SAME against the revert.

The last one is the one to read if only one is read: `derive.load` reads the
last 24 MB of the journal, every other figure on the page is a count over a
recent window so a tail costs them nothing, and the headline metric is a SPAN
OF DAYS. Forced with a 4 MB tail against the real journal, the old code
returned 0 survived / 0 have not / 64 cannot tell and explained it with *"the
run is 2.1 days old"* about a run seven and a half days old.

**WHAT THE PASS MEASURED AND LEFT ALONE.** Each is a hold with a named
trigger, which is §4's test for a hold that is real:

- **22.1 `[ ]` The heredoc half of the 2026-09-14 fence scar.** A column-0
  fence inside a heredoc body still closes a block, so a tool whose source
  contains one lands cut. **0 real occurrences in 1,588 uncut replies** -- the
  five the first pass found were the creature quoting its own `| `-prefixed
  transcript, and the 192 the pass before that found were the journal's own
  800-character cap on `cmd`. *Trigger: the first real one, or any SyntaxError
  in a tool whose source contains a column-0 fence.* Not patched at three in
  the morning, because the 09-14 scar is specifically about what a midnight
  change to this parser costs.
- **22.2 `[ ]` A journal read costs 0.33 s at 14.6 MB and a wake does
  several.** Every piece of the manager's state is derived from the journal by
  design (§6.1) and the journal only grows: ~6-8% of a cycle today against a
  25-33 s model call, rising. This is the spine's *28-second scan a human
  found by hearing the laptop fan*, at one-hundredth of the size. *Trigger: a
  full read crossing 5 seconds (~220 MB, months away) -- or run 3, where it
  should be designed out rather than measured.*
- **Deliberately NOT copied from the spine: block de-duplication.** It drops
  a repeated identical block; we run both. Deciding a repeated command was not
  meant twice is a judgement about intent, and this framework holds bounds.
  26 of 1,927 replies repeat a block, nearly all `cat`.
- **Confirmed by running, not by reading:** the fault-injection drills
  (`rehearse.py`) pass end to end on the new code -- the container drill's 30
  checks all true, including `keys_unreadable`, `spine_invisible` and
  `tools_survived_respawn`; the give-up drill reaching exit 5 -> 2 bounded
  restarts -> `failed`, with `loop_error` firing ten times in a path that has
  **never once fired in production** (0 records in the whole of run 2, against
  2,410 waits, longest run 260 of a 600 ceiling).

**Acceptance, and it is checkable:** every fix above has a test that was seen
RED against the code as it shipped; the gate is green on both boxes (972
assertions on the laptop); and none of it was deployed into the window that
settles item 21.1.

---

## Phase 9 — what our own words presuppose (added 2026-09-21)

### 23. `[~]` Audit every instruction against what its recipient actually has

**Tue, 2026-09-21:** *"do we need to go through all our prompts and verify
they are fed to an agent with a goal and doesn't fall flat in the process?"*

Yes. **The class has now appeared seven times** (`CLAUDE.md` §5 lists them),
including the largest finding this project has made. One question per
instruction: *what does this presuppose about its recipient, and is that
true?*

- **23.1 `[x]` `CREATURE-PROMPT.md`, read line by line 2026-09-21.** Two live
  falsehoods found, both verified inside the running containers rather than
  argued.
- **23.2 `[x]` "install packages" — FIXED by providing the capability.**
  `HOME` now points at the mind, so `pip install --user` works and survives
  the body. The drift check learned the environment as a third field.
- **23.3 `[!]` "free-tier LLM API access over the network" — FALSE, and the
  fix is a real choice rather than a patch.** Neither box holds a credential
  and `selfcheck`'s `keys_unreadable` is designed to keep it that way. The
  creature ran `subagent-orchestrator run` **80 times** against
  `api.openai.com` with the literal string `"default_key"`, and **8 of those
  runs exited 0** while doing nothing. Three ways out, and they are not
  equivalent:
  1. **Retract it** at the brief's unfreeze — cheapest, and it costs the
     creature a whole category of tool it has spent eleven rewrites on.
  2. **A keyed proxy in the box** — gives the category back, and puts a
     credential where §5's oldest security scar says one must never be.
  3. **A framework hand** that makes a rung call on the creature's behalf,
     keyless from inside — keeps `keys_unreadable` true and spends the
     shared free tier the cousin and the spine are already contending for.

  > **RECOMMENDED 2026-09-21, asked for by Tue — *is the keyless hand right,
  > or is it framework bloat?* NOT (3), and not because it is bloat.**
  >
  > **It is not bloat by this project's own line.** The deleted 99% was
  > *scheduling, caches, edge-trigger state files, warning composition,
  > surfacing rules -- all of which exists because nobody was there to
  > decide.* A hand is a CAPABILITY, not apparatus; this framework already
  > ships five, and the spine ships `ask` as exactly such a tool. The
  > bloat objection does not survive contact with the definition.
  >
  > **The reason not to build it is that the user has never asked, and it is
  > measured rather than assumed.** 117 wants across run 2, **99 distinct**,
  > and **one** touches this area at all:
  >
  > > *"delegate to sub-agents or perform real work instead of just echoing
  > > the task"*
  >
  > **That is not a request for the capability. It is the cousin reporting
  > that the tool echoed the task and did nothing** -- which is precisely
  > what `subagent-orchestrator` does with no credential. The single datum
  > anyone would cite as demand is the symptom of the missing key. What the
  > user actually asks for, over and over, is small deterministic plumbing:
  > the twelve most recent distinct wants are JSON flatten/merge/filter and
  > plan filtering.
  >
  > **And the cost of building it is worse than neutral. 28 of the 69 tools
  > -- 41% of the library -- are already in or downstream of the
  > subagent/subtask family**, administering the outputs of an orchestrator
  > that has never once authenticated. A keyless hand would make that
  > category WORK rather than make it QUESTIONED, and the 2026-09-18
  > retraction is that the creature builds the list it is handed. Making the
  > handed list executable does not test this project's thesis; retracting a
  > promise the box cannot keep does.
  >
  > **So: (1), retract, as the first scored change at the brief's unfreeze**,
  > under item 8's discipline -- a direction across several reps, split by
  > rung, detection and correction together.
  >
  > **THE ONE THING THAT WOULD FLIP THIS, and it is Tue's because it is about
  > what the project is FOR.** The spine's creature HAS `ask`; ours does not;
  > both are handed the same starter map. That asymmetry is a confound in the
  > comparison (§4), and it has been live for the whole of both runs with no
  > document recording it. **If the comparison is meant to be clean, the
  > argument for giving ours the same hand becomes the strong one** -- not
  > because our creature needs it, but because the other one has it. That is
  > a question about the experiment, not about the engine, which makes it
  > his.

- **23.4 `[~]` `MANAGER-PROMPT.md`, the same pass -- READ IN FULL 2026-09-24,
  NOTHING CHANGED.** Read line by line with the one question; changes to the
  brief are scored before they are made (item 8), and the scoring needs the
  Windows bench's GPU. What it presupposes, and what is true:

  | the brief says | true of the cousin we run? | consequence |
  |---|---|---|
  | *"Every invocation reduces to: can I use what it JUST built?"* | **No** on 220 of 246 visits -- stalls and heartbeats built nothing just now | the same fault 23.5 fixes in the kernel's case text; **once `TRUTHFUL_VISITS` is on, the brief and the case contradict each other on every stall visit.** Arm C must be read for that, not only for detection |
  | the five tests apply *"only as tests of what the creature is claiming"* | nine visits in ten carry no claim | four of the five tests have nothing to test on a stall; only "does it run for me" is left. Probably right, never said |
  | `ACCEPTED` -- *"the claim stands, the done-mark lands"* | no claim and no done-mark on most visits | harmless mechanically -- only a RETURN gates -- and wrong as a description |
  | *"the creature returns with 'I fixed the thing you complained about'"* | **the cousin never sees a word the creature writes**, only the framework's one-line claim, and until 23.5's notes it could not remember its own complaint | the whole repair section described a judgement it had no means to make; verdict-time notes are the first thing that gives it one |
  | *"you genuinely could not do the thing you came to do"* | it has no thing it came to do | item 16's root, already recorded |
  | *"a tool that refuses incomplete input ... you called it wrong"* | written for the bare probe; the cousin now CHOOSES its arguments | excuses the cousin's own thin invocation (16.5) |
  | *"It has no outbound channel"* | `say` exists and the hands block will announce it | true of the channel TO THE COUSIN, which is what the sentence is for; false as written |

  **One hypothesis REFUTED by the journal, kept because the method is the
  point.** The brief says a missing key *not caused by this work* is an
  ACCEPT with a `noticed` -- which, beside 23.3's keyless
  `subagent-orchestrator`, looked like the rule that hid a tool that cannot
  work. It did not: the cousin judged that tool **once** in its 80 runs and
  RETURNED it, with *"Error solving subtask: 'choices'"* in the testimony.
  What hid it was that the cousin almost never visited it.

  *Trigger: arm C (item 23.5) on the Windows bench, whose reading decides
  whether the brief's "just built" sentence must change before the switch is
  flipped. Brief edits are then scored as their own arm.*
- **23.5 `[ ]` The kernel's own served text** — the history header, the
  library legend, the want block, the invocation template. Not frozen, so
  anything found here is fixable the same day.

---

### 24. `[x]` A pure-ollama deployment on the Windows box -- PROPOSED AND DECLINED, both on 2026-09-23

> **DECLINED BY TUE THE SAME HOUR, and his reason is better than the one this
> write-up gave.** *"lets skip the idea for now the lower context window will
> ahve the two programs compete on fixes i think its too much of a hassle."*
>
> The analysis below argued from POPULATIONS OF NUMBERS -- a third set of
> figures that must never be mixed with the other three. Tue argued from
> **CONSTANTS**, which is the sharper objection: a smaller-context model hits
> its walls in different places, and §5's standing rule is that a cap, a
> budget or a ladder order is tuning and therefore **per-model**. So every
> such constant would have two right answers and one config file, and each
> fix would pull the engine toward whichever deployment was being looked at
> that evening.
>
> **This very day is the worked example.** `HISTORY_TOTAL_CHARS` went to
> 40,000 because the replay put the knee there for a rung with a large
> context. On an 8B at `num_ctx` 32k that number is not merely unnecessary,
> it is unaffordable -- the served context would not fit -- so the same
> measurement, run on the other box, would have demanded a different answer
> to the same constant on the same evening.
>
> **It is DECLINED rather than deferred, so it is off the board.** §4's test
> is that a hold names a trigger and a date; this has neither, because it is
> not waiting for anything. What survives is the capability WITHOUT the
> second deployment: the Windows box has ollama with `gemma4:12b` and the
> gate's live-model assertions run there (`CLAUDE.md` §0, habits). A local
> rehearsal is a thing to RUN, not a thing to DEPLOY -- and running one needs
> no second engine, no second config and no second service.
>
> Reopen only if someone is proposing the *second creature*, which is item 11
> territory and gated on an empty board.

**The proposal and the analysis are kept below**, because a rejected design
with its reasoning is worth more than a deleted one.

*"i was wondering if we should make an alternative version of the
growing-cousin that is pure ollama run and for this pc not the laptop. but
basically the same program and synched with the same fixes all around - or is
that too hard to handle?"*

**It is not hard, and the reason is that almost none of it is code.** The
ladder is already configuration (`rungs.local.json`, §0), `backends.ollama`
already exists and the gate already drives `gemma4:12b` through it, and
`--root` and `--body docker` are already flags. So *the same program with
different rungs* is a config file and a service definition.

**It must be a DEPLOYMENT, not a fork, and that is the whole of the
maintenance answer.** §2.6 carries the scar in as many words -- *a file that
keeps being merged is how two independent systems quietly become one* -- and
it was written about `observer.py`, one file. A forked engine would rot inside
a week and every fix would have to be applied twice, which is how the two
copies stop being comparable and stop being correct. One codebase, two
configs, cannot drift.

**The real cost is operational**: a Windows service in place of systemd, the
monitor's five-minute timer, and confirming `DockerBody` works against Docker
Desktop (the WSL distro list shows it is installed). An evening, not a project.

**TWO SIZINGS THAT MUST BE DONE BEFORE PROMISING IT WORKS**, both measured
2026-09-23 while building the local A/B rig:

- The served context is now `CREATURE-PROMPT.md` (8,935) + the library
  (~12,000, growing) + a transcript bounded at **40,000** -- roughly 61,000
  characters, ~17,500 tokens, so `num_ctx` wants ~32k. **`gemma4:12b` needs
  8.1 GB of a 10 GB card at `num_ctx` 8192 and will not fit beside a 32k KV
  cache.** The local instance runs an 8B. That is a DIFFERENT MODEL FAMILY
  from the deployed rung, and it is the same shape of confound §4 recorded
  about the spine's `ask` hand.
- One ollama rung means **no ladder fall-through at all**, so it does not
  exercise the quota paths, the walling logic or `ladder_dry` -- the code
  paths that produced four of §5's scars.

**RECOMMENDED SHAPE: a rehearsal bench, not a second creature.** As a bench it
is pure upside and §4 has asked for it since 2026-09-12 -- *anything needing
many cycles quickly must be run against a local model on a development box
first*. On 2026-09-23 that capability was missing and the cost was visible:
production was restarted twice in one evening to answer a question about
`recent_block` that a local loop could have settled in minutes. As a second
LIVING creature it is a THIRD population of numbers, on different hardware,
under a different model, with a one-rung ladder -- and §0's standing rule is
that the three existing populations *must never be mixed*.

~~**THE ONE THING THAT IS TUE'S**, and the only one: bench, or a second
creature he can watch grow on his own GPU.~~ **Answered within the hour:
neither.** The second is genuinely interesting and is close to **item 11**,
which he himself gated on an empty board on 2026-09-21 -- so it is not to be
started quietly under another name. And the bench does not need a deployment
at all, which is what the decision above turns on.
