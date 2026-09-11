# Growing Cousin — architecture

**Status: no engine — no container, no loop, no creature.** The design below is
validated: `trial/` put this brief in front of the parent's real library and
scored **detection 110/110 and correction 10/10** on a stand-in for the workhorse
model. Dated 2026-09-10, results 2026-09-11.

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

**Ordering rule:** one manager invocation at a time, and the creature's cycles
continue while it runs. The manager is asynchronous; a verdict lands on the
next wake. It is not a synchronous gate — blocking the creature on manager
latency would put the free-tier budget and the throughput in direct conflict.

## 7. Economics — the binding constraint

Free tier only, permanently. That is a standing decision in the parent project
and it is not revisitable, so it shapes everything.

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

### What is still unproven

Not the state — that is now derived. What remains is **complaint fidelity**: the
manager's `tried` and `outcome` are its own testimony, and nothing but a census
checks whether the thing it says happened actually happened. That census is the
only thing keeping the manager honest and it should be built early.

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
- **A synchronous manager gate.** Blocking coder cycles on manager latency puts
  throughput and budget in direct conflict.
- **The manager writing or editing tools.** It is the second user, not a second
  builder. That coupling surface is what killed the "builder" proposal in the
  parent project.
- **Manager-visible full output while the creature sees a window.** It relocates
  the truncation problem rather than removing it, and makes the manager the
  creature's eyes — a dependency the design exists to avoid.
