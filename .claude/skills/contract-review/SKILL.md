---
name: contract-review
description: Review an ODCS contract change or a proposer draft against the MetricMine contract rules before it lands. Use when reviewing a file under contracts/ or proposals/, a contract-only pull request, a version bump, or an amend proposal. Covers the all-or-nothing column rule, trusted constraints, the never-weaken rule and its relaxation gate, provenance, the properties-file obligations, and the separate-PR order.
argument-hint: [contract-path]
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff *)
  - Bash(uv run datacontract lint *)
---

# Contract review

Review the contract named by `$ARGUMENTS` (or the contract files in the
current diff when none is named). Read the committed version and the
proposed version side by side (`git diff main -- contracts/`). Every
item below is answered yes or no with the evidence (file and line). The
rules are CLAUDE.md hard rules 4, 5, 6, 9, 11, 16, and 17; the decisions
are D-08, D-22, D-30, and D-35; the findings are F-06, F-28, and F-29.

## Checklist

1. Shape (rule 4). Every column declares `name` and `data_type`. A
   contract is all-or-nothing; a partial column list fails.
2. Constraints (rule 5, F-06). Only `not_null` is trusted as an enforced
   constraint. Uniqueness and referential integrity are quality rules
   that render as generated tests, never trusted constraints.
3. Never weaken (rule 6, D-08, D-35). Classify every change as widening,
   neutral, or narrowing. A change that makes the contract enforce less
   (a dropped column or rule, a required flag removed, a type loosened)
   is a relaxation: it is refused unless `--allow-relaxation` was passed,
   the version is a major bump, and the rule-6 warning was printed. A
   relaxation offered to make a failing build pass is refused outright.
4. Version and order (rule 6, D-08, F-28, F-29). A contract change
   carries a version bump and lands in its own pull request; the model
   change follows in a second pull request. A required addition enters
   optional and tightens after the model lands. A bump to a governing
   contract (the gold star or the mapping contract) carries its
   compiled-context refresh in the same pull request (D-30).
5. Provenance (rule 16, D-22). `customProperties` carries proposedBy,
   proposerVersion, promptVersion, modelId, profileHash, proposedAt, and
   proposerStance; an amendment also carries amendsContract as
   `<id>@<version>#sha256:<hash>` over the committed contract's bytes.
   A hand-written contract carries proposedBy: human and no stance. A
   pattern-derived contract carries profileHash ABSENT plus a
   provenanceNote. Provenance is never stripped and never fabricated.
6. Mapping contracts (rule 9). `physicalType: mapping`; the category
   name never equals a dbt model name; no quality rules (gate 3 skips
   them, so they are dead letters).
7. Properties files (rule 11). The silver properties file is
   hand-authored; sync output is a proposal. Delete any accepted_values
   test that sync generated from a duplicateValues rule; keep uniqueness
   as a data_test. Engine-owned gold properties are generated code and
   are reviewed in regeneration pull requests.
8. Lint. `uv run datacontract lint <path>` passes for every changed
   contract.
9. The human flow (rule 17). The draft was copied from the outbox onto a
   branch by a person; nothing wrote into contracts/ directly; make demo
   stays keyless.

## Report

Print one table: item, result, evidence. Then one verdict line:
READY (every item yes), NEEDS CHANGES (list the failing items), or
REFUSE (a relaxation without its gate, or fabricated provenance).
