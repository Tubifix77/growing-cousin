# Correction loop: 100% (10/10), from a 50% baseline

    ascii_plot.fixed            (genuine)  ACCEPTED 5/5
    wake_catchup_fetcher.fixed  (cosmetic) RETURNED 5/5
    RecallScheduler.fixed       (partial)  RETURNED 5/5  (observed)
    catchup_plan_archive.fixed  (partial)  RETURNED 5/5  (observed)

Three rules got it here, each earned from what the judge SAID rather than from
its score, and each measured against the run before it:

1. "unverifiable is not failed"          92.8% -> 99.1% detection
2. "a want is for capability BEYOND the  cosmetic repair 0/5 -> 5/5
    claim, never for the claim itself"
3. "judge the result, not the tidiness"  genuine repair 1/5 -> 5/5

One attempted rule made things worse (genuine repairs 5/5 -> 1/5 while catching
nothing) and was reverted, not layered over. It is kept in
results/repair-after-need-rule/.
