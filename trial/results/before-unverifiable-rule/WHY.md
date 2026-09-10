# Baseline: before the "unverifiable is not failed" rule

gemma4:12b, 7 passes, 92.8% green. One case carried nearly all the loss:
`keyword-archive-search` returned 5 of 6 times because the judge could not
verify the word "top-matching" in the claim -- while accepting a near-identical
tool with the same wording every time.

Kept so the rule that followed can be measured against the ground it landed on.
Without this baseline, any improvement afterwards is a story rather than a
number.
