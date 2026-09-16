# The creature's body. PLAN item 7.
#
# `DockerBody` has been named as "the real body" since the design and was
# never exercised, so the creature's shell has shared a uid with the engine
# ever since -- and therefore with `~/keys/*.key`. `child_env` closed the
# environment variables on 2026-09-13 and said plainly that the FILES stayed
# readable by anything running as this user. This closes that.
#
# What goes in is decided by what the creature's library actually needs,
# counted rather than guessed (2026-09-16, over its 46 tools):
#   63 shebangs  #!/usr/bin/env python3
#    7 shebangs  #!/usr/bin/env bash
#    5 tools     import requests
# and `subprocess` in 15 of them, because its tools call each other.
#
# A body missing any of those breaks every tool at once while reporting
# healthy -- the relative-root scar, which cost thirteen honest refusals and
# a creature rebuilding one tool three ways. That is why the drill proves
# each one from inside before this ever becomes the live body.
FROM python:3.11-slim

# `requests` is the only third-party import in the whole library. Pinned to a
# major line rather than floating: a body that changes under the creature
# without anyone choosing it is a constant nobody chose.
RUN pip install --no-cache-dir "requests>=2.31,<3" \
 && rm -rf /root/.cache/pip

# Nothing else is installed on purpose. The image is not a place to give the
# creature capabilities -- its capabilities are the tools it writes. Adding a
# package here on its behalf is us building for it.
#
# No USER line: the container is run with --user matching the host uid that
# owns the bind-mounted mind, so what the creature writes stays readable by
# the engine and nothing in here runs as root.
# The contract names bash and `DockerBody` runs it. Debian slim ships it,
# but "ships it" is a belief about an image; this is the check. A build
# without bash fails here, in daylight, rather than every command failing
# at 03:00 with the body reporting healthy.
RUN bash -c 'exit 0'

WORKDIR /mind
