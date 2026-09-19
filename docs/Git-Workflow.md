# Git workflow

How work moves from idea to `main` in this project. It matches how Sprint 1 was
actually run, plus the tooling added afterwards.

## One-time setup per clone

```bash
git config core.hooksPath .githooks     # enables the pre-commit test hook
pip install -e ".[dev]"
```

## Branches

| Branch | Purpose |
|---|---|
| `main` | Always green and releasable. Changes arrive only through a merged PR. |
| `sprint-N` | The work of one sprint (see `docs/Sprints.md`), branched from a fresh `main`. |
| `fix/<topic>`, `chore/<topic>` | Small out-of-band fixes or tooling that shouldn't wait for a sprint. |

**Branches are kept after merging.** They are history, so don't delete them,
locally or on the remote.

Always branch from an up-to-date `main`:

```bash
git checkout main && git pull --ff-only
git checkout -b sprint-2
```

## Commits

- One purpose per commit, and the unit tests pass at every commit. Use
  `git add -p` to split a messy working tree into clean commits.
- Subject line: `Sprint N: <what changed>` for sprint work, or a plain
  imperative sentence for chores. Keep it around 70 characters.
- Body: explain **why**, not just what. Name the root cause, the alternatives
  that were tried and rejected, how it was verified, and the caveats. Recent
  history is the model to copy (`git log -5`).
- Behavior changes get called out explicitly in the body.

## Pull requests

1. Push the branch and open a PR into `main`. The template
   (`.github/pull_request_template.md`) prompts for summary, results, behavior
   changes, known open items and testing.
2. For anything touching LLM behavior, include the before/after eval numbers and
   link the `docs/eval/` report.
3. CI must be green (`.github/workflows/ci.yml`: unit tests, plus ruff as
   informational until the existing findings are cleaned up).
4. Merge with a merge commit, which is what PR #1 and #3 used. It keeps the
   sprint's commits and their explanatory bodies intact.

## Automated checks

| Where | What | Bypass |
|---|---|---|
| `.githooks/pre-commit` (local) | Runs `pytest` when a commit touches `src/`, `tests/` or `pyproject.toml` | `git commit --no-verify` |
| GitHub Actions `CI` | `pytest` (blocking), `ruff check` (informational) on PRs and pushes to `main` | none for tests |

The live eval harness (`tests/eval/run_eval.py`) needs a local Ollama model, so it
runs manually and is deliberately not part of CI.

## Milestone tags

Tag the merge commit at the end of each sprint so the state of the project at
that point is always one command away:

```bash
git tag -a v0.1.0-sprint1 <merge-commit> -m "Sprint 1: evaluation foundation"
git push origin v0.1.0-sprint1
git checkout v0.1.0-sprint1             # look around; `git checkout -` to return
```

## Recommended GitHub settings (Settings, then Branches, then add rule for `main`)

- Require a pull request before merging.
- Require the `CI / test` status check to pass.
- Block force-pushes to `main`.

## Recovery and investigation cheat sheet

| Situation | Command |
|---|---|
| "I lost a commit or branch" | `git reflog`, then `git branch <name> <sha>` |
| Undo a commit that's already pushed | `git revert <sha>` (adds a new commit, rewrites nothing) |
| Discard changes to one file | `git restore <file>` |
| Park unfinished work | `git stash -u`, then `git stash pop` |
| Find which commit broke something | `git bisect start`, `git bisect bad`, `git bisect good <sha>` |
| Who added this line, and why | `git blame <file>`, then `git show <sha>` |
| When did this text appear or vanish | `git log -S "text" --oneline` |
| Compare eval baselines across sprints | `git diff v0.1.0-sprint1 HEAD -- docs/eval/` |
| Run two branches side by side | `git worktree add ../app-main main` |

**Never rewrite published history** (`push --force`, or a rebase of a branch
others have pulled) on `main` or any branch under review.
