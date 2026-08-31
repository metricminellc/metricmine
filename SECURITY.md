# Security policy

MetricMine is a local-first reference implementation. It runs on one
machine, needs no account, and ships no hosted service. The surfaces that
matter for security are the read-only MCP server a desktop client spawns,
the code paths that open the local warehouse, and the repository's own
supply chain (pinned dependencies, GitHub Actions, and the committed demo
artifact).

## Supported versions

Security fixes land on `main` and in the next tagged release. Older tags are
not patched; move to the latest tag.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability.

Report it privately by email to github@metricmine.ai with the affected
file or command, the version or commit, the steps that reproduce it, and
the impact you observed. If GitHub's private vulnerability reporting is
enabled on the repository, the "Report a vulnerability" form under the
Security tab works too.

You will get an acknowledgement within seven days. A confirmed report is
fixed by a pull request that cites the report, and the fix is noted in the
changelog and, when it changes a gate or a boundary, in the decision
register.

## What counts

- A way to make the MCP server, the query module, or the demo export write
  to the warehouse, run more than one statement, or reach outside the
  configured database file (the serving layer is read-only three layers
  deep by design, D-31 to D-33).
- A way to make the pipeline read or write outside the repository working
  tree during a coding-agent session that the working-tree guard should
  have denied (D-37).
- A dependency or GitHub Action pin that ships a known vulnerability.
- A credential, token, or private path committed anywhere in the history.

## What does not count

- Findings that need the local warehouse file to be replaced with a
  crafted one; the file is the operator's own.
- Throughput, resource use, or data-volume limits. Those are documented
  measurements, not security boundaries.
- Behavior of the sample dataset itself, which is public and cited (D-15).
