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

# Sent on every remote call. See the note in `openai_chat`: a missing
# User-Agent is read as bot traffic by Cloudflare-fronted providers.
USER_AGENT = "growing-cousin/1.0 (+https://github.com/Tubifix77/growing-cousin)"


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
           timeout=900, temperature=0):
    """gemma4 family wraps reasoning in <thought> blocks and will spend the
    entire budget without closing one. think=False is not a preference."""
    def ask(prompt):
        payload = {"model": model, "prompt": prompt, "stream": False,
                   "options": {"temperature": temperature, "num_ctx": num_ctx,
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
                timeout=180, extra_headers=None, temperature=0):
    """Any OpenAI-compatible `/chat/completions` rung. Covers the free tier.

    Give it `key_file` (a path outside the repo) or `key_env`. Either way the
    credential is fetched per call and never stored, logged, or carried in
    `meta`.

    **`temperature` defaults to 0 and that is right for a MEASUREMENT and wrong
    for a LIFE.** At 0 the same context produces the same decision forever, so
    a creature that reaches a repeating state can never leave it -- this engine
    has now watched that happen twice: `ls -R tools/own/` on six consecutive
    cycles (2026-09-11), and `cat plan; cat log-read` on twelve (2026-09-12,
    replies of 31-65 chars, every one `finish=stop`, nothing truncated and
    nothing built). Both times the context was not quite identical, so a strict
    fixed point is not even required -- near enough is enough.

    The trial keeps 0 because a judge that answers differently on Tuesday
    cannot be measured. The creature should not.
    """
    def ask(prompt):
        key = read_key(key_file, key_env)
        body = {"model": model, "temperature": temperature,
                "max_tokens": num_predict,
                "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer " + key,
                   # Several free rungs sit behind Cloudflare's WAF, which
                   # blocks clients by signature. urllib's default
                   # `Python-urllib/3.x` is on the list: 2026-09-12, Groq
                   # returned HTTP 403 "error code: 1010" -- a CLOUDFLARE code,
                   # not Groq's -- on every call, and the same request with any
                   # ordinary User-Agent succeeded. The key was never bad.
                   # Without this the ladder condemns working rungs.
                   "User-Agent": USER_AGENT}
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
        clean = strip_reasoning(text)
        return clean, {
            "model": d.get("model") or model,
            "done_reason": choice.get("finish_reason"),
            "completion_tokens": usage.get("completion_tokens"),
            # How much of the reply was reasoning we removed. Without this,
            # "the model said nothing" and "the model said ONLY reasoning and
            # never closed the block" arrive identical -- and they have
            # different fixes, which is the oldest lesson in this project.
            # 2026-09-12 it cost a diagnosis: the raw capture stored the reply
            # AFTER stripping, so the evidence it existed for was already gone.
            "chars_before_strip": len(text),
            "chars_stripped": len(text) - len(clean),
            # The text BEFORE stripping, capped. Stripping an unclosed
            # reasoning block is correct in general and catastrophic in one
            # case: when the answer was inside the block the model never
            # closed. Keeping the original lets a consumer recover a verdict
            # that stripping would otherwise have destroyed -- it can only
            # find answers that are there, never invent one.
            "raw_text": text[:8000],
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
    if code == 401:
        return WALL, "credential rejected (HTTP 401)"
    if code == 403:
        # 403 used to WALL alongside 401, and that was a wrong diagnosis with
        # an expensive consequence. 2026-09-12: Groq sits behind Cloudflare,
        # whose WAF answered 403 "error code: 1010" to a request with no
        # User-Agent -- nothing to do with the credential. Walling on that
        # permanently disabled a rung that worked perfectly the moment a header
        # was added. A bad key reliably says 401; 403 is ambiguous, so it steps
        # to the next rung for this call rather than condemning the rung for
        # the session. Retrying a genuinely forbidden rung is cheap; silently
        # losing a working one is not.
        return NEXT, "forbidden (HTTP 403) -- credential, or a WAF blocking us"
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
    verdict -- an instrument that cannot run says UNKNOWN, never FAULTY.

    `all_walled` separates the two cases, and they need opposite responses:

    - **False** -- the rungs are rate-limited or down. That is the WORLD saying
      come back later, not a fault. Waiting is the correct behaviour and an
      overnight run must survive it: free-tier quota resets on a clock, and on
      the deployed box there is no local rung to fall to.
    - **True** -- every rung rejected our credential. Waiting cannot fix that;
      only a human can. Ending the loop is correct, because a loop that waits
      politely forever on a broken key looks identical to one that is working.
    """

    def __init__(self, message, all_walled=False):
        Exception.__init__(self, message)
        self.all_walled = all_walled


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
        raise LadderExhausted(
            "no rung answered; tried %s" % (", ".join(tried) or "nothing"),
            all_walled=bool(tried) and all("(walled)" in t for t in tried))
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
