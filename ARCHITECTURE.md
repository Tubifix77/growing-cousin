# Growing Cousin — architecture

**Status: DEPLOYED.** A creature and its cousin run unattended under systemd on
the same laptop as the spine, free tier only. The loop closes in production:
the creature builds, the cousin runs what was built and judges it, and the
capability it asks for next reaches the creature and gets built.

> This header said *"No creature, nothing deployed"* until 2026-09-13 — three
> days after it stopped being true, and it was found by an outside review
> rather than by anyone here. `CLAUDE.md` §0 is the status of record; this file
> is the design. **The gate count is deliberately not quoted anywhere in prose**
> — run `python tests/test_kernel.py` for the number. A hard-coded count is a
> constant nobody chose, obeyed forever, which is the fault this project's own
> doctrine names first.

The design below was validated *before* deployment: `trial/` put this brief in
front of the parent's real library and scored **detection 110/110 and correction
10/10** on a stand-in for the workhorse model — **in-sample**, on twelve cases,
with the rules derived from those same cases. Dated 2026-09-10, results
2026-09-11. That is a floor for the brief and says nothing about the live
ladder; see `trial/README.md`.

A mutation of [Growing Spine](https://github.com/Tubifix77/growing-spine). Same
creature, same volume, same instruments — a different engine.

---

## 1. The claim

Growing Spine is a deterministic Python framework that guides, guards and binds
an LLM into expanding itself. It works: 43.6 thinks/hour at best, a library that
went 508 → 643 tools in 82 productive hours.

But read that project's scar list honestly and the faults are overwhelmingly
**the framework's**, not the creature's. And a striking number are one specific
disease: *a constant nobody chose, obeyed forever.*

- The creature's entire view of any command's output was 300 characters. `git
  log -S` traces that number to the v0.4 **skeleton commit**. Nobody decided it.
  It was the creature's whole world for the life of the project.
- `classify_error` ended in `return "hard"`, which raises and aborts the provider
  chain. An unenumerated error shape killed **651 cycles in one day** and dropped
  throughput from 82 thinks/hour to 6.
- A dependency scan ran 433 × 433 = **187,489 full-content regex scans per
  wake**, 28.3 seconds, getting worse every time the creature succeeded. It was
  found because a human could hear the laptop fan.
- A guard built to catch fabricated data hunted the literal string
  `"Mock News Item"`; the fixture said `"Test Article 1"`, so it reported
  healthy over two `example.com` articles.

Underneath all of it: **the framework is doing LLM work in Python, badly.** The
done-gate is a hand-written approximation of *"is this actually finished?"* The
novelty gate approximates *"is this a duplicate idea?"* The loop warning
approximates *"are you spinning?"* Each approximation cost a scar.

There is a second, sharper problem. Growing Spine's own doctrine, learned the
hard way, is: **state the invariant, never the mechanism** — because a mechanism
named is a mechanism routed around. Told not to use `jq -n`, the creature
rebuilt the identical fault with a heredoc 36 hours later.

**Python can only encode mechanisms.** The framework is structurally incapable of
expressing the thing the project has learned is correct.

So: remove ~99% of the framework. Take the *goal* each guard served and write it
into a brief for a second agent — the manager. Keep only the bounds that must
hold when both agents are wrong.

## 2. The inversion

Almost every guard in Growing Spine's framework is a **negative**: of the
seventeen enumerated below, **fourteen are refusals**. The framework can prevent
a bad tool; it has almost no vocabulary for promoting a good one. (The three that
*do* aim are named under the table — and they are the ones the cousin replaces
with *accept-with-a-want* rather than with complaints.)

### The enumeration, from the source

*Verified 2026-09-10 against `growing-spine` at `57f702f`, by listing
guard-shaped functions across `executive/`, `volume/` and `scripts/` and reading
each. An earlier draft of this document listed "sixteen guards" derived from the
parent's prose. That was wrong in two ways — it undercounted, and it merged two
populations that must not be merged.*

**Population A — creature-facing. These are what the cousin replaces.**

| Guard (source) | The goal it serves |
|---|---|
| `_enforce_done_gate` → false completion (a non-zero exit this cycle) | A claim of completion must be true |
| `_enforce_done_gate` → `_hollow_tools_touched` | A tool must do something |
| `_enforce_done_gate` → `_unstartable_tools_touched` | A tool must be able to start |
| `_enforce_done_gate` → gate-choice target unchanged | An edit must change behaviour |
| `_build_loop_warning` | Don't repeat a command that can't tell you anything new |
| `_build_data_warning` | Stored data must be real and readable |
| `_build_broken_tool_warning` | Everything in the library must start |
| **`_build_stuck_tool_warning`** | Work you started must actually finish, or you must see that it didn't |
| `_finish_stub_spec` (stub organ) | Something demanded and missing should get built |
| `_gate_choice_spec` | Extend what exists before building beside it |
| `idea_gate` (DUPLICATE / EXTEND / NEW) | Don't build what already exists |
| `embed_gate` (semantic layer beneath it) | …including paraphrases lexical matching cannot see |
| **`architect`** (KEEP / DROP / RESHAPE per refill) | Direction: what is worth building next |
| `_build_knowledge_block` | It must know how its tools connect |
| **`_build_active_project_block`** | It must know what it is in the middle of |
| **`_build_retro_directive_block`** | Last cycle's lesson must reach this cycle |
| `_build_done_block` | A refusal must say what it was |

Four of those (**bold**) the earlier draft missed entirely. `_build_stuck_tool_warning`
is a real guard with a real scar behind it — 49 orphan processes, 16 hours, a
thermally throttled laptop. The last three are not guards at all in the
prohibitive sense: they are **continuity and direction**, which matters, because
they are the parts of the framework the cousin's *accept-with-a-want* replaces
rather than its complaints.

**Population B — health tripwires. These report to Tue and the maintainer, and
they are NOT replaced.**

`check_sensor` · `check_fallbacks` · `stub_janitor` · `check_unmet_demand` ·
`check_wake_cost` · `check_throughput` · `check_tool_wiring` · `check_jsonl` ·
`check_flatline` — all in `scripts/spine_health.py`, all appending to
`~/spine-health.log`, none of them entering the creature's context.

**Merging A and B would be a serious design error.** Population B is the outside
instrument. In this engine it is also what judges the *manager* — and an engine
whose only checker is the agent being checked has no checker.

### Which of Population B the cousin makes redundant

Three, and only three, because a cousin that genuinely tries to *use* the work
hits them naturally in the course of using it: `check_sensor` (a cousin reading
three `example.com` articles needs no phrase list), `check_jsonl` (a cousin that
cannot read the store *is* the parse-rate check), and `check_tool_wiring` (a
cousin looking for data where it was told it lives finds the split).

Keep them anyway through the first months. They are cheap, and they are the
cross-check that catches a cousin reporting a clean handover over a broken one.
The other six have no cousin equivalent: nothing about a handover reveals a
stalled loop, a wake-cost regression, or a dark provider rung.

### The dividing line is not audience — and it is not determinism either

*Revised 2026-09-10, twice, in discussion with Tue. Both earlier versions are
recorded because the second wrong answer is the more instructive one.*

**First attempt:** split by audience — creature-facing guards go to the cousin,
outward-facing tripwires stay. Wrong: it puts a free, deterministic, already-
working startability scan in front of an LLM, which buys nothing and costs calls.

**Second attempt:** split by cost — *deterministic and cheap stays in code,
judgment goes to the cousin*. Also wrong, and wrong in the way that matters: the
free Python scans **are** the framework. Keep them all and you have deleted the
judgment layer and kept the machinery — about 20%, not 99%.

**The resolution: a scan does two separable things.**

1. **Gather the fact** — walk `tools/own/`, parse 643 files, report which do not
   start.
2. **Decide to look, decide it matters, decide what to say about it.**

Only the second is framework. The first is *reading the filesystem*, which every
agent does; enumerating this document's own guard list was a `grep`, and that did
not make `grep` a framework.

**So the scans do not stay as framework code. They become small scripts the
cousin runs when it wants to know.** Determinism stays. The framework does not.

And that is where the 99% actually is. Around a ~30-line startability scan, the
parent carries: per-cycle scheduling; a `(mtime, size, st_mode)` parse cache —
which itself had a bug, because `chmod +x` changes neither mtime nor size; an
edge-trigger state file remembering what was last said; set-comparison logic;
warning-composition code turning facts into a string; and rules about when to
speak at all. **Every one of those exists because nobody was there to decide.**
With someone there, it is a script and a judgment.

This also kills the wake-cost failure class outright. Nothing runs per wake, so
nothing can silently grow quadratic in the library's size — which is what
187,489 regex scans per cycle were.

### The audit rules

The cousin **may** look at the whole library. An earlier draft of this document
said it never audits; that was a blanket rule with no justification behind it,
and the parent framework audits constantly. Three real constraints replace it,
and the first two are the parent's own doctrine:

1. **Edge-triggered, never continuous.** *A fact repeated every cycle is a nag it
   learns to skip, or a trap it cannot exit when it looks and finds nothing it
   can fix.*
2. **Library-wide visibility is fine; library-wide blocking is a trap.** A cousin
   may look at anything. It may never withhold a done-mark over something the
   creature did not touch — *a tool it wrote sixty seconds ago is always still
   fixable*, and a library-wide block is not.
3. **Pull works for the cousin and not for the creature.** The creature *cannot
   request a check for a problem it does not know it has*, so a pull-only scan is
   worthless to it. Going to look is the cousin's natural mode. Facts still reach
   the creature unprompted — as testimony from someone who went and looked,
   rather than as a string composed by a formatter.

What a cousin audit is actually for is the judgments no scan can make: are these
twins redundant or did they diverge into different jobs; does this tool's
description match what it does; this store parses fine, but is what is in it
*information*; fifteen tools cluster on one job — is that a capability or a
habit.

Population A's goals collapse into five:

1. A claim must be true.
2. A thing must actually run.
3. Don't rebuild what already exists.
4. Effort must be moving.
5. What's stored must be readable by what reads it.

Thousands of lines of Python encoding five sentences — every one an *invariant*,
which is the form the project's own doctrine demands and the form the medium
cannot hold.

## 3. But five constraints are not a purpose

All five are negative. They say what must not happen; none says what the creature
is *for*. The goal:

> **Every cycle should leave it more capable than it found it — a capability it
> did not have, or one it had, made genuinely better.**

Under that goal the five stop being free-standing prohibitions and become **tests
of a claim**, which is a better place for them: a test of a claim can be applied
by judgment; a prohibition can only be obeyed literally.

## 4. The cousin

The goal above still has a failure mode, and it is the one Growing Spine actually
suffered: *"expand your capability"* is exactly what the creature believed it was
doing when it wrote a routing wrapper whose own comment said **"we simulate the
routing"**, delegating to something that echoed the prompt back as an answer.
Exit 0, answer-shaped, no model anywhere.

So the goal is framed one turn outward:

> **Help your cousin expand.**

That single move smuggles in the entire handover contract without stating a
single prohibition — *it must work for someone who wasn't there, in a state they
can use and understand.*

Because every recurring fault in the parent project is a **single-occupancy
fault**: a defect that survives only because the author is the sole user. A mock
is fine if you know it's a mock. Error-text-as-return-value is fine if you wrote
it. 39 duplicate twins are fine if you remember which you meant. Unreadable JSONL
is fine until a reader that isn't the writer tries. None is a logic error; all
are the same error, and none is visible from inside.

The framework needed fifteen guards to *enumerate* the ways single-occupancy
fails. Installing a second inhabitant makes the whole class impossible to hide.

**And in this design the cousin is not hypothetical.** The manager genuinely
reads and genuinely fails to use things. A hypothetical cousin degrades under
pressure — the creature can always imagine one who happens to know the fetcher is
a mock. It cannot imagine that about a manager who opens the file and finds three
`example.com` articles.

### The asymmetry

Failure arrives as a **specific user's specific failure**: *"I ran it and got
three example.com articles."* That is a true report of a real event, which is
exactly the category the framework is permitted to give the creature. Nothing is
fabricated — contrast the mock, where something *pretends* to have happened.

Success is framed as a handover — but **the tool stays home.** The cousin does
not take it away. The creature bears the *cost* of handover quality and keeps the
*benefit*.

And the fiction is a lens onto a fact: the creature's recent state lives in a
five-slot register that overwrites each cycle. Ask it what made its work harder
and every item it names is months old. **It genuinely is a stranger to its own
work after a few days.** A tool it cannot hand to a cousin is a tool it cannot
hand to itself next month. The personification makes visible something true that
it cannot perceive directly.

### Why testimony beats doctrine

A doctrine-driven manager would inherit the parent project's only *recurring*
failure class — text obeyed to the letter. But the manager's output is not
doctrine. **You cannot obey a complaint to the letter.** Advice names a mechanism
and gets routed around; a complaint names an *outcome* — "I got nothing back" —
and the only way to satisfy an outcome is to actually fix it.

Full brief: [`MANAGER-PROMPT.md`](MANAGER-PROMPT.md).

## 5. The kernel — the 1% that stays code

Some prerogatives are **not judgments**. They are bounds that must hold when both
agents are wrong, and every scar in the parent project where a human had to
intervene was a missing bound. The fix is always a limiter, never a judgment.

| Stays in code | Why |
|---|---|
| Body lifecycle; PID 1 that reaps (`--init`) | An init that never calls `wait()` turned every orphan into a permanent zombie — 9,082 of them, until the PID namespace was full and the body could not fork for 3.5 hours |
| Liveness proved by *doing*, not by status | `docker inspect .State.Running` read `true` throughout that outage |
| `run_command` timeout, and a reaper for what it backgrounds | The timeout bound the exec, not its children; 49 orphans accumulated |
| Journal append + schema | Ground truth. Neither agent may edit it |
| Truncation caps, with the marker invariant | A marker reports **total** characters not shown; a later cut may only increase that number |
| Provider ladder mechanics + `classify_error` | An unrecognised error routes to the next rung, never walls the account, and announces itself once with its text |
| Test gate | Must literally contain `ALL TESTS PASS`, written to a file, never a pipe |
| Trigger detection | Mechanical, cheap, unarguable — see below |

That is the whole kernel: small and boring, which is the point. Note what is
**not** in it — no scans, no censuses, no warning composition, no catalogue
assembly, no context building.

### Three bounds the trial added, each found by running it

| bound | why |
|---|---|
| **An empty-but-complete reply is a failure, never an answer** | A reasoning model burned its entire allowance without closing its block and returned nothing, with `finish_reason=length`. Raising the budget does not fix it — measured at 900 and 3,000 tokens, both empty; disabling reasoning returned a full verdict in 216. Such a call registers as a SUCCESS, so nothing walls the rung and nothing below it is reached. **The manager is then silently absent rather than visibly broken.** |
| **A `RETURNED` carrying no message is never delivered** | Observed once and gone on the rerun, which is worse than consistent: it passes tests and fails in production. A refusal with no reason is the arbitrary world the brief exists to prevent. |
| **A judge that cannot be reached produces no verdicts** | A dead backend once wrote 31 rows that read exactly like the model failing everything. *An instrument that cannot run must say UNKNOWN, never FAULTY* — so the kernel proves the judge answers before recording anything. |

All three are limiters, not judgements. They belong in code precisely because
they must hold when the manager is wrong.

### Beside the kernel, not inside it: the cousin's instruments

A handful of small deterministic scripts — startability, hollow-stub detection,
duplicate-stem listing, dependency edges, store parse rates. These are **not
kernel**. Nothing schedules them, nothing caches them, nothing formats their
output into a warning. They are tools, they live where tools live, and the cousin
runs one when it wants to know something.

A library audit is therefore cheap: one script invocation, twenty-three names
back, then judgment. Not 643 LLM reads. An earlier draft of this document argued
audits had to be paced because of that imagined cost; that was a mistake about
how an agent looks at a filesystem.

## 6. Triggers — mechanical only

The manager fires on **events the kernel detects**, never on the creature's say-so
about its own state.

This matters more than it looks. If the creature declares its own milestone, the
false-completion problem reappears one level up — and the parent project measured
that: **139 false-completion blocks in one window.** It claims done constantly.

| Trigger | Fires when |
|---|---|
| `DONE_CLAIM` | The creature marks a phase or tool complete |
| `TOOL_WRITE` | A new file lands in `tools/own/` (creation, not edit) |
| `STALL` | N cycles with no new file and no done-claim |
| `HEARTBEAT` | Every N cycles regardless, so a quiet creature is still visited |

`DONE_CLAIM` is the primary and the one the design is built around. The others
exist so the creature is never *unvisited*, and so the manager can be the source
of direction when nothing is being claimed.

**Ordering rule — CHANGED IN THE CODE 2026-09-13, and this paragraph described
the old one until an outside review caught it.**

It used to read: *"the manager is asynchronous; a verdict lands on the next
wake. It is not a synchronous gate — blocking the creature on manager latency
would put the free-tier budget and the throughput in direct conflict."*

**The two agents now share one queue.** The visit happens inside the cycle, and
a cousin that cannot be reached defers the whole cycle rather than letting the
creature run on. Tue's reason, and it is the stronger one: *"how can the
creature think when there is no rung available? it is as dependent on the rung
as the mentor."* Silence from the second inhabitant is not approval, and a
creature that keeps building through it is building unjudged.

**The cost is real and is the price of the invariant**, not an oversight: with
a free-tier ladder and no local floor, a window in which every rung is at quota
now idles *both* agents. Measured the same day — long stretches where the
creature's thinks deferred one after another with nothing wrong anywhere. The
throughput premise in §7 was argued from the asynchronous property and no
longer holds; read those figures as a design point, never as this engine's
behaviour.

## 7. Economics — the binding constraint

Free tier only, permanently. That is a standing decision in the parent project
and it is not revisitable, so it shapes everything.

> **Everything in this section is a DESIGN ESTIMATE derived from the parent's
> counts, and the ~13% below is a floor, not a measurement of this engine.**
> Flagged by an outside review 2026-09-13, which found "~13%" quoted as though
> measured in three other places. It is now qualified at each of them.
> The measured figure lives in `vitals.py` (`cousin calls ÷ total calls`, split
> by rung); a figure with no denominator and no era is not a figure. Two things
> this estimate cannot see: calls that produced no usable verdict — 14 in one
> measured window — and the one-queue change in §6, which removed the
> asynchronous property the throughput half of this argument rested on.

From the parent's last full window (82 productive hours), per day:

| | per day |
|---|---|
| Coder thinks | ~1,047 |
| Done-marks | ~129 |
| Authoring actions | ~353 |

Manager cost by trigger policy, as a share of total LLM calls:

| Policy | Manager calls/day | Share |
|---|---|---|
| Per cycle ("50% manager") | ~1,047 | **50%** |
| `DONE_CLAIM` + every `TOOL_WRITE` | ~482 | **31%** |
| **`DONE_CLAIM` + `STALL`/`HEARTBEAT`** | **~150** | **~13%** |

The third is the design point. The first is the version discussed and rejected —
it halves coder throughput for supervision the triggers already provide.

**Corrected 2026-09-11 (§14):** this table treats the manager as pure addition,
and that overstates it. The parent already makes management LLM calls from
eleven sites — at least 5.6% of its call volume over a measured 24 hours. The
manager consolidates those into one briefed agent plus an increment; it does not
introduce the cost class.

Two cautions on that table:

- **Manager calls are fatter than coder calls.** It reads a diff plus context, so
  its share of *tokens* exceeds its share of *calls*. The percentages above are
  a floor, not a budget.
- **The rung that serves matters more than the count.** In the parent project
  one pool rung wasted **86.7%** of the cycles it served — clean, complete
  replies containing no command at all. A manager routed onto a rung like that
  produces confident garbage rather than an obvious failure. The manager must
  record which model served each verdict, and the census must split by it.

## 8. Compatibility — deliberately identical where it counts

Not black-box identical in *behaviour* — if the sibling behaves identically the
experiment has no signal. Behaviour is the dependent variable.

Identical in **measurement surface**, so comparison is real and the parent's
eight standing inspections work unmodified:

- Same volume layout: `/mind`, `tools/own/`, `tools/attic/`, `data/`.
- Same `journal.jsonl` schema, keyed on epoch `ts`. (Never date-grep it — the
  parent has a scar for exactly that: grepping a date string returns coincidental
  hits and reads like a quiet day.)
- Same health-log line formats, so FLATLINE / WAKE / UNMET / JANITOR parse.
- Same tool contract and `framework-tools/` hands.

New journal kinds this engine adds: `cousin_verdict`, `cousin_want`,
`trigger_fired`. All outside `MEANINGFUL_KINDS` — they reach the instruments and
never the creature.

## 9. The manager's state — derived, never authored

The manager has a context window and no memory between calls. An earlier draft
of this document treated that as the hardest open problem, and proposed a state
document the manager writes and rereads. **That was wrong, and the fix is Tue's
(2026-09-10): the state is already there. It is the trigger history.**

Every guard firing in the parent is an event with a time: the done-gate blocks,
the gate-choice verdicts, the stub organ's demands, the idea-gate's
DUPLICATE/EXTEND rulings. The *sequence* of those events over a week is a
complete description of what the creature is trying to do and where it keeps
failing — more honest than any summary, because nothing composed it.

So:

> **The manager is stateless between invocations. Its state is a query over an
> append-only event log the kernel writes and neither agent may edit.**

That removes the whole failure mode. A document the manager authors and only the
manager reads drifts into confident fiction with nothing to correct it. A
*derivation* cannot drift; at worst it is misread, and the next invocation
re-derives it from the same ground truth. It is also cheaper — no state file, no
write path, no reconciliation.

### The one design rule this imposes

The parent cannot do this cleanly, and the reason is a scar it already has.

**All five done-gate refusals journal under kind `"error"` with a prose prefix**
(`loop.py:2552, 2574, 2609, 2643, 2687`) — `"Done-gate blocked a false
completion: "` and so on. So reconstructing "what has this creature been blocked
on" means string-matching English inside a kind that also carries real errors.
The parent has a scar for exactly this shape: *a census keyed on `kind ==
"error"` cannot see a failure journalled as something else* — and its own
instrument read **0 provider errors** while two sat in the journal under a
different kind.

Therefore, in this engine:

> **Every trigger and every verdict is journalled under its own `kind`, with
> structured fields — never stuffed into a shared kind behind a prose prefix.**

`trigger_fired{type, target}` · `cousin_verdict{verdict, target, model, tried,
outcome}` · `cousin_want{text}`. A `Counter` over kinds must be able to answer
"what has been happening" without reading a single sentence of English.

That rule is what makes §9 work at all. It is small, and it is load-bearing.

### Complaint fidelity — built 2026-09-12, in `census.py`

Not the state — that is now derived. What remained was **complaint fidelity**:
the manager's `tried` and `outcome` are its own testimony, and nothing but a
census checks whether the thing it says happened actually happened.

`census.py` pairs each `cousin_verdict` with the `cousin_probe` immediately
preceding it and grades the correspondence by severity. It is possible only
because of the one-kind-per-event rule above — a census over prose prefixes is
the parent's scar *a census keyed on `kind ==` counted nothing*, repeated.

**It reports; it never gates.** Two reasons, and the second is the real one.
An instrument that can wall the thing it measures stops being an instrument. And
this census will be wrong sometimes — the highest-severity finding it emits
today, *a verdict with no recorded probe*, fires on honest verdicts where the
cousin reasoned from the header without running anything, which the brief
permits. A gate on that would punish exactly the behaviour *unverifiable is not
failed* was earned to protect.

### What is still unproven

**The cousin's right to audit** (§6.4 in `CLAUDE.md`). It is now shown the
library a tool joins — names with each sibling's own `# does:` line — because
without that its third test asks for a comparison with one side missing: over 40
live cycles the creature built four greps and two readers, two of them
duplicate-stem twins, and every one was accepted.

A/B on the standin, same tool and same transcript, five passes each:

| | verdict |
|---|---|
| a fourth grep, library **not** shown | ACCEPTED 5/5 |
| a fourth grep, library shown | **RETURNED 5/5** |
| a genuinely new tool, library shown | ACCEPTED 5/5 |

The third row is the one that matters: a judge taught to refuse would score
perfectly on the second row and be worthless. Detection and correction from §12
are unaffected — `build_prompt` with an empty library is byte-identical to the
prompt before this change, and the trial passes none.

**Still unproven:** that is one case on one rung over ten calls, not a long run.
An audit remains where a manager most easily produces confident garbage, and the
census is still the only thing checking.

## 10. The honest trade

This engine **sheds the solved failure class and inherits the recurring one.**

Growing Spine's ~33 diagnosed scars are mostly Python-framework faults —
`classify_error`'s default, truncation caps in series, the quadratic scan, guards
hunting literals. This engine does not have those failure modes; most of that
scar list arrives here as archaeology and must not be copied in as if earned.

But **8 of those 33 live in text the creature reads, and they are the only ones
that have ever recurred after being fixed.** A code fix ships with a test; a text
fix was verified by hoping. This engine is 100% text.

So the first thing to instrument is not throughput. It is: **does the manager's
guidance recur as a fault after being given?**

## 11. Does it start with a copy of the parent's tools?

**Direction: copy them.** Decided in discussion 2026-09-10, reversing this
document's first recommendation. One sub-question below is still open.

> **AND IT WAS NEVER DONE — recorded 2026-09-16.** Run 1 and run 2 both began
> from nothing: no journal, no context, no memory, no tools. So everything
> below is a plan that has not been executed, the refutation-in-a-week it
> argues for has never been attempted, and every reading of the cousin's
> judgement so far comes from a library with no known answers in it. Bound to
> run 3 — `PLAN.md` item 11, `CLAUDE.md` §6.2. Two documents disagreeing about
> what happened is the fault an outside review found here on 2026-09-13, so
> this note exists in both.

The two options answer different questions, and the first draft picked the wrong
one as primary:

- **Copy** answers *does the cousin work at all?*
- **Empty** answers *does the cousin produce better work?*

We do not yet know the first, and it is strictly prior.

**Why copy wins.** The parent library is a **known-answer test set**: 23 tools
that cannot start, 39 twins, ~50 returning error text as their value, a fetcher
serving three `example.com` articles. If the cousin runs against that and does
not notice — accepts a handover of a tool that will not start, never trips on the
mock — **the design is refuted in a week, cheaply.** That is the most valuable
thing available right now and an empty library does not sell it.

The "inherited debt" objection in the first draft was weak. The creature does not
know or care who wrote its library; it inherits it *as its own*. And repairing an
inherited broken library is exactly the capability-expansion the goal names. The
parent moved `cannot_start` 32 → 23 over months; a cousin taking it to zero in a
week would be a headline result, and it is only available under copy.

**A claim from the first draft that does not hold:** that the parent's early
journal makes cousin-week-1 against spine-week-1 an honest comparison.
Spine-week-1 was the v0.4 skeleton — the era that produced the 300-character
window nobody chose. That compares the cousin to a framework nobody would defend.

**What copy costs.** Attribution: every number now confounds inherited with
created, forever. Mitigation is to **tag all inherited tools at t=0** and split
every metric on it — discipline that has to hold for the life of the project, and
this lineage has a bad record there (a "67 unused tools" figure that was really
8; a "+151 in three days" from mixing two counters).

**Still open — does it also inherit the journal and memory?** The argument for
no: a fresh event log is what the derived state in §9 needs, and a creature that
wakes to 643 tools it has no memory of building **is** the handover situation,
structurally, on day one. Whether that is the sharpest possible start for this
engine or simply disorienting is not resolved. Tue's call.

## 12. What gets measured

Throughput is the wrong headline — different call economics, and this engine will
lose on it by construction. Library size is wrong too: the manager may correctly
cause *fewer, better* tools.

| Metric | Why |
|---|---|
| Tools that start, are invoked by something else, and are **still invoked a week later** | Surviving useful capability. The thing the goal actually names |
| `cannot_start` count, and the **flow** not the stock | The parent's most persistent unfixed class. A manager reading writes should kill it |
| Twins / near-duplicates | Test 3. No checker can do it; this is the manager's distinctive claim |
| `RETURNED` rate, and whether it falls | Is the creature learning handover, or just being refused repeatedly |
| **Complaint fidelity** — do `tried`/`outcome` correspond to real journal events | The manager's honesty. Nothing else checks it |
| Recurrence-after-guidance | The inherited failure class from §10 |

## 13. Deliberately not built

- **A committee of specialists** (architect / security / UI / …). Those roles are
  imported from human org charts, not from any fault measured here. The creature
  has no UI and no inbound network. The parent project's own finding: *every
  serious bug in its history was found by running it and reading behaviour, never
  by review.* If a specialist is ever wanted, make it **summonable** by the
  manager and count the summons — one never summoned gets deleted; one summoned
  constantly becomes code.
- ~~**A synchronous manager gate.**~~ **BUILT 2026-09-13, deliberately,
  reversing this entry.** Blocking coder cycles on manager latency does put
  throughput and budget in conflict — that reasoning was right and the cost
  arrived exactly as predicted. It was outweighed: silence from the second
  inhabitant is not approval, and the two agents share one queue so that an
  unreachable ladder stops *both*. See §6.
- **The manager writing or editing tools.** It is the second user, not a second
  builder. That coupling surface is what killed the "builder" proposal in the
  parent project.
- **Manager-visible full output while the creature sees a window.** It relocates
  the truncation problem rather than removing it, and makes the manager the
  creature's eyes — a dependency the design exists to avoid.

## 14. The engine workflow, mapped from source

*Read from `growing-spine/executive/loop.py` — `run_forever` (4085) and
`run_cycle` (3942) — on 2026-09-11. The guard enumeration in §2 says what the
framework FORBIDS. This says what it DOES, step by step, and which half each step
belongs to.*

### `run_cycle`, in order

| step | what it is | goes to |
|---|---|---|
| `journal.recent(n=20)` | gather | **kernel** |
| `chat.peek_unread` — peek, do not consume | gather + bound: a cycle that dies on quota must not eat the message | **kernel** |
| `_build_context(...)` | assembles the creature's entire world | **manager — see below** |
| `_record_wake_cost` | instrument | kernel (largely moot once nothing is assembled per cycle) |
| `keychain.complete(ctx, 3072)` | the think | **kernel** |
| `<reply>` extraction, re-queue, give up loudly after 3 | parse + bound | **kernel** |
| `served_by` with rung AND model | attribution invariant | **kernel** |
| `parse_bash_blocks` | parse | **kernel** |
| no blocks → truncation vs silence | classifier over `finish_reason` + fence parity | **kernel, and exemplary** |
| `ensure_body` before each exec | liveness proved by doing | **kernel** |
| `managed_exec` + timeout | bound | **kernel** |
| `exec_end` with caps and markers | bound + marker invariant | **kernel** |
| mid-abort bookkeeping still runs | bound (P1-F8 scar) | **kernel** |
| `_enforce_done_gate` | judgement | **manager** |
| `_classify_completion_category` | already an LLM call | **manager** |
| `_track_tool_usage` | gather | **kernel** |
| `_ensure_or_redirect` | judgement, already an LLM call | **manager** |
| `_stamp_gage` | bookkeeping | **kernel** |
| `_maybe_retrospective` | already an LLM judge, every `RETRO_INTERVAL`=20 cycles | **manager — and it is the heartbeat** |
| self-restart `prepare_and_arm` | a gate that must hold | **kernel** |

`run_forever` is kernel end to end: image pruning, `sandbox.start`, and an
exception ladder with four distinct waits (quota→120s and rebuild the keychain,
unavailable→60s, exec timeout→30s, DNS→60s). None of it decides anything.

### Finding 1 — the retrospective already IS the heartbeat trigger

`_maybe_retrospective` fires every 20 real cycles, builds a digest, and asks a
fresh stateless judge for PROGRESSING or STUCK — then clears the project and
applies a timed directive. That is a manager invocation on a mechanical interval,
already built, already costed, already an LLM call. **The cousin's `HEARTBEAT`
trigger is not new work; it is this, re-briefed.**

### Finding 2 — the parent ALREADY pays for management LLM calls, so §7 was wrong

There are **eleven LLM call sites** in the framework besides the main think:
completion classification, two redirect prompts, the idea-gate batch judge,
`assess_idea`, a novelty check, and the retro judge among them. Measured over 24
hours: **496 main thinks against at least 28 recorded management calls** —
≥5.6%, and that counts only the two kinds that journal under their own name.

So the manager is **not a new cost class**. It is a consolidation of management
calls the project already makes, scattered across eleven sites with no shared
brief, into one agent with one brief — plus an increment. §7's arithmetic treated
the manager as pure addition, which overstated its cost.

### Finding 3 — `_build_context` is the hard one, and the answer is edge-triggered

Building the wake context is the single largest thing the framework does, and
both obvious answers are wrong. Have the manager build it **per cycle** and you
are back to one manager call per wake — 50%, the version rejected on economics.
Leave it in code and you have kept the framework.

> **The manager WRITES the context; the kernel SERVES it.**

At a trigger the manager decides the recipe — what the active project is, which
warning still stands, what belongs in front of the creature. The kernel then
serves that same context every cycle until the next trigger changes it. Same
edge-triggered discipline as everything else here: *surface on a change of state,
never continuously.*

This also retires the wake-cost failure class outright. Nothing is assembled per
wake, so nothing can silently grow quadratic in the library's size — the context
is a file the manager last wrote, and reading it costs the same on day 400 as on
day 1.

### Finding 4 — one classifier to copy rather than replace

When the reply contains no bash block, the framework refuses to record *"proposed
no commands"* without first checking `finish_reason` and whether the fence count
is odd. It distinguishes **commands that were lost** from **commands that were
never offered** — 21 of 60 `exec_skip`s were the former, and every downstream
reader had been counting them as model quality.

That is *don't assert without checking* implemented in free, deterministic code,
and it is the exact shape of the cousin's own mute-refusal bound. Keep it as it
is. Not everything in the framework is a hand-written approximation of judgement;
this one is a measurement, and measurements stay.

## 15. Monitoring — the layer that reports outward

Added 2026-09-15, after a session in which the journal held the facts for
every fault and nobody derived a signal from them: fourteen unusable verdicts
read as weather for four hours, the same `SyntaxError` twelve times over nine
hours, a want channel discarding direction, a give-up that exited 0. The
instruments that existed — `observer.py`, `vitals.py`, `census.py` — were a
window for a desk, a time series, and a check on one agent. None of them said
*something changed, look here*, and none wrote anything a helper on the other
end of an ssh session could read without re-deriving it.

Spine's answer to the same problem is `scripts/spine_health.py` with hourly and
daily timers; this engine takes the **lessons** from it and none of the code
(§2.6 of `CLAUDE.md`): floors declared with the measurement behind them, never
learned; absence of evidence is not a zero; a stale number is never shown as
live; the exit code reserved for *a human is needed*; read the journal, never
`journalctl`; and **who receives this** — us, never either inhabitant.

Five layers, of which the kernel owns the first:

| layer | where | what |
|---|---|---|
| **RECORD** | `kernel/` | one kind per event with structured fields. Added 2026-09-15: `engine_start` (commit, dirty, caps, rungs — so every window can name its instrument), served facts on `wake` (`library_shown/named/total`, `wants_served`, `window`), `selfcheck` at every start (the sandbox and PATH tested by their EFFECT, recorded, never a veto), `loop_end.fault`, and `cousin_probe.picked_by` — WHY the cousin was sent to that tool, because the first evening's read found the unrecorded reason had been "alphabetically last" for two days |
| **DERIVE** | `monitor/derive.py` | counts and ratios of counts, split by rung; a ratio over few events is labelled an anecdote |
| **DETECT** | `monitor/detectors.py` | one detector per scar. Each returns OK / ALARM / CANNOT_TELL / INFO — never a boolean, because a detector that cannot see enough must say so rather than report OK. Floors are declared in the source with the measurement behind each |
| **PRESENT** | `monitor/status.py` | `live/monitor/status.md` + `.json` regenerated every five minutes; `alarms.jsonl` written only on a change of state; `regression/<sha>-<start>.md` written once per engine start, an hour in |
| **PROVE** | `tests/fixtures/journal/` | slices of the real journal where each scar happened. The gate asserts each detector fires there no later than the moment a human could have known — and no earlier — and stays quiet on a healthy hour |

Two rules make it an observation surface rather than part of the system under
test. **It writes only its own directory**, asserted by the gate on the code and
made impossible by the unit (`deploy/cousin-monitor.service`, read-only over
`live/` with `PrivateUsers=yes`). **Nothing it produces reaches either
inhabitant** — the creature is never told about its own bugs (§2.4), and a
repeated-failure alarm is precisely a bug we may have manufactured.

`python3 -m monitor pack` writes the per-run **evidence pack**: the journal,
the vitals series, the alarm log, the regression reports, the engine log and a
snapshot of the creature's tools, with a manifest that hashes every file and
counts every journal kind. The manifest is committed under `evidence/`; the
tarball is not, and the pack refuses to exist if anything key-shaped is inside.
That closes the gap an outside review named on 2026-09-13: a figure in
`CLAUDE.md` §7 can now be traced to bytes.
