#!/usr/bin/env python3
"""library.py -- what the creature has built, and whether its user ever ran it.

Two facts about every tool, both DERIVED from the journal, neither a judgement:
what the tool says it is for, and what happened the last time the person who
needs it actually ran it. No opinion is formed here and nothing is withheld.
That placement is deliberate and was decided 2026-09-13 (Tue):

- **Running the test belongs to the cousin.** The builder is structurally
  unable to judge its own work -- it knows what it meant, which is exactly the
  knowledge a user does not have.
- **Enforcing the verdict belongs to nobody.** A cousin that can keep a tool
  out of the library is a second builder through the back door (CLAUDE.md
  §2.3) and a second judge with no judge of its own, which is why `census.py`
  reports and never gates. On a bad model day it would wall a working tool and
  the creature could not route around it.
- **Recording who ran what belongs HERE**, in the framework, because it is a
  bound and not an opinion: a count and an exit code, already in the journal.

So the pressure this file applies is visibility, not a gate. A creature looking
at its own library sees which of its tools its user has never once touched.

**It counts the COUSIN's probes and nothing else.** The creature runs its own
tools constantly while building them; counting that would make every tool look
exercised the moment it was written, which is the top scar in CLAUDE.md §5 --
a checker that cannot distinguish the thing it measures reports a clean-looking
wrong number, never an error. `test_library_counts_only_its_users_runs` is the
assertion that keeps these two populations apart.

The listing is shown to BOTH inhabitants, and the wording is the same for each
because two audience-specific strings is two chances to get the audience
backwards. "Its user" is the cousin, stated in the legend rather than inferred.
"""
import os

from . import triggers as trigmod

LIBRARY_LIMIT = 40
HEADER_LINES = 8

LEGEND = ("Its user is the person your work is for -- the one whose verdicts "
          "reach you. Runs counted here are THEIRS, never your own.")


def headers(path):
    """The tool's own `# does:` and `# call:` lines, or empty strings.

    A tool's header is a CLAIM, not an instrument -- it says what the author
    intended, which is why it sits beside a run count rather than instead of
    one.
    """
    does = call = ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f.readlines()[:HEADER_LINES]:
                t = line.strip()
                if t.startswith("# does:") and not does:
                    does = t.split(":", 1)[1].strip()
                elif t.startswith("# call:") and not call:
                    call = t.split(":", 1)[1].strip()
    except OSError:
        pass
    return does, call


def use_history(journal):
    """name -> {runs, last_code} from `cousin_probe`, the cousin's own attempts.

    `cousin_probe` is the record of the cousin actually executing a tool, with
    the real exit code. It is the only event in the journal that means someone
    other than the author ran the thing.
    """
    out = {}
    if journal is None:
        return out
    try:
        rows = journal.read(kinds=["cousin_probe"])
    except Exception:
        return out
    for r in rows:
        name = (r.get("tool") or "").strip()
        if not name:
            continue
        rec = out.setdefault(name, {"runs": 0, "ok": 0, "asked": 0,
                                    "last_code": None})
        rec["runs"] += 1
        if r.get("exit_code") == 0:
            rec["ok"] += 1
        elif r.get("bare"):
            # CALLED WITH NO ARGUMENTS, by a tool whose own call-line says it
            # takes some. Refusing that and saying what it needs is the tool
            # working, not failing -- the brief says so explicitly -- and
            # counting it as a failure is the framework inventing a complaint.
            rec["asked"] += 1
        rec["last_code"] = r.get("exit_code")
    return out


def status(rec):
    """One line of fact. No adjectives -- counts and an exit code.

    **THE RECORD, NOT THE LAST EVENT.** Until 2026-09-14 this said "its user
    ran this 31 times; the last run exited 1", which is true and useless: a
    tool that has NEVER ONCE worked rendered identically to one that works and
    failed once. Measured the same day, on the live library: `plan` returned 0
    on its first probe and non-zero on the thirty after it, and read as though
    it were fine; `integrate-subagent-orchestrator-with-plan` had failed eight
    times and succeeded twice, and read as "the last run exited 0".

    That is the oldest fault in this project -- a display that cannot
    distinguish the thing it measures -- committed in the column built to make
    exactly this visible. Both inhabitants read this line every wake, so both
    were being shown a broken floor as a sound one.

    "Never run" and "never worked" are the two load-bearing cases and both are
    stated plainly, because a tool nobody has used and a tool nobody has
    succeeded with are different problems with different answers.
    """
    if not rec or not rec.get("runs"):
        return "its user has NEVER run this"
    n, ok, asked = rec["runs"], rec.get("ok", 0), rec.get("asked", 0)
    times = "once" if n == 1 else "%d times" % n
    code = rec.get("last_code")
    failed = n - ok - asked
    # A bare call that got a usage message back is not a failure, so it is
    # never reported as one. It is still worth saying, because "your user
    # keeps reaching for this without knowing how to call it" is real.
    note = "" if not asked else (", and %s asked for arguments"
                                 % ("once" if asked == 1 else "%d times" % asked))
    if failed == 0 and ok == 0:
        return "its user ran this %s%s, never getting further" % (times, note)
    if failed == 0:
        return ("its user ran this %s and it worked" % times if n == 1
                else "its user ran this %s, and it worked every time it was "
                     "called properly%s" % (times, note))
    if ok == 0:
        return ("its user ran this %s and it has NEVER WORKED for them "
                "(%d real failures%s); the last exited %s"
                % (times, failed, note, code))
    return ("its user ran this %s, %d worked and %d FAILED%s; the last exited %s"
            % (times, ok, failed, note, code))


def render(tools_dir, journal=None, exclude=None, limit=LIBRARY_LIMIT,
           title="## The tools you have built"):
    """The whole library as the inhabitants see it. Empty string when empty.

    Ordering is alphabetical and therefore STABLE between wakes. Sorting the
    never-run tools to the top would make them louder, and would also make the
    list move under a reader who is trying to recognise it -- a bound that
    changes shape every cycle is a bound nobody learns.
    """
    names = [t for t in trigmod.list_tools(tools_dir) if t != exclude]
    if not names:
        return ""
    hist = use_history(journal)
    lines = []
    for name in names[:limit]:
        does, call = headers(os.path.join(tools_dir, name))
        lines.append("- %s%s" % (name, (" - " + does) if does else ""))
        if call:
            lines.append("    used as: %s" % call)
        lines.append("    %s" % status(hist.get(name)))
    body = "\n".join(lines)
    if not title:
        return body
    return "%s\n\n%s\n\n%s" % (title, body, LEGEND)
