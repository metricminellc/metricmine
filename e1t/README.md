# e1t/: the instruments of E1T, the consumer feedback loop a person starts

An experiments-lane branch (CLAUDE.md rule 19). The key is
`docs/experiments/e1t/KEY.md`; the finding lands under `docs/experiments/`
by its own pull request when the sitting ends. Nothing here binds.

## What is here

- `key.py`: the key's values as code (the served file, the fixtures, the
  second turn, the controls, the canary, the bounds, the thresholds).
- `capture_shim.py`: the transparent stdio capture between a host and the
  server; one capture file per server process (`MM_E1T_CAPTURE`).
- `capture_slice.py`: cuts one Desktop conversation out of the capture
  of Desktop's chat connection, the shim whose initialize names the
  client `claude-ai` (`begin`, `end`). Desktop 6.28899.6 opens a second
  connection for its local agent mode; its shim is watched, and a tool
  call in any other capture file since the mark stops the turn rule,
  the slice, and the re-run door.
- `desktop_switch.py`: points Claude Desktop's one server entry at the
  shim (`backup`, `set`, `check`, `restore`).
- `fetch_pinned.py`: the v1.3.0 asset by sha256 into `e1t/served/`.
- `driver.py`: the driven host, Claude Code in print mode from a fresh
  temporary directory outside any repository, one fresh conversation per
  fixture and repeat, with the ledger and the stops in code (`smoke`,
  `fixtures`, `controls`, `canary`, `status`). A conversation's cost is
  the sum of its calls' reported costs, an upper bound if the host
  reports a session's cumulative cost on a resumed call; both values are
  in meta.json. The host's own error (a call that ends `is_error` with
  the host's `<synthetic>` message last, or with no assistant message,
  never at the key's turn or dollar cap) stops the batch: before the
  model wrote anything (and at the smoke, which is never scored), the
  conversation is set aside under `host-errors/` with no ledger row and
  runs again later; after the model began to answer, it is kept as it
  ran and never re-run. A conversation with a ledger row is never run
  again. The canary, fixtures, and controls run only after a smoke that
  passed every check, `list_fact_categories` called.
- `transcript.py`: the scripted host, Claude Desktop (`ids`, `new`,
  `paste`, `turn`, `finish`, and `abandon`, the one re-run door, which
  under the key's host-error reason spends no re-run).
- `score.py`: the scores and the verdict by the key's rule, from the
  ledger alone, with `verify` run on the producer's build.
- `screen.py`: every file reaches the public branch through this.
- `ledger/<host>/`: one folder per conversation (prompt, the host's
  stream or the pasted reply, the capture, the tool's message, meta),
  `ledger.jsonl`, `scores/`, and `host-errors/` when the host's own
  error ended a conversation before the model wrote anything, or ended
  the smoke (kept, never scored). Committed at the sitting's evidence
  commit, after the screen.
- `tests/`: the instruments' tests, run as
  `uv run pytest e1t/tests -q` with the pinned file present.

Gitignored: `served/` (the asset), `local/` (the Desktop config backup,
the screen's names file, and `interrupted/`, a conversation interrupted
before its record was written), `capture/` (the live Desktop capture).

## The module the tool delegates to

`src/metricmine/feedback/`: `prepare` (the governed message, rendered by
code), `verify` (the producer's re-measurement, four outcomes), and the
command door, `python -m metricmine.feedback prepare|verify`, the same
code as the server's `prepare_feedback` tool.

## Running a sitting

Claude Code, from the branch's worktree with the pinned file placed:

    uv run python e1t/fetch_pinned.py --source demo/demo.duckdb
    uv run python e1t/driver.py smoke --model <alias>
    uv run python e1t/driver.py fixtures --model <alias>
    uv run python e1t/driver.py controls --model <alias>
    uv run python e1t/driver.py canary --model <alias>
    uv run python e1t/score.py --host claude-code --build warehouse/metricmine.duckdb

Claude Desktop, after `desktop_switch.py backup`, `set`, a full restart,
and `check`:

    uv run python e1t/transcript.py new cd-smoke --app-version <v> --model <m>
    (paste the clipboard into a new Desktop conversation and send; copy the reply)
    uv run python e1t/transcript.py paste cd-smoke
    uv run python e1t/transcript.py turn cd-smoke
    uv run python e1t/transcript.py finish cd-smoke --minutes <n>
    ... the same for each id `transcript.py ids` lists ...
    uv run python e1t/score.py --host claude-desktop --build warehouse/metricmine.duckdb

Before any commit of the ledger:

    uv run python e1t/screen.py e1t/ledger
