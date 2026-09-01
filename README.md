# Job Search Copilot

**An agentic system for end-to-end job search automation.**

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Job Search Copilot observes job postings and market signals, makes
judgment-based decisions on fit, and produces ready-to-act outputs: a
ranked digest, tailored resumes, outreach drafts, and autofilled
applications. It automates everything except the few steps that legal and
platform-terms constraints require to stay manual.

The system is built to be cloneable. Any job seeker can run their own
instance by supplying their own profile data.

## How It Works

Job Search Copilot runs as a continuous agent loop:

<div align="center">

**Observe → Reason → Act → Record → Wait → (back to Observe)**

</div>

| Step             | What happens                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| **Observe**      | New listings, application status changes, time-elapsed triggers                                              |
| **Reason** (LLM) | Evaluate a signal against the candidate's profile and accumulated history; decide discard vs. pursue         |
| **Act**          | Score and rank, generate a tailored resume, draft outreach, autofill, flag a skill gap, or queue a follow-up |
| **Record**       | The outcome is written back to state                                                                         |
| **Wait**         | For the next trigger                                                                                         |

Every Record feeds the next Reason step. This is a loop with memory, not a
one-shot pipeline. Consequential actions, like submitting an application or
sending a message, always stop for explicit human approval before they
happen.

The full design (functional requirements, non-functional requirements, the
named agent tools, and the technology stack) is documented in
[`docs/Design-Requirements.docx`](docs/Design-Requirements.docx).

## What It Does

- Collects listings from Greenhouse, Lever, Ashby, Adzuna India, RemoteOK, Himalayas, and configurable custom career pages
- Evaluates each listing's fit using the candidate's profile and past outcomes, with a stated rationale for every decision
- Generates ATS-friendly tailored resumes for roles above a self-adjusting match threshold
- Delivers a daily digest via a dashboard, with a nudge-only email
- Autofills applications across major ATS platforms, always stopping before submission
- Tracks follow-ups for dream-company and referral-contact roles
- Surfaces recurring skill gaps across everything it has evaluated, not just applied-to roles

## Technology

| Layer              | Tool                        |
| ------------------ | --------------------------- |
| Language           | Python                      |
| Scheduler          | GitHub Actions              |
| LLM access         | LiteLLM (provider-agnostic) |
| State / tracking   | Supabase (Postgres)         |
| Dashboard          | Streamlit                   |
| Autofill           | Playwright (local-only)     |
| Custom collectors  | Scrapy + scrapy-playwright  |
| Package management | uv                          |

Full component-by-component rationale is in the design document linked
above.

## Getting Started

This project is set up to be cloned and run with your own profile and your
own Supabase project, with no code changes required. Setup instructions
(Supabase project creation, `profile.yaml` configuration, secrets, and LLM
provider selection) live in [`docs/SETUP.md`](docs/SETUP.md).

## Project Structure

```
job-search-copilot/
├── docs/               Design docs, setup instructions, and the task log
├── config/             profile.yaml and collector configuration
├── collectors/         Job listing sources (ATS + aggregator + custom)
├── reasoning/          Match scoring, tailoring, skill-gap analysis
├── act/                Tool selection and dispatch
├── llm/                Provider-agnostic LLM access (LiteLLM)
├── state/               Supabase client and schema
├── dashboard/           Streamlit dashboard
├── autofill/             Local, browser-driven application autofill
├── loop/                 The Observe, Reason, Act, Record, Wait loop
└── tests/                Unit and integration tests
```

## Development

This project is built in dependency-ordered phases, each delivering one or
more complete features. No feature is split across phases. Coding
conventions, testing strategy, and the task template used for every unit of
work are documented in [`AGENTS.md`](AGENTS.md).

## License

MIT, see [LICENSE](LICENSE) for details.

<div align="center">

<sub>Built by <a href="https://github.com/AishShyam">Aishwarya Shyam</a> and <a href="https://github.com/karishmahegde">Karishma Hegde</a></sub>

</div>
