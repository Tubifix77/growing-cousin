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
# **ANCHORED TO COLUMN 0, both ends.** A fence opens or closes a block only
# when it starts a line -- which is what markdown means by a fence, and what
# the creature's own prompt shows it.
#
# Without the anchor the closing match was non-greedy against ANY run of
# three backticks, including one inside the code the creature was writing.
# Measured 2026-09-13/14 on the live run: it wrote `subagent-orchestrator`,
# whose job is stripping markdown fences off an LLM reply, so its source
# contains a startswith() against a fence literal. That inner run closed the
# bash block early, the heredoc never terminated, and the file landed cut
# mid-string:
#
#     File ".../subagent-orchestrator", line 68
#         if text.startswith("
#     SyntaxError: unterminated string literal
#
# **Twelve SyntaxErrors across twelve rewrites over nine hours.** Each time
# the creature read a syntax error in its own file and rewrote the tool;
# each time we cut it at the same character. It could not see the cut,
# because the transcript shows what RAN -- and what ran was the truncated
# command.
#
# Eleventh appearance of the framework damaging the creature's work and the
# creature being billed for it, and the most expensive measured so far: a
# tool that manipulates fences is exactly the tool this made impossible to
# write.
# **ONLY THE CLOSING FENCE IS ANCHORED**, and the asymmetry is the whole
# point. Anchoring both ends was shipped an hour before this and lost a
# real command within forty minutes:
#
#     ...</thought>```bash
#     cat "$MIND/tools/own/plan"
#     ```
#
# The model closed a reasoning tag and opened the block on the SAME LINE,
# so `^` never matched, the block was dropped, and the creature lost the
# one command it had proposed -- the framework discarding work again, by a
# fix meant to stop the framework discarding work.
#
# The closing anchor is what fixes the original fault, and it needs no help
# from the opener: a fence run inside the code being written sits mid-line
# (`if text.startswith("```")`), so it cannot close a block, while a
# genuine terminator always starts its own line. Opening mid-line is
# harmless by comparison -- the worst case is a literal that reads exactly
# like an opener AND is followed by a newline, in a reply that contains no
# real block.
# **CRLF IS A KNOWN GAP AND STAYS ONE.** `[ \t]*` does not match a
# carriage return, so a provider that sent CRLF would have every command
# classified `unclosed_fence` -- LOST, which is at least visible, and
# unfixable from the creature's side because it is not the creature's
# doing. Measured 2026-09-21 over the live journal: **0 of 1,926 replies
# contain CRLF at all.**
#
# **A FIX FOR IT WAS WRITTEN, SHIPPED AND REVERTED THE SAME NIGHT, and
# the revert is the entry worth reading.** It added `\r?` at both ends.
# The tag end was harmless. The CLOSING end became `^```\r?$`, and `$`
# under `re.M` means the fence must now END its line -- so a closer with
# a trailing space stopped closing, and a run of backticks that had been
# a closer stopped being one. Replayed over every raw reply in run 2 by
# an independent verifier: **9 replies parsed differently**, and the
# direction was the block SWALLOWING MORE. In one, two valid
# `remember current-phase done` commands became a single block
# containing `</thought>` and a literal fence -- a guaranteed shell
# error, attributed to the creature.
#
# That is the 2026-09-14 scar exactly: a midnight change to the parser
# the creature speaks through, justified as insurance, costing real
# commands. The measured risk was 0 and the measured cost was 9.
# **Invariant: a parser change is scored by REPLAYING IT OVER THE REAL
# REPLIES before it ships, not after.** `replay_parser.py` is that rule
# with teeth, and the gate asserts the tool itself works in
# `test_a_parser_change_can_be_replayed_before_it_ships`.
#
# *Trigger to revisit: the first reply that actually contains CRLF.*
FENCE_RE = re.compile(r"```(?:bash|sh)[ \t]*\n(.*?)^```", re.S | re.M)

# A tagged marker ANYWHERE in the reply. If one is present and yet no block
# was parsed, the creature marked work as an action and the channel did not
# deliver it -- whether the fence never closed, or the opener sat mid-line
# where it cannot anchor. Either way the work was PROPOSED AND LOST, and
# saying 'no command' about it is the exact lie this module exists against.
TAGGED_MARKER_RE = re.compile(r"```(?:bash|sh)\b")

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
    # REVERTED 2026-09-21 with the CRLF change above. The line that stood
    # here for one commit read `b.replace("\\r\\n", "\\n")` -- DOUBLE
    # backslashes, so it matched the four literal characters and no
    # carriage return was ever stripped. It did do one thing: it rewrote a
    # command the creature really wrote. One live occurrence in run 2's
    # 2,327 commands -- `tr -d '\\r\\n'` inside a tool being written to
    # disk, which would have landed as `tr -d '\\n'`. The framework
    # editing the creature's source, by a patch whose whole subject was
    # the framework not doing that.
    #
    # Third time in one night that an escape did not survive crossing a
    # tool boundary, and the first time it reached a commit. The habit in
    # CLAUDE.md says to write the file and run it; it does not say what to
    # do when the escape is INSIDE the thing being written, and now it does.
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
    # Asked by OUTCOME, not by counting backticks. This function is only
    # reached when `parse_blocks` returned nothing, so a tagged marker still
    # present means the creature proposed work the channel did not deliver.
    #
    # Counting parity was the first attempt and it was worse: a fence inside
    # a string literal made a healthy reply look unbalanced, and a mid-line
    # opener -- which cannot anchor, so never runs -- came back as
    # "no_command", which is the framework blaming the model for work it
    # threw away itself.
    if TAGGED_MARKER_RE.search(text):
        return "unclosed_fence", (
            "a ```bash marker is present but no complete block starts a line; "
            "commands were LOST, not absent")
    if ANY_FENCE_RE.search(text):
        # Fenced text, but nothing marked as an action. Its own reason, so a
        # reader can tell "said nothing" from "quoted something and ran
        # nothing". Three causes have been collapsed into one label in this
        # project before and each had a different fix.
        return "untagged_fence", (
            "the reply has fenced text but no ```bash block; nothing in it was "
            "marked as a command, so nothing was run")
    return "no_command", "a complete reply that contains no command"


def unusable_think(text, meta):
    """The creature ladder's predicate: WAS THERE A REPLY AT ALL.

    Returns a reason to step to the next rung, or None to accept.

    **The predicate belongs to the QUESTION, not to the agent** (the 2026-09-16
    scar), and the creature's question is not the cousin's. A think with no
    command is a REAL ANSWER -- the creature is allowed to look, to read, to
    conclude there is nothing to do -- so this rejects emptiness and nothing
    else. Anything with a character of text in it is accepted.

    Why it exists at all: this project wrote the rule down on 2026-09-10, about
    the cousin's rung, and then left the creature's ladder contradicting its
    own classifier. `classify_no_blocks` calls a reply that spent its whole
    budget and returned nothing `budget_spent` and puts it in LOST; the ladder
    banked the same reply as the answer and never tried the rung underneath.

    > An empty reply that consumed its whole budget is a FAILURE, never an
    > answer... such a call registers as a SUCCESS, so nothing walls the rung
    > and nothing below it is ever reached.

    Measured over run 2 on 2026-09-21: 9 of 1,967 thinks came back with no text
    at all -- seven gemini at finish=length, two groq at finish=stop. Nine
    cycles thrown away with a working rung sitting below.

    **Three emptinesses, three names**, because every distinction refused here
    is one a reader has to guess later: the budget ate it, the reasoning ate
    it, or nothing came back and we do not know why.
    """
    if (text or "").strip():
        return None
    meta = meta or {}
    before = meta.get("chars_before_strip") or 0
    stripped = meta.get("chars_stripped") or 0
    if stripped and stripped >= before:
        return "reasoning-only: the whole reply was deliberation, no answer"
    if meta.get("done_reason") == "length":
        return "budget spent: nothing came back and the ceiling was hit"
    return "empty reply: the rung answered with no text at all"


LOST = ("truncated", "unclosed_fence", "budget_spent")


def commands_were_lost(reason):
    """True when the creature DID propose work and the channel destroyed it.
    Counting these as 'proposed nothing' is what made a budget problem look
    like a quality problem for months."""
    return reason in LOST
