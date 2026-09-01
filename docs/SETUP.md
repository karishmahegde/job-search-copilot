# Setup

This guide takes a fresh clone to a running instance: dependencies, a
Supabase project, credentials, your profile, an LLM provider, and the
scheduled loop. No code changes are required anywhere — every
instance-specific value lives in `config/profile.yaml` or `.env`.

## 1. Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12+ | `.python-version` pins 3.12; `uv` will fetch it if missing |
| [uv](https://docs.astral.sh/uv/) | latest | package and environment manager |
| git | any recent | |
| LibreOffice | any recent | only for the headless `.docx` → PDF step when generating tailored resumes |
| [Ollama](https://ollama.com/) | latest | only if you run a local model as your LLM provider |

A [Supabase](https://supabase.com/) account (free tier is sufficient) and
a Gmail account for digest email are also required — both are set up
below.

## 2. Clone and install

```bash
git clone https://github.com/karishmahegde/job-search-copilot.git
cd job-search-copilot
uv sync
```

`uv sync` creates `.venv/` and installs locked dependencies. Run
everything through `uv run <cmd>` so it uses that environment.

## 3. Supabase project

State (every evaluated role, contact, draft, and outcome) and resume
files live in your own Supabase project. Nothing is shared with the
project maintainers or other clones.

1. Create a new project at [app.supabase.com](https://app.supabase.com/).
   Any region and the free tier are fine.
2. Apply the schema. In the project's **SQL Editor**, run the contents of
   `state/schema.sql`. This creates all tables and the
   Row Level Security policies — RLS is enabled even for single-user
   instances as defense-in-depth (NFR9).
3. Create a **Storage** bucket named `resumes` (Storage → New bucket,
   keep it private). Generated resume PDFs are uploaded here.
4. Collect three values from **Project Settings**:
   - **Project URL** (Settings → API) → `SUPABASE_URL`
   - **`service_role` key** (Settings → API → Project API keys) →
     `SUPABASE_SERVICE_ROLE_KEY` — secret, backend only, never ship it to
     the dashboard or browser
   - **`anon` key** → `SUPABASE_ANON_KEY`

## 4. Environment variables

```bash
cp .env.example .env
```

Fill in `.env` with your real values. It is gitignored (`.env`,
`.env.*`, except `.env.example`) — never commit it, not even briefly.

| Group | Variables | When you need it |
| --- | --- | --- |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` | always |
| LLM | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_HOST` | set only the provider(s) your `profile.yaml` references |
| Email | `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` | always (digest delivery) |
| Autofill | `LOCAL_LISTENER_TOKEN` | only if you use the autofill listener; any long random string |
| Shared mode | `PARTNER_<NAME>_SUPABASE_READONLY_KEY` | only if `mode: shared` |

To load `.env` into a shell on zsh (plain `source .env` breaks on
comment lines):

```bash
set -a; source <(grep -v '^#' .env | grep -v '^\s*$'); set +a
```

## 5. Profile configuration

```bash
cp config/profile.example.yaml config/profile.yaml
```

`config/profile.yaml` is the single file a new user edits. Fill it in:

| Field | Required | Notes |
| --- | --- | --- |
| `resume_path` | yes | path to your master resume, `.pdf` or `.docx` |
| `preferred_roles` | yes | non-empty list of role titles |
| `locations` | yes | non-empty list of locations |
| `compensation.minimum_salary` | | number; `0` means no floor |
| `compensation.currency` | | ISO 4217 code, e.g. `USD`, `INR`, `GBP` |
| `dream_companies` | | drives follow-up eligibility |
| `referral_contacts` | | each: `{name, company, email?}` |
| `email` | yes | profile-level contact email |
| `llm.provider` | yes | `anthropic`, `openai`, or `ollama` |
| `llm.model` | yes | provider-specific model id |
| `llm.fallback_provider` / `llm.fallback_model` | | optional, but required together |
| `thresholds.tailoring_score_min` | | default `0.75`; self-adjusts over time |
| `thresholds.follow_up.*` | | outreach / with-contact / expiry windows |
| `sources.ats` | | subset of `greenhouse`, `lever`, `ashby` |
| `sources.aggregators` | | subset of `adzuna_india`, `remoteok`, `himalayas` |
| `sources.custom_career_pages_config` | | path to a custom-pages file (see §7) |
| `mode` | | `single` (default) or `shared` (see §8) |
| `notifications.digest_email_enabled` | | `true`/`false` |
| `notifications.send_time_local` | if digest enabled | `HH:MM`, 24-hour |
| `notifications.timezone` | if digest enabled | IANA name, e.g. `Asia/Kolkata` |
| `dashboard.access_control` | | `restricted` (default) |

## 6. LLM provider

All model calls route through LiteLLM (FR15), so the provider is a
configuration choice, not a code dependency. Pick one in `profile.yaml`:

**Anthropic**
```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5
```
Set `ANTHROPIC_API_KEY` in `.env`.

**OpenAI**
```yaml
llm:
  provider: openai
  model: gpt-4o
```
Set `OPENAI_API_KEY` in `.env`.

**Ollama (local, no API cost)**
```yaml
llm:
  provider: ollama
  model: llama3.1
```
Run `ollama serve` and `ollama pull llama3.1` first. Set `OLLAMA_HOST`
only if it is not on the default `http://localhost:11434`.

Optionally add a fallback used when the primary provider errors or times
out (both fields required together):

```yaml
  fallback_provider: ollama
  fallback_model: llama3.1
```

## 7. Custom career pages (optional)

To monitor a company that has its own career page rather than a
supported ATS, point `sources.custom_career_pages_config` at a YAML file
(e.g. `config/custom_pages.yaml`) with one entry per company — name, URL,
and CSS selectors. Multi-page crawls and JavaScript-rendered listings are
supported. New entries are picked up on the next scheduled run with no
code change (FR3).

## 8. Shared mode (optional)

`mode: single` (the default) is a fully standalone instance. To share
only contacts and skill-gap data with a partner running their own
instance, set `mode: shared` and add each partner with their Supabase
project URL and a **read-only** key scoped to those two data sets. The
key is referenced from `profile.yaml` as `${PARTNER_<NAME>_SUPABASE_READONLY_KEY}`
and its value goes in `.env`. No other data is ever shared, and the code
path is inactive unless `mode: shared` is set (FR16).

## 9. Run it

**Dashboard** (digest content — roles, resumes, drafts):
```bash
uv run streamlit run dashboard/app.py
```

**The loop** (Observe → Reason → Act → Record → Wait): run the loop
entry point via `uv run`. A single pass can be triggered manually for
testing; normally GitHub Actions runs it on schedule (see §10).

**Autofill listener** (local only): install browsers once with
`uv run playwright install`, then start the token-secured listener bound
to localhost. Autofill always stops before submission — you review and
submit each application yourself (NFR1).

## 10. Scheduled runs (GitHub Actions)

The daily digest pass runs on GitHub Actions. In your fork's **Settings
→ Secrets and variables → Actions**, add the same values as `.env`
(`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, the
LLM key(s) you use, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`). The workflow
reads these as secrets; `profile.yaml` is committed to your fork and read
directly. Autofill is local-only and never runs in CI.

## 11. Verify the setup

- `uv run ruff check .` and `uv run ruff format --check .` are clean
- `uv run pytest` passes
- `python -c "import yaml; yaml.safe_load(open('config/profile.yaml'))"`
  parses, and required fields are filled
- Supabase SQL Editor shows the schema tables and the `resumes` bucket
  exists
- A smoke call to your configured LLM provider succeeds

This clone-and-run path is exercised end to end at the project's final
cloneability gate (FR14 / NFR5): an independent clone configured using
only this document, with no code changes.
