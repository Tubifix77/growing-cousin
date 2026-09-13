#!/usr/bin/env python3
"""quota.py -- remember which rungs are spent, instead of rediscovering it.

Taken as an IDEA from Growing Spine's `keychain/quota_state.py`, read
2026-09-13 at Tue's suggestion, and rewritten here rather than copied --
CLAUDE.md §2.6 allows reading that source and forbids sharing files with it.

**The fault it fixes is a documented constraint not met.** §4 says the ladder
must be quota-polite because the free tier is SHARED with the spine. It was
not: every call re-probed every rung, so a rung that had already answered 429
was asked again, and again. Measured in run 2's first 26 minutes: **15 of 29
rung failures were repeat 429s against rungs already known spent** -- about 35
wasted requests an hour, each one a real request against the account the
sibling project depends on.

Two distinctions this file exists to keep, and both were learned the hard way
elsewhere in this kernel:

1. **Only QUOTA marks a rung spent.** A 500 or a timeout is transient and says
   nothing about budget. In the same window gemini produced ten non-quota
   failures; marking those would have walled a rung that was working minutes
   later. Same shape as the WAF 403 that was read as a bad credential.
2. **Spent is not dead.** A mark expires, so the rung is tried again rather
   than condemned for the session -- a circuit breaker with a half-open state,
   not a wall. Free-tier windows reset on a clock; the point is to stop asking
   every few seconds, not to stop asking.

The state is PERSISTED because restarts were frequent while this was built,
and an in-memory mark forgets everything a restart taught it.
"""
import json
import os
import time

# First skip window. Doubles per consecutive failure to the cap, which is the
# same backoff shape `forever.py` uses for waits -- one idea, not two.
FIRST_SKIP_SECS = 300.0
MAX_SKIP_SECS = 3600.0


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        # A missing or corrupt file must not stop the engine: the worst case of
        # an empty state is the behaviour we had before this file existed.
        return {}


def save(path, state):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


def record_exhaustion(state, rung, now=None):
    """A 429. Stamp the FIRST failure of a dark period and widen the skip.

    Subsequent failures inside the same period do not move `since`, so the
    recovery time measured later is from the first failure rather than the
    last -- otherwise a long outage reports as a short one.
    """
    now = now or time.time()
    s = state.setdefault(rung, {})
    if "since" not in s:
        s["since"] = now
        s["skip"] = FIRST_SKIP_SECS
    else:
        s["skip"] = min(float(s.get("skip", FIRST_SKIP_SECS)) * 2, MAX_SKIP_SECS)
    s["last_fail"] = now
    return state


def record_success(state, rung, now=None):
    """It answered. Clear the mark and KEEP how long the dark period lasted.

    The duration is the only evidence there is for how long these windows
    actually are. Guessing a backoff without it is how a constant gets chosen
    with no evidence, which this project has a scar for.
    """
    now = now or time.time()
    s = state.setdefault(rung, {})
    since = s.pop("since", None)
    s.pop("skip", None)
    s.pop("last_fail", None)
    if since is not None:
        s["last_recovery_secs"] = round(now - since, 1)
    s["last_success"] = now
    return state


def is_spent(state, rung, now=None):
    """Skip this rung for now? False once the window has passed, so the rung is
    RETRIED rather than condemned."""
    now = now or time.time()
    s = state.get(rung) or {}
    if "since" not in s:
        return False
    return (now - s.get("last_fail", s["since"])) < float(
        s.get("skip", FIRST_SKIP_SECS))


def spent_rungs(state, now=None):
    return sorted(r for r in state if is_spent(state, r, now))
