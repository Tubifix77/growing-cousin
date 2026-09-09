# Growing Cousin — architecture

**Status: design only. No code exists yet.** Dated 2026-09-10.

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

Every guard in Growing Spine's framework is a **negative**. All fifteen are
refusals. The framework has no vocabulary for *yes*: it can prevent a bad tool,
it cannot promote a good one.

Write out what each one is actually *for*:

| Guard (live volume, 82h window) | The goal it serves |
|---|---|
| Done-gate, false-completion — **139 blocks** | A claim of completion must be true |
| Done-gate, startability | A tool must be able to start |
| Done-gate, unfilled scaffold + empty-placeholder (8) | A tool must do something |
| `upgrade-no-change` (40) | An edit must change behaviour |
| `idea_gate` (157 all-time) + `novelty_block` (52) | Don't build what already exists |
| Repetition / loop warning | Don't repeat a command that can't tell you anything new |
| Spin trap (1) | Effort must be going somewhere |
| Broken-tool warning | Everything in the library must start |
| Stub organ | Something demanded and missing should get built |
| JSONL sensor / WIRING | Stored data must be readable; writer and reader must agree on the path |
| SENSOR (mock detection) | Data must come from the world, not a fixture |
| Catalogue + rotation | It must know what it has |
| Knowledge block / dependency summary | It must know how its tools connect |
| Truncation markers | A cut must announce itself honestly |
| Janitor | Nothing is destroyed; dead things move aside |
| FLATLINE / throughput / wake cost | Silence and slowness must be noticed |

Those sixteen goals collapse into five:

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

That is the whole kernel: small and boring, which is the point.

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

## 9. The manager's state

The manager has a context window and no memory between calls. It needs running
project state: what is being built, what has been tried, what failed.

The risk is obvious — a document the manager writes and only the manager reads
will drift into confident fiction over a month, with nothing to correct it.

**The answer is that its state must be checkable against records it cannot
edit.** The journal is ground truth written by the kernel. The manager's `tried`
and `outcome` fields exist precisely so a later census can ask: did the thing you
complained about actually happen? That is the same trick that keeps the parent's
live-state section honest — measurement it does not author.

**This is the least-proven part of the design and should be built first, not
last.**

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

## 11. Open decision — the seed

The one thing not settled. Three options:

- **Full copy of the live spine.** Truest parallel: same starting point, so the
  difference is engine, not age. But it inherits 643 tools including 23 that
  cannot start, 39 twins, and ~50 returning error text as their value. The
  cousin's first thousand triggers would be complaints about inherited debt,
  and the engine never gets tested on its own output.
- **Empty.** Clean signal, but no shared baseline and a long cold start.
- **Recommended: volume layout and `framework-tools/` (its hands), with an empty
  `tools/own/`.** The comparison then isn't "who has more tools" — it is
  *surviving useful capability per unit of budget*, measured for each engine from
  its own zero. The parent's early history is in its journal, so cousin-week-1
  against spine-week-1 is an honest comparison and a better one.

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
