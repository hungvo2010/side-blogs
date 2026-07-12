# Shell scripts: commands only, no comments or chatter

**Rule:** Shell scripts (`.sh`) in this project must contain only the core commands needed to get the job done. No `#` comments, no `echo` status messages, no decorative output or buzz words. Keep them terse and functional.

## What to keep
- The `#!/bin/bash` shebang (interpreter directive, not a comment).
- `set -e` and similar options that control script behavior.
- The actual commands (`docker-compose`, `python`, `cp`, `psql`, `alembic`, etc.).
- Control flow required for correctness: `if`/`fi` guards, `until`/`for`/`while` loops, retry/timeout counters, `exit` on failure.
- Variables that the commands depend on (e.g. `MAX_RETRIES`, `COUNT`).

## What to remove
- All `#` comment lines, including numbered phase headers (`# 1. Start Platform`, `# 2. ...`).
- All `echo` statements: progress banners, emoji decorations, "DONE/SUCCESS/WARNING" messages, in-loop progress dots (`echo -n "."`), and final summary/info blocks (URLs, "to stop run: ...").
- Buzz words and narration that add no functional value.

## Phasing
- Breaking a script into clear sequential steps is encouraged and good, but phases must be separated by blank lines only — **never** by `#` comments or `echo` headers. If a phase needs a label, the script should be split into separate files or functions instead.

## Requirements
- Do **not** add `#` comments to `.sh` files — not phase labels, not "what this does", not TODOs.
- Do **not** add `echo` for user-facing narration. If a command fails, the script's `exit` code (or `set -e`) is sufficient; do not print an error string first.
- The only acceptable `#` line is the `#!/bin/bash` shebang.
- Empty/blank lines are fine for visual separation between phases.

## Scope
Applies to every `.sh` file you **edit or create** in this project (e.g. `start.sh`, `demo.sh`, `setup.sh`). After editing, verify with `bash -n <file>` and confirm `grep -nE '(^[[:space:]]*#|echo )' <file>` returns only the shebang line.
