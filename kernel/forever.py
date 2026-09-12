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


class StopRequested(Exception):
    """The stop file was already present at start-up."""


class Supervisor:
    def __init__(self, run_one, stop_file, journal=None, pause=PAUSE_SECS,
                 backoff_cap=BACKOFF_CAP_SECS,
                 max_consecutive_failures=MAX_CONSECUTIVE_FAILURES,
                 sleep=time.sleep, now=time.time, exists=None):
        self.run_one = run_one
        self.stop_file = stop_file
        self.j = journal
        self.pause = pause
        self.backoff_cap = backoff_cap
        self.max_consecutive_failures = max_consecutive_failures
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
        ran = failures = 0
        reason = "asked to stop"
        started = self._now()

        while max_cycles is None or ran < max_cycles:
            if self.stop_requested():
                break
            try:
                self.run_one()
                failures = 0
            except Exception as e:
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
