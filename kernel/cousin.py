#!/usr/bin/env python3
"""cousin.py -- invoke the manager, read its verdict, enforce the bounds.

The brief is `MANAGER-PROMPT.md` and lives outside this module on purpose: it is
the product, and it changes far more often than this code does.

Three bounds live here, and none of them is a judgement. They are the things
that must hold when the manager is wrong:

1. **A verdict is read from the END of the reply.** Models mention a verdict
   mid-thought before committing to one; three parsers in the parent needed this
   cure.
2. **A `RETURNED` carrying no message is never delivered.** A refusal with no
   reason is the arbitrary world the brief exists to prevent. Observed once in
   the trial and gone on the rerun -- which is worse, not better, because it
   passes tests and fails in production.
3. **An empty-but-complete reply is a failure, never an answer.** Handled in
   `think.classify_no_blocks`; here it means a verdict that could not be read is
   recorded as UNKNOWN and gates nothing. An instrument that cannot run must say
   UNKNOWN, never FAULTY.
"""
import re

BLOCK_RE = re.compile(r"<<<COUSIN\b(.*?)(?:^COUSIN\s*$|\Z)", re.S | re.M)
FIELD_RE = re.compile(r"^\s*(verdict|tried|outcome|want|noticed)\s*:\s*(.*)$",
                      re.I | re.M)

ACCEPTED = "ACCEPTED"
RETURNED = "RETURNED"
UNKNOWN = "UNKNOWN"


class Verdict:
    def __init__(self, verdict=UNKNOWN, tried="", outcome="", to_creature="",
                 want="", noticed="", error=None, raw=""):
        self.verdict = verdict
        self.tried = tried
        self.outcome = outcome
        self.to_creature = to_creature
        self.want = want
        self.noticed = noticed
        self.error = error
        self.raw = raw

    @property
    def deliverable(self):
        """A RETURNED with no testimony must never reach the creature."""
        if self.verdict == RETURNED and not (self.to_creature or "").strip():
            return False
        return self.verdict in (ACCEPTED, RETURNED)

    @property
    def blocks_done(self):
        return self.verdict == RETURNED and self.deliverable

    def as_fields(self):
        return {"verdict": self.verdict, "tried": self.tried,
                "outcome": self.outcome, "to_creature": self.to_creature,
                "want": self.want or None, "noticed": self.noticed or None,
                "error": self.error}


def parse(reply):
    """Read the LAST block. Anything unreadable is UNKNOWN, never a verdict."""
    blocks = BLOCK_RE.findall(reply or "")
    if not blocks:
        return Verdict(UNKNOWN, error="no-block", raw=reply or "")
    body = blocks[-1]
    got = {k.lower(): v.strip() for k, v in FIELD_RE.findall(body)}

    m = re.search(
        r"^\s*to_creature\s*:\s*\|?\s*\n(.*?)"
        r"(?=^\s*(?:want|noticed|verdict|tried|outcome)\s*:|\Z)",
        body, re.S | re.M)
    if m:
        msg = "\n".join(l.strip() for l in m.group(1).strip().splitlines()).strip()
    else:
        m2 = re.search(r"^\s*to_creature\s*:\s*(.+)$", body, re.I | re.M)
        msg = m2.group(1).strip() if m2 else ""

    v = (got.get("verdict") or "").upper()
    if RETURNED in v:
        v = RETURNED
    elif ACCEPTED in v:
        v = ACCEPTED
    else:
        return Verdict(UNKNOWN, error="no-verdict", raw=reply or "")

    out = Verdict(v, got.get("tried", ""), got.get("outcome", ""), msg,
                  got.get("want", ""), got.get("noticed", ""), raw=reply or "")
    if not out.deliverable:
        out.error = "mute-refusal"
    return out


LIBRARY_TEMPLATE = """

## What it already had before this

{library}

Look before you accept. Its third test is whether this is genuinely new or the
fifth variant of something already here -- and a near-duplicate is a cost it
pays forever, in a library it must later hand to you whole.
"""


def build_prompt(brief, claim, header, transcript, library=""):
    out = brief + CASE_TEMPLATE.format(
        claim=claim, header=header, transcript=transcript)
    if library:
        out += LIBRARY_TEMPLATE.format(library=library)
    return out


CASE_TEMPLATE = """

---

# This visit

The creature has just marked a piece of work done. You went to use it.

## What it claims

{claim}

## The tool's header, as you read it

```
{header}
```

## What happened when you tried to use it

```
{transcript}
```

---

Decide. Emit exactly one `<<<COUSIN` block as the last thing in your reply.
"""


REASONING_SHARE = 0.5


def why_unreadable(finish, before_strip, stripped):
    """WHY was there no verdict block? Three answers, three different fixes.

    The think side has done this since the kernel's first week
    (`think.classify_no_blocks`): *truncated*, *budget_spent* and *no_command*
    are kept apart because each has its own repair, and collapsing them makes a
    budget problem look like a quality problem. **The cousin side said
    `no-block` for all of them**, and that single label cost four hours on
    2026-09-13: 14 of 16 verdicts came back "no-block", I read it as "the model
    declined to answer", called it expected weather, and left it frozen under
    the tuning rule while the engine produced nothing.

    What the fields actually said, once read: `chars_before_strip=8407`,
    `chars_stripped=7935`, `finish=length`. The model wrote 8,400 characters,
    **94% of them reasoning**, and was cut off before reaching the block the
    contract puts LAST. That is not a model with nothing to say. It is the
    oldest measured finding in this project -- *budget is not the binding
    constraint, unbounded reasoning is* -- wearing a label that hid it.

    The label is FRAMEWORK and model-independent. What to DO about a rung that
    reasons past its budget is tuning, and is a separate decision.
    """
    if finish != "length":
        # A complete reply that simply contains no block. The only one of the
        # three that is genuinely the model choosing not to answer.
        return "no-block"
    if before_strip and stripped and stripped >= REASONING_SHARE * before_strip:
        return "reasoning-ate-the-budget"
    return "truncated-before-block"


def visit(ask, brief, claim, header, transcript, journal=None, trigger=None,
          library=""):
    """One manager invocation, end to end. `ask(prompt) -> (text, meta)`."""
    prompt = build_prompt(brief, claim, header, transcript, library)
    try:
        reply, meta = ask(prompt)
    except Exception as e:
        # **UNREACHABLE IS NOT A VERDICT, AND IT IS NOT THIS CYCLE'S ANSWER.**
        #
        # A ladder that no rung would serve is the same event for the cousin as
        # for the creature, and it must get the same response: the cycle stops
        # and the supervisor waits. Turning it into UNKNOWN here let the cycle
        # walk on as though the work had been looked at -- the creature marked
        # something done, nothing reviewed it, and it was told nothing.
        #
        # 2026-09-13, measured over 546 cycles: 39 of 98 visits never happened.
        # Every one was discarded, and the creature's whole trajectory formed
        # against feedback that silently went missing. Tue's call, and it is the
        # right one: the two agents SHARE ONE QUEUE AND WAIT FOR EACH OTHER.
        # That run was archived rather than patched, because a trajectory
        # cannot be repaired retroactively.
        #
        # Anything else -- a model that answered badly, a parse failure, a
        # timeout inside a rung that DID serve -- is still UNKNOWN, because
        # that is an instrument that ran and produced nothing usable.
        from . import backends
        if isinstance(e, backends.LadderExhausted):
            if journal:
                journal.append("visit_deferred", trigger=trigger,
                               detail=str(e)[:300])
            raise
        v = Verdict(UNKNOWN, error="%s: %s" % (type(e).__name__, e))
        if journal:
            journal.append("cousin_verdict", trigger=trigger, **v.as_fields())
        return v

    v = parse(reply)
    if v.verdict == UNKNOWN and v.error == "no-block":
        # Stripping may have eaten the answer. `gemma-4-31b-it` opens a
        # <thought> and, on a long brief, never closes it -- 7,386 characters
        # produced and every one removed, four verdicts in a row (2026-09-12).
        # If the block it never closed CONTAINED the verdict, the honest reply
        # is there and only our cleaning hid it.
        #
        # This can only ever find a block that was really emitted; it cannot
        # manufacture one. A reply with no verdict stays UNKNOWN.
        raw_text = (meta or {}).get("raw_text") or ""
        if raw_text:
            recovered = parse(raw_text)
            if recovered.verdict != UNKNOWN:
                recovered.recovered_from_reasoning = True
                v = recovered
    if v.verdict == UNKNOWN and v.error == "no-block":
        v.error = why_unreadable((meta or {}).get("done_reason"),
                                 (meta or {}).get("chars_before_strip"),
                                 (meta or {}).get("chars_stripped"))
    if journal:
        # The rung is recorded beside the model because the ladder is
        # heterogeneous: the brief was measured on gemma-4-31b-it, and a
        # verdict served by some other rung is a different instrument. Without
        # this, an accept/refuse rate read later silently mixes them.
        fields = v.as_fields()
        if v.verdict == UNKNOWN:
            # STORE THE RAW EVIDENCE when the verdict could not be read. A
            # summary cannot be re-interrogated when the summary is what is
            # wrong -- the oldest scar in this project.
            #
            # 2026-09-12: seven UNKNOWNs in a 7-hour run, all `no-block`. The
            # cause was diagnosable only because `finish=length` happened to be
            # recorded; the reply itself was gone. Capped, because a runaway
            # reply is exactly the case this fires on and the journal must not
            # inherit its size.
            fields["raw"] = (v.raw or "")[:1200]
            fields["raw_chars"] = len(v.raw or "")
            # What the model produced BEFORE reasoning was stripped. An empty
            # `raw` with a large `before_strip` is a model that talked itself
            # out of answering -- a different fault from one that said nothing,
            # and raising the budget fixes neither.
            fields["chars_before_strip"] = (meta or {}).get("chars_before_strip")
            fields["chars_stripped"] = (meta or {}).get("chars_stripped")
        journal.append("cousin_verdict", trigger=trigger,
                       model=(meta or {}).get("model"),
                       rung=(meta or {}).get("rung"),
                       finish=(meta or {}).get("done_reason"),
                       **fields)
        if v.noticed:
            journal.append("cousin_noticed", text=v.noticed)
        if v.want and v.verdict == ACCEPTED:
            journal.append("cousin_want", text=v.want)
    return v
