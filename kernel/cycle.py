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

from . import body as bodymod
from . import cousin as cousinmod
from . import think as thinkmod
from . import triggers as trigmod
from .journal import EXEC_CMD_CHARS, EXEC_STDERR_CHARS, EXEC_STDOUT_CHARS, capped


class Engine:
    def __init__(self, journal, body, brief, ask_creature, ask_cousin,
                 context_path):
        self.j = journal
        self.body = body
        self.brief = brief
        self.ask_creature = ask_creature
        self.ask_cousin = ask_cousin
        self.context_path = context_path
        self.cycles_since_visit = 0
        self.cycles_since_change = 0
        self.done_blocked = None       # testimony the creature must see next wake

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
        if os.path.exists(self.context_path):
            with open(self.context_path, encoding="utf-8") as f:
                parts.append(f.read())
        return "\n\n---\n\n".join(p for p in parts if p)

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

    def recent_block(self, cycles=3):
        """The last few things it ran and what came back -- already capped, with
        the loss announced where it was cut."""
        rows = self.j.read(kinds=["exec_start", "exec_end", "exec_skip"],
                           limit=cycles * 6)
        if not rows:
            return ""
        out = ["## What you just did", ""]
        for r in rows:
            if r["kind"] == "exec_start":
                out.append("```\n$ %s\n```" % (r.get("cmd") or ""))
            elif r["kind"] == "exec_end":
                body = (r.get("stdout") or "").rstrip()
                err = (r.get("stderr") or "").rstrip()
                out.append("exit %s%s" % (r.get("exit_code"),
                                          ("\n" + body) if body else ""))
                if err:
                    out.append("stderr: " + err)
            else:
                out.append("(nothing ran: %s)" % r.get("reason"))
        out.append("\n**Do not run any of those again.** You already have the "
                   "answer; act on it.")
        return "\n".join(out)

    def write_context(self, text):
        d = os.path.dirname(self.context_path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(self.context_path, "w", encoding="utf-8") as f:
            f.write(text)

    # ------------------------------------------------------------------ cycle

    def run_cycle(self):
        """Returns a dict describing what happened. Substantive = something ran."""
        tools_dir = os.path.join(self.body.mind, "tools", "own")
        tools_before = trigmod.list_tools(tools_dir)

        context = self.serve_context()
        self.done_blocked = None

        self.j.append("wake", context_chars=len(context))
        try:
            reply, meta = self.ask_creature(context)
        except Exception as e:
            self.j.append("error", where="think",
                          detail="%s: %s" % (type(e).__name__, e))
            return {"substantive": False, "reason": "think_failed"}

        meta = meta or {}
        self.j.append("think", chars=len(reply or ""),
                      model=meta.get("model"), finish=meta.get("done_reason"))

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
            # A visit is the ANSWER to whatever fired. Both counters reset, or a
            # STALL re-fires on every subsequent cycle and the cousin becomes a
            # nag the creature learns to skip -- the parent's rule is surface on
            # a CHANGE of state, never continuously.
            self.cycles_since_visit = 0
            self.cycles_since_change = 0
        else:
            self.cycles_since_visit += 1
        return result

    # ----------------------------------------------------------------- cousin

    def visit_cousin(self, fired, executed, tools_after, tools_before):
        trigger, _fields = fired
        target = self.pick_target(executed, tools_after, tools_before)
        claim, header, transcript = self.evidence(target, executed)

        v = cousinmod.visit(self.ask_cousin, self.brief, claim, header,
                            transcript, journal=self.j, trigger=trigger)

        if v.verdict == cousinmod.UNKNOWN:
            # Gates nothing. An instrument that cannot run says UNKNOWN.
            self.j.append("cousin_unusable", error=v.error)
            return v
        if v.blocks_done:
            self.done_blocked = v.to_creature
        return v

    def pick_target(self, executed, tools_after, tools_before):
        new = sorted(set(tools_after) - set(tools_before))
        if new:
            return new[-1]
        for cmd, _ in reversed(executed):
            m = trigmod.TOOL_WRITE_RE.search(cmd)
            if m:
                tail = cmd[m.end():].strip().split()
                if tail:
                    return os.path.basename(tail[0].strip("'\""))
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

        claim = "I finished %s." % (target or "this work")
        if target:
            # Invoke BY NAME, never by a path this code assembles. 2026-09-11,
            # first live run: os.path.join produced `tools\own\fetcher.py` on
            # Windows and the cousin reported "command not found" six times over
            # a tool that was perfectly good. The creature was told its working
            # work was broken, by the framework, in honest words about a false
            # event -- the exact fault this whole design exists to prevent.
            r = self.body.run(target)
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
        return claim, header, transcript
