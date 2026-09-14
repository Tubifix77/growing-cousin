#!/usr/bin/env python3
"""cycle.py -- one wake, end to end. The whole engine is this file plus bounds.

The context rule, which is the load-bearing architectural decision (§14):

> **The manager WRITES the context; the kernel SERVES it.**

Nothing is assembled per wake. The kernel reads a file the cousin last wrote and
hands it over unchanged. That keeps the economics (no manager call per cycle) and
retires the wake-cost failure class outright -- reading a file costs the same on
day 400 as on day 1, however large the library grows.
"""
import os
import re
import shlex

from . import body as bodymod
from . import cousin as cousinmod
from . import library as librarymod
from . import think as thinkmod
from . import triggers as trigmod
from .journal import EXEC_CMD_CHARS, EXEC_STDERR_CHARS, EXEC_STDOUT_CHARS, capped


WANTS_KEPT = 3

# Generous, because this is EVIDENCE and the point of keeping it is that the
# question it will be asked has not been thought of yet. The creature's replies
# measured 2026-09-13 on the live ladder run ~3,100 chars, so this keeps whole
# replies rather than the interesting half of one. `capped` marks any cut.
THINK_RAW_CHARS = 12000

# Any run of three or more backticks. Anything the creature is SHOWN must be
# unable to parse as a block it could act on.
FENCE_RUN = re.compile(r"`{3,}")


class Engine:
    def __init__(self, journal, body, brief, ask_creature, ask_cousin,
                 context_path, creature_brief=""):
        self.j = journal
        self.body = body
        self.brief = brief                  # the cousin's brief
        self.creature_brief = creature_brief  # identity: served, never written
        self.ask_creature = ask_creature
        self.ask_cousin = ask_cousin
        self.context_path = context_path    # the part the COUSIN owns
        self.cycles_since_visit = 0
        self.cycles_since_change = 0
        self.done_blocked = None       # testimony the creature must see next wake
        self.served = {}               # what the last serve_context put on the page

    # ---------------------------------------------------------------- context

    def serve_context(self):
        """Serve what the cousin wrote, plus what just happened.

        The curated part is the cousin's -- the kernel does not decide what
        belongs in it. But WHAT JUST HAPPENED is a fact, not a judgement, and
        gathering facts is kernel work.

        2026-09-11, first live run: without this the creature ran `ls -R
        tools/own/` on all six cycles. Nothing was broken -- the context was
        byte-identical every wake, so at temperature 0 the same input produced
        the same decision forever. Its own hard rule is *never run the same
        command twice in a row*, and **a rule about what you last did is
        unfollowable if nothing shows you what you last did.**
        """
        parts = []
        if self.done_blocked:
            # A refusal is delivered once, at the top, then cleared. Surfacing
            # it every cycle would be a nag it learns to skip.
            parts.append("## The person who needs this could not use it\n\n"
                         + self.done_blocked)
        mem = self.memory_block()
        if mem:
            parts.append(mem)
        recent = self.recent_block()
        if recent:
            parts.append(recent)
        # ITS OWN LIBRARY, EVERY WAKE. 2026-09-13 (Tue): "I want and need the
        # creature to be always aware of the tools available to it", after the
        # way MCP and skills present a tool's frontmatter on every load rather
        # than once.
        #
        # It was never shown this. The cousin's library gap (CLAUDE.md §5) was
        # fixed in September and the same gap aimed at the BUILDER went
        # unnoticed for as long: a creature asked not to build the fifth
        # variant of something, while never being shown the four. The prompt
        # promises its tools are on PATH; a promise the context does not keep
        # is a contract violation, not a detail -- the same rule `memory_block`
        # exists for.
        #
        # Placed directly before the wants, so what it HAS and what is still
        # ASKED FOR are read together. That adjacency is the whole anti-twin
        # pressure, and it costs nothing.
        own = os.path.join(self.body.mind, "tools", "own")
        names = trigmod.list_tools(own)
        lib = librarymod.render(own, self.j)
        if lib:
            parts.append(lib)
        wants = []
        if os.path.exists(self.context_path):
            with open(self.context_path, encoding="utf-8") as f:
                managed = f.read().strip()
            if managed:
                parts.append(managed)
                wants = self.wants()
        if self.creature_brief:
            parts.append(self.creature_brief)
        # WHAT WAS SERVED, AS FACTS, gathered here where it was served. Until
        # 2026-09-15 the wake recorded one number -- how long the context was
        # -- and length cannot say whether the library was on the page or
        # whether a standing want reached the creature. The builder's library
        # gap survived a day and the want channel was dead for the life of
        # the kernel under a green gate (CLAUDE.md §5), both invisible because
        # nothing recorded what the context HELD. A reader recomputing these
        # from the directory would be a second account of the same event, and
        # two accounts drift; the kernel says what it served, once.
        self.served = {
            "library_shown": min(len(names), librarymod.LIBRARY_LIMIT),
            "library_total": len(names),
            "wants_served": len(wants),
            "window": self.HISTORY_OUTPUT_CHARS,
            "refusal_served": bool(self.done_blocked),
            "memory_served": bool(mem),
        }
        return "\n\n---\n\n".join(p for p in parts if p)

    def record_want(self, want):
        """The cousin asking for the next capability IS the direction mechanism.

        2026-09-12: wants were journalled and went nowhere. `write_context` was
        called once, at seed, and never again -- so "the manager writes the
        context" was aspirational, and the three parent guards that AIM rather
        than refuse (architect ruling, retro directive, active-project block)
        had no replacement at all. The creature was told what it got wrong and
        never what was wanted next.

        BOUNDED, and newest-first. A managed context that only grows is the
        wake-cost failure class returning by another door: the cost of every
        wake would climb with the age of the project, forever.
        """
        want = (want or "").strip()
        if not want:
            return
        retired = [w for w in self.wants() if w != want]
        # NUMBERED, because `wants()` reads this file back and matches on the
        # number. One item needs no list -- but a writer and a reader that
        # agree only by eye drift, and this pair drifted the moment the
        # numbering was dropped: `wants()` returned nothing, `retire_wants`
        # believed nothing was standing, and the round trip was silently open.
        body = ["## What the person who uses your work asked for next", "",
                "1. %s" % want, "",
                "That is what they asked for last. It is a want, not an order "
                "-- but it is the only thing anyone has actually asked you "
                "for."]
        self.write_context("\n".join(body))
        if retired:
            self.j.append("want_retired", count=len(retired),
                          because="superseded", texts=retired[:WANTS_KEPT])
        self.j.append("context_written", wants=1, chars=len(body))

    def want_was_acted_on(self):
        """Has the creature written a tool since the standing want was issued?

        **MEASURED 2026-09-14, and it is why this exists: of 50 wants issued
        over twenty hours, 29 were retired without the creature writing
        anything at all.** Fifty-eight percent of the only direction channel in
        the design, discarded before its recipient had a turn.

        That was my doing. The first version retired a want on the next
        ANSWERED VISIT, whatever that visit was about, and I wrote the
        objection into the docstring at the time -- *"the answering visit may
        have been about a different tool, so a want can retire without the
        creature ever having built it"* -- and chose recency anyway. With n=50
        the objection is no longer a worry, it is the behaviour.

        The fault being fixed is still real and still fixed: a want that stood
        forever was re-served every wake and the creature re-ran the same
        commands against it. But *acted on* is the honest test for that, not
        *answered*. A want the creature has already built against will not be
        re-served; a want it never saw a turn at survives to be seen.

        Supersession is unchanged and does the rest: any accept brings a new
        want, and `record_want` replaces what was standing.

        Derived from the journal, never authored -- the same rule as every
        other piece of state here (§6.1). A tool WRITE is the evidence, which
        includes edits: extending an existing tool is acting on a want just as
        much as creating one, and a rule that only counted new files would
        reward exactly the proliferation this engine is already showing.
        """
        wants = self.j.read(kinds=["cousin_want"])
        if not wants:
            return False
        since = wants[-1].get("ts", 0)
        return any(r.get("ts", 0) > since
                   and r.get("type") == "TOOL_WRITE"
                   for r in self.j.read(kinds=["trigger_fired"]))

    def retire_wants(self, because):
        """The cousin spoke and did not ask for this again, so it stops standing.

        **A want had no completion signal.** It was written into the managed
        context and re-served EVERY wake until three newer wants pushed it out,
        and new wants only arrive on an accept. So between accepts the creature
        was handed the same direction again and again with no way to mark it
        discharged -- and on 2026-09-13 it spent a run of cycles re-running
        `plan goal / plan add / plan list` against a standing
        *"add a task to the plan"*.

        That is the trigger scar one level up: *a trigger that does not reset
        its own counter fires forever*, and its resolution is already written
        three lines from where this is called -- **a visit is the ANSWER to
        whatever summoned it, so it clears what summoned it.** A want is
        answered by the cousin's next answered visit, whatever that visit
        said.

        **The objection, stated rather than hidden:** that visit may have been
        about a different tool, so the want can retire without the creature
        ever having built it. Recency still wins, for the same reason the
        channel supersedes rather than appends -- the cousin is the direction
        authority and its most recent word is its direction. A want from three
        visits ago competing with today's refusal is exactly the *three
        restatements standing at once* fault in another costume. If the
        capability is still missing, the cousin is the one who will say so
        again, and it gets a turn every visit.

        An UNANSWERED visit retires nothing: nobody spoke.
        """
        standing = self.wants()
        if not standing:
            return
        self.write_context("")
        self.j.append("want_retired", count=len(standing), because=because,
                      texts=standing[:WANTS_KEPT])

    def wants(self):
        """Read back the wants the managed context currently holds."""
        if not os.path.exists(self.context_path):
            return []
        out = []
        with open(self.context_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\d+\.\s+(.*\S)", line)
                if m:
                    out.append(m.group(1))
        return out

    def memory_block(self):
        """What it remembered. The prompt promises memory is shown each cycle;
        a promise the context does not keep is a contract violation, not a
        detail."""
        p = os.path.join(self.body.mind, "state", "memory.json")
        try:
            import json
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            return ""
        if not d:
            return ""
        lines = ["## What you remember", ""]
        lines += ["- **%s** = %s" % (k, str(v)[:400]) for k, v in sorted(d.items())]
        return "\n".join(lines)

    HISTORY_QUOTE = "| "
    # 2026-09-12, measured against the live library: the creature's tools are
    # 706-3157 bytes, so the old 700 guaranteed a mid-file cut on essentially
    # every `cat` of a tool -- a constant I chose with no evidence at all.
    # It cut `log-read` (706 bytes) at exactly `print(line.str`, six characters
    # short, and the creature reported *"the previous log-read had a bug:
    # print(line.str. It was truncated"* and rewrote the tool.
    HISTORY_OUTPUT_CHARS = 2400
    HISTORY_TOTAL_CHARS = 6000

    def recent_block(self, cycles=3):
        """The last few things it ran and what came back.

        **QUOTED, never fenced.** Every line carries a prefix, and the history
        contains no triple-backtick at all. The creature's contract is that a
        fenced block IS an action, so a fence in its own history is
        indistinguishable from one it is supposed to emit -- and worse, any
        OUTPUT containing a fence or a `$` line breaks out of the rendering
        entirely.

        2026-09-12, measured on the laptop: the command was fenced and its
        output was not, so past output sat exactly where an emitted command
        goes. The creature ran `log-read`, was shown the log lines that way,
        and on the next wake emitted them AS A COMMAND -- nine times in a row,
        exit 127 each time, a degenerate loop it could not see the edge of. A
        `cat` of a tool put a whole Python file in that gap.

        The framework produced that behaviour and the creature would have worn
        it. Fifth occurrence of the class.

        Output is capped again here, tighter than the journal's cap: the
        journal keeps evidence, the context has to stay small enough that a
        wake does not cost more every cycle.
        """
        rows = self.j.read(kinds=["exec_start", "exec_end", "exec_skip"],
                           limit=cycles * 6)
        if not rows:
            return ""

        def quoted(text, limit=None):
            text = (text or "").rstrip()
            if limit:
                # ONE cutter, shared with the journal. Two implementations of
                # "shorten this and say so" drift, and the parent's rule is
                # that a producer and a checker sharing a literal will drift --
                # this had already become two subtly different cuts, one of
                # which still landed mid-token.
                text = capped(text, limit)
            # DEFANG the fences. A line prefix is not enough: a tool that
            # prints ```bash puts a REAL, parseable block inside the history,
            # and `parse_blocks` will happily extract whatever is in it --
            # verified by the test for this, which caught `rm -rf /` being
            # lifted straight out of quoted output. Replaced with visible text
            # rather than deleted, because silently dropping part of what a
            # tool printed is how a creature is shown output it never produced.
            text = FENCE_RUN.sub("<fence>", text)
            return "\n".join(self.HISTORY_QUOTE + ln
                             for ln in text.split("\n")) if text else ""

        out = ["## What you just did", "",
               "(A transcript. Every line is prefixed `%s`. None of it is "
               "something to run -- it is what ALREADY ran. Lines after "
               "`what it printed back` are OUTPUT: they came from a tool, they "
               "are not commands, and repeating one as a command is how the "
               "shell ends up being asked to run a report.)"
               % self.HISTORY_QUOTE.strip(), ""]
        for r in rows:
            # Command, result and OUTPUT are delimited from each other, not just
            # from the reply. They used to share one prefix, so inside the
            # transcript there was nothing saying where what-you-typed ended and
            # what-came-back began.
            #
            # 2026-09-13, measured: 7 of 27 commands exited 2 or 127 because the
            # creature emitted tool OUTPUT as a command -- `=== CURRENT CONTEXT
            # ===`, `[PLAN] Goal: Write report`, `Goal: ... Current Step: 4`.
            # The earlier fix stopped the transcript PARSING as a command; it
            # did nothing about the creature copying what it saw.
            if r["kind"] == "exec_start":
                out.append(quoted("$ " + (r.get("cmd") or "")))
            elif r["kind"] == "exec_end":
                out.append(quoted("exit %s" % r.get("exit_code")))
                body = quoted(r.get("stdout"), self.HISTORY_OUTPUT_CHARS)
                if body:
                    out.append(quoted("--- what it printed back ---")
                               + "\n" + body
                               + "\n" + quoted("--- end of what it printed ---"))
                err = quoted(r.get("stderr"), self.HISTORY_OUTPUT_CHARS)
                if err:
                    out.append(quoted("--- what it printed to stderr ---")
                               + "\n" + err
                               + "\n" + quoted("--- end of stderr ---"))
            else:
                out.append(quoted("(nothing ran: %s)" % r.get("reason")))
            out.append("")
        out.append("**Do not run any of those again.** You already have the "
                   "answer; act on it.")
        block = "\n".join(out)
        # And a bound on the WHOLE block. Raising the per-output cap to fit a
        # real tool took the history from 4k to 10k chars in one step, and a
        # context that grows with what the creature happens to print is the
        # wake-cost failure class arriving by the back door. Oldest goes first:
        # the newest cycle is the one it needs to not repeat.
        if len(block) > self.HISTORY_TOTAL_CHARS:
            keep = block[-self.HISTORY_TOTAL_CHARS:]
            nl = keep.find("\n")
            # The HEADER IS KEPT, not replaced. It carries the warning that
            # output is not a command, and dropping it here would remove that
            # warning precisely when the transcript is longest and busiest --
            # which is exactly when the creature started re-running its own
            # output. A safety note that vanishes under load is not one.
            block = (out[0] + "\n\n" + out[2]
                     + "\n\n(Older lines dropped; this is the most recent part "
                       "of the transcript.)\n"
                     + (keep[nl:] if nl > 0 else keep))
        return block

    def write_context(self, text):
        d = os.path.dirname(self.context_path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(self.context_path, "w", encoding="utf-8") as f:
            f.write(text)

    # ------------------------------------------------------------------ cycle

    def resume(self):
        """Restore the engine's counters from the journal. Returns cycles seen.

        **Derived, never saved.** A savegame written beside the journal is a
        second account of the same facts, and the two drift the moment a run
        dies between the cycle and the save -- which is exactly when a savegame
        is supposed to help. The journal is already ground truth and is already
        written as it goes, so the only honest resume is a replay of it. Same
        reasoning that made the manager's state derived rather than authored
        (CLAUDE.md 6.1): a derivation cannot drift.

        A crash therefore costs the current cycle and nothing before it.

        Counters move at the END of a cycle, so the journal is folded as a list
        of CLOSED cycles rather than counted at each wake -- counting at wakes
        drops the last cycle's increment, which is the one a resume most needs.
        """
        cycles, blocked = [], None
        for r in self.j.read():
            kind = r.get("kind")
            if kind == "wake":
                cycles.append({"visit": False, "change": False})
                blocked = None          # cleared at the top of every cycle
            elif not cycles:
                continue
            elif kind == "tools_changed":
                cycles[-1]["change"] = True
            elif kind == "cousin_verdict":
                cycles[-1]["visit"] = True
                if (r.get("verdict") == "RETURNED"
                        and (r.get("to_creature") or "").strip()):
                    blocked = r.get("to_creature")

        since_visit = since_change = 0
        for c in cycles:
            if c["visit"]:
                # A visit is the ANSWER to whatever summoned it: both counters
                # clear, or a STALL re-fires on every later cycle.
                since_visit = since_change = 0
            else:
                since_visit += 1
                since_change = 0 if c["change"] else since_change + 1

        self.cycles_since_visit = since_visit
        self.cycles_since_change = since_change
        self.done_blocked = blocked
        return len(cycles)

    def run_cycle(self):
        """Returns a dict describing what happened. Substantive = something ran."""
        tools_dir = os.path.join(self.body.mind, "tools", "own")
        tools_before = trigmod.list_tools(tools_dir)

        context = self.serve_context()
        self.done_blocked = None

        # The served facts ride on the wake, so `wake.library_shown == 0` while
        # tools exist, or `wants_served == 0` while a want stands, is a fault a
        # monitor can see in the journal rather than a belief about the code.
        self.j.append("wake", context_chars=len(context), **self.served)
        try:
            reply, meta = self.ask_creature(context)
        except Exception as e:
            # A ladder with nothing to give is the free tier working as
            # designed, not a fault. Journalling it as `error` told every
            # later reader -- human or model -- that something was broken,
            # which is how a night gets spent fixing the weather.
            from . import backends as _b
            expected = isinstance(e, _b.LadderExhausted)
            self.j.append("think_deferred" if expected else "error",
                          where="think",
                          detail="%s: %s" % (type(e).__name__, e))
            # RE-RAISED, not swallowed. Deciding what a failure MEANS is the
            # supervisor's job -- it is the thing that knows the difference
            # between "come back later" and "broken", and it owns the pacing.
            #
            # 2026-09-12, caught on the laptop before the first overnight run:
            # swallowing this turned an exhausted ladder into a quiet
            # `think_failed`, so the loop saw a successful cycle and started the
            # next one TWO SECONDS later. Measured: 174s, then 2s. Every bound
            # built for exactly this case -- the wait, the backoff, the failure
            # ceiling -- was unreachable, and a night of it would have hammered
            # rungs the spine also depends on.
            #
            # The dead `want` channel in a new costume: a channel nothing routes
            # to is dead however carefully it was built.
            raise

        meta = meta or {}
        # `rung` as well as `model`: with a heterogeneous ladder these answer
        # different questions -- which PROVIDER served us, and which MODEL
        # actually produced the text. The brief was measured on
        # gemma-4-31b-it, so any later reading of accept/refuse rates has to be
        # able to separate verdicts by both.
        # THE REPLY ITSELF, capped. The cousin's verdict has kept its raw text
        # since 2026-09-12 (`test_an_unreadable_verdict_keeps_its_evidence`);
        # the creature's think never did, and the asymmetry cost a diagnosis
        # on 2026-09-13.
        #
        # A cycle ran three command blocks, two of which were the creature's
        # own transcript pasted back -- a quoted history line, `| exit 0`, sent
        # to bash. The question that matters is which agent produced that: a
        # framework that extracts commands the creature never fenced is the
        # worst fault this design has, and a creature copying its own context
        # is ordinary confusion nobody may touch. **Only the raw reply can
        # tell those apart, and it had been thrown away.** The answer came
        # from reading `FENCE_RE` instead, which is not an answer the next
        # reader can reproduce from the log.
        #
        # `chars` and `finish` are a summary, and a summary cannot be
        # re-interrogated when the summary is what is wrong -- the oldest scar
        # in CLAUDE.md §5, here in the one channel still missing its evidence.
        self.j.append("think", chars=len(reply or ""),
                      model=meta.get("model"), rung=meta.get("rung"),
                      finish=meta.get("done_reason"),
                      raw=capped(reply or "", THINK_RAW_CHARS))

        blocks = thinkmod.parse_blocks(reply)
        if not blocks:
            reason, detail = thinkmod.classify_no_blocks(
                reply, meta.get("done_reason"), meta.get("completion_tokens"))
            self.j.append("exec_skip", reason=reason, detail=detail,
                          lost=thinkmod.commands_were_lost(reason))
            self.cycles_since_visit += 1
            self.cycles_since_change += 1
            return {"substantive": False, "reason": reason}

        executed = []
        for i, cmd in enumerate(blocks):
            if not bodymod.ensure_body(self.body, self.j):
                self.j.append("error", where="body",
                              detail="could not respawn; skipping remaining blocks")
                break
            self.j.append("exec_start", block=i + 1,
                          cmd=capped(cmd, EXEC_CMD_CHARS))
            r = self.body.run(cmd)
            if r.setup_failed:
                # Infrastructure breakage is never recorded as the command's
                # own output, and never counted as work the creature did.
                self.j.append("body_unresponsive", block=i + 1,
                              detail=capped(r.stderr, EXEC_STDERR_CHARS))
                break
            self.j.append("exec_end", block=i + 1, exit_code=r.code,
                          stdout=capped(r.stdout, EXEC_STDOUT_CHARS),
                          stderr=capped(r.stderr, EXEC_STDERR_CHARS))
            executed.append((cmd, r.code))

        if not executed:
            self.cycles_since_visit += 1
            self.cycles_since_change += 1
            return {"substantive": False, "reason": "nothing_ran"}

        tools_after = trigmod.list_tools(tools_dir)
        if tools_after != tools_before:
            # Journalled explicitly, and not left to be inferred from
            # TOOL_WRITE: a DELETION changes the set and fires no trigger, so
            # inferring "did the library change" from triggers silently misses
            # it. State is derived from the event log (CLAUDE.md 6.1), which
            # only works when the event is actually IN the log.
            self.j.append("tools_changed",
                          added=sorted(set(tools_after) - set(tools_before)),
                          removed=sorted(set(tools_before) - set(tools_after)))
            self.cycles_since_change = 0
        else:
            self.cycles_since_change += 1

        fired = trigmod.detect(executed, tools_before, tools_after,
                               self.cycles_since_visit, self.cycles_since_change)
        for t, fields in fired:
            self.j.append("trigger_fired", type=t, **fields)

        result = {"substantive": True, "executed": len(executed),
                  "triggers": [t for t, _ in fired], "verdict": None}

        if fired:
            v = self.visit_cousin(fired[0], executed, tools_after, tools_before)
            result["verdict"] = v.verdict
            if v.verdict != cousinmod.UNKNOWN:
                # A visit is the ANSWER to whatever fired. Both counters reset,
                # or a STALL re-fires on every subsequent cycle and the cousin
                # becomes a nag the creature learns to skip -- the parent's rule
                # is surface on a CHANGE of state, never continuously.
                self.cycles_since_visit = 0
                self.cycles_since_change = 0
            else:
                # The cousin RAN and produced nothing usable -- a bad reply, an
                # unparseable verdict. That is an instrument that ran, so it
                # says UNKNOWN and gates nothing. But it is still not an ANSWER
                # to what summoned it, so the counters stay and HEARTBEAT will
                # bring the cousin back to the work.
                #
                # A cousin that could not be REACHED never gets here at all:
                # `cousin.visit` re-raises LadderExhausted so the whole cycle
                # defers, which is the one queue both agents share.
                self.cycles_since_visit += 1
                self.j.append("visit_unanswered", trigger=fired[0][0],
                              error=v.error)
        else:
            self.cycles_since_visit += 1
        return result

    # ----------------------------------------------------------------- cousin

    def visit_cousin(self, fired, executed, tools_after, tools_before):
        trigger, _fields = fired
        target = self.pick_target(executed, tools_after, tools_before)
        claim, header, transcript, library = self.evidence(target, executed)

        v = cousinmod.visit(self.ask_cousin, self.brief, claim, header,
                            transcript, journal=self.j, trigger=trigger,
                            library=library)

        if v.verdict == cousinmod.UNKNOWN:
            # Gates nothing. An instrument that cannot run says UNKNOWN.
            self.j.append("cousin_unusable", error=v.error)
            return v
        if v.verdict == cousinmod.ACCEPTED and v.want:
            # DIRECTION. Without this the cousin can only ever say no, and the
            # three parent guards that aim rather than refuse have no
            # replacement at all.
            self.record_want(v.want)
        elif self.want_was_acted_on():
            # An answered visit discharges a want the creature has ALREADY
            # HAD A TURN AT -- and only that one. See `want_was_acted_on`.
            self.retire_wants("acted on, then answered by a %s" % v.verdict)
        if v.blocks_done:
            self.done_blocked = v.to_creature
        return v

    def pick_target(self, executed, tools_after, tools_before):
        """Which tool the cousin is sent to use. **It must be one that EXISTS.**

        The fallback parses the token after a write pattern in the command
        text, and a command is arbitrary text: 2026-09-13, run 2, it returned
        a single backtick. The cousin was sent to use a tool named `` ` ``, got
        `command not found`, and filed an honest RETURNED -- which the creature
        then read as *"I tried to run the tool you finished, but the system
        told me the command was not found"*, about a tool it had never made.

        **The framework manufactured a complaint against the creature**, which
        is the one outcome this whole design exists to prevent, and the seventh
        time that class has appeared here. `shlex.quote` had already made the
        probe SAFE; safe is not the same as real.

        Guessing a name from text is allowed. Believing the guess is not.
        """
        new = sorted(set(tools_after) - set(tools_before))
        if new:
            return new[-1]
        for cmd, _ in reversed(executed):
            m = trigmod.TOOL_WRITE_RE.search(cmd)
            if m:
                tail = cmd[m.end():].strip().split()
                if tail:
                    guess = os.path.basename(tail[0].strip("'\""))
                    # Only if the library actually holds it.
                    if guess in tools_after:
                        return guess
        return tools_after[-1] if tools_after else ""

    def evidence(self, target, executed):
        """What the cousin is shown. It runs the tool ITSELF -- the transcript
        is the cousin's own attempt, never a replay of the creature's."""
        path = os.path.join(self.body.mind, "tools", "own", target)
        header = ""
        if target and os.path.exists(path):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    header = "".join(f.readlines()[:8])
            except OSError:
                header = ""
        # What the tool says it needs. The trial learned this the expensive way:
        # calling every tool bare put a visible failure in 11 of 12 transcripts,
        # including every control, and the judge returned work that was fine.
        # A tool invoked wrongly has not been tested -- it has been mishandled.
        call_line = ""
        for line in (header or "").splitlines():
            if line.strip().startswith("# call:"):
                call_line = line.split(":", 1)[1].strip()
                break
        needs_args = bool(call_line and len(call_line.split()) > 1)

        # WHAT ELSE IS ALREADY THERE. Without this the cousin judges every tool
        # in isolation and cannot answer its own third test -- "is this new, or
        # the fifth variant of something it has?" -- which the brief calls a
        # judgment no checker can make and one of the main reasons it exists.
        #
        # Measured 2026-09-12 over 40 cycles: the creature built four greps and
        # two readers, including two duplicate-stem twins, and the cousin
        # accepted every one. It was never shown the library, so the comparison
        # it is asked to make was not available to it. That is a structural gap,
        # not a prompt weakness: no rewording helps a judge that cannot see what
        # it is comparing against.
        # BOTH `# does:` and `# call:` come through `library.render`. The
        # does-line says what a tool is for; the call-line says what it can be
        # ASKED to do, and without the second the cousin cannot tell a tool
        # with sub-commands from one without.
        #
        # 2026-09-13, measured over an evening: it accepted work and asked for
        # "Ability to add and update steps in the plan" three times in
        # different words, while `plan add-step` already worked. All three
        # restatements stood in the creature's direction at once -- one idea
        # filling a channel bounded to three. It was not being shown that the
        # capability existed.
        #
        # `title=None` because the cousin's own LIBRARY_TEMPLATE already frames
        # the list; two headings over one list is the sort of seam a reader
        # spends attention on.
        library = librarymod.render(
            os.path.join(self.body.mind, "tools", "own"), self.j,
            exclude=target, title=None)

        claim = "I finished %s." % (target or "this work")
        if target:
            # Invoke BY NAME, never by a path this code assembles. 2026-09-11,
            # first live run: os.path.join produced `tools\own\fetcher.py` on
            # Windows and the cousin reported "command not found" six times over
            # a tool that was perfectly good. The creature was told its working
            # work was broken, by the framework, in honest words about a false
            # event -- the exact fault this whole design exists to prevent.
            #
            # QUOTED, because a filename is data and must never become shell
            # source. 2026-09-12, first run on the real rung: a file briefly
            # named "`." appeared in tools/own, the probe interpolated it raw,
            # and bash died with "unexpected EOF while looking for matching `".
            # The cousin then reported a syntax error the creature's tool never
            # had. Same class as the line above and the third time it has been
            # this exact shape -- and the sharper edge is that an unquoted name
            # is not merely fragile, it EXECUTES: a file called `$(rm -rf ~)`
            # would have run. The creature names its own files, so the name is
            # untrusted input to this line.
            r = self.body.run(shlex.quote(target))
            # The cousin's OWN attempt, recorded as fact. Nothing else can check
            # whether its testimony describes an event that actually happened --
            # and a fabricated complaint is the exact fault this design exists
            # to prevent, committed by the agent meant to catch it.
            # `bare` is the honest qualifier on the exit code, and without it
            # the record LIES. 2026-09-14: of 153 probes, 39 exited 0 and 97
            # were the tool correctly refusing incomplete input -- the brief
            # counts that as the tool doing its job. Only ~12 were real
            # failures. The probe always invokes the tool with NO ARGUMENTS,
            # so a tool that requires one can never exit 0, and a run-record
            # that counts those as failures reports a healthy library as a
            # broken one. I built exactly that display two hours before
            # measuring this, and read a creature "building storeys on a
            # broken floor" out of a number the harness manufactures.
            self.j.append("cousin_probe", tool=target, exit_code=r.code,
                          bare=needs_args,
                          stdout=capped(r.stdout, EXEC_STDOUT_CHARS),
                          stderr=capped(r.stderr, EXEC_STDERR_CHARS))
            transcript = "$ %s\nexit %d\n%s%s" % (
                target, r.code,
                capped(r.stdout, EXEC_STDOUT_CHARS),
                ("\n" + capped(r.stderr, EXEC_STDERR_CHARS)) if r.stderr else "")
            if needs_args:
                # Say plainly that the call was incomplete. Without this the
                # judge reads a usage message as a fault and punishes the tool
                # for being called wrongly -- and the creature can never pass,
                # because the empty hands are the cousin's, not its own.
                transcript += ("\n\n(I called it with NO ARGUMENTS, because I had "
                               "none to give it. Its own usage line says: %s)"
                               % call_line)
        else:
            transcript = "(nothing to run)"
        return claim, header, transcript, library
