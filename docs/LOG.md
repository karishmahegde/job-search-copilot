# Job Search Copilot — Task Log

Replaces manually re-summarizing what happened between coding-agent
sessions. Every task, on completion, gets one row appended below, written
by the agent that did the work, as part of the task itself, before the PR
is opened, and reviewed in the PR like any other change.

**Format:** 2-3 lines per task, appended as a new row at the bottom.
`Card` = Trello card ID. `Agent` = `Claude Code` or `Codex`. `What changed`
= one specific line, not "made changes." `Contracts touched` = `None`, or
name the exact contract (DB schema, `completion()` signature,
`profile.yaml` schema, a named agent tool signature); mandatory to fill in
per `CONVENTIONS.md` §8. `Notes / follow-ups` = anything the next task
needs to know, or `None`. If a decision needs more room than that, put it
in the PR description and reference it here (`See PR #14`).

**Rules:** Agent-written, not human-paraphrased. Written before the PR,
part of the PR diff. Append-only: never edit or delete an earlier row; a
correction gets its own new row ("Corrects S0-03: ..."). One row per task.
"None" is a complete answer; "made some changes to the schema" is not.

**Before starting a new task:** read the last 5-10 rows below, then run
`git log --oneline sprint-1..HEAD` (or the relevant sprint branch) to see
the real commit sequence alongside them. If a recent row's "Contracts
touched" names something relevant to the current task, re-read that
contract's current definition before writing code against it. Don't rely
on memory of a previous session or ask a human to re-summarize; this table
and git history are the source of truth.

**Merge conflicts:** expected occasionally, since this is one shared file
with entries appended at the bottom. Keep both new rows; exact ordering of
two same-day entries doesn't matter.

See `docs/dev/CONVENTIONS.md` for coding style, `docs/dev/TESTING.md` for test
requirements, and `docs/dev/TASK_TEMPLATE.md` for how a task is scoped.

---

| Card | Agent | What changed | Contracts touched | Notes / follow-ups |
|---|---|---|---|---|
