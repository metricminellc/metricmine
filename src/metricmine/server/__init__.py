"""The MetricMine MCP server (docs/spec/serving.md §7).

Exports the configured `server` so consumers import it from the package
rather than reaching into the module that happens to build it.
"""

from metricmine.server.app import server

__all__ = ["server"]
