## Shell Usage
- Use `bash` for shell command execution in this repo.
- Prefix command runs with `source source_me.sh && ...` so repo defaults are consistently applied.
- Prefix command runs with `source source_me.sh && python3 ` for python to get an allow 

## Coding Style
See Python coding style in docs/PYTHON_STYLE.md.
See Markdown style in docs/MARKDOWN_STYLE.md.
See repo style in docs/REPO_STYLE.md.
When making edits, document them in docs/CHANGELOG.md.
Agents may find pytest programs to run in the tests folder, including smoke tests and pyflakes runner scripts. These should all be capable of the -k flag, such as pytest test_feature.py -k changed_file.py

## Python Environment
AI agents (Codex/Claude) must run Python using `source source_me.sh && python3` (use Python 3.12 only).
AI agents should execute shell commands with Bash (`bash -lc`) instead of Zsh because `source_me.sh` and this repo's environment assumptions target Bash semantics.
This is only for AI agents runtime, not a requirement for repo scripts.
On this user's macOS (Homebrew Python 3.12), Python modules are installed to `/opt/homebrew/lib/python3.12/site-packages/`.

please only run pointed pytests specific to your update; we have too many files to run pytest all of the time
