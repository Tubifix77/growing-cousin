#!/usr/bin/env python3
"""forever.py -- the loop that lets the engine live without a hand on it.

Everything here is a BOUND, not a judgement. The cycle already knows what to do;
this file only decides when to do it again, when to wait, and when to stop.
That is the same split as the rest of the kernel, and it is why the supervisor
knows nothing about creatures, cousins or verdicts.

Four bounds, each earned:

1. **A loop that can only be stopped with `kill` is not deployable.** Killing
   mid-cycle throws away the cycle in flight, and on a box shared with the spine
   it is the blunt instrument that hits the wrong process. So stopping is a
   file: touch it and the loop finishes the cycle it is in, then exits.

2. **A stop request is never silently overridden.** If the stop file is already
   there at start-up the loop refuses to run and says so. Otherwise a restart --
   systemd, cron, a reboot -- would quietly undo a deliberate stop.

3. **A loop that spins on failure burns quota that is not its own.** The spine
   shares these accounts (CLAUDE.md §4), so our crash loop is billed to the
   sibling. Failures back off exponentially, and a run of them ends the loop
   rather than hammering forever.

4. **Cycles are paced.** The free tier is rate-limited and the ladder answers a
   429 by stepping down, not by waiting -- so without a pause here, a fast local
   fallback would drive the remote rungs straight back into their limits.

`sleep`, `now` and `exists` are injected so the whole policy is testable without
waiting real seconds or reaching a real model.
"""
import time

PAUSE_SECS = 30.0
BACKOFF_CAP_SECS = 900.0
MAX_CONSECUTIVE_FAILURES = 5

# **FLAT, not exponential, and the number is not arbitrary.** Tue, 2026-09-13:
# the framework tries the best rung, then the next, then the next,
# deterministically, and retries the whole ladder every two or three minutes.
#
# **The cadence is matched to `gemma-4-31b-it`** -- the rung that carries most
# of the traffic and comes back quickly after a refusal. That is what makes
# two or three minutes the right number rather than a guess: it is the
# recovery time of the rung this engine actually depends on. Change the
# primary rung and this constant has to be re-derived, not inherited.
#
# The backoff this replaces climbed to an hour, which is wrong for the thing it
# was waiting on: free-tier windows reset on a CLOCK, so an hour-long wait can
# miss a reset by up to an hour and leave the engine idle through a window that
# had already opened. Doubling is right for a fault that might be self-
# inflicted; it is wrong for a budget that returns on a schedule nobody here
# controls.
#
# It is also a politeness floor. Hammering a provider seconds after it refuses
# is how a client gets flagged, and the account is shared with the spine --
# see `backends.RETRY_GAP_SECS` for the same rule at the single-rung level.
WAIT_BASE_SECS = 150.0
WAIT_CAP_SECS = 150.0
# A wait is not progress, so without a ceiling a permanently rate-limited run
# can never reach its cycle limit and hangs forever -- found by the test for
# this very feature hanging, which is the test doing its job.
#
# Raised with the flat cadence: at 150s a day of patience is ~576 waits, and a
# free tier that resets daily deserves at least that. The old 24 was sized
# against an hour-long backoff and would now give up after an hour.
MAX_CONSECUTIVE_WAITS = 600


class StopRequested(Exception):
    """The stop file was already present at start-up."""


def default_is_wait(e):
    """Is this the world saying `come back later`, or is something broken?

    The distinction is the difference between an overnight run that survives a
    rate limit and one that is dead before midnight. Only the ladder can tell
    us, and only it knows whether the rungs refused us (quota) or rejected us
    (credentials) -- a rejected credential is not a wait, because waiting
    cannot fix it and a loop that waits politely forever on a broken key looks
    exactly like one that is working.
    """
    from . import backends
    return isinstance(e, backends.LadderExhausted) and not e.all_walled


class Supervisor:
    def __init__(self, run_one, stop_file, journal=None, pause=PAUSE_SECS,
                 backoff_cap=BACKOFF_CAP_SECS,
                 max_consecutive_failures=MAX_CONSECUTIVE_FAILURES,
                 wait_base=WAIT_BASE_SECS, wait_cap=WAIT_CAP_SECS,
                 max_consecutive_waits=MAX_CONSECUTIVE_WAITS,
                 is_wait=None,
                 sleep=time.sleep, now=time.time, exists=None):
        self.run_one = run_one
        self.stop_file = stop_file
        self.j = journal
        self.pause = pause
        self.backoff_cap = backoff_cap
        self.max_consecutive_failures = max_consecutive_failures
        self.wait_base = wait_base
        self.wait_cap = wait_cap
        self.max_consecutive_waits = max_consecutive_waits
        self._is_wait = is_wait or default_is_wait
        self._sleep = sleep
        self._now = now
        if exists is None:
            import os
            exists = os.path.exists
        self._exists = exists

    def _log(self, kind, **fields):
        if self.j:
            self.j.append(kind, **fields)

    def stop_requested(self):
        return bool(self.stop_file) and self._exists(self.stop_file)

    def loop(self, max_cycles=None):
        """Run cycles until asked to stop. Returns (cycles_run, reason).

        `max_cycles` exists for tests and for a bounded overnight run; None
        means until the stop file appears.
        """
        if self.stop_requested():
            raise StopRequested(
                "%s exists; remove it to start. A restart must never silently "
                "undo a deliberate stop." % self.stop_file)

        self._log("loop_start", pause=self.pause, max_cycles=max_cycles)
        ran = failures = waits = 0
        reason = "asked to stop"
        started = self._now()

        while max_cycles is None or ran < max_cycles:
            if self.stop_requested():
                break
            try:
                self.run_one()
                failures = waits = 0
            except Exception as e:
                if self._is_wait(e):
                    # Every rung is rate-limited. That is the WORLD saying come
                    # back later, not a fault, and it must not spend the
                    # failure budget -- on the deployed box there is no local
                    # rung to fall to, so an overnight run would otherwise be
                    # over within the hour and the night wasted. Free-tier
                    # quota resets on a clock; waiting is the correct move.
                    waits += 1
                    if waits >= self.max_consecutive_waits:
                        reason = "no rung available after %d waits" % waits
                        break
                    # Flat. See WAIT_BASE_SECS: the thing being waited on
                    # returns on a clock, so a widening gap can only miss it.
                    delay = min(self.wait_base, self.wait_cap)
                    self._log("loop_waiting", consecutive=waits,
                              seconds=round(delay), detail=str(e)[:200])
                    self._sleep(delay)
                    continue          # not a cycle: nothing ran
                failures += 1
                self._log("loop_error", consecutive=failures,
                          detail="%s: %s" % (type(e).__name__, e))
                if failures >= self.max_consecutive_failures:
                    reason = "%d consecutive failures" % failures
                    break
                # Back off before the next attempt, so a persistent fault costs
                # the shared quota geometrically less rather than linearly more.
                self._sleep(min(self.pause * (2 ** failures), self.backoff_cap))
                ran += 1
                continue

            ran += 1
            if max_cycles is not None and ran >= max_cycles:
                reason = "reached %d cycles" % max_cycles
                break
            # Checked before sleeping as well as after: a stop should not have
            # to wait out a pause it arrived during.
            if self.stop_requested():
                break
            self._sleep(self.pause)

        if max_cycles is not None and ran >= max_cycles and reason == "asked to stop":
            reason = "reached %d cycles" % max_cycles
        self._log("loop_end", cycles=ran, reason=reason,
                  seconds=round(self._now() - started, 1))
        return ran, reason
