# Build log

## 2026-10-01 — Step 1 foundation

- Created an independent Meme Coin Radar directory and repository with its own VS Code workspace; no HVAC files were used or modified.
- Recovered the full uploaded transcript from the referenced conversation attachment and preserved an exact local research copy with a SHA-256 manifest.
- Read the established plan and mapped source timestamps to unvalidated hypotheses, including the Axiom thresholds and ambiguous global-fees unit.
- Formalized FOMO gating, WATCH/HIGH semantics, immutable evidence, outcome horizons, executable-return assumptions and the Discovery/Exit boundary.
- Added the validation plan and a blank, explicit Step 2 source-audit framework. No vendor access or current API capability has been verified.
- No services, subscriptions, purchases, credentials, live collectors, alerts or trading systems were created.

## 2026-10-01 — Immutable observation foundation

- Added a Python schema package under `src/meme_coin_radar` for immutable candidate observations and audit-friendly provenance.
- Implemented `TokenIdentity`, `CandidateObservation`, `ObservationStore`, `FomoExecutability`, and supporting evidence dataclasses for token context, market structure, narrative analysis, social evidence, wallets, attention, catalysts, verification, and outcomes.
- Enforced chain + contract identity, explicit provenance, UTC timestamps and append-only/as-of reconstruction in the model layer.
- Added validation tests covering token identity rules, timestamp/provenance requirements, FOMO executability states, and historical snapshot reconstruction.
- Kept the implementation read-only and research-only; no live data sources, paid APIs, trading systems or financial commitments were added.

Verification: executed the focused regression suite for the immutable observation foundation. Result: `4 passed in 0.04s` using the local workspace Python runtime.

Next milestone: not started. The next phase remains a source-feasibility and fixture-based ingestion slice, subject to approval before implementation begins.

## 2026-10-01 — BUNDAR Narrative Research Prototype

- Inspected repository status/history, all current Python models/tests, README, architecture, data contract, decisions, roadmap, build log, source audit and validation/research notes. No separate historical-data implementation was present. Preserved existing `models.py`, legacy tests and all research/source files.
- Added `narrative.py` with deeply frozen typed coin identity, provenance, evidence, raw Decimal measurements, cited annotations, packet, offline builder and in-memory append-only packet store. Exported its public types from the existing package.
- Added fixed support rule `contract-linked-narrative/v1`: a hypothesis must cite same-subject identity, exact-contract capture and narrative evidence. Exposed state, reason, support IDs, canonical JSON and deterministic SHA-256 packet identity. Explicit `NO_NARRATIVE_FOUND` retains unsupported hypotheses for inspection.
- Required aware UTC-normalized occurrence/retrieval/detection/cutoff/completion timestamps and rejected future/late evidence, future measurements, wrong contract references, dangling citations and duplicate evidence. Preserved detection latency, completion latency and raw catalyst freshness.
- Represented CT/X account/post/relevance, underlying subject attention separately from ticker mentions, competition, saturation/novelty, market context, identity evidence/confidence, runway hypotheses, contradictions/risks, unknowns and provenance. Derived classifications require an explicit caller-supplied rubric version and citations; no classification rubric is evaluated.
- Added 34 narrative test cases alongside the four existing regression cases. Set pytest discovery to `tests/` after the unrestricted run tried to parse an existing UTF-16 `test_output.txt` as a doctest and failed collection; that artifact was preserved.
- Updated README/ARCHITECTURE/DATA_CONTRACT/DECISIONS/ROADMAP/BUILD_LOG. Application brand is BUNDAR; repository/package engineering names remain unchanged.
- No live APIs, J7/X integrations, paid services, purchases, LLM scoring, execution/trading, HIGH/WATCH policy changes, predictive weights, thresholds or price forecasts were added.

Verification: full configured suite `python -m pytest -q -p no:cacheprovider` using the bundled Python runtime: **38 passed in 0.12s** on the final run (initial successful run: 0.24s). Synthetic fixtures test mechanics only, not source truth or trading edge. `git diff --check` passed.

Assumptions/limits: annotations and subject IDs are caller supplied; addresses use exact chain-specific strings without inferred normalization; occurrence/retrieval/detection must be known; timestamps are trusted inputs; measurements are nonnegative (signed flows are outside this slice); completion time is explicit; durable persistence, provenance authenticity, deduplication of source events and correction links remain unimplemented. New narrative immutability does not upgrade legacy nested objects. Default mode is synthetic; historical backfill cannot invent earlier receipt times.

Proposed next milestone: fixture/manual replay with source coverage, deduplication, explicit correction lineage, rubric registry and durable-storage design/tests. Complete the source feasibility audit before live collection. Stopped after this prototype foundation.

## 2026-10-01 — BUNDAR CT/X Parser Experiment V1

Inspected git status/files, current Narrative module, existing models/tests, all core documentation and prior research boundaries before edits. The shared checkout contained the previous milestone's uncommitted changes; they were retained. No new historical-data/research implementation from John appeared. `models.py`, `narrative.py`, both prior test files, research/source files, `.gitignore` and `pytest.ini` were not changed during this milestone. The existing README has a pre-existing NUL-containing trailing title; preserved it rather than rewriting unrelated content.

Exact files added:

- `.env.example`
- `src/meme_coin_radar/ct_models.py`
- `src/meme_coin_radar/ct_parser.py`
- `src/meme_coin_radar/ct_replay.py`
- `src/meme_coin_radar/x_adapter.py`
- `tests/test_ct_parser.py`
- `tests/fixtures/ct_x_v1.json`
- `tests/fixtures/CT_X_REPLAY.md`
- `CT_X_REPLAY_REPORT.json`

Exact files modified during this milestone: `src/meme_coin_radar/__init__.py`, `README.md`, `ARCHITECTURE.md`, `DATA_CONTRACT.md`, `DECISIONS.md`, `ROADMAP.md`, `BUILD_LOG.md`. Existing `.gitignore` already covers `.env` / `.env.*` while allowing `.env.example`; verified the configuration without accessing real secrets.

Implemented architecture:

- Supplied official-v2 response/local fixture → immutable raw payload/account snapshots + append-only raw store → point-in-time alias registry and deterministic parser → raw measurements and separately cited/versioned descriptive interpretations → explicit Narrative bridge → unchanged Narrative builder.
- Preserved post/author/entity/reference/API engagement data, unknown fields, occurrence/detection/parse times, provenance URLs/source IDs/hashes and source account snapshots without source-quality inference.
- Added direct-address/alias/indirect-subject/ambiguous/unrelated relationships. Dictionary-based subjects work without any coin mention. Unknown subjects retain original text. Multiple contracts and chain/ticker collisions remain visible; no winner is chosen.
- Measured receipt-window post/known-author counts, separate subject/contract/ticker counts, reference behaviors, exact/normalized/near duplicate observations, repeated URL/contracts, competing-contract post evidence and deterministic latency. Independent-source count remains null. Noise labels preserve explicit rule/config/evidence; no bot/manipulation assertion.
- Rejected future creation/detection/parsing, future registry/derived result/catalyst and later engagement snapshots at earlier cutoffs. Preserved old raw snapshots; deduplicated only the aggregation view by latest cutoff-safe post snapshot. Ignored expanded referenced-post bodies for interpretation.
- Integrated CT observations without creating identity/capture/hypothesis evidence. Reported missing-field exclusions instead of guessing values or weakening the Narrative contract. Multi-subject bridge IDs preserve distinct subject/version lineage.
- Added response-only adapter with no transport, environment-variable-name configuration and externally reported immutable usage events. Ledger tracks requests/posts/user lookups/pagination/duplicates/errors/429s, rate metadata and explicit known or method-versioned estimated units. It invents neither units nor costs.
- Added public exports, 48 additional regression/replay test cases and 19 manually labeled synthetic fixture scenarios, including all 15 requested cases. No new runtime dependencies.

Verification: complete suite `python -m pytest -q -p no:cacheprovider` using bundled Python: **86 passed in 0.34s** on the final run (preceding run: 0.45s). All 38 prior tests passed. `git diff --check` passed; `git check-ignore` confirmed `.env` and `.env.local` are ignored. Standalone replay CLI exited 0 and regenerated `CT_X_REPLAY_REPORT.json`: **19/19 exact case matches**, 22 accepted posts, 1 expected future rejection, exact-contract identity TP=6/TN=16/FP=0/FN=0; precision/recall/accuracy=1.0. Three ambiguous relationships (colliding ticker, missing text, stock/ticker confusion), three UNKNOWN classes (irrelevant, missing, unregistered subject); 0 unexpected parsing errors and 0 structurally unsupported inferences. Fixture coverage=1.0 means all supplied cases attempted, not coverage of X. These are synthetic rule-conformance results, not open-world parser or financial performance.

Capabilities: literal registered entity/subject extraction, tokenless possible catalysts, conservative reference resolution, evidence-backed descriptive classes, scoped propagation counts/noise observations, source snapshots and auditable Narrative-compatible CT evidence.

Cannot infer: truth, causal originality, semantic negation, all unseen entities/narratives, account independence/skill, bot/manipulation identity, actual narrative capture, complete X reach, prospective trading utility, HIGH eligibility or price outcomes. Registry subject links and timestamps are trusted supplied research inputs. Exact chain/address strings are required; normalization remains outside V1. Similarity=0.9 / timing=60s are exposed text-experiment parameters, not trading thresholds. Stores/ledger are temporary/in-memory and not tamper-proof or durable.

Existing Narrative issues/limits found: CT_X requires known account/occurrence while real responses may omit them; bridge exclusions preserve these unknowns. The support rule validates cited presence, not semantic truth or independent confirmation; therefore the parser intentionally cannot generate capture/identity/hypothesis claims, including for negated/coincident mentions. The Narrative evidence schema has no dedicated parser/registry fields; bridge relevance and content IDs carry this lineage, while ParsedCTPost preserves structured interpretation metadata. No existing Narrative behavior was changed.

Official adapter field assumptions checked against X lookup/rate-limit documentation (linked in ARCHITECTURE). No account entitlement/billing was inspected. **Zero live X API calls**, zero paid usage, purchases/upgrades, alerts, HIGH changes, wallet scoring, predictions or execution/trading. Stopped after CT/X Parser Experiment V1.

Exact recommended next milestone: **Real X Response Replay Validation V1** — import a small permitted saved/exported official-response sample at actual receipt times, independently label and evaluate held-out posts/unknowns/collisions against the offline harness. Only after verified entitlement/cost and separately authorized no-cost or explicit budget should a bounded read-only lookup transport be added with fail-closed request/post/unit caps, rate-limit ledger and no automatic pagination/retries. Durable storage/Supabase and correction links remain separately scoped work.

## 2026-10-01 — Real X Response Replay Validation V1 (in progress)

User supplied the new milestone specification, explicitly required a credential-configuration stop, then confirmed “Credential configured. Continue … exactly as specified.” Inspected shared git state/adapter/environment template/ignore rules/models/parser/replay/tests first. Read only credential availability (never printed value); used the configured local `.env` without changing or committing it. Preserved all prior uncommitted work and found no new separate historical-data implementation from John.

Exact source files added this milestone:

- `src/meme_coin_radar/x_bounded_capture.py`
- `src/meme_coin_radar/x_real_replay.py`
- `tests/test_x_bounded_capture.py`
- `tests/test_x_real_replay.py`

Exact existing files modified: `README.md`, `ARCHITECTURE.md`, `DATA_CONTRACT.md`, `DECISIONS.md`, `ROADMAP.md`, `BUILD_LOG.md`. Existing CT models/parser/replay, response adapter, Narrative models, package exports, prior tests, `.env.example`, `.gitignore`, `pytest.ini` and research files remain unchanged in this milestone.

Implemented separate opt-in credential loading/transport with fixed api.x.com paths, no redirects/retry/pagination loops, 20-second timeout, raw-response size guard, token-echo redaction and allowed rate headers only. Frozen ceiling persisted before requests: 4 total attempts / 31 primary posts / 62 resources (including author expansions). Every reservation persists before connection, consumes budget even if it fails, and is preserved across restart. Responses/bytes/hash/receipt/status/error/pagination metadata/usage events persist before normalization. `.env` and all real sample material under `data/` are gitignored; verified with `git check-ignore`.

Requests/attempts (UTC; local Eastern time is UTC-4):

| ID | Endpoint | Result | Receipt | Primary posts / total resources |
|---|---|---|---|---|
| request-01 | GET https://api.x.com/2/tweets/1228393702244134912 | Local sandbox socket denial; no HTTP status | 2026-10-01 21:35:44.970872 UTC | 0 / 0 |
| request-02 | Same single-post lookup, after explicit reviewed local-denial record and network approval | HTTP 200 | 2026-10-01 21:37:34.961333 UTC | 1 / 2 |
| request-03 | GET https://api.x.com/2/tweets/search/recent, max_results=10 | HTTP 200 | 2026-10-01 21:39:37.667174 UTC | 10 / 20 |
| request-04 | GET https://api.x.com/2/tweets/search/recent, max_results=10 | HTTP 200 | 2026-10-01 21:39:50.873998 UTC | 10 / 20 |

Before the reviewed second attempt, unauthenticated DNS succeeded and socket diagnostics established local PermissionError errno 13 before HTTP. The failure and review are retained; no automatic retry was made. HTTP failures cannot be reopened by the review mechanism. Only the reviewed existing user-authorized requests ran with network access. No approval-review rejection occurred.

Exact two frozen search queries:

```text
("memecoin" OR "$PEPE" OR "0x6982508145454ce325ddbe47a25d4ec3d2311933") lang:en
("pepe the frog" OR "meme") lang:en
```

Requested fields: created_at,author_id,entities,referenced_tweets,public_metrics,conversation_id; author_id expansion; username,public_metrics,verified user fields. Verification ID comes from official X lookup documentation. PEPE is an exploratory target, not a recommendation; address matches the [CoinGecko Ethereum API example](https://www.coingecko.com/en/api/ethereum). Registry/dictionary, target/queries/split seed froze before search receipts. No token mapping was learned from winners or outcomes. Account-specific billing was not queried beyond the authorized sample.

Actual totals: **4 reserved attempts, 3 successful API/HTTP requests, 21 posts, 21 expanded authors, 42 total returned resources, 0 duplicates, HTTP/API errors, 429s or pagination requests; 1 local pre-HTTP transport failure**. Lookup rate limit/remaining/reset: 450/449/1790891555. Search rate metadata: 450/449/1790891677 then 450/448/1790891677. Page cursors are preserved but unused. Known usage units/credits and monetary charge remain undetermined from response metadata; no dollar estimate, credit purchase, upgrade or subscription change. Capture ceiling is exhausted; no further requests will run in this experiment.

Prepared 20 genuine research posts (lookup is control only), 20 distinct observed author IDs, all with text/author/created/public metrics; raw API inventory shows 3 replied_to and 7 retweeted references, 2 posts with cashtag entities, 9 with URL entities, no quote references and no missing core fields. This does not establish semantic relevance, independent authors, tokenless catalysts or full requested diversity. Missing coverage is preserved; no extra calls were made to fill it.

Frozen deterministic grouped split: **15 development / 5 held-out**. Groups join known authors, reference lineage and normalized duplicate content. Parser source hash, registry/plan/source hashes, assignments and seed persist in `split_manifest.json`. Related narratives may still overlap; no population independence is claimed. `human_labels.json` has **20 pending blank human rows**; LABEL_REVIEW shows raw facts without predictions or split membership. No AI/parser prediction was used as ground truth. Held-out predictions remain sealed.

Implemented label schema/provenance/aware-time validation, explicit UNKNOWN abstentions, separate split metrics, set-based identity/subject precision/recall/FP/FN, field accuracies, exact-match denominators, parsing errors/coverage and preserved mismatch/error categories. Locks prevent silent post-evaluation label replacement; future/raw/registry/plan/parser drift fails closed. Tests use clearly synthetic annotations only; these never populate real human labels.

Timestamp issue found: existing parser requires parsed_at <= observed_at, so actual later normalization cannot honestly become a receipt-time completed packet. The wrapper preserves original receipt `source_cutoff_at` and actual later computation separately, reads only original source bytes with the registry known at receipt, and marks replay retrospective. It does not invent past parse timestamps or alter the Narrative support rule. The bridge tests reject later completion masquerading as an earlier packet.

Development-only actual-response integrity smoke: **15/15 passed**, **0 parsing errors**, **1 CT evidence emitted**, **14 explicit same-subject exclusions**. Verified provenance/occurrence/detection, CT-only evidence, future completion rejection, ambiguity preservation and **NO_NARRATIVE_FOUND**. These are structural checks, not proof of correctly understanding posts. Held-out predictions were not accessed. Development and held-out performance metrics are **null/pending**, as are real FP/FN and semantic failure analysis.

Local ignored artifacts: capture manifest; request-01 through request-04 reservations/raw bytes/response envelopes; explicit request-01 review; registry/collection plan; split manifest; blank human_labels.json; LABEL_REVIEW.md; raw inventory; development integrity checks; usage_report.json; evaluation_status.json. Files use append-only/exclusive-create snapshots; no existing source/history is overwritten. Local filesystem snapshots are not a durable database or tamper-proof archive.

Verification: full suite with bundled Python `python -m pytest -q -p no:cacheprovider`: **114 passed in 2.59s** on the final run (preceding run: 1.97s), including all 86 pre-existing tests and 28 new transport/replay tests. `git diff --check` passed. Genuine saved-response hash/timestamp tests are read-only and make no requests; they skip when local capture is absent. No parser rules, tests or HIGH criteria were weakened.

**Milestone remains incomplete, waiting on human labels.** No grounded real development/held-out accuracy claim, trading edge or readiness for prospective CT observation exists yet. Immediate next step: human reviews raw posts and fills local labels; then run development evaluation and explicitly release the unchanged frozen parser for held-out evaluation, preserving errors. Only those results can support a separately scoped/budgeted prospective observation proposal. No HIGH/wallet scoring, predictions, trading/execution, continuous monitoring, paid plan changes or larger ingestion were implemented.
