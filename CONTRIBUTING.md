# Contributing to MetricMine

Thank you for looking under the hood. MetricMine is a contract-driven
medallion pipeline built as a reference implementation. Its governing idea
also governs contributions: agents propose, humans approve, deterministic
code executes, and every change lands through a reviewed pull request that
the contract gates judge the same way whether a person or an agent wrote it.

## Before you start

Read three things, in this order:

1. [CLAUDE.md](CLAUDE.md), the hard rules every contributor and every coding
   agent works under. The rules cite decisions by ID.
2. [docs/decisions/decision-register.md](docs/decisions/decision-register.md),
   the binding decisions. A change that touches a pin, a gate, or an
   architecture boundary amends the register in its own documentation pull
   request before the implementing change lands.
3. The spec for the layer you are touching, under [docs/spec/](docs/spec/).
   Specs merge before their implementation pull requests open.

If a rule, a spec, and the code disagree, say so in an issue before you
write code. The disagreement is the finding.

## Set up

MetricMine runs locally on macOS or Linux with Python 3.12 and
[uv](https://docs.astral.sh/uv/). No API key is needed for the demo, the
tests, or CI.

```bash
git clone https://github.com/metricminellc/metricmine.git && cd metricmine
uv sync
uv run ruff check .
uv run pytest -m "not local" -q
make demo
```

`make demo` lands the committed sample into bronze, builds silver and the
gold star from the committed contracts, and rebuilds the demo export.
Restore `demo/demo.duckdb` with `git checkout` afterwards; the committed
export changes only when a release refreshes it (D-33). The contract gates
run locally with the isolated tool the CI workflow installs:
`uv tool install 'datacontract-cli[duckdb]==1.0.12'`.
[docs/demo.md](docs/demo.md) walks through the serving path.

## The rules that gate every change

- **Contracts are never weakened to pass.** A narrowing change is refused
  without an explicit flag, a major version bump, and a printed warning
  (D-08). A required addition enters optional and tightens once the model
  lands.
- **A contract change is its own pull request** with a version bump; the
  transform change that follows it is a separate pull request. The gates are
  symmetric: what fails in CI fails the same way locally.
- **Engine-emitted files are never hand-edited.** Everything under
  `transform/models/gold/` is written by the engine under an ownership
  manifest; a hand edit is refused at the next regeneration (rule 8, D-09).
  Change the mapping contract and regenerate; the regeneration is a pull
  request.
- **Silver is hand-written on purpose** and enforced by its contract at
  build time. What an agent proposes for silver is the contract, not the
  SQL.
- **Exactly two pipeline agents exist** (D-10). New behavior is a stance of
  one of them or deterministic code, never a third agent.
- **CI is the gate of record.** Local hooks and skills are conveniences that
  only deny or ask; nothing migrates out of CI.
- **Nothing prints a credential.** The demo, the tests, and CI stay keyless.

## Commits and pull requests

- Subjects follow Conventional Commits (`docs(spec): ...`, `fix(engine): ...`).
- Every commit body says why, and cites the governing decision when one
  applies (D-14). One commit per file is the default; small, directly
  connected changes may share one.
- Pull request descriptions carry three sections: Summary, What changed,
  Why. The pull request title and description become the permanent commit
  on `main` (squash merge, branch deleted).
- Keep pull requests small and reviewable. A pull request that changes a
  contract and its transform, or the engine and its fixtures, gets split.
- Breakage never merges. A red check is a stop, not a negotiation.

## Sign-off

Every commit carries a `Signed-off-by` line certifying the
[Developer Certificate of Origin 1.1](https://developercertificate.org/):
that you wrote the change or have the right to submit it under the
project's license. `git commit -s` adds the line from your Git identity.
The DCO check enforces it on every pull request: a commit without a
well-formed sign-off does not merge. Commits authored by the repository's
own automation are exempt; the workflow file carries the list.

## Provenance

The repository was built fresh from an independent written specification,
and [NOTICE](NOTICE) carries that statement. Do not contribute code copied
from another MetricMine implementation, from a proprietary system, or from
any source whose license is incompatible with Apache-2.0. Sample data must
be public and cited; the committed sample is Online Retail II from the UCI
Machine Learning Repository under CC BY 4.0 (D-15).

## Working with the coding agents

Claude Code is a first-class contributor here, and the repository is set up
for it:

- `CLAUDE.md` is the agent's instruction file. If you use Claude Code, the
  workspace trust dialog lists a project hook, the working-tree guard, that
  denies reads and writes outside the repository (D-37). It is deterministic
  code, not a model, and you can read it under `.claude/hooks/`.
- `/contract-review` is a project Skill that checks a contract change
  against the review conventions and reports READY, NEEDS CHANGES, or
  REFUSE. Run it before opening a contract pull request.
- Oscar is the repository's resident guide, a read-only subagent under
  `.claude/agents/`. Ask Claude Code for Oscar and ask how the system
  works, where a task is done, what a rule means, how to keep silver
  clean, or how the proposers draft contracts; it answers from the
  repository's own files and cites the file and line. Ask it to review a
  contract, a draft, or a contract-only pull request and it runs the
  same checklist as `/contract-review`, prints the table and the verdict,
  and never edits.
- The repository's GitHub Action prepares pull requests for backlog issues
  when a maintainer asks it to in a comment. It never opens, approves, or
  merges a pull request; a person does. Contributors do not need it and
  cannot trigger it.

## Issues

Open an issue for a defect, a documentation gap, or a proposal. State what
you observed, what you expected, and the command that shows the difference.
A finding with a measurement is worth more than a feature request.

## Security and conduct

Report a vulnerability through [SECURITY.md](SECURITY.md), never in a public
issue. Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
