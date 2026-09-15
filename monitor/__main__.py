#!/usr/bin/env python3
"""python3 -m monitor -- the command line.

    python3 -m monitor status --root live --repo .     # write live/monitor/*, print the page
    python3 -m monitor status --no-write               # print only
    python3 -m monitor replay tests/fixtures/journal/X.jsonl
    python3 -m monitor detectors

Exit code from `status`: 1 when an alarm needs a human, else 0 -- so the
systemd unit shows under `--failed` exactly when someone should look.
"""
import argparse
import os
import sys

from . import derive, detectors, status


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m monitor")
    sub = ap.add_subparsers(dest="cmd")
    st = sub.add_parser("status", help="derive, detect, write the page")
    st.add_argument("--root", default="live")
    st.add_argument("--repo", default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    st.add_argument("--no-write", action="store_true")
    st.add_argument("--json", action="store_true", help="print status.json instead")
    rp = sub.add_parser("replay", help="run the detectors over a journal slice")
    rp.add_argument("fixture")
    rp.add_argument("--step", type=int, default=1)
    sub.add_parser("detectors", help="list the detectors")
    pk = sub.add_parser("pack", help="write the per-run evidence pack + manifest")
    pk.add_argument("--root", default="live")
    pk.add_argument("--out", required=True, help="directory for the tarball and manifest")
    pk.add_argument("--run", required=True, help="label, e.g. run-2")
    pk.add_argument("--repo", default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    vf = sub.add_parser("verify", help="check a pack against its manifest")
    vf.add_argument("tarball")
    vf.add_argument("manifest")
    args = ap.parse_args(argv)

    if args.cmd == "pack":
        from . import pack
        try:
            tar_path, man_path, man = pack.build(
                args.root, args.out, args.run, repo_head=status.git_head(args.repo))
        except pack.PackRefused as e:
            sys.stderr.write("REFUSED, nothing written: %s\n" % e)
            return 3
        print("packed %d files, %d bytes -> %s" % (len(man["files"]), man["total_bytes"], tar_path))
        print("manifest %s  (commit this one; the tarball stays here)" % man_path)
        if man.get("skipped"):
            print("skipped: %s" % man["skipped"])
        return 0

    if args.cmd == "verify":
        from . import pack
        problems = pack.verify(args.tarball, args.manifest)
        print("\n".join(problems) if problems else "pack matches its manifest")
        return 1 if problems else 0

    if args.cmd in (None, "status"):
        root = getattr(args, "root", "live")
        repo = getattr(args, "repo", None)
        try:
            md, data, rc = status.run_once(
                root, repo, write=not getattr(args, "no_write", False))
        except Exception:
            # THE MONITOR ITSELF BROKE, and that is its own exit code. An
            # instrument that fails must not report in the same voice as the
            # thing it watches -- exit 1 means "a finding needs a human", and
            # a traceback wearing that code would read as an ordinary alarm
            # while the page silently went stale.
            import traceback
            traceback.print_exc()
            sys.stderr.write("\nThe MONITOR failed, which is not a finding "
                             "about the engine. The page may be stale; its "
                             "first line carries the time it was written.\n")
            return status.EXIT_BROKEN
        if getattr(args, "json", False):
            import json
            print(json.dumps(data, indent=1, default=str))
        else:
            sys.stdout.write(md)
        return rc

    if args.cmd == "replay":
        rows = derive.load_fixture(args.fixture)
        if not rows:
            sys.stderr.write("no rows in %s\n" % args.fixture)
            return 2
        print("%d rows, %s -> %s" % (len(rows), derive.ts_str(rows[0]["ts"]),
                                     derive.ts_str(rows[-1]["ts"])))
        for c in status.replay(rows, step=args.step):
            print("%s  %-36s %s -> %s  %s" % (derive.ts_str(c["ts"]), c["name"],
                                              c["from"], c["to"], c["msg"][:110]))
        return 0

    if args.cmd == "detectors":
        for d in detectors.ALL:
            doc = (d.__doc__ or "").strip().split("\n")[0]
            print("%-26s %s" % (d.__name__, doc))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
