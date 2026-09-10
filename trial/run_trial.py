#!/usr/bin/env python3
"""run_trial.py -- put the cousin in front of a known-answer library and score it.

Runs entirely locally. It does NOT touch the laptop, the live creature, or any
free-tier provider: the evidence in cases.json was captured once, read-only, and
is a fixture from here on.

    python run_trial.py --model gemma4:e2b
    python run_trial.py --model qwen2.5-coder:14b --model gemma4:12b

What it can prove: that the brief produces structurally valid, well-attributed,
discriminating verdicts on a small model. What it CANNOT prove: that the design
works on the free-tier ladder, which is a different and larger model. A pass here
is a floor, not a verdict. A failure here is ambiguous -- design or model.

Scoring never collapses to one number. 7 cases expect RETURNED and 3 expect
ACCEPTED, so "always RETURNED" would score 70%. Catch rate and false-return rate
are reported separately, and format failures are counted on their own because
that is the fault that wasted 86.7% of one provider rung in the parent project.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BRIEF = os.path.join(REPO, "MANAGER-PROMPT.md")
CASES = os.path.join(HERE, "cases.json")
LOCK = os.path.join(HERE, ".trial.lock")


class Lock:
    """One trial process at a time. Never two.

    2026-09-10: two runs were launched concurrently against a 10 GB GPU. Passing
    several --model flags to ONE process is fine and stays sequential; launching
    a second PROCESS is what overcommits the card. A human had to stop it, and
    per CLAUDE.md that makes the missing bound the finding rather than the
    mistake. So the bound exists now, in code, and cannot be forgotten.

    Deliberately not a timeout or a retry: a second run must FAIL LOUDLY and say
    what is already running, not queue up behind it and start later when nobody
    is watching the card.
    """

    def __enter__(self):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                held = open(LOCK, encoding="utf-8").read().strip()
            except Exception:
                held = "unknown"
            sys.stderr.write(
                "REFUSED: another trial is already running (%s).\n"
                "Only one model may be resident at a time -- a second process "
                "overcommits the GPU.\n"
                "To run several models, pass several --model flags to ONE "
                "process; they run in sequence.\n"
                "If no trial is running, the previous one was killed: delete "
                "%s\n" % (held, LOCK))
            raise SystemExit(2)
        os.write(fd, ("pid=%d started=%s" % (
            os.getpid(), time.strftime("%Y-%m-%d %H:%M:%S"))).encode())
        os.close(fd)
        return self

    def __exit__(self, *exc):
        try:
            os.unlink(LOCK)
        except OSError:
            pass
        return False

CASE_TEMPLATE = """\
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


# ---------------------------------------------------------------- backends

def call_ollama(model, prompt, host, timeout=900, think=False):
    """Ask, and record WHY the answer was the size it was.

    2026-09-10, and this is the whole lesson of the night in one function.
    gemma4:12b returned an empty string on all twelve cases. The first reading
    was "format failure"; the second was "it returned nothing". Both wrong. It
    generated its ENTIRE 900-token budget, opened a reasoning block, never
    closed it, and Ollama surfaced none of it -- visible only in `done_reason`
    and `eval_count`, which this function used to throw away.

    A checker that reads only `response` cannot tell apart: the model said
    nothing, the model was cut off mid-thought, and the model answered somewhere
    else. Three faults, three different fixes, one label. That is the same
    disease this whole project exists to hunt, committed by the instrument.

    And the obvious fix is the wrong one, measured: at num_predict=3000 it still
    returned 0 chars, having burned 3000 tokens instead of 900. `think=False`
    returns a complete verdict in 216. **Budget is not the binding constraint;
    unbounded reasoning is.** Directly relevant to any real rung: a reasoning
    model registers a SUCCESSFUL call while delivering nothing, so it is never
    walled and the rungs below it are never reached.
    """
    payload = {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 900},
    }
    if think is not None:
        payload["think"] = think
    t0 = time.time()
    try:
        req = urllib.request.Request(
            host.rstrip("/") + "/api/generate", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if think is None:
            raise
        # Model does not accept the think flag; ask again without it rather
        # than recording a failure the model never had.
        return call_ollama(model, prompt, host, timeout, think=None)

    meta = {
        "done_reason": data.get("done_reason"),
        "eval_count": data.get("eval_count"),
        "thinking_len": len(data.get("thinking") or ""),
        "think_flag": think,
    }
    return data.get("response", ""), round(time.time() - t0, 1), meta


# ---------------------------------------------------------------- parsing

BLOCK_RE = re.compile(r"<<<COUSIN\b(.*?)(?:^COUSIN\s*$|\Z)", re.S | re.M)
FIELD_RE = re.compile(r"^\s*(verdict|tried|outcome|want|noticed)\s*:\s*(.*)$", re.I | re.M)


def parse_verdict(text):
    """Read the LAST block, from the end backwards.

    Models mention a verdict mid-thought before committing to one. Three parsers
    in the parent project needed this exact cure; it is cheaper to inherit it
    than to rediscover it.
    """
    blocks = BLOCK_RE.findall(text or "")
    if not blocks:
        return None, "no-block"
    body = blocks[-1]
    out = {}
    for k, v in FIELD_RE.findall(body):
        out[k.lower()] = v.strip()

    m = re.search(r"^\s*to_creature\s*:\s*\|?\s*\n(.*?)(?=^\s*(?:want|noticed|verdict|tried|outcome)\s*:|\Z)",
                  body, re.S | re.M)
    if m:
        out["to_creature"] = "\n".join(l.strip() for l in m.group(1).strip().splitlines()).strip()
    else:
        m2 = re.search(r"^\s*to_creature\s*:\s*(.+)$", body, re.I | re.M)
        if m2:
            out["to_creature"] = m2.group(1).strip()

    v = (out.get("verdict") or "").upper()
    if "RETURNED" in v:
        out["verdict"] = "RETURNED"
    elif "ACCEPTED" in v:
        out["verdict"] = "ACCEPTED"
    else:
        return out, "no-verdict"
    return out, None


# ------------------------------------------------- prose smells (advisory)

# NOT a pass/fail gate. A keyword list is exactly the "guard hunting one literal
# string" fault this project has a scar for, so these only mark a verdict for a
# human to read. The judgement stays with the reader.
SMELLS = [
    (r"\byou should\b|\bmake sure\b|\btry (?:adding|using|changing)\b|\bneeds? to be\b", "instructs"),
    (r"\bsyntax error\b|\bshebang\b|\bunterminated\b|\bU\+[0-9A-F]{4}\b|\bline \d+\b", "diagnoses"),
    (r"\bmock\b|\bhardcoded\b|\bfixture\b|\bplaceholder\b|\bstub\b", "names-the-cause"),
    (r"\bimport\b|\bdef \b|\bNameError\b|\bTraceback\b", "quotes-internals"),
]


def prose_smells(msg):
    hits = []
    for pat, label in SMELLS:
        if re.search(pat, msg or "", re.I):
            hits.append(label)
    return hits


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True,
                    help="ollama model tag; repeat to compare models. Several "
                         "flags run SEQUENTIALLY in this one process, which is "
                         "the only safe way -- never launch a second process.")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--case", action="append", help="run only these case names")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--think", default="false", choices=["false", "true"],
                    help="reasoning channel. Default false: a reasoning model "
                         "can burn its whole budget without closing the block "
                         "and return an EMPTY reply (measured 2026-09-10 on "
                         "gemma4:12b at both 900 and 3000 tokens).")
    args = ap.parse_args()

    args.think = (args.think == "true")
    lock = Lock(); lock.__enter__()
    try:
        return _run(args)
    finally:
        lock.__exit__()


def assert_brief_names_no_case(brief, cases):
    """THE ONE leak check. Both the runner and make_prompts.py call this; neither
    keeps its own copy, because a producer and a checker that share a literal
    will drift and no test notices.

    From the first commit until 2026-09-10 the brief's opening example named a
    real news fetcher together with the exact fact that disqualified it -- and
    that fetcher was a case. Every judge was handed the answer inside its own
    brief, and every semantic number measured on it was worthless. An example
    that names something real is not an illustration, it is a hint, and a hint
    reads exactly like competence when it comes back.
    """
    names = {c["name"] for c in cases} | {c["name"].replace(".py", "") for c in cases}
    leaks = sorted(n for n in names
                   if re.search(r"(?<![\w.-])" + re.escape(n) + r"(?![\w-])", brief))
    if leaks:
        sys.stderr.write(
            "REFUSED: the brief names %d tool(s) under test: %s\n"
            "An example naming a real tool hands the judge the answer.\n"
            "Rename them to invented tools before running.\n"
            % (len(leaks), ", ".join(leaks)))
        raise SystemExit(2)


def _run(args):
    brief = open(BRIEF, encoding="utf-8").read()
    cases = json.load(open(CASES, encoding="utf-8"))["cases"]
    assert_brief_names_no_case(brief, cases)
    if args.case:
        want = set(args.case)
        cases = [c for c in cases if c["name"] in want]
    os.makedirs(args.out, exist_ok=True)

    for model in args.model:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", model)
        path = os.path.join(args.out, "%s_%s.jsonl" % (stamp, safe))
        rows = []
        # Append per case, never at the end. A run killed part-way used to lose
        # every row it had already earned -- eight real verdicts went that way
        # on 2026-09-10. Evidence that cost a model call is written the moment
        # it exists.
        sink = open(path, "a", encoding="utf-8")
        print("\n=== %s ===" % model, flush=True)

        for c in cases:
            prompt = brief + "\n\n" + CASE_TEMPLATE.format(
                claim=c["claim"], header=c["header"], transcript=c["transcript"])
            try:
                reply, secs, meta = call_ollama(model, prompt, args.host,
                                                think=args.think)
                err = None
            except Exception as e:
                reply, secs, meta = "", 0.0, {}
                err = "%s: %s" % (type(e).__name__, e)

            parsed, perr = parse_verdict(reply)
            verdict = (parsed or {}).get("verdict")
            msg = (parsed or {}).get("to_creature", "")

            # A refusal with no reason is the "world is arbitrary" failure the
            # brief exists to prevent, and it is not a judgement error - the
            # model may have judged well and simply not spoken. 2026-09-10: one
            # model correctly spotted a fabricated "Domain is stable" conclusion,
            # wrote it into `outcome`, and sent the creature nothing at all. The
            # kernel must never deliver this.
            mute = (verdict == "RETURNED" and not (msg or "").strip())

            # An empty reply whose budget was exhausted is NOT a format fault.
            # It is a model that spent everything and delivered nothing -- the
            # failure that registers as a successful call and never walls a rung.
            spent = (not (reply or "").strip()
                     and meta.get("done_reason") == "length")

            if spent and c["expect"] != "OBSERVE":
                mark = "BUDGET-SPENT"
            elif mute and c["expect"] != "OBSERVE":
                mark = "MUTE-REFUSAL"
            elif c["expect"] == "OBSERVE":
                mark = "obs-mute" if mute else "obs"
            elif perr or err:
                mark = "FORMAT-FAIL"
            elif verdict == c["expect"]:
                mark = "ok"
            else:
                mark = "MISS"

            row = {
                "kind": "trial_verdict", "model": model, "case": c["name"],
                "class": c["class"], "expect": c["expect"], "verdict": verdict,
                "mark": mark, "parse_error": perr or err, "seconds": secs,
                "tried": (parsed or {}).get("tried"),
                "outcome": (parsed or {}).get("outcome"),
                "to_creature": msg, "want": (parsed or {}).get("want"),
                "noticed": (parsed or {}).get("noticed"),
                "smells": prose_smells(msg), "raw_len": len(reply),
                "done_reason": meta.get("done_reason"),
                "eval_count": meta.get("eval_count"),
                "thinking_len": meta.get("thinking_len"),
                "think_flag": meta.get("think_flag"),
                "raw": reply,
            }
            rows.append(row)
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
            print("  %-11s %-26s %-9s %-8s %ss %s" % (
                mark, c["name"][:26], c["expect"], verdict or "-", secs,
                ",".join(row["smells"]) or ""), flush=True)

        sink.close()
        report(rows, model, path)


def report(rows, model, path):
    scored = [r for r in rows if r["expect"] != "OBSERVE"]
    ret = [r for r in scored if r["expect"] == "RETURNED"]
    acc = [r for r in scored if r["expect"] == "ACCEPTED"]
    fmt = [r for r in scored if r["mark"] == "FORMAT-FAIL"]
    caught = [r for r in ret if r["verdict"] == "RETURNED"]
    falsely = [r for r in acc if r["verdict"] == "RETURNED"]
    smelly = [r for r in rows if r["smells"]]

    print("\n  -- %s --" % model)
    print("  catch rate        %d/%d   (broken work correctly returned)"
          % (len(caught), len(ret)))
    print("  false-return rate %d/%d   (good work wrongly returned)"
          % (len(falsely), len(acc)))
    print("  format failures   %d/%d   (no parseable verdict block)"
          % (len(fmt), len(scored)))
    print("  prose smells      %d/%d   (advisory only - read them)"
          % (len(smelly), len(rows)))
    spentr = [r for r in rows if r["mark"] == "BUDGET-SPENT"]
    if spentr:
        print("  BUDGET SPENT      %d      (empty reply, done_reason=length: "
              "burned the whole" % len(spentr))
        print("                            allowance and delivered nothing) %s"
              % [r["case"] for r in spentr])
    mutes = [r for r in rows if str(r["mark"]).endswith("mute") or r["mark"] == "MUTE-REFUSAL"]
    if mutes:
        print("  MUTE REFUSALS     %d      (RETURNED with an empty message: a "
              "refusal with no reason." % len(mutes))
        print("                            The kernel must never deliver one.) %s"
              % [r["case"] for r in mutes])
    if len(ret) and len(acc):
        print("  NOTE: %d cases expect RETURNED and %d expect ACCEPTED. A model that "
              "always returns\n        scores %d/%d on catch and %d/%d on false-return. "
              "Read both numbers." % (len(ret), len(acc), len(ret), len(ret), len(acc), len(acc)))
    miss = [r["case"] for r in scored if r["mark"] == "MISS"]
    if miss:
        print("  missed: " + ", ".join(miss))
    print("  written: %s" % path)


if __name__ == "__main__":
    sys.exit(main())
