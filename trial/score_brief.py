#!/usr/bin/env python3
"""score_brief.py -- the one runner, and it cannot report half a score.

PLAN item 8.2. `run_trial.py` will happily measure detection on its own, and
on 2026-09-11 that is exactly what went wrong: a mock fetcher scored **10/10
detection** and was then **ACCEPTED 5/5** once its timestamps moved to today
and nothing else changed. It had never been detected as fabrication -- it had
been detected as old dates -- and a 99.1%% detection figure sat on top of that
for a week. The rule earned there is stated in `CLAUDE.md` §5 and has no
enforcement anywhere:

  **Never report a detection number without a correction number beside it.**

So this wrapper runs both halves and prints one block. When the correction
half has no cases it says **NOT MEASURABLE**, loudly, with the reason and the
condition that would change it -- because the failure mode is a detection
figure travelling alone, and an absent denominator travels just as far as a
wrong one.

    TRIAL_API_KEY=$(cat ~/keys/gemini-gemma31b.key) \\
      python3 trial/score_brief.py --model gemma-4-31b-it \\
        --backend openai --host https://.../chat/completions --label baseline
"""
import argparse
import glob
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DETECT = os.path.join(HERE, "heldout-cases.json")
CORRECT = os.path.join(HERE, "heldout-repair-cases.json")
BASELINES = os.path.join(HERE, "baselines")


def load_cases(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return None, "unreadable: %s" % path
    cases = (doc.get("cases") if isinstance(doc, dict) else doc) or []
    return cases, (doc.get("_why_empty") or "") if isinstance(doc, dict) else ""


def newest_result(out_dir, after):
    files = [p for p in glob.glob(os.path.join(out_dir, "*.jsonl"))
             if os.path.getmtime(p) >= after]
    return max(files, key=os.path.getmtime) if files else None


def run_half(args, cases_file, tag):
    """One `run_trial.py` invocation. Returns its rows, or None."""
    out_dir = os.path.join(args.out, tag)
    os.makedirs(out_dir, exist_ok=True)
    started = time.time() - 1
    cmd = [sys.executable, os.path.join(HERE, "run_trial.py"),
           "--model", args.model, "--backend", args.backend,
           "--host", args.host, "--cases", cases_file, "--out", out_dir,
           "--reps", str(args.reps), "--label", "%s-%s" % (args.label, tag)]
    if args.max_tokens:
        cmd += ["--max-tokens", str(args.max_tokens)]
    print("\n>>> %s half: %s" % (tag, " ".join(cmd[-8:])))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.stderr.write("the %s half exited %d\n" % (tag, r.returncode))
    path = newest_result(out_dir, started)
    if not path:
        return None
    rows = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def tally(rows):
    scored = [r for r in rows if r.get("expect") != "OBSERVE"]
    ret = [r for r in scored if r.get("expect") == "RETURNED"]
    acc = [r for r in scored if r.get("expect") == "ACCEPTED"]
    return {
        "n": len(scored),
        "caught": sum(1 for r in ret if r.get("verdict") == "RETURNED"),
        "of_broken": len(ret),
        "falsely_returned": sum(1 for r in acc if r.get("verdict") == "RETURNED"),
        "of_good": len(acc),
        "unreadable": sum(1 for r in scored if not r.get("verdict")),
        "answered": sum(1 for r in scored if r.get("verdict")),
        "call_errors": sum(1 for r in scored if r.get("call_error")),
        "call_error_kinds": sorted({str(r.get("call_error")).split(":")[0]
                                    for r in scored if r.get("call_error")}),
    }


def detection_line(d):
    """`(measurable, text)`. A RATE IS ONLY A RATE IF THE JUDGE ANSWERED.

    The first baseline attempt returned `caught 0/8 broken, falsely returned
    0/8 good` -- which reads as a brief that catches nothing -- when what had
    actually happened was sixteen `HTTP 429`s: the free tier was busy and the
    judge was never reached. Zero readable verdicts, and this printed a score
    over them.

    `run_trial` already refuses to START against a dead backend, for exactly
    this reason and in those words (*"a results file full of failures the
    model never made is worse than no file"*). A rung that dies mid-run walks
    straight past that check, so the same refusal belongs here, where the
    number is finally spoken.
    """
    if not d["n"]:
        return False, "no cases were scored at all"
    if not d["answered"]:
        why = (", ".join(d["call_error_kinds"]) or "no verdict block in any reply")
        return False, ("the judge never answered -- %d/%d calls produced no "
                       "readable verdict (%s). This measures the rung, not the "
                       "brief." % (d["unreadable"], d["n"], why))
    if d["answered"] < d["n"]:
        return True, ("caught %d/%d broken     falsely returned %d/%d good"
                      "   [%d of %d replies unreadable -- the rates below are "
                      "over what ANSWERED]"
                      % (d["caught"], d["of_broken"], d["falsely_returned"],
                         d["of_good"], d["unreadable"], d["n"]))
    return True, ("caught %d/%d broken     falsely returned %d/%d good"
                  % (d["caught"], d["of_broken"], d["falsely_returned"],
                     d["of_good"]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--backend", default="ollama", choices=["ollama", "openai"])
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--label", default=None)
    ap.add_argument("--detection", default=DETECT)
    ap.add_argument("--correction", default=CORRECT)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "heldout"))
    args = ap.parse_args(argv)
    args.label = args.label or time.strftime("%Y%m%d-%H%M")

    dcases, _ = load_cases(args.detection)
    ccases, why_empty = load_cases(args.correction)
    if not dcases:
        sys.stderr.write("no held-out detection cases at %s\n" % args.detection)
        return 2

    drows = run_half(args, args.detection, "detection")
    crows = run_half(args, args.correction, "correction") if ccases else None

    d = tally(drows or [])
    c = tally(crows or []) if crows else None

    print("\n" + "=" * 72)
    print("HELD-OUT SCORE -- %s -- %s -- %d rep(s)"
          % (args.model, args.label, args.reps))
    print("=" * 72)
    measurable, line = detection_line(d)
    print("DETECTION   %s%s" % ("" if measurable else "**NOT MEASURABLE** -- ",
                                line))
    if c:
        print("CORRECTION  accepted %d/%d real repairs"
              % (c["of_good"] - c["falsely_returned"], c["of_good"]))
    else:
        print("CORRECTION  **NOT MEASURABLE** -- no held-out correction case "
              "exists yet.")
        for line in (why_empty or "no reason recorded").split(". "):
            if line.strip():
                print("            %s." % line.strip().rstrip("."))
        print("            Read the detection figure with that missing: a "
              "detection score")
        print("            has sat on top of a total failure at correction in "
              "this project before.")
    if d["unreadable"] and measurable:
        print("NOTE        %d repl(ies) carried no readable verdict; those are "
              "neither" % d["unreadable"])
        print("            caught nor missed, and a rate over them measures the "
              "rung, not the brief.")
    print("\nOne pass is an anecdote. This framework is not deterministic, so a "
          "brief change\nis scored by a DIRECTION that survives several runs, "
          "split by model -- never by\none number moving.")

    os.makedirs(BASELINES, exist_ok=True)
    path = os.path.join(BASELINES, "%s_%s.json"
                        % (args.label, args.model.replace("/", "_")))
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"model": args.model, "label": args.label, "reps": args.reps,
                   "detection": d, "correction": c,
                   "detection_measurable": measurable,
                   "detection_not_measurable": None if measurable else line,
                   "correction_not_measurable": None if c else (why_empty or True),
                   "cases": {"detection": os.path.basename(args.detection),
                             "correction": os.path.basename(args.correction)},
                   "when": time.time(), "when_str": time.strftime("%Y-%m-%d %H:%M")},
                  f, indent=1)
    print("written: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
