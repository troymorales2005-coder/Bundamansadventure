# Architecture v0.1

This is a proposed architecture, not deployed software.

```text
Permitted read-only sources
  → adapters → append-only raw evidence → normalized observations
  → point-in-time features → FOMO + freshness + quality gates
  → versioned Discovery policy → frozen WATCH/HIGH alert → human review

Frozen alert → independent outcome scheduler → paper results → evaluation

Explicit human entry event → [later: isolated Exit Intelligence]
```

## Responsibilities

- Adapters capture original timestamps, receipt time, source identity, raw payload hash and access/coverage limitations. Reconnect with checkpoints and idempotency keys.
- Evidence storage preserves original payloads where retention is permitted, otherwise permitted excerpts/metadata plus retrieval reference and retention limitation. A hash alone cannot reproduce unavailable evidence.
- Normalization keys coins by chain and contract, never ticker alone; records pools and lifecycle changes without overwriting prior observations.
- Feature computation reads only evidence received by the decision cutoff. Definitions, model versions and lookback windows are recorded.
- FOMO verification establishes supported network, exact token and current executable route/availability. Missing or expired evidence stops actionable classification.
- Discovery evaluates narrative/X, wallets, market/liquidity, attention, structure/safety, project credibility and stage context. Families may be correlated; separate names do not imply independence.
- Alert persistence precedes delivery. Retries use one alert ID. Reclassification creates a new event linked to its predecessor. Initial experiments are labeled shadow and are not validated HIGH alerts.
- Outcome collection has read access to frozen alerts and writes to a separate results namespace. Discovery production features cannot read future outcomes. Offline training uses only temporally separated, versioned cohorts.
- Operations report ingestion lag, stale sources, excluded-candidate counts, missed outcome jobs and delivery failure separately from opportunity alerts.

## Logical stores for the current milestone

The current implementation adds the foundational Python data layer for `coin_observations` and related evidence objects, with explicit support for immutable append-only history and as-of reconstruction. The logical store set remains `raw_evidence`, `coin_observations`, `wallet_qualifications`, `feature_snapshots`, `eligibility_checks`, `discovery_decisions`, `alerts`, `outcomes`, `experiment_registry`, `service_health`.

Current runtime model responsibilities:

- `CandidateObservation` stores chain + contract identity, timestamps, provenance, narrative analysis and all evidence families required for Discovery Radar.
- `ObservationStore` preserves append-only history by snapshotting each accepted observation at its observed timestamp and allowing historical reconstruction by cutoff time.
- `FomoExecutability` is an explicit enum with `TRUE`, `FALSE`, and `UNVERIFIED` so evidence status is not silently converted into a binary claim.
- Outcome tracking remains separate from discovery scoring and cannot retroactively alter earlier alert evidence.

Use append-only application permissions, explicit correction records, content hashes, durable backups and replayable manifests. Hashes detect changes but are not sufficient tamper protection on their own. Treat chain reorganizations as additional invalidation/correction events.

## Exit boundary

Reserve a future entry event containing `entry_id`, `coin_id`, human-reported time/price/market_cap, provenance and optional related alert. It is not an order. Exit Intelligence has its own storage, features, model versions and evaluation; it cannot mutate Discovery records or feed target ranges back into Discovery scoring. No Exit engine is implemented in V1.

## Operational boundary

No private keys, wallet signing, order submission or exchange trading permissions. Credentials, if later needed for approved read-only access, stay out of Git and logs. Paid hosting and data are not provisioned. External text is untrusted data and cannot issue tool or trading instructions.
