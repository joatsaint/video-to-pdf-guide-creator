# DECISIONS.md
## Architectural Decision Log — Video-to-PDF-Guide-Creator

**Version:** 1.0
**Owner:** Randy Skiles
**Last Updated:** May 2026

---

## Why This Document Exists

Every significant architectural decision is recorded here with context,
alternatives considered, and reasoning. This prevents re-litigating the
same decisions across sessions and serves as a portfolio artifact
demonstrating enterprise-grade thinking.

**Read this file at the start of every Claude Code session.**

---

## ADR-001 — Streamlit for MVP, Next.js for Production
**Date:** May 2026
**Status:** Active

**Context:**
Need a live demo deployed as fast as possible for portfolio purposes.
Long-term goal is a production revenue product.

**Decision:**
Phase 1: Build with Streamlit — deploy to Streamlit Cloud.
Phase 2: Rebuild with Next.js + PostgreSQL for production scale.

**Alternatives considered:**
- WordPress — too slow to build, wrong tool for a web app
- Flask — more control but more boilerplate, slower to demo
- Next.js from day one — correct for production, too slow for MVP

**Reasoning:**
Streamlit converts Python scripts to web apps with minimal overhead.
Since the core logic is Python (transcript fetch + Claude API), Streamlit
requires almost no additional code. A live URL for portfolio purposes
can be deployed in hours, not days. Next.js rebuild happens when there
are paying customers to justify the investment.

**Consequences:**
- ✅ Live demo in hours not days
- ✅ Portfolio URL available immediately
- ✅ Core Python logic reusable in Next.js version
- ⚠️ Streamlit has UI limitations — acceptable for MVP
- ⚠️ Will require full rebuild for production — planned and expected

---

## ADR-002 — Haiku Model for Guide Generation
**Date:** May 2026
**Status:** Active

**Context:**
Guide generation runs one Claude API call per user request.
Cost per request directly affects unit economics at scale.

**Decision:**
Use `claude-haiku-4-5-20251001` for all guide generation.

**Alternatives considered:**
- Claude Sonnet — higher quality, ~4x cost
- Claude Opus — highest quality, ~15x cost
- GPT-4o-mini — comparable cost, less familiar

**Reasoning:**
Guide generation is a formatting and structuring task, not a reasoning task.
The transcript contains all the information — Claude's job is to reorganize
it into a clean format. Haiku handles this adequately at ~$0.001 per guide.
At Sonnet pricing, 1,000 guides/month = ~$4 vs ~$1 with Haiku.
Quality difference for formatting tasks does not justify the cost difference.

**Upgrade trigger:**
If user feedback consistently indicates guide quality is poor, test Sonnet
on 50 guides and compare before upgrading permanently.

**Consequences:**
- ✅ ~$0.001 per guide — economically viable at scale
- ✅ Fast response time — Haiku is fastest Claude model
- ⚠️ May miss nuanced instructions in complex videos — monitor feedback

---

## ADR-003 — Model-Agnostic Architecture
**Date:** May 2026
**Status:** Active

**Context:**
AI token pricing is not permanent. As Anthropic and OpenAI approach IPO
and face investor pressure, token prices may increase significantly.
Vendor lock-in is a real risk for any AI-powered product.

**Decision:**
All Claude API calls are isolated in `src/guide_generator.py` only.
No other file makes LLM API calls. Switching providers requires
changing one file and one environment variable.

**Alternatives considered:**
- Inline API calls in app.py — faster initially, impossible to migrate
- Multiple provider support from day one — over-engineered for MVP

**Reasoning:**
The cost of isolation is one afternoon. The cost of not isolating is
a full rewrite when pricing changes. This is ADR-009 from the
enterprise-ai-pipeline project applied here from day one.

**Switching options if needed:**
1. AWS Bedrock — same Claude models, enterprise compliance
2. Google Gemini Flash — ~$0.075/1M tokens
3. OpenAI GPT-4o-mini — ~$0.15/1M tokens
4. Ollama local — zero cost, open-source models

**Consequences:**
- ✅ Provider switch = one file change
- ✅ Documents vendor risk awareness for portfolio
- ⚠️ Requires discipline to never add LLM calls outside guide_generator.py

---

## ADR-004 — Prompt as Versioned File, Not Inline String
**Date:** May 2026
**Status:** Active

**Context:**
The Claude prompt for guide generation directly determines output quality.
Iterating on prompts is different from iterating on code — it requires
A/B testing, rollback capability, and version tracking.

**Decision:**
Store the guide generation prompt in `prompts/guide_prompt.txt`.
Load it at runtime. Version it separately from code.

**Alternatives considered:**
- Inline prompt string in guide_generator.py — simpler, not evolvable
- Database-stored prompts — overkill for MVP

**Reasoning:**
Treating prompts as first-class artifacts enables:
- Prompt changes without code deployments
- A/B testing different prompt versions
- Rolling back to a previous prompt if quality degrades
- Clear documentation of what instructions Claude receives

This also demonstrates prompt engineering discipline for portfolio purposes.

**Consequences:**
- ✅ Prompt evolution independent of code deployments
- ✅ Clear audit trail of prompt changes via git history
- ⚠️ One additional file to manage — acceptable overhead

---

## ADR-005 — Email Capture as Primary CTA, Not Download
**Date:** May 2026
**Status:** Active

**Context:**
The app needs to build an email list as a secondary business objective.
Two options: download button only, or email-first with download as secondary.

**Decision:**
Primary CTA is "Email this guide to myself."
Secondary CTA is "Download PDF."
Both available. Email is presented first and more prominently.

**Alternatives considered:**
- Download only — user gets guide, we get nothing
- Email required before download — too much friction, reduces conversions
- No email capture — missed opportunity

**Reasoning:**
A user who emails the guide to themselves has self-identified as someone
who finds how-to video content valuable enough to save. That's a
high-quality email subscriber — far more targeted than a generic opt-in.
Making email optional (not required) reduces friction while still
capturing motivated users. Every subscriber proves product-market fit.

**Consequences:**
- ✅ Builds targeted email list of how-to content consumers
- ✅ Low friction — download always available without email
- ✅ Each subscriber = validation data point
- ⚠️ Requires SMTP or email API integration — schedule for Phase 1.5

---

## Decision Backlog

Decisions to document when made:

- [ ] PDF library selection (ReportLab vs WeasyPrint)
- [ ] User guide library/database design
- [ ] Authentication strategy for small business accounts
- [ ] Rate limiting strategy per user
- [ ] Streamlit Cloud vs self-hosted deployment
- [ ] Privacy policy hosting approach

### ADR-016 — UptimeRobot for Streamlit Cloud Keep-Alive
**Date:** May 2026
**Status:** Active

**Context:**
Streamlit Community Cloud free tier hibernates apps after 2 consecutive
days of zero traffic. A sleeping app takes ~30 seconds to wake — acceptable
for occasional use but unacceptable for a portfolio demo or public product.

**Decision:**
Use UptimeRobot free tier to ping the app URL every 12 hours.
Monitor ID: 803030948
URL: https://video-to-pdf-guide-creator.streamlit.app/

**Alternatives considered:**
- GitHub Actions scheduled workflow — free but adds complexity to repo
- Upgrade to paid Streamlit hosting — unnecessary at current stage
- Migrate to Railway/Render — Tier 4 decision, deferred to Stage 4

**Reasoning:**
UptimeRobot free tier pings every 12 hours — well within the 48-hour
sleep threshold. Zero cost, zero repo complexity, 5-minute setup.
Solves the problem completely at current scale.

**Upgrade trigger:**
When app has paying customers requiring guaranteed uptime SLA —
migrate to Railway ($5/month) and document as ADR update.

**Consequences:**
- ✅ App stays alive indefinitely at zero cost
- ✅ No changes to repo or deployment pipeline
- ✅ UptimeRobot also provides uptime monitoring and alerts
- ⚠️ Free tier limited to 50 monitors — not a concern for this project

---

### ADR-006 — Error Tracking with Sentry
**Status:** Deferred — implement before public launch
**Decision:** Add Sentry SDK for unhandled exception capture
**Trigger:** Before sharing public URL beyond portfolio audience
**Effort:** 30 minutes — one line + SENTRY_DSN env var
**Notes:** Free tier at sentry.io. Silently disabled if DSN is empty — safe for local dev.

---

### ADR-007 — Per-Session Rate Limiting
**Status:** Deferred — implement before public launch
**Decision:** Limit guides per session to prevent API cost abuse
**Trigger:** Before promoting app beyond portfolio audience
**Effort:** 15 minutes — Streamlit session_state counter
**Default:** 5 guides per session on free tier
**Notes:** Session-based only. IP-based Redis rate limiting is Tier 4 (ADR-014).

---

### ADR-008 — GitHub Actions CI Pipeline
**Status:** Deferred — implement before public launch
**Decision:** Automated test + pip audit on every push
**Trigger:** Before first public commit of working app
**Effort:** 30 minutes — copy pattern from enterprise-ai-pipeline
**Notes:** Blocks merges to master if tests fail.

---

### ADR-009 — Dependency Vulnerability Scanning
**Status:** Deferred — implement before public launch
**Decision:** pip audit in CI + pre-deployment manual check
**Trigger:** Before public launch
**Effort:** 10 minutes — pip install pip-audit, add to CI
**Notes:** Run manually before every deployment: `pip audit`

---

## Deferred ADRs — Tier 3 (Before Paying Customers)

### ADR-010 — Pre-commit Hooks
**Status:** Deferred — implement before Stage 4
**Decision:** black + ruff + detect-secrets on every commit
**Trigger:** Before first paying customer
**Effort:** 30 minutes — .pre-commit-config.yaml + pre-commit install
**Notes:** detect-secrets prevents accidental API key commits.

---

### ADR-011 — Full Type Hints and mypy
**Status:** Deferred — implement before Stage 4
**Decision:** mypy --strict on all src/ files
**Trigger:** Before first paying customer
**Effort:** 2-3 hours
**Notes:** Run: `mypy --strict src/`

---

### ADR-012 — CHANGELOG.md
**Status:** Deferred — implement before Stage 4
**Decision:** Semantic versioning + changelog per release
**Trigger:** Before first paying customer
**Format:** Keep a Changelog (keepachangelog.com)

---

## Deferred ADRs — Tier 4 (Production Scale)

### ADR-013 — Dockerfile and Container Deployment
**Status:** Deferred — implement at Stage 5
**Decision:** Containerize for reproducible deployment everywhere
**Trigger:** Stage 5 Next.js rebuild begins

---

### ADR-014 — Redis Rate Limiting
**Status:** Deferred — implement when session rate limiting proves insufficient
**Decision:** IP-based rate limiting via Redis
**Trigger:** Abuse detected OR Stage 4 paying customers
**Notes:** ~$5/month on Railway or Redis Cloud free tier.

---

### ADR-015 — Health Check Endpoint
**Status:** Deferred — implement at Stage 5 with FastAPI backend
**Decision:** /health endpoint for load balancer and monitoring
**Trigger:** Stage 5 Next.js + FastAPI rebuild

---

## Template — Copy This for New Decisions

```markdown
## ADR-00X — [Short Title]
**Date:** [Month Year]
**Status:** Active | Deferred | Superseded by ADR-[NUMBER]

**Context:**
[What situation forced this decision]

**Decision:**
[What was chosen, in one clear sentence]

**Alternatives considered:**
- Option A — [why rejected]
- Option B — [why rejected]

**Reasoning:**
[Why this option won over the alternatives]

**Consequences:**
- ✅ What this gains
- ⚠️ What this costs or risks

**Upgrade trigger:** [Optional — what would cause you to revisit this]
```

---

*Version 1.0 — May 2026*
*Update this document whenever a significant architectural decision is made*
