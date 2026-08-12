# The signature test: a new dimension by amendment alone

Phase 4 exit evidence, Sitting K (August 11-12, 2026). The unified event star's
signature property (D-17, [engine spec §1](../spec/engine.md)): a new
dimension added to the mapping contract flows through regeneration and
`dbt build` with **no engine code change, no physical schema change, and
no gold contract amendment** — announced by a new schema key in the
columns dimension and a registry row. This document records the live
demonstration; every number below was first measured at the pre-K
rehearsal ([F-21](gate_proof_findings.md#f-21)) and then reproduced live.

## The sequence

1. **The amendment (PR #70).** `country` — deliberately reserved
   out of mapping v1.0.0 at Sitting H exactly for this test — joins as a
   ninth mapped field, `mappingRole: dimension`. The contract bumps to
   v1.1.0. Per the recorded D-08 reading, the PR carries the bump, the
   freshly minted compiled-context artifact `v0002`, and the refreshed
   23-file byte oracle, and nothing else.
2. **The staleness guard, fired live.** Between the bump and the mint,
   `make regen` refuses, fail-closed, nothing written:

   ```
   ERROR: compiled-context artifact v0001 is stale: sources.mapping_contract is 1.0.0, contracts say 1.1.0; run `make context` (D-30)
   ```

   `make context` then mints `v0002` (byte-identical across two
   machines:
   `sha256 5fa60c0c28376130c68b268fa694836bf46fdb5a107a4c8e52291d00512d0337`).
3. **The regeneration (PR #71).** `make regen` lands 23 files,
   +58/−55, and a second run is a no-op. The engine version does not
   move: v0.2.0 before, v0.2.0 after. The gold contract does not move:
   v1.2.0 before, v1.2.0 after. No table gains or loses a column.
4. **The announcement.** The dimensions manifest key moves
   (`0f6d343a…` to `2d27bd36…`); the measures, source, run, and
   timeframe keys stay put; all five `context_registry` rows re-cite
   mapping `1.1.0`; C3 covers the new key by construction.

## The numbers

Conservation is unchanged to the digit — the star's shape did not move:
`44721 | 44721 | 44721 | 2004 | 1 | 1 | 2 | 5 | 44721` (silver, fact,
dim lines, timeframe, source, run, manifests, registry, typed view). The
typed projection reconciles TEN fields (the nine mapped fields plus the
derived `line_identity` join key) — country now among them — at
44,721 for 44,721 against silver
([evidence](evidence/2026-08-10_prek_typed_reconciliation_ten_fields.log)).

## The refusal twin (rule 8, D-09)

The same machinery that regenerates freely also refuses correctly. With
one engine-owned file hand-edited, the engine names it and writes nothing:

```
ERROR: refusing to overwrite human-owned files whose bytes diverged from the ownership-manifest baseline (rule 8):
  transform/models/gold/dim_source_values.sql
Nothing written.
```

Captured live on the break-demo branch (closed unmerged by design):
[screenshot](evidence/2026-08-12_prek_drift_refusal_live.png), demo PR #72.

## Why this matters

A star that absorbs a new dimension through a reviewed contract amendment
and a deterministic regeneration — with its lineage re-cited and its
conservation intact — is the legibility argument made executable. The
next source, the next column, the next category are contract events, not
engineering projects.
