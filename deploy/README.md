# Deploying Growing Cousin

It runs on the **same Linux laptop as Growing Spine** (Tue, 2026-09-12). That is
not convenience — it is the only configuration in which the comparison means
anything. Same hardware, same network, same shared quota. On different boxes no
latency or throughput figure from the two projects is comparable, and the
project exists to compare them.

**They share the box and nothing else.** Separate directory, separate journal,
separate systemd units, no shared volume, no shared file. `CLAUDE.md` §2.6.

## What changes on the laptop

**The local standin rung is gone.** A 15-year-old laptop cannot run
`gemma4:12b`, so the deployed ladder is free-tier only and there is no floor
when a rung 429s — the cycle fails, the supervisor backs off, and it tries
again later. That is slower and gappier than a development run here, and it is
also **more honest**: the standin's presence is precisely how a number gets
quoted later as though it came from the real rung.

The consequence for maintenance: **fast multi-cycle experiments are no longer
possible on the deployed box.** Anything needing many cycles quickly has to be
run against a local model on a development machine first.

## Install

```bash
cd ~ && git clone https://github.com/Tubifix77/growing-cousin.git
cd growing-cousin && python3 -m pip install --user PyQt6      # observer only
```

Write `rungs.local.json` and `rungs.cousin.local.json` from
`rungs.example.json`. Both are gitignored. They name a `key_file` — a path to a
credential **outside this repo**. No key ever goes in the repo or in the spec;
the repo is public.

Drop the local standin rung from both files: there is no ollama on that box.

### Credentials, and the one coupling this creates

Done 2026-09-12: the two credentials this engine uses were copied out of the
spine's `config.yaml` into `~/keys/*.key`, mode 600. The spine's config was
read and never modified, and the values were never printed — the parent's rule
is *grep that file for the one field you need; never dump it*.

They are **copies on purpose.** Pointing this engine at the spine's config would
make the two share a file, which §2.6 forbids for good reason: they are supposed
to be independent systems that happen to share a box.

> **The cost, and it is real: rotate a key in the spine's `config.yaml` and the
> copy in `~/keys/` goes stale.** This engine will then wall that rung and say
> so in the journal (`rung_error … credential rejected`), but nothing will
> connect the two events for you. If a rung starts refusing for no reason, check
> whether the spine's key changed.

```bash
mkdir -p ~/.config/systemd/user
cp deploy/*.service deploy/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now cousin-engine cousin-observer
systemctl --user enable --now cousin-vitals.timer cousin-monitor.timer
loginctl enable-linger "$USER"      # so it survives logout
```

## Running it

| | |
|---|---|
| stop after the current cycle | `touch ~/growing-cousin/live/STOP` |
| start again | `rm ~/growing-cousin/live/STOP && systemctl --user start cousin-engine` |
| watch | `journalctl --user -u cousin-engine -f` or the observer window |
| **is it healthy? read this first** | `cat ~/growing-cousin/live/monitor/status.md` |
| what changed since I last looked | `tail ~/growing-cousin/live/monitor/alarms.jsonl` |
| regenerate the page now | `cd ~/growing-cousin && python3 -m monitor status --root live` |
| what it has been doing | `python3 census.py ~/growing-cousin/live/journal.jsonl` |
| the evidence pack for a run | `python3 -m monitor pack --root live --out ~/growing-cousin-evidence --run run-2` |

**Stop with the file, not with `systemctl stop`.** The file lets the cycle in
flight finish; `systemctl stop` kills it mid-cycle and throws that work away.

The stop file is also honoured at START-up: while it exists the engine refuses
to run and says so. A reboot or a `systemctl restart` therefore cannot quietly
undo a deliberate stop.

`Restart=on-failure`, never `always`. The loop exits **0** both when it was
asked to stop and when a run of consecutive failures ended it; restarting either
would defeat the bound. A crash loop here is billed to the spine's quota.

## Reading the monitor

`cousin-monitor.timer` runs `python3 -m monitor status` every five minutes and
writes **`live/monitor/`** — for the helper on the other end of an ssh session
and for the next session that should re-derive nothing:

| file | what it is |
|---|---|
| `status.md` | the page: alarms first, then what it cannot tell, weather, counts per window **each naming its engine**, the library with its run record, the latest wants / verdicts / skips |
| `status.json` | the same, for a program |
| `alarms.jsonl` | one line when a finding **enters** or **leaves** ALARM — nothing between. `tail` it to see what changed since you last looked |
| `regression/<sha>-<start>.md` | written **once** per engine start, an hour in: the hour after against the hour before, on the correctness indicators |
| `state.json` | the runner's memory (last states, since-when); derived, delete it and it rebuilds |

Every finding is one of **OK / ALARM / CANNOT_TELL / INFO** — a detector with
too few events says so rather than reporting OK. Only an ALARM that needs a
human makes the run exit 1, so `systemctl --user --failed` says exactly when to
look. The unit is read-only over everything but `live/monitor` (`PrivateUsers=yes`
makes that real), and nothing it produces is shown to either inhabitant.

Each detector is proven against a slice of the real journal where its scar
happened — `tests/fixtures/journal/`, replay one with
`python3 -m monitor replay tests/fixtures/journal/<name>.jsonl`.

## If something looks wrong

Read `live/monitor/status.md`, then `CLAUDE.md` §1. The short version, and it has been right four times
out of four: **before believing a behavioural finding about either agent, prove
the harness was not producing it.** Twice now, a creature that appeared to be
building duplicate tools was actually a creature responding rationally to a
framework that had broken its work.

## What needs a restart, and what does not

Asked 2026-09-13 and worth not re-deriving. The engine is one long-lived Python
process: it imports `kernel/` once and reads its briefs and ladder specs once,
in `main()`, before the loop starts.

| changed | picked up | why |
|---|---|---|
| `kernel/*.py`, `run.py` | **restart** | imported once at startup |
| `CREATURE-PROMPT.md`, `MANAGER-PROMPT.md` | **restart** | read once in `main()` (`run.py:156-158`) — the creature's identity is SERVED from memory every wake, not re-read |
| `rungs.local.json`, `rungs.cousin.local.json` | **restart** | `load_spec` runs once (`run.py:178-179`) |
| `deploy/*.service`, `*.timer` | **`daemon-reload` + restart** | and copy it to `~/.config/systemd/user/` first — editing the repo copy alone changes nothing |
| `live/context.md` (the wants) | **live** | the cousin writes it, the kernel re-reads it every wake. This is the whole point of "the manager writes the context, the kernel serves it" |
| `live/journal.jsonl` | **live** | append-only; `vitals.py`, `census.py` and the observer all read it while the engine runs |
| `tools/own/*` | **live** | the creature's own world, discovered per cycle |
| `monitor/*.py` | **live** (next timer run) | the monitor is a `oneshot`; every run imports afresh. `vitals.py` and `census.py` likewise |
| `*.md` docs, `tests/`, `LICENSE` | **never** | the engine does not read them |

**Restarting is cheap but not free:** `systemctl --user restart` kills the cycle
in flight and throws it away. `touch live/STOP` lets the current cycle finish
first, which matters when a rung call is in progress and the free tier is thin.

**Before claiming a change needs no restart, check.** On 2026-09-13 a "docs
only" commit also touched `run.py`; comparing the two revisions' ASTs with
docstrings stripped showed the only executable difference was an argparse help
string, so it genuinely needed none — but that was verified rather than assumed.
