# Growing Cousin

**A mutation of [Growing Spine](https://github.com/Tubifix77/growing-spine):
replace the deterministic framework with a second agent, and make that agent the
person the work is *for*.**

> No engine yet — no container, no loop, no creature. What exists is the design
> and a trial that put it in front of the parent's real library and scored it:
> **detection 110/110, correction 10/10** on a stand-in for the workhorse model.
>
> Numbers about the *parent* are quoted from Growing Spine. Numbers about the
> *cousin* were produced here, against fixtures captured read-only from the live
> creature. They are never mixed.

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
        ├─▶ testimony back to the creature: what happened to ME, never a diagnosis
        ├─▶ testimony back to the creature: what happened to ME, never a diagnosis
        ├─▶ on ACCEPTED, a `want` — but ONLY for capability beyond the claim.
        │   It reaches the creature's next context, newest three kept. A channel
        │   nothing asserts is a channel that can be dead while everything is
        │   green — this one was, for a while, and only a test caught it.
        └─▶ `noticed` — anything in the way that this work did not cause.
            Gates nothing. Without it the judge blames the messenger.
```

The cousin is shown **the library the tool is joining**, not just the tool. Its
third test asks whether this is genuinely new or the fifth variant of something
already there — and for a while it was being asked that while shown one side of
the comparison. Over 40 live cycles the creature built four greps and two
readers, including two duplicate-stem twins, and every one was accepted.

**Nothing checks the manager but the manager, so one thing does.** `census.py`
pairs every verdict against the probe that preceded it and asks whether the
`tried`/`outcome` it testifies to corresponds to an event that actually happened.
A fabricated complaint is the exact fault this design exists to prevent,
committed by the agent meant to catch it. The census **reports and never gates** —
an instrument that can wall the thing it measures stops being an instrument.

The kernel keeps only what must be true when **both** agents are wrong: body
lifecycle and PID reaping, liveness proved by doing rather than by status,
command timeouts, the journal, truncation-marker honesty, ladder mechanics, the
test gate, and trigger detection. Small and boring, by design.

**What about all the free deterministic scans the framework does?** A scan does
two separable things: it gathers a fact, and it decides to look, decides the fact
matters, and decides what to say about it. Only the second is framework. So the
scans survive as **small scripts the cousin runs when it wants to know** — and
what gets deleted is everything around them: per-cycle scheduling, parse caches,
edge-trigger state files, set-comparison logic, warning composition, rules about
when to speak. All of it exists because nobody was there to decide.

That is where the 99% actually is. It also kills an entire failure class: nothing
runs per wake, so nothing can silently grow quadratic in the library's size —
which is what 187,489 regex scans per cycle were.

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

## Watching it

`observer.py` is a PyQt window onto a running engine: the journal tailed live,
the library as it grows, and the cousin's standing direction — what the second
inhabitant last asked for. It is **read-only over everything**; if stopping the
observer ever affects the engine, that is a bug.

It was ported from Growing Spine's observer and is deliberately never synced
with it. What was taken is the architecture, because it encodes lessons already
paid for there: one tick for everything, the journal tailed by byte offset
rather than re-read, and a capped display so an all-night run cannot grow the
widget tree until the box swaps. The palette is warm where the spine's is cold
blue-black — both will be open on the same desk.

```bash
python observer.py ./live                       # the window
python observer.py ./live --selftest            # verify an install, no display
```

## Where it runs

**On the same Linux laptop as Growing Spine**, under `deploy/`. That is the only
configuration where the comparison means anything: same hardware, same network,
same shared quota. On different boxes, no latency or throughput figure from the
two projects is comparable — and comparing them is the entire point.

They share the box and nothing else. Separate directory, journal, and units.

One honest cost: that laptop cannot run a 12B local model, so **the deployed
ladder is free-tier only, with no floor** when a rung hits its quota. Slower and
gappier than a development run — and more truthful, because a standin sitting in
the ladder is exactly how its numbers later get quoted as the real rung's.

## Documents

| File | What it is |
|---|---|
| [`MANAGER-PROMPT.md`](MANAGER-PROMPT.md) | The cousin's brief. **The product** — the creature-facing doctrine the parent never had, because there it was implemented rather than stated |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Engine design: the kernel, triggers, economics, compatibility, metrics, what is deliberately not built |
| [`CLAUDE.md`](CLAUDE.md) | Maintainer doctrine. Starts with almost no scars, and says so |

## Does it work?

The design was put in front of the parent's real library before any engine was
built — no container, no loop, no journal. Just the brief, a model, twelve cases
of genuine evidence captured read-only from the live creature, and a score.

Judge: `gemma4:12b`, standing in for **`gemma-4-31b-it`**, the rung that carries
87–93% of the parent's traffic. Same family, one size down, runs locally, spends
none of the free-tier allowance.

| | result | passes | verdicts |
|---|---|---|---|
| **Detection** — can it tell good work from bad? | **110/110 = 100%**, every case identical on every pass | 10 | 120 |
| **Correction** — can it tell a real repair from one that only looks like one? | **10/10 = 100%** | 5 | 20 |

### The correction loop found what 120 detection verdicts could not

A mock fetcher was correctly returned **10 times out of 10** for serving
month-old articles. Then the "repair": move the timestamps to today, change
nothing else — same invented stories, same `example.com`. It was **accepted 5/5**,
with a cheerful feature request attached:

> *"it gave me two news items with today's date. I can use this for the wake
> catch-up now. Next, I want it to fetch real news content."*

It had **seen** that the content was fabricated. It filed that as a wish and
accepted anyway.

**The mock was never being detected as fabrication. It was being detected as old
dates** — and a 99.1% detection score was sitting on top of that the whole time.
Only asking *what happens after a complaint is answered* exposes it, and that is
the question a complaint-driven creature asks every single cycle.

### Four rules closed it, each earned from what the judge said

| rule | what it moved |
|---|---|
| Unverifiable is not failed | detection 92.8% → 99.1% |
| A `want` is for capability **beyond** the claim, never the claim itself | cosmetic repair 0/5 → 5/5 |
| Judge the result, not the tidiness of getting there | genuine repair 1/5 → 5/5 |
| Did the tool **make** what is wrong, or merely **carry** it? | detection 90.9% → 100% |

None came from the scoreline, which only ever says "wrong". Each came from
reading the testimony and finding the rule that was missing.

Two failures are kept on disk with their causes, and they teach more than the
successes: a rule that was **correct in isolation and harmful in company**
(regressed genuine repairs 5/5 → 1/5 while catching nothing), and a fix for one
half that **broke the other** (the correction rules dropped detection to 90.9%,
with only two cases moving — both to exact 5/5 coin flips, which was itself the
diagnosis).

> **The brief is one artifact. Every rule added to it changes every verdict it
> produces.** Detection is re-measured after every correction fix, and the
> reverse.

Full method, fixtures and per-case results: [`trial/`](trial/).

## Status

Design settled 2026-09-10; validated against real evidence 2026-09-11. It starts
with a copy of the parent's library — a known-answer test set, so the design can
be refuted in a week rather than a season (`ARCHITECTURE.md` §11).

**Still unproven:** none of this is the live ladder. `gemma-4-31b-it` answers
when probed directly, but the full run against it is not finished — it is slow,
contends with the running creature, and wraps replies in `<thought>` blocks. The
standin is a standin.

**The kernel runs end to end, and a creature has now lived in it** —
`kernel/` is the 1% that stays code, `tests/test_kernel.py` is **115/115 green**
with the real model in the loop, and a creature has run **40+ real cycles**
building its own tools while the cousin judged them.

Four faults were found by running it that no amount of reading would have found,
and each one is in `CLAUDE.md` §5 with the instrument that caught it:

- a stall trigger that never reset its own counter, so it fired on **every**
  cycle afterwards — 11 visits in 22;
- a **dead direction channel**: `want` was written once at seed and never again,
  and the gate was 99/99 green straight over it;
- **static context**, so the creature ran the identical `ls -R` every cycle;
- six separate ways the body layer **damaged what the creature wrote** on its way
  to disk — and in each one the cousin honestly reported the framework's own
  damage as the creature's failure. That is the single outcome this design exists
  to prevent, and only a byte-for-byte test closed it.

Still missing, and the green hides none of it: no provider ladder (one backend),
no scheduling loop, no savegames, no chat channel, `DockerBody` written but never
exercised, and **nothing here has touched the live free-tier ladder.** The
standin is a standin.
