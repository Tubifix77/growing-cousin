#!/usr/bin/env python3
"""backends.py -- how a model is asked. One shape: ask(prompt) -> (text, meta).

`meta` always carries `done_reason` and `completion_tokens`, because without
them an empty reply that said nothing and an empty reply that spent its whole
budget look identical -- and those have different fixes.
"""
import json
import time
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434"


def ollama(model, host=OLLAMA, num_predict=900, num_ctx=8192, think=False,
           timeout=900):
    """gemma4 family wraps reasoning in <thought> blocks and will spend the
    entire budget without closing one. think=False is not a preference."""
    def ask(prompt):
        payload = {"model": model, "prompt": prompt, "stream": False,
                   "options": {"temperature": 0, "num_ctx": num_ctx,
                               "num_predict": num_predict}}
        if think is not None:
            payload["think"] = think
        req = urllib.request.Request(
            host.rstrip("/") + "/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return d.get("response", ""), {
            "model": model,
            "done_reason": d.get("done_reason"),
            "completion_tokens": d.get("eval_count"),
            "seconds": round(time.time() - t0, 1),
        }
    return ask


def scripted(replies):
    """A creature or cousin whose answers are fixed. Lets an end-to-end test
    exercise the whole engine deterministically, so a kernel fault cannot hide
    behind model variance."""
    seq = list(replies)
    state = {"i": 0}

    def ask(_prompt):
        i = state["i"]
        state["i"] = i + 1
        r = seq[i] if i < len(seq) else ""
        if isinstance(r, tuple):
            return r
        return r, {"model": "scripted", "done_reason": "stop",
                   "completion_tokens": len(r) // 4}
    return ask


def preflight(ask, what):
    """Prove the backend answers before anything is recorded. A trial that
    cannot reach its judge has no verdicts to report, and a results file full of
    failures the model never made is worse than no file."""
    try:
        ask("Reply with exactly: ok")
        return True, None
    except Exception as e:
        return False, "%s unreachable: %s: %s" % (what, type(e).__name__, e)
