# Prospective validation plan

No predictive edge is established. Before each experiment, freeze the hypothesis, cohort definition, collection period, feature versions, eligibility/freshness rules, cost/latency/notional assumptions, outcome handling, primary metric, sample-size requirement and promotion criteria in an experiment manifest. Unset values block formal evaluation, not exploratory labeled research.

1. Collect all discovered candidates and decision exclusions. Record source coverage and outage periods; do not claim recall over coins never observed.
2. Use chronological training, tuning and untouched forward cohorts. Purge overlapping 24-hour labels at split boundaries and group related narrative/launch clusters to limit leakage.
3. Qualify wallets only with history available at qualification time. Wallets found through today's winners can confirm later events, not retroactively improve today's detection. Include unsuccessful trades, transfers and incomplete history when estimating wallet quality.
4. Test single families and ablations before convergence. Compare HIGH, WATCH, no-alert eligible coins and simple stage/market/liquidity baselines, matched or stratified by time, age, market cap and regime.
5. Measure distributions of net executable return at every horizon, tail loss, execution failure, missingness, sampled MFE/MAE, alert latency, precision under a predefined success label, and alert density. Report effective sample sizes, cluster-aware uncertainty and multiple-testing exposure.
6. Evaluate clustered HIGH days separately. Zero HIGH is acceptable; multiple HIGHs require individual qualification. Do not tune to a trade-count quota.
7. Freeze the candidate policy and run prospectively in shadow mode. Preserve every output before outcomes arrive. A changed rule creates a new version and cohort.
8. Promote only after preregistered criteria are met with adequate coverage and uncertainty. Poor coverage, small samples or post-hoc thresholds mean inconclusive. No automatic transition to real money.

Historical reconstruction must carry source availability evidence. If the original receipt time is unknowable, mark retrospective and exclude from claims of prospective performance. Delistings, rugs and non-executable exits stay in denominators. Report conservative sensitivity bounds for missing/trapped positions rather than evaluating only survivors.

Test infrastructure with fixtures covering duplicate events, stale eligibility, late evidence, chain reorganization, corrections, missing prices, exhausted liquidity, delivery retries, horizon timing and interrupted/resumed jobs. Those tests belong to Step 3 onward; this foundation has no executable collector to test.
