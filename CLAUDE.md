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

**No engine, no kernel, no creature, nothing deployed.** What exists is the three
design documents and `trial/` — a harness that puts the brief in front of a
known-answer library and scores it. That is code, and it has produced real
measurements, so this repository is no longer design-only.

**Two populations of number live here and must never be mixed.** Anything about
the parent's behaviour is quoted from Growing Spine and was not re-measured.
Anything in `trial/README.md` was produced here, locally, against fixtures
captured read-only from the parent's live library. **No number anywhere was
produced by a running cousin engine, because no such engine exists.**
When the first cousin verdict lands, that changes and this section is the first
thing to rewrite.

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
3. **When does the cousin earn the right to audit?** It may look at the whole
   library from day one (`ARCHITECTURE.md` §2, the audit rules), but an audit is
   where a manager most easily produces confident garbage, and nothing checks it
   but the complaint-fidelity census. Consider proving it on the
   touched-this-cycle path first. No named trigger yet — this needs one.
3. **Repo visibility.** Private while it is documents only (Tue, 2026-09-10).
   Revisit when code lands — the parent is public, so the default is public, but
   confirm rather than assume.
4. **Which rung serves the manager.** In the parent, one pool rung wasted 86.7%
   of the cycles it served with clean, complete, command-free replies. A manager
   on a rung like that produces confident garbage instead of an obvious failure.
   Record the model per verdict from day one.

## 7. State — 2026-09-10 (evening)

**No engine, no creature, no deployment. But the design has been tested against
real evidence and it survived.** See `trial/README.md` for the full results.

**Semantic judgment appears between 5.1B and 7.5B.** Three local models, twelve
real cases from the live parent library, identical fixtures. `gemma4:e2b` caught
6/6 mechanical and **0/1 semantic** — a free static scan with extra steps.
`gemma-4-E4B` (7.5B) and `gemma4:12b` both caught **1/1 semantic** with 1/3 false
returns. Format compliance was never the problem: **0 failures in 30 scored
calls**. The trial existed to settle whether a small-model manager can judge a
handover at all, and the answer is yes, above a threshold.

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
