#!/usr/bin/env python3
"""make_prompts.py -- build one leak-free prompt file per case, for judges that
cannot be driven over HTTP (Claude Code subagents).

Two gates, both of which have already caught a real contamination:

1. The answer key (`why`, `expect`) must not appear in a prompt.
2. NO TOOL UNDER TEST MAY BE NAMED ANYWHERE IN THE BRIEF. From the first commit
   until 2026-09-10 the brief's opening example named a real news fetcher along
   with the exact fact that disqualified it -- and that fetcher was a case. Every
   judge was handed the answer to it inside its own brief. An example that names
   something real is not an illustration, it is a hint.
"""
import json, io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_trial as R

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    brief = io.open(os.path.join(HERE, '..', 'MANAGER-PROMPT.md'), encoding='utf-8').read()
    cases = json.load(io.open(os.path.join(HERE, 'cases.json'), encoding='utf-8'))['cases']

    # THE one leak check lives in run_trial.py and is called by both. Never a
    # second copy: a producer and a checker that share a literal will drift, and
    # no test notices.
    R.assert_brief_names_no_case(brief, cases)

    out = os.path.join(HERE, 'prompts')
    os.makedirs(out, exist_ok=True)
    for c in cases:
        body = brief + "\n\n" + R.CASE_TEMPLATE.format(
            claim=c['claim'], header=c['header'], transcript=c['transcript'])
        assert c['why'][:50] not in body, ('why leaked', c['name'])
        assert '"expect"' not in body, ('expect leaked', c['name'])
        io.open(os.path.join(out, c['name'] + '.md'), 'w', encoding='utf-8').write(body)
    print("wrote %d prompts; no case name appears in the brief; answer key absent"
          % len(cases))


if __name__ == '__main__':
    main()
