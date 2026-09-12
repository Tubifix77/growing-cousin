#!/usr/bin/env python3
"""backends.py -- how a model is asked. One shape: ask(prompt) -> (text, meta).

`meta` always carries `done_reason` and `completion_tokens`, because without
them an empty reply that said nothing and an empty reply that spent its whole
budget look identical -- and those have different fixes.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434"


# ------------------------------------------------------- reasoning blocks

FENCE_RE = re.compile(r"```.*?(?:```|\Z)", re.S)
_TAGS = "thought|think|reasoning|thinking"
CLOSED_RE = re.compile(r"<(%s)\b[^>]*>.*?</\1\s*>" % _TAGS, re.S | re.I)
OPEN_RE = re.compile(r"<(?:%s)\b[^>]*>.*\Z" % _TAGS, re.S | re.I)


def strip_reasoning(text):
    """Remove reasoning blocks a model wraps its answer in.

    Stripped at the BACKEND, not at each consumer, because a reasoning block is
    a property of the MODEL and not of whoever is reading. `gemma-4-31b-it` --
    the rung carrying 87-93% of the parent's traffic -- emits `<thought>` inside
    `content`, and unstripped it reaches `parse_bash_blocks` and the verdict
    parser alike. Fixing that in two places means drifting in two places.

    **Never inside a fenced block.** The creature writes files through fenced
    heredocs, and a creature writing a parser for these very tags would have its
    work silently damaged on the way to disk -- the single failure this project
    exists to prevent, and the one the body layer already cost six fixes.

    An UNCLOSED block swallows the rest of the text, which is correct: that is a
    model that started reasoning and never came back, and what follows is not an
    answer. It leaves an empty reply, which the classifiers already treat as a
    failure rather than as an answer.
    """
    if not text:
        return text
    out, last = [], 0
    for m in FENCE_RE.finditer(text):
        out.append(_strip_prose(text[last:m.start()]))
        out.append(m.group(0))          # fenced content is untouchable
        last = m.end()
    out.append(_strip_prose(text[last:]))
    return "".join(out)


def _strip_prose(chunk):
    chunk = CLOSED_RE.sub("", chunk)
    return OPEN_RE.sub("", chunk)


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
        return strip_reasoning(d.get("response", "")), {
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


def read_key(key_file=None, key_env=None):
    """The credential, fetched at CALL time from a file or the environment.

    A `key_file` points OUTSIDE this repo and is read on every call. It is never
    copied into the spec, the journal, `meta`, or an error message -- the only
    thing that travels is the PATH. This repo is public, so "no keys in the
    repo" stopped being tidiness and became the load-bearing rule it was always
    written as.
    """
    if key_file:
        try:
            with open(os.path.expanduser(key_file), encoding="utf-8") as f:
                key = f.read().strip()
        except OSError as e:
            raise RuntimeError("no credential: cannot read %s (%s)"
                               % (key_file, e.__class__.__name__))
        if not key:
            raise RuntimeError("no credential: %s is empty" % key_file)
        return key
    key = os.environ.get(key_env or "", "")
    if not key:
        raise RuntimeError("no credential in $%s" % key_env)
    return key


def openai_chat(model, base_url, key_env=None, key_file=None, num_predict=900,
                timeout=180, extra_headers=None):
    """Any OpenAI-compatible `/chat/completions` rung. Covers the free tier.

    Give it `key_file` (a path outside the repo) or `key_env`. Either way the
    credential is fetched per call and never stored, logged, or carried in
    `meta`.
    """
    def ask(prompt):
        key = read_key(key_file, key_env)
        body = {"model": model, "temperature": 0,
                "max_tokens": num_predict,
                "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer " + key}
        headers.update(extra_headers or {})
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(), headers=headers)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        choice = (d.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content")) or ""
        usage = d.get("usage") or {}
        return strip_reasoning(text), {
            "model": d.get("model") or model,
            "done_reason": choice.get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            "seconds": round(time.time() - t0, 1),
        }
    return ask


# ------------------------------------------------------------- the ladder

RETRY, NEXT, WALL = "retry", "next", "wall"


def classify_error(e):
    """(disposition, reason). **The default is NEXT and it never raises.**

    The parent's `classify_error` had a default branch that raised, so one
    unrecognised error took down the whole ladder instead of stepping past a
    single rung. An unknown failure is a reason to try the next rung, not a
    reason to stop -- and it announces itself once, WITH ITS TEXT, so the
    unknown becomes known instead of staying a mystery that recurs.
    """
    code = getattr(e, "code", None)
    if code in (401, 403):
        return WALL, "credential rejected (HTTP %s)" % code
    if code in (429, 402):
        return NEXT, "quota or rate limit (HTTP %s)" % code
    if code in (408, 500, 502, 503, 504, 529):
        return RETRY, "transient upstream (HTTP %s)" % code
    if code is not None:
        return NEXT, "HTTP %s" % code
    if isinstance(e, (urllib.error.URLError, TimeoutError, OSError)):
        return RETRY, "unreachable: %s" % (getattr(e, "reason", None) or e)
    if isinstance(e, RuntimeError) and "no credential" in str(e):
        return WALL, str(e)
    return NEXT, "%s: %s" % (type(e).__name__, e)


class LadderExhausted(Exception):
    """Every rung refused. Callers must treat this as UNKNOWN, never as a
    verdict -- an instrument that cannot run says UNKNOWN, never FAULTY."""


def ladder(rungs, journal=None, retries=1):
    """`rungs` is [(name, ask), ...] tried in order.

    A walled rung is skipped for the rest of the session: a rejected credential
    will be rejected again, and retrying it burns a cycle each time to learn
    nothing.

    Which rung served is recorded on every reply. In the parent, one pool rung
    wasted 86.7% of the cycles it served with clean but useless replies -- a
    manager on a rung like that produces confident garbage instead of an
    obvious failure, and you cannot notice that without the per-call record.
    """
    walled, announced = set(), set()

    def announce(name, reason):
        key = (name, reason.split(":")[0])
        if key in announced:
            return
        announced.add(key)
        if journal:
            journal.append("rung_error", rung=name, reason=reason)

    def ask(prompt):
        tried = []
        for name, rung in rungs:
            if name in walled:
                continue
            for attempt in range(retries + 1):
                try:
                    text, meta = rung(prompt)
                    meta = dict(meta or {})
                    meta["rung"] = name
                    if journal and tried:
                        journal.append("rung_fell_through",
                                       served_by=name, past=",".join(tried))
                    return text, meta
                except Exception as e:
                    verdict, reason = classify_error(e)
                    announce(name, reason)
                    if verdict == WALL:
                        walled.add(name)
                        tried.append("%s(walled)" % name)
                        break
                    if verdict == NEXT or attempt == retries:
                        tried.append("%s(%s)" % (name, verdict))
                        break
        raise LadderExhausted("no rung answered; tried %s"
                              % (", ".join(tried) or "nothing"))
    return ask


KINDS = {"ollama": ollama, "openai_chat": openai_chat}


def from_spec(spec, journal=None):
    """Build a ladder from plain data: [{name, kind, model, ...}, ...].

    Rungs are CONFIGURATION, not code, so adding or dropping one is not a commit
    -- "free tier only, permanently" means the ladder changes whenever a
    provider's terms do, and a rung behind a paywall is defunct by definition.

    The spec carries `key_env`, the NAME of an environment variable. It never
    carries a key. This file is public.
    """
    rungs = []
    for r in spec:
        # Keys starting with "_" are notes to the human. A config that refuses
        # to be annotated stops being annotated.
        r = {k: v for k, v in r.items() if not k.startswith("_")}
        name = r.pop("name", None) or r.get("model") or "rung%d" % len(rungs)
        kind = r.pop("kind", "ollama")
        if kind not in KINDS:
            raise ValueError("rung %r: unknown kind %r (have %s)"
                             % (name, kind, ", ".join(sorted(KINDS))))
        rungs.append((name, KINDS[kind](**r)))
    if not rungs:
        raise ValueError("empty ladder spec")
    return ladder(rungs, journal=journal)


def load_spec(path):
    """Read a ladder spec, or None when there is none. Absent is not an error:
    the local model is the honest default and says so."""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def preflight(ask, what):
    """Prove the backend answers before anything is recorded. A trial that
    cannot reach its judge has no verdicts to report, and a results file full of
    failures the model never made is worse than no file."""
    try:
        ask("Reply with exactly: ok")
        return True, None
    except Exception as e:
        return False, "%s unreachable: %s: %s" % (what, type(e).__name__, e)
