# Development roadmap

Reconciled with the user-supplied revised roadmap on November 27, 2026. Completed work is retained in STATUS.md and ISSUES.md; issue identifiers from Claude's review remain unchanged. Work continues through actionable issues without routine approval prompts.

| Priority | Workstream / issue IDs | Acceptance criteria | Current position |
|---|---|---|---|
| 1 | Security and baseline — S1–S4, C6, H2, H5, O9 | Protected local actions; declared dependencies; backup and demonstrated restore; transactional migration ledger; automated regression checks; identifiable installed build | Request protection and CI delivered. Recovery drill and migration tests now pass. Remaining legacy-writer/security audit is open. |
| 2 | Automatic intake — O1–O8 | Manual and scheduled runs choose working dependencies; queues survive interruptions; failures remain visible; retries bounded; changed Pages safely extracted; coverage is measured | Fixed manual Python selection; isolated dependencies; per-source budgets; actual local lane passed with one source explicitly pending. Unattended Pages and complete acquisition recovery remain open. |
| 3 | Scripture infrastructure — B1–B6 | One parser; canonical verse IDs; verified abbreviations, lists, cross-chapter ranges, multi-word names and verse bounds; all consumers migrated | Common reference normalization delivered. Numeric identities, full range/list support and complete consolidation remain open. |
| 4 | LFBI ingestion — L1–L6 | Entire Acts course verified from authenticated lesson pages through resources, transcripts, indexed text and reader; real-file duplicate checks; routine updater integration | LFBI downloads already run in normal/local updates. Full Acts completeness is not yet proven. |
| 5 | Transcription quality — T1–T8 | Compare larger models against corrected real-sermon samples; vocabulary hints; model/timestamp/confidence metadata; preserve original/corrected versions; selective reprocessing | Original base model remains unchanged until measured comparison. |
| 6 | Search/reading — R1–R12 | Repeatable relevance/performance benchmark; filters, metadata, matching highlights, readable previews and playback at timestamp | Existing preferred/excluded management and reader retained; continue performance and metadata work. |
| 7 | Private phone access — P1–P5 | Evaluate Tailscale first; authenticated iPhone reading/search separated from Mac ingestion; no public exposure; retain future offline possibilities | Tailscale is an option to evaluate, not installed or activated. Mac-dependent access is an initial option, not equivalent to future independent access. |
| 8 | Bible-first interface — F1–F6, F8 | Licensed KJV text, Strong's, TSK, Nave's and Webster's; e-Sword-style workflow linked to personal materials | Pending data/rights and schema work. |
| 9 | External Christian library — F7, H6 | Permitted acquisition with provenance and duplicate checks; no doctrinal author classifications | Existing discovery/intake retained; permission review before sharing remains mandatory. |
| 10 | Additional devices — P6 | Separate reMarkable feasibility test; distinguish interactive access from export | Exploratory; no hardware recommendation yet. |

Across every priority: preserve original materials and existing functionality. Maintain integrity checks, a documented full-index rebuild procedure, consistent provenance, installed build detection and integrated library status. Distinguish code implementation, synthetic automated tests and verification against real data.

## Prior roadmap provenance
The earlier provisional roadmap was based on HANDOFF.md and Claude's review. The missing revised roadmap has now been supplied and incorporated; no handoff document is outstanding. Prior completed work remains recorded rather than reset.
