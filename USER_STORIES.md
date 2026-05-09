# USER_STORIES.md
## User Stories — Video-to-PDF-Guide-Creator

**Version:** 1.0
**Format:** As a [user type], I want to [action] so that [outcome]
**Owner:** Randy Skiles
**Last Updated:** May 2026

---

## About This Document

User stories are written in BA (Business Analyst) format to document
what the system must do from the user's perspective — not how it does it.
Each story has acceptance criteria that define when the story is complete.

This document is a portfolio artifact demonstrating requirements
documentation skills for AI/BA roles.

---

## Epic 1 — Guide Generation (MVP)

### US-001 — Generate Guide from YouTube URL
**As a** DIY homeowner,
**I want to** paste a YouTube URL and receive a formatted step-by-step guide,
**So that** I can follow the instructions without rewinding the video.

**Acceptance Criteria:**
- [ ] User can paste any YouTube URL format (youtube.com/watch, youtu.be, shorts)
- [ ] System fetches transcript within 10 seconds for videos under 20 minutes
- [ ] Guide is displayed on screen within 30 seconds of clicking Generate
- [ ] Guide includes: title, materials list, time estimate, numbered steps, tips
- [ ] All steps from the video are captured in correct sequence
- [ ] No steps are hallucinated — only content from the transcript appears

**Priority:** Must Have
**Stage:** 1

---

### US-002 — Handle Missing Transcript Gracefully
**As a** user who pastes a URL for a video without captions,
**I want to** receive a helpful error message,
**So that** I understand why the guide cannot be generated and what to do instead.

**Acceptance Criteria:**
- [ ] Error message is plain English — no technical jargon or stack traces
- [ ] Message explains the problem specifically (no transcript vs. private video vs. invalid URL)
- [ ] Message suggests a next step ("Try a video with captions enabled")
- [ ] User can immediately try a different URL without refreshing

**Priority:** Must Have
**Stage:** 1

---

### US-003 — Download Guide as PDF
**As a** user who has generated a guide,
**I want to** download it as a PDF,
**So that** I can print it and use it without a screen nearby.

**Acceptance Criteria:**
- [ ] Download button visible immediately after guide is generated
- [ ] PDF downloads within 3 seconds of clicking
- [ ] PDF is formatted cleanly — readable typography, numbered steps
- [ ] Materials list formatted as checkboxes
- [ ] Footer includes source YouTube URL and generation date
- [ ] PDF filename is descriptive (e.g., `how-to-remove-oil-stains-guide.pdf`)

**Priority:** Must Have
**Stage:** 1

---

## Epic 2 — Email Capture

### US-004 — Email Guide to Self
**As a** user who wants to save the guide for later,
**I want to** enter my email address and receive the guide as an attachment,
**So that** I have it available on my phone or can forward it to someone else.

**Acceptance Criteria:**
- [ ] Email input field is visible after guide is generated
- [ ] Email field validates format before sending
- [ ] Guide arrives as PDF attachment within 60 seconds
- [ ] Confirmation message shown immediately after clicking Send
- [ ] Opt-in language is clear and honest
- [ ] Unsubscribe is easy and immediate

**Priority:** Should Have
**Stage:** 1.5

---

### US-005 — Opt Into Updates
**As a** user who found the tool useful,
**I want to** opt in to receive tips about using AI tools,
**So that** I can learn more without having to seek it out myself.

**Acceptance Criteria:**
- [ ] Opt-in checkbox is pre-unchecked (not pre-checked)
- [ ] Opt-in language is specific about what emails will be sent
- [ ] Opt-in is separate from guide delivery — guide arrives regardless
- [ ] Subscriber is tagged in email system as coming from this tool

**Priority:** Should Have
**Stage:** 1.5

---

## Epic 3 — Guide Library

### US-006 — Browse Public Guide Library
**As a** user looking for how-to guides,
**I want to** browse a library of guides created by other users,
**So that** I can find instructions without needing to find a specific video first.

**Acceptance Criteria:**
- [ ] Library is searchable by keyword
- [ ] Guides are organized by category (DIY, cooking, fitness, tech, etc.)
- [ ] Each guide shows title, category, source video title, date generated
- [ ] Guides are publicly accessible without login
- [ ] Source YouTube video is linked from each guide

**Priority:** Should Have
**Stage:** 3

---

### US-007 — Share Guide to Library
**As a** user who generated a useful guide,
**I want to** share it to the public library,
**So that** others can benefit from it without generating it themselves.

**Acceptance Criteria:**
- [ ] Share option is opt-in — never automatic
- [ ] User sees preview of how guide will appear in library before sharing
- [ ] Shared guides are attributed to "Community" not individual user
- [ ] User can request removal of their shared guide

**Priority:** Could Have
**Stage:** 3

---

## Epic 4 — Small Business Features

### US-008 — Bulk Convert Video Library
**As a** small business owner with multiple tutorial videos,
**I want to** convert my entire YouTube playlist to guides in one operation,
**So that** I can add guides to my website without processing each video individually.

**Acceptance Criteria:**
- [ ] User can paste a YouTube playlist URL
- [ ] System converts all videos in the playlist
- [ ] Progress shown for each video
- [ ] Failed conversions clearly identified with reason
- [ ] All guides downloadable as a ZIP file
- [ ] Feature available on paid plan only

**Priority:** Should Have
**Stage:** 4

---

### US-009 — Add Business Branding to Guides
**As a** small business owner,
**I want to** add my logo and contact information to generated guides,
**So that** customers who print them see my business information.

**Acceptance Criteria:**
- [ ] Logo upload (PNG, JPG, max 2MB)
- [ ] Business name and contact info fields
- [ ] Preview shows branded guide before download
- [ ] Branding appears in PDF header and footer
- [ ] Feature available on Business plan only

**Priority:** Should Have
**Stage:** 4

---

## Story Map Summary

| Epic | Stories | Stage | Status |
|---|---|---|---|
| Guide Generation | US-001, US-002, US-003 | 1 | IN PROGRESS |
| Email Capture | US-004, US-005 | 1.5 | NOT STARTED |
| Guide Library | US-006, US-007 | 3 | NOT STARTED |
| Small Business | US-008, US-009 | 4 | NOT STARTED |

---

*Version 1.0 — May 2026*
*Add new stories as features are identified*
*Update acceptance criteria as implementation reveals edge cases*
