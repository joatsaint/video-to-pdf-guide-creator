# SPEC.md
## Product Specification — Video-to-PDF-Guide-Creator

**Version:** 1.0
**Owner:** Randy Skiles
**Last Updated:** May 2026

---

## Product Summary

A web application that converts YouTube how-to video transcripts into
formatted, printable step-by-step guides using Claude AI.

**One sentence:** Paste a YouTube URL, get a printable how-to guide.

---

## Problem Statement

YouTube how-to videos are excellent for demonstrating processes but poor
for reference. Users must pause, rewind, and re-watch constantly. There
is no printable or saveable version of the instructions. The information
exists in the video but is locked in a format that requires a screen and
continuous attention to use.

**The specific pain:** A user watching a video on removing oil stains from
concrete cannot follow the steps, check the materials list, and monitor
timing simultaneously. A printed guide solves all three problems.

---

## Target Users

### Primary — DIY Consumer
- Age 30-65
- Homeowner, hobbyist, or DIY enthusiast
- Watches YouTube how-to videos for home repair, cooking, fitness, crafts
- Wants to follow instructions without a screen nearby
- Would print the guide or save it to their phone

### Secondary — Small Business Owner
- Runs a service business (plumber, electrician, HVAC, landscaper, coach)
- Has 10-100 YouTube tutorial videos
- Wants to convert them to guides for their website or customer handouts
- Willing to pay monthly for bulk conversion

### Tertiary — Content Creator
- YouTube creator with tutorial channel
- Wants to offer companion guides to their audience
- Drives traffic from YouTube to their website via the guide library

---

## MVP Feature Specification (Stage 1)

### Feature 1 — URL Input
**What:** Text input field accepting any YouTube URL format
**Accepted formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

**Validation:**
- Must be a YouTube URL — show error for other URLs
- Must have a transcript available — show helpful error if not

---

### Feature 2 — Guide Generation
**What:** Convert transcript to formatted step-by-step guide via Claude API

**Output format:**
```
## [Guide Title — inferred from video content]

### What You'll Need
- [Material or tool 1]
- [Material or tool 2]

### Time Required
[Estimated completion time]

### Steps
1. **[Step Name]**
   [2-3 sentence description of what to do]

2. **[Step Name]**
   [2-3 sentence description]

[All steps from video...]

### Tips & Warnings
- ⚠️ [Safety warning if applicable]
- 💡 [Pro tip]

### Summary
[One paragraph recap of the complete process]
```

**Quality requirements:**
- All steps from the video must be captured
- Steps must be in correct sequence
- Materials list must be complete
- Time estimate must be reasonable
- No hallucinated steps — only what's in the transcript

---

### Feature 3 — PDF Download
**What:** Download button generates and downloads a formatted PDF

**PDF requirements:**
- Letter size (8.5 x 11 inches)
- Clean, readable typography
- Numbered steps clearly formatted
- Materials as checkbox list (user can check off items)
- Footer: source YouTube URL + generation date
- No watermark on free tier (add in Stage 4 for branding)

---

### Feature 4 — Email to Self (Stage 1.5)
**What:** Input field + send button emails the guide to the user

**Behavior:**
- User enters email address
- Clicks "Email me this guide"
- Guide delivered as PDF attachment
- User added to email list (with clear opt-in language)
- Confirmation message shown

**Opt-in language:** "I'll also send you occasional tips on using AI tools
to get more out of online video content. Unsubscribe anytime."

---

## Error States

| Error | User Message |
|---|---|
| Invalid URL | "Please paste a valid YouTube URL (youtube.com or youtu.be)" |
| No transcript | "This video doesn't have a transcript. Try a different video." |
| Private video | "This video is private or unavailable." |
| API error | "Something went wrong generating your guide. Please try again." |
| Empty transcript | "This video's transcript appears to be empty." |
| Rate limit | "We're processing a lot of guides right now. Please try again in a minute." |

---

## UI Layout (Streamlit MVP)

```
┌─────────────────────────────────────────┐
│  🎬 Video-to-PDF-Guide-Creator          │
│  Convert any YouTube how-to into a      │
│  printable step-by-step guide           │
├─────────────────────────────────────────┤
│                                         │
│  YouTube URL:                           │
│  [________________________________]     │
│                                         │
│  [Generate Guide →]                     │
│                                         │
├─────────────────────────────────────────┤
│  ⏳ Fetching transcript...              │
│  ⏳ Generating your guide...            │
├─────────────────────────────────────────┤
│                                         │
│  ## How to Remove Oil Stains            │
│  ### What You'll Need                   │
│  - Oil remover solution                 │
│  ...                                    │
│                                         │
│  [📥 Download PDF]  [📧 Email to me]   │
│                                         │
└─────────────────────────────────────────┘
```

---

## Performance Requirements

| Metric | Target |
|---|---|
| Time to guide (fast video) | Under 15 seconds |
| Time to guide (long video) | Under 45 seconds |
| PDF generation | Under 3 seconds |
| Email delivery | Under 60 seconds |
| Uptime (Streamlit Cloud free) | Best effort |

---

## Pre-Launch Requirements

These items must be completed before the app is shared publicly:

**Privacy Policy (required)**
The app collects email addresses. A privacy policy is legally required
before public launch. Minimum content:
- What data is collected (email address)
- How it is used (guide delivery + optional newsletter)
- How to unsubscribe or request deletion
- No data is sold to third parties

Even a simple one-page policy hosted on the Streamlit app satisfies
this requirement. Streamlit Cloud may enforce this before allowing
a public URL. Do not launch publicly without it.

**Rate Limiting (required before wide promotion)**
One user making repeated API calls could run up significant costs.
Add per-IP or per-session rate limiting before promoting the app
beyond the immediate portfolio audience. Limit: 10 guides per IP
per day on free tier. Implemented in Stage 2.

---

## Out of Scope for MVP

- User accounts or login
- Guide history / saved guides
- Non-YouTube video sources
- Video upload
- Multiple languages
- Mobile app
- Payment processing
- Admin dashboard
- Analytics beyond basic usage logging

---

## Success Metrics

**Stage 1 success:**
- App is deployed and accessible at a public URL
- At least 10 guides successfully generated in testing
- PDF download works on all tested URLs
- Zero unhandled exceptions visible to users

**Stage 2 success:**
- First email subscriber via in-app capture
- 50+ guides generated by real users

---

*Version 1.0 — May 2026*
*This spec is the source of truth for what gets built in Stage 1*
