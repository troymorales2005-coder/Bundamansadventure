# Build roadmap

| Step | Deliverable | Completion gate | Status |
|---|---|---|---|
| 1 | Research specification and separate repository | Traceable source, data contract, decisions, validation boundaries | Complete; v0.1 baseline |
| 2 | Data-source feasibility audit | Official access methods, permissions, timestamps, coverage, latency, cost, FOMO verification and fallbacks documented | Next |
| 3 | Ingestion and immutable storage | Versioned machine-readable schemas; fixture-based collector; deduplication, time and correction checks | In progress: immutable candidate + observation foundation implemented |
| 4 | Shadow collection | All observed candidates retained; gaps and exclusions visible; reliable historical reconstruction labeled separately | Planned |
| 5 | Individual signal research | Time-split tests, baselines and ablations; no arbitrary composite score | Planned |
| 6 | WATCH/HIGH convergence policy | Frozen evidence requirements, freshness, thresholds, exclusions and explanation format | Planned |
| 7 | Full prospective paper run | Frozen policy and execution assumptions; complete outcome tracking | Planned |
| 8 | Evaluate HIGH | Out-of-sample executable results, uncertainty, coverage and failure review | Planned |
| 9 | Iterate and repeat | New version; new prospective cohort; no rewriting earlier alerts | Planned |
| Later | Exit Intelligence research | Separate specification, datasets, model and evaluation after explicit human entry | Deferred |

24/7 operation is an eventual requirement, not a current capability. Before unattended operation, prove restart recovery, durable scheduling, rate-limit handling, clock checks, outage visibility, backup/restore and delivery deduplication. Do not confuse no opportunities with no data.

Step 2 should produce an evidence-backed audit and one proposed read-only collector slice. It must not sign up for paid plans. If access is unavailable, explicitly record it and use labeled fixtures/manual observations for contract development; do not pretend those are live coverage.
