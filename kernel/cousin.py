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


def visit(ask, brief, claim, header, transcript, journal=None, trigger=None,
          library=""):
    """One manager invocation, end to end. `ask(prompt) -> (text, meta)`."""
    prompt = build_prompt(brief, claim, header, transcript, library)
    try:
        reply, meta = ask(prompt)
    except Exception as e:
        v = Verdict(UNKNOWN, error="%s: %s" % (type(e).__name__, e))
        if journal:
            journal.append("cousin_verdict", trigger=trigger, **v.as_fields())
        return v

    v = parse(reply)
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
