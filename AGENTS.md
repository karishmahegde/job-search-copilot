# Job Search Copilot — Agent Instructions

This file is read automatically by both Claude Code and Codex at the start
of every session in this repository. It contains everything needed to
write code, write tests, and scope a task consistently, regardless of
which agent or which person is doing the work.

## Before Starting Any Task

Run this sequence before writing any code, even for a small or seemingly
obvious task:

1. `git fetch && git pull` on the current sprint branch — work from the
   real latest state, not a stale local copy.
2. `git log --oneline <sprint-branch>..HEAD` — see what's actually been
   committed since the sprint started.
3. Read the last 5-10 rows of `docs/LOG.md` — they explain
   _why_ recent changes were made, which the commit log alone won't tell
   you.
4. Read the current task's Trello card in full. It is the task prompt.
   Do not start from a paraphrase or a verbal instruction alone if a card
   exists for the task.
5. If a recent task-log row's "Contracts touched" column, or the current
   card's "Contracts / Interfaces Touched" section, names anything (DB
   schema, `completion()` signature, `profile.yaml` schema, a named agent
   tool signature), re-read that contract's current definition before
   writing code against it — it may have changed since you last saw it.

## Naming Convention

Sprint numbers map 1:1 to phase numbers from the Development Plan's Build
Plan: Sprint 0 = Phase 0, Sprint 1 = Phase 1, and so on. Trello card IDs
follow `S<phase>-<sequence>`, e.g. `S0-01`, `S0-02`, `S0-03` for the first,
second, and third cards of Phase 0. Branch names derive from the card:
`feature/s0-01-<short-name>`.

---

## Coding Conventions

This is the single source of truth for how code is written in this
repository, regardless of which coding agent or human produces it.

### Language & Tooling

- **Python 3.12+**
- **Package management:** `uv` — `uv add <pkg>` to add a dependency, `uv run <cmd>` to run anything, `uv lock` to regenerate the lock file. Never hand-edit `uv.lock`.
- **Linting & formatting:** Ruff, configured in `pyproject.toml`. Run `uv run ruff check .` and `uv run ruff format .` before considering any task done. No code is committed with outstanding Ruff errors.
- **Type checking:** type hints are mandatory (see below). If a type checker (e.g. `mypy` or `pyright`) is added later, it will be configured in `pyproject.toml` and this document updated — do not add one unilaterally in a feature task.

### Docstrings

Google-style docstrings on every public module, class, and function (private
helpers prefixed `_` are exempt unless non-obvious).

```python
def score_match(jd: str, resume: str, preferences: dict, history: list[dict]) -> MatchResult:
    """Evaluate a job description against the candidate's profile and history.

    Args:
        jd: Normalized job description text.
        resume: Master resume text.
        preferences: Candidate preferences (roles, location, comp).
        history: Prior outcomes for similar roles, most recent first.

    Returns:
        A MatchResult containing the discard/pursue verdict, numeric score,
        and a human-readable rationale.

    Raises:
        ValueError: If jd or resume is empty.
    """
```

Module-level docstrings (top of file) should state the module's single
responsibility in one or two sentences — if it takes more than two sentences
to describe what a module does, it likely needs to be split.

### Type Hints

- Every function signature is fully typed — parameters and return type. No
  bare `def foo(x):`.
- Use built-in generics (`list[str]`, `dict[str, int]`), not `typing.List`/`typing.Dict` (Python 3.9+ style).
- Use `| None` instead of `Optional[...]`.
- Prefer `dataclasses` or `TypedDict`/`pydantic` models over passing raw
  `dict` around for any structure used in more than one place (e.g. the
  `completion()` contract's input/output, a `MatchResult`, a `RoleRecord`).
  The Development Plan's `completion()` contract (§7.4) should be a typed
  model, not an untyped dict, once implemented.

### Naming Conventions

| Element                   | Convention                                                                     | Example                               |
| ------------------------- | ------------------------------------------------------------------------------ | ------------------------------------- |
| Files / modules           | `snake_case.py`                                                                | `score_match.py`                      |
| Functions / variables     | `snake_case`                                                                   | `fetch_job_posting`                   |
| Classes / Pydantic models | `PascalCase`                                                                   | `MatchResult`                         |
| Constants                 | `UPPER_SNAKE_CASE`                                                             | `DEFAULT_TAILORING_THRESHOLD`         |
| Environment variables     | `UPPER_SNAKE_CASE`                                                             | `SUPABASE_SERVICE_ROLE_KEY`           |
| Named agent tools         | match the Design doc's signatures exactly                                      | `check_ats_compatibility(resume, jd)` |
| Branches                  | `feature/<trello-card-name>`, `fix/<issue-name>`, `test/<area>`, `docs/<area>` | `feature/s0-03-schema-rls`            |
| Trello card IDs           | `S<sprint>-<number>`                                                           | `S0-03`                               |

Named agent tool functions (§1.2 of the Design doc) must keep the exact
parameter names and order given in the Design doc. If an implementation
needs to deviate, that's a Design-doc change to discuss first, not a
silent rename.

### File & Folder Structure

Follow the Development Plan's project folder structure exactly (collectors/,
reasoning/, act/, llm/, state/, notify/, dashboard/, autofill/,
networking_tool/, contacts/, resume_generation/, loop/, tests/, docs/). Do
not introduce a new top-level folder without updating this document and the
folder structure section of the Development Plan — an agent should never
invent a new location for something ad hoc.

One module = one file = one responsibility. If a file is doing two distinct
jobs (e.g. fetching _and_ parsing), split it before adding more to it rather
than after.

### Configuration & Secrets

- All tunable values (thresholds, provider names, timeouts) come from
  `config/profile.yaml`, never hardcoded in source.
- Secrets never appear in source, comments, docstrings, or committed
  fixtures — including in test files. `.env` is gitignored from the first
  commit of any new repo; this is a hard gate before any other work starts.
- If a secret is ever exposed anywhere outside its intended location — a
  chat, a screenshot, a commit later reverted — rotate it immediately.
  Removing it from a file does not undo the exposure.
- `.env` sourcing on zsh: use
  `set -a; source <(grep -v '^#' .env | grep -v '^\s*$'); set +a` — plain
  `source .env` breaks on comment lines.

### Error Handling

- Deterministic-layer code (collectors, DB I/O, scheduling) must catch and
  log expected failure modes (network errors, malformed responses, missing
  selectors) rather than letting them propagate and kill the loop — this is
  NFR3 (graceful degradation), and it is a hard requirement, not a
  nice-to-have, on every collector.
- Never use a bare `except:`. Catch the specific exception type(s) you
  expect; let unexpected exceptions surface.
- LLM-layer code (anything calling `completion()`) must handle provider
  errors and timeouts explicitly and return a typed error/result, not raise
  an unhandled exception into the Reason/Act step.

### Commits & Pull Requests

- No direct commits to `main`. Every task gets its own branch off the
  current sprint branch.
- PR description includes: what changed, how it was tested, related Trello
  card. (Per Development Plan §7.5.)
- The author does not merge their own PR.
- Every PR that touches a documented contract (DB schema, `completion()`
  signature, `profile.yaml` schema, a named agent tool's signature) must
  include the task-log entry (see `docs/LOG.md`) — this
  is checked by the reviewer, not optional.

If something comes up that isn't covered here, resolve it once, add the
rule to this document, and reference the addition in the task log — don't
let two agents independently invent two different answers to the same
question.

---

## Test Strategy

This project's test rules exist because of a specific, real failure: two
coding agents once independently generated test cases for overlapping
code, producing more tests than necessary, in inconsistent formats, with
no clear ownership. These rules are designed to make that failure
structurally impossible, not just less likely.

### Core Rule: One Source File, One Test File, One Owner

Every source file has **exactly one** corresponding test file, at the
mirrored path:

```
reasoning/score_match.py       -> tests/reasoning/test_score_match.py
collectors/greenhouse.py       -> tests/collectors/test_greenhouse.py
state/supabase_client.py       -> tests/state/test_supabase_client.py
```

**Before writing any test, check whether the mirrored file already exists.**
If it does, extend it — add test functions to the existing file. Do not
create a second file (`test_score_match_2.py`, `test_score_match_extra.py`,
etc.) for the same source file, ever. If the existing file's tests look
wrong or incomplete, fix or extend them in place; don't work around them
with a parallel file.

### Framework & Layout

- **pytest**, run via `uv run pytest`.
- Top-level split: `tests/unit/` and `tests/integration/`, each mirroring
  the source tree beneath it:

```
tests/
├── unit/
│   ├── collectors/
│   ├── reasoning/
│   ├── act/
│   ├── state/
│   └── autofill/
├── integration/
│   ├── collectors/
│   ├── reasoning/
│   ├── state/
│   └── llm/
├── conftest.py
└── fixtures/
```

- **Unit tests** mock all external I/O (network calls, Supabase, LLM
  providers, filesystem where reasonable). They test one function/module's
  logic in isolation.
- **Integration tests** exercise a real path against a real or realistic
  dependency (a test Supabase project, a real LiteLLM call to a local
  Ollama model, a real Greenhouse API response fixture). They are slower
  and fewer in number than unit tests, and are reserved for the actual
  seams between components — not a duplicate of unit coverage with mocks
  removed.

### Naming Convention

Test functions: `test_<function_or_behavior>__<condition>__<expected>`

```python
def test_score_match__high_fit_role__returns_pursue_verdict():
    ...

def test_dedupe__duplicate_ats_id__keeps_first_seen_row():
    ...

def test_greenhouse_collector__api_timeout__logs_and_skips_source():
    ...
```

The name should make the test's intent readable without opening the
function body. If you can't name it this way, the test is probably
checking more than one thing — split it.

### What Must Be Tested, Per Feature

Every phase's "done" bar includes tests for:

- **The happy path** — the documented, expected behavior.
- **Documented edge cases from the Design/Development Plan** — e.g. FR4's
  dedup rule has explicit OR-match, keep-first-seen, append-source
  behavior; each of those is its own test, not folded into one.
- **Graceful degradation** (NFR3) — for every collector, a test that
  simulates the source failing (timeout, malformed response, broken
  selector) and asserts the loop continues rather than raising.
- **Any documented contract** — e.g. the `completion()` input/output
  contract (Development Plan §7.4) gets tests asserting the shape of what
  it returns, independent of which provider is configured.

A task is not "done" because code exists — it's done when the mirrored test
file covers the behaviors above and `uv run pytest` passes.

### LLM-Provider Tests Specifically

- At least one integration test must exercise the **real config-loading
  path** (`profile.yaml → config/loader.py → completion()`), not just an
  env-var shortcut — this is a standing requirement, not optional polish.
- Multi-provider proof (Phase 0 exit criteria) means: the same test (or a
  parametrized version of it) runs against at least two configured
  providers and asserts the same output contract shape from both.

### Fixtures & Test Data

- Shared fixtures live in `tests/fixtures/` (e.g. sample job description
  text, a sample `profile.yaml`, sample API responses per source).
- Fixtures are named for what they represent, not which task created them:
  `fixtures/greenhouse_listing_sample.json`, not
  `fixtures/dev_notes.json`.
- No real secrets, tokens, or personal data in any fixture, ever — this
  applies even to a fixture that looks like it needs a "realistic" API key;
  use an obviously-fake placeholder value instead.

### Before Opening a PR

- `uv run pytest` passes locally, full suite.
- `uv run ruff check .` passes.
- If the task touched a documented contract, the task-log entry states
  what test(s) cover the change.
- No new test file was created where a mirrored file already existed.

---

## Task Card Template

Every Trello card in this project is written using this exact template, in
full. The card **is** the coding-agent prompt — copy its contents directly
into Claude Code or Codex with minimal to no editing. If a section doesn't
apply to a given task, write "N/A" rather than deleting the section, so the
template stays predictable across every card.

Filling this out fully is part of scoping the task, not paperwork to do
afterward — a card that's hard to fill in is usually a sign the task itself
is still too vague or too large.

```markdown
# [Card ID] — [Short Task Title]

## Phase & Feature

Phase: [number, from the Development Plan's Build Plan]
Feature: [FR/NFR reference(s), e.g. FR5 — Role Evaluation]

## Scope

In scope:

- [explicit bullet list of what this task delivers]

Explicitly out of scope:

- [explicit bullet list — anything a reasonable agent might assume is
  included but isn't, e.g. "does not include the dashboard display of
  this data, only the underlying function"]

## Relevant Files

Existing files to read before starting:

- [path — why it matters, e.g. "state/schema.sql — table this task writes to"]

Files this task is expected to create or modify:

- [path]

## Contracts / Interfaces Touched

[State explicitly: "None" OR name the exact contract, e.g. "Modifies the
completion() output shape defined in Development Plan §7.4" — if a contract
is touched, the task-log entry after this task is mandatory, not optional.]

## Conventions to Follow

Follow the Coding Conventions and Test Strategy sections above in full.
Do not restate their rules here — this section exists only to flag
exceptions.
Exceptions for this task, if any: [state explicitly, or "None"]

## Test Requirements

Mirrored test file(s) this task owns:

- [path, e.g. tests/unit/reasoning/test_score_match.py]

Specific behaviors that must be tested (beyond the standard happy-path +
edge-case + graceful-degradation baseline above):

- [bullets, if any — or "None beyond the standard baseline"]

## Acceptance Criteria

- [ ] [Concrete, checkable statement — "returns X given Y", not "works correctly"]
- [ ] [ ... ]
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] Task log row appended to docs/LOG.md

## Task Log Requirement

Before opening the PR, append one row to `docs/LOG.md` per the
format described at the top of that file: card ID, agent, what changed,
contracts touched, and any notes or follow-ups.

## Related PR

[filled in once the PR is opened, not before]
```

### Notes for the Card Author

- **Write the card before assigning it to either agent** — the card should
  be usable by _either_ Claude Code or Codex without modification. If a
  card only makes sense for one of the two tools, that's a sign it's
  under-specified.
- **"Explicitly out of scope" is not optional filler.** Most of the
  half-finished-feature problem from an earlier attempt at this project
  came from tasks that quietly grew or shrank in scope mid-execution
  because the boundary was never written down. If you're unsure what's
  out of scope, that's a sign to resolve it before writing the card, not
  during.
- **One card should map to one complete, reviewable unit of work** — per
  the project's build-order principle, a card should not represent a
  partial slice of a larger feature that gets "finished later." If a
  feature is too large for one card, split it into multiple cards that are
  each still individually complete pieces of that feature (e.g. one card
  per collector source, if each collector is independently testable and
  reviewable — not one card that does "half the dedup logic").
- **Acceptance criteria should be verifiable by the reviewer without
  re-deriving intent** — a reviewer should be able to check each box
  against the actual PR without needing to ask "what did you mean by
  this."

---

## Rules That Always Apply

- Follow the Coding Conventions section above for how code is written.
- Follow the Test Strategy section above for how tests are structured. In
  particular: check whether a mirrored test file already exists before
  creating one — never create a second test file for a source file that
  already has one.
- Every task ends with a new row appended to `docs/LOG.md`,
  written before the PR is opened, per the format described at the top of
  that file.
- No direct commits to `main`. Branch per task: `feature/<trello-card-name>`.
- The author does not merge their own PR.
- Never commit secrets. `.env` is gitignored from the first commit.

## Where Things Live

- `docs/SETUP.md` — user-facing setup instructions for running your own instance.
- `docs/Design-Requirements.docx` — the Design & Requirements
  specification (source of truth for what the system does).
- `docs/LOG.md` — the running task log; format and rules are
  in a header block at the top of that same file.

If an instruction in a Trello card conflicts with something in this file
or the design docs, say so explicitly rather than silently picking one —
this usually means the docs need updating, not that the conflict should
be quietly resolved in code.
