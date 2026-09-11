#!/usr/bin/env python3
"""think.py -- ask the creature, and be honest about what came back.

The whole point of this module is one parent finding, copied rather than
replaced because it is a MEASUREMENT and not an approximation of judgement:

> Do not record "proposed no commands" without checking. An unclosed fence or a
> `finish_reason=length` means commands WERE proposed and the budget ate them.
> 21 of 60 `exec_skip`s were that, and every downstream reader had been counting
> them as model quality.

Same shape as the cousin's mute-refusal bound: *never assert something you did
not check.*
"""
import re

FENCE_RE = re.compile(r"```(?:bash|sh)?\s*\n(.*?)```", re.S)


def parse_blocks(text):
    """Every fenced bash block, in order. Empty blocks are dropped."""
    return [b.strip() for b in FENCE_RE.findall(text or "") if b.strip()]


def classify_no_blocks(text, finish_reason=None, completion_tokens=None):
    """WHY were there no commands? Three different answers, three fixes.

    Returns (reason, detail). Never collapses them into one label, because a
    checker that cannot distinguish the thing it measures reports a
    clean-looking wrong number rather than an error.
    """
    text = text or ""
    if not text.strip():
        # An empty reply that consumed its whole budget is a FAILURE, never an
        # answer: the model spent everything and delivered nothing, which
        # otherwise registers as a successful call and never walls a rung.
        if finish_reason == "length":
            return "budget_spent", (
                "empty reply, finish_reason=length, %s tokens generated: the "
                "model spent its whole allowance and returned nothing"
                % (completion_tokens if completion_tokens is not None else "?"))
        return "empty_reply", "the model returned nothing at all"
    if finish_reason == "length":
        return "truncated", (
            "the reply hit the token ceiling; commands were LOST, not absent")
    if text.count("```") % 2 == 1:
        return "unclosed_fence", (
            "the reply ends on an unclosed fence; commands were LOST, not absent")
    return "no_command", "a complete reply that contains no command"


LOST = ("truncated", "unclosed_fence", "budget_spent")


def commands_were_lost(reason):
    """True when the creature DID propose work and the channel destroyed it.
    Counting these as 'proposed nothing' is what made a budget problem look
    like a quality problem for months."""
    return reason in LOST
