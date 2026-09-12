---
name: defect-ledger
description: Every defect named in a turn must end that turn with a disposition — fixed, with evidence, or explicitly deferred. Use when finishing a piece of work, reporting status, summarising what was done, answering "is it done", or whenever about to name a problem and continue past it. Fire it especially when the honest report is "I found X and moved on" — that is the exact shape it exists to interrupt.
---

# The defect ledger

## The invariant

**A defect that is named must be dispositioned in the same turn.** Fixed, or
deferred out loud. There is no third state where something was mentioned and
neither of us wrote down what happened to it.

## Why this exists and not the obvious alternative

The obvious rule is *"never stop while a known bug exists."* Do not adopt it. It
does not ban the bug, it bans the report — it makes KNOWING expensive, so the
pressure lands on the cheapest available escape, which is softer language.
*"A real defect I haven't fixed"* becomes *"one small thing worth a look
sometime"*, the turn ends anyway, and the reader is now worse off than before
the rule existed.

This is a known failure shape, measured in this repo: **any field that gives a
shortfall a comfortable home will be used to avoid refusing.** A locked door is
such a field. So the door is not locked. Deferral is always available, costs one
line, and needs no permission.

What is forbidden is the silence.

## The two dispositions

**FIXED** — proved by an actual edit in this turn, not by saying so. *"I fixed
it"* is testimony; the tool call is the event. That asymmetry is not pedantry —
it is the same check `census.py` runs against the cousin, and it exists because
testimony about your own work is the one kind nobody else is auditing.

**DEFERRED** — a line beginning `DEFERRED:` naming what is being left and why.
Good deferrals are specific and carry a trigger:

> `DEFERRED: the 40-cycle confirmation run — the A/B is tighter evidence for
> this question, and a long run needs the GPU free. Trigger: next time nothing
> else is queued on it.`

A deferral is not an apology and not a failure. Most defects *should* be
deferred. Scope discipline is good; silent scope discipline is not.

## What counts as naming a defect

Anything a reader would act on: something does not work, is stale, is a real
bug, still fails, needs fixing, was left unfixed. Including — especially — when
it appears at the end of good news. *"Gate is green, and separately there's a
thing I noticed"* is the precise construction this catches, because the green
is doing the work of making the thing sound small.

## The honest note

Prose asking you to police yourself has the same weakness as a manager judging
its own testimony, which is the fault this whole project exists to instrument.
So this skill is not the enforcement. `.claude/hooks/defect_ledger.py` is a Stop
hook that blocks the turn mechanically, and `test_defect_ledger.py` proves it
fires AND proves it stays quiet on ordinary work.

This file is why. The hook is whether.

Run `python .claude/hooks/defect_ledger.py --report` to see what it has actually
been doing, rather than what it was meant to do.
