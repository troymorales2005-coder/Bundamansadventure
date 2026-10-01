# Decision register

Accepted product requirements originate from the user's request and established research conversation. Engineering conventions below are a v0.1 design baseline, not empirically validated trading rules.

| ID | Decision | Reason |
|---|---|---|
| D01 | Independent repository and VS Code workspace | Keep all HVAC work separate |
| D02 | Discovery → alert → human decision → deferred Exit Intelligence | Keep selection separate from managing a chosen position |
| D03 | FOMO-only actionable universe | Supported chain alone does not establish token tradability |
| D04 | WATCH/HIGH; quality determines frequency | Zero or multiple independent HIGHs allowed; no quota |
| D05 | HIGH is evidence priority only | No buying instruction or position sizing |
| D06 | Immutable prospective evidence and alert snapshots | Prevent hindsight and silent corrections |
| D07 | Paper/shadow validation first | No established signal edge yet |
| D08 | Observe all candidates, exclusions and failures | Reduce survivorship and selection bias |
| D09 | Trader rules are hypotheses | Anecdotes, reported P&L and filters are not validation |
| D10 | Separate Exit data, scoring and evaluation | Comparable-coin exit targets must not enter Discovery features |
| D11 | No purchases, subscriptions or execution | Current authorization is research and foundation only |
| D12 | Eventual 24/7 operation with health reporting | Silence must be distinguishable from an outage |
| D13 | Unknown/stale FOMO verification blocks actionable alerts | Fail closed; preserve internal research observations |
| D14 | No initial score weights or HIGH thresholds | Learn incremental usefulness before combining signals |
| D15 | Immutable candidate observation records | Preserve historical evidence and prevent future information from leaking into earlier decisions |
| D16 | Explicit `NO_NARRATIVE_FOUND` and `UNVERIFIED` states | Fail closed on missing evidence instead of inventing narrative or executability |

Current-market narrative similarity using only pre-decision evidence is permitted Discovery research. Historical comparable-coin target ranges, de-risking zones and exit recommendations belong exclusively to deferred Exit Intelligence.

Unresolved: current FOMO supported chains and authoritative eligibility evidence; providers and permitted access; freshness/latency budgets; runtime/storage/hosting; observation cadence; simulation notionals and fees; wallet qualification and cluster method; model thresholds; validation sample size and success criteria; alert destination. Resolve and version these before the dependent implementation or experiment. No current vendor capability is assumed from the transcript.
