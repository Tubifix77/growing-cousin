#!/usr/bin/env python3
"""pack.py -- the per-run evidence pack.

CLAUDE.md §0 has said since 2026-09-13 that nothing in `live/` is committed,
so no figure in §7 is checkable by anyone who was not present. An outside
review named the fix -- a per-run evidence pack -- and it was still not
built two days later. This is it.

What a pack is: the journal, the vitals series, the monitor's alarm log and
last page, every regression report, the engine log, the quota memory, the
cousin's standing direction, and a snapshot of the creature's tools -- as a
tarball, with a MANIFEST that hashes every file and counts every journal
kind. The manifest is small and is what gets committed (`evidence/`); the
tarball stays where it was built. Where else it may live is Tue's decision,
because raw model output can contain anything the creature happened to
`cat` -- which is also why:

**It refuses to pack anything key-shaped.** A pack with a credential in it
is worse than no pack, and the scan runs over every byte before a single
one is written. The same patterns guarded the replay fixtures.

    python3 -m monitor pack --root live --out ~/growing-cousin-evidence --run run-2
    python3 -m monitor verify PACK.tar.gz PACK.manifest.json
"""
import collections
import hashlib
import io
import json
import os
import re
import tarfile
import time

from . import derive

# Key shapes for the providers this engine uses, plus the general one: a
# long run of base64-ish characters. Scanned over text decoded leniently, so
# a key inside a JSON string is still a key.
#
# EVERY PREFIX IS ANCHORED ON A NON-WORD BOUNDARY. The first version was not,
# and refused the first live pack on 216 "keys" that were all the creature's
# tool `subta|sk-log-filter-by-parent` -- a checker that cannot tell a tool
# name from a credential, the oldest fault in CLAUDE.md §5, in the tool built
# to keep credentials out of the public repo. `sk-` keys are alphanumeric
# after the prefix; the hyphenated forms are named explicitly.
SECRET_RE = re.compile(
    r"(?<![A-Za-z0-9_\-])(?:"
    r"AIza[0-9A-Za-z_\-]{30,}|gsk_[A-Za-z0-9]{20,}|"
    r"sk-(?:proj|ant|or-v1)-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{20,}|"
    r"hf_[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{48,}={0,2}(?![A-Za-z0-9+/])")
# A run of 48+ hex digits is a hash, not a key: sha256 is 64 of them and the
# creature's tools print hashes. Only mixed-case or +/ runs count.
HEX_RE = re.compile(r"^[0-9a-f]+$|^[0-9A-F]+$")

# What goes in, relative to the root. Directories are taken whole. A file
# over PER_FILE_CAP is listed in the manifest as skipped -- never packed
# silently and never dropped silently.
INCLUDE = ("journal.jsonl", "vitals.jsonl", "engine.log", "quota.json",
           "context.md", "monitor/alarms.jsonl", "monitor/status.md",
           "monitor/status.json", "monitor/regression",
           "body/mind/tools/own", "body/mind/state", "body/mind/data")
PER_FILE_CAP = 8 * 1024 * 1024
MANIFEST_NAME = "MANIFEST.json"


class PackRefused(Exception):
    """Something key-shaped was found; nothing was written."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def candidates(root):
    """`(relpath, abspath)` for every file the pack would take."""
    out = []
    for rel in INCLUDE:
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            out.append((rel, p))
        elif os.path.isdir(p):
            for dp, _dn, fn in os.walk(p):
                for n in sorted(fn):
                    ap = os.path.join(dp, n)
                    if os.path.isfile(ap):
                        out.append((os.path.relpath(ap, root).replace(os.sep, "/"), ap))
    return sorted(out)


def scan_secrets(paths):
    """`[(relpath, line, prefix)]` for every key-shaped match. Empty is the
    only acceptable answer."""
    hits = []
    for rel, ap in paths:
        try:
            with io.open(ap, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    for m in SECRET_RE.finditer(line):
                        s = m.group(0)
                        if HEX_RE.match(s.rstrip("=")):
                            continue
                        hits.append((rel, i, s[:10] + "…"))
        except OSError:
            continue
    return hits


def real_keys(keys_dir=None):
    """The actual credentials on this box, byte for byte, when readable.

    Shapes are a guess about what a key looks like; this is the thing itself.
    2026-09-16: a shape scan first refused a live pack on 216 tool names, and
    the same evening a hand-rolled shape scan reported the creature's memory
    held a credential -- it was `subtask-log-filter` again. Meanwhile the one
    decisive check, *is any real key in these bytes*, had never been run. It
    is run now, and the manifest says how many were checked, so "0 key-shaped
    strings" is never mistaken for "0 keys".

    Only the values are read, only into memory, only to be searched for.
    Nothing here writes or prints them.
    """
    import glob
    keys_dir = keys_dir or os.path.expanduser("~/keys")
    out = {}
    for p in sorted(glob.glob(os.path.join(keys_dir, "*.key"))):
        try:
            with io.open(p, encoding="utf-8", errors="replace") as f:
                v = f.read().strip()
        except OSError:
            continue
        if len(v) >= 12:
            out[os.path.basename(p)] = v
    return out


def scan_real_keys(paths, keys):
    """`[(relpath, keyname)]` for every real key found verbatim."""
    hits = []
    if not keys:
        return hits
    for rel, ap in paths:
        try:
            with io.open(ap, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for name, v in keys.items():
            if v in text:
                hits.append((rel, name))
    return hits


def describe_hits(hits, limit=5):
    """The refusal message: where, and WHICH shapes, so a false positive is
    diagnosable from the message alone -- the first live refusal showed five
    of 216 locations and nothing about what they had in common."""
    shapes = collections.Counter(h[2][:4] for h in hits)
    where = "; ".join("%s:%d %s" % h for h in hits[:limit])
    return "%d key-shaped string(s) -- by shape: %s -- first: %s" % (
        len(hits), ", ".join("%s… x%d" % (s, n) for s, n in shapes.most_common()), where)


def journal_summary(path):
    rows, _complete, bad = derive.load(path, tail_bytes=1 << 40)
    kinds = collections.Counter(r.get("kind") for r in rows)
    engines = []
    for r in rows:
        if r.get("kind") == "engine_start":
            sha = r.get("engine") or "unknown"
            if sha not in engines:
                engines.append(sha)
    return {"events": len(rows), "bad_lines": bad, "kinds": dict(kinds),
            "first_ts": float(rows[0]["ts"]) if rows else None,
            "last_ts": float(rows[-1]["ts"]) if rows else None,
            "engines": engines,
            "loop_starts": kinds.get("loop_start", 0)}


def build(root, out_dir, run, repo_head=None, now=None, keys_dir=None):
    """Write `<out_dir>/<run>-<stamp>.tar.gz` and `<...>.manifest.json`.
    Returns `(tarball_path, manifest_path, manifest)`. Raises PackRefused --
    having written nothing -- if anything key-shaped is found, or if any
    REAL key on this box appears verbatim."""
    now = time.time() if now is None else float(now)
    root = os.path.abspath(root)
    paths = candidates(root)
    hits = scan_secrets(paths)
    if hits:
        raise PackRefused(describe_hits(hits))
    keys = real_keys(keys_dir)
    real_hits = scan_real_keys(paths, keys)
    if real_hits:
        raise PackRefused("%d REAL credential(s) found verbatim: %s"
                          % (len(real_hits), "; ".join(
                              "%s holds %s" % h for h in real_hits[:5])))

    # Hash first, write second: the manifest inside the tarball must already
    # know every member.
    files, skipped, total = [], [], 0
    for rel, ap in paths:
        size = os.path.getsize(ap)
        if size > PER_FILE_CAP:
            skipped.append({"path": rel, "bytes": size, "why": "over per-file cap"})
            continue
        files.append({"path": rel, "bytes": size, "sha256": sha256(ap)})
        total += size
    stamp = derive.ts_str(now, "%Y%m%d-%H%M")
    base = "%s-%s" % (run, stamp)
    manifest = {
        "run": run, "created": now, "created_str": derive.ts_str(now),
        "root": root, "tarball": base + ".tar.gz", "repo_head": repo_head,
        "files": files, "skipped": skipped, "total_bytes": total,
        "secret_scan": "0 key-shaped strings in %d files; %s" % (
            len(paths),
            ("0 real keys, %d checked byte-for-byte" % len(keys)) if keys
            else "no key files were readable to check byte-for-byte"),
    }
    jp = os.path.join(root, "journal.jsonl")
    if os.path.isfile(jp):
        manifest["journal"] = journal_summary(jp)

    os.makedirs(out_dir, exist_ok=True)
    tar_path = os.path.join(out_dir, base + ".tar.gz")
    man_path = os.path.join(out_dir, base + ".manifest.json")
    packed = {f["path"] for f in files}
    inner = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    with tarfile.open(tar_path, "w:gz") as tar:
        for rel, ap in paths:
            if rel in packed:
                tar.add(ap, arcname="%s/%s" % (base, rel))
        info = tarfile.TarInfo("%s/%s" % (base, MANIFEST_NAME))
        info.size, info.mtime = len(inner), int(now)
        tar.addfile(info, io.BytesIO(inner))
    # A file cannot carry its own hash, so only the manifest BESIDE the
    # tarball has this field.
    manifest["tarball_sha256"] = sha256(tar_path)
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    return tar_path, man_path, manifest


def verify(tar_path, man_path):
    """Recompute every hash in the manifest against the tarball's members.
    Returns the list of mismatches; empty means the pack is what it says."""
    with open(man_path, encoding="utf-8") as f:
        man = json.load(f)
    problems = []
    if sha256(tar_path) != man.get("tarball_sha256"):
        problems.append("tarball sha256 differs from the manifest")
    want = {f["path"]: f for f in man.get("files", [])}
    base = os.path.basename(tar_path)
    base = base[:-len(".tar.gz")] if base.endswith(".tar.gz") else base
    seen = set()
    with tarfile.open(tar_path, "r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            rel = m.name[len(base) + 1:] if m.name.startswith(base + "/") else m.name
            if rel == MANIFEST_NAME:
                continue
            seen.add(rel)
            if rel not in want:
                problems.append("%s is in the tarball but not the manifest" % rel)
                continue
            h = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
            if h != want[rel]["sha256"]:
                problems.append("%s: sha256 differs" % rel)
    for rel in want:
        if rel not in seen:
            problems.append("%s is in the manifest but not the tarball" % rel)
    return problems
