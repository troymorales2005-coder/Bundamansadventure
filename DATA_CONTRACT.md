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

## Executable BUNDAR narrative contract — bundar-narrative/0.1

This dedicated prototype contract is implemented in `narrative.py`. The broader v0.1 common envelope above remains a target for ingestion; the narrative prototype does not claim to implement all of its fields (run IDs, persisted timestamps, finality, correction links, per-field status or extractor versions). Existing candidate models remain unchanged. Narrative packet completion is explicit rather than using an implicit creation clock.

| Object | Executable fields and semantics |
|---|---|
| CoinIdentity | Required nonblank `chain`, `contract_address`; optional symbol/name. Match exact chain + contract strings, never ticker. Immutable snapshot independent of legacy mutable identity objects. |
| NarrativeResearchPacket | Coin; `observed_at` cutoff; `completed_at`; category and category evidence IDs; evidence/claims/unknowns tuples; explicit synthetic/retrospective/prospective mode (default synthetic); schema and support rule versions. Computed state, reason, supporting evidence IDs and content-addressed record ID. |
| NarrativeProvenance | Nonblank source ID/type, required retrieval timestamp; optional URL, hash, retention notes. A native source identifier is sufficient when no URL exists. Hash does not replace access to source content. |
| NarrativeEvidence | Unique evidence ID; typed kind; occurrence and Radar detection timestamps; provenance; retained observation and subject identifier; optional exact token, account, post ID, relevance explanation; raw measurements tuple. All text is supplied source data/annotation, never executable instructions. |
| Measurement | Name, finite nonnegative Decimal value, unit, measurement `as_of`, scope/denominator/coverage description and optional window start. USD market cap and liquidity are separate named measurements on `market_context` evidence for the exact token. Missing measurements are absent; explain gaps in packet unknowns, never substitute zero or FDV. Counts use count units and an explicit measured universe/window. |
| ResearchClaim | Role, text and unique nonempty evidence references. Roles: hypothesis, continuation, contradiction_risk, identity_confidence, novelty_saturation, classification. Identity confidence, novelty/saturation labels and other derived classifications require nonblank `rule_version`; no rubric is implemented or certified by this engine. |

Categories are `meme/community`, `person/celebrity`, `event/tweet/external_catalyst`, `product/tech`, `unknown`. A nonunknown supplied category requires citations; it is an analyst annotation, not an automatic label.

Evidence kinds are `identity_match`, `catalyst`, `ct_x`, `subject_attention`, `ticker_mention`, `token_capture`, `competing_token`, `novelty_saturation`, `product`, `contradiction_risk`, `market_context`. Identity/capture/market evidence must match the packet token exactly. Competitor evidence requires a different chain + contract identity. Subject attention is distinct from ticker mentions. `ct_x` requires source/account, native post ID and a relevance explanation; occurrence represents the original post timestamp. Engagement/propagation observations use named measurements such as likes, reposts, replies, unique authors or observed repost count, with source provenance and scope/window. The builder neither deduplicates authors nor estimates coverage.

Identity confidence may remain unknown with raw identity-match observations instead of a numeric confidence. Continuation/runway entries are cited, unverified hypotheses about future attention, not observed future events or price forecasts. Contradictions/risks are cited claims or evidence; unknowns are explicit unanswered questions. Novelty and saturation may be raw counts/observations, or cited classifications under an explicit versioned rubric. Free text is not interpreted as an engine-generated STRONG/EARLY/LOW label.

### Support and as-of invariants

`contract-linked-narrative/v1` returns `NARRATIVE_FOUND` only when at least one hypothesis cites identity-match, capture of the packet's exact contract, and at least one catalyst/CT-X/subject-attention/product observation under the same subject identifier. The packet exposes the qualifying evidence IDs. Otherwise `NO_NARRATIVE_FOUND` and its explicit reason are computed. No threshold, weight, truth check, independent-source requirement or predictive claim is implied. Unsupported supplied hypotheses are retained as annotations, never promoted by uncited evidence. The rule is fixed in this version; unknown rule versions are rejected.

Require timezone-aware inputs and normalize to UTC. Enforce `occurred_at <= retrieved_at <= detected_at <= observed_at <= completed_at`. Measurement window start <= measurement as_of <= evidence detection. Reject future evidence instead of dropping it silently; earlier source time with later receipt/detection still fails. Receipt timestamps for retrospective sources must reflect actual later retrieval, so a later backfill cannot masquerade as a prospective packet at the original event time. Unknown original occurrence times are not accepted in this prototype; record the gap externally instead of inventing timestamps.

Latency fields: evidence `detection_latency_seconds = detected_at - occurred_at`; packet `completion_latency_seconds = completed_at - observed_at`; catalyst freshness is a tuple of evidence ID and `observed_at - occurred_at` seconds. Each evidence detection-to-completion interval can be calculated from its preserved timestamps. No freshness bucket or arbitrary expiration limit is assigned.

Canonical JSON preserves UTC times, Decimal strings, all citations and provenance, status and rule reason. Packet ID is SHA-256 of canonical content; it is not included recursively in its own hash. It provides deterministic content identity, not source authenticity. The in-memory store rejects identical IDs and returns packets only after completion; it does not silently repair earlier records.

## Executable CT/X contract — ct-parser/v1

This evidence layer preserves the Narrative contract above. It neither changes the support rule nor implements WATCH/HIGH policy.

| Object | Executable fields / interpretation |
|---|---|
| RawXPost | Required post ID, detection/parse time, source provenance and immutable full-response JSON; optional raw text, author ID/username, post time, immutable account JSON; tuples of URLs/mentions/hashtags/cashtags/references/public metrics; explicit data mode. Missing scalar fields are null; absent API metrics are absent, not zero. |
| PostReference / PublicMetric | Native reference type + ID (including unknown types); metric name + nonnegative integer. Replied-to, quoted and reposted IDs remain distinct. Missing reference arrays do not prove originality. |
| CTRegistry | Known-at time, explicit version, immutable SubjectAlias and TokenAlias entries; content ID. Subject aliases support person/company/product/meme/animal_character/event/phrase/subject kinds. Token aliases link names/cashtags/subject hypotheses to chain+contract without proving association. |
| ParsedCTPost | Raw snapshot, target identity, cutoff, matched entities and literal strings, subjects, all candidate IDs, resolved exact-address IDs, relationship/classification RuleInterpretation, possible external catalyst boolean, unknowns, registry ID and parser version. |
| RuleInterpretation | Descriptive label, reason, nonempty evidence IDs, explicit rule version and as-of boundary. Parser outputs cite raw snapshot and registry. Noise outputs cite relevant raw snapshots and preserve config on CTPropagation. |
| CTPropagation | Target, subject, receipt-window start/end, selected parsed snapshots, immutable JSON facts, separate interpretations, PropagationConfig and optional cited catalyst evidence. |
| NarrativeCTBridge | CT_X evidence tuple, cited/versioned exclusion reasons and cutoff. No automatic identity/capture/hypothesis is emitted. |
| ApiUsageEvent / Ledger | Request ID/time/status; returned posts, actual user lookups, pagination requests, duplicate receipts, API payload error count, known units, optional remaining/reset counters; optional caller-configured estimated units with required method version. Ledger totals requests/HTTP errors/429s by cutoff. Known/estimated units stay null if any event lacks them. No dollars/pricing assumption. |

### Fixed descriptive rules

`ct-parser/v1` extracts EVM-shaped hex and base58-shaped address **candidates**, literal registered addresses, `$cashtags`, token-name aliases, hashtags, accounts, HTTP URLs/domains and dictionary subjects/entities. Base58-shaped text is not confirmed as a contract. Address strings use exact matching; no chain or address-case normalization is invented. A registered address matching multiple chains remains ambiguous. Ticker/name collisions remain ambiguous even when subjects overlap. An unresolved/unregistered address is retained as a candidate but cannot establish relation to the supplied target. Nonmatching text is unrelated to that target, not globally irrelevant.

Relationship precedence: missing text → AMBIGUOUS_RELATION; uniquely registered target exact address → DIRECT_CONTRACT_REFERENCE; unresolved target address chain or colliding target alias → AMBIGUOUS_RELATION; target alias only → DIRECT_TICKER_OR_NAME_REFERENCE; overlap with target's registered subject hypothesis → INDIRECT_NARRATIVE_RELATION; otherwise UNRELATED. Explicit multiple contracts are preserved, never selected as a winner. Exact mention proves only a textual reference, not ownership, identity of an official project or narrative capture.

Classification precedence: promotional phrases (`buy now`, `100x`, `gem alert`, `don't miss`) → PROMOTION_OR_SHILL; reply/quote → REACTION; repost → NARRATIVE_PROPAGATION; news phrases (`news`, `announced`, `launches`) → NEWS_OR_INFORMATION; address or token alias → TRADER_OR_CALLER_MENTION; registered subject plus `meme`/`community` → MEME_OR_COMMUNITY; remaining subject-only text → candidate ORIGINAL_CATALYST; otherwise UNKNOWN. These labels describe matched structure. They do not establish intent, account profession, originality, causality, bot status or predictive ability. Possible external catalyst means a subject match without address/cashtag/name references; it may also occur on a reaction/repost. Exact rules, matches, raw and registry evidence remain inspectable.

### Measurements and anti-hindsight

Require posting (when known) <= retrieval <= detection <= parsing <= CT cutoff, plus registry known-at <= parsing/cutoff. Unknown posting time is retained without a fabricated latency and excluded from Narrative CT_X conversion. Replays using later downloaded engagement/profile fields must use their actual receipt time. Source timestamps alone never make later API snapshots available earlier. `data_mode` marks synthetic/retrospective/prospective sources; there is no inferred historical availability.

Propagation measures a **receipt window**, inclusive bounds. Select the latest cutoff-safe snapshot per post ID; older raw snapshots stay in the store. Reject future interpreted results and mixed registry versions. Relevant sample = posts matching requested subject or naming the target as a candidate. Specific-token mentions require a uniquely mapped exact target address; ticker/name mentions are counted separately and can remain ambiguous. Underlying-subject mention count is literal matching posts, including posts without any token reference. Missing author counts and known unique-author counts are separate. Independent-source count remains null with no inferred independence evidence.

Facts include total received observations, duplicate receipts, selected/relevant posts, known unique authors, unknown authors, direct contract/ticker-name/subject/specific-token posts, observed repost/quote/reply counts, first receipt/known occurrence/latest receipt, exact duplicate count/ratio, normalized duplicate count, near-duplicate pairs, similar pairs within a timing window, repeated URL/contract/promotion counts, co-mentioned competing contracts and contract→post evidence. Count units and denominators describe this sample, not the X population. Contract competition is observed subject co-mention evidence, not proof of an economic competitor. API public engagement counters remain raw per-post snapshots, not invented totals.

`ct-propagation/v1`: exact duplicates count surplus identical raw texts (`sum(count-1)`); ratio denominator = relevant posts with text. Normalized duplicates use casefolded/collapsed-whitespace text. Near-duplicate pairs use SequenceMatcher similarity >= configurable 0.9 by default; tight timing uses absolute detection difference <= configurable 60 seconds. These are documented text/noise experiment parameters, not financial thresholds. Similar-pair counts use pair units, not unique-post units. Repeated URL/contract counts count surplus occurrences; promotion counts use the explicit promotional-phrase classification. No bot/manipulation finding is generated.

Latency: post→detection (null without source time), detection→parsing, catalyst age, and earliest observed same-subject post after catalyst occurrence (excluding catalyst post ID). The last interval is temporal co-occurrence, not a causal inference. Empty/unavailable ratios/timestamps remain null. All measurements can be traced to raw snapshots, registry, cutoff and config; caller edits to returned fact dictionaries cannot mutate stored JSON.

The Narrative bridge emits only literal same-subject CT observations with known account/time. It carries raw source URL/ID/hash and parser/registry lineage. A negated association can still contain an observed mention; neither it nor positive chatter establishes capture. `NO_NARRATIVE_FOUND` remains the default without separately supplied identity/capture/hypothesis support.

### Adapter, accounting and limitations

Official-response normalization handles single/list `data`, optional `includes.users`, `entities`, `referenced_tweets` and `public_metrics`, while preserving other response fields in immutable raw JSON. It performs no HTTP request and makes no assumption about current account entitlement. `.env` stays ignored; only a blank variable declaration is committed in `.env.example`. Configuration stores an environment-variable **name**, never the token value. The ledger accepts actual caller-reported request events; offline normalization does not increment usage. User expansions are not counted as separate user lookups. Known units are accepted only as explicit metadata/configured facts; estimated units require an explicit caller-supplied method/version. No automatic estimate or dollar cost is calculated.

This slice is not the entire target common envelope: no durable persistence/run IDs, correction links, clock-uncertainty quarantine, account qualification, semantic negation engine, recursive reference lookup, source-universe completeness or broad NLP. Literal dictionaries do not discover all novel narrative subjects. The synthetic replay checks labeled parsing/rule conformance; it cannot establish real-X recall or trading utility.

## Real X replay validation contract v1

New transport/replay modules preserve the existing raw/CT/Narrative schemas and versions.

Capture manifest freezes integer ceilings (4 attempts / 31 primary posts / 62 total resources), timeout, response-size bound, host and no-redirect/retry/pagination behavior. Exclusive-create `request-NN.json` reservations record endpoint/method/parameters/requested time and worst-case post/resource allocation, before any HTTP operation. Raw response bytes and `request-NN-response.json` retain actual receipt time, status/null transport failure, allowlisted rate headers, IDs/counts, pagination metadata, API errors, usage event, SHA-256 and explicit stop reason. Monetary charges and usage units remain unavailable unless authoritatively exposed; rate limits are never substituted for credits/costs. An explicitly reviewed local pre-HTTP denial appends a review record without removing the failed reservation or increasing ceilings. HTTP errors stop collection.

`split_manifest.json` freezes seed, source IDs/receipt/hash, grouped assignments, registry content ID, plan content ID and parser source hash. Groups connect known authors, shared/direct references and normalized exact duplicates; held-out groups are selected by seeded content hashes, approximately 25%, leaving development groups where possible. One-group samples cannot produce a held-out set; report insufficiency instead of inventing independence. Grouping does not establish narrative/population independence.

`human_labels.json`: version, manifest ID, target and canonical known subject hints; one row per sample post, raw source reference, status pending/labeled, human reviewer ID/time, notes, optional error categories and labels. Labels: relevance; subject IDs; relationship; descriptive class; tokenless external catalyst; direct/competing chain:contract IDs; duplicate/repost/quote/reply post IDs. Null = pending; empty array = known none; UNKNOWN = reviewed insufficient evidence. Reviewer timestamps must be aware and no earlier than original receipt. Predictions are absent. Lists do not infer chains from tickers. Human labels must cover the sample once and preserve source lineage.

Evaluation refuses unreviewed labels, changed parser/registry/plan/raw sources, or silent label replacement after a split has been evaluated. Development and held-out locks/reports remain separate. Held-out output is sealed until explicit release. Human abstentions are excluded from scored fields; all-abstention rows cannot inflate exact-match accuracy. Metrics include denominators, null precision/recall for empty denominators, identity/subject set TP/FP/FN, per-field accuracy, coverage/parsing errors, ambiguity/UNKNOWN/lineage checks and preserved post-level mismatches. Results do not contain financial outcomes. Proposed error categories map to the user's taxonomy; without human diagnosis they are provisional.

Original source cutoff and actual computation are distinct. Raw detection/retrieval use original response receipt. Parse/completion time uses actual later computation, never a guessed past value. Replay restricts inputs to original source bytes and a dictionary known before receipt, retaining source cutoff in the wrapper report. The stricter existing CT parser still rejects later-completed interpretations as if they existed at original receipt. Historical downloaded data cannot become prospective performance merely through this replay.

All genuine data/templates/results remain in local gitignored `data/real_x_replay_v1/`. Read-only real-response tests verify saved hashes/timestamp boundaries without network calls and skip when local data is absent. Unit tests for scoring use explicitly synthetic annotations, never the real sample's ground truth. Completed human labels are required for real accuracy and final readiness conclusions.
