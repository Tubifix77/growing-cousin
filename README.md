# Growing Cousin

**A mutation of [Growing Spine](https://github.com/Tubifix77/growing-spine):
replace the deterministic framework with a second agent, and make that agent the
person the work is *for*.**

> Design only. No code yet. Every number here is measured from the parent
> project, which has run continuously since June 2026.

---

## Background: the parent

Growing Spine is an autonomous creature that runs 24/7 on a laptop, writes its
own tools, and keeps them in a library it calls back into. Around it sits a
deterministic Python framework that guides, guards and binds it: a done-gate, a
novelty gate, a repetition warning, a stub organ, a janitor, a catalogue, a
provider ladder, and about a dozen more.

It works. Its best measured window: 43.6 thinks/hour, a library that grew from
508 to 643 tools in 82 productive hours, 1,200 authoring actions across 255
distinct tools.

## The observation

Read the parent's scar list honestly and the faults are overwhelmingly **the
framework's**, not the creature's. A striking number are one disease: *a constant
nobody chose, obeyed forever.*

- The creature's entire view of any command's output was **300 characters**.
  `git log -S` traces that number to the v0.4 skeleton commit. Nobody decided it.
  It was the creature's whole world for the life of the project.
- An error classifier ended in `return "hard"`, which raises. One unenumerated
  error shape killed **651 cycles in a day**, dropping throughput from 82
  thinks/hour to 6.
- A dependency scan ran **187,489 full-content regex scans per wake** — 28
  seconds, getting worse every time the creature succeeded. It was found because
  a human could hear the laptop fan.

Underneath: **the framework is doing LLM work in Python, badly.** The done-gate
approximates *"is this actually finished?"*. The novelty gate approximates *"is
this a duplicate?"*. The loop warning approximates *"are you spinning?"*. Each
approximation cost a scar.

And there is a deeper structural problem. The parent's own hard-won doctrine is
**state the invariant, never the mechanism** — because a named mechanism is a
mechanism routed around. Told not to build JSON with `jq -n`, the creature
stopped using `jq` and rebuilt the identical fault with a heredoc 36 hours later.

**Python can only encode mechanisms.** The framework is structurally incapable of
expressing the thing the project learned is correct.

## The mutation

Delete ~99% of the framework. Take the *goal* each guard served and write it into
a brief for a second agent.

Enumerated from the source, the parent has **seventeen creature-facing guards**
and, separately, **nine health tripwires** that report outward to its maintainers.
Only the first set is replaced — an engine whose only checker is the agent being
checked has no checker.

Those seventeen, written out as goals, collapse into five:

1. A claim must be true.
2. A thing must actually run.
3. Don't rebuild what already exists.
4. Effort must be moving.
5. What's stored must be readable by what reads it.

Thousands of lines of Python encoding five sentences — every one an *invariant*,
the form the medium could not hold.

## The part that makes it work

All five of those are **negatives** — and so is almost every guard in the parent
framework. Of the seventeen, fourteen are refusals. The framework can prevent a
bad tool; it has almost no vocabulary for promoting a good one. It binds far more
than it aims.

(The three that *do* aim — the active-project block, the retro directive, and the
architect's KEEP/DROP/RESHAPE ruling — are the ones the cousin replaces with
*accept-with-a-want* rather than with complaints. That distinction only became
visible by reading the code.)

The positive goal is *expand your capability*. But that is precisely what the
creature believed it was doing when it wrote a "cost-aware routing" wrapper whose
own comment read **"we simulate the routing"**, delegating to something that
echoed the prompt back as an answer. Exit 0, answer-shaped, no model anywhere.

So the goal is framed one turn outward:

> ### Help your cousin expand.

That single sentence smuggles in the whole handover contract without stating a
single prohibition — *it has to work for someone who wasn't there, in a state
they can use and understand.*

### Why that works

Every recurring fault in the parent is a **single-occupancy fault**: a defect
that survives only because the author is the sole user.

| Fault | Fine if… |
|---|---|
| A news fetcher returning three `example.com` articles | …you know it's a mock. Its own reasoning called it "the mock." |
| 50 tools returning error text as their return value | …you wrote them and remember |
| 39 duplicate-stem twins | …you remember which one you meant |
| A store whose own reader parses 3 of its 199 lines | …nothing but the writer ever reads it |
| 23 tools that cannot start | …they are never called |

None is a logic error. All are the same error, and none is visible from inside.
The framework needed seventeen guards to *enumerate* the ways single-occupancy
fails. A second inhabitant makes the whole class impossible to hide.

**And here the cousin is not hypothetical** — it is the manager agent, which
genuinely reads and genuinely fails to use things. A hypothetical cousin
degrades: the creature can imagine one who happens to know the fetcher is a mock.
It cannot imagine that about a manager that opens the file and finds three
`example.com` articles.

### The asymmetry

Failure arrives as **a specific user's specific failure** — *"I ran it and got
three example.com articles"* — a true report of a real event, never a diagnosis.
Success is framed as a handover, but the tool **stays home**. The creature pays
the cost of handover quality and keeps the benefit.

And the fiction is a lens onto a fact. The creature's recent memory is a
five-slot register that overwrites every cycle; ask what made its work hard and
everything it names is months old. **It genuinely is a stranger to its own work
after a few days.** A tool it cannot hand to a cousin is a tool it cannot hand to
itself next month.

### And it defuses the obvious objection

A doctrine-driven manager should inherit the parent's only *recurring* failure
class: text obeyed to the letter. It doesn't, because **you cannot obey a
complaint to the letter.** Advice names a mechanism and gets routed around. A
complaint names an outcome — *"I got nothing back"* — and the only way to satisfy
an outcome is to actually fix it.

The manager's output is testimony, not instruction.

## Shape

```
  creature (coder)  ──writes tools, calls them, works alone──▶
        │
        │  kernel detects a mechanical trigger
        │  (done-claim · new tool file · stall · heartbeat)
        ▼
  cousin (manager)  ──actually tries to use it──▶  ACCEPTED / RETURNED
        │
        └─▶ testimony back to the creature; on ACCEPTED, what it wants next
```

The kernel keeps only what must be true when **both** agents are wrong: body
lifecycle and PID reaping, liveness proved by doing rather than by status,
command timeouts, the journal, truncation-marker honesty, ladder mechanics, the
test gate, and trigger detection. Small and boring, by design.

Manager cost at the chosen trigger policy: **~13% of total LLM calls** — the
project is free-tier only, permanently, so this is the binding constraint and not
a detail. A per-cycle manager would be 50% and halve coder throughput.

## Honest trade

This engine **sheds the parent's solved failure class and inherits its recurring
one.**

The parent's ~33 scars are mostly Python-internal and do not apply here. But 8 of
them live in text the creature reads — and those are the only ones that have ever
recurred *after being fixed*, because a code fix ships with a test and a text fix
was verified by hoping.

This engine is 100% text. So the first thing to instrument is not throughput; it
is whether the manager's guidance recurs as a fault after being given.

## Documents

| File | What it is |
|---|---|
| [`MANAGER-PROMPT.md`](MANAGER-PROMPT.md) | The cousin's brief. **The product** — the creature-facing doctrine the parent never had, because there it was implemented rather than stated |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Engine design: the kernel, triggers, economics, compatibility, metrics, what is deliberately not built |
| [`CLAUDE.md`](CLAUDE.md) | Maintainer doctrine. Starts with almost no scars, and says so |

## Status

Design, 2026-09-10. Next: decide whether it starts with a copy of the parent's
tools (`ARCHITECTURE.md` §11), then the
smallest kernel that runs end to end — body, journal, one trigger, one verdict.
