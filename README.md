# Growing Cousin

**A mutation of [Growing Spine](https://github.com/Tubifix77/growing-spine):
replace the deterministic framework with a second agent, and make that agent the
person the work is *for*.**

> **It runs.** A creature and its cousin live unattended on a laptop beside the
> spine, under systemd, on the free tier only. The loop closes in production:
> the creature builds, the cousin runs what was built and judges it, and what
> the cousin asks for next reaches the creature and gets built.
>
> **The spine RUNS** (corrected 2026-09-18; this paragraph claimed it was
> paused for five days after it came back up on 2026-09-15). The free tier is
> shared, which is the condition this comparison is designed for rather than
> an obstacle to it, and a detector now reads the unit every five minutes
> instead of this sentence being trusted.
>
> Numbers about the *parent* are quoted from Growing Spine. Numbers about the
> *cousin* were produced here. They are never mixed, and every rate is split by
> which model served it — an accept from one rung and an accept from another are
> different instruments.

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
        ├─▶ on ACCEPTED, a `want` — but ONLY for capability beyond the claim.
        │   It reaches the creature's next context and STANDS UNTIL THE NEXT
        │   ANSWERED VISIT discharges it: a visit is the answer to what
        │   summoned it. A channel nothing asserts is a channel that can be
        │   dead while everything is green — this one was, for a while.
        └─▶ `noticed` — anything in the way that this work did not cause.
            Gates nothing. Without it the judge blames the messenger.
```

### What the second inhabitant has, and what it took to give it

Making the cousin real turned out to mean more than running it. Three things
were missing for most of the project's life, and each was found by reading the
design rather than the logs:

- **Its own memory.** The creature's prompt describes a user that *wakes with
  no idea what changed while it slept* and *cannot plan across cycles* — and
  four of the five tool kinds it is told to build follow from that. The cousin
  had no continuity at all until 2026-09-18: its world was remade every visit
  and discarded. A judge with no yesterday cannot test a memory tool's only
  real claim, which is cross-session.
- **Not the builder's notes.** Its copy of the world included the creature's
  `state/memory.json` — the author's own record of what it had decided and
  verified — and one command prints all of it. **The judge was holding the
  answer key**, in the mechanism built to stop exactly that class of fault.
  Fixed 2026-09-18: the cousin receives the creature's *work* and never its
  *notes*. Every verdict taken before that date is caveated in `CLAUDE.md` §7.
- **Instruments of its own.** `ARCHITECTURE.md` §5 specified a handful of
  small scripts the cousin runs when it wants to know something —
  startability, hollow stubs, duplicate stems, dependency edges, store parse
  rates. They were specified on 2026-09-10 and written on 2026-09-18. Nothing
  schedules them. On their first run they found a shared store no reader can
  parse, and a hub tool named by 37 of 60 that no previous reading of that
  library had noticed.

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

Manager cost at the chosen trigger policy: **a design estimate of ~13% of total
LLM calls, derived from the parent's counts — a floor, never measured here** — the
project is free-tier only, permanently, so this is the binding constraint and not
a detail. A per-cycle manager would be 50% and halve coder throughput.

## The two projects, 1:1

Read from Growing Spine's source on 2026-09-13, not from its prose — the last
time this comparison was written from prose it was wrong twice over, and reading
the code changed the design.

**The headline: spine's cousin is fictional.** `executive/loop.py` briefs the
creature to build *"a toolkit for a near-conscious LLM 'cousin' (Linux
container, Python 3, persistent memory, shell tools, free-tier LLM APIs, no
human watching)"* — which is a description of the creature's own environment.
Nobody ever runs those tools. This project exists to make that second inhabitant
real. (Our own creature's prompt carried the same *free-tier LLM APIs* line,
false inside our box, until 2026-09-25 — see *No subagents* below.)

### The creature

| | Growing Spine | Growing Cousin | |
|---|---|---|---|
| What it is | LLM agent in a container building shell tools | identical | **same** |
| Hands (tools the framework puts on its PATH) | 14 in `framework-tools/`, among them `tool-new`, `tool-edit`, `remember`, `recall`, `web-fetch` and **`ask`** | 6: `tool-new`, `tool-edit`, `tool-replace` (edit part of a file), `remember`, `recall`, `say` — each announced every wake by its own header | different |
| **Can it call a language model?** | **yes** — `ask` sends one question to `gpt-oss-120b` on Groq (500 a day), and the provider keys sit in its environment | **no, and it is told so** — no key exists in either box (`selfcheck` proves it at every start) | **the difference, on purpose** (2026-09-25, below) |
| `tools/own` is its world, never edited by the framework | yes | yes | **same** |
| Think budget | 3,072 tokens | 8,192 (raised 2026-09-20, when whole-tool rewrites were being cut off) | different |
| Who it builds for | an **imagined** cousin described in prompt text | a **real** agent that runs what it builds | **the difference** |
| What it hears back | framework-computed warnings about itself | one user's testimony about what happened to *them* | different |
| Context per wake | ~16 blocks assembled fresh every cycle | a few parts — testimony, memory, library, hands, the cousin's standing wants, its own brief, and a transcript of what it just did — under a **56,000-character budget on the whole page** | different |
| Wake cost as the library grows | rises | bounded: the transcript is sized last, to whatever the page has left | different |

### Second LLM session

Spine has **no second inhabitant** but **eight-plus separate LLM roles**, each
verified at its call site: the creature's own `run_cycle`, `_maybe_retrospective`
(every 20 cycles), `run_architect`, the `idea_gate` batch judge,
`_refill_composition_queue`, `_oracle_composition_spec`, `_oracle_gap_spec`,
`_is_basin_relapse`, `_classify_category_cheap`, and chat.

| | Growing Spine | Growing Cousin | |
|---|---|---|---|
| Roles besides the creature | 8+ | 1 | different |
| Do any of them **run** the creature's tools? | **no** — they judge names, descriptions, registries, metric digests | **yes, and that is the only first-hand evidence in the design** — though the brief lets it say *"I could not try it, and here is what stopped me"* rather than invent one | **the difference** |
| Evidence judged on | second-hand: text about tools | first-hand: exit code and output | different |
| May write the creature's tools? | the architect rules, renames, retires | never — a second *user*, not a second builder | different |
| Direction mechanism | architect ruling + retro directive + active-project block | one `want`, superseding, discharged by the next answered visit | different |
| Who decides *when* they run | the framework | the framework | **same shape** |
| Who decides *what they say* | framework prompt templates | the cousin's brief | different |

### The framework

| | Growing Spine | Growing Cousin | |
|---|---|---|---|
| Size | `loop.py` ~4,100 lines plus `executive/` and `keychain/` | `kernel/`, ten small modules | different |
| Free tier only, same accounts, same laptop | yes | yes | **same** |
| Provider ladder | `keychain` + `quota_state` | `backends.ladder` + `kernel/quota.py` | **same shape** |
| 429 steps down, never retries | yes | yes | **same** |
| A truncated reply is not an answer | `provider.py` returns reasoning-only as an error and hops window | `unusable_reply` rejects it and the ladder falls through — **taken from spine** | **same** |
| State | derived from the event log | derived from the event log | **same** |
| Journal | one record per event | one *kind* per event, structured fields | **same principle** |
| Creature-facing guards | about twenty | **zero** | **the deleted 99%** |
| Who composes a warning | Python | the cousin, or nobody | different |
| Triggers | intervals and cycle counts | done-claim, tool-write, stall, heartbeat | different |
| Health tripwires reporting outward | flatline, tier check, health script | observer, vitals, **monitor** (a detector per scar, replayed on the real journal slice where it happened) | **same principle** |

**In one line:** spine encodes the judgement about the creature's work in Python
and imagines the user; cousin deletes the Python, states the judgement in prose,
and hires the user.

Nothing above carries a number that was not earned. The call sites, guard names,
cadence constants and the cousin description were read from source; spine's live
tool counts and rates were **not** re-measured and are not quoted here.

## No subagents, in either creature (decided 2026-09-24/25)

Both creatures were handed the same starter map, and one of its five kinds of
tool was *subagent orchestration — spawning helper LLM calls over the free-tier
APIs*. It is an idea the models bring with them anyway: coding assistants have
subagents, and agents and orchestrators are all over what they have read.

**Here it was a promise the box could not keep.** Our creature's prompt said its
cousin had *free-tier LLM API access*, while the deployment is built so that no
key ever enters either box. The creature did what it was told. It built
`subagent-orchestrator` and ran it **80 times** against a literal `"default_key"`
— every call failed to authenticate, and 8 exited 0 having done nothing. A
family of tools grew up around the logs of an orchestrator that never really
ran. Seventeenth time this project has recorded *the framework manufactures
work and the creature is billed for it* (`CLAUDE.md` §5).

**In the spine the calls are real, and so is the dependence.** Its framework gave
the creature `ask` on 2026-08-14. Read-only from here, and checked by the spine's
own session against its own instruments: about 398 of its ~750 tools depend on
one hub, `subagent_ask_helper`. So removing model access there would break most
of the library, and deleting the tools would be worse than useless.

Tue's perspective settled what to do with that: the subagent idea is off for a
free-tier project — a helper is not extra capacity, it spends the same small
shared allowance — and yet building around it may have produced good ideas,
such as breaking a task into steps or asking a fresh model for an outside
check. Nobody can sort those by reading the code. **Use can**: a tool that
keeps being used by someone other than its author was worth building. The
spine's session measured that it already is sorting them: 58 of those 398
tools used this week, 337 quiet, use of the family falling month on month
while plain `ask` rises.

So the fix is **stop the false promise, keep the work**:

| | Growing Spine (its own repo, its own session) | Growing Cousin |
|---|---|---|
| The prompt | stops presenting subagents as the model of good growth, retires the category and the build suggestions that route through it | three sentences replaced by true ones: *"It cannot call a language model: nothing in its box, or in yours, holds a key to one."* The category is gone, and the composition example no longer calls a subagent helper |
| Model access | keeps `ask`, described by what it is — one question to a fresh model, no memory of you, a daily token budget | **none** (Tue: *"no ask for cousin, that's the idea here"*) — no key, no relay, no account |
| Existing tools | kept; use decides | kept; they are the creature's world (`CLAUDE.md` §2.1) |

The wording states facts rather than forbidding a mechanism — *"ask is not an
agent"* names the thing to avoid, and a creature told what not to do obeys the
letter and rebuilds it another way (the spine's `jq -n` scar, above).

**The two creatures now differ by one granted capability, openly.** That is a
recorded condition of every comparison between them, run 3 included, rather
than a confound somebody has to discover — which is how it was found, on
2026-09-21, after being true for the life of both runs.

**And one waste closed in the same change.** Our creature's page (~14,000
tokens) can never fit Groq's 8,000 tokens-per-minute limit, so every think that
fell through to Groq came back *413, request too large* — about 400 a day, **0
answered since 09-21**, on an account the spine shares. The ladder now remembers
the smallest request each rung refused as too large and does not send it one
that big again. A 413 is a fact about the *request* — the same prompt gets the
same answer — so the ladder stays deterministic; a 429 (*not now*) still skips
nothing.

Deployed 2026-09-25 23:21 as `d833f7d`. What it changes is read a day later,
one signal per cause (`PLAN.md` step 4).

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
inhabitant last asked for. It never writes the engine's data. **It is also the
engine's on/off switch** (Tue, 2026-09-26: *"no rogue backend run"*): nothing
starts the engine at boot — its unit cannot be enabled — so it runs only after
someone presses **Start**. **Stop**, or **closing the window**, asks it to
finish the cycle it is in and then stop; a closed window stays open, saying so,
until the engine has stopped, and then closes itself. Closing it a second time
leaves at once, and the engine still stops after its cycle.

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

**The monitor is the window for someone who was not there.** `python3 -m monitor
status` derives a page from the journal — alarms first, each with the scar it
would have caught and its runbook line; then what it *cannot* tell; then counts
per window, every one naming the engine commit that produced it. A detector has
three states, never two, and each is proven by replay against a slice of the
real journal where its scar happened (`tests/fixtures/journal/`). Deployed as a
five-minute timer that may write only `live/monitor/`; `alarms.jsonl` gets a
line only when a state changes. `python3 -m monitor pack` writes a hashed
evidence pack per run so a quoted figure can be traced to bytes.

```bash
python3 -m monitor status --root ./live          # write live/monitor/*, print the page
python3 -m monitor replay tests/fixtures/journal/0913-fence-syntaxerror.jsonl
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
| [`CREATURE-PROMPT.md`](CREATURE-PROMPT.md) | What the creature is told every wake: its purpose, its user, the starter map. Changed on 2026-09-25 to stop promising model access |
| [`PLAN.md`](PLAN.md) | The board: every open item in order, with checkable acceptance criteria, and the next-steps table at its top |
| [`CLAUDE.md`](CLAUDE.md) | Maintainer doctrine and log: the handover, standing decisions, and every scar with the instrument that caught it |
| [`deploy/README.md`](deploy/README.md) | How it runs on the laptop: units, what may write where, the evidence pack |

## Does it work?

The design was put in front of the parent's real library before any engine was
built — no container, no loop, no journal. Just the brief, a model, twelve cases
of genuine evidence captured read-only from the live creature, and a score.

Judge: `gemma4:12b`, standing in for **`gemma-4-31b-it`**, the rung that carries
87–93% of the parent's traffic. Same family, one size down, runs locally, spends
none of the free-tier allowance.

> **These are IN-SAMPLE.** The four brief rules were derived from failures
> on these same twelve cases and re-scored on them; there is no held-out
> set, and the brief was measured on a local stand-in rather than on either
> rung that serves production. It is a floor for the brief, not a claim
> about the live ladder. Full caveats in `trial/README.md`.


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

**As of 2026-09-25 23:21 the laptop runs `d833f7d`.** What it carries that
earlier engines did not, newest first — each with its reason in `CLAUDE.md` §5
and its reading on `PLAN.md`'s board:

- **No model promised, none reachable, and no requests Groq can never take**
  (*No subagents*, above).
- **A partial-edit hand, `tool-replace`, and a served "Your hands" block** that
  names every hand from its own header. The creature's only editing idiom used
  to be rewriting a whole file, and its central tool had outgrown one reply.
- **A 56,000-character budget on the whole page**, with the transcript sized
  last. On 2026-09-24 a bigger transcript pushed the page past what the one
  rung that serves nine thinks in ten will accept, and the engine sat wedged for
  eight hours with no alarm. A detector (`context_outgrew_rung`) now watches the
  page against what rungs have actually accepted.
- **A refusal is not a crash** to systemd any more, so a deliberate STOP left
  over a reboot no longer spends the restart budget and locks the Start button.

What the day before this deploy measured: the creature stopped re-reading its
12 KB `plan` tool (74 reads a day to 2) but has not yet written it, and it
thought about half as often as before — which may be the page now sitting at
the budget on every wake. Both are read again after a day of `d833f7d`.

Design settled 2026-09-10; the brief was scored against real fixtures
2026-09-11 -- in-sample, on a local stand-in, which is a floor and not a
validation of the live ladder.

~~It starts with a copy of the parent's library — a known-answer test set, so
the design can be refuted in a week rather than a season.~~ **Decided
2026-09-10 and never executed; corrected here 2026-09-18.** Both runs began
from nothing: no journal, no context, no memory, no tools. So the
known-answer refutation path has never been taken, and every reading of the
cousin's judgement so far rests on a library with no known answers in it. It
is bound to run 3 (`PLAN.md` item 11) with the tagging requirement intact.

**Still unproven:** none of this is the live ladder. `gemma-4-31b-it` answers
when probed directly, but the full run against it is not finished — it is slow,
contends with the running creature, and wraps replies in `<thought>` blocks. The
standin is a standin.

**It is deployed and the loop closes in production.** `kernel/` is the 1% that
stays code, `tests/test_kernel.py` is the gate — **run it for the count; no
document here quotes one**, because four documents once quoted four different
numbers and a count in prose is a constant nobody chose. A creature and its
cousin run unattended under systemd on the same laptop as the
spine — same hardware, same network, same free-tier accounts, which is the only
configuration in which comparing the two projects means anything.

A measured example, 2026-09-13: the cousin asked for *"a way to link tasks in
the plan to specific entries in the archive"*; three cycles later the creature
read its archive tool, rewrote its plan tool to add the link, tested it, and the
cousin accepted and asked for the next thing — *"a way to suggest new tasks for
the plan based on information stored in the archive."* Wants that build on the
previous one rather than restating it are the signal worth having.

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

**What the deployment itself taught, and none of it was findable by reading.**
Nine times now the framework has manufactured work and the creature has been
billed for it: a relative root that hid every tool; a history that parsed as a
command; a tool name passed unquoted to a shell; a probe sent to a tool that did
not exist; a parser that executed a bare fence the creature's own contract said
was not a command — after which the creature read the manufactured failure in
its transcript and formed a false belief about its user; and two truncation caps
in series, where the one that had been carefully tuned was not the one that
acted, so a 4KB tool was shown to its author 1200 characters at a time while it
tried to extend it.

Every one of those looked, from outside, like a creature going in circles.

**Still missing, and both are now scheduled rather than merely absent
(`PLAN.md`, 2026-09-16):** the chat channel is **wanted** and is item 14 — it
lands last on purpose, because it adds a surface to the creature's context and
must not arrive while anything is being measured. ~~`DockerBody` is written
but never exercised — the deployed body is local, which is also why the
creature's shell still shares a uid with the engine's key files (item 7).~~
**Both were fixed on 2026-09-16 and this paragraph was stale for two days**
(corrected 2026-09-18): the creature runs in a container, its cousin runs in a
second one, and `selfcheck` re-proves at every start that the engine's keys
are unreadable from inside. What is still missing is in `PLAN.md`: the chat
channel (item 14), run 3 starting from the parent's library (item 11), and
item 20 -- the cousin is the second inhabitant this project exists to make
real, and until 2026-09-18 it had no memory of its own visits.
