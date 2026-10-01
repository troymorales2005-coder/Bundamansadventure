# V1 Discovery data contract

Version: 0.1, research baseline, 2026-10-01. This human-readable contract precedes executable schemas. Field names are proposed canonical names; all threshold parameters remain versioned research choices.

## Common envelope and missingness

Every record requires `schema_version`, immutable `record_id`, `record_type`, `created_at`, `source_id`, `evidence_ids`, and `run_id`. Coin records require `coin_id = chain_namespace:chain_id:contract_address`; normalization must respect chain-specific address rules. Never merge by symbol.

Times are UTC RFC3339 with milliseconds. Record `event_at` (source event time, nullable with reason), `received_at` (first local receipt), `persisted_at`, and any chain block/transaction identifiers and finality state. Feature snapshots also require `cutoff_at`, `computed_at`, definition version and source lookback bounds. Evidence is usable only if received by cutoff; late arrivals never repair a prior decision silently. Clock uncertainty/future timestamps quarantine evidence pending review.

Each measured or derived field has `value`, `unit`, `status`, `as_of`, `evidence_ids`, and `method_version` when derived. Status is `observed`, `derived`, `unavailable`, `stale`, `not_applicable`, or `invalid`. Missing values are null with a reason, never zero. Confidence is nullable and must cite a rubric; invented precision is prohibited. Counts are nonnegative integers; money uses decimal representation and explicit currency; ratios are fractions [0,1] unless explicitly signed or unbounded. Store precision and denominator definitions.

Corrections append `supersedes_record_id`, reason and new evidence; preserve the original. Source events have deduplication keys. Synthetic, retrospective and prospective data have distinct `data_mode` values and never silently share an evaluation cohort.

## Evidence and identity

This project milestone adds a machine-readable schema layer that preserves the requirements above while making the object model explicitly append-only and as-of reconstructable.

| Group | Required capture |
|---|---|
| Evidence | Source URL/native ID or transaction; observed/received times; permitted retained payload location and SHA-256; access/retention limitations; extractor version; source claim vs analyst annotation |
| Coin context | Chain, contract, symbol/name as observed, deploy time, token age seconds, launchpad, pool IDs, lifecycle `new_pair/final_stretch/migrated/other/unknown`, migration time and evidence |
| Valuation | Price USD and quote source; market cap USD; circulating supply and method; FDV separately; valuation freshness and reliability. Do not substitute FDV silently |

### Current Python foundation

The codebase now includes a schema layer in `src/meme_coin_radar/models.py` with the following responsibilities:

- `TokenIdentity` requires chain + contract address and rejects ticker-only identity.
- `CandidateObservation` requires explicit provenance, observed timestamp and evidence lineage.
- `FomoExecutability` is restricted to `TRUE`, `FALSE`, or `UNVERIFIED`.
- `NarrativeAnalysis.result` supports the explicit `NO_NARRATIVE_FOUND` result.
- `ObservationStore` captures append-only historical snapshots and reconstructs as-of evidence without allowing late information to rewrite earlier decisions.

## Signal families

| Family | Fields and definitions to capture |
|---|---|
| Market/liquidity | Liquidity USD by pool and usable route; depth by test notional; buy/sell quotes; spread, price impact, fees; volume USD, buy/sell counts and unique buyer/seller addresses over explicit windows; window-over-window acceleration; returns and extension from a defined reference |
| Structure/safety | Holder count; top-N shares with N and excluded pool/burn/treasury addresses; developer/insider share with attribution confidence; sniper/bundle/cluster estimates; mint/freeze or equivalent controls; liquidity ownership/lock/removal evidence; transfer restrictions/taxes; suspicious volume; raw global-fees value, currency and aggregation scope |
| Narrative | Category `community_meme/tweet_catalyst/product_tech/celebrity/other/unknown`; catalyst ID/time; semantic relationship with explanation; strength/freshness rubric; competing token count over explicit universe/window; novelty, saturation, failed predecessor count; current-market match using cutoff-safe evidence |
| X/social | Post/account IDs; author history known at cutoff; original/repost counts and unique authors; mention velocity and engagement acceleration with windows; account-quality version; coordinated/bot-like indicators and uncertainty; catalyst-to-coin mapping; platform coverage |
| Wallets | Wallet ID/chain; qualification snapshot, history cutoff, sample size, realized P&L method including costs/transfers, win rate denominator, holding times, early-entry behavior, drawdown; observed buys/sells and entry MC; net accumulation; cluster IDs/confidence; independent qualified cluster count |
| Attention | Axiom concurrent viewers and timestamp if available; change per second/window; FOMO theses and unique authors; thesis sentiment/reason; community velocity; ratios to market cap/holders with denominators; suspected manipulation and source coverage |
| Project credibility | Applicability; claimed product vs observed working demo; observation method/time; developer identity/reputation evidence; reputable mutuals/followers under a fixed historical account list; unknowns and conflicts. Social links are not proof of legitimacy |

Windows, rubrics and account lists are versioned. Undefined windows make a value non-comparable. Correlated wallets/posts/theses must not be counted as independent confirmations. Launchpad reputation is time-dependent research, not a permanent whitelist.

## FOMO eligibility and executability

An `eligibility_check` requires coin ID, `checked_at`, `expires_at`, method, source evidence, chain support status, exact token availability status, buy-route and sell-route status, applicable user/region restrictions when known, quote timestamp, quote currency, test notional and failure reason. Status values are `verified`, `unsupported`, `unavailable`, `unknown`, `stale`. No supported-chain list is asserted in this foundation.

Only fresh `verified` eligibility and execution evidence can pass the actionable gate. A token visible in search or a chain supported in general is insufficient. Quote-based capacity is conditional, never a fill guarantee. If lawful reliable verification is unavailable, retain internal research candidates with a blocked reason; emit no actionable WATCH/HIGH. Freshness TTLs and route requirements must be established in Step 2 and frozen before experiments.

## Decisions and alerts

Every considered candidate gets an immutable `decision_id`, cutoff, feature snapshot IDs, gate results and reasons, policy/config hash, data coverage and status (`excluded`, `insufficient_data`, `no_alert`, `WATCH`, `HIGH`). Store exclusions as carefully as alerts.

An alert requires `alert_id`, decision ID, `generated_at`, `persisted_at`, `delivered_at` (nullable), class, `mode` (`shadow` or `validated_paper`), frozen reference price/MC/liquidity, eligibility evidence, signal reasons, counterevidence, missing fields, model version, validation status and related prior alert. Persist before delivery; delivery time does not replace generation time.

WATCH identifies an eligible candidate worth observation under its policy. HIGH requires a policy that passed preregistered prospective validation; no such policy exists yet. Experimental HIGH labels must remain explicitly shadow-only. Neither class instructs entry or sizing. Deduplication suppresses repeated delivery of the same event, not independently qualifying coins. No daily quota.

## Outcomes and executable-return protocol

Track all cohort candidates, including excluded/no-alert controls and failed/delisted tokens where observable. Alert horizons are exactly 300, 1800, 7200, 21600 and 86400 seconds after `generated_at`. Each outcome records target time, actual observation time, delay, quote/evidence IDs, status and observation coverage. Never substitute an old price silently.

Before a run freeze simulation parameters: test notionals (research probes, not sizing advice), decision/entry latency, fee schedule, quote freshness, route constraints, maximum observation lag, sampling cadence and failure/partial-fill treatment. These remain unset until source feasibility is known; a run with unset parameters is not evaluable.

At simulated entry time, estimate tokens actually received after entry costs and route price impact. At each horizon obtain a sell-side liquidation estimate for that quantity, including exit costs and capacity. `net_return = (net_exit_proceeds - total_entry_cost) / total_entry_cost`. Avoid double-counting fees already embedded in quotes. Store mark-price return separately; market-cap change is not executable return.

Record attempted/filled quantity, partial fills, unfilled residual and valuation policy, route failure, fees, spread, slippage estimate, price impact, liquidity/depth, entry and exit latency, and simulation confidence. No route means `non_executable`; missing data means `unobservable`, not a fabricated zero return. Report both explicitly, with conservative loss-bound sensitivity for trapped positions so failures cannot improve apparent results by disappearing.

For every horizon compute MFE = maximum sampled return and MAE = minimum sampled return over entry through that horizon, including the initial zero reference. Store mark-price and executable-series extrema separately, timestamps, cadence, gaps and coverage. Sparse snapshots produce only sampled extrema, not a claim of continuous highs/lows. No executable entry means executable MFE/MAE are unavailable. Peaks are descriptive outcomes, never assumed achievable exits.

Outcome jobs append results and corrections without changing alert snapshots. Separate future outcome storage prevents those values from becoming pre-alert evidence.
