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

```bash
mkdir -p ~/.config/systemd/user
cp deploy/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now cousin-engine cousin-observer
loginctl enable-linger "$USER"      # so it survives logout
```

## Running it

| | |
|---|---|
| stop after the current cycle | `touch ~/growing-cousin/live/STOP` |
| start again | `rm ~/growing-cousin/live/STOP && systemctl --user start cousin-engine` |
| watch | `journalctl --user -u cousin-engine -f` or the observer window |
| what it has been doing | `python3 census.py ~/growing-cousin/live/journal.jsonl` |

**Stop with the file, not with `systemctl stop`.** The file lets the cycle in
flight finish; `systemctl stop` kills it mid-cycle and throws that work away.

The stop file is also honoured at START-up: while it exists the engine refuses
to run and says so. A reboot or a `systemctl restart` therefore cannot quietly
undo a deliberate stop.

`Restart=on-failure`, never `always`. The loop exits **0** both when it was
asked to stop and when a run of consecutive failures ended it; restarting either
would defeat the bound. A crash loop here is billed to the spine's quota.

## If something looks wrong

Read `CLAUDE.md` §1 first. The short version, and it has been right four times
out of four: **before believing a behavioural finding about either agent, prove
the harness was not producing it.** Twice now, a creature that appeared to be
building duplicate tools was actually a creature responding rationally to a
framework that had broken its work.
