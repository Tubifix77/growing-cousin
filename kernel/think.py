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

# **THE TAG IS REQUIRED.** `CREATURE-PROMPT.md` states the contract twice, and
# an optional tag here contradicted it both times: line 54 says *"To DO anything
# you MUST write executable ```bash blocks"*, and the prompt teaches the tool
# header using a BARE fence as an example that is plainly not a command.
#
# 2026-09-13, live, found in a raw think reply the cycle after `raw` began being
# journalled: the creature quoted a tool's OUTPUT in a bare fence while
# reasoning about it -- "Tasks sorted by priority (Goal: ...)" -- and the
# framework ran it as a command. Exit 2. Then, in the very next reply, it read
# that manufactured failure in its own transcript and concluded *"This happened
# because the cousin probably copied the output of a tool and tried to run it
# as a script."*
#
# So the framework invented work, billed the creature for it, and the creature
# built a FALSE BELIEF ABOUT ITS USER out of the evidence. Eighth time this
# class has appeared here, and the first time it has reached one agent's model
# of the other.
#
# The creature was following its contract exactly. The parser was not.
FENCE_RE = re.compile(r"```(?:bash|sh)[ \t]*\n(.*?)```", re.S)

# Any fence at all, tagged or not -- used ONLY to explain an absence, never to
# execute. A reply whose only fences are untagged used to run and now does not,
# and that difference has to be VISIBLE rather than silent: a change that
# quietly stops doing something is indistinguishable from a model that stopped
# asking for it.
ANY_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def parse_blocks(text):
    """Every ```bash (or ```sh) block, in order. Empty blocks are dropped.

    An untagged fence is NOT a command. The creature is told to mark its
    actions and it does; text it merely quotes is not made executable by
    sitting between backticks.
    """
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
    if ANY_FENCE_RE.search(text):
        # Fenced text, but nothing marked as an action. Its own reason, so a
        # reader can tell "said nothing" from "quoted something and ran
        # nothing". Three causes have been collapsed into one label in this
        # project before and each had a different fix.
        return "untagged_fence", (
            "the reply has fenced text but no ```bash block; nothing in it was "
            "marked as a command, so nothing was run")
    return "no_command", "a complete reply that contains no command"


LOST = ("truncated", "unclosed_fence", "budget_spent")


def commands_were_lost(reason):
    """True when the creature DID propose work and the channel destroyed it.
    Counting these as 'proposed nothing' is what made a budget problem look
    like a quality problem for months."""
    return reason in LOST
