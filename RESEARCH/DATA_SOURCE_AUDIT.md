# Step 2: data-source feasibility audit

Status: not performed. Entries below are questions and required evidence, not assertions of current APIs, free access, or vendor support. Consult official documentation at audit time and retain dated links/evidence. Do not purchase, subscribe, or accept financial commitments.

| Source family | Needed capability | Questions to resolve |
|---|---|---|
| FOMO | Exact token/network availability, executable routes, theses/activity | Authoritative eligibility method? Region/account constraints? Read-only API/export? Quote freshness? Retention rights? |
| Axiom | Stage, market, filters, viewer count | Documented permitted access? Fee metric unit/window? Viewer history and timestamps? Coverage? |
| J7 / X | Catalyst posts and latency | Legitimate API/webhook/export? Original and receipt timestamps? Account coverage? Access/redistribution rights? |
| Chain/DEX data | Contracts, trades, holders, depth and wallet history | Networks, finality, reorgs, backfill, rate limits, quote simulation and transfer accounting? |
| Wallet analytics | Historical qualification and clusters | Complete losses/transfers? Independent history verification? Method transparency? |
| Project evidence | Public demos, developer reputation, launchpad identity | What can be safely verified without wallet connections? Timestamped mutual/account history? |

For every candidate provider record: official source URL and checked date; authentication; permission/terms; available fields; historical depth; source/receipt timestamps; measured latency; rate limits; retention rules; price/free-tier limitations; fallback; blocker; recommendation. Unknown is a valid result.

Deliverables: completed matrix, prioritized minimal read-only provider set, FOMO gate evidence standard, freshness budgets, operating-cost estimate without commitment, and a scoped first collector proposal.

Next implementation after feasibility: versioned schemas plus a fixture-driven append-only observation pipeline and eligibility gate. Demonstrate raw evidence → normalized coin → frozen decision → scheduled outcome record before adding scoring. If live access is blocked, fixtures may prove mechanics but cannot validate a signal.
