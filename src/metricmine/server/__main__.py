"""Entry point: `python -m metricmine.server` serves gold over stdio.

Spec: docs/spec/serving.md §7. No arguments and no configuration switches —
the served database is resolved by the query module from MM_SERVE_DB, then
the committed demo artifact (§5), so a desktop client configures this
server entirely through its environment.
"""

from __future__ import annotations

from metricmine.server.app import server


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
