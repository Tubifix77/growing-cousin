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

**DEPLOYED. A creature and its cousin run unattended on the laptop beside the
spine, under systemd.** `kernel/` is the 1% from `ARCHITECTURE.md` §14 —
journal, body, think, triggers, cousin, cycle, backends, forever — `run.py`
drives it, `observer.py` is the window, `census.py` is the only thing that
checks the manager, and `tests/test_kernel.py` is the gate.

**The gate count is deliberately not written down here.** It said 242 while the
gate was at 348, and three other documents each said something different —
found by an outside review 2026-09-13, not by anyone here. A count in prose is
a constant nobody chose, obeyed forever, which is the first fault this file's
own doctrine names. Run it for the number; `test_no_document_hard_codes_the_gate_count`
keeps it that way.

`kernel/` is **ten modules** plus `__init__.py`, and that list is asserted
against the directory rather than typed: see
`test_the_module_list_matches_the_kernel`.

### Handover — updated 2026-09-16, read this before touching anything

**The board is `PLAN.md`.** Every open item this project knows about, in the
order they are being done, one at a time, each with acceptance criteria that
can be checked rather than asserted, and each verified by a reader who did not
build it. Do not start work that is not on it; do not leave work off it.

**Tue's decisions, 2026-09-16**, so the next session does not reopen them:

- **The chat channel stays** — wanted, not abandoned, and **scheduled as item
  14**. It lands after everything else because it adds a surface to the
  creature's context, and a new surface arriving mid-measurement makes every
  number before and after it incomparable.
- **The evidence tarball stays on the laptop.** The repo carries the hashed
  manifest and nothing else.
- **The cousin gets its own shell** (item 9). That is the answer to *where
  does "running the test" end* — not a framework that composes invocations,
  which would move judgement back into the 99% this design deleted, and not
  the creature demonstrating its own work, which is the wrong side of §4.

**Is anything wrong right now?** `ls live/monitor/ALARM` — that file exists
only while something needs a human, and carries the standing alarms. **Is the
monitor alive?** the first line of `status.md` carries the time it was written.
**Is the monitor itself broken?** `systemctl --user --failed` — and that now
means only that, because the unit declares the alarm exit code a success
(`SuccessExitStatus=1`, 2026-09-15). Before that fix a standing alarm left
`cousin-monitor.service` in `failed`, which Tue read as *the monitor is not
running* — the correct reading of that signal, and not what it meant.

**Read `live/monitor/status.md` on the laptop before deriving anything by
hand.** A monitor exists as of 2026-09-15 (`monitor/`, `ARCHITECTURE.md` §15):
`cousin-monitor.timer` regenerates that page every five minutes — alarms first,
each with the scar it would have caught and a runbook line; then what it
**cannot** tell; then counts per window, every one naming the engine commit
that produced it. `live/monitor/alarms.jsonl` gets a line only when a finding
enters or leaves ALARM, so `tail` it to see what changed since you last looked.
Every detector was proven by replay on the real journal slice where its scar
happened (`tests/fixtures/journal/`). **Tue's standing instruction
(2026-09-15): no Claude-side monitor. Let it run; he asks for a check in the
morning.** The page says which commit is running and whether a restart is
owed; do not work it out from `git log` and systemd by hand again.

**The engine is running and does not need you.** If it gives up it exits
non-zero and systemd restarts it, bounded to 5 starts per 30 minutes; the page's
`gave_up` and `engine_silent` findings say so if that ever stops being true.

**BOTH inhabitants now have their own container** (2026-09-16). The creature's
is `growing-cousin-body`; the cousin's is `growing-cousin-body-user`, and it
holds a **copy** of the library, remade before every visit and discarded with
whatever it did to it — which is how §2.3 stopped being a promise and became
a fact. The cousin has no hands of ours: it is the second user, never a
second builder. It now chooses its own invocation instead of being sent to
run things bare (PLAN item 9), which costs two cousin calls per visit.

**The creature lives in a container as of 2026-09-16** (`--body docker`, PLAN
item 7). Its world is a bind mount of `live/body/mind` at `/mind`, our hands
read-only at `/hands`; `~/keys`, the host home, this repo and the sibling
project do not exist inside it. **Its library is on the HOST**, so removing or
rebuilding the container costs nothing it built — `docker rm growing-cousin-body`
is safe and the engine recreates it. `selfcheck` re-proves `keys_unreadable`
at every start.

**`rehearse.py` manufactures faults on a scratch root** — give-up, body death,
walled rung, torn journal, silence, a fabricated verdict, the container. It
refuses the live root, any git checkout and the sibling project, asks before
it destroys anything, and watches the live root's whole tree across every
drill. Use it before believing a path works; three real bugs came out of its
first run, and two of them were in the harness itself.

**The first day of the monitor, read 2026-09-15 18:55 (18 hours unattended):**
`commands_lost[gemini]` raised 00:50 (3/20) and cleared 03:25, never flapped —
the floor stands, nothing to tune. `served_context_contract` raised 07:00 when
the library crossed 40 — and the page's "Latest" showed the same want and the
same accept three times running, which led to the §5 scar of that date: the
probe chooser's alphabetical default and the listing's alphabetical cut had
manufactured six identical wants and five twins. Both fixed the same evening
(`Engine.choose_target`, names-only tail in `library.render`), two detectors
added (`want_repeated`, `probe_stuck`), engine restarted on the commit the
page names. **What to read next time:** `probe_stuck` should be OK with
`picked_by=least_probed` walking the library; `want_repeated` should clear
once the cousin's wants move on; `served_context_contract` should be INFO
("shown by name and purpose only"), never ALARM. If the same want persists
with the chooser fixed, the remaining cause is the **bare probe** — the cousin
cannot supply arguments — which is the design question in §6 (a shell for the
cousin), not a patch.

**Frozen, and the condition to unfreeze it.** `MANAGER-PROMPT.md` and
`CREATURE-PROMPT.md` are NOT to be edited. Three prompt changes shipped on
2026-09-14 (repair-not-delete, handover-completes, record display) and none has
a before/after yet. The brief's third test is known to be failing on judgement
(§5) — **that is the next real question, and it needs a measurement regime,
not a midnight patch.**

> **The instrument now exists (2026-09-16, PLAN item 8).**
> `trial/heldout-cases.json` — 16 cases the brief was never written against,
> labelled by evidence rather than opinion: 8 parent tools whose interpreter
> refuses them (established statically, because §2.6 forbids running one) and
> 8 of our own that the journal records running to exit 0 with output.
> `trial/score_brief.py` is the one runner, and it cannot print a detection
> figure alone — the correction half says NOT MEASURABLE, with the reason,
> until a real failure is followed by a real repair in the journal.
>
> **THE FIRST BASELINE EXISTS (2026-09-16 02:00), so the unfreeze condition
> is met.** `gemma-4-31b-it`, one rep, engine paused:
> **caught 7 of 8 broken; falsely returned 5 of 8 good**; 2 of 16 replies
> unreadable; correction NOT MEASURABLE and said so.
> `trial/baselines/baseline-frozen_gemma-4-31b-it.json`.
>
> **The discipline that replaces the freeze**: a brief change is scored by a
> DIRECTION across several reps, split by model, with detection and
> correction reported together — never by one number moving. And before
> touching a rule over that 5-of-8, read the five transcripts: the ACCEPTED
> label means *ran and produced output*, which is weaker than *did what its
> header claims*, so some of those refusals may be correct.

**Do not re-derive these; they are settled and each cost real time:**

| trap | the answer |
|---|---|
| "probe exit codes show the tools are broken" | the harness probes BARE; a usage refusal is the tool working. Read `bare` on `cousin_probe`. |
| "`subagent-orchestrator` is broken" | it compiles clean, `--help` exits 0. Its SyntaxErrors were the fence bug, since fixed. |
| "the creature is idle" | count `exec_start` and `exec_skip`; do not infer activity from probe or verdict counts. |
| "nothing is being produced" | count tool writes BOTH ways — `tool-edit NAME` **and** `cat > tools/own/NAME`. A tool-edit-only count undersells by half. |
| "the tier is broken" | a flat think count with `loop_waiting` climbing is weather. Never restart to clear it. The page's `ladder_dry` line says so, with times. |
| "is it healthy?" / "what happened overnight?" | `cat live/monitor/status.md`, then `tail live/monitor/alarms.jsonl`. Grepping the journal by hand is how the tool-write count was undersold by half. |
| "`plan` has 30 real failures" | 36 of `subagent-orchestrator`'s 43 probes and 30 of `plan`'s 31 predate the `bare` flag and are **unqualified**, not failures — and `plan` was probed 30 times because it was the **alphabetically last tool** and the chooser defaulted to it (§5, 2026-09-15). The library now says so to both inhabitants; it used to say FAILED. |
| "the cousin keeps asking for the same thing" / "the creature keeps building twins" | check `probe_stuck` and `want_repeated` on the page FIRST. On 2026-09-15 six identical wants and five twins were the chooser sending the cousin to `view-subtask-logs` bare, 28 of 30 visits. |

**Habits this session had to learn the hard way**, all cheap and all mine:

- **Re-arm a monitor in the same turn as the check**, before writing the
  report. Claiming a re-arm that never happened has occurred twice.
- **Never put a backtick in a shell string.** A monitor died on
  *unexpected EOF while looking for matching* — the same fault class being
  fixed in the creature's channel that hour.
- **Python with escapes never goes through a bash heredoc.** Write a file in
  the scratchpad and run it; `\b` became a literal backspace byte otherwise.
- **After changing a parser the creature speaks through, hunt for the cost in
  the next hour.** The regression watch earned its keep twice in one evening —
  and is now automatic: `deploy_regression` writes
  `live/monitor/regression/<sha>-<start>.md` an hour after every start.
- **Stop and start the engine in SEPARATE remote commands.** 2026-09-15 00:24:
  one ssh command did `touch STOP`, waited for the cycle, then `rm STOP &&
  start` — and the tool's timeout killed it between the wait and the start,
  leaving the engine stopped with a STOP file for ninety seconds. Nothing
  would have restarted it. Stop; confirm; start; confirm — four calls.

**Nothing in `live/` is committed** — but the per-run evidence pack now exists:
`python3 -m monitor pack --root live --out ~/growing-cousin-evidence --run run-2`
writes a tarball and a manifest that hashes every file and counts every journal
kind, and refuses to exist if anything key-shaped is inside. The **manifest**
is committed under `evidence/`. **The tarball stays on the laptop** (Tue,
2026-09-16) — in `~/growing-cousin-evidence/` and nowhere else;
`evidence/*.tar.gz` is gitignored so the repo cannot carry one even by
accident, because a pack holds raw model output and this repo is public.
`deploy/README.md` says the same where an operator will meet it. **The first
manifest is committed:
`evidence/run-2-20260915-0054.manifest.json`** — run 2 at 36 hours,
72 files, every one hashed, `python3 -m monitor verify` passing; the tarball is
`~/growing-cousin-evidence/run-2-20260915-0054.tar.gz` on the laptop. A figure
in §7 can now be traced to bytes by anyone holding that tarball.

**The gate's authority moved to the laptop (2026-09-12).** The Windows box
fails the liveness assertion intermittently under the suite's process churn —
`code=124 timed out after 15s` spawning bash, once a Windows `Katastrofal fejl
/ Bash/Service`. Linux runs the identical suite in 2.4s, clean, repeatedly. Run
it there before committing; the pattern that works without pushing first is a
scratch `git clone ~/growing-cousin /tmp/gate-check` with the changed files
uploaded over it.

**The design closes its loop in production, repeatedly.** Creature builds,
cousin uses and accepts, cousin asks for the next capability, the want reaches
the creature, it builds that.

**EVERY PRODUCTION FIGURE MUST NAME ITS RUN.** There are two, and they are not
comparable:

| run | when | status |
|---|---|---|
| **run 1** | to 2026-09-13 12:44 | **ARCHIVED AS CONTAMINATED** — `archive-contaminated-20260913-1244`. The two agents did not share a queue, so 39 of 98 visits never happened and ~40% of the cousin's judgements were discarded silently. Nothing in it is quotable as trajectory. |
| **run 2** | from 2026-09-13 12:48 | current. Started from nothing: no journal, no context, no memory, no tools. |

The figures that stood here until 2026-09-13 — *"6 accepts, 4 wants, 33
verdicts, measured 2026-09-12/13"* — are **run 1**, i.e. the run this project
declared unusable. They were quoted for a day without saying so, against this
file's own rule: *say which era a figure comes from or do not quote it.* Found
by an outside review, not here.

**Run 2, and each figure names the engine that produced it.** The engine was
changed roughly ten times during it, so even within run 2 a rate spans
instruments:

- The loop closes: cousin asked for *"a way to link tasks in the plan to
  specific entries in the archive"* (19:05 CEST, `gemini/gemma-4-31b-it`); the
  creature read its archive tool, rewrote `plan` to add the link, tested it,
  and the cousin accepted and asked for the next capability. Engine `8715e42`.
- Wants **progress rather than repeat** — the second built on the first. That
  is the signal worth having; in run 1 the wants had begun restating themselves.
- **Cousin verdicts are scarce and the ladder is the reason.** In one measured
  window (15:40–18:00, engine `41deceb`) `gemini/gemma-4-31b-it` served the
  cousin 14 times and produced **0** usable verdicts — every one truncated
  before the terminal block — while `groq/gpt-oss-120b` went **2 for 2**.

**No production journal or vitals output is committed** (`live/` is gitignored),
so none of the above can be checked by anyone who was not there. That is a real
gap in the evidence chain, named here rather than papered over.

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
correct; it says nothing about whether a creature can live in it. **Numbers from
a creature on the real ladder now exist (§7) and are a FOURTH population** —
6 accepts across `gemini/gemma-4-31b-it` and `groq/gpt-oss-120b`, and the brief
was measured on neither of those exact deployments. They are not comparable to
`trial/` and must never be quoted as if they were, which is why `rung` is
journalled beside `model`. **Split every rate by rung before reading it**: the
ladder is heterogeneous now, so an aggregate accept rate mixes instruments.

Do not let a borrowed number turn into a claim about this system. The parent
project's most expensive errors were numbers nobody could source.

## 1. The two rules

**1. This engine's faults were PREDICTED to be in what the manager says. Measured,
they have overwhelmingly been in Python.**

The prediction was: *"the parent's faults were in Python — a constant nobody
chose, a guard hunting one literal, a default branch that raised. Those failure
modes are mostly gone here."* **They are not gone.** Of the scars in §5,
counting by where the fault lived rather than where it hurt, the large majority
are framework and harness faults; three are the brief; three are process. And
every fault found on 2026-09-13 — nine of them — was Python or a systemd unit:
a parser that ran what the contract said was not a command, two truncation caps
in series, a reply banked as an answer, one label for three faults, a want with
no completion signal, an exit code that suppressed its own restart, a
`StartLimit` in the section where it is ignored, a sandbox that was never in
force, and a shell inheriting the engine's environment.

Put plainly: **the design moved the judgement out of Python and the faults
stayed.** That is not a reason to abandon it — the faults are *findable*, each
one had a test that failed first, and none of them was the manager producing
confident garbage. But a doctrine file whose §1 says the Python danger is over
will mislead the next session that reads §0–§3 and skips §5, which is exactly
how this drifted for three days. Corrected 2026-09-13 after an outside review
pointed at the contradiction between this section and the git log.

The prose rules below still hold, because the manager's faults *when they come*
behave as described — not reproducible, and no test catches them:

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
   shared files, no shared volume, no shared container. Reading its source is
   allowed and has twice changed this design; writing to it never is.
   **One recorded exception** (Tue, 2026-09-12): `observer.py` was ported from
   the spine's. An observer is an observation surface, not part of the system
   under test, and copying it changes neither framework's behaviour. The
   condition is that it was copied **once and is never synced** — a file that
   keeps being merged is how two independent systems quietly become one. What
   was taken is the architecture (single tick, incremental tail, capped
   display); the kinds, panels and palette are this engine's own.
   **They now share the laptop** (§4), and that is the only thing they share.
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

- ~~Every scar about Python framework internals: `classify_error`'s default,
  **truncation caps in series**, the quadratic dependency scan, guards keyed on
  one literal string, the `st_mode` cache key. This engine does not have those
  failure modes.~~

  **WRONG, and expensively so. Corrected 2026-09-13.** This engine had
  truncation caps in series for its whole life: `EXEC_STDOUT_CHARS = 1200` cut
  stdout on the way into the journal, and `HISTORY_OUTPUT_CHARS = 2400` was
  then applied to data already cut — so a carefully measured 700→2400 raise did
  nothing at all, and a 4 KB tool was shown to its own author 1,200 characters
  at a time while it tried to extend it. Guards keyed on one literal string
  also recurred, three times in one evening, inside the tests written to catch
  that class.

  The general lesson is the opposite of what this section said: **a failure
  mode you inherit the *shape* of, you inherit.** What does not transfer is the
  parent's specific code; what transfers is every way a cap, a literal or a
  default can quietly do nothing. Read the parent's scars as a checklist of
  shapes to look for here, not as archaeology.
- The parent's §8 live state. It describes a different running system.

**This repo starts with almost no scars, and that is the honest condition.** The
parent's doctrine is valuable *because it was earned*. Resist the urge to
pre-populate §5 with plausible-sounding lessons; a scar nobody paid for is a
guess with authority it has not earned.

## 4. Standing decisions (Tue's, inherited)

- **It runs on the same Linux laptop as the spine** (Tue, 2026-09-12), under
  `deploy/cousin-engine.service`. Not convenience — **the only configuration in
  which the comparison means anything**: same hardware, same network, same
  shared quota. On different boxes no latency or throughput figure from the two
  projects is comparable, and comparing them is the point.
  **Two consequences.** The laptop cannot run `gemma4:12b`, so the deployed
  ladder is free-tier only with **no floor** when a rung 429s — slower and
  gappier, and more honest, because a standin in the ladder is exactly how its
  numbers later get quoted as the real rung's. And **fast multi-cycle
  experiments end when we deploy**: anything needing many cycles quickly must be
  run against a local model on a development box first (Tue's point, and it is
  why the 60-cycle local run was done before the move rather than after).

- **SPINE IS PAUSED as of 2026-09-13 13:50 CEST** (Tue), to raise this engine's
  cadence. It was `enabled` and had been up continuously since 2026-09-10
  00:41; in its last hour it made 18 served calls, **every one to
  `google_gemma / gemma-4-31b-it`** — exactly this engine's primary rung.

  > Restore with `systemctl --user enable --now growing-spine`.

  **Numbers taken while spine is paused are NOT comparable to numbers taken
  before it**, in either direction. Any rate measured now is measured against a
  free tier this engine has to itself, which is not the condition the project
  is designed around. Say which era a figure comes from or do not quote it.

  The parallel comparison is suspended, not abandoned: it was already void on
  throughput (below), and nothing is being compared while the framework is
  still being fixed every few minutes. It becomes meaningful again only when
  both run untouched, side by side, which requires restarting spine first.

- **Growing Spine is on the SAME API accounts, so the free tier is SHARED**
  (Tue, 2026-09-12). **Suspended 2026-09-13 — see above.** This engine gets at most half of what it would with its own
  account, and the two projects can starve each other. Three consequences, all
  binding: (1) a rate limit here may be the spine's traffic, not a real ceiling
  — never read a 429 as a measurement of this engine's cost; (2) **throughput is
  not comparable between the two projects** and must never be reported as if it
  were, though cost-per-cycle and verdict quality still are; (3) the ladder must
  be quota-polite — fall through on 429 rather than retry, which is why 429 is
  `NEXT` and not `RETRY` in `classify_error`. Measured the same day:
  `openrouter/gemma-4-31b-it:free` was already returning 429 while
  `gemini/gemma-4-31b-it` answered in ~32s.

- **Where each function lives — creature, cousin, or framework** (Tue,
  2026-09-13, deciding it rather than leaving it implicit). The prompt was that
  "task prioritization" is not one function but several, and that **testing
  belongs on the non-coding side**, because a builder judging its own work has
  the wrong evidence: it knows what it meant.

  | function | home |
  |---|---|
  | task invention — what to build | **creature** |
  | need statement — what I cannot do | **cousin** |
  | ordering of needs | **framework** (the want channel: newest-3, superseding) |
  | ordering of the creature's own work | **creature**, inside its world |
  | tool availability — what exists, what is on PATH | **framework** |
  | running the test | **cousin** |
  | the verdict | **cousin** |
  | **enforcing** the verdict | **nobody** |
  | recording who ran what | **framework** (`kernel/library.py`) |

  Two of these are the load-bearing ones. **The cousin states a lack, never a
  task** — a user says *"I have tasks in `plan` and no way to say which matters
  first"*, not *"add a priority flag"*; the creature owns the shape of the
  solution or it is taking dictation. That is §1's *state the invariant, never
  the mechanism*, aimed at the cousin's wants, and the live want
  `"Task prioritization."` is already on the wrong side of it. **And a failed
  verdict withholds nothing.** A cousin that could keep a tool out of the
  library would hold a write path into the creature's world without touching a
  file (§2.3) and be a second judge with no judge of its own — the reason
  `census.py` reports and never gates. The pressure is visibility instead: the
  library listing carries, per tool, whether its user has ever run it and what
  the last run exited.

- **Both inhabitants see the library, every time, as state rather than news**
  (Tue, 2026-09-13): *"I want and need the creature to be always aware of the
  tools available to it"*, after the way MCP and skills re-present a tool's
  frontmatter on every load. The cousin's library gap was found and fixed
  2026-09-12 (§5); **the identical gap aimed at the BUILDER survived it for a
  day**, because the fix had been written as "a judge needs both sides of a
  comparison" rather than "both inhabitants need to see the library". A
  creature told its tools are on PATH and never told which is being handed a
  promise the context does not keep.

- **NO RESET YET — and the trigger that would start one is named** (2026-09-14).
  Twenty hours on one unmodified build produced **29 tools added and one
  removed** (a temp file), a library of 31 with ~11 near-duplicate stems
  (`archive-*` ×7, `plan-*` ×7, `subtask-log*` ×4), every twin **accepted**.
  That is a flat pile rather than compounding capability — the failure spine's
  own composition prompt is written against — and it is the headline finding of
  run 2.

  Two candidate causes, and only one was actionable without guessing.
  **Rejected by measurement:** *the creature cannot read what it must extend*
  (window 2400 < several tools). It edits 7 KB files freely —
  `subagent-orchestrator` eleven times, `plan` four — so the window is friction,
  not a wall. **Acted on:** the direction channel was discarding 29 of 50 wants
  before the creature had a turn, so it was chasing a target that moved every
  visit. Fixed in `17d8951`.

  **The reset is HELD deliberately, because resetting now would confound the
  two.** A clean library *and* a fixed want channel, changed together, tells us
  nothing about which mattered. Worse, it would hide the more interesting
  question: the creature merged `prioritize` into `plan` and deleted `taskprio`
  on 2026-09-13, so digging out of its own pile is a capability it has shown.

  > **Trigger, RE-CUT 2026-09-14 within the hour, because the first version
  > measured the wrong thing.** It was adds-per-want and removals — a count of
  > tools. Then the tools were actually read, and the count turned out not to
  > be the problem.

  **What reading them showed.** The architecture is good: all seven `archive-*`
  tools share one store (`data/archive.json`) rather than reimplementing it,
  nearly every tool calls two to four others, and there is exactly one stub
  marker in 31 files — and it is a comment. `subagent-orchestrator` decomposes
  a task via an LLM, `preview-subtasks` shows that decomposition without
  running it, `archive-synthesize` merges entries. The creature is building
  itself an agent framework, and the twin-stem count badly misrepresented it.

  **The execution is what is broken. Cousin probes: 39 exit-0, 109 non-zero —
  three quarters of the time its user runs one of these tools, it fails.** And
  the shape is worse than the ratio: `plan`, the centre of the system, went
  `0` once and then non-zero on **thirty consecutive probes**; the entire
  subtask-log family (`subtask-log-viewer`, `view-subtask-logs`,
  `summarize-subtask-logs`) has **never once returned 0**; `subagent-orchestrator`
  is 7 zeros in 43.

  So this is not a creature making twins. **It is a creature building storeys
  onto a floor that returns errors to the only person standing on it** — and a
  cousin accepting enough of that to keep the wants coming. Consolidation
  cannot fix that; nothing above `plan` means anything while `plan` fails.

  > **RETRACTED THE SAME EVENING, and the retraction is the finding.** The
  > trigger above was the exit-0 share of `cousin_probe`, against a "26%
  > baseline". That number is an artifact of the harness. `evidence()` invokes
  > every tool **bare, with no arguments**, so a tool whose call-line takes an
  > argument can never exit 0 — and the brief tells the cousin explicitly that
  > a tool refusing incomplete input and saying what it needs has done its job.
  >
  > Re-counted over 153 probes: **39 exited 0, 97 were the tool correctly
  > asking for its arguments, and about 12 were real failures.** So ~89% of
  > probes behaved properly and the "broken floor" was mostly the probe's own
  > empty hands. `plan` read as "1 worked and 30 failed" because it asked for
  > an argument thirty times.
  >
  > This is §5's top scar, committed by me twice in two hours: I built the
  > display that counted refusals as failures, then read a creature "building
  > storeys on a broken floor" out of it and wrote that into doctrine and two
  > prompts before checking whether the harness produced it. `cousin_probe`
  > now records `bare`, and the run-record counts a usage refusal as its own
  > thing — the framework already knew, it simply never wrote it down.
  >
  > **What survives:** `subagent-orchestrator` has a real, repeated Python
  > error, and that is a genuine broken floor worth watching. What does not
  > survive is the claim that the library at large is failing its user.
  >
  > **The reset trigger is therefore withdrawn, not re-cut.** There is no
  > measured crisis to reset over: the twins are real but the failure rate was
  > not. Run 3 becomes a deliberate clean-start when the framework is settled,
  > which is the reason it was always worth doing — not a rescue.

  Tool counts stay recorded but are no longer the decision variable: a library
  that doubles while nothing runs is worse than one that does not grow at all.

  Until that fires, the brief is not to be touched: two changes at once and
  neither is measurable.

- **Who may propose a cull** (2026-09-16, PLAN item 10). **The creature owns
  it; the framework owns only the visibility; the cousin gets nothing.** §4's
  table already settles the principle — *ordering of the creature's own work*
  is the creature's — and a cull is that. A cousin that could retire a tool
  would hold a write path into the creature's world without touching a file
  (§2.3), and since 2026-09-16 that is impossible rather than forbidden: its
  shell gets a **copy** of the library, remade per visit. What the framework
  may add, and has not, is one line of stem families in the listing both
  inhabitants already see. **Trigger: forty-eight hours after the cousin's
  shell goes live, if families of 3+ are still growing and nothing has been
  removed.** Not before — the twins may be an artifact of a user that could
  only ever call things bare.

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

- **This framework is NOT DETERMINISTIC, so one observation is not a
  measurement — and I spent a night forgetting that.** Tue, 2026-09-13, after
  watching it happen: *"any amount of change to the way the mentor or creature
  behaves could actually steer it away from a better course, and you might go
  back and forth and never get an improvement because it is as good as it ever
  gets. Also some models react very differently — while you are optimising for
  gemini and then get some other model, that model might fail or succeed where
  gemini did not."* All three were already true of the work in progress. **Five
  changes to how the creature's context reads were made in four hours** —
  fenced→quoted history, cap 700→2400, line-boundary cuts, output delimiters,
  header wording — plus temperature 0→0.4, a cousin budget change and a ladder
  reorder, **each declared good from a single 15–50 minute window with no
  baseline and no control.** "The call-line fix worked, the newest want is
  distinct" was ONE want.

  **Split every change into two kinds and treat them differently:**

  | | |
  |---|---|
  | **Correctness** — wrong for any model | a relative root that hides tools; a history that parses as a command; a marker that will not say who cut; a WAF 403 read as a bad credential; a swallowed exception that makes a bound unreachable. **Fix immediately; no measurement needed.** |
  | **Tuning** — behaviour under one model | temperatures, caps, budgets, prompt wording, ladder order. **A change here needs a before/after across several windows, split by rung, or it is superstition.** |

  The second kind is where this goes wrong, because it FEELS like the first.
  `vitals.py` exists to make it measurable: counts and ratios only, **split by
  rung always**, directions rather than a score — a score invites declaring a
  change good because one number moved. It prints, in its own output, that one
  window is an anecdote.

  **And the ladder is heterogeneous now**, so an accept from `gemma-4-31b-it`
  and one from `gpt-oss-120b` are different instruments whose average measures
  neither. Tuning the transcript against whichever model happened to answer is
  optimising into noise.

- **The parser contradicted the contract the creature is held to, and the
  creature built a false belief about its USER out of the evidence we handed
  it.** 2026-09-13. `CREATURE-PROMPT.md` says it twice — line 54, *"To DO
  anything you MUST write executable ```bash blocks"*, and the prompt teaches
  the tool header using a **bare** fence as an example that is plainly not a
  command. `FENCE_RE` made the tag optional. So when the creature quoted a
  tool's OUTPUT in a bare fence while reasoning about it — *"Tasks sorted by
  priority (Goal: ...)"* — the framework ran it. Exit 2. **And in the next
  reply it read that manufactured failure out of its own transcript and
  concluded: *"This happened because the cousin probably copied the output of
  a tool and tried to run it as a script."*** Eighth appearance of *the
  framework manufactures work and the creature is billed for it*, and the
  first time it has reached one agent's model of the other — a fabricated
  complaint arriving by the back door, against the agent whose testimony this
  design exists to keep honest. **Invariant: when the prompt names a marker,
  the parser requires that marker. An optional tag is a second, unstated
  contract, and only one of the two is in the creature's prompt.** Fixed by
  requiring `bash`/`sh`; an untagged-only reply now classifies as
  `untagged_fence` rather than `no_command` and is explicitly NOT counted as
  commands lost, because a change that quietly stops doing something looks
  exactly like a model that stopped asking for it. Measured across the
  restart: exec `exit 2` **12 before, 0 after**.
  **Two process failures made this cost more than it should have.** (1) I
  reported the opposite an hour earlier — *"harness exonerated, the creature
  emitted those blocks itself"* — reasoning from what `FENCE_RE` does rather
  than from the contract the creature is given. Reading the implementation
  told me what happened; only the prompt could say whether it was allowed.
  (2) It was findable **only** because `raw` had started being journalled on
  the think one cycle earlier. `chars` and `finish` had been the whole record
  for the life of the kernel, and the cousin's verdict had kept its raw text
  since 2026-09-12 — the asymmetry was the bug, and the top scar below says
  so in general terms.

- **THE FENCE THAT ATE NINE HOURS, and then my fix ate a command forty minutes
  later.** 2026-09-14, and it is two scars in one because the second is what
  the first teaches.

  `FENCE_RE` closed a command block on ANY run of three backticks, non-greedy.
  The creature wrote `subagent-orchestrator`, whose job is stripping markdown
  fences off an LLM reply, so its source contains a `startswith` against a
  fence literal. That inner run closed the bash block early, the heredoc never
  terminated, and the file landed cut mid-string: *SyntaxError: unterminated
  string literal*, line 68. **Twelve SyntaxErrors across twelve rewrites
  between 19:46 and 04:35.** Each time the creature read a syntax error in its
  own file and rewrote the tool; each time we cut it at the same character. It
  could not see the cut, because the transcript shows what RAN -- and what ran
  was the truncated command. **A tool that manipulates fences is exactly the
  tool this made impossible to write**, which is why it went round twelve
  times instead of being noticed once.

  The fix anchored BOTH fence ends to column 0. Within forty minutes the
  regression watch caught the cost: a reply ending `...</thought>` immediately
  followed by the opener ON THE SAME LINE meant `^` never matched, and a real
  command was dropped as `unclosed_fence`. **Only the CLOSING fence needs
  anchoring** -- a fence inside code sits mid-line and so cannot close a block,
  while a genuine terminator always starts its own line. The asymmetry was
  there to be seen and I did not look for it.

  **Invariant: when you change a parser the creature speaks through, assume the
  change has a cost and go looking for it in the next hour.** The watch found
  it in forty minutes; without the watch it would have been another nine-hour
  silence. And the classifier that reports these must ask by OUTCOME -- a
  tagged marker present with no block parsed means work was LOST -- never by
  counting delimiters, which mistook a fence inside a string for an unbalanced
  block and a mid-line opener for "no command".

- **I measured the creature with an instrument that could not see what it was
  measuring, twice in one evening, and wrote both readings into doctrine before
  checking.** 2026-09-14.

  First: *"26% probe success -- the creature is building storeys on a broken
  floor."* Re-counted over 153 probes: **39 exited 0, 97 were the tool
  CORRECTLY refusing incomplete input, ~12 were real failures.** `evidence()`
  invokes every tool BARE, so a tool whose call-line takes an argument can
  never exit 0 -- and the brief tells the cousin in as many words that refusing
  incomplete input and saying what you need is the tool doing its job. `plan`
  read as "1 worked and 30 failed" because it asked for an argument thirty
  times.

  Second: *"subagent-orchestrator has a repeated Python error."* It compiles
  clean, its `--help` exits 0, and its twelve SyntaxErrors were all historical.
  What it has never had is one invocation WITH arguments from its user.

  Both readings were built on the harness's own behaviour, and both were
  written into CLAUDE.md, the cousin's brief and the creature's prompt before
  anyone checked. **The top scar in this file says to prove the harness was not
  producing a finding before believing it. I did not, twice, in one hour, while
  actively citing that scar.** `cousin_probe` now records `bare`, and the
  run-record counts worked / asked-for-arguments / really-FAILED apart.

- **The anti-twin rule fails on JUDGEMENT, not on missing evidence -- and that
  is now isolated.** 2026-09-14, 23:06. The cousin's want named
  `list-parent-tasks` as the example of what it needed. That tool already
  existed in the library the creature is shown every wake. The creature wrote a
  new tool, `obtain-parent-task-id`. The cousin then **ACCEPTED it after
  actually running it and getting real output** -- so this is not the
  bare-call problem, and not the 2026-09-12 problem of a judge shown only one
  side. The library was on the page, the run-record was on the page, the rule
  was in the brief, and the verdict still went the wrong way.

  Run 2 in total: **40 tools added, 3 removed, 38 in the library, with
  `archive-*` x9, `plan-*` x8 and `subtask-*` x5.** That is a flat pile rather
  than compounding capability. It is the open question this project now turns
  on, it is a BRIEF matter, and it is frozen until it can be measured properly
  rather than patched at midnight.

- **AN INSTRUMENT SPOKE IN THE VOICE OF THE THING IT WATCHES, AND ITS READER
  CONCLUDED IT WAS DEAD.** 2026-09-15, found by Tue rather than by me: *"not
  sure why the monitor is not running."* It was running — 272 runs, the last
  ninety seconds earlier — but `cousin-monitor.service` sat in `failed`,
  because I had made a standing alarm exit 1 and written in the unit that this
  makes `systemctl --user --failed` *"say exactly when to look"*. A `failed`
  unit is indistinguishable from a crashed script, so one face served both
  *the engine has a problem* and *your instrument is dead* — and the reading
  he took is the correct reading of that signal. Fifth appearance of **a
  checker that cannot distinguish the thing it measures**, and the first where
  the confusion was about the checker's OWN health. **Invariant: a monitor's
  failure is never reported in the same channel as its findings.** Three exit
  codes now (0 / 1 finding / 2 the monitor broke), `SuccessExitStatus=1` so
  `failed` means only *go fix the monitor*, and the standing state is a file
  whose presence is the signal (`live/monitor/ALARM`, removed when the last
  alarm clears) rather than a unit state that has to be interpreted. A monitor
  that stops running entirely is caught by neither, which is why the page's
  first line is the time it was written.

- **A GUARD THAT RUNS AFTER THE DESTRUCTION IS A COMMENT.** 2026-09-16, found
  by an independent verifier who pointed the new drill harness at a simulated
  live root. `rehearse.main()` cleared each target with `shutil.rmtree` and
  *then* asked `scratch_root` whether it was allowed one — so it printed
  `REFUSED` having already deleted a subtree of the deployment, including a
  file under `tools/own`, which §2.1 makes a hard boundary. The real `live/`
  survived only because none of its seven entries happens to share a name with
  a drill. The same guard also allowed `~/growing-cousin` (the live unit's
  WorkingDirectory) and **`~/growing-spine`** outright — §2.6's hard boundary,
  which the harness would have created and removed directories inside without
  a murmur. **Invariant: ask before destroying, and check every ancestor, not
  the leaf.** It now refuses the sibling by name and refuses any git checkout,
  because a checkout is somebody's working tree. The gate reproduces the exact
  attack and asserts the file is still there afterwards.

  Worth keeping for its shape: this is the THIRD version of that guard. The
  first checked the path it was given (missed `<live>/tool-gone`), the second
  walked ancestors (missed the destruction ordering), the third asks first.
  Each version was written against the failure the previous one had just
  shown, which is what a guard's history looks like when it is being earned
  rather than assumed.

- **A LADDER THAT HAD ALREADY DIAGNOSED A DEAD CREDENTIAL FORGOT IT ON THE
  NEXT CALL.** 2026-09-16, found by the give-up drill — which is what the
  drill is for. `ladder()` walls a rung by adding it to a set and skipping it
  thereafter, so the second time every rung is walled, `tried` is empty and
  `all_walled=bool(tried) and all(...)` came out **False**. `default_is_wait`
  says in as many words that a rejected credential is not a wait, *"because
  waiting cannot fix it and a loop that waits politely forever on a broken key
  looks exactly like one that is working"* — and the ladder contradicted it
  from the second call onward. An engine whose every credential had been
  rejected would have waited 600 × 150s: **twenty-five hours looking healthy
  while nothing could ever answer it.** **The first call was honest**, which
  is why nothing that only ever looked at a first failure could see it, and
  why it took manufacturing the fault to find it. Fixed by asking about the
  RUNGS rather than about what this call happened to attempt.

- **THE EDIT THAT WAS COMMITTED AWAY, AND A GATE THAT COULD NOT SEE WHICH BODY
  IT DEPLOYS.** 2026-09-16. The unit was changed to `--body docker`; a file
  shuffle then copied a stale copy over it; the commit shipped and the engine
  deployed with the creature still on `LocalBody` — keys readable, exactly as
  before — while the commit message described the change as done. **Nothing in
  the gate noticed**, because every assertion about that unit was about
  restart bounds and sandboxing and none about which body the engine runs.
  §5's oldest systemd scar is *a setting that is present, parsed and live can
  still do nothing*; this is its mirror, and it is harder to see, because
  there is no directive to read back — only an absence. The same start also
  showed an `ExecStartPre` image build that could never succeed (buildx writes
  under `~/.docker`, which `ProtectHome=read-only` forbids), hidden by its own
  `-` prefix: **an advisory step that always fails is worse than no step.**
  Both are asserted now, and the body assertion was verified red against the
  exact version that shipped.

- **ALPHABETICAL ORDER WAS AN IMPLICIT CHOOSER IN TWO PLACES, AND IT
  MANUFACTURED A DAY OF TWINS.** 2026-09-15, found at 18:55 in the monitor's
  first evening read, eighteen hours after it began. (1) `pick_target`'s
  fallback was `tools_after[-1]` — the alphabetically last tool — taken on
  every `DONE_CLAIM` and `STALL` visit for the life of run 2. On 2026-09-13
  that was `plan`: **30 probes, bare**, which is the whole of the "1 worked
  and 30 failed" reading, not only the bare-call artifact. From 2026-09-14 it
  was `view-subtask-logs`: **63 probes; 28 of 30 non-write visits in eighteen
  hours**; each exited 2 with its usage line, the brief correctly counted that
  as the tool working, the cousin ACCEPTED, and — unable to run it *with*
  IDs — asked for *"retrieve logs for multiple parent task IDs"* **six
  times**. The creature answered five different ways (`view-multi-`,
  `view-recursive-`, `view-multiple-subtask-logs`, `synthesize-multi-parent-
  logs`, `subtask-logs-multi`). (2) The listing was `names[:40]`, alphabetical,
  so from 07:00 the seven tools past the cut were **exactly those answers** —
  shown to nobody, so it could not see them and built the next. Thirteenth
  instance of *the framework manufactures work and the creature is billed for
  it*, and it reverses part of the 2026-09-14 scar: this batch of twins was
  not the cousin's judgement.

  **Invariant: a position in a sorted list is never a reason.** Every choice
  the framework makes on the creature's behalf carries its reason as a
  recorded field (`cousin_probe.picked_by`: `new` / `written` / `ran` /
  `least_probed`), and a bound on a listing DEGRADES it — name and purpose
  past the limit — and never hides from it. `want_repeated` and `probe_stuck`
  now fire within three visits; replayed, they fire on every fixture this repo
  has, including the one cut as a "healthy hour", because the fault was live
  in all of them. **Proven with the journal before believed** (the chains
  trigger → probe → verdict → want, since start), per the top scar — and the
  proof took one query because the page had already pointed at the exact
  three identical want/verdict pairs.

- **The record was corrected and the display was not, so both inhabitants
  kept being shown a broken floor for a day after the misreading was found.**
  2026-09-15. `cousin_probe` gained `bare` on 2026-09-14 (f52ac78) and the
  run-record started counting usage refusals apart — for probes written AFTER
  that. Every probe from the first day and a half has no flag, and
  `library.status()` computed `failed = runs - ok - asked`, so all of them
  read as real failures: `subagent-orchestrator` "7 worked and 36 FAILED",
  `plan` "1 worked and 30 FAILED", served to the creature and the cousin every
  wake. Found by the monitor's library table on its first live render, which
  had an *unqualified* column because the detector rule is three states, never
  two. **Invariant: when a field is added to make a distinction, every reader
  of the old records must have a third answer — cannot tell — or the fix
  applies only to the future while the display keeps lying about the past.**
  Fixed the same hour; the listing now says "unknown outcome" for those.

- **A SETTING THAT IS PRESENT, PARSED AND LIVE CAN STILL DO NOTHING — twice in
  one evening, and only testing the EFFECT found either.** 2026-09-13.
  (1) `StartLimitIntervalSec`/`StartLimitBurst` were written into `[Service]`,
  where systemd ignores them; the unit read back `StartLimitIntervalUSec=10s`
  while the file said 1800. (2) Far worse: `ProtectSystem=strict`,
  `ProtectHome=read-only` and `ReadWritePaths` were **entirely inert** in a
  *user* unit without `PrivateUsers=yes` — a throwaway unit carrying all three
  **wrote a file into `$HOME`**. So the creature's bash, written by free-tier
  third-party models, could read *and write* anywhere this user can, including
  `~/growing-spine`, which §2.6 makes a hard boundary. The unit's own comment
  claimed the opposite. **Invariant: a directive read back off the unit proves
  it was PARSED, never that it WORKS — test the effect, from inside the same
  sandbox, before believing any protection exists.** Six effects were checked
  before shipping the fix, because a sandbox that breaks the run is discovered
  at 03:00 by nobody.

- **The body ran untrusted input in the class whose docstring forbids exactly
  that, and passed it the engine's whole environment.** 2026-09-13, found by an
  **outside review of the public repo**, confirmed here the same evening:
  `LocalBody` says *"not a sandbox... for running OUR fixtures, never untrusted
  input"*, and production feeds it bash from third-party models with
  `env=dict(os.environ, ...)`. A creature-style command read `~/keys/*.key` and
  listed the spine's directory. Fixed with an **allow-list** child environment —
  a deny-list has to be updated every time a new secret-shaped variable appears
  and it will not be. **Still open and stated rather than implied: the key files
  remain readable by anything running as this uid.** The generalisation:
  **a class's own docstring is a contract, and deploying against it is a
  decision someone has to make on purpose** — nobody ever did.

- **Two caps in series, and the one that was tuned was not the one that acts.**
  2026-09-13. `HISTORY_OUTPUT_CHARS` was raised 700→2400 against a real
  measurement; `EXEC_STDOUT_CHARS = 1200` had already cut the data on the way
  into the journal, so the raise did nothing and the served context had been
  printing `window 1200` ever since for anyone who read it. Cost: `plan` grew
  to 4,022 bytes, the creature ran `cat tools/own/plan` six times in fifteen
  minutes, saw a third of it each time, and built nothing. **Invariant: the
  journal is the evidence, so it may never keep LESS than a consumer is allowed
  to show** — asserted now, so the next raise cannot be swallowed.

- **A reply is not automatically an answer, and banking one hid a dead rung.**
  2026-09-13: `gemini/gemma-4-31b-it` served the cousin 14 times and produced 0
  usable verdicts — every one cut at `finish=length` after spending ~94% of its
  budget on reasoning — while `groq/gpt-oss-120b` went 2 for 2. The ladder
  counted all 14 as successes, so it never fell through. This project had
  already written that down — *such a call registers as a SUCCESS, so nothing
  walls the rung and nothing below it is ever reached* — and I read the symptom
  as weather for four hours anyway. **The fix came from reading Growing Spine**,
  whose `keychain/provider.py` returns a reasoning-only completion as an error
  so the keychain hops window. Spine also settled the tempting wrong fix:
  *"verdict-first fights how reasoning models generate"* — do not ask a
  reasoning model for the answer first; **fund the musing** and require a
  terminal block.

- **One label for three faults let a broken channel read as weather.**
  2026-09-13: 14 of 16 verdicts came back `no-block`, which I read as "the model
  declined to answer". The fields said otherwise the whole time —
  `chars_before_strip=8407`, `chars_stripped=7935`, `finish=length`. The think
  side had kept `truncated` / `budget_spent` / `no_command` apart since the
  kernel's first week; the cousin side collapsed them. **Every distinction you
  refuse to record, you will later have to guess.**

- **A channel with no completion signal is re-served forever.** 2026-09-13: a
  `want` stayed in the managed context until three newer ones pushed it out, and
  new wants only arrive on an accept — so between accepts the creature was
  handed the same direction every wake with no way to mark it done, and spent
  cycles re-running `plan goal / plan add / plan list`. The trigger scar one
  level up, and its resolution was already written three lines from where the
  fix hooks in: **a visit is the ANSWER to what summoned it, so it clears what
  summoned it.** An UNKNOWN clears nothing — a bad reply must not erase the only
  direction the creature has.

- **Giving up is not finishing, and exiting 0 for both meant nothing restarted.**
  2026-09-13: the supervisor abandons the run after 5 consecutive failures or
  600 waits, `run.py` returned 0, and the unit says `Restart=on-failure` — so
  the engine could quit at 03:00, report success, and lie there. Found while
  answering *"can I check once a day?"*, which is the only reason it mattered
  enough to look. **A flag, never a parsed reason string**: the reason is prose
  for a human, and a caller that decides by matching it is a checker agreeing
  with a producer by eye.

- **An outside reader found in one pass what three days inside did not.**
  2026-09-13, a review with GitHub-only access under a zero-assumption contract.
  It found the inert sandbox path, four different gate counts in four documents,
  `ARCHITECTURE.md` still announcing *"nothing deployed"* three days after
  deployment, production headline figures quoted from the run this project had
  itself archived as contaminated, and §1/§3 contradicted by §5 and the git log.
  **None of it needed access we do not have; all of it needed a reader who had
  not been here while it happened.** The generalisation is uncomfortable and
  worth keeping: *the documents drift fastest in exactly the sessions that are
  working hardest*, because every fix is written into the commit message and the
  status sections are updated from memory. Where a number can be generated,
  generate it; where it cannot, date it and name its run.

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
   life of the project. `ARCHITECTURE.md` §11.

   > **DECIDED AND NOT EXECUTED — recorded 2026-09-16, because this file was
   > claiming a thing that never happened.** Run 2 began *"from nothing: no
   > journal, no context, no memory, no tools"* (§0), and run 1 before it was
   > the same. So the copy has never been done, the known-answer refutation
   > path has never been taken, and every reading of the cousin's judgement to
   > date rests on a library with no known answers in it.
   >
   > **Bound to run 3 (PLAN item 11)**, with the tagging requirement intact:
   > every inherited tool tagged at t=0 and every metric split on that tag, or
   > the run measures a mixture and reports it as one number.
   >
   > **Still open: does it also inherit the journal and memory?** Tue's call,
   > and it can be taken at run 3 rather than now.
4. **When does the cousin earn the right to audit?** It may look at the whole
   library from day one (`ARCHITECTURE.md` §2, the audit rules), but an audit is
   where a manager most easily produces confident garbage, and nothing checks it
   but the complaint-fidelity census — which PLAN item 1 wires into the monitor
   so that it runs on every pass rather than only when a human types it. (What
   is actually deployed is a question for `live/monitor/status.md`, never for
   this file: a document asserting the state of a running system is the scar in
   §5 about settings that are present, parsed and doing nothing.)
   Consider proving it on the touched-this-cycle path first.

   > **Trigger, named 2026-09-16: when the cousin can invoke tools with
   > arguments (PLAN item 9).** Until then an audit is confident garbage by
   > construction — it would be a judgement about a library the judge cannot
   > operate, and §4 is explicit that a hold without a named trigger is
   > inaction in the costume of caution.
5. **Repo visibility.** Private while it is documents only (Tue, 2026-09-10).
   Revisit when code lands — the parent is public, so the default is public, but
   confirm rather than assume.
6. **Which rung serves the manager.** In the parent, one pool rung wasted 86.7%
   of the cycles it served with clean, complete, command-free replies. A manager
   on a rung like that produces confident garbage instead of an obvious failure.
   Record the model per verdict from day one.

## 7. State — 2026-09-14, run 2 at 35 hours (the loop works; the judgement is the question)

> **2026-09-15 addendum.** The figures below are now *derivable* rather than
> typed: `python3 -m monitor status --root live` prints them per window with
> the engine commit beside each, and `live/monitor/status.md` is regenerated
> every five minutes on the laptop. The next rewrite of this section should be
> pasted from that page, not composed from memory — the outside review's
> finding was that these sections drift fastest in the sessions that work
> hardest. First live render, 00:38: 0 alarms, 4 cannot-tell, 3 informational;
> `selfcheck` proved all six deployment effects; run 2 stands at 37 tools.
>
> **Evening read, 2026-09-15 18:52, engine `00d77d1` since 00:56:** 424
> wakes / 157 thinks / 212 commands; 17 verdicts (gemini 14 ACCEPTED, 2
> RETURNED; groq 1 ACCEPTED); 16 wants, **11 distinct — one of them six
> times**; 10 tools added, 0 removed, **47 in the library** (`archive-*` ×10,
> `plan-*` ×9, `subtask-*` ×6, `view-*` ×4). Probes: 4 worked / 41 asked for
> arguments / 0 failed. `rung_broken` 0. The six-times want and the `view-*`
> family are the chooser fault (§5); the numbers after the 19:xx restart are
> the first measured without it.

**Measured over run 2 entire, 2026-09-13 12:48 to 2026-09-14 23:48 (35.0 h).
The engine changed roughly twenty times inside that window, so these are
totals, never rates of anything:**

| | |
|---|---|
| wakes / thinks / commands | 935 / 755 / 944 |
| cousin probes | 179 |
| verdicts | 133 |
| wants | 63 |
| tools added / removed | 40 / 3 |
| library now | 38 |
| `rung_broken` (needed a human) | **0** |

**Verdicts split by rung, because the ladder is not one instrument:**

| rung | accepted | returned | unknown |
|---|---|---|---|
| `gemini/gemma-4-31b-it` | 57 | 31 | 19 |
| `cloudflare/llama-3.3-70b` | 2 | 18 | 0 |
| `groq/gpt-oss-120b` | 4 | 2 | 0 |

Gemini accepts 57 of 107; cloudflare accepts 2 of 20. **An aggregate over that
ladder measures neither**, and the difference is not yet explained.

**What works.** The loop closes repeatedly and unattended: the creature builds,
the cousin runs and judges, the want reaches the creature, it builds that. It
survived eleven hours overnight with no intervention. The one genuine repair
this session was proven by the creature running the tool with real arguments
before marking it done.

**What does not.** The library is a flat pile -- 38 tools, `archive-*` x9,
`plan-*` x8, `subtask-*` x5 -- and the cousin accepts the duplicates while
being shown both the library and each tool's run record (§5). That is the
project's open question and it is a brief matter, frozen pending measurement.

**Open, and Tue's:** whether the 2400-character output window should grow
(PLAN item 13 — explicitly not doing, with the symptom that would reopen it).

> **CLOSED 2026-09-16: the creature's shell no longer shares a uid with the
> engine's key files.** It runs in a container (`--body docker`, PLAN item 7)
> whose world is a bind mount of `live/body/mind` and nothing else. From
> inside it, `~/keys`, the host home, this repo and the sibling project do not
> exist. `selfcheck` carries `keys_unreadable` and re-proves it at every
> start; the first start under the container body reported `ok: True` — every
> bound this deployment relies on proven, by effect, rather than believed.
>
> **CLOSED 2026-09-15: the evidence pack.** `evidence/` carries a hashed
> manifest per run; the tarball stays on the laptop.

### Previous state — 2026-09-13, run 2 opening (deployed; the loop closes, throughput is the limit)

**Run 2 began 12:48 CEST from nothing** — no journal, no context, no memory, no
tools — after run 1 was archived as contaminated (§0). Everything below this
heading, until "Previous state", is **run 2**.

The loop closes and the wants progress rather than repeat (§0 carries the
measurement and names the engine SHA for each figure). What limits it is not
the design: it is a free tier where every rung can be at quota at once, and the
one-queue rule means that idles both agents. Nine framework faults were found
and fixed during run 2 (§5), so no rate spans the whole of it.

**Open, and both are Tue's:** the creature's shell still shares a uid with the
engine, so the key files are readable by anything it runs — `DockerBody` or
`LoadCredential=` closes that; and whether the 2400-character output window
should grow, now that a single tool exceeds it.

### Previous state — 2026-09-12, RUN 1 (archived as contaminated)

> Everything in this subsection is from the run whose verdicts were ~40%
> silently discarded because the two agents did not share a queue. It is kept
> because the faults it found were real and the fixes are in the code; its
> **numbers are not quotable as trajectory**.

**It runs unattended on the laptop and it is not yet working.** Seven hours, 95
cycles, 16 verdicts, and **one** of them usable:

> RETURNED — *"I ran `fetch` and it told me it wasn't written yet."*

Correct, and the only judgement the second inhabitant has ever delivered in
production. The creature built four tools (`archive`, `ask`, `fetch`, `plan`)
and that verdict says what they are: **stubs printing "not written yet".**

**CORRECTED 2026-09-12, 21:40 — the direction channel closed the loop in
production.** This section said, twenty minutes earlier, that it never had.
The measurement:

> `TOOL_WRITE` fired on a tool the creature had just written. The cousin ran
> `log "test"`, confirmed `activity.log` had gained a timestamped line,
> **ACCEPTED** it, and asked for the next capability — *"retrieve recent log
> entries (e.g., last 10 lines)"*. `record_want` wrote that into the managed
> context; the creature's next wake served it 17,000 chars including that line;
> it then wrote `log-read`, ran `log-read -n 10`, and got ten lines back.

Creature builds → cousin uses → cousin accepts and asks for what it wants next
→ the want reaches the creature → the creature builds exactly that → it works.
**That is the whole design, and it had never once happened outside a test.**

Two things about how it happened are worth more than the fact of it:

1. **It was served by `groq/gpt-oss-120b`, not by the rung the brief was
   measured on.** The gemma rung was still returning `no-block`. So the first
   working verdict in this project's history came from a model the brief was
   never tuned against — and the accept/refuse rates it produces are therefore
   NOT comparable to `trial/`. This is exactly why `rung` is journalled.
2. **It only happened because of a bug fixed an hour earlier.** Without the
   User-Agent fix, groq was walled as "credential rejected" and this cycle
   would have been another wait.

One swallow. It is one accept, on one rung, on one tool.

The 15 UNKNOWNs split into two causes, and keeping them apart is the point of
recording `error`:

| cause | n | meaning |
|---|---|---|
| `LadderExhausted` | 8 | no rung answered; the cousin correctly refused to judge |
| `no-block`, `finish=length` | 7 | the model answered and was **cut off before the verdict block** |

The second is the creature's own scar one level up: **the contract puts the
block LAST, so a truncated reply loses the whole verdict.** The 700-token
cousin budget was measured on `gemma4:12b`; the real `gemma-4-31b-it` is more
verbose and spends budget on `<thought>` blocks. Raised to 2048 — **not yet
proven**, no trigger had fired at the time of writing.

**Creature truncation is NOT the same problem and was deliberately left alone**:
5 of 65 thinks finish on `length`, but only 2 of 65 lose commands (~3%), which
is where the parent settled after raising 2048→3072. No evidence to tune it.

**What the deployment itself taught**, all four found by running and none by
reading: a relative root made every tool vanish; `run_cycle` swallowed the
exhausted ladder so every wait/backoff bound was unreachable; preflight vetoed
startup on a transient hiccup; and a missing User-Agent had a Cloudflare WAF
403 read as "credential rejected", permanently walling a rung that worked.

### Previous state — 2026-09-12 (on the real rung, first time)

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
