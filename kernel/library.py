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
        rec = out.setdefault(name, {"runs": 0, "last_code": None})
        rec["runs"] += 1
        rec["last_code"] = r.get("exit_code")
    return out


def status(rec):
    """One line of fact. No adjectives -- a count and an exit code.

    "Never run" is the load-bearing case and is stated plainly rather than
    dressed up, because the whole point of the column is that an untouched tool
    should be impossible to miss while reading past it.
    """
    if not rec or not rec.get("runs"):
        return "its user has NEVER run this"
    code = rec.get("last_code")
    n = rec["runs"]
    times = "once" if n == 1 else "%d times" % n
    if code is None:
        return "its user ran this %s" % times
    return "its user ran this %s; the last run exited %d" % (times, code)


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
