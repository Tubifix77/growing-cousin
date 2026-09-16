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


def unusable_invocation(text, meta):
    """Reason to reject an INVOCATION-choosing reply, or None to accept.

    **A different question needs a different predicate, and reusing the
    verdict's cost fifteen hours of production.** Item 9 gave the cousin its
    own shell by adding a second call -- *what would you like to run?* --
    whose answer is a bash block. It was made through the same `ask_cousin`
    the verdict uses, and that ladder carries `unusable_reply`, which rejects
    any reply without a VERDICT block. So every model that answered correctly
    was judged unusable, every rung was walled, the ladder exhausted, and the
    probe was lost.

    Measured 2026-09-16, the fifteen hours after the shell went live:
    **112 probes, 112 lost, 0 verdicts, 0 wants** -- while the creature
    thought 112 times on the same ladder. `answered but unusable: no-block`
    98 times. The cousin's shell had never once worked in production.

    The distinction that matters: for a verdict, no block is a FAILURE -- the
    contract requires one. For an invocation, no block is an ANSWER, and
    `choose_invocation` says so in as many words: *a user who cannot think
    what to type has told you something about the tool.* So "no-block" is
    accepted here and only a reply we never actually heard -- truncated, or
    all reasoning and no answer -- rejects the rung.

    This is `backends.ladder`'s own comment collecting its debt: *the
    predicate is the CALLER's, because only the caller knows what a usable
    reply looks like.* A second caller arrived and inherited the first one's.
    """
    from . import think as thinkmod
    if thinkmod.parse_blocks(text or ""):
        return None
    raw = (meta or {}).get("raw_text") or ""
    if raw and thinkmod.parse_blocks(raw):
        return None                # stripping hid it; the caller recovers it
    why = why_unreadable((meta or {}).get("done_reason"),
                         (meta or {}).get("chars_before_strip"),
                         (meta or {}).get("chars_stripped"))
    return None if why == "no-block" else why


def unusable_reply(text, meta):
    """Reason to reject this reply and try the next rung, or None to accept.

    Handed to the COUSIN's ladder only. The creature's ladder passes nothing:
    a think containing no command is a real answer, and rejecting it would
    spend the whole ladder on a creature that had simply decided to look
    around.

    It runs the SAME parse and the SAME recovery path `visit` runs, rather than
    a cheaper lookalike. A producer and a checker that agree only by eye drift,
    and this file lost an afternoon to exactly that today when the context
    writer and `wants()` stopped agreeing about a list format.
    """
    v = parse(text or "")
    if v.verdict != UNKNOWN:
        return None
    raw_text = (meta or {}).get("raw_text") or ""
    if raw_text and parse(raw_text).verdict != UNKNOWN:
        return None            # stripping hid it; `visit` will recover it
    return why_unreadable((meta or {}).get("done_reason"),
                          (meta or {}).get("chars_before_strip"),
                          (meta or {}).get("chars_stripped"))


INVOKE_TEMPLATE = """You are about to judge a tool someone else built. Before
you do, you get to USE it, in a shell of your own. The other tools listed
below are on your PATH too, and so is `recall`, which reads back what has
been remembered in this world.

Here is what it says about itself:

{header}

{library}

Write ONE ```bash block containing what you want to run. Usually that is a
single command with the arguments you judge sensible. If you would first need
to look something up -- an ID, a file name -- a few lines are fine: the lookup,
then the call. Do not invent an identifier when a tool on the list would tell
you a real one.

If you genuinely cannot think of a way to invoke it, write a bash block
containing only the tool's own name.
"""


def argless(cmd):
    """True when the cousin's block is a single word: the tool's name and
    nothing else, however it was arrived at.

    `bare` used to mean *the harness called it with no arguments*. Once the
    cousin composes the command, the harness knows nothing about arguments
    unless it looks at what was composed -- and the shell path shipped with
    `bare=False` hard-coded, so `view-subtask-logs task-123` exiting 1 on an
    ID the cousin had been told to invent was rendered as *NEVER WORKED for
    them (1 real failures)*. The 2026-09-14 misreading, rebuilt through the
    new door, on the page both inhabitants read every wake.

    A heuristic and stated as one: one token across the whole block, comments
    aside. `cd data && plan` is not bare by this test although `plan` got no
    arguments; that error is on the side of claiming less, which is the safe
    side for a flag whose false value used to mean *real failure*.
    """
    import shlex
    toks = []
    for line in (cmd or "").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            toks += shlex.split(s)
        except ValueError:
            toks += s.split()
    return len(toks) <= 1


def choose_invocation(ask, header, library=""):
    """Ask the cousin what it wants to run, and return its own words.

    **The framework must never compose this.** §4 gives *running the test* to
    the cousin, and until 2026-09-16 the harness invoked every tool BARE --
    so the cousin owned a job it structurally could not do, and spent two days
    accepting usage lines. The obvious repair is to have the kernel build a
    command out of the `# call:` header, and that is the wrong repair: it
    moves judgement back into the framework, which is the 99% this design
    deleted. A user who cannot think what to type has told you something
    about the tool.

    Returns `(command, meta)`; `command` is None when the cousin proposed
    nothing, and nothing is substituted for it.
    """
    from . import think as thinkmod
    prompt = INVOKE_TEMPLATE.format(header=header or "(no header)",
                                    library=library or "")
    reply, meta = ask(prompt)
    blocks = thinkmod.parse_blocks(reply or "")
    if not blocks:
        return None, dict(meta or {}, raw=(reply or "")[:400])
    # THE WHOLE FIRST BLOCK, not its first line. Until 2026-09-16 this took
    # `split("\n")[0]`: a cousin that wrote a lookup and then the call, or
    # set a variable and used it, had everything after line one silently
    # dropped -- and was then shown a transcript of a command it did not
    # issue and asked to judge the tool on it. The framework manufacturing
    # the cousin's own testimony. The block is the cousin's; it runs whole
    # and is recorded whole, and attribution is unaffected because the probe
    # carries every line of it.
    cmd = (blocks[0] or "").strip()
    return (cmd or None), dict(meta or {}, raw=(reply or "")[:400],
                               proposal_lines=len(cmd.splitlines()))


def visit(ask, brief, claim, header, transcript, journal=None, trigger=None,
          library="", tool=None):
    """One manager invocation, end to end. `ask(prompt) -> (text, meta)`.

    `tool` is journalled on the verdict so the library can report WHAT ITS
    USER SAID about each tool -- accepted, returned -- which is a fact about
    testimony, in place of the *FAILED* the framework used to compute from
    an exit code it can no longer interpret (see `argless`)."""
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
        journal.append("cousin_verdict", trigger=trigger, tool=tool,
                       model=(meta or {}).get("model"),
                       rung=(meta or {}).get("rung"),
                       finish=(meta or {}).get("done_reason"),
                       **fields)
        if v.noticed:
            journal.append("cousin_noticed", text=v.noticed)
        if v.want and v.verdict == ACCEPTED:
            journal.append("cousin_want", text=v.want)
    return v
