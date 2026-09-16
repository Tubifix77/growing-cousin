# PLAN.md — the thirteen, with the test that says each one is done

Written 2026-09-16. Every open item this project knows about, in the order they
will be done, **one at a time**, each with acceptance criteria that can be
checked rather than asserted.

**Two hard rules, both earned:**

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

### 9. `[~]` The cousin gets its own shell  — built and live; 9.5 is MEASURING (window opened 2026-09-16 02:49)

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
> **THAT WINDOW IS VOID, AND WHY IS THE WHOLE FINDING. Reopened
> 2026-09-16 18:36:16, engine `3f20c3f`.** Fifteen hours produced **112
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
> **THE AFTER-WINDOW STARTS 2026-09-16 03:19:13, ENGINE `221b978`.** It was
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

### 11. `[~]` Run 3  — 11.2 and 11.3 met; the run itself is deliberately not taken

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

### 12. `[!]` Spine restarts — OVERTAKEN BY EVENTS

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

### 13. `[x]` The 2400-character window — explicitly NOT doing

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

### 14. `[~]` The chat channel (item 2's build)  — 14.1–14.4 met; 14.5 rides with the brief's unfreeze, and is now watched

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

> **14.5 is NOT met and cannot be met yet.** `CREATURE-PROMPT.md` lists the
> built-in hands and is FROZEN (§0) until item 8.4 has a baseline. So `say`
> exists, works, and the creature has not been told about it — a hand nobody
> mentioned is a hand nobody uses, which is this project's *dead channel*
> scar with the freeze as its cause. **Trigger: add `say` to the prompt's
> hand list in the same change that unfreezes the brief.** Recorded here so
> the unfreeze does not quietly forget it.

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

### 16. `[ ]` The cousin, not us, notices when a tool serves nothing

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
