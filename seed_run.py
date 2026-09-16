#!/usr/bin/env python3
"""seed_run.py -- start a run, with or without an inherited library.

PLAN item 11. `CLAUDE.md` §6.2 decided on 2026-09-10 to **copy the parent's
tools**, because that library is a known-answer test set -- *"23 tools that
cannot start, 39 twins, ~50 returning error text as their value"* -- and a
cousin that accepts a handover of a tool which will not start is refuted in a
week rather than in months. Run 1 and run 2 both began from nothing, so the
decision has never been executed and the refutation has never been attempted.
Recorded as not-done in §6.2 and ARCHITECTURE §11 on 2026-09-16; this is the
machinery that would carry it out.

**Two things it will not do.**

It never DELETES a run. The previous root is moved aside, dated, the way run
1 was on 2026-09-13 (`archive-contaminated-20260913-1244`) -- because a
trajectory cannot be repaired retroactively and a run you cannot go back and
read is a measurement you have to take on trust.

It never copies a tool without TAGGING it. §6.2's condition is *"tagging
every inherited tool at t=0 and splitting every metric on it, for the life of
the project"*, and an untagged copy is worse than no copy: every figure
afterwards silently mixes what the creature built with what it was handed,
and nobody can tell which library the cousin was judging.

    python3 seed_run.py --root ~/growing-cousin/live --inherit ~/growing-spine-mind
    python3 seed_run.py --root ~/growing-cousin/live --empty
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

INHERITED = "inherited.json"
NOT_A_TOOL = (".bak", ".orig", ".tmp", ".swp", ".rej", "~")


class Refused(Exception):
    """Something is alive in there, or the target is not ours to take."""


def why_it_cannot_start(path):
    """The interpreter's own words, or None if the file starts fine.

    Reads; never executes -- §2.6 forbids running anything of the parent's,
    and its tools would write into its creature's world. A syntax error is
    the one defect that needs no opinion: the tool cannot run for anybody, on
    any day, under any brief.

    THE canonical implementation. `trial/make_heldout.py` imports it rather
    than keeping a second copy, because a producer and a checker that each
    carry their own rule drift and no test notices.
    """
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError:
        return None
    first = src.split(chr(10), 1)[0]
    if "python" in first:
        try:
            compile(src, os.path.basename(path), "exec")
        except SyntaxError as e:
            return "%s: %s (line %s)" % (type(e).__name__, e.msg, e.lineno)
        except ValueError as e:
            return "ValueError: %s" % e
        return None
    if "bash" in first or "/sh" in first:
        import subprocess
        try:
            r = subprocess.run(["bash", "-n", path], capture_output=True,
                               text=True, timeout=20)
        except Exception:
            return None
        if r.returncode != 0:
            return (r.stderr or "").strip().split(chr(10))[-1][:200] or "syntax error"
        return None
    return None


def engine_is_running(unit="cousin-engine.service"):
    import subprocess
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", unit],
                           capture_output=True, text=True, timeout=20)
    except Exception:
        return None                      # cannot tell, and says so
    return (r.stdout or "").strip() == "active"


def check_safe(root, unit="cousin-engine.service"):
    """`(ok, why)`. A creature is living in there until proven otherwise.

    The rehearsal harness learned this the hard way on 2026-09-16: its guard
    ran AFTER it had cleared the target. So this is asked first, by the
    caller, and answers `False` on anything it cannot establish -- a
    `systemctl` it cannot reach is *cannot tell*, and cannot tell is not
    permission.
    """
    running = engine_is_running(unit)
    if running is None:
        return False, ("cannot tell whether %s is running; refusing rather "
                       "than guessing" % unit)
    if running:
        return False, ("%s is ACTIVE. Stop it the documented way first -- "
                       "`touch <root>/STOP` lets the cycle in flight finish; "
                       "`systemctl stop` throws it away." % unit)
    return True, "nothing is running"


def archive_root(root, label="run"):
    """Move the old run aside, dated. Returns the path, or None if there was
    nothing there."""
    if not os.path.isdir(root) or not os.listdir(root):
        return None
    dest = "%s-archive-%s-%s" % (root.rstrip("/\\"), label,
                                 time.strftime("%Y%m%d-%H%M"))
    shutil.move(root, dest)
    return dest


def inherit_library(src_own, dst_own, limit=None):
    """Copy a library and RECORD WHAT WAS COPIED.

    The tag is a file rather than a naming convention: renaming a tool is the
    creature's business and a convention it did not agree to would be broken
    by its first rename -- and then every metric split on it would be quietly
    wrong, which is the failure §6.2's condition exists to prevent.
    """
    os.makedirs(dst_own, exist_ok=True)
    tagged = {}
    names = sorted(n for n in os.listdir(src_own)
                   if os.path.isfile(os.path.join(src_own, n))
                   and not n.startswith(".") and not n.endswith(NOT_A_TOOL))
    for n in names[:limit] if limit else names:
        src = os.path.join(src_own, n)
        try:
            with open(src, "rb") as f:
                blob = f.read()
        except OSError:
            continue
        shutil.copy2(src, os.path.join(dst_own, n))
        os.chmod(os.path.join(dst_own, n), 0o755)
        # THE HASH AND WHETHER IT STARTS. The hash alone can only say
        # "changed", and a change is a fix or a breakage -- `repaired` meant
        # `modified` until an independent verifier said so on 2026-09-16.
        # §6.2 chose this library for `cannot_start 32 -> 23`, so the thing
        # worth counting is whether a tool that COULD NOT RUN now can.
        tagged[n] = {"sha": hashlib.sha256(blob).hexdigest(),
                     "starts": why_it_cannot_start(src) is None}
    return tagged


def write_tag(root, tagged, source):
    doc = {
        "_about": "Every tool in this library at t=0, i.e. INHERITED rather "
                  "than built by the creature. CLAUDE.md §6.2 requires every "
                  "metric to be split on this for the life of the project: "
                  "an untagged copy makes every later figure a mixture of "
                  "what was handed over and what was made.",
        "source": source,
        "at": time.time(),
        "at_str": time.strftime("%Y-%m-%d %H:%M"),
        "count": len(tagged),
        # The hash, not just the name: the creature may REPAIR an inherited
        # tool, which is the capability the whole experiment is about, and a
        # name alone cannot tell a repaired inheritance from an untouched one.
        "tools": tagged,
    }
    with io.open(os.path.join(root, INHERITED), "w", encoding="utf-8",
                 newline="\n") as f:
        json.dump(doc, f, indent=1, sort_keys=True)
    return doc


def load_tag(root):
    try:
        with io.open(os.path.join(root, INHERITED), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def classify_on_tag(root, own_dir):
    """Per tool, what it IS relative to the inheritance: the one place that
    decides, so a count and a listing can never disagree.

    Returns `(by_name, deleted)`, where `by_name` maps each tool now in
    `own_dir` to a dict -- `origin` (the inherited name it descends from, or
    None if the creature built it here), `renamed`, `modified`, `repaired`,
    `broke` -- and `deleted` lists inherited tools that are gone.

    Split out 2026-09-16. `split_on_tag` returned counts and nothing else, so
    a caller that wanted to say *which* tools were inherited had to
    re-implement the hash matching -- two copies of a rule that drift while
    no test notices, which is the fault this repo has already paid for in
    `wants()`, in the caps and in the census. Counts are now derived FROM
    this rather than computed beside it.
    """
    doc = load_tag(root) or {}
    tags = doc.get("tools") or {}
    # Tolerates the pre-2026-09-16 shape, where a tag was a bare hash string.
    norm = {}
    for name, t in tags.items():
        norm[name] = t if isinstance(t, dict) else {"sha": t, "starts": None}
    by_sha = {}
    for name, t in norm.items():
        by_sha.setdefault(t["sha"], name)

    by_name, seen = {}, set()
    try:
        names = sorted(os.listdir(own_dir))
    except OSError:
        return {}, sorted(norm)
    for n in names:
        p = os.path.join(own_dir, n)
        if not os.path.isfile(p) or n.startswith(".") or n.endswith(NOT_A_TOOL):
            continue
        try:
            with open(p, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            continue
        rec = {"origin": None, "renamed": False, "modified": False,
               "repaired": False, "broke": False}
        if n in norm:
            rec["origin"] = n
        elif sha in by_sha:
            # THE HASH IS THE INDEX, so a rename is followed. Keying by name
            # and consulting the hash only after a name match counted a
            # renamed-but-identical tool as BUILT, while PLAN claimed in as
            # many words that a hash-based tag made a rename harmless.
            rec["origin"] = by_sha[sha]
            rec["renamed"] = True
        if rec["origin"] is None:
            by_name[n] = rec
            continue
        seen.add(rec["origin"])
        if sha != norm[rec["origin"]]["sha"]:
            rec["modified"] = True
            was = norm[rec["origin"]].get("starts")
            now = why_it_cannot_start(p) is None
            # `repaired` means what §6.2 chose this library FOR -- a tool that
            # could not start and now starts -- never merely *modified*. Its
            # opposite is counted too: a number that can only move in the
            # flattering direction is not a measurement.
            if was is False and now:
                rec["repaired"] = True
            elif was is True and not now:
                rec["broke"] = True
        by_name[n] = rec
    return by_name, sorted(n for n in norm if n not in seen)


def split_on_tag(root, own_dir):
    """What became of an inherited library, as counts. Derived from
    `classify_on_tag`, which is the only thing that decides.

    **Rewritten 2026-09-16 after a verifier tested it on its own fixtures and
    found all three answers wrong.** The first version keyed the tag by NAME
    and consulted the hash only after a name match, so:

    - a tool RENAMED with identical bytes counted as **built** -- and
      `PLAN.md` claimed in as many words that a hash-based tag made a rename
      harmless, which was the opposite of true;
    - `repaired` meant *modified*, incrementing for a comment, a cosmetic
      edit, or a tool the creature BROKE;
    - a DELETED inheritance vanished from every count, so a creature that
      threw one away looked like one that never had it.
    """
    by_name, deleted = classify_on_tag(root, own_dir)
    out = {"inherited": 0, "renamed": 0, "built": 0, "modified": 0,
           "deleted": len(deleted), "repaired": 0, "broke": 0}
    for _n, rec in by_name.items():
        if rec["origin"] is None:
            out["built"] += 1
            continue
        out["inherited"] += 1
        for k in ("renamed", "modified", "repaired", "broke"):
            if rec[k]:
                out[k] += 1
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--inherit", default=None,
                    help="a mind to copy tools/own from, READ-ONLY")
    ap.add_argument("--empty", action="store_true",
                    help="start from nothing, as runs 1 and 2 did")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--label", default="run")
    ap.add_argument("--unit", default="cousin-engine.service")
    ap.add_argument("--yes", action="store_true",
                    help="required. Without it this only says what it would do.")
    args = ap.parse_args(argv)
    if not args.inherit and not args.empty:
        sys.stderr.write("choose --inherit <mind> or --empty\n")
        return 2

    ok, why = check_safe(args.root, args.unit)
    if not ok:
        sys.stderr.write("REFUSED, nothing touched: %s\n" % why)
        return 3
    src_own = (os.path.join(os.path.expanduser(args.inherit), "tools", "own")
               if args.inherit else None)
    if src_own and not os.path.isdir(src_own):
        sys.stderr.write("REFUSED: no library at %s\n" % src_own)
        return 3
    n_src = len([n for n in os.listdir(src_own)
                 if not n.endswith(NOT_A_TOOL)]) if src_own else 0
    print("would archive %s and start %s" %
          (args.root, "from %d inherited tools" % n_src if src_own else "empty"))
    if not args.yes:
        print("dry run: nothing was touched. Pass --yes to do it.")
        return 0

    moved = archive_root(args.root, args.label)
    os.makedirs(os.path.join(args.root, "body", "mind", "tools", "own"),
                exist_ok=True)
    os.makedirs(os.path.join(args.root, "body", "mind", "data"), exist_ok=True)
    print("archived: %s" % (moved or "(nothing was there)"))
    if src_own:
        dst = os.path.join(args.root, "body", "mind", "tools", "own")
        tagged = inherit_library(src_own, dst, args.limit)
        write_tag(args.root, tagged, args.inherit)
        print("inherited %d tools, tagged in %s/%s"
              % (len(tagged), args.root, INHERITED))
    else:
        write_tag(args.root, {}, None)
        print("started empty; the tag records that nothing was inherited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
