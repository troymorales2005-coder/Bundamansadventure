# Architecture v0.1

This is a proposed architecture, not deployed software.

The offline Python observation foundation and BUNDAR narrative module described below are implemented; collectors, policy, delivery and services in the diagram remain proposed.

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

## Implemented BUNDAR narrative boundary

```text
Human/manual or synthetic timestamped evidence + cited research annotations
  → NarrativeResearchEngine.build
  → typed validation + occurrence/retrieval/detection/cutoff checks
  → contract-linked-narrative/v1 support rule
  → frozen NarrativeResearchPacket → canonical JSON / content-addressed ID
  → NarrativePacketStore.append → as_of(packet completion cutoff)
```

`narrative.py` is separate from the existing candidate layer. Frozen dataclasses, validated immutable tuples and immutable nested identities/provenance/Decimal measurements prevent ordinary nested mutation. This strengthens the new narrative boundary without changing the existing models, their historical semantics or separate research work. No automatic attachment to `CandidateObservation` is implemented.

The engine has no wall-clock access, random IDs, network or semantic model. Callers supply every timestamp, source observation, relevance explanation and hypothesis. Exact strings identify chain and contract; address normalization is deliberately not inferred across chains. Evidence is sorted by ID during construction; identical inputs including supplied timestamps, annotations and Decimal representation produce identical JSON and SHA-256 IDs. Annotation order is preserved and therefore part of the packet identity.

The builder and direct packet constructor enforce the same validation. Occurrence <= retrieval <= detection <= observation cutoff <= completion. A late source receipt/detection is rejected even if the packet is completed later. Measurements must be available by evidence detection. Evidence can describe a prior measurement window. Packet-store `as_of` exposes only completed packets, including when append order differs from timestamp order; evidence availability and packet availability are separate concepts.

The store returns a tuple and offers only append, rejecting duplicate packet IDs. An update or correction creates a new packet with new evidence/annotations or completion time while preserving the original. It is in-memory only, with no transaction, persistence, correction-link workflow, access control or tamper-proof guarantee. Python frozen objects are an application convention, not protection against deliberate bypass. Durable storage, source idempotency and correction links remain later work.

Support is an auditable minimum-lineage rule, not scoring: a hypothesis must cite identity, exact-contract capture and narrative evidence with the same subject identifier. Ticker-only mentions and competing-contract posts cannot supply support. No inferred semantic matching, source truth verification, account independence, numeric confidence or category selection occurs. All supplied evidence, risks and unsupported hypotheses remain in the packet. Raw engagement and propagation measurements retain their scope/window; they are not automatically interpreted as confirmation.

## Implemented CT/X Parser Experiment V1

```text
Saved official X v2 response / labeled local fixture
  → OfficialXResponseAdapter.normalize (no HTTP transport)
  → frozen RawXPost + RawXStore (append-only snapshots)
  → CTParser + point-in-time CTRegistry
  → ParsedCTPost (raw facts, entities, cited/versioned interpretations)
  → measure_propagation (scoped facts + separately cited noise interpretation)
  → narrative_bridge (CT observations + explicit exclusion records)
  → existing NarrativeResearchEngine (unchanged)
```

- `ct_models.py`: frozen nested post/reference/public-metric/entity/interpretation models, canonical content IDs and temporary append-only raw storage. Full response/account expansion JSON strings preserve unknown API fields without mutable payload aliases.
- `ct_parser.py`: immutable alias registry with availability timestamp/version; literal extraction; conservative target relationships; descriptive rules; scoped receipt-window propagation and latency measurements; bridge into the existing narrative layer.
- `x_adapter.py`: official-response normalization and credential-presence configuration only, plus an append-only caller-reported API usage ledger. There is no transport or request loop; local normalization does not count as a request.
- `ct_replay.py`: CLI evaluation against manually labeled JSON fixtures; parser identity/classification conformance is separate from any financial evaluation.

All raw timestamps are aware UTC; known posting <= retrieval <= detection <= parsing. CT interpretation requires parsing and registry availability by cutoff; derived snapshots preserve their own cutoff/config/evidence. A future raw post, detection, parse, dictionary or catalyst is rejected. Expanded referenced-post bodies are retained in raw payloads but not recursively interpreted, avoiding implied access to missing/future reference content.

Raw stores expose snapshots by detection time; parsed availability remains independently validated. Propagation chooses the latest available observation per post in the receipt window and rejects conflicting same-time snapshots/mixed registries. It counts observed posts, not all X discussion. Public API engagement remains per-post snapshot data and is never conflated with observed repost/quote/reply counts. Source account metadata remains raw; no source-quality model exists.

The bridge never generates identity-match, token capture, a narrative hypothesis or HIGH output. Missing account/occurrence fields are preserved in CT raw/parsed records and reported as exclusions from the stricter Narrative schema. Source/registry/version references accompany derived relevance; multi-subject observations have distinct evidence IDs. The existing Narrative module and legacy candidate models are untouched.

Storage is in-memory and restart-volatile; JSON fixtures/report are static experiment artifacts. Durable storage/Supabase, source correction links, compliance deletion/retention enforcement and recovery remain future infrastructure. No credentials, HTTP headers or request configuration are retained as post payloads; callers supply response objects only.

Official-response field assumptions were checked on 2026-10-01 against [X post lookup](https://docs.x.com/x-api/posts/lookup/quickstart) and [X rate-limit documentation](https://docs.x.com/x-api/fundamentals/rate-limits). Account-specific access/costs were not checked; no API request was made.

## Real-response replay workflow (capture complete; labeling pending)

The above describes the completed offline CT experiment. The later real replay adds a separate `x_bounded_capture.py` transport and `x_real_replay.py` validation workflow, without modifying `x_adapter.py`, CT parser rules or Narrative models.

Transport uses only explicit GETs to fixed `api.x.com` lookup/recent-search paths. Local credential loading reads only `X_BEARER_TOKEN` from process environment or gitignored `.env`, with no shell evaluation/interpolation. Token values are never configuration fields or log output. Redirection is disabled. Persisted reservations precede network operations and consume budget even on local errors; interrupted/failed attempts stop subsequent collection. An explicit reviewed local pre-HTTP permission failure was preserved and reopened once after independent socket diagnostics. HTTP errors cannot be reopened by this review mechanism. No retry/pagination loop exists.

Each response is frozen to exclusive-create bytes before parsing, hashed and accompanied by a timestamped envelope/usage event. Only rate-limit headers are retained; token echoes are redacted and recorded. Files are fsynced; raw response retention is local and gitignored, not a durable database/security boundary. Restart does not reset reservations or limits. Collection requires separate deliberate invocation and is now exhausted.

Replay preparation verifies raw byte hashes, excludes the verification/control lookup, retains first receipt per research post and freezes an author/reference/exact-text-grouped split. Parser/registry/plan/source hashes prevent silent drift. Ground-truth files start blank with source lineage and cannot silently import predictions. Human labels are an external dependency. Metrics stay null while pending; held-out prediction/evaluation is sealed until explicit final release. Every field can be reviewed as UNKNOWN without pretending it is a correct positive/negative.

Retrospective replay source boundary = original API receipt. Computation boundary = actual subsequent normalization/parse time. The wrapper rejects dictionaries not known at source receipt and reads only the frozen response; it never loads later metrics/profiles/referenced bodies. The existing parser's `observed_at` remains its actual computational cutoff, while the wrapper retains `source_cutoff_at` separately. Original packet completion is not backdated. Narrative bridge provenance/source occurrence/Radar detection survive; actual later completion is visible.

The evaluation workflow emits separate development/held-out field accuracies, exact-match rate, micro set precision/recall/FP/FN for identities and subjects, ambiguity/UNKNOWN/structural-lineage counts, parsing errors, coverage and per-post mismatches/error categories. Unknown human judgments abstain from scored fields. It never reads price/outcome data. Error categories inferred from mismatched fields are provisional mechanical categories, not verified semantic causes; human notes can preserve context.

The actual access check and two search requests succeeded. Billing/credit quantities were not exposed in response metadata; rate counters are not billing counters. No further requests will run. Human labels and final held-out evaluation remain required before this milestone or prospective-parser readiness can be claimed.
