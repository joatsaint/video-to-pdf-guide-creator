# PROMPT_ARCHITECTURE.md
## AI-Assisted Development Methodology — Video-to-PDF-Guide-Creator

**Version:** 1.0
**Owner:** Randy Skiles
**Last Updated:** May 2026

---

## Overview

This document explains how Claude AI was used to build this project —
the prompting patterns, constraints, and validation strategies that
produced reliable, production-grade output.

This is a portfolio artifact demonstrating enterprise-level AI-assisted
development capability. For the companion document from the related
enterprise-ai-pipeline project, see:
github.com/joatsaint/enterprise-ai-pipeline/blob/master/PROMPT_ARCHITECTURE.md

---

## Core Methodology: Spec-First AI Development

The same methodology used in enterprise-ai-pipeline is applied here:

```
1. Write the spec in CLAUDE.md (human)
2. Write the user story in USER_STORIES.md (human)
3. Direct Claude to build against the spec (AI-assisted)
4. Validate output against acceptance criteria (human)
5. Document the architectural decision (human)
6. Merge only when tests pass (CI/CD enforced)
```

No module is built without a spec. No spec is written without a user story.
No code is merged without passing tests.

---

## The Core Product Prompt

The guide generation prompt lives in `prompts/guide_prompt.txt`.
It is versioned separately from code (see ADR-004).

**Design principles behind the prompt:**

**1. Format specification over instruction**
Rather than telling Claude "write a good guide," the prompt specifies
the exact output format — section headers, step numbering, materials
list structure. This produces consistent, parseable output.

**2. Boundary enforcement**
The prompt explicitly instructs Claude not to add information not
present in the transcript. This prevents hallucination — a critical
requirement when users will follow these guides in real situations
(home repair, cooking, etc.).

**3. Inference permission**
The prompt permits Claude to infer a reasonable title and time estimate
from context — these are not always explicit in transcripts. All other
content must come from the transcript directly.

**4. Tone calibration**
The prompt specifies plain, actionable language. No motivational
padding. No "great question!" filler. Direct instructions only.

---

## Session Structure for Development

Every Claude Code session follows this protocol:

```
Session open:
1. Read CLAUDE.md — architecture rules and module specs
2. Read DECISIONS.md — all active ADRs
3. State one specific deliverable for this session

During session:
4. Build against spec — not against assumptions
5. Handle all failure modes before considering done
6. Write tests alongside code — not after

Session close:
7. Update CLAUDE.md if architecture changed
8. Add ADR if significant decision was made
9. Confirm tests pass before ending session
```

---

## Key Prompting Patterns

### For the transcript fetcher:
```
Build transcript_fetcher.py to this spec: [spec from CLAUDE.md]
It must handle these exact failure modes and return these exact errors.
Test with these URL formats: [list]
Do not proceed until all failure modes are handled.
```

### For the guide generator:
```
Build guide_generator.py with ONE constraint above all others:
All Claude API calls live in this file only.
No other file may import anthropic or make LLM calls.
The function signature is: generate_guide(transcript: str) -> str
Return the guide text only — no metadata, no wrapper objects.
```

### For the PDF creator:
```
Build pdf_creator.py that accepts guide text (string) and returns
PDF bytes — not a file path, not a saved file. Bytes only.
The Streamlit download button will handle the rest.
Use ReportLab. Letter size. Clean typography. Checkbox materials list.
```

---

## What This Demonstrates

1. **Requirements-first thinking** — USER_STORIES.md written before code
2. **Constraint-driven prompting** — model-agnostic architecture from day one
3. **Prompt as artifact** — versioned prompt file, not inline string
4. **Hallucination prevention** — explicit transcript-only constraint
5. **Cost governance** — Haiku selected with documented reasoning
6. **Failure mode discipline** — all error states specified before building

---

*Version 1.0 — May 2026*
*Update when new modules are built or prompting patterns evolve*
