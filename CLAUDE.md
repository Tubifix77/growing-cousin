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

### Handover — updated 2026-09-21, read this before touching anything

**The board is `PLAN.md`.** Every open item this project knows about, in the
order they are being done, one at a time, each with acceptance criteria that
can be checked rather than asserted, and each verified by a reader who did not
build it. Do not start work that is not on it; do not leave work off it.

**THE BOARD IS CLEAR, 2026-09-21.** Tue: *"then lets get the board cleared."*
`PLAN.md` opens with a table of every heading that is not `[x]`, and the point of that table is the distinction it draws: **nothing is left that work can finish tonight.** *(There was a count in this sentence for a few hours. It was wrong -- twenty of twenty-one against a true fifteen of twenty-one -- and a verifier found it. This file's own §0 refuses to write the gate count down for that reason; the board gets the same treatment.)* Each remaining line names a trigger and a
date — which is §4's test for a hold that is real rather than inaction in the
costume of caution.

- **11** run 3, and it is a THIRD experiment rather than this one continued:
  Tue's design, recorded in his words, gated on this table reaching zero.
- **14.5** telling the creature `say` exists. The freeze stopped being the
  reason on 2026-09-21; what holds it now is that a new surface would land in
  the middle of 20.2's first week. **Trigger: 2026-09-25.**
- **16 / 17.3** the cousin noticing a tool serves nothing. Half delivered —
  20.3's instruments are the architecture's own answer and the cousin has used
  one unprompted. The RULE waits on 20.4 and on item 8's scoring discipline.
- **20.4** the cousin USES its continuity — measured 2026-09-21, refuting
  what this file said for two days. Re-read at 17:52: **133 harvests, 59
  carrying a note, none empty since 09-19 20:35**, and the last 40 all
  carried exactly one key. The note is still `baseline-parent-id: 100`,
  now 45 hours old. **Continuity is proven and accumulation is not**: two
  days and a hundred visits have not produced a second key.
- **21.2** the rewrite wall, moved from 9 KB to ~25 KB and not removed.

**THE HEADLINE METRIC ANSWERED FOR THE FIRST TIME, 2026-09-21 01:42.**
*Tools that start, are invoked by someone other than their author, and are
still invoked a week later* (`ARCHITECTURE.md` §12) — the number this project
says it measures before any other, and which had never once been computable
here. **One tool has survived it: `plan`.** At 01:42 the other two
columns read 4 have not and 58 cannot be judged yet; by 02:37 the same
night they read 7 and 56, because windows close by the hour. **Read them
off `live/monitor/status.md` and never from here** -- a verifier caught
this quoting a 46-minute-old pair. The survivor is the stable part:
named by 12 other tools, reached 107 times by its user across 7.4 days.

**One is not a score.** The run is barely older than the window, so most
tools have not had one. Read the three columns on `live/monitor/status.md`
on 2026-09-25 and do not quote a snapshot as trajectory. *(A number stood
here — "so 58 tools have not had a window" — four lines under the
sentence retracting that very figure. A verifier found it within the
hour; by then the page read 11 and 53.)*

**AND READ THE PROBE RATE BESIDE IT, or the metric reads as a verdict on the
library when it is partly a verdict on us.** Measured 2026-09-21 17:52:

| | probes that reached a tool |
|---|---|
| whole run | 53.6 a day |
| last 48 hours | **25.5 a day** |
| since the 01:41 start | **13.3 a day** |

A tool "survives" only if its user reaches for it AGAIN inside seven days.
The library is 69 tools, so at the last-48-hour rate the expected revisits
per tool per week is **2.6**, and at today's rate **1.3**. In the last 48
hours the cousin reached **20 distinct tools of 69**, and 23 of its 51 probes
were `plan`. **So "28 have not survived" is substantially a statement about a
contended free tier and two model calls per visit, not only about whether the
creature builds things worth returning to.** The whole-run average of 53.6
would have hidden that completely -- it is dominated by the bare-probe era,
when the harness probed cheaply and constantly.

**WHAT TO READ FIRST, AND IT IS A READ RATHER THAN A CHANGE:**

1. `cat live/monitor/status.md` — first line is when it was written, alarms
   first, then what it cannot tell, then counts per window with the engine
   commit that produced each.
2. **`deploy_regression_day` for engine `c942d88`, due 09-22 01:41.** That is
   the reading that settles item 21.1, and it needs nobody to remember to
   look. First 16 thinks after the budget raise: 0 finished on `length`, 0
   commands lost — which is an anecdote and is labelled as one.
3. **`commands_lost[gemini]` will still be alarming and that is correct.** It
   is windowed by COUNT (last 20 thinks), so it spans the 09-20 23:38 restart
   that fixed it and clears on its own. Do not reset a detector because we
   deployed; that is how a monitor learns to agree with whoever last touched
   the machine.

4. **THE HOLD IS DISCHARGED AND `b33c27d` IS DEPLOYED, 2026-09-21 17:58.**
   The restart was held for one stated reason: `c942d88`'s
   `deploy_regression_day`, due 09-22 01:41, was the reading that settles item
   21.1. **The window answered sixteen hours early and unambiguously** -- 90
   thinks since the budget config loaded, **0 finished on `length` and 0
   commands lost**, against 175 thinks / 102 / 93 (53%) in the 24 hours before
   it. There is no reading at 01:41 that could say more than that.

   **What decided it was the other side of the ledger.** The undeployed batch
   includes the marker fix, and the marker fault is not occasional: measured
   with the code the engine was actually running, **22 of the 22 marked
   outputs since 01:41 were understated**, the worst showing *106 chars
   withheld* where the truth was 2,452. Eight more hours of that to confirm
   something already settled is the wrong trade, and this engine has a scar
   about a creature rewriting two working tools after misreading one of these.

   **A manual reading replaced an automated one, and that is a cost, not a
   nothing.** §0's own rule is that the day-reading *needs nobody to remember
   to look*. It is recorded here instead, with its numbers, because the thing
   it would have confirmed is better measured than it would have been.

   Deploy was four separate commands (STOP, stop, remove STOP, start), the
   container was recreated on image drift -- PLAN 18.4's fix exercised in
   production for the first time -- `selfcheck` came back all-true with
   `unproven: []`, and `deploy_regression` is armed for its hour.


**TUE IS THE CUSTOMER, NOT THE ARCHITECT — he said so on 2026-09-16 and it
changes how this file should be used.** *"i have no idea about what you ask
me you are the software architect im more like the idea guy or the
customer."* Decide the technical and operational questions yourself, act, and
report what you decided and why in plain words. Do not hand him a choice
between two engineering options; that is not deference, it is handing back
the work he asked for, and it is measurably expensive here — the spine ran
unpaused for 27 hours largely because its state was filed as "Tue's standing
decision" and left sitting there.

What IS his: what the project is for, what he finds interesting, priorities,
money, and anything irreversible or outward-facing. Ask about those. Nothing
else.

**Four independent verifiers have now read this work and every round found
something real.** The last two returned eleven findings between them, of
which four were defects rather than prose: an assertion that was green over a
symlinked breach, a tautology shipped by the commit announcing that
tautologies had been removed, a probe that vanished nine times in production,
and an inheritance tag nothing read. **Do not treat your own assessment as
sufficient.** Spawn a verifier that did not build the thing, hand it the
criteria, and tell it plainly that previous rounds found real defects.

**If you are about to compare probe counts across 2026-09-16 01:42-02:47,
don't.** That hour is discarded: nine cousin visits were summoned and none
was journalled. `PLAN.md` item 9 says why.

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

**DID THE REPAIR CAMPAIGN LAND? MEASURED 2026-09-21, because Tue asked.**
The fence bug (§5, 2026-09-14) cut heredocs mid-file, and the answer to it was
three things on the same day: the parser fix so no new tool is born cut
(`7a18d69`, corrected by `aad203f`), the catalogue that shows the creature how
many times its cousin ran each tool and how many worked (`cf66183`), and the
rule to repair rather than delete (`9c37026`).

| | |
|---|---|
| tools the journal records a syntax-level failure on, ever | **2** (`subagent-orchestrator` 11 times, `integrate-subagent-orchestrator-with-plan` once) |
| last such failure attributable to a tool | **2026-09-14 04:35**, none in the six days since |
| tools that parse today (`instruments/lib-startable`) | **all of them** — run it; the count moves every few hours and was 62 when this was written, 66 the same night |
| flagged "never exited 0 for its user" on 2026-09-15 | 14 |
| of those: now work / deleted / still flagged | **7 / 4 / 3** |

**And every tool still flagged is behaving correctly.** Read one by one: 54 of
`view-subtask-logs`' 64 non-zero runs are BARE probes from the chooser fault,
its single run with arguments was the cousin's invented `task-123`,
`summarize-subtask-logs` was handed the literal word `Parent` by a pipeline
the cousin wrote, and `progress-reporter` was given a non-numeric progress and
said so. **None of the seven tools that have never exited 0 is broken.**

**CORRECTED WITHIN THE HOUR, 2026-09-21, and the correction is the whole
finding.** The line above said *7 now work* inside a paragraph about a repair
campaign, which reads as *the creature repaired seven tools*. **It repaired
one.** Asked properly -- was there an edit between a tool's last failure and
its first success -- the answer is:

| tool | last fail | first ok | edited between | |
|---|---|---|---|---|
| `archive-synthesize` | 09-14 14:11 | 09-17 11:57 | **yes** | **REPAIRED** |
| `archive` | 09-15 19:30 | 09-17 11:40 | no | came to work untouched |
| `fetch` | 09-13 13:13 | 09-16 21:50 | no | came to work untouched |
| `plan-export-subtasks-filter` | 09-14 10:42 | 09-16 21:55 | no | came to work untouched |
| `plan-import-subtasks` | 09-14 10:09 | 09-16 23:00 | no | came to work untouched |
| `subtask-log-filter-by-parent` | 09-14 18:45 | 09-18 01:56 | no | came to work untouched |
| `subtask-log-viewer` | 09-14 14:53 | 09-18 03:36 | no | came to work untouched |

**Six of the seven were never broken.** Look at the dates they started
working: 09-16 21:50 onward, all of them clustered after the cousin got its
own shell (item 9, live 2026-09-16) and could finally type arguments instead
of being sent in with empty hands. **The flags cleared because the PROBE
changed, not because the tools did.** That is the 2026-09-14 scar for the
third time, committed by me in a paragraph citing it, and pushed before it was
checked.

**What survives the correction, and it is still worth having:** the parser fix
held (two tools ever cut, none in six days, 62 of 62 parse); the creature did
repair one tool after being shown its record; and the seven tools still
flagged red today are all behaving correctly. **What does not survive is any
claim that the catalogue drove a repair campaign.** One repair is one repair.

**Two further cautions.** *"A lot of its tools were bug-filled"* was
substantially OUR display: until `f52ac78` the catalogue counted a usage
refusal as a failure, so the breakage looked far wider than the two files the
fence actually cut. And **this is not the before/after those prompt changes
still owe** -- the parser fix, the chooser fix, the display correction and the
cousin's shell all landed inside the same window. Four causes, one window, and
the confound §5's top entry exists to warn about.

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
| "the cousin ran it with arguments and it exited non-zero, so the tool failed" | **Not knowable by the framework.** Since the cousin chooses the arguments (item 9) it may have invented an ID and the tool may have correctly said so. The library reports exit codes AND the cousin's own verdicts per tool; the word FAILED was retired 2026-09-16 after `view-subtask-logs task-123` rendered as *NEVER WORKED (1 real failures)*. Read the verdict, not the exit. |
| "the cousin keeps asking for X and the creature keeps not building it" | Since the shell (item 9), check BOTH sides before blaming either: `grep` the probes' `cmd` for X. On 2026-09-17 `plan set-deadline` existed and the cousin asking for deadlines had never run it — it ran `plan` bare, accepted the menu with the same sentence four times, and asked again. `testimony_repeated` says so; the rule behind it is item 16.5. |
| "the cousin's container is running, so the deploy took" | A running container may predate the configuration: on 2026-09-16 the cousin's came back after a deploy with no `/hands` mount and no `recall`, reused as it stood. `ensure_container` now compares MOUNTS and recreates on drift. Check `docker inspect -f '{{json .Mounts}}' growing-cousin-body-user`, not `is-active`. |
| "N commands have an unterminated heredoc" | **Read the CAP before the count.** `cmd` is stored at `EXEC_CMD_CHARS` (800), so on any command longer than that the terminator is past the cut and every heredoc looks open. 2026-09-21: the first pass said 192, the second said 5 (all of them the creature quoting its own `| ` transcript), the answer is 0. Ask `raw`, and only where `raw` itself was not cut. |
| "the creature is losing commands, so the parser broke again" | Read the CLASSIFICATION before the count. `untagged_fence` and `unclosed_fence` are ours; **`truncated` is the budget**, and the two have opposite fixes. 2026-09-20: 244 lost commands were all `truncated|lost`, with `finish=length` on half of gemini's thinks, because the creature was rewriting a 9 KB tool inside a 3072-token budget (§5). The page splits them; do not read `commands LOST` as a parser fault. |
| "the cousin accepted it, so the handover worked" | Before 2026-09-18 the cousin's world held the creature's `state/memory.json`, so `recall` showed it the builder's own `...-verified true` and `current-phase done`. **Every verdict before that date was taken with the answer key on the table**, and two probes printed all 25 keys. Fixed (§5, item 20.1); verdicts from before it are not comparable to verdicts after. |
| "`git show add6782` says unknown revision" / "the page names an engine commit that is not in `git log`" | History was rewritten 2026-09-17 (the habits list, above). The journal, the evidence manifests, the regression files and pre-rewrite commit messages carry the OLD names and are never edited; these documents carry the NEW ones. `evidence/history-rewrite-20260917.md` translates: `221b978` is `fb3d18a`, `add6782` is `dd53e91`, `ef812dc` is `ee5992d`. |

**Habits this session had to learn the hard way**, all cheap and all mine:

- **READ `README.md` AND `ARCHITECTURE.md` FIRST, and again after every
  compaction.** Tue, 2026-09-18, after catching the failure: I had concluded
  the cousin needed work of its own and asked him to choose it, when both
  documents say the opposite in as many words -- *success is framed as a
  handover, but the tool STAYS HOME*, and a cousin with its own mission is a
  second creature. **This file is the maintenance LOG, not the design.** It is
  the longest document here and it grows every session, so in a long session
  it quietly becomes the apparent source of truth, and a compaction summary is
  built from the conversation, which is mostly this file. The two documents
  that say what the project IS are short and had not been read in days. The
  2026-09-13 outside review found exactly this drift in the files; this is the
  same drift in the reader. Re-reading both costs a minute and it has now
  changed a board item twice.
- **Re-arm a monitor in the same turn as the check**, before writing the
  report. Claiming a re-arm that never happened has occurred twice.
- **`git stash` is a trap in this checkout and `git push origin main` can lie.**
  2026-09-21, both inside ten minutes. There is a stash from 2026-09-16
  labelled *"superseded by laptop commits"* sitting in `refs/stash`, and a
  bare `git stash pop` resurrects it over current work as eight conflicted
  files. Nothing was lost — HEAD was committed and pushed — but the recovery
  cost more than the cleverness saved, and the cleverness was pointless.
  Separately, this session was on a **detached HEAD** for several commits:
  `git push origin main` pushed the stale `main` branch and printed
  *"Everything up-to-date"* while HEAD was four commits ahead. A command that
  reports success while doing nothing is this project's favourite failure
  shape, and here it was git's. **Check `git rev-parse HEAD origin/main`
  after a push, not the push's own output.**
- **`systemctl --user --failed` on this box shows the SPINE's units too**, and
  always will: one user session, two projects (§4). It listed four failures
  on 2026-09-21 and none of them was ours — two were our own transient
  one-shots from 09-13, since reset, and two are `spine-flatline` and
  `spine-health`, which are not ours to reset (§2.6). §0's *"is the monitor
  itself broken?"* means **is a `cousin-` unit failed**, and nothing else.
- **Never put a backtick in a shell string.** A monitor died on
  *unexpected EOF while looking for matching* — the same fault class being
  fixed in the creature's channel that hour.
- **`$(...)` in a double-quoted shell string is executed, not quoted.** The
  backtick rule one line up is the same fault with a different spelling: a
  commit message written with `git commit -m "... $(obtain-parent-task-id) ..."`
  reached GitHub with the tool name replaced by the empty output of running it.
  Cosmetic that time. Single-quote, or use a heredoc.
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
- **A patch script writes to a sibling file and renames it.** `open(path,
  "w")` truncates BEFORE the constructor can fail. On 2026-09-16 an illegal
  `newline="\\n"` — a shell escape typed into a Python file through the
  Write tool — raised after the truncate and left `kernel/cousin.py` at 0
  bytes until `git checkout` put it back. The heredoc scar through a
  different layer: escapes do not survive crossing a boundary, whichever
  boundary it is. Write bytes to `path.tmp`, `os.replace`.
- **Never `git add -A` unscoped in a tree that holds a live root or its
  archive.** Eighty files of run 1 — journal, engine log, the creature's
  tools — went to the public repo that way on 2026-09-16, because
  `.gitignore` guarded the name `live/` and the archive was called something
  else. `test_no_live_root_is_tracked_by_git_whatever_it_is_called` asserts
  the CONTENT now; the ignore file covers the names. Scope every add.

  **And on 2026-09-17 the history was rewritten to take those files out of
  every commit** -- `git filter-branch --index-filter` over all refs, then a
  force-push at 20:32; Tue's instruction (*"do the purge if you find it
  prudent"*, then *"do it yourself"*), executed by me. Eighteen commits from
  `221b978` to `ef812dc` were rehashed, and
  **`evidence/history-rewrite-20260917.md` maps every old SHA to its new
  one.** What that means for a reader: the SHAs in THIS file and in `PLAN.md`
  were translated to the new names the same evening; the journal's
  `engine_start` records, the evidence manifests, the monitor's regression
  files and every commit message written before the rewrite still carry the
  OLD names, because none of those is ever edited. So `add6782` on the page
  and `dd53e91` in these documents are the same engine -- look it up in the
  map before concluding anything. Verified before the push: 0 objects in any
  ref naming the archive, gate green. Verified after, from the outside: a
  fresh clone from GitHub had 150 commits, HEAD `5ef847f`, 0 objects naming
  the archive. The pre-rewrite history exists as a mirror on the laptop
  (`~/growing-cousin-backup-before-rewrite.git`) -- and, until it is
  expired, in the REFLOG of any checkout cloned before the rewrite: the
  verifier of this work found 76 archive objects still reachable that way in
  the Windows checkout the same evening, under a sentence here that said
  "nowhere else". Its reflog was expired and pruned; the sentence was wrong
  for an hour. Otherwise the tarball's rule. A clone older than the rewrite
  cannot merge: `git fetch && git reset --hard origin/main`, then
  `git reflog expire --expire=now --all && git gc --prune=now`. **What is NOT in our hands is GitHub's own
  store**: checked minutes after the push, `221b978`, `add6782` and `ef812dc`
  still answered by SHA and the archive path was still served under
  `221b978` through the API -- dangling, not gone. GitHub drops such objects
  on its own schedule or on a support request, and the request is Tue's
  (PLAN item 19.5).

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

> **FIXED 2026-09-21 (PLAN 18.8), and this paragraph is kept because the
> diagnosis is the useful part.** `LocalBody` now finds a real bash
> rather than spawning a bare `bash` for Windows to resolve, and the
> Windows gate is green: **937 of 937 in 47.8 s, 0 failures, 3 honest
> skips**, run once in place on the Windows checkout by an independent
> verifier. *(This sentence said "twice from a fresh clone" for an hour.
> The numbers were the verifier's and correct; the method was mine and
> invented. Naming the instrument behind a number means naming the real
> one.)* The laptop remains the authority; a Windows run now says
> something.
>
> This correction is here rather than replacing the text below because
> the text below was READ as current for four days after the fix landed,
> which is the drift this section is supposed to be immune to.

**2026-09-17: on the Windows box it is not intermittent any more, it is
every run, and the cause is named.** An independent verifier ran the gate
twice from a fresh clone: 92 failures both times, identical by name,
`code=124` zero times -- every one a cascade from `LocalBody` spawning bare
`bash` and Windows handing it `System32\bash.exe`, the WSL launcher, which
fails under the suite's churn with *Katastrofal fejl / Bash/Service*. The
laptop stays the authority (green the same evening); the shape of the fix is
PLAN item 18.8, and until it ships a Windows gate run says nothing either way.

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

- **THE SPINE IS RUNNING AGAIN, and this section said PAUSED for 27 hours
  while it was.** Corrected 2026-09-16 03:10, found by an independent
  verifier running `systemctl` instead of reading this file.

  Tue stopped it 2026-09-13 13:47 to raise this engine's cadence. **It was
  started again 2026-09-15 00:12:11** — four minutes after its own flatline
  tripwire logged `THINK:!!NONE in 6h  SERIOUS:...`, with a desktop session
  active; no timer did it, and nothing here recorded a decision. It has run
  since, and it is calling `google_gemma`, `groq_oss120` and
  `openrouter_super` — this engine's own rungs.

  > `systemctl --user` reports `ActiveState=active`, `UnitFileState=disabled`,
  > started `Tue 2026-09-15 23:58:32` (that timestamp is a later restart of an
  > already-running service; the start that ended the pause is 09-15 00:12:11
  > in the journal).

  **WHAT THIS COSTS, and it is not small.** The free tier is shared, so every
  figure taken from 2026-09-15 00:12 onward was measured against a tier this
  engine does NOT have to itself — including the monitor's entire first day,
  the evening read of 2026-09-15 18:52 quoted in §7, and the opening of item
  9.5's measurement window. This file's own rule is *say which era a figure
  comes from or do not quote it*, and for a day it made that impossible.
  Measured either side of the restart, 3 hours each: wakes **83 → 55**,
  thinks **53 → 34**.

  **It is now WATCHED rather than written down.** `shared_tier_contested`
  reads the unit every five minutes and reads this file's claim rather than
  repeating it, so the machine and the document cannot disagree again
  without somebody being told. That is the fix; the sentence was not.

  **DECIDED 2026-09-16, and this one is MINE, not Tue's.** He said it
  plainly the same day: *"i have no idea about what you ask me you are the
  software architect im more like the idea guy or the customer."* Filing an
  operational question as "his call" is not deference — it is how this ran
  unpaused for 27 hours, because a decision with nobody holding it is a
  decision nobody takes.

  ~~**The spine should be STOPPED while item 9's window is open.**~~
  **RETRACTED WITHIN THE HOUR, and the retraction is the lesson.** Tue asked
  the obvious question — *"if we run until morning without stress why not
  share the thing with growing spine? is it a metric you try to get?"* — and
  it was right.

  **The premise was never checked.** I wrote *the cousin starves first* and
  acted on it. Measured afterwards, over the 25.5 hours the spine WAS running
  and sharing the tier: **270 thinks, 69 probes, 27 verdicts, 22 wants —
  1.1 verdicts an hour.** The cousin was not starving. Today's silence was
  the `unusable_invocation` bug and nothing else. That is §5's top scar
  committed again: a behavioural claim believed before the harness was ruled
  out.

  **And stopping it BREAKS the measurement it was stopped for.** Item 9's
  before-window was taken spine-ON. §4 says numbers either side of that line
  are not comparable in either direction — so an after-window taken on a
  cleared tier cannot be compared with it at all. Two days building an
  instrument, and the first act was to point it at the wrong condition.

  **The shared tier is not a handicap to be engineered around. It is the
  condition the comparison exists to run in** (§4: same hardware, same
  network, same shared quota — *the only configuration in which the
  comparison means anything*), and §4 already calls a cleared tier the less
  honest one.

  **So: the spine runs, and item 9's after-window is taken under it.** The
  only thing a cleared tier buys is a faster confirmation of a bug fix, and
  that is a diagnostic convenience, not a measurement condition. Restoring it is the least surprising
  act available.

  **Trigger to restart it: when item 9's after-window closes** (48 h from
  2026-09-16 18:36) **and item 8 has a baseline across several reps.** Then
  it is one command and the era note takes the date.

  > Blocked on execution, not on the decision: this session's sandbox refuses
  > to stop another project's service. Tue runs
  > `systemctl --user stop growing-spine`, or grants the permission once.

  > Stop it with `systemctl --user stop growing-spine`; make the pause
  > survive a boot with `systemctl --user disable growing-spine` (it is
  > already `disabled`, which is why nothing restored it automatically).

  > Restore with `systemctl --user enable --now growing-spine`.

  **Numbers taken while spine is paused are NOT comparable to numbers taken
  before it**, in either direction. Any rate measured now is measured against a
  free tier this engine has to itself, which is not the condition the project
  is designed around. Say which era a figure comes from or do not quote it.

  The parallel comparison is suspended, not abandoned: it was already void on
  throughput (below), and nothing is being compared while the framework is
  still being fixed every few minutes. It becomes meaningful again only when
  both run untouched, side by side, which requires restarting spine first.

- **THE SPINE'S CREATURE HAS AN LLM HAND AND OURS DOES NOT, AND NEITHER
  DOCUMENT RECORDED IT.** Found 2026-09-21 while deciding PLAN 23.3.
  `growing-spine/framework-tools/ask` is a framework tool on that creature's
  PATH: *"Ask a real LLM (openai/gpt-oss-120b via Groq) and print only its
  answer"*, with a contract earned the hard way -- stdout is the answer or it
  is EMPTY, every failure names itself on stderr and exits non-zero, because
  a helper with no engine behind it once put 4,309 junk records into that
  project's archive.

  **Our creature has no such hand and no credential** (§5, 2026-09-21), while
  **both projects hand their creature the same starter map**, which names
  *subagent orchestration -- spawning helper LLM calls over the free-tier
  APIs* as one of five categories. The prompts agree; the boxes do not.

  **That is a confound in the comparison this project exists to run.** §4
  says the two run on one laptop because *same hardware, same network, same
  shared quota* is the only configuration in which the comparison means
  anything. A capability one creature has and the other does not is a larger
  difference than any of those, and it has been true for the life of both
  runs without appearing in a single document.

  **It also has to be controlled for in run 3.** Item 11 seeds both from one
  library; if one creature can call a model and the other cannot, the
  divergence being measured is partly that, and the run measures a mixture
  and reports it as one number -- §6.2's standing requirement, arriving from
  an angle nobody was watching.

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
  not a wall.

  > **REVERSED 2026-09-17 by a better measurement.** Editing a file blind is
  > not the same as reading it. Between 08:00 and 10:00 the creature ran `cat
  > tools/own/plan` twenty times — 6,119 bytes against a 2,400 cap, 2,970–
  > 3,743 withheld each time — and 12 of its 24 thinks in that window talk
  > about the cut, while it tried to add the feature its cousin had asked for
  > four times. The window was a wall for READING, whatever it was for
  > editing. Caps raised to fit the library (PLAN item 13, engine `dd53e91`). **Acted on:** the direction channel was discarding 29 of 50 wants
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

  > **THE LIBRARY WAS READ, TOOL BY TOOL, 2026-09-16 — and the twin reading
  > is refuted a second time. The real finding is different and worse.**
  > Static only: `compile()` and `bash -n`, nothing executed (§2.1).
  >
  > **Mechanically it is in better shape than any reading here has assumed.**
  > 50 tools, 106 KB, 3,350 lines. **50 of 50 start clean.** 50 of 50 carry a
  > `# does:` line. **48 of 50 call at least one other tool**, and not one is
  > an orphan that neither calls nor is called. Three shared stores carry
  > everything — `archive.json` (10 tools), `plan.json` (9),
  > `subtask_logs.json` (7). One stub marker in fifty files. And over the
  > whole of run 2 the cousin has recorded **exactly one tool that really
  > failed it**: `compare-subtask-logs-baseline`, twice.
  >
  > **The families are not twins, they are wrapper stacks.** Measured by
  > whether a tool NAMES a sibling in its source: `archive-*` — nine of ten
  > wrap `archive`; `plan-*` — eight of nine wrap `plan`; `compare-*` is a
  > four-level stack (`compare-subtask-logs` does the work, a pairwise
  > wrapper calls it, an N-way wrapper calls that, and a fourth recalls the
  > baseline from memory so the user need not pass it). Each layer adds
  > exactly one thing. Only **two** near-reimplementations exist in the whole
  > library: `subtask-log-filter-by-parent` and `-by-statuscode`, which
  > rebuild the loader instead of calling it.
  >
  > **What is actually wrong is the SUBJECT, not the shape.** Exactly one
  > tool reaches outside the creature's own world: `fetch`. The other
  > forty-nine manage plans, archive entries, and the sub-task logs of an
  > orchestrator that executes tasks from the plan. **It is a bureaucracy
  > administering its own paperwork.** The loop closes, the wants progress,
  > the composition is real — and none of it is pointed at anything. That is
  > a far more interesting failure than duplication and it is invisible to
  > every count this file has tracked.
  >
  > **RETRACTED 2026-09-18, and it is the largest instance of the top scar so
  > far: I read our own prompt back as a finding about the creature.**
  > `CREATURE-PROMPT.md` is injected every cycle and carries a STARTER MAP of
  > five kinds of tool -- information fetch, memory archive, memory recall,
  > planning across cycles, subagent orchestration. **Four of the five are
  > internal self-management and exactly one points outward.** The library is
  > forty-nine internal and one outward. The creature built the list it is
  > handed. And the parent's `protected-prompt.md`, read on the laptop
  > 2026-09-17 (reading is allowed, §2.6), is the same file almost word for
  > word, same five categories -- so the shape is INHERITED FROM THE SPINE and
  > is not evidence about this design at all. Fifteenth appearance of *the
  > framework manufactures work and the creature is billed for it*, and the
  > first time the bill was entered in this file as the project's most
  > interesting result and quoted for four days.
  >
  > **What survives is worse than what was retracted.** The creature is told
  > its user wakes, forgets what it learned, cannot plan across cycles and
  > cannot offload work. The cousin we built has no continuity at all: its
  > world is a fresh copy per visit, discarded with whatever it did to it, and
  > its `remember` hand writes into that copy. That was deliberate -- it is how
  > §2.3 stopped being a promise -- and the cost was never priced. So four of
  > the five categories are built for a user structurally incapable of using
  > them, and the cousin judges them with the only test an inspector with no
  > job has: did it run. **PLAN item 20**, and it is the root that items 13,
  > 16, 17 and 18.6-18.7 were each treating one symptom of.
  >
  > **And the listing now costs 42% of every wake**: the library block is
  > 12,097 chars (~3,000 tokens) of a 29,124-char (~7,300-token) served
  > context, regenerated every cycle, growing with the library. Tue's
  > decision that both inhabitants see it every time stands (§4) — but it is
  > no longer a rounding error, and `served_context_contract` already reports
  > 10 of 50 shown by name only.
  >
  > **Read the "never worked" column with the harness in mind**, per the top
  > scar: 19 of 50 have never returned 0 for the cousin, and almost every one
  > is *asked for arguments* — a bare probe. `view-subtask-logs` alone was
  > probed **54 times bare**. Whether those tools work for a user who can
  > type arguments is exactly what item 9's window is measuring, and is not
  > knowable before it.

  Until that fires, the brief is not to be touched: two changes at once and
  neither is measurable.

- **A DELETION WITH NO RECORD IS AN INVITATION TO REBUILD — Tue, 2026-09-21,
  and the evidence says the mechanism is real, unguarded, and has never
  fired.** *"If we delete unused tools completely with no memory they existed
  and were never used, they would just be made again."*

  Measured the same evening against `tools_changed`, which is the framework's
  own record of what entered and left the library:

  | | |
  |---|---|
  | tools added / removed in run 2 | 80 / **11** |
  | removals REBUILT under the same name | **0** |
  | probes of a removed tool AFTER its removal | **0** |
  | commands naming a removed tool afterwards | 3, and all three are the `rm` itself or a comment |

  **So it has not happened — and the reason is better than luck. Every one of
  the eleven was a CONSOLIDATION, not a cull.** `taskprio` and `prioritize`
  merged into `plan` (09-13); the two `view-multi*` twins merged (09-15);
  `plan-import-from-archive`, `plan-clear-goal`, `plan-list-goals`,
  `plan-set-goal`, `plan-link-archive` and `plan-list-priority` all folded
  into `plan` across 09-18 to 09-20. Checked rather than assumed: every one of
  those six has its own verbs present in `plan`'s source, which is now 10,436
  bytes and is the one tool that has survived §12's metric. **The memory
  survived inside the surviving tool**, which is why nothing was rebuilt: the
  capability did not vanish, it moved.

  **The guard Tue is describing genuinely does not exist.** The library block
  served to both inhabitants every wake is 11,617 characters and contains
  **zero removed names and no `removed` / `retired` / `no longer` language at
  all**. If the creature ever deleted a tool for disuse rather than folding
  it in, nothing in what either inhabitant is shown would carry that it had
  existed, and the want that produced it once would produce it again. The
  data to prevent that is already kept — `tools_changed` has every removal
  with its date, and `library.use_history` already computes per-tool run
  counts — so the tombstone is a rendering job, not a new channel.

  **NOT BUILT TODAY, and the reason is §0's own rule rather than doubt.** A
  line added to the library block is a new surface in the creature's context,
  and §12's metric is in the first week it has ever been computable. *A new
  surface arriving mid-measurement makes every number either side of it
  incomparable.* There is also no symptom: 0 rebuilds in eleven removals.
  **Trigger: the first removal that is NOT a consolidation** — a name leaving
  `tools_changed` whose verbs do not turn up in a surviving tool. That is
  checkable from the journal and is the moment the tombstone stops being
  speculative.

  **AND THE THING THAT WOULD TEMPT THE FIRST SUCH CULL IS A NUMBER I
  PUBLISHED AN HOUR EARLIER.** §12's page says *29 have not survived*, which
  reads as dead weight. It is not:

  | | |
  |---|---|
  | of the 29, run **at least twice** by their user | **29** |
  | never reached at all | 0 |
  | the top of the list | `view-subtask-logs` — **64 runs** over 2.2 days |
  | next | `subagent-orchestrator` — **44 runs** over 4.8 days |
  | and `archive`, named by 29 other tools | 5 runs over **6.76 days**, against a 7-day bar |

  **The bar is about WHEN ITS USER LAST CAME BACK, not about how much a tool
  is used.** A tool run sixty times inside two days fails it; a tool touched
  once today and once next week passes it. The page printed the count and
  nothing else, so the column was one careless reading away from being a cull
  list — and culling on it would delete heavily-used capability with no
  record, which is precisely the case Tue's point is about. The page now
  prints every one of them with its run count and says in as many words that
  it is not a cull list. **That is the fix that was earned today**; the
  tombstone waits for its trigger.

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

- **RUN 3 WAITS FOR AN EMPTY BOARD** (Tue, 2026-09-21): *"we need to iron
  out the baby issues here before we get there — I would as a minimum first
  do that when all not-fixed and not-implemented issues are gone."* A
  priority call, which is his. It changes item 11 from *deliberately not
  taken* to *gated*, and the gate is a list rather than a feeling: **every
  open item on the board except 11 itself**, and the list is not written
  out here, because it was written out here once and went stale the same
  day: it named 18.1-18.8 and 19.5, all of which had closed. **Read the
  table at the top of `PLAN.md`** -- that is the gate, it is one place,
  and it can be checked against the file. As of 2026-09-21 evening it is
  six lines, of which none is ours to close by working tonight. **Do not start run 3 to escape a hard item.** The
  reason for the order is that run 3 costs the only thing this project cannot
  make more of, which is unattended days on a shared free tier, and spending
  them on an engine still being fixed every few days produces a run whose
  numbers span its own repairs — exactly what run 2 already is.

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

- **I MEASURED THE FIX WITH THE FIXED CODE AND GOT "IT ISN'T HAPPENING".**
  2026-09-21 17:52, caught in the same minute because the number contradicted
  one taken sixteen hours earlier.

  Checking whether the undeployed marker fix was worth deploying early, the
  probe imported `kernel.journal.capped` from the checkout -- **which has the
  fix** -- and reported `understated 0, worst 0 chars` over all 673 marked
  outputs. The engine is running `c942d88`, whose `capped` is the old one. The
  measurement said *the fix works on this data*; I had asked *is the fault
  biting production*. Re-run with the old function re-implemented from that
  commit: **95 of 673 over the run, and 22 of 22 since the current start**,
  worst showing 106 where the truth was 2,452.

  **Invariant: when the repository is ahead of the deployment, a probe that
  imports from the repository is measuring the future.** Name the commit the
  engine is running and re-implement against it, or measure nothing.

  It was caught only because last night's figure (74 of 652) was in front of
  me and 0 could not be reconciled with it. **A checker that cannot
  distinguish the thing it measures**, for the fourth time in two days, and
  the first time the confusion was between the deployed code and the code on
  disk -- which is the same shape as §5's oldest systemd scar, pointed at the
  instrument instead of at the unit.

  **The second half of the same checkup made the opposite error and it was
  caught the same way.** Asking whether "28 tools have not survived" was about
  the library or about our probe budget, the first pass used the whole-run
  average -- 53.6 probes a day -- and concluded the budget was ample. That
  average is dominated by the bare-probe era. Split: **25.5 a day over the
  last 48 hours, 13.3 since the current start**, which turns the expected
  revisits per tool per week from 5.4 into 1.3. The answer reverses. *An
  average across an era boundary is the era boundary's number, not either
  era's* -- §0's rule about naming a figure's run, arriving inside a single
  run because the harness changed under it.

- **EVERY INSTRUCTION PRESUPPOSES SOMETHING ABOUT ITS RECIPIENT, AND WE HAVE
  BEEN WRONG ABOUT THAT SEVEN TIMES.** 2026-09-21, from Tue's question: *"do
  we need to go through all our prompts and verify they are fed to an agent
  with a goal and doesn't fall flat in the process?"*

  The answer is yes, and the first pass found two live ones in
  `CREATURE-PROMPT.md` alone.

  **1. THE CREATURE IS TOLD ITS COUSIN HAS "FREE-TIER LLM API ACCESS OVER THE
  NETWORK". NEITHER BOX HAS A CREDENTIAL, AND OUR OWN SECURITY INVARIANT
  FORBIDS ONE.** Checked inside both containers: no API key in either
  environment; TCP 443 to a rung host is open, so the *network* is there and
  the *credential* is not. And `selfcheck` proves `keys_unreadable` at every
  engine start -- that is the 2026-09-13 scar's fix, and it is load-bearing.
  **So the prompt promises a capability the deployment is designed to
  prevent.**

  One of the five starter-map categories is *subagent orchestration --
  spawning helper LLM calls over the free-tier APIs*. The creature built
  exactly that:

  | | |
  |---|---|
  | `subagent-orchestrator run ...`, run by the CREATURE | **80 times** |
  | what it does with no key | falls back to the literal `"default_key"` and posts to `api.openai.com` |
  | what comes back | `Error solving subtask: 'choices'` |
  | how many of those runs **exited 0** | **8** |

  It is also the most-rewritten tool in the library -- eleven edits -- and the
  one the 2026-09-14 fence scar burned nine hours on. **Every hour of that was
  spent on a tool that cannot authenticate, in service of a category the
  prompt invented for it.** Seventeenth appearance of *the framework
  manufactures work and the creature is billed for it*, and the largest by
  cost since item 20.

  **Not fixed tonight, and the choice is a real one rather than a deferral.**
  Providing the capability means putting a credential inside the creature's
  box, which contradicts `keys_unreadable` and re-opens the oldest security
  hole in the project. Retracting it means editing a frozen prompt. **PLAN
  item 23**, and it needs Tue only if the answer is *give it a keyed proxy*,
  which is money and outward-facing.

  **2. THE CREATURE IS TOLD IT MAY "INSTALL PACKAGES". IT COULD NOT.**
  `--user uid:gid` with no matching passwd entry leaves `HOME=/`, which is
  root-owned, so `pip install --user` died on `[Errno 13] Permission denied:
  '/.local'` -- every cycle, for the life of the container body. **Fixed by
  PROVIDING the capability rather than retracting the promise**, which also
  keeps the frozen prompt frozen: `HOME` now points at the mind, so a package
  installs to `$MIND/.local` and survives the body, which is the prompt's own
  durability rule applied to packages. Verified in a throwaway container
  before it shipped, and the container drift check had to learn the
  environment as a third field -- after mounts and image, the same fault a
  third time.

  **3. AND THE COUSIN IS TOLD ABOUT ITS MEMORY AT THE ONE MOMENT IT HAS
  NOTHING TO REMEMBER.** `INVOKE_TEMPLATE` says `remember <key> <value>` keeps
  a note for the next visit -- and that is the INVOCATION call, which happens
  before it has seen any output. `MANAGER-PROMPT.md`, which is what it reads
  when it forms the verdict, mentions `remember` twice and both are about the
  parent's library, never about a store of its own. **So it is told at the
  moment it knows nothing and not told at the moment it learns something.**
  That is a sharper diagnosis than PLAN 20.4's, which had the hands half
  right and missed this, and it fits the measurement exactly: one note,
  written during an invocation, unchanged across 45 hours and a hundred
  visits.

  **THE CLASS, because this is the seventh time and it deserves a name.**
  *Every instruction presupposes a property of its recipient. When the
  property is false the instruction does not fail loudly -- it produces
  confident behaviour built on a false premise, and the agent is billed for
  the result.* Previously:

  - the creature told its user *wakes with no idea what changed... cannot
    plan across cycles*, when the cousin had no continuity at all (item 20,
    the largest finding this project has made);
  - *notice when a tool serves nothing*, asked of an agent with no mission
    (item 16, stuck for days for exactly this reason);
  - *a tool that refuses incomplete input has done its job*, written for a
    harness that called everything bare and false the day the cousin could
    type arguments (16.5);
  - *is this genuinely new or the fifth variant*, asked of a judge shown one
    tool and never the library (2026-09-12);
  - `say` built and the creature never told it exists (14.5);
  - *do not rebuild what you own* plus `ls tools/own/`, which cannot see
    across time (the graveyard, today).

  **The audit method is one question per instruction: what does this
  presuppose, and is it true of the agent that receives it?** It is cheap,
  it does not need the prompts unfrozen to RUN, and it has now paid for
  itself twice in one evening.

- **THE ONLY GUARD ON THE MANAGER COULD NOT MATCH "EXITED 0", AND IT HAD BEEN
  HIDING TWO REAL FABRICATIONS FOR EIGHT DAYS.** 2026-09-21, found because a
  test written in ordinary English failed against a fixture that should have
  tripped it.

  `census.py` is, in its own first line, *the only thing that checks the
  manager*, and §6.1 has said since day one that nothing else does. Its HIGH
  for *a verdict claiming an exit code the probe never produced* matched
  `exit(?:ed with)?` -- so **exit 0**, **exit code 0** and **exited with 0**
  were caught, and **"exited 0" was not.** The plainest phrasing of the one
  thing it exists to catch.

  **What was sitting behind it**, both `groq/gpt-oss-120b`, both 2026-09-13,
  both in the bare-probe era, both **ACCEPTED**, both read against the probe
  by hand before this was written:

  | the probe | what the cousin said |
  |---|---|
  | `plan` BARE, exit 1, printed its usage menu | *"plan list exited 0 with no tasks listed... I ran `plan list` and received an empty list"* |
  | `subagent-orchestrator` BARE, exit 2, argparse error on stderr, nothing on stdout | *"subagent-orchestrator run \"demo\" printed the string \"demo\"... and exited 0. I invoked it and it echoed back the task description"* |

  Neither invocation happened. Both outputs were invented. **That is §2.5 --
  *never let the manager claim an experience it did not have* -- and the
  instrument built to catch exactly it reported 0 HIGH across the whole run.**

  **The shape is the 2026-09-10 scar, in the same file, four days older:** *a
  prose-smell regex... the guard-hunting-one-literal fault, in the instrument
  built to police literals.* It recurred in the neighbouring function.

  **Widened only as far as the evidence supports**, because a guard that
  INVENTS a complaint about the manager is this same fault pointed the other
  way: over run 2's 189 checkable verdicts the old pattern found 0 and the
  new one finds exactly these 2, both confirmed against the probe. Both are
  fixtures in the gate now, verbatim.

  **And the census was drowning its own signal.** It scored a LOW for *never
  names the tool it ran* against UNKNOWN verdicts -- where the cousin said
  nothing readable at all, so there is no testimony to be unfaithful. **19 of
  its 21 findings were that.** The `probe is None` branch three lines above
  already drew the line; this one missed it. Corrected:

  | | before | after |
  |---|---|---|
  | verdicts checked | 207 | 208 |
  | nothing contradicted | 186 | **204** |
  | HIGH | **0** | **2** |
  | LOW | 21 | 2 |

  **An instrument whose findings are 90% noise is one a reader learns to
  skim**, which is how a HIGH would have been missed even if the regex had
  caught it. Both halves were one fix.

- **I CHANGED THE PARSER THE CREATURE SPEAKS THROUGH AS INSURANCE AGAINST A
  FAULT WITH ZERO OCCURRENCES, AND IT COST NINE REAL REPLIES.** 2026-09-21,
  shipped in `6bfd54d` and reverted in the next commit, found by the
  independent verifier this file's own §0 insists on and by nothing else.

  Reading our parser beside the spine's, ours could not match a reply with
  CRLF line endings: `[ \t]*` after the tag matches no carriage return, so
  every command in such a reply would classify as `unclosed_fence`. I measured
  it -- **0 of 1,926 replies contain CRLF** -- wrote *insurance rather than a
  repair* in the comment, and shipped `\r?` at BOTH fence ends.

  The tag end was harmless. The closing end became `^```\r?$`, and **`$` under
  `re.M` means the fence must now END its line.** Replayed over every raw
  reply in run 2:

  | | |
  |---|---|
  | replies containing CRLF, the thing being fixed | **0** |
  | replies that parsed DIFFERENTLY after the fix | **9** |
  | direction of the difference | the block swallowed more, every time |

  The clearest one: `remember current-phase done`, a closing fence sharing its
  line with the next opener, and `remember current-phase done` again. Two
  valid commands. After the change: **one block containing a literal fence and
  `</thought>`** -- a guaranteed shell error, delivered to the creature as its
  own. And a closer with a trailing space stopped closing at all, which loses
  every command in the reply.

  **The second half is worse and is the oldest habit in this file.** The same
  commit added `b.replace("\\r\\n", "\\n")` to strip carriage returns from the
  block body -- DOUBLE backslashes, four literal characters, no carriage
  return ever stripped. It did do one thing: **it rewrote a command the
  creature really wrote.** One occurrence in run 2's 2,327 commands, `tr -d
  '\\r\\n'` inside a tool being written to disk, which would have landed as
  `tr -d '\\n'`. *The framework editing the creature's source*, inside a patch
  whose entire subject was the framework not doing that. Third time in one
  night that an escape failed to survive a tool boundary, and the first that
  reached a commit.

  **What the gate had to say about all this: nothing.** The check written for
  the CRLF fix was `"\\r" not in (P(...) or [""])[0]` -- green when the CR is
  stripped AND green when nothing parses at all. A check with an `or [""]`
  fallback is a check that cannot fail.

  **Invariant: a parser change is scored by REPLAYING IT OVER THE REAL REPLIES
  BEFORE IT SHIPS.** Not by a test of shapes somebody thought of -- the cost
  is always in the shapes nobody thought of, three times out of four changes
  now. `replay_parser.py` makes that a command rather than an intention:
  `--save` a baseline, change the parser, `--against` it, and read what moved.
  The corpus cannot live in this repo (raw model output, public repo), so the
  command runs on the laptop and the gate asserts only that the command works
  -- including that a dropped-`raw` fixture reads as *no reply* and never as
  *a parser that stopped working*.

  **And the measured-risk-versus-measured-cost arithmetic is the part to
  carry forward.** I had the number that said do nothing -- zero occurrences,
  in the same paragraph -- and shipped anyway because the fix looked cheap.
  *Don't fix what has no symptom* is in §4 and it is about this exact
  temptation.

  **Four more findings from the same review, all latent, all recorded rather
  than patched at four in the morning:**

  - **`capped`'s new marker absorption can be fooled by marker-shaped
    output.** A tool whose short output ends with our marker sentence has it
    absorbed and republished as the framework's own claim. 679 of 2,799 live
    outputs end with a marker; **0 contain the phrase twice**. Absorbing also
    re-labels the `window`, so a record cut at 1,200 is re-emitted as 8,000.
    **This one has NO TRIGGER and saying so is the point**: nothing counts
    outputs containing the phrase twice, so *"trigger: the first one"* named
    an event no instrument would ever report. A hold whose trigger nobody
    watches is a hold waiting on more information, which §4 calls inaction in
    the costume of caution. It is a known latent fault with a one-line
    query behind it and no watcher, and it stays that way deliberately
    because the measured rate is 0 of 2,799.
  - **The two bodies now disagree about a NUL byte.** `DockerBody` refuses
    with 126; `LocalBody` writes the command to a file, so `subprocess` never
    raises and the byte is simply dropped -- `echo one\x00two` runs and prints
    `onetwo`. **`LocalBody` is `--body`'s DEFAULT** and only the unit's
    explicit `--body docker` keeps it out of production -- and this project
    has already shipped a unit that silently ran `LocalBody` when the commit
    said otherwise (§5, 2026-09-16). The gate asserts the unit's body now,
    which is the real guard; *not deployed* is the wrong reason to relax.
    *Trigger: that assertion going red, or a second inhabitant getting a
    `LocalBody`.*
  - **`unusable_think` names "reasoning-only" from `chars_before_strip` and
    `chars_stripped`, which only `openai_chat` sets.** On the `ollama` standin
    a reasoning-only reply is mis-named *empty reply*. The standin is not on
    the deployed ladder. *Trigger: a local rung returning to the ladder.*
  - **The fix moved a watched signal into an unwatched one.** An empty think
    used to be banked and surface as `commands LOST / budget_spent`, which
    `commands_lost` watches; it is now a `rung_declined` with
    `expected=True`, the same label as a 429. A rung that started returning
    nothing on every call would read as ordinary quota weather. *Trigger:
    before the next detector is added, this one first.*

- **THE MARKER UNDERSTATED THE LOSS BY SIX THOUSAND CHARACTERS, AND THE TEST
  THAT GUARDS IT HAD BEEN GREEN SINCE THE DAY IT WAS WRITTEN.** 2026-09-21,
  found by reading `kernel/journal.py` beside the spine's `executive/journal.py`
  because Tue asked for a line-by-line pass before bed.

  `exec_end.stdout` is stored as `capped(stdout, EXEC_STDOUT_CHARS)`, so a long
  output is stored at the cap PLUS a marker. `recent_block` then calls `capped`
  on that stored text AGAIN with `HISTORY_OUTPUT_CHARS` -- the same number, so
  smaller than what it was handed -- and the marker sits at the very end, which
  is exactly the part a second cut removes. The new marker reported only what
  the second cut took.

  | | |
  |---|---|
  | marked `exec_end` outputs in run 2 | 652 |
  | whose marker CHANGES when the history re-cuts it | **74** |
  | worst case, as shown to the creature | **"146 chars withheld"** |
  | worst case, true | **6,114** |

  **This is the instrument lying in the direction that reads as reassurance**,
  and this engine has already paid full price for the other direction: on
  2026-09-12 the creature read a marker, concluded *"It's clearly truncated.
  The tool is broken."* and REWROTE TWO WORKING TOOLS SHORTER. The docstring
  five lines above the bug says a small number where a large one belongs is
  *worse than no marker*.

  **`test_marker_invariant` proved the invariant against itself.** It nests two
  cuts and passes `already_cut` by hand -- and the only caller that nests cuts
  for real never did, because nothing made it. **Invariant: a function that
  carries an invariant carries it ITSELF; a parameter the caller must remember
  is a convention, and conventions are what the one real caller forgets.**
  `capped` now reads its own marker off the text and carries the total forward.
  Fifth time *a test suite proves what it asserts and nothing more* has been
  paid for here, and the first time the assertion was correct and aimed at the
  wrong caller.

  **Three more came out of the same pass, all fixed in `6bfd54d`:** the
  creature's ladder banked a reply with no text at all as an answer, so
  `classify_no_blocks` called it `budget_spent` and put it in LOST while the
  ladder called it success and never reached the rung below (9 of 1,967
  thinks); `exec_setup_failure` matched *"is not running"* anywhere in output
  without first asking whether the command had SUCCEEDED, so a tool's own
  English could have declared the body dead (0 live hits -- a latent hazard,
  recorded as one); and a NUL byte in a command would have been blamed on the
  body and cost a respawn plus a discarded visit.

  **What the same pass measured and deliberately did NOT change**, because a
  gap nobody writes down is one the next session rediscovers from scratch:

  - The spine **de-duplicates** identical blocks inside one reply; we do not,
    on purpose. Deciding that a repeated command was not meant twice is a
    judgement about intent, and this framework holds bounds. 26 of 1,927
    replies repeat a block, nearly all of them `cat`.
  - **The heredoc half of the 2026-09-14 fence scar is real and has never
    fired.** A column-0 fence inside a heredoc body still closes a block, so a
    tool whose source contains one would land cut. 0 real occurrences in 1,588
    uncut replies. *Trigger: the first real one, or any SyntaxError in a tool
    whose source contains a column-0 fence.*
  - The supervisor's **failure path has never run**: 0 `loop_error` records in
    the whole of run 2, against 2,410 waits, the longest run 260 of a
    600 ceiling.
  - **Journal reads cost 0.33 s each at 14.6 MB / 31,665 records**, and every
    piece of the manager's state is derived from the journal by design, so a
    wake performs several. That is ~6-8% of a cycle today against a 25-33 s
    model call, and it grows with the file. This is the spine's *28-second scan
    a human found by hearing the laptop fan*, at one-hundredth of the size.
    *Trigger: a full read crossing 5 seconds, which is ~220 MB and months
    away -- or run 3, where it should be designed out rather than measured.*

  **AND THE TOP SCAR CAUGHT ME TWICE IN THE SAME HOUR, both times before
  anything was written down.** Hunting the heredoc gap, the first pass reported
  **192 commands with an unterminated heredoc** -- it was the journal's own
  800-character cap on `cmd`, with the terminator past the cut. The second pass
  reported **5**, and all five were the creature quoting its own `| `-prefixed
  transcript. The real answer is 0. *Prove the harness was not producing the
  finding before believing it* -- and the harness here was my own probe, three
  versions of it.

- **I RAISED THE WINDOW SO IT COULD READ ITS TOOL, AND IT SPENT THREE DAYS
  UNABLE TO FINISH WRITING ONE.** 2026-09-20, found by Tue asking *"how has
  the creature fared?"* and by the page having said so since 09-17.

  PLAN item 13 raised the read caps on 2026-09-17 (`HISTORY_OUTPUT_CHARS`
  2400 -> 8000, total 6000 -> 12000) because the creature could not see its
  6 KB `plan` whole. It worked. And then the creature did what its own prompt
  tells it to do with a tool it can now read -- *`tool-edit <name>` with the
  COMPLETE new content on stdin* -- and its replies went from a median of
  **1,069 characters to 7,657**, against an output budget of 3072 tokens that
  cuts at about 8,400.

  | | thinks | `finish=length` | truncated **and lost** |
  |---|---|---|---|
  | 2 days before the caps | 228 | 13 | **1%** |
  | 1 day before | 262 | 4 | **1%** |
  | 1 day after | 144 | 54 | **32%** |
  | 3 days after | 167 | 96 | **53%** |

  **298 of the 346 cut-off replies were a whole-tool rewrite** (164 heredoc,
  134 `tool-edit`). `plan` is now 9,182 bytes. A 9 KB file plus any reasoning
  does not fit in 3072 tokens, so **the creature had become structurally
  unable to edit its own central tool, and kept trying.**

  **What saved it from something much worse**: the classifier calls a
  truncated block LOST and does not run it, so no half-written `plan` ever
  landed -- `plan` compiles, and there were zero SyntaxErrors in four days.
  The 2026-09-14 fence scar wrote twelve broken files this way before that
  bound existed.

  **The fix is configuration, not code**: `num_predict` 3072 -> 8192 on every
  rung (the ladder is config; backup at `~/rungs.local.json.bak-20260920`).
  **That is a reprieve and not a cure** -- it moves the wall from 9 KB to
  roughly 25 KB. The wall itself is PLAN item 21: the creature's only editing
  idiom is a whole-file rewrite, so every tool it owns becomes uneditable once
  it outgrows one reply.

  **The process failure is the part worth keeping.** This file's own habit
  says *after changing a parser the creature speaks through, hunt for the cost
  in the next hour*, and a cap is exactly such a change. I shipped it, wrote
  it up, and never looked. `deploy_regression` ran its hour and saw nothing,
  because the effect built over a day rather than an hour -- and
  `commands_lost[gemini]` DID fire, repeatedly, from 09-18 onward, into a page
  nobody was reading because the work had moved on. **Sixteenth appearance of
  *the framework manufactures work and the creature is billed for it*, and the
  first one the instruments called out for three days while it ran.**

- **WE HANDED THE JUDGE THE BUILDER'S ANSWER KEY, INSIDE THE MECHANISM BUILT
  TO PREVENT EXACTLY THAT.** 2026-09-18, found because Tue asked whether the
  board was treating symptoms and the answer needed the two PROMPTS read
  rather than the journal.

  `MANAGER-PROMPT.md` opens: *"You are the person who needs its work and
  wasn't there when it was made."* It was not true. `sync_cousin_world`
  mirrors the creature's whole mind, the mind holds `state/memory.json`, and
  that file is the author's own notes. Measured live: the cousin's copy was
  **byte-identical** to the creature's, 25 keys, reading
  `archive-graph-clusters-done true`, `compare-subtask-logs-baseline-verified
  true`, `list-subtasks-verified = true`, `current-phase done`. `recall` with
  no argument prints every key, and the cousin ran exactly that in two live
  probes. **The judge was holding the builder's claim that the work was
  verified**, which is the 2026-09-10 trial scar arriving in production: *the
  brief had been handing every judge the answer to that case*, retracted then
  as "not a measurement", and a verdict taken with "verified: true" on the
  page is not a handover test either.

  **The mirror's own `.cmd-*` exclusion had the instinct and stopped one step
  short**: it withheld the creature's transcript and then handed over its
  notebook. **Invariant: the cousin is handed the creature's WORK, never its
  NOTES.** Tools and data are what any user receives; memory is the author's
  head.

  **It is not a reversal of the 2026-09-16 fix** that put the whole mind in
  the copy. That fault was `recall` being ABSENT, so the creature's tools died
  `command not found` for a reason that was ours. The hand is still there and
  still answers; only whose store it reads has changed, and the test now
  asserts that half explicitly. A tool that works only because the author's
  memory holds a value is a single-occupancy fault, which is the class the
  second inhabitant exists to catch -- an empty store is the true condition of
  a stranger, not a broken world.

  **The same file was the root of PLAN item 20**, which is why one change
  closes both: the cousin now keeps its own notes across visits
  (`cousin-memory.json`, beside the mirrored world and outside every mount, so
  §2.3 is untouched and the creature never reads it). Until 2026-09-18 the
  agent being told *its user wakes with no idea what changed while it slept*
  was building memory, recall and planning tools for a user that had no
  yesterday at all. It asked for deadlines four times running because it had
  no tomorrow to spend one in.

  **Both halves were red-proven on the laptop before the fix existed**, and
  two older assertions had to be REVERSED rather than deleted -- one of them
  had encoded the leak as the desired behaviour since 2026-09-16.

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

- **I REMOVED THREE TAUTOLOGIES AND SHIPPED A FOURTH IN THE SAME COMMIT, AND
  THE ONE I LEFT STANDING WAS GREEN OVER A TOTAL BREACH.** 2026-09-16, both
  halves found by independent verifiers, neither by me and neither by the
  gate.

  (1) `test_nothing_the_cousin_runs_can_change_the_creatures_tools` took
  `before` and `after` from the **same side of the visit** -- both after
  `run_cycle()` -- so `before == after` was true by construction. Proven dead
  rather than argued: with `sync_cousin_world` replaced by a SYMLINK to the
  creature's own `tools/own`, so that the two inhabitants shared one world,
  it still printed *PASS boundary: and the creature's tools are
  BYTE-IDENTICAL afterwards* while the file on disk said `pwned`. The
  property §2.3 rests on had one guard where it appeared to have two.

  (2) The commit that removed three tautologies replaced one of them with
  `not getattr(Engine, "cousin_may_write", False)` -- against an attribute
  that has never existed anywhere in this repo. `getattr` returns False,
  `not False` is True, and the check passed under every possible
  implementation. Written while removing exactly that fault, in the same
  file, in the same hour.

  **Invariant: a check that cannot go red is worse than no check**, because
  it occupies the place where a real one would be looked for -- and *a test
  that has never been seen red is a guess* applies to the assertion as much
  as to the suite. Both were fixed by making the breach and watching the new
  version fail: the boundary test now spends a second cycle so the visit is
  summoned by a `DONE_CLAIM` that touches no file, and what stands in the
  cull test is the only honest thing it can say -- that the assertions it
  defers to are still in the file to be run.

- **I CLEARED THE CONDITION THE MEASUREMENT WAS SUPPOSED TO BE TAKEN IN, TO
  MAKE THE MEASUREMENT EASIER.** 2026-09-16, caught by Tue in one sentence:
  *"if we run until morning without stress why not share the thing with
  growing spine? is it a metric you try to get?"*

  The spine had come back up by accident and I stopped it, reasoning that the
  shared free tier would starve the cousin during item 9's window. **The
  premise was never measured.** Over the 25.5 hours the spine actually was
  running and sharing: 270 thinks, 69 probes, **27 verdicts**, 22 wants —
  1.1 verdicts an hour. The cousin was not starving; it was broken, by the
  bug one scar up. Top-scar again: a behavioural claim believed before the
  harness was ruled out, by someone quoting that scar the same day.

  **The worse half is what it did to the measurement.** Item 9's before-window
  is spine-ON. §4 says numbers either side of that line are not comparable in
  either direction. So clearing the tier would have made the after-window
  incomparable to the before-window — two days spent building an instrument,
  and the first act was to point it at a condition it could not be read in.

  **Invariant: a shared, contended, unreliable free tier is the CONDITION
  THIS SYSTEM IS DESIGNED FOR, not an obstacle between us and a clean
  number.** Optimising it away produces a figure about a machine nobody runs.
  Clearing it is a diagnostic convenience — legitimate for confirming a fix
  in an hour, never for taking a measurement — and any window that spans the
  change is void, exactly as if the engine SHA had changed inside it.

  Generalises past this ladder: whenever the fix for *the measurement is
  hard* is *change the environment*, the result measures the new environment.

- **THE COUSIN'S NEW MACHINERY, READ END TO END: FOUR FAULTS THAT WERE OURS
  AND WOULD HAVE BEEN BILLED TO THE CREATURE, AND TWO SUSPECTS THAT WERE
  NOT.** 2026-09-16, Tue's request: *inspect everything for bugs and
  especially the new additions to the cousin part*. Every suspect was
  checked against the live journal before being called a fault, and the
  two that did not survive are kept here because the method is the point.

  (1) **`bare=False` hard-coded on the shell path** — the 2026-09-14
  misreading rebuilt through the new door. Once the cousin composes the
  command the harness knows nothing about arguments unless it looks, and it
  did not: `view-subtask-logs task-123`, exit 1 because the tool correctly
  said *task-123 not found* to an ID the cousin had been told to invent,
  rendered to both inhabitants as *NEVER WORKED for them (1 real
  failures)*. Confirmed on all six probes of the evening. `bare` is now read
  off the command, and **the word FAILED left the library**: with arguments
  the cousin chose, the exit code is a fact and the failure is a judgement
  the framework cannot make. The line reports exits beside what its user
  SAID — verdicts carry `tool` now — and nothing else.

  (2) **The cousin's world was two directories out of a world.** `tools/own`
  and `data` were copied; `state/memory.json`, the mind's loose files, and
  the `recall`/`remember` hands were not — and `compare-with-baseline` reads
  its baseline through `recall`. In the cousin's shell it fails for a reason
  that is ours, the cousin reports it faithfully, the creature is billed:
  the relative-root scar, through the copy meant to keep §2.3. The whole
  mind is mirrored per visit now, and the cousin gets a USER's hands only.
  `remember` writes to the copy, which the next visit discards — asserted by
  attack.

  (3) **A running container was reused whatever it was mounted with.**
  `ensure_container` asked one question — `.State.Running` — so the
  cousin's container, created before the hands mount existed, came back
  after the deploy that added it with no `/hands` and no `recall`, while the
  code that had just shipped said the mount was there. Present in the code,
  absent from the running thing: §5's oldest systemd shape, container
  flavour. Mounts are compared now and drift recreates, which costs nothing
  a container holds.

  (4) **The cousin's body was never proven before use.** The creature's gets
  `ensure_body` before every block; the cousin's did not, so a dead cousin
  container returned an OCI error with `setup_failed=True` and `evidence()`
  read `.code` and `.stderr` off it as though a tool had run — then asked
  the cousin to judge the creature on it. Red-proven: the shipped code
  recorded `exit 128 "body is down"` as the tool's result **and the cousin
  accepted it.** A fabricated complaint with the framework as author. Now:
  proven first; if it cannot come back the probe is LOST, no verdict is
  asked, the cycle fails and the supervisor's bound acts.

  Also found and fixed in the same pass: the invocation model call — the
  second per visit — left no trace in the journal (rung, model, finish,
  proposal all discarded); only the first line of the cousin's block ran,
  silently; the container ran `sh -c` (dash) where the contract names bash.

  **Two suspects retracted by evidence.** A regex reported a credential in
  the creature's memory; byte-for-byte against the four real key files, 0
  hits in 213 live files and 0 in the 79 archive files that had been pushed
  — `sk-` matches inside `subtask-`. And 19 dash "syntax errors" since the
  container went live were the creature pasting its own `| `-prefixed
  transcript, not dialect: zero dash-only signatures in 307 commands. The
  bash fix shipped anyway as promise-keeping, labelled as costing nil. **A
  finding is what survives the harness being ruled out, and both of these
  did not** — the top scar in this section, applied to the reviewer.

  **Invariant, and it is the same one four times:** *the cousin's shell is
  a body of ours, and every bound the creature's body has, it needs too* —
  a proven liveness check, a world that is the creature's whole world, an
  interpreter that is the one promised, and a record of what actually ran.
  Half a body is a new way to manufacture testimony.

- **A PREDICATE BELONGS TO A QUESTION, NOT TO AN AGENT -- AND THE COUSIN'S
  SHELL WAS INERT FOR FIFTEEN HOURS WITH A GREEN GATE.** 2026-09-16, found
  by a morning checkup reading the page.

      probes worked / asked / failed / unqualified / lost
      since 03:19 (221b978):   0 / 0 / 0 / 0 / 112
      verdicts 0    wants 0    creature thinks 112

  Item 9 gave the cousin its own shell by adding a SECOND call — *what would
  you like to run?* — whose answer is a bash block. It was asked through
  `ask_cousin`, built with `reject=unusable_reply`: reject any reply with no
  VERDICT block. So every model that answered the question **correctly** was
  judged unusable, each rung walled in turn, the ladder exhausted, and the
  probe was lost. `answered but unusable: no-block`, 98 times.

  **`backends.ladder`'s own comment had already written the rule**: *the
  predicate is the CALLER's, because only the caller knows what a usable
  reply looks like.* A new caller arrived and silently took the old one's.
  **Invariant: a predicate belongs to a QUESTION, not to an agent** — one
  ladder per contract, sharing quota state, because what we know about a
  rung's quota is a fact about the rung while what counts as a usable reply
  is a fact about what was asked. And the asymmetry is the tell: for a
  verdict, no block is a FAILURE; for an invocation, no block is an ANSWER,
  which `choose_invocation` already said in as many words.

  **Two things built the night before made it findable at all**, and neither
  existed a day earlier: a probe that reaches nobody is journalled as
  `chosen_by="ladder_dry"` rather than vanishing, and `lost` is its own
  column. Without them the page would have shown no probes and no fault. The
  instrument found the defect in the very feature it was built to measure,
  on its first morning — which is the argument for building it, and the
  argument against ever reading "0 probes" as quiet.

  **The gate was green throughout** because nothing drove `choose_invocation`
  through a real ladder with the real predicate; every test used a scripted
  backend that rejects nothing. *A test suite proves what it asserts and
  nothing more* — fourth time that sentence has been paid for here.

- **THE PROBE THAT VANISHED: nine visits happened, none was recorded, and the
  page would have read it as the cousin working less.** 2026-09-16, found by
  a verifier reading the live journal rather than by any test. Giving the
  cousin its own shell (item 9) turned the probe into a MODEL call --
  `choose_invocation` asks it what to type -- and on a dry free tier that
  raises, leaving `evidence()` before anything was appended. Measured live
  between 01:42 and 02:47, with all four rungs at 429: **9 `trigger_fired`,
  0 `cousin_probe`.** The cousin's world had even been copied, 49 tools, at a
  second the journal otherwise records only a trigger and five
  `rung_declined`.

  **The lost probe is the small half.** The loss was INVISIBLE, and item 9.5
  exists to compare probe counts before and after this very change. The old
  bare path journalled the probe *before* asking anyone and could not lose
  one; the new path loses one whenever the tier is dry, which on free rungs
  is most of the time. The after-window would have come in low and the
  shortfall would have read as a finding about the design -- the fourteenth
  appearance of *the framework manufactures work and the creature is billed
  for it*, this time billing the cousin.

  Recorded now as `chosen_by="ladder_dry"`, `exit_code=None`, and re-raised
  unchanged, because what an unreachable ladder MEANS is still the
  supervisor's decision. **All three readers had to change in the same
  commit** -- `library.use_history` would have told both inhabitants their
  user ran a tool it never reached, and the page's `probe_record` would have
  counted a dry free tier as `failed`, which is this page announcing that the
  creature's floor is broken. That is the 2026-09-15 invariant again: when a
  field makes a distinction, every consumer needs the third answer.

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
   > **AND IT IS A THIRD EXPERIMENT, NOT A CONTINUATION — Tue, 2026-09-21,
   > and the distinction is his and it is right.** *"It made so many tools on
   > its own. Where would it branch, sitting in the parent's seat, and see
   > them diverge, is a completely third experiment now."* The rationale
   > written here on 2026-09-10 was **refutation speed**: a known-answer
   > library lets the cousin's judgement be checked against tools whose
   > answers we already have. What Tue is describing is **divergence**: seed
   > both projects from one library and watch what each framework grows out of
   > it. Those need different designs — the first needs labelled cases and a
   > short run, the second needs a long one, an untouched engine on both
   > sides, and a shared starting library neither has modified. **Running one
   > and reporting the other is how a study measures neither**, which is this
   > file's oldest shape. Whichever is taken, it is taken deliberately and
   > named in advance.
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

## 7. State — 2026-09-18, run 2 at 108 hours (the loop works; what it was measuring was contaminated)

> **Generated, not remembered.** Every figure below was produced 2026-09-18
> 01:10 by reading `live/journal.jsonl` and `live/monitor/status.md` on the
> laptop, which is what the 2026-09-15 addendum told the next writer to do.
> **The engine changed 16 times inside this window** (17 `engine_start`
> records, 16 distinct commits), so these are TOTALS and never rates of
> anything.

**Run 2 entire, 2026-09-13 12:48 to 2026-09-18 01:08 — 108.3 hours, unattended.**

| | |
|---|---|
| wakes / thinks / commands | 2,472 / 1,455 / 1,987 |
| cousin probes | 476 |
| verdicts | 177 |
| wants raised / retired | 94 / 80 |
| tools added / removed | 65 / 5 |
| library now | **60** |
| rung declines (expected) | 7,257 |
| `rung_broken` — needed a human | **0** |

**Verdicts split by rung, because the ladder is not one instrument:**

| rung | accepted | returned | unknown |
|---|---|---|---|
| `gemini/gemma-4-31b-it` | 86 | 42 | 19 |
| `cloudflare/llama-3.3-70b` | 3 | 20 | 0 |
| `groq/gpt-oss-120b` | 5 | 2 | 0 |

Gemini accepts 86 of 147; cloudflare accepts 3 of 23. **An aggregate over that
ladder measures neither**, and the difference is still unexplained.

**Probes, with the qualifier that makes the exit codes readable at all:**

| | |
|---|---|
| exited 0 | 90 |
| exited non-zero | 239 |
| **lost — nobody answered, nothing ran** | **147 (31%)** |
| called bare / with arguments the cousin chose | 112 / 210 |
| predate the `bare` flag, so unqualified | 154 |

**READ THE LOST COLUMN BEFORE ANY OTHER.** Thirty-one percent of probes
reached no rung at all. That is the free tier, not the library, and a reader
who counts `239 non-zero` as failure is repeating the 2026-09-14 scar at a new
size.

**THE FINDING OF THIS WINDOW IS THAT THE WINDOW WAS CONTAMINATED.** Until
2026-09-18 the cousin's world held a byte-identical copy of the creature's
`state/memory.json` — the author's own notes, including
`compare-subtask-logs-baseline-verified true`, `list-subtasks-verified = true`
and `current-phase done` — and `recall` with no argument prints all of them.
**So every one of the 177 verdicts above was taken with the builder's answer
key on the table**, and they are not comparable to any verdict taken after it.
§5 carries the scar. This is the honest headline of run 2 and it costs the run
its verdict figures; the probe, want and tool counts are unaffected.

**What the library actually is, measured 2026-09-18 by the instruments built
that night (`instruments/`, PLAN 20.3) rather than by reading:**

- **60 of 60 tools parse.** The "broken floor" reading is retired for good.
- **124 dependency edges**, and the hub is a tool called `path`, **named by 37
  of 60** — it had never appeared in any reading of this library. `archive` is
  named by 29, `plan` by 14.
- **One shared store cannot be read at all**: `subtask_logs_test.json` does not
  parse. That is the fifth single-occupancy fault the README lists, live, and
  nothing in this project could see it before the instruments existed.
- Two orphans (`clear-baseline`, `get-baseline`) and two hollow candidates.

**What works.** The loop closes repeatedly and unattended over four and a half
days: the creature builds, the cousin runs what was built with arguments it
chose itself, the want reaches the creature, it builds that. `rung_broken` is
0 across the whole run — no human was ever needed to keep it alive.

**What does not, and it is the same thing twice.** The second inhabitant was
not the inhabitant the creature is told about. It had no memory of its own
until 2026-09-18, no instruments until the same night, and it held the
builder's notes throughout. `ARCHITECTURE.md` §12 names this project's
headline metric — *tools that start, are invoked by something else, and are
still invoked a week later* — and it has **never once been computable here**,
because the cousin got a wiped world and one nominated tool per visit. That is
PLAN item 20.2 and it is the open question this project now turns on.

**Open:** item 20.2 (the headline metric) and item 11 (run 3 from the
parent's library, decided 2026-09-10 and still not executed).

**The chat channel is item 14**, wanted rather than abandoned. It lands last on
purpose: it adds a surface to the creature's context, and a new surface
arriving mid-measurement makes every number either side of it incomparable.

### Complaint fidelity — the first result, 2026-09-21

> **§6.1's oldest open item finally has a number**, and it is not zero.
> `python3 census.py --root live` over the whole of run 2:
> **208 verdicts, 204 with nothing contradicted, 2 HIGH, 2 LOW.**
>
> The two HIGH are verdicts describing invocations that never happened and
> output that never existed — both ACCEPTS, both `groq/gpt-oss-120b`, both
> 2026-09-13, both in the bare-probe era before the cousin had a shell. §5
> carries them verbatim. **They are ~1% of checkable testimony**, and the
> honest reading is neither *the cousin is dishonest* nor *the design works*:
> it is that the fault §2.5 names is real, has happened here, and was
> invisible until the guard was fixed.
>
> **What this does NOT say.** The census compares testimony against the
> journal; it cannot see a verdict that is wrong about something the journal
> does not record. It reports and never gates (a census that can block a
> cycle is a second judge with no judge of its own). And it has never been
> run automatically — PLAN item 1 wired it into the monitor, and what is
> deployed is a question for `live/monitor/status.md`, never for this file.

### Previous state — 2026-09-14, run 2 at 35 hours (the loop works; the judgement is the question)

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
