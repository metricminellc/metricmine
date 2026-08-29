Phase 8 prep probes, August 28, 2026: the head reproduction at e996672, the working-tree guard measured on stdin and end to end inside Claude Code, the Skill and settings registration, and the CI lane with the new files
Repo head: e996672ce36b73a9739345f93429764118bfd07e (main, the #105 squash)

Environment (the Architect's sandbox, stated because every number below is a measurement, never a claim):
Linux x86_64 container; uv 0.8.17; CPython 3.12 (uv-managed) for the project venv; the system python3 is CPython 3.11.15 and the guard was also run under CPython 3.9.23 (uv-managed) for compatibility; Claude Code 2.1.251 installed from npm; datacontract-cli 1.0.12 as an isolated uv tool with the [duckdb] extra; dbt_utils 1.3.3 vendored by git clone of its tag (hub.getdbt.com is unreachable from this sandbox; the Mac and CI use dbt deps); AIRBYTE_OFFLINE_MODE=1 for every ingest; no API key present and none needed. The one end-to-end Claude Code run in section 3 used the sandbox session's own Claude Code login, never a repository secret; nothing printed a credential. Absolute sandbox paths are written as <sandbox> (the clone) and <home> (the sandbox home directory). Byte sizes and wall times are per-machine reports; the D-33 digest is the gate.

== 0. Head reproduction at e996672 (every lane at its recorded value) ==
$ uv sync --frozen                       -> 0m12.773s wall; dbt-core 1.12.3, dbt-duckdb 1.11.0, dbt-adapters 1.24.5, dbt-core-experimental-parser 2.0.0b2 (the sdist built by fetching its wheel from GitHub releases), metricflow 0.212.0, duckdb 1.4.3, airbyte 0.53.2, anthropic 1.0.0, mcp 1.29.0, ruff 0.15.21, pytest 9.1.1; the venv 864M
$ uv tool install --python 3.12 "datacontract-cli[duckdb]==1.0.12" -> 0m5.260s wall; datacontract --version 1.0.12
$ uv run ruff check .                    -> All checks passed!
$ uv run pytest -m "not local" -q        -> 411 passed, 52 deselected, 13 warnings in 26.75s
$ uv run pytest tests/agents -q          -> 240 passed in 13.99s
$ AIRBYTE_OFFLINE_MODE=1 make ingest     -> landed {'online_retail_ii': 45228} into bronze of warehouse/metricmine.duckdb (0m26.285s wall)
$ uv run dbt build --project-dir transform --profiles-dir transform --target local
                                         -> Running with dbt=1.12.3; Registered adapter: duckdb=1.11.0; Found 13 models, 96 data tests, 1 source, 617 macros
                                         -> Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=109 (0m12.872s wall)
$ uv run pytest tests/agents -m local -q -> 8 passed, 232 deselected in 8.75s
$ uv run pytest tests/test_adoption_scan.py -q -> 11 passed in 2.21s
$ make scan (twice)                      -> models scanned: 13; skip_engine_owned 12; in_sync 1; The queue: Empty. Every model is in sync or skipped by decision.
                                         -> plan_hash sha256:0f8e153083b6fdd743e8eff17e842bac58260be6a3aa2e57402c74218e20bf1c on both runs (per-machine; it embeds the repo head line)
$ make export-demo                       -> view vw_invoice_lines_typed: 44721 rows, digest match (08eca7be30707e2aa0b48c3d19ddeea4); artifact size: 12333056 bytes; demo/demo.duckdb restored with git checkout; tree clean.

== 1. The working-tree guard on stdin (the script exactly as Claude Code runs it: JSON in, a decision out, exit 0) ==
Each case is one line of JSON piped to `python3 .claude/hooks/working_tree_guard.py` with CLAUDE_PROJECT_DIR=<sandbox> and cwd <sandbox>.
Bash  find ~ -name libduckdb.dylib      -> {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "working-tree guard: Bash names <home>, which resolves outside the project root <sandbox>. CLAUDE.md Conventions: never read or write paths outside the repository working tree. Stage the input inside the repository, or use a path under it, and retry."}}
Bash  uv run pytest -m "not local" -q   -> (no output: no decision, the normal permission flow applies)
Bash  ls /opt/homebrew/Cellar/duckdb    -> (no output: a system toolchain path)
Bash  echo x > /tmp/scratch.txt         -> deny; the reason names /tmp/scratch.txt
Read  <home>/elsewhere/secret.txt       -> deny; the reason names the path
Edit  <home>/elsewhere/secret.txt       -> deny
Write <home>/elsewhere/secret.txt       -> deny
Read  README.md                         -> (no output)
malformed stdin ({not json)             -> {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "working-tree guard could not evaluate this call (Expecting property name enclosed in double quotes: line 1 column 2 (char 1)); confirm it by hand."}}
CLAUDE_PROJECT_DIR unset               -> ask; the reason names CLAUDE_PROJECT_DIR
Under CPython 3.9.23 the home-directory case returns the same deny line (the guard is standard-library only, Python 3.9 and later).

== 2. The test module and the lanes with the new files staged ==
$ uv run pytest tests/hooks -q           -> 40 passed in 1.51s (subprocess runs of the script: the Deviation 4 class, parent climbs, /tmp, quoted paths, unbalanced quotes, the six file tools outside and inside the root, a symlink out of the tree, an unrelated tool, malformed input, a missing root, the settings wiring, the shebang and executable bit)
$ uv run ruff check .                    -> All checks passed! (ruff --show-files lists .claude/hooks/working_tree_guard.py and tests/hooks/test_working_tree_guard.py, so the guard is linted)
$ uv run pytest -m "not local" -q        -> 451 passed, 52 deselected, 13 warnings in 20.77s (411 at head plus the 40 guard tests)
$ touch .claude/settings.local.json && git check-ignore -v .claude/settings.local.json -> not ignored at head (the *.local pattern does not match a .json name); the hook PR adds the path to .gitignore.
$ python3 -c "import json; json.load(open('.claude/settings.json'))" -> parses

== 3. End to end inside Claude Code 2.1.251 (non-interactive, the project settings read from <sandbox>/.claude/settings.json) ==
$ claude -p "Run exactly this shell command with the Bash tool and report what happened in one sentence: find ~ -maxdepth 1 -name '*.txt'" --max-turns 3 --debug
Model reply: The command was blocked by the working-tree guard: it references `~` (`<home>`), which resolves outside the repository root `<sandbox>`, and CLAUDE.md's Conventions section prohibits reading or writing paths outside the repo working tree.
Debug log (~/.claude/debug/<session>.txt):
  Watching for changes in setting files <home>/.claude/settings.json, <sandbox>/.claude/settings.json, <sandbox>/.claude/settings.local.json, /etc/claude-code/managed-settings.json...
  Hooks: Parsed initial response: {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"working-tree guard: Bash names <home>, which resolves outside the project root <sandbox>. ..."}}
  Hook PreToolUse (working-tree guard) returned permissionDecision: deny (reason: working-tree guard: Bash names <home>, ...)
  Hook result has permissionBehavior=deny
A preceding run with an in-tree command ("List the files in the repository root.") logged "Hook output does not start with {, treating as plain text" and the Bash call dispatched normally (tool_dispatch_end outcome=ok): the guard printed nothing and the call proceeded.

== 4. Skill and settings registration without a model call ==
$ claude -p "ok" --model claude-does-not-exist-5 --max-turns 1 --debug -> the run fails at the model name (cost $0.0000) after loading configuration; the debug log reads:
  Loading skills from: managed=/etc/claude-code/.claude/skills, user=<home>/.claude/skills, project=[<sandbox>/.claude/skills]
  Loaded 9 unique skills (8 unconditional, 1 conditional, managed: 0, user: 1, project: 1, additional: 0, legacy commands: 0)
The one conditional skill is contract-review (its frontmatter carries paths:, so it activates on matching files). The SKILL.md frontmatter fields (name, description, argument-hint, paths, allowed-tools) are all documented fields; the description is 410 characters against the 1,536-character listing cap.

== 5. Facts about the surface, verified in the Claude Code documentation on August 28, 2026 ==
Built-in read-only Bash commands (ls, cat, echo, pwd, head, tail, grep, find, wc, which, diff, stat, du, cd, read-only git) run without a permission prompt in every mode and the set is not configurable; this is the class of call in Deviation 4. A PreToolUse hook runs before the permission prompt for every tool call except EndConversation; a JSON deny blocks the call; exit code 2 also blocks; other non-zero exits do not block. Project hooks in .claude/settings.json are used in a clone once the folder is trusted (the trust dialog lists hooks and helper commands) and in `claude -p` runs; `--settings '{"disableAllHooks": true}'` or `--bare` opts a run out. ${CLAUDE_PROJECT_DIR} is the project root where the session started, worktrees included.
