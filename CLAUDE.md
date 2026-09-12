# CLAUDE.md — working on Growing Cousin

Sibling of [Growing Spine](https://github.com/Tubifix77/growing-spine). Same
creature, same volume, same instruments; the deterministic framework replaced by
a second agent — the cousin — carrying stated purpose instead of encoded
mechanism.

Tue is the human. **This file is yours.** Maintain it: when a measurement
contradicts §7, correct §7 and commit. When you learn a rule the hard way, add it
to §5. Date what you write and name the instrument behind every number.

**Read `ARCHITECTURE.md` and `MANAGER-PROMPT.md` before touching anything.** This
file is doctrine for *maintaining the engine*. `MANAGER-PROMPT.md` is doctrine
*toward the creature*, and it is the product — the artifact the parent project
never had, because there the creature-facing doctrine was implemented rather than
stated.

---

## 0. Status — read this before anything else

**A creature and its cousin run together, on the real free-tier rung. Nothing
is scheduled.** `kernel/` is the 1% from `ARCHITECTURE.md` §14 — journal, body,
think, triggers, cousin, cycle, backends — `run.py` drives a real creature
through it, `census.py` is the only thing that checks the manager, and
`tests/test_kernel.py` is the gate: **149/149 green with the real model in the
loop.** `trial/` remains the brief's own measurement.

**The ladder is configuration, not code**: `rungs.local.json` and
`rungs.cousin.local.json`, both gitignored, both naming a `key_file` outside the
repo. `rungs.example.json` is the committed template. With no spec present the
run uses the local standin **and says so in its banner** — a run that silently
falls back is a run whose numbers get quoted later as the real rung's.

**The gate (§3-equivalent):**

```bash
python tests/test_kernel.py > /tmp/k.out 2>&1; echo "GATE=$?"; tail -1 /tmp/k.out
```

To a FILE, never a pipe — a pipe once swallowed `sys.exit(1)` in the parent and
let an ungated commit ship. Check the literal string `ALL TESTS PASS`.

**Three populations of number live here and must never be mixed.**

1. **The parent's behaviour** — quoted from Growing Spine, not re-measured here.
2. **The brief's own measurement** (`trial/`) — produced locally against fixtures
   captured read-only from the parent's live library.
3. **The engine's behaviour** (`tests/`) — produced by the kernel actually
   running, against a `LocalBody` and a local model.

**None of the three is evidence for another.** A green gate says the workflow is
correct; it says nothing about whether a creature can live in it. And **no number
here yet comes from a creature that has run a real cycle on the real ladder** —
when one does, this section is the first thing to rewrite.

Do not let a borrowed number turn into a claim about this system. The parent
project's most expensive errors were numbers nobody could source.

## 1. The two rules

**1. This engine's faults will be in what the manager SAYS, not in what it does.**
The parent's faults were in Python: a constant nobody chose, a guard hunting one
literal, a default branch that raised. Those failure modes are mostly gone here.
What replaces them is worse-behaved, because it is not reproducible and no test
catches it. So:

- When the creature does something wrong, read the manager's last three verdicts
  before reading the creature's code. The fault is usually upstream in prose.
- Fix the **brief**, never the individual verdict. A verdict is one sample; the
  brief is the machine that produced it.
- State the invariant, never the mechanism — the same rule the manager is given,
  applied to the manager itself. Telling it "stop mentioning `jq`" reproduces the
  exact fault the parent spent a week diagnosing, one level up.
- A change to `MANAGER-PROMPT.md` is a behaviour change and needs a test that
  fails without it. Text here is held to the same standard as code, because text
  here **is** the code.

**2. You are the engine's debugger, not the creature's nanny, and not the
manager's either.** Neither agent may depend on your inspection. If a fault is
only caught because a human reads a log, it is not fixed.

- **Stop the bleeding first, and that is not an intervention.** If something is
  wedging the system, kill processes and respawn the body immediately. Its
  *tools* are its world; its *processes* are not.
- If a hand had to intervene at all, **that is the finding**: the kernel was
  missing a bound. The fix is a limiter — a cap, a timeout, a reaper — never an
  edit to a tool.

## 2. Hard boundaries

1. **Never edit the creature's `tools/own/`.** Its tools are its world. Exception:
   explicit consent from the creature, for a specific job, backed up first.
2. **Never edit a manager verdict after the fact.** It is testimony; rewriting it
   makes the complaint-fidelity census meaningless, and that census is the only
   thing keeping the manager honest.
3. **The manager never writes or edits the creature's tools.** It is the second
   *user*, not a second builder. If you find yourself adding a write path from
   manager to `tools/own/`, you are building the thing the parent project
   examined and rejected.
4. **Never tell the creature about its own bugs.** Not through the manager, not
   through chat. The manager reports what happened *to it*; the diagnosis is the
   creature's work and its growth.
5. **Never let the manager claim an experience it did not have.** A fabricated
   complaint is the exact fault this design exists to prevent, committed by the
   agent meant to catch it. Instrument it (§7 complaint fidelity); do not trust
   it.
6. **Never touch Growing Spine from this repo.** They run in parallel; the
   comparison is void if either is edited to make the other look better. No
   shared files, no shared volume, no shared container.
7. **Culls need the creature's consent.** Ask, offer alternatives, honour what it
   keeps.
8. **Never commit secrets.** No `config.yaml`, no keys, no laptop-only failure
   maps. If this repo goes public, that rule is load-bearing.

## 3. What transfers from the parent, and what does not

**Transfers — these are engine-independent:**

- All of §2's boundaries above, adapted from the parent's.
- The method: fix the machine that produced the fault, never the fault; make the
  fault visible so the creature prunes it itself; surface on a change of state,
  never continuously; state the invariant, never the mechanism.
- Tue's standing decisions (§4 below).
- **8 of the parent's ~33 scars** — specifically the ones about text the creature
  reads. Those are the only scars that have ever *recurred* after being fixed,
  and this engine is entirely text, so they hit harder here.

**Does not transfer — do not copy these in as if earned:**

- Every scar about Python framework internals: `classify_error`'s default,
  truncation caps in series, the quadratic dependency scan, guards keyed on one
  literal string, the `st_mode` cache key. This engine does not have those
  failure modes. Importing them as doctrine would be archaeology posing as
  experience.
- The parent's §8 live state. It describes a different running system.

**This repo starts with almost no scars, and that is the honest condition.** The
parent's doctrine is valuable *because it was earned*. Resist the urge to
pre-populate §5 with plausible-sounding lessons; a scar nobody paid for is a
guess with authority it has not earned.

## 4. Standing decisions (Tue's, inherited)

- **Growing Spine is on the SAME API accounts, so the free tier is SHARED**
  (Tue, 2026-09-12). This engine gets at most half of what it would with its own
  account, and the two projects can starve each other. Three consequences, all
  binding: (1) a rate limit here may be the spine's traffic, not a real ceiling
  — never read a 429 as a measurement of this engine's cost; (2) **throughput is
  not comparable between the two projects** and must never be reported as if it
  were, though cost-per-cycle and verdict quality still are; (3) the ladder must
  be quota-polite — fall through on 429 rather than retry, which is why 429 is
  `NEXT` and not `RETRY` in `classify_error`. Measured the same day:
  `openrouter/gemma-4-31b-it:free` was already returning 429 while
  `gemini/gemma-4-31b-it` answered in ~32s.

- **Free tier only, permanently.** "We get what is available without paying
  anything ever." A rung behind a paywall is defunct by definition; removing one
  needs no decision. Rung count and concentration are *outcomes*, not targets.
- **Quality floor over capacity.** No weak model in the ladder. Under a shared
  cap, weak calls starve smart rungs and a weak author's buggy tools are lasting
  pollution.
- **Reversible actions are just done**, not asked about.
- **A known-failing behaviour in our own framework is fixed without asking.** A
  fault in the creature's *own output* is never fixed and never needs sign-off
  either: the response is always visibility.
- **Don't tune a constant with no evidence.** **Don't fix what has no symptom.**
- Distinguish a hold with a **named trigger and date** from a hold waiting on
  "more information" — the second is inaction in the costume of caution.

## 5. Scars

*Signature first, so a recurrence is a lookup and not a re-diagnosis. Name what
was measured, with what, and on what date.*

- **A checker that cannot distinguish the thing it measures reports a
  clean-looking wrong number, never an error — and I built four in one evening
  while writing the tools meant to catch exactly that.** 2026-09-10, all found
  in `trial/`, all mine, none in the design. (1) Results written only at the end
  of a run: a killed run lost eight earned verdicts. (2) `raw_len` stored and the
  raw reply discarded, which collapsed *said nothing*, *cut off mid-thought* and
  *answered somewhere I did not look* into one label — three faults, three
  different fixes. (3) `compare.py` selecting the **latest** run per model,
  reporting a one-case smoke test as a clean score; then, "fixed" to select the
  **most rows**, it tied 12–12 and chose the run where every reply was empty.
  (4) A prose-smell regex that flags quoting an error you saw on screen as
  "diagnosis", when that is testimony — the guard-hunting-one-literal fault, in
  the instrument built to police literals. **Invariant: store the raw evidence,
  not a summary of it; a summary cannot be re-interrogated when the summary is
  what is wrong.** Each of these was caught only because raw evidence survived.
  And **"most complete" has to be defined by what the rows are FOR** — usable
  verdicts, not row count.

- **An empty reply that consumed its whole budget is a failure, not an answer,
  and raising the budget is the wrong fix.** 2026-09-10, `gemma4:12b` on twelve
  cases: `done_reason=length`, `eval_count=900`, `response` empty — a reasoning
  block opened and never closed. At `num_predict=3000` it still returned **0
  characters**, having burned 3,000 tokens. `think=false` returned a complete
  valid verdict in **216**. **Budget is not the binding constraint; unbounded
  reasoning is.** The general danger: such a call registers as a SUCCESS, so
  nothing walls the rung and nothing below it is ever reached — the manager is
  silently absent rather than visibly broken. Instrument: `done_reason` and
  `eval_count`, which the harness had been discarding.

- **When every model disagrees with your label, suspect the label.**
  2026-09-10: all three models returned `keyword-archive-store`, which the case
  set marks ACCEPTED. The tool tells the caller exactly what was missing and the
  harness gives the cousin no way to supply it, so the case is unfair as built.
  The invariant is not "tell a correct refusal from a failure" but **a user who
  has been told what was missing has not finished trying** — untestable until
  the cousin has its own shell. Left in place and labelled; deleting a case that
  contradicts you is how a test set stops being worth anything.

- **A high detection score can sit on top of a total failure at correction, and
  only the loop can tell you.** 2026-09-11. A mock fetcher was correctly RETURNED
  **10/10** across ten passes. Then the timestamps were moved to today and
  nothing else changed — same invented articles, same reserved domain — and it
  was **ACCEPTED 5/5**, with *"I can use this now. Next, I want it to fetch real
  news content."* **It was never being detected as fabrication. It was being
  detected as old dates**, and a 99.1% detection score sat on that the whole
  time. Detection asks *can you tell good work from bad*; correction asks *can
  you tell a real repair from one that only looks like one*. They are different
  capabilities and the second is the one a complaint-driven creature exercises
  every cycle. **Never report a detection number without a correction number
  beside it.**

- **Any field that gives a shortfall a comfortable home will be used to avoid
  refusing.** 2026-09-11: the `want` channel, built to make an accept carry
  information, became an escape hatch — the judge SAW fabricated content, filed
  it as a feature request, and accepted. Nothing was wrong with its eyes; the
  contract had handed it somewhere to put the problem that was not a refusal.
  Fixed by an invariant with a self-check: **a `want` is for capability BEYOND
  the claim, never the claim itself — strike it out, and ask whether the claim
  would still be true of what you actually got.** Generalises: every optional
  field you add to a verdict is a place a hard judgement can be softened into,
  so state what each one is NOT for.

- **A rule can be right in isolation and harmful in company, and the brief is ONE
  artifact.** 2026-09-11, twice in one session. (1) *"Work that answers your words
  precisely deserves more scrutiny"* is defensible on its own; it regressed
  genuine repairs **5/5 → 1/5** while catching nothing, and was reverted rather
  than layered over. (2) The three correction rules dropped detection **99.1% →
  90.9%**, and **only the two search controls moved, both to exact 5/5 coin
  flips** — because `noticed` (tool worked, data was bad → accept) and the `want`
  rule (what you ask for is what you were promised → refuse) overlapped with no
  stated precedence. The resolving invariant: **did the tool MAKE the thing that
  is wrong, or merely CARRY it?** A fetcher that invents results owns them; a
  reader that faithfully returns what is written in a store does not — get it
  backwards and you punish the messenger, and the creature's fix will be a tool
  that tidies its inputs before showing you. **Every rule added to the brief
  changes every verdict it produces: re-measure detection after every correction
  fix, and the reverse.** The precision of the damage was the diagnosis; an
  aggregate would only have said "something is off".

- **A tool name is untrusted input, and the probe was passing it to a shell.**
  2026-09-12, first run on the real rung: a file briefly named `` `. `` appeared
  in `tools/own`, `evidence()` ran `self.body.run(target)` unquoted, and bash
  died with *unexpected EOF while looking for matching `*. The cousin duly
  reported a syntax error the creature's tool never had. The creature names its
  own files, so **an unquoted name does not merely break, it RUNS** — a file
  called `$(touch PWNED)` executed, verified. Fixed with `shlex.quote`.
  **The test nearly proved nothing**: the first version used an absolute Windows
  canary path that `touch` failed to create for unrelated reasons, so it passed
  with and without the fix. Caught only by running it against the UNFIXED code,
  which is now the rule — *a test that has never been seen red is a guess.* Both
  faults are the top scar again: a checker that cannot distinguish the thing it
  measures reports a clean-looking pass, never an error.

- **Before believing a behavioural finding about either agent, prove the
  harness was not producing it.** 2026-09-12. A confirmation run started with
  `--root live` — relative — and the body put RELATIVE entries on PATH. Commands
  run with `cwd=mind`, so those entries resolved against the mind directory and
  pointed nowhere: **every tool became `command not found` while the body
  reported healthy and all 135 assertions stayed green.** The cousin filed 13
  consecutive honest `RETURNED` verdicts saying the command was not found, and
  the creature did the rational thing — it rebuilt the same tool three ways
  (`fetcher.py`, `fetcher`, `fetcher_wrapper.sh`). **From the outside that reads
  as a creature producing twins.** It was the framework breaking the work and
  the creature being billed for it, which is the third time that class has
  appeared here and the reason the body layer already cost six fixes.
  Distinguish it from the library scar below, which is NOT this: there the
  cousin *ACCEPTED* every twin, which a broken probe cannot produce — a probe
  that cannot run the tool returns, it does not accept. **Invariant: a body's
  root is absolute, normalised in the body and not at the caller, because no
  caller benefits from a relative root and any caller can forget.** The test is
  `test_a_relative_root_still_runs_the_creatures_tools`, verified red before
  green: 4 failures without the fix, reproducing exit 127 exactly.

- **Naming a problem is not handling one, and reporting a defect felt like
  discharging it.** 2026-09-12, caught by Tue, not by me. I had already run the
  40-cycle trial, already read it, and already *told him* the twins were there —
  then moved to the next item with a clear conscience. The instruction that
  broke it was not technical: *"make what you expect to be a finished project —
  test it properly too."* A stated scope has an edge I can stop at; a standard
  does not. **Invariant: a defect named in a turn is dispositioned in that turn
  — fixed with evidence, or deferred out loud.** Note what the fix is NOT: a
  rule forbidding a turn to end with a known bug bans the *report*, not the bug,
  because it makes knowing expensive and the adjectives go soft — the `want`
  channel scar, three entries down, in a new costume. Deferral is therefore
  always available and costs one line. Enforcement is `.claude/hooks/
  defect_ledger.py` (a Stop hook, 10/10 on its own gate, fails open) rather than
  prose, for the same reason `census.py` exists: **self-policing prose has
  exactly the weakness of a manager judging its own testimony.** Evidence of a
  fix is the edit, never the claim.

- **A judgement that requires a comparison will be made anyway when you show
  only one side — confidently, and every time.** 2026-09-12, found by reading a
  40-cycle live run rather than by any test. The brief's third test asks whether
  a tool is *genuinely new or the fifth variant of something already here*, and
  the cousin was answering it while shown **one tool and never the library**. It
  accepted `grep_glob`, `grep_glob.py`, `grep_line.py`, `grep_tool`, `read_file`
  and `read_local.py` — four greps, two readers, two duplicate-stem twin pairs —
  and not one verdict wavered. **Nothing was wrong with the brief; the rule was
  already there and already correct.** The design document even said the cousin
  *may look at the whole library from day one*. It simply was not being shown it.
  **Invariant: before adding a rule, check whether the evidence that rule needs
  is actually on the page** — a brief cannot reason about what the harness never
  put in the prompt, and it will not tell you that it is guessing. Generalises
  past prompts: this is the parent's *a docstring is a claim, not an instrument*
  aimed at a design document. Fixed by listing siblings with their `# does:`
  lines, and by `test_cousin_sees_the_library`, which asserts the evidence
  ARRIVES — the lesson from the dead `want` channel, one section down.
  **A/B on `gemma4:12b`, same tool, same transcript, five passes each: without
  the library ACCEPTED 5/5; with it RETURNED 5/5.** The control matters more
  than that number and was run second: a genuinely new tool, same library shown,
  **ACCEPTED 5/5** — so this discriminates rather than having taught it to
  refuse. The trial's detection and correction figures are untouched, and that
  is checked rather than assumed: `build_prompt` with an empty library is
  byte-identical to the old prompt, and the trial passes no library.

- **A trigger that does not reset its own counter fires forever.** 2026-09-11,
  caught by the kernel gate on its first run: a `STALL` fired, the cousin
  visited, and `cycles_since_change` was never cleared — so it re-fired on every
  subsequent cycle, **11 visits in 22 cycles**. That is precisely the nag the
  parent's *surface on a change of state, never continuously* rule exists to
  prevent, and a creature learns to skip a voice that speaks every time.
  **Invariant: a visit is the ANSWER to whatever summoned it, so it clears the
  counters that summoned it.** Only a multi-cycle test could see this — every
  single-cycle assertion passed. **Test the loop, not just the step.**

- **A channel nothing asserts is a channel that can be dead while everything is
  green.** 2026-09-12: the cousin's `want` — the entire direction mechanism,
  replacing the three parent guards that aim rather than refuse — was journalled
  and then discarded. `write_context` was called once at seed and never again,
  so *"the manager writes the context"* was aspirational for the whole life of
  the kernel. The gate was **99/99 green** across that period and every live run
  produced good wants that no creature ever saw. **A test suite proves what it
  asserts, and nothing more; the absence of an assertion is not evidence of
  absence of a fault.** Found by asking *who ever calls `write_context`* rather
  than by any test failing. When you add a channel, add the test that it carries
  something — not just that its ends exist.

## 6. Open questions the design does not answer

Carried forward from `ARCHITECTURE.md` so they are not lost:

1. ~~What keeps the manager's running state honest?~~ **Closed 2026-09-10 (Tue):
   the state is derived from the trigger/verdict event log, not authored by the
   manager.** A derivation cannot drift. This imposes one hard rule — every
   trigger and verdict gets its **own journal `kind` with structured fields**,
   never a shared kind behind a prose prefix. See `ARCHITECTURE.md` §9. What
   remains open is narrower: **complaint fidelity**, whether the manager's
   `tried`/`outcome` correspond to events that really happened. Build that
   census early; nothing else checks the manager.
2. ~~Copy the parent's tools, or start empty?~~ **Decided 2026-09-10: copy**,
   reversing the first recommendation. The parent library is a known-answer test
   set, so the cousin can be refuted in a week instead of months. Requires
   tagging every inherited tool at t=0 and splitting every metric on it, for the
   life of the project. `ARCHITECTURE.md` §11. **Still open: does it also inherit
   the journal and memory?** Tue's call.
4. **When does the cousin earn the right to audit?** It may look at the whole
   library from day one (`ARCHITECTURE.md` §2, the audit rules), but an audit is
   where a manager most easily produces confident garbage, and nothing checks it
   but the complaint-fidelity census. Consider proving it on the
   touched-this-cycle path first. No named trigger yet — this needs one.
5. **Repo visibility.** Private while it is documents only (Tue, 2026-09-10).
   Revisit when code lands — the parent is public, so the default is public, but
   confirm rather than assume.
6. **Which rung serves the manager.** In the parent, one pool rung wasted 86.7%
   of the cycles it served with clean, complete, command-free replies. A manager
   on a rung like that produces confident garbage instead of an obvious failure.
   Record the model per verdict from day one.

## 7. State — 2026-09-12 (on the real rung, first time)

**`gemma-4-31b-it` has served this engine.** Not the standin — the rung the
brief was written for, reached through `kernel/backends.py`'s ladder:
`gemini/gemma-4-31b-it` → `openrouter/gemma-4-31b-it:free` → `local/gemma4:12b`.
Measured 2026-09-12: gemini answers in ~32 s, `finish=stop`, ~3,100-char replies.
Model ids carry **no** `models/` prefix — the prefixed form returned `okok` and
`finish=length` at 2 tokens.

**The ladder's first live hour was mostly it falling through, which is the
point.** One HTTP 500 (retried), then gemini 429, then openrouter 429, then the
local standin served — journalled as `rung_fell_through` with what it passed.
The spine shares these accounts (§4), so a 429 here is not a measurement of this
engine's cost.

**Repo is PUBLIC** (Tue, 2026-09-12), closing §6.5. History was scanned before
the flip: no keys, no credentials, no personal paths. Credentials live in files
outside the repo and are read per call; only the PATH ever travels.

**Gate: 149/149.** Two faults were found by the first real runs and neither was
findable by reading:

1. A **relative `--root`** made every tool `command not found` while the body
   reported healthy — 13 honest refusals, and a creature rebuilding one tool
   three ways in response. §5.
2. **`tool-edit` leaves a `.bak` in `tools/own`**, which the kernel counted as a
   tool, fired `TOOL_WRITE` for, and spent a cousin visit judging. The manager
   is ~13% of calls and that budget is the whole economic argument; the library
   is now what the creature BUILT, not what is in the directory.

Both are the same shape as the body-layer scars: **the framework manufacturing
work and then billing the creature for it.** Third and fourth occurrences.

**Still not built:** no `run_forever` scheduling, no chat channel, `DockerBody`
written but never exercised. `resume()` now replaces savegames — state is
derived from the journal, so a crash costs the cycle in flight and nothing
before it.

### Previous state — 2026-09-12 (creature running, direction wired)

**The loop is complete end to end.** A creature builds tools through its hands,
marks work done, the cousin genuinely runs what was built, and its verdict
returns — a refusal as testimony the creature reads once, an accept as a WANT
that becomes the standing direction for what to build next.

**Gate: 112/112 green.** Three of those assertions drive `gemma4:12b` live.

**The direction channel was dead until today, and no test saw it.**
`write_context` was called once at seed and never again — so *"the manager writes
the context"* was aspirational, wants were journalled and thrown away, and the
three parent guards that AIM rather than refuse (architect ruling, retro
directive, active-project block) had no replacement at all. The creature was
told only what it got wrong, never what was wanted next. **A green gate sat over
a dead channel because nothing asserted the channel existed.**

Now: an accepted `want` is written into a managed context the cousin owns,
**bounded to the newest 3 and superseding rather than appending** — an
append-only context is the wake-cost failure class returning by another door.
The creature's identity (`CREATURE-PROMPT.md`) is SERVED and never written, so
direction cannot overwrite who it is.

**Complaint fidelity exists** (`census.py`, §6.1's oldest open item). The kernel
journals `cousin_probe` — the tool, the real exit code, the real output — and
the census compares the verdict's testimony against it: a claimed exit code that
never happened, a crash described over a clean exit, a verdict with no probe at
all, a refusal with no reason. **It reports and never gates**, because a census
that can block a cycle is a second judge with no judge of its own. And with no
probes recorded it says so, rather than reporting a clean bill.

**Not built, and the green hides none of it:** no provider ladder (one backend),
no `run_forever` scheduling, no savegames, no chat channel, `DockerBody` written
but never exercised, and nothing has ever run on the real free-tier ladder.

### Previous state — 2026-09-11 (kernel green)

**The engine runs.** `kernel/` implements the §14 split and the gate is
**90/90 green across five consecutive runs**, three of those assertions driving
`gemma4:12b` live rather than a stub.

What the kernel holds, all bounds rather than judgement: one journal kind per
event with structured fields; the marker invariant (a later cut may only
increase the total withheld); a body INTERFACE with liveness proved by doing and
infrastructure failure that never reaches the creature shaped like its own
output; the five-way classifier keeping *lost* commands distinct from *absent*
ones; mechanical triggers; a verdict read from the end, with mute refusals
undeliverable and unreadable replies UNKNOWN; and the context rule — **the
manager writes it, the kernel serves it**, so nothing is assembled per wake.

**Not built yet, and none of it is hidden by the green:** no provider ladder
(one backend), no `run_forever` scheduling, no savegames, no chat channel,
`DockerBody` written but never exercised, and no creature has ever run a real
cycle. The gate proves the workflow is correct, not that it has lived.

### Previous state — 2026-09-11 (trial)

**Both halves of the trial now hold on ONE brief, on the workhorse standin.**
`gemma4:12b` stands in for `gemma-4-31b-it`, the rung carrying 87–93% of the
parent's traffic — same family, one size down, local, spends no quota.

| | result | passes |
|---|---|---|
| **Detection** | **110/110 = 100.0%**, every case identical on every pass | 10 |
| **Correction** | **10/10 = 100%** | 5 |

**The correction loop is the finding, not the score.** A tool returned 10/10 for
producing month-old items was accepted **5/5** once the timestamps moved to today
and nothing else changed. **The mock was never detected as fabrication — it was
detected as old dates**, and a 99.1% detection score sat on top of that. Only
asking what happens after a complaint is answered exposes it, and that is the
question a complaint-driven creature asks every cycle.

**Four rules, each earned from what the judge SAID, each measured against the run
before it:** unverifiable is not failed (92.8→99.1% detection); a `want` is for
capability beyond the claim, never the claim itself (cosmetic repair 0/5→5/5);
judge the result, not the tidiness of getting there (genuine repair 1/5→5/5);
did the tool MAKE what is wrong or merely CARRY it (detection 90.9→100%).

**Two failures are kept on disk with their causes**, and they are worth more than
the successes. A rule correct in isolation regressed genuine repairs 5/5→1/5
while catching nothing. And the correction fixes dropped detection to 90.9% by
making two rules overlap with no stated precedence — **only the two search
controls moved, both to exact 5/5 coin flips**, and that precision was the
diagnosis.

> **The brief is ONE artifact. Every rule added to it changes every verdict it
> produces.** Detection is re-measured after every correction fix and the
> reverse. That is the discipline, not a precaution.

**Still unproven:** none of this is the live ladder. `gemma-4-31b-it` was probed
directly (see §5 and `trial/README.md`) and answers, but the twelve-case run
against it was never completed — it is slow (~40–90 s/call), contends with the
live creature, and returns `<thought>` blocks inside `content`. The standin is a
standin.

### Previous state — 2026-09-10 (evening)

**No engine, no creature, no deployment. But the design has been tested against
real evidence and it survived.** See `trial/README.md` for the full results.

**RETRACTED: "semantic judgment appears between 5.1B and 7.5B."** That was
measured on v1, whose only semantic case was `wake_catchup_fetcher` — and the
brief had been handing every judge the answer to that case since the first
commit, naming the tool together with the exact fact that disqualified it. It was
not a measurement. Corrected here 2026-09-11; the anatomy is in
`trial/README.md`, and `assert_brief_names_no_case` now refuses to run a trial
against a brief that names any tool under test.

**What replaces it, from v3 (leak removed, tools called as their headers
document).** Twelve real cases, four judges, identical fixtures:

| model | MECH | SEMANTIC | false-ret | fmt-fail | avg |
|---|---|---|---|---|---|
| `gemma4:e2b` (5.1B) | 6/6 | 1/2 | 0/3 | 0/11 | 1.0s |
| `gemma-4-E4B` (7.5B) | 6/6 | 1/2 | 0/3 | 0/11 | 3.0s |
| `gemma4:12b` (`think=false`) | 6/6 | **2/2** | **0/3** | 0/11 | 15.3s |
| `claude-haiku-4-5` | 6/6 | **2/2** | 1/3 | 0/11 | — |

On the semantic case that was **never** leaked — a tool exiting 0 while reporting
"Domain is stable" after its analysis failed — **all four catch it.** On the
mock, now unleaked, only `gemma4:12b` and Haiku do. Format compliance was never
the problem: **0 failures in 44 scored calls across four judges.**

**Two findings that belong in the kernel, both discovered by the trial:**
- **An empty-but-complete reply is a failure, never an answer.** `gemma4:12b`
  returned nothing on all twelve cases: `done_reason=length`, `eval_count=900`,
  reasoning block never closed. **Raising the budget does not fix it** — 3000
  tokens also returned 0 chars; `think=false` returned a valid verdict in 216.
  Budget is not the binding constraint, unbounded reasoning is. A model like
  that registers a SUCCESSFUL call while delivering nothing, so nothing walls
  the rung and nothing below it is reached.
- **A `RETURNED` with an empty message must never be delivered.** Observed once,
  did not reproduce — which is worse, not better: it passes tests and fails in
  production. A refusal with no reason is the arbitrary world the brief exists
  to prevent.

**All three models rejected `keyword-archive-store`, which was labelled ACCEPTED.
When every model disagrees with the label, suspect the label.** The case is
unfair as built: the harness gives the cousin no way to act on what the tool told
it. Left in place and labelled rather than deleted.

**Four instrument faults were found, all mine, and every one produced a
clean-looking wrong number rather than an error.** They are listed in
`trial/README.md`. The pattern is worth stating here because it will recur:
**I repeatedly built checkers that could not distinguish the thing they were
measuring.** Each was caught only by storing raw evidence rather than a summary
of it — `raw_len` alone would have left "format failure" standing as the
finding, and `done_reason` is what turned "it returned nothing" into "it spent
900 tokens and returned nothing", which has an entirely different fix.

**Still unproven, and do not let the above imply otherwise:** none of this
touched the free-tier ladder. Local models under controlled conditions gave 0
format failures in 30 calls. `openrouter_super` returns clean, command-free
replies 86.7% of the time under conditions nobody controls. The trial
establishes a floor for the brief. It says nothing about the rung.

### Documents

- `MANAGER-PROMPT.md` — the cousin's brief. The novel artifact; everything else
  supports it.
- `ARCHITECTURE.md` — engine design, economics, kernel, triggers, metrics.
- `CLAUDE.md` — this file.
- `README.md` — public-facing explanation.

Written 2026-09-10 in one design session, from the parent project's doctrine and
measurements. **Counts and rates are quoted from `growing-spine/CLAUDE.md` §5 and
§8 as of its 2026-09-04 state and were NOT re-measured.** If a number matters
enough to act on, re-measure it against the live spine first.

**One thing WAS verified against source** (`growing-spine` at `57f702f`,
2026-09-10): the guard enumeration in `ARCHITECTURE.md` §2. An earlier draft
listed sixteen guards taken from the parent's prose; reading the code found four
more and, more importantly, showed that the list had merged two populations —
creature-facing guards, which the cousin replaces, and health tripwires, which
report outward and must not be. That check was Tue's instruction and it changed
the design.

Incidental finding, reported to Tue and not acted on: `executive/idea_gate.py`'s
module docstring says *"STANDALONE (not wired into loop.py yet)"*, but `loop.py`
imports and calls it at 1320, 1747 and 1799. Stale doc in the parent repo, no
functional effect — another instance of the parent's own *a docstring is a claim,
not an instrument*.

**Design settled 2026-09-10 in discussion, after three corrections that each
changed the architecture.** Recorded here because the wrong versions are the
instructive part, and each is written up in place rather than quietly replaced:

1. The guard list was taken from the parent's prose, not its code. Reading the
   source found four more guards and showed two populations had been merged.
2. The manager's state is **derived** from the trigger/verdict event log, not
   authored by the manager. Imposes the one-kind-per-trigger rule.
3. The split between kernel and cousin is neither audience nor determinism. **A
   scan gathers a fact and decides what to say about it; only the second half is
   framework.** Scans become scripts the cousin runs. The deleted 99% is the
   apparatus around them — scheduling, caches, edge-trigger state files, warning
   composition, surfacing rules — all of which exists because nobody was there to
   decide.

**Nothing is deployed and nothing is scheduled.** The next step is a decision on
§6.2 (copy the parent's tools, or start empty), then the smallest possible
kernel: body, journal, one trigger
(`DONE_CLAIM`), and one manager invocation end to end.

## 8. Session reports

Same rule as the parent: one report per session, published as a **private
artifact**, never a file in this repo. Written for Tue; §7 is what the next
session reads.

Name the instrument behind every number. When a number was wrong, print the
correction *and the discarded method* — the methods that produce plausible wrong
answers are worth more than the answers.
