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

### 1. `[ ]` The complaint-fidelity census runs by itself

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

### 2. `[ ]` The chat channel is a scheduled intention, not a silence

Tue, 2026-09-16: **it stays.** It has sat in every "not built" list since
2026-09-11 without ever being decided either way.

- **2.1** No document describes it as merely *not built*; each states it is
  wanted, and scheduled as item 14.
- **2.2** The reason for the slot is recorded: it adds a surface to the
  creature's context, so it must not land while phases 3–4 are measuring.

### 3. `[ ]` The inherited library is recorded as NOT executed

§6.2 says *"Decided 2026-09-10: copy"*. Run 2 started from nothing. The
doctrine claims a thing that never happened, and the refutation path it was
chosen for — a known-answer test set — was never taken.

- **3.1** §6.2 states the decision was not executed and why.
- **3.2** It is bound to run 3 (item 11) with the tagging requirement intact.

### 4. `[ ]` The cousin's audit has a named trigger

§6.4 currently ends *"No named trigger yet — this needs one."*

- **4.1** The trigger is stated: **when the cousin can invoke tools with
  arguments (item 9)**.
- **4.2** The reason is stated: an audit by an agent that can only run things
  bare is confident garbage by construction.

### 5. `[ ]` The evidence tarball's home is recorded

Tue, 2026-09-16: **laptop only**; the hashed manifest is what the repo
carries.

- **5.1** `CLAUDE.md` §0 and `deploy/README.md` say so without hedging.
- **5.2** `.gitignore` keeps `evidence/*.tar.gz` out of the repo.

---

## Phase 1 — make the untriggered paths triggerable

### 6. `[ ]` The fault-injection rehearsal

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
- **6.7** The live root is byte-identical before and after every drill.

---

## Phase 2 — close the oldest security hole

### 7. `[ ]` The creature's shell cannot read the engine's keys

Open since 2026-09-13 and named in §7 as Tue's. The child environment is
already an allow-list; the key **files** remain readable by anything running
as this uid.

- **7.1** From inside the live body: `cat ~/keys/*.key` fails.
- **7.2** The engine itself still reaches every rung — it reads those files
  per call.
- **7.3** Six effects checked from inside the sandbox before it ships (body
  answers, hands on PATH, writes `live/`, reads the repo, reaches both
  providers, spine invisible), as on 2026-09-13.
- **7.4** Rehearsed under item 6 before it goes live. *A sandbox that breaks
  the run is discovered at 03:00 by nobody.*
- **7.5** `selfcheck` gains the assertion, so the bound is re-proved at every
  start rather than once.

---

## Phase 3 — unfreeze the brief

### 8. `[ ]` Held-out cases, so a brief change can be scored

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

---

## Phase 4 — the boundary question

### 9. `[ ]` The cousin gets its own shell

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
- **9.5** Measured against item 8's baseline, split by rung, before and after.

### 10. `[ ]` Who may propose a cull

Deliberately deferred until item 9 produces data: a library that is finally
*used properly* may consolidate itself — the creature has done it twice
unprompted.

- **10.1** A named trigger and a date, not a hold waiting on "more
  information" (§4).
- **10.2** Whatever the answer, the cousin never gains a write path into
  `tools/own` (§2.3).

---

## Phase 5 — settle

### 11. `[ ]` Run 3

- **11.1** Clean start on a framework that has stopped changing weekly.
- **11.2** Carries item 3's decision, with every inherited tool tagged at t=0
  and every metric split on that tag.
- **11.3** An evidence pack for run 2 is committed before it ends.

### 12. `[ ]` Spine restarts

- **12.1** `systemctl --user enable --now growing-spine`.
- **12.2** §4's era note records the date, so no figure crosses it silently.

### 13. `[ ]` The 2400-character window — explicitly NOT doing

*Don't fix what has no symptom.* It stays on the board as a decision, not as
something forgotten.

- **13.1** Recorded as not-doing, with the symptom that would reopen it: the
  creature re-reading one tool across consecutive wakes without editing it.
- **13.2** A detector for that symptom, or a stated reason there is none.

---

## After the plan

### 14. `[ ]` The chat channel (item 2's build)

Slotted here because it adds a surface to the creature's context and must not
land while anything is being measured. Acceptance criteria to be written when
it starts.

### 15. `[ ]` Should a body that cannot be respawned end the run?

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
