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

#: How many departed tools the listing carries. BOUNDED, newest first, for the
#: reason every bound here exists: a block that grows with the age of the run
#: is the wake-cost failure class arriving by a new door, and this one is
#: already ~42% of a wake. Past the bound the count is still printed, because
#: a bound must degrade rather than hide (2026-09-15).
GRAVEYARD_LIMIT = 12

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
        rows = journal.read(kinds=["cousin_probe", "cousin_verdict"])
    except Exception:
        return out
    for r in rows:
        name = (r.get("tool") or "").strip()
        if not name:
            continue
        if r.get("kind") == "cousin_verdict":
            # WHAT ITS USER SAID, per tool. A fact about testimony, and the
            # only honest replacement for the *FAILED* the framework used to
            # compute from an exit code: once the cousin chooses the
            # arguments, a non-zero exit is not the framework's to judge.
            v = r.get("verdict")
            if v in ("ACCEPTED", "RETURNED"):
                rec = out.setdefault(name, {"runs": 0, "ok": 0, "asked": 0,
                                            "unqualified": 0, "nonzero": 0,
                                            "accepted": 0, "returned": 0,
                                            "last_code": None})
                rec["accepted" if v == "ACCEPTED" else "returned"] += 1
            continue
        if r.get("exit_code") is None:
            # NOTHING RAN -- the ladder never answered when the cousin was
            # asked what to type. Counting it as a run would tell both
            # inhabitants their user had tried something it never tried, and
            # `choose_target`'s `least_probed` would walk away from a tool
            # that has still never been probed.
            continue
        rec = out.setdefault(name, {"runs": 0, "ok": 0, "asked": 0,
                                    "unqualified": 0, "nonzero": 0,
                                    "accepted": 0, "returned": 0,
                                    "last_code": None})
        rec["runs"] += 1
        if r.get("exit_code") == 0:
            rec["ok"] += 1
        elif "bare" not in r:
            # RECORDED BEFORE THE FLAG EXISTED (f52ac78, 2026-09-14). Without
            # it a refusal and a failure are the same non-zero exit, so the
            # honest count is a third bucket: neither. Counting these as
            # failures re-creates, for every probe of the first day and a
            # half, exactly the misreading the flag was added to end.
            rec["unqualified"] += 1
        elif r.get("bare"):
            # CALLED WITH NO ARGUMENTS, by a tool whose own call-line says it
            # takes some. Refusing that and saying what it needs is the tool
            # working, not failing -- the brief says so explicitly -- and
            # counting it as a failure is the framework inventing a complaint.
            rec["asked"] += 1
        else:
            # NON-ZERO, WITH ARGUMENTS ITS USER CHOSE. Not "failed": the
            # cousin may have invented the ID and the tool may have correctly
            # said so. That judgement is the cousin's and arrives as a
            # verdict; this is the count of what happened.
            rec["nonzero"] += 1
        rec["last_code"] = r.get("exit_code")
    return out


def qualified_runs(rec):
    """How many probes actually TOLD US SOMETHING about this tool.

    A bare call that came back with a usage line says the tool works and
    nothing about whether it does its job; a probe recorded before the `bare`
    flag existed cannot be classified at all; a probe the ladder never
    answered never reached the tool (those are not in `runs`). None of the
    three is knowledge. What counts is a real invocation with a real exit
    code: `ok` plus genuine failures.

    ONE definition, here, because two copies of a rule drift and no test
    notices -- already paid for in this repo by `wants()`, by the caps and by
    the census. `choose_target` ranks on it and `status` renders from it.
    """
    if not rec:
        return 0
    return max(0, rec.get("runs", 0) - rec.get("asked", 0)
               - rec.get("unqualified", 0))


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
    unq = rec.get("unqualified", 0)
    nonzero = rec.get("nonzero", max(0, n - ok - asked - unq))
    times = "once" if n == 1 else "%d times" % n
    code = rec.get("last_code")
    # A bare call that got a usage message back is not a failure, so it is
    # never reported as one. It is still worth saying, because "your user
    # keeps reaching for this without knowing how to call it" is real.
    note = "" if not asked else (", and %s asked for arguments"
                                 % ("once" if asked == 1 else "%d times" % asked))
    if unq:
        # Neither a failure nor a success: the record cannot say which.
        note += (", and %s from before the call was recorded (unknown "
                 "outcome)" % ("once" if unq == 1 else "%d times" % unq))
    # WHAT ITS USER SAID. "FAILED" and "NEVER WORKED" were retired 2026-09-16:
    # once the cousin chooses the arguments, a non-zero exit may be the tool
    # correctly refusing an invented ID, and the framework cannot tell. The
    # verdict can, and it is a fact about testimony, so it is reported as
    # such -- beside the exit codes, never instead of them.
    acc, ret = rec.get("accepted", 0), rec.get("returned", 0)
    said = ""
    if acc or ret:
        said = " -- its user accepted it %s and returned it %s" % (
            "once" if acc == 1 else "%d times" % acc,
            "once" if ret == 1 else "%d times" % ret)
    if nonzero == 0 and ok == 0:
        return "its user ran this %s%s, never getting further%s" % (times, note, said)
    if nonzero == 0:
        return (("its user ran this %s and it worked" % times if n == 1
                 else "its user ran this %s, and it worked every time it was "
                      "called properly%s" % (times, note)) + said)
    if ok == 0:
        return ("its user ran this %s and it has never exited 0 for them "
                "(%d exited non-zero with arguments its user chose%s); the "
                "last exited %s%s" % (times, nonzero, note, code, said))
    return ("its user ran this %s: %d exited 0 and %d exited non-zero with "
            "arguments its user chose%s; the last exited %s%s"
            % (times, ok, nonzero, note, code, said))


def graveyard(journal, tools_dir, limit=GRAVEYARD_LIMIT):
    """Tools that were in the library and are not now. Newest departure first.

    **Tue, 2026-09-21:** *"if we delete unused tools completely with no memory
    they existed and was never used, they would just be made again."*

    `CREATURE-PROMPT.md` already carries the rule -- *do not rebuild what you
    own* -- and tells the creature to run `ls tools/own/` when unsure. **`ls`
    shows what exists now.** A tool that was built, never came back to, and
    removed left no trace anywhere either inhabitant is shown: measured
    2026-09-21, zero removed names in an 11,617-character library block.

    That is the 2026-09-12 shape, and that scar says what to do about it:
    *before adding a rule, check whether the evidence that rule needs is
    actually on the page.* The rule was already right then too; the library
    simply was not being shown.

    **Facts only.** Name, when it left, how many times its USER ran it before
    it went, and which live tools contain its words. Whether that means
    *consolidated*, *abandoned* or *worth rebuilding* is the creature's to
    decide -- a scan gathers a fact and then decides what to say about it, and
    only the first half is framework (§2.3).
    """
    if journal is None:
        return []
    try:
        rows = journal.read(kinds=["tools_changed"])
    except Exception:
        return []
    left = {}
    for r in rows:
        for n in (r.get("added") or []):
            left.pop(n, None)          # it came back; it is not departed
        for n in (r.get("removed") or []):
            left[n] = float(r.get("ts") or 0)
    live = set(trigmod.list_tools(tools_dir))
    # A name that is on disk now is not in the graveyard whatever the journal
    # says -- the directory is the library, the journal is only how it moved.
    # And a BACKUP was never a member, so it cannot have left: `.testbak`
    # slipped past `NOT_A_TOOL` for the life of the project and came back on
    # 2026-09-21 as a capability the creature had removed.
    gone = sorted(((ts, n) for n, ts in left.items()
                   if n not in live and not trigmod.is_backup(n)),
                  reverse=True)

    hist = use_history(journal)
    srcs = {}
    for n in live:
        try:
            with open(os.path.join(tools_dir, n), encoding="utf-8",
                      errors="replace") as f:
                srcs[n] = f.read()
        except OSError:
            pass

    out = []
    for ts, name in gone[:limit]:
        rec = hist.get(name) or {}
        # WHICH LIVE TOOL CARRIES ITS DISTINCTIVE PART, as a literal. The
        # first version matched every word longer than three characters, so
        # `plan-set-goal` came back as *its words are in `plan`,
        # `plan-analyze-bottlenecks`, `integrate-subagent-orchestrator`* --
        # true, and useless, because the words were `plan` and `goal`.
        #
        # What follows the first hyphen is what makes a tool itself.
        # Against the real library that gives `plan-set-goal -> plan`,
        # `plan-clear-goal -> plan`, `plan-link-archive -> plan` and **nothing
        # at all** for the other seven -- and the nothings are the entries
        # worth reading, because those are the removals that left no trace.
        verb = name.split("-", 1)[1] if "-" in name else name
        where = sorted(n for n, src in srcs.items() if verb in src)
        out.append({"tool": name, "removed_ts": ts,
                    "runs": rec.get("runs", 0), "ok": rec.get("ok", 0),
                    "asked": rec.get("asked", 0),
                    "words_survive_in": where[:3]})
    return out


def render_graveyard(journal, tools_dir, limit=GRAVEYARD_LIMIT):
    """The graveyard as lines, or nothing at all when nothing has left.

    An empty heading every wake is noise a reader learns to skip, which is the
    parent's *surface on a change of state, never continuously*.
    """
    if journal is None:
        return []
    try:
        rows = journal.read(kinds=["tools_changed"])
    except Exception:
        return []
    g = graveyard(journal, tools_dir, limit=limit)
    if not g:
        return []
    total = 0
    live = set(trigmod.list_tools(tools_dir))
    seen = {}
    for r in rows:
        for n in (r.get("added") or []):
            seen.pop(n, None)
        for n in (r.get("removed") or []):
            seen[n] = True
    # The SAME filter as the listing, or the bound announces "1 more, older"
    # about a backup it would never show -- a count and a list that disagree,
    # which is how a reader learns to distrust both.
    total = sum(1 for n in seen if n not in live and not trigmod.is_backup(n))

    lines = ["", "## What you built and removed", "",
             "These were in your toolkit and are not now. The count is your "
             "USER's runs before it went, not your own -- so a tool nobody "
             "ever reached for says so. What it means is yours to read: a "
             "capability you folded into something else is not the same as "
             "one you dropped, and either may be worth having again or worth "
             "leaving alone."]
    for row in g:
        bits = ["%d run%s by its user"
                % (row["runs"], "" if row["runs"] == 1 else "s")]
        if row["asked"]:
            bits.append("%d of them with no arguments" % row["asked"])
        if row["words_survive_in"]:
            verb = (row["tool"].split("-", 1)[1] if "-" in row["tool"]
                    else row["tool"])
            bits.append("`%s` now contains `%s`"
                        % ("` and `".join(row["words_survive_in"]), verb))
        lines.append("- %s - %s" % (row["tool"], "; ".join(bits)))
    if total > len(g):
        lines.append("- ...and %d more, older" % (total - len(g)))
    return lines


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
    # THE LIMIT BOUNDS THE FULL ENTRIES, NEVER THE NAMES. Until 2026-09-15 it
    # was `names[:limit]` and nothing else: the library crossed 40 at 07:00,
    # and the seven tools past the cut -- alphabetically the `subtask-*`,
    # `synthesize-*` and `view-*` family, i.e. every tool the creature had
    # built that day to answer one repeated want -- were shown to NOBODY.
    # The creature could not see its own previous answers and built a sixth.
    # A bound on context size must DEGRADE the listing, never hide from it:
    # past the limit each tool keeps its name and purpose on one line, which
    # is the minimum the anti-twin comparison needs.
    rest = names[limit:]
    if rest:
        lines.append("")
        lines.append("Also here, by name and purpose only (%d more; nothing is "
                     "hidden from this list):" % len(rest))
        for name in rest:
            does, _call = headers(os.path.join(tools_dir, name))
            lines.append("- %s%s" % (name, (" - " + does) if does else ""))
    lines.extend(render_graveyard(journal, tools_dir))
    body = "\n".join(lines)
    if not title:
        return body
    return "%s\n\n%s\n\n%s" % (title, body, LEGEND)
