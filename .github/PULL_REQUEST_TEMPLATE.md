## What changed


## How it was tested


## Related Trello card


---

### Checklist (author fills in before requesting review)

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] No new test file was created where a mirrored test file already existed (see `AGENTS.md` Test Strategy section)
- [ ] `docs/dev/task-log/LOG.md` has a new row for this task
- [ ] If this PR touches a documented contract (DB schema, `completion()` signature, `profile.yaml` schema, a named agent tool signature) — the task-log entry's "Contracts / interfaces touched" section says so explicitly
- [ ] No secrets, keys, or `.env` values included in this diff

### Checklist (reviewer confirms before approving)

- [ ] Code matches the agreed design (Design & Requirements doc, Development Plan)
- [ ] Task-log entry exists and is specific, not vague boilerplate
- [ ] Naming and folder structure match `AGENTS.md` Coding Conventions section
- [ ] No unrelated changes included
