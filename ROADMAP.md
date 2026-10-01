# Build roadmap

| Step | Deliverable | Completion gate | Status |
|---|---|---|---|
| 1 | Research specification and separate repository | Traceable source, data contract, decisions, validation boundaries | Complete; v0.1 baseline |
| 2 | Data-source feasibility audit | Official access methods, permissions, timestamps, coverage, latency, cost, FOMO verification and fallbacks documented | Next |
| 3 | Ingestion and immutable storage | Versioned machine-readable schemas; fixture-based collector; deduplication, time and correction checks | In progress: immutable candidate + observation foundation implemented |
| 3a | BUNDAR Narrative Research Prototype | Immutable evidence/packet, deterministic builder, explicit unsupported result, cutoff/latency/citation checks and regression tests | Complete: bundar-narrative/0.1; no collector or scoring |
| 3b | BUNDAR CT/X Parser Experiment V1 | Immutable raw posts, deterministic extraction/identity/classification, propagation facts, bridge, labeled replay and usage accounting | Complete: ct-parser/v1; offline responses only |
| 3c | Real X Response Replay Validation V1 | Frozen bounded actual API sample, human labels, separate development/held-out evaluation, error analysis and Narrative integrity | In progress: capture/setup complete; human labels and metrics pending |
| 4 | Shadow collection | All observed candidates retained; gaps and exclusions visible; reliable historical reconstruction labeled separately | Planned |
| 5 | Individual signal research | Time-split tests, baselines and ablations; no arbitrary composite score | Planned |
| 6 | WATCH/HIGH convergence policy | Frozen evidence requirements, freshness, thresholds, exclusions and explanation format | Planned |
| 7 | Full prospective paper run | Frozen policy and execution assumptions; complete outcome tracking | Planned |
| 8 | Evaluate HIGH | Out-of-sample executable results, uncertainty, coverage and failure review | Planned |
| 9 | Iterate and repeat | New version; new prospective cohort; no rewriting earlier alerts | Planned |
| Later | Exit Intelligence research | Separate specification, datasets, model and evaluation after explicit human entry | Deferred |

24/7 operation is an eventual requirement, not a current capability. Before unattended operation, prove restart recovery, durable scheduling, rate-limit handling, clock checks, outage visibility, backup/restore and delivery deduplication. Do not confuse no opportunities with no data.

Step 2 should produce an evidence-backed audit and one proposed read-only collector slice. It must not sign up for paid plans. If access is unavailable, explicitly record it and use labeled fixtures/manual observations for contract development; do not pretend those are live coverage.

Next recommended milestone: **Real X Response Replay Validation V1**. Obtain a small permitted saved/exported official-response sample, record actual retrieval/detection/parsing times, independently label entity/relationship/classification and ambiguity cases, and evaluate held-out data with the local harness. Include unknown subjects, chain/ticker collisions, missing fields and false semantic associations; retain errors/exclusions. No live request is needed for the first validation pass.

Before a transport test, verify the account's actual entitlement, field access, billing and retention rules; obtain separately authorized no-cost or explicit request/post/unit budget. Then implement one bounded read-only lookup transport with fail-closed caps, environment credentials, response/rate-limit ledger, and no automatic retries/pagination. Stop on limit/error, preserve raw snapshots before parsing and label actual later receipt times. Do not upgrade plans or buy data. Durable storage/corrections/Supabase remain a separately scoped next foundation task. John's historical-data/research work remains separate. No HIGH policy changes are part of these parser milestones.

Progress: user confirmed credential configuration and explicitly authorized this milestone. One lookup + two 10-post searches succeeded; one local pre-HTTP permission failure was retained. Capture ceiling is exhausted. The 20 search posts are frozen, grouped and split into 15 development / 5 held-out. Human labels remain blank, parser rules unchanged, held-out predictions sealed. No more collection is needed or authorized by this capture manifest.

Immediate next step: independently label the saved raw-source review/template, run development evaluation, then explicitly release the unchanged frozen parser for held-out evaluation and preserve failures. This milestone remains incomplete until both real metric sets and error analysis exist. Evidence does not yet support moving to bounded prospective CT observation. After validation, propose a separately budgeted prospective pilot only if held-out performance/coverage justify it; otherwise append a development-only parser experiment and obtain a fresh held-out sample under separate authorization.
