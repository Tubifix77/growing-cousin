# The correction rules regressed detection: 99.1% -> 90.9%

Both search controls became exact coin flips (ACCEPTED 5 / RETURNED 5). Nothing
else moved.

Cause: two rules overlapped on "I got something, but it has a problem".
  - `noticed`  : the tool worked, the DATA was bad -> accept and note it
  - `want` rule: what you are asking for is what you were promised -> refuse

A search tool that faithfully returns contradictory archive records sits exactly
on that line, and the brief did not say which rule wins. The judge flipped a coin,
consistently, 5-5 on both.

The missing distinction: did the tool MAKE the thing that is wrong, or CARRY it?
A fetcher that invents results owns them. A reader that returns what is actually
written in the store does not.

Kept because it is the clearest example in this repo of a rule that is correct in
isolation and harmful in company. The brief is ONE artifact: every rule added to
it changes every verdict it produces.
