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

def call_ollama(model, prompt, host, timeout=600):
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 900},
    }).encode()
    req = urllib.request.Request(
        host.rstrip("/") + "/api/generate", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data.get("response", ""), round(time.time() - t0, 1)


# ---------------------------------------------------------------- parsing

BLOCK_RE = re.compile(r"<<<COUSIN\b(.*?)(?:^COUSIN\s*$|\Z)", re.S | re.M)
FIELD_RE = re.compile(r"^\s*(verdict|tried|outcome|want)\s*:\s*(.*)$", re.I | re.M)


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

    m = re.search(r"^\s*to_creature\s*:\s*\|?\s*\n(.*?)(?=^\s*(?:want|verdict|tried|outcome)\s*:|\Z)",
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
                    help="ollama model tag; repeat to compare models")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--case", action="append", help="run only these case names")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    args = ap.parse_args()

    brief = open(BRIEF, encoding="utf-8").read()
    cases = json.load(open(CASES, encoding="utf-8"))["cases"]
    if args.case:
        want = set(args.case)
        cases = [c for c in cases if c["name"] in want]
    os.makedirs(args.out, exist_ok=True)

    for model in args.model:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", model)
        path = os.path.join(args.out, "%s_%s.jsonl" % (stamp, safe))
        rows = []
        print("\n=== %s ===" % model, flush=True)

        for c in cases:
            prompt = brief + "\n\n" + CASE_TEMPLATE.format(
                claim=c["claim"], header=c["header"], transcript=c["transcript"])
            try:
                reply, secs = call_ollama(model, prompt, args.host)
                err = None
            except Exception as e:
                reply, secs, err = "", 0.0, "%s: %s" % (type(e).__name__, e)

            parsed, perr = parse_verdict(reply)
            verdict = (parsed or {}).get("verdict")
            msg = (parsed or {}).get("to_creature", "")

            if c["expect"] == "OBSERVE":
                mark = "obs"
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
                "smells": prose_smells(msg), "raw_len": len(reply),
            }
            rows.append(row)
            print("  %-11s %-26s %-9s %-8s %ss %s" % (
                mark, c["name"][:26], c["expect"], verdict or "-", secs,
                ",".join(row["smells"]) or ""), flush=True)

        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
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
