#!/usr/bin/env python3
"""history.py -- every version of the creature's world, kept outside it.

PLAN 6f, 2026-10-02. That morning the creature's central tool, `plan`, was lost
from its own directory: a hand wrote a SEARCH block over it, and the next edit
backed the broken file up over the good `.bak`. It could be found again only
because a `cat` of it happened to sit in the journal. And the hands' `.bak` was
never the whole safety net anyway -- measured over the 7 days before, **33% of
the creature's tool writes went through no hand at all** (`cat > tools/own/x`,
`cp`, `mv`) and kept no backup, and it overwrote its own `data/archive.json` 50
times and `plan.json` 20 times with `>`, mostly while setting up tests.

Growing Spine reached the same place on 2026-09-21 by the other road: versioning
inside `tool-edit` misses the writes that do not use it, and only a snapshot of
the world covers every door. This is that, as a BOUND rather than a judgement:

- After every cycle that ran commands (and once, as a baseline, at the first),
  every regular file under the mind whose stamp moved is read, and kept if its
  content differs from the last version kept. Nothing decides what matters.
- It is kept BESIDE THE JOURNAL (`<live>/history/`), outside every mount, so
  neither the creature nor its cousin can see it or reach it (§2.3 untouched).
- It never goes through a link -- not the last component, and not a parent the
  creature swaps for a link mid-walk: the walk and every open are relative to a
  directory descriptor (`os.fwalk`, `dir_fd`, `O_NOFOLLOW`). A file the
  creature linked to `/home/...` would otherwise copy host files -- the key
  directory among them -- into the store. Opens are non-blocking and re-checked
  as regular files, so a FIFO swapped in cannot hang the engine.
- It restores NOTHING. A restore into `tools/own` is still the creature's
  consent (§2.1); this only turns *"is the good version anywhere?"* into a
  lookup. `python3 -m kernel.history --root live list tools/own/plan`.
- Bounded. Versions past the age bound go; over the size bound, the oldest
  version of whichever path holds the MOST bytes goes first, so one file
  rewritten every cycle can never erase every other file's past. The newest
  version of a file that still exists is never dropped; a file the creature
  deleted ages out like anything else.
- It can never break a cycle: one file that cannot be kept is recorded and
  skipped, and the engine journals any other failure and carries on -- an
  instrument that can kill a cycle is worse than no instrument (the spine).

The 2026-10-02 verifier found every one of the bounds above missing or wrong in
the first version, in the hour it was written.
"""
import argparse
import hashlib
import heapq
import os
import re
import stat
import sys
import time

MAX_FILE_BYTES = 1000000            # larger files are recorded as skipped
MAX_TOTAL_BYTES = 200 * 1024 * 1024
MAX_AGE_S = 30 * 86400
PRUNE_EVERY_S = 3600
PART_STALE_S = 3600
# Not the creature's work: pip's caches and packages, Python's bytecode, a git
# store's objects, and the body's own per-command scripts.
SKIP_DIRS = frozenset((".cache", ".local", "__pycache__", ".git"))
SKIP_PREFIXES = (".cmd-",)
SKIP_SUFFIXES = (".pyc", ".tmp")
VERSION_RE = re.compile(r"^(\d{13})-([0-9a-f]{16})$")
_FLAGS = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
          | getattr(os, "O_BINARY", 0))


def printable(rel):
    """A path as the journal can hold it: a filename that is not valid UTF-8
    (`touch $'\\xff'`) would otherwise make the record itself fail."""
    return rel.encode("utf-8", "surrogateescape").decode("utf-8", "replace")


def _skip_file(n):
    return n.startswith(SKIP_PREFIXES) or n.endswith(SKIP_SUFFIXES)


class History:
    def __init__(self, mind, root, journal=None):
        self.mind = os.path.abspath(mind)
        self.root = os.path.abspath(root)
        inside = os.path.join(self.mind, "")
        if self.root == self.mind or self.root.startswith(inside):
            raise ValueError("history must live outside the mind it keeps")
        self.files = os.path.join(self.root, "files")
        self.j = journal
        self.seen = {}            # relpath -> (mtime_ns, size) already handled
        self._last_prune = 0.0

    # -------------------------------------------------------------- reading
    def _entries(self):
        """`(rel, reader)` for every regular file, never through a link.
        `reader()` returns the bytes or raises OSError; it opens relative to
        the directory descriptor the walk holds, so a parent swapped for a
        link after it was listed is not followed."""
        if hasattr(os, "fwalk"):
            for dirpath, dirnames, filenames, dfd in os.fwalk(
                    self.mind, follow_symlinks=False):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for n in sorted(filenames):
                    if _skip_file(n):
                        continue
                    try:
                        st = os.stat(n, dir_fd=dfd, follow_symlinks=False)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, n), self.mind)
                    yield (rel.replace(os.sep, "/"), st,
                           lambda n=n, dfd=dfd: self._read(n, dfd))
        else:                      # no fwalk (Windows): the bench, never the body
            for dirpath, dirnames, filenames in os.walk(self.mind, followlinks=False):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and
                                     not os.path.islink(os.path.join(dirpath, d)))
                for n in sorted(filenames):
                    if _skip_file(n):
                        continue
                    p = os.path.join(dirpath, n)
                    try:
                        st = os.lstat(p)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    yield (os.path.relpath(p, self.mind).replace(os.sep, "/"), st,
                           lambda p=p: self._read(p, None))

    @staticmethod
    def _read(name, dfd):
        fd = os.open(name, _FLAGS, dir_fd=dfd) if dfd is not None else os.open(name, _FLAGS)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("not a regular file any more")
            chunks, left = [], MAX_FILE_BYTES + 1
            while left > 0:
                b = os.read(fd, min(left, 1 << 16))
                if not b:
                    break
                chunks.append(b)
                left -= len(b)
            return b"".join(chunks)
        finally:
            os.close(fd)

    def _dir(self, rel):
        return os.path.join(self.files, *rel.split("/"))

    def versions(self, rel):
        """`[(name, ts, sha)]` oldest first for one path under the mind."""
        try:
            names = os.listdir(self._dir(rel))
        except OSError:
            return []
        out = []
        for n in sorted(names):
            m = VERSION_RE.match(n)
            if m and os.path.isfile(os.path.join(self._dir(rel), n)):
                out.append((n, int(m.group(1)) / 1000.0, m.group(2)))
        return out

    def read(self, rel, name):
        with open(os.path.join(self._dir(rel), name), "rb") as f:
            return f.read()

    # -------------------------------------------------------------- keeping
    def keep(self, now=None):
        """Keep every changed file once. Returns the paths kept."""
        now = time.time() if now is None else now
        kept, nbytes, skipped, failed = [], 0, [], []
        for rel, st, reader in self._entries():
            stamp = (st.st_mtime_ns, st.st_size)
            if self.seen.get(rel) == stamp:
                continue
            if st.st_size > MAX_FILE_BYTES:
                skipped.append(rel)
                self.seen[rel] = stamp
                continue
            try:
                data = reader()
                if len(data) > MAX_FILE_BYTES:
                    skipped.append(rel)
                    self.seen[rel] = stamp
                    continue
                sha = hashlib.sha256(data).hexdigest()[:16]
                have = self.versions(rel)
                if not have or have[-1][2] != sha:
                    d = self._dir(rel)
                    os.makedirs(d, exist_ok=True)
                    # MONOTONIC names, so "newest" is the last kept even if
                    # the clock steps back.
                    ms = int(now * 1000)
                    if have:
                        ms = max(ms, int(have[-1][0][:13]) + 1)
                    name = "%013d-%s" % (ms, sha)
                    tmp = os.path.join(d, "." + name + ".part")
                    with open(tmp, "wb") as f:
                        f.write(data)
                    os.replace(tmp, os.path.join(d, name))
                    kept.append(rel)
                    nbytes += len(data)
                self.seen[rel] = stamp
            except OSError as e:
                # ONE path that cannot be kept never stops the rest.
                failed.append("%s: %s" % (rel, e.__class__.__name__))
        pruned = (0, 0)
        if now - self._last_prune >= PRUNE_EVERY_S:
            pruned = self.prune(now)
            self._last_prune = now
        if self.j is not None and (kept or skipped or failed):
            self.j.append("history_kept", files=len(kept), bytes=nbytes,
                          paths=[printable(p) for p in kept[:20]],
                          skipped=[printable(p) for p in skipped[:20]],
                          failed=[printable(p) for p in failed[:20]])
        if self.j is not None and pruned[0]:
            self.j.append("history_pruned", versions=pruned[0], bytes=pruned[1])
        return kept

    def _live(self, rel):
        try:
            return stat.S_ISREG(os.lstat(os.path.join(self.mind, *rel.split("/"))).st_mode)
        except OSError:
            return False

    def prune(self, now=None):
        """Drop versions past the age bound; then, while over the size bound,
        the oldest version of the path holding the most bytes. Never the newest
        version of a file that still exists. Stale `.part` files go too."""
        now = time.time() if now is None else now
        paths = {}                       # rel -> [(ts, size, fullpath)] oldest first
        for dirpath, _dirs, names in os.walk(self.files):
            for n in names:
                p = os.path.join(dirpath, n)
                if n.endswith(".part"):
                    try:
                        if now - os.path.getmtime(p) > PART_STALE_S:
                            os.remove(p)
                    except OSError:
                        pass
                    continue
                m = VERSION_RE.match(n)
                if not m:
                    continue
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                rel = os.path.relpath(dirpath, self.files).replace(os.sep, "/")
                paths.setdefault(rel, []).append((int(m.group(1)) / 1000.0, size, p))
        dropped = freed = 0

        def drop(entry):
            nonlocal dropped, freed
            try:
                os.remove(entry[2])
            except OSError:
                return False
            dropped += 1
            freed += entry[1]
            return True

        for rel, vs in paths.items():
            vs.sort(key=lambda v: v[2])
            protect = vs[-1] if self._live(rel) else None
            keep = []
            for v in vs:
                if v is not protect and now - v[0] > MAX_AGE_S and drop(v):
                    continue
                keep.append(v)
            paths[rel] = keep
        total = sum(v[1] for vs in paths.values() for v in vs)
        if total > MAX_TOTAL_BYTES:
            heap = []
            for rel, vs in paths.items():
                droppable = vs[:-1] if (vs and self._live(rel)) else vs
                if droppable:
                    heapq.heappush(heap, (-sum(v[1] for v in vs), rel, list(droppable)))
            while total > MAX_TOTAL_BYTES and heap:
                neg, rel, droppable = heapq.heappop(heap)
                v = droppable.pop(0)
                if drop(v):
                    total -= v[1]
                    neg += v[1]
                if droppable:
                    heapq.heappush(heap, (neg, rel, droppable))
        return dropped, freed


def main(argv=None):
    """For a human or a maintainer, never on the creature's PATH."""
    ap = argparse.ArgumentParser(prog="python3 -m kernel.history")
    ap.add_argument("--root", required=True, help="the live root, e.g. live")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="versions of one path under the mind")
    ls.add_argument("path")
    sh = sub.add_parser("show", help="print one version to stdout")
    sh.add_argument("path")
    sh.add_argument("version")
    a = ap.parse_args(argv)
    h = History(os.path.join(a.root, "body", "mind"),
                root=os.path.join(a.root, "history"))
    if a.cmd == "list":
        vs = h.versions(a.path)
        if not vs:
            sys.stderr.write("no versions kept of %s\n" % a.path)
            return 1
        for name, ts, sha in vs:
            size = os.path.getsize(os.path.join(h._dir(a.path), name))
            print("%s  %s  %7d bytes" % (name, time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(ts)), size))
        return 0
    try:
        sys.stdout.buffer.write(h.read(a.path, a.version))
    except OSError as e:
        sys.stderr.write("%s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
