const { useState, useEffect, useRef, useMemo, useCallback } = React;

/* ============================================================
   TWEAK DEFAULTS — host-persisted
   ============================================================ */
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "heroLayout": "centered",
  "accent": "#b794ff",
  "showBlobs": true
}/*EDITMODE-END*/;

/* ============================================================
   SAMPLE DATA — what a finished guide looks like
   ============================================================ */
const SAMPLE_GUIDES = {
  default: {
    sourceTitle: "How to Make a Perfect Sourdough Loaf at Home",
    sourceChannel: "Bread by Hand",
    duration: "18:42",
    thumbnail: "sourdough",
    summary: "A complete walkthrough of mixing, bulk ferment, shaping, cold proof, and baking sourdough in a Dutch oven. Best for beginners with a mature starter.",
    tools: ["Active sourdough starter", "Dutch oven", "Bench scraper", "Banneton or bowl + tea towel", "Kitchen scale"],
    steps: [
      { title: "Feed your starter the night before", body: "Mix 50g starter, 50g flour, 50g water. Cover loosely and leave at room temperature for 8-12 hours until doubled and bubbly.", time: "12h ahead" },
      { title: "Mix the dough", body: "Combine 500g bread flour with 350g water. Rest 30 min (autolyse). Add 100g active starter and 10g salt. Squeeze together until incorporated.", time: "9:00 AM" },
      { title: "Bulk ferment with stretch & folds", body: "Every 30 min for the first 2 hours, perform a set of 4 stretch-and-folds. Then let rest until dough has risen ~50% and shows bubbles on the surface.", time: "4-6 hours" },
      { title: "Pre-shape and bench rest", body: "Turn dough onto a lightly floured surface. Shape into a loose round using a bench scraper. Cover and rest 20 minutes.", time: "20 min" },
      { title: "Final shape and cold proof", body: "Shape tightly into a boule or batard. Place seam-side up in a floured banneton. Cover and refrigerate overnight.", time: "8-16 hours" },
      { title: "Bake in a Dutch oven", body: "Preheat Dutch oven at 500°F for 1 hour. Score the dough, transfer in, cover and bake 20 min. Remove lid, drop to 450°F, bake 20-25 min more until deep brown.", time: "45 min" }
    ],
    tips: [
      "If dough feels slack, add 25g less water next time.",
      "Score with a sharp blade at a shallow angle for the best ear.",
      "Cool fully (1+ hour) before slicing or the crumb will be gummy."
    ]
  }
};

/* ============================================================
   UTILITIES
   ============================================================ */
function applyAccent(hex) {
  const root = document.documentElement;
  root.style.setProperty("--accent", hex);
  root.style.setProperty("--accent-strong", `color-mix(in oklch, ${hex}, black 12%)`);
  root.style.setProperty("--accent-deep",   `color-mix(in oklch, ${hex}, black 38%)`);
}

function isValidYouTubeUrl(url) {
  if (!url) return false;
  const patterns = [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]{11}/,
    /^https?:\/\/youtu\.be\/[\w-]{11}/,
    /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]{11}/
  ];
  return patterns.some(p => p.test(url.trim()));
}

/* ============================================================
   SVG ICONS
   ============================================================ */
const Icon = {
  Arrow: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>,
  Play: (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><polygon points="7 4 20 12 7 20 7 4"/></svg>,
  Copy: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>,
  Download: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>,
  Mail: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="5" width="18" height="14" rx="2"/><polyline points="3 7 12 13 21 7"/></svg>,
  Check: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" {...p}><polyline points="20 6 9 17 4 12"/></svg>,
  Sparkle: (p) => <svg viewBox="0 0 24 24" fill="currentColor" {...p}><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2z"/></svg>,
  Close: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  Reload: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
  Doc: (p) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
};

/* ============================================================
   BLOB CLUSTER — CSS-only "3D" gradient blobs
   ============================================================ */
function BlobCluster({ size = 1, animated = true, opacity = 1 }) {
  return (
    <div className="blob-wrap" style={{ "--bs": size, opacity }}>
      <div className={`blob b1 ${animated ? "float-a" : ""}`}></div>
      <div className={`blob b2 ${animated ? "float-b" : ""}`}></div>
      <div className={`blob b3 ${animated ? "float-c" : ""}`}></div>
      <div className={`blob b4 ${animated ? "float-a" : ""}`}></div>
      <div className={`blob b5 star ${animated ? "spin" : ""}`}>
        <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="starGrad" cx="35%" cy="30%" r="70%">
              <stop offset="0%" stopColor="oklch(0.95 0.05 195)" />
              <stop offset="50%" stopColor="oklch(0.75 0.18 295)" />
              <stop offset="100%" stopColor="oklch(0.4 0.22 295)" />
            </radialGradient>
          </defs>
          <path d="M50 5 Q 55 35 60 40 Q 90 45 90 50 Q 60 55 55 60 Q 50 90 50 95 Q 45 60 40 55 Q 10 50 5 50 Q 40 45 45 40 Q 50 10 50 5 Z" fill="url(#starGrad)" />
        </svg>
      </div>
    </div>
  );
}

const BLOB_CSS = `
.blob-wrap {
  position: relative;
  width: calc(420px * var(--bs, 1));
  height: calc(280px * var(--bs, 1));
  pointer-events: none;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(0.5px);
}
.blob.b1 {
  width: 38%; height: 55%;
  top: 18%; left: 12%;
  background: radial-gradient(ellipse 80% 80% at 30% 25%, oklch(0.95 0.06 195), oklch(0.75 0.12 200) 50%, oklch(0.4 0.18 295) 100%);
  border-radius: 50% 55% 60% 50%;
  box-shadow: 0 30px 60px -20px oklch(0.3 0.2 295 / 0.6);
}
.blob.b2 {
  width: 32%; height: 48%;
  top: 28%; left: 38%;
  background: radial-gradient(ellipse 70% 70% at 35% 30%, oklch(0.9 0.08 195), oklch(0.7 0.14 220) 55%, oklch(0.5 0.22 300) 100%);
  border-radius: 60% 50% 55% 55%;
  box-shadow: 0 40px 80px -20px oklch(0.3 0.22 295 / 0.6);
}
.blob.b3 {
  width: 30%; height: 44%;
  top: 38%; left: 25%;
  background: radial-gradient(ellipse 75% 75% at 40% 35%, oklch(0.88 0.08 320), oklch(0.65 0.2 305) 55%, oklch(0.35 0.22 290) 100%);
  border-radius: 55% 60% 50% 55%;
  box-shadow: 0 30px 70px -15px oklch(0.3 0.22 295 / 0.7);
}
.blob.b4 {
  width: 18%; height: 27%;
  top: 12%; left: 5%;
  background: radial-gradient(ellipse 70% 70% at 35% 30%, oklch(0.92 0.06 195), oklch(0.7 0.14 250) 60%, oklch(0.45 0.22 295) 100%);
  border-radius: 50% 55% 50% 55%;
  box-shadow: 0 20px 40px -10px oklch(0.3 0.22 295 / 0.6);
}
.blob.b5.star {
  position: absolute;
  width: 28%; height: 40%;
  top: 5%; left: 58%;
  filter: drop-shadow(0 30px 40px oklch(0.3 0.22 295 / 0.7));
}
.float-a { animation: floatA 8s ease-in-out infinite; }
.float-b { animation: floatB 10s ease-in-out infinite; }
.float-c { animation: floatC 9s ease-in-out infinite; }
.spin    { animation: spinSlow 22s linear infinite; }
@keyframes floatA { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-12px) } }
@keyframes floatB { 0%,100% { transform: translateY(0) translateX(0) } 50% { transform: translateY(-8px) translateX(6px) } }
@keyframes floatC { 0%,100% { transform: translateY(0) } 50% { transform: translateY(10px) } }
@keyframes spinSlow { from { transform: rotate(0) } to { transform: rotate(360deg) } }
`;

/* ============================================================
   HEADER
   ============================================================ */
function Header({ onSample, onReset, hasResult }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <svg viewBox="0 0 32 32" width="22" height="22">
            <defs>
              <radialGradient id="bm" cx="30%" cy="30%" r="80%">
                <stop offset="0%" stopColor="oklch(0.95 0.08 195)"/>
                <stop offset="60%" stopColor="oklch(0.75 0.18 300)"/>
                <stop offset="100%" stopColor="oklch(0.4 0.22 295)"/>
              </radialGradient>
            </defs>
            <path d="M16 2 L 19 13 L 30 16 L 19 19 L 16 30 L 13 19 L 2 16 L 13 13 Z" fill="url(#bm)"/>
          </svg>
        </div>
        <div className="brand-text">
          <span>video</span>
          <span className="dot">→</span>
          <span>pdf</span>
          <span className="dot">·</span>
          <span className="brand-faint">guide creator</span>
        </div>
      </div>
      <nav className="topnav">
        <button className="link-btn" onClick={onSample}>Try a sample</button>
        <a className="link-btn" href="#how">How it works</a>
        {hasResult && <button className="link-btn" onClick={onReset}>New guide</button>}
      </nav>
    </header>
  );
}

/* ============================================================
   URL INPUT — shared across hero variants
   ============================================================ */
function UrlInput({ value, onChange, onSubmit, size = "md", error, autofocus }) {
  const ref = useRef(null);
  useEffect(() => { if (autofocus && ref.current) ref.current.focus(); }, [autofocus]);
  const valid = isValidYouTubeUrl(value);
  return (
    <form
      className={`url-form ${size} ${error ? "has-error" : ""}`}
      onSubmit={(e) => { e.preventDefault(); if (valid) onSubmit(); }}
    >
      <div className="url-field">
        <span className="url-prefix">youtube.com/</span>
        <input
          ref={ref}
          type="text"
          placeholder="watch?v=… or paste any video link"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          spellCheck="false"
          autoComplete="off"
        />
        <button
          type="submit"
          className={`url-go ${valid ? "ready" : ""}`}
          disabled={!valid}
          aria-label="Generate guide"
        >
          <span className="go-text">Generate</span>
          <Icon.Arrow width="16" height="16"/>
        </button>
      </div>
      {error && <div className="url-error">{error}</div>}
    </form>
  );
}

/* ============================================================
   HERO LAYOUTS
   ============================================================ */
function HeroCentered({ url, setUrl, onSubmit, error, showBlobs }) {
  return (
    <section className="hero centered">
      {showBlobs && (
        <div className="hero-blobs">
          <BlobCluster size={1.1} />
        </div>
      )}
      <div className="hero-eyebrow">
        <span className="eyebrow-dot"></span>
        <span>YouTube → printable how-to guide</span>
      </div>
      <h1 className="display">
        Turn any video<br/>
        <span className="accent-grad">into a guide.</span>
      </h1>
      <p className="hero-sub">
        Paste a YouTube URL. We pull the transcript, distill the steps,<br/>
        and hand you a clean printable PDF in seconds.
      </p>
      <div className="hero-input-wrap">
        <UrlInput value={url} onChange={setUrl} onSubmit={onSubmit} size="lg" error={error} />
      </div>
      <div className="hero-trust">
        <span>No login</span><span className="sep">·</span>
        <span>No ads</span><span className="sep">·</span>
        <span>Copy · PDF · Email</span>
      </div>
    </section>
  );
}

function HeroSplit({ url, setUrl, onSubmit, error, showBlobs }) {
  return (
    <section className="hero split">
      <div className="split-left">
        <div className="hero-eyebrow">
          <span className="eyebrow-dot"></span>
          <span>v1.0 · Free while in beta</span>
        </div>
        <h1 className="display split-display">
          Watch less.<br/>
          <span className="accent-grad">Learn faster.</span>
        </h1>
        <p className="hero-sub left">
          Drop a YouTube link, get a step-by-step PDF you can save,
          print, or email to yourself in one click.
        </p>
        <div className="hero-input-wrap left">
          <UrlInput value={url} onChange={setUrl} onSubmit={onSubmit} size="md" error={error} />
        </div>
        <div className="hero-trust left">
          <span>✦ Works with any video that has captions</span>
        </div>
      </div>
      <div className="split-right">
        {showBlobs && <BlobCluster size={1.4} />}
        <div className="preview-stack">
          <div className="preview-card pc-1">
            <div className="pc-bar"><span></span><span></span><span></span></div>
            <div className="pc-title">Step 03 — Bulk ferment</div>
            <div className="pc-line"></div>
            <div className="pc-line w70"></div>
            <div className="pc-line w50"></div>
          </div>
          <div className="preview-card pc-2">
            <div className="pc-bar"><span></span><span></span><span></span></div>
            <div className="pc-title">Step 02 — Mix dough</div>
            <div className="pc-line"></div>
            <div className="pc-line w80"></div>
          </div>
        </div>
      </div>
    </section>
  );
}

function HeroDock({ url, setUrl, onSubmit, error, showBlobs }) {
  return (
    <section className="hero dock">
      <div className="dock-top">
        <div className="hero-eyebrow center">
          <span className="eyebrow-dot"></span>
          <span>For YouTube tutorials, lectures, recipes & how-tos</span>
        </div>
        <h1 className="display dock-display">
          A printable guide<br/>
          for <em>every</em> <span className="accent-grad">video.</span>
        </h1>
      </div>
      {showBlobs && (
        <div className="dock-blobs">
          <BlobCluster size={0.9} opacity={0.85} />
        </div>
      )}
      <div className="dock-bottom">
        <UrlInput value={url} onChange={setUrl} onSubmit={onSubmit} size="lg" error={error} autofocus={false} />
        <div className="dock-feature-row">
          <FeatureChip label="Transcript" sub="auto-fetched" />
          <FeatureChip label="Step extraction" sub="AI structured" />
          <FeatureChip label="PDF export" sub="print-ready" />
          <FeatureChip label="Email yourself" sub="one tap" />
        </div>
      </div>
    </section>
  );
}

function FeatureChip({ label, sub }) {
  return (
    <div className="feat-chip">
      <div className="feat-label">{label}</div>
      <div className="feat-sub">{sub}</div>
    </div>
  );
}

/* ============================================================
   PROCESSING STATE
   ============================================================ */
const PROCESS_STEPS = [
  { id: 0, label: "Fetching video metadata", detail: "Reading title, channel, duration" },
  { id: 1, label: "Downloading transcript", detail: "Pulling captions track" },
  { id: 2, label: "Analyzing content", detail: "Identifying steps & sequence" },
  { id: 3, label: "Structuring the guide", detail: "Titles, descriptions, tips" },
  { id: 4, label: "Rendering PDF preview", detail: "Typesetting your guide" }
];

function Processing({ url }) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => {
      setActive((a) => (a < PROCESS_STEPS.length - 1 ? a + 1 : a));
    }, 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <section className="processing">
      <div className="proc-blobs">
        <BlobCluster size={0.8} opacity={0.6} />
      </div>
      <div className="proc-inner">
        <div className="proc-eyebrow">
          <span className="pulse"></span>
          <span>Working on your guide</span>
        </div>
        <h2 className="proc-title">Reading the video…</h2>
        <div className="proc-url">{url || "youtube.com/watch?v=demo"}</div>
        <ul className="proc-steps">
          {PROCESS_STEPS.map((s, i) => {
            const state = i < active ? "done" : i === active ? "active" : "pending";
            return (
              <li key={s.id} className={`ps ${state}`}>
                <div className="ps-marker">
                  {state === "done" ? <Icon.Check width="12" height="12"/> :
                   state === "active" ? <span className="spinner"></span> : <span className="ps-dot"></span>}
                </div>
                <div className="ps-body">
                  <div className="ps-label">{s.label}</div>
                  <div className="ps-detail">{s.detail}</div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

/* ============================================================
   GUIDE RESULT
   ============================================================ */
function GuideResult({ guide, url, onReset }) {
  const [copied, setCopied] = useState(false);
  const [showEmail, setShowEmail] = useState(false);
  const [emailVal, setEmailVal] = useState("");
  const [emailSent, setEmailSent] = useState(false);

  const guideText = useMemo(() => {
    let t = `${guide.sourceTitle}\nSource: ${guide.sourceChannel} · ${guide.duration}\n\n${guide.summary}\n\n`;
    t += `WHAT YOU'LL NEED\n`;
    guide.tools.forEach((x) => { t += `- ${x}\n`; });
    t += `\nSTEPS\n`;
    guide.steps.forEach((s, i) => {
      t += `\n${String(i+1).padStart(2,'0')}. ${s.title}${s.time ? `  (${s.time})` : ""}\n   ${s.body}\n`;
    });
    t += `\nTIPS\n`;
    guide.tips.forEach((x) => { t += `- ${x}\n`; });
    t += `\nGenerated from ${url || "youtube.com"} by video-to-pdf-guide-creator`;
    return t;
  }, [guide, url]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(guideText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) { console.error(e); }
  };

  const handlePdf = () => {
    window.print();
  };

  const handleEmail = () => {
    if (!emailVal) return;
    setEmailSent(true);
    setTimeout(() => {
      const subject = encodeURIComponent(`Your guide: ${guide.sourceTitle}`);
      const body = encodeURIComponent(guideText);
      window.location.href = `mailto:${emailVal}?subject=${subject}&body=${body}`;
      setEmailSent(false);
      setShowEmail(false);
      setEmailVal("");
    }, 800);
  };

  return (
    <section className="result">
      {/* Header strip with actions */}
      <div className="result-bar no-print">
        <div className="result-bar-left">
          <button className="ghost-btn" onClick={onReset}>
            <Icon.Reload width="14" height="14"/>
            <span>New guide</span>
          </button>
        </div>
        <div className="result-bar-right">
          <button className={`pill-btn ${copied ? "ok" : ""}`} onClick={handleCopy}>
            {copied ? <Icon.Check width="14" height="14"/> : <Icon.Copy width="14" height="14"/>}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>
          <button className="pill-btn" onClick={() => setShowEmail(true)}>
            <Icon.Mail width="14" height="14"/>
            <span>Email</span>
          </button>
          <button className="pill-btn primary" onClick={handlePdf}>
            <Icon.Download width="14" height="14"/>
            <span>Save as PDF</span>
          </button>
        </div>
      </div>

      {/* The guide document */}
      <article className="guide-doc">
        <header className="doc-head">
          <div className="doc-meta">
            <div className="doc-source">
              <Icon.Play width="11" height="11"/>
              <span>{guide.sourceChannel}</span>
              <span className="sep">·</span>
              <span>{guide.duration}</span>
            </div>
            <div className="doc-stamp">
              <Icon.Sparkle width="11" height="11"/>
              <span>AI-distilled guide</span>
            </div>
          </div>
          <h1 className="doc-title">{guide.sourceTitle}</h1>
          <p className="doc-summary">{guide.summary}</p>
        </header>

        <div className="doc-cols">
          <aside className="doc-side">
            <div className="doc-card">
              <div className="doc-card-label">What you'll need</div>
              <ul className="tool-list">
                {guide.tools.map((t, i) => <li key={i}>{t}</li>)}
              </ul>
            </div>
            <div className="doc-card tips-card">
              <div className="doc-card-label">Tips & notes</div>
              <ul className="tips-list">
                {guide.tips.map((t, i) => <li key={i}>{t}</li>)}
              </ul>
            </div>
            <div className="doc-source-card">
              <div className="src-thumb">
                <div className="src-thumb-inner">
                  <Icon.Play width="22" height="22"/>
                </div>
              </div>
              <div className="src-meta">
                <div className="src-label">Source video</div>
                <div className="src-url">{url || "youtu.be/sample"}</div>
              </div>
            </div>
          </aside>

          <main className="doc-main">
            <div className="steps-header">
              <span className="steps-count">{guide.steps.length} steps</span>
              <span className="steps-line"></span>
            </div>
            <ol className="step-list">
              {guide.steps.map((s, i) => (
                <li key={i} className="step">
                  <div className="step-num">{String(i+1).padStart(2,'0')}</div>
                  <div className="step-body">
                    <div className="step-headline">
                      <h3 className="step-title">{s.title}</h3>
                      {s.time && <span className="step-time">{s.time}</span>}
                    </div>
                    <p className="step-text">{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="doc-foot">
              <Icon.Doc width="12" height="12"/>
              <span>Generated by video-to-pdf-guide-creator</span>
            </div>
          </main>
        </div>
      </article>

      {/* Email modal */}
      {showEmail && (
        <div className="modal-shroud no-print" onClick={() => setShowEmail(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowEmail(false)}><Icon.Close width="16" height="16"/></button>
            <div className="modal-eyebrow">
              <Icon.Mail width="14" height="14"/>
              <span>Email this guide to yourself</span>
            </div>
            <h3 className="modal-title">Where should we send it?</h3>
            <p className="modal-sub">We'll open your mail client with the guide pre-filled. Nothing is sent from our server.</p>
            <div className="modal-form">
              <input
                type="email"
                placeholder="you@email.com"
                value={emailVal}
                onChange={(e) => setEmailVal(e.target.value)}
                autoFocus
              />
              <button className="pill-btn primary lg" disabled={!emailVal || emailSent} onClick={handleEmail}>
                {emailSent ? "Opening…" : "Send"}
                {!emailSent && <Icon.Arrow width="14" height="14"/>}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

/* ============================================================
   "HOW IT WORKS" — small footer strip on idle
   ============================================================ */
function HowItWorks() {
  const steps = [
    { n: "01", t: "Paste a link", b: "Any YouTube video with captions." },
    { n: "02", t: "We read the transcript", b: "And distill it into clear steps." },
    { n: "03", t: "You get a PDF guide", b: "Copy, save, or email it to yourself." }
  ];
  return (
    <section id="how" className="how">
      <div className="how-rule"></div>
      <div className="how-head">
        <h2 className="how-title">How it works</h2>
        <span className="how-meta">Free during beta · No login</span>
      </div>
      <div className="how-grid">
        {steps.map((s) => (
          <div key={s.n} className="how-cell">
            <div className="how-num">{s.n}</div>
            <div className="how-t">{s.t}</div>
            <div className="how-b">{s.b}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ============================================================
   APP
   ============================================================ */
function App() {
  const [tweaks, setTweaks] = useTweaks(TWEAK_DEFAULTS);
  const [phase, setPhase] = useState("idle"); // idle | processing | ready
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [guide, setGuide] = useState(null);

  useEffect(() => { applyAccent(tweaks.accent); }, [tweaks.accent]);

  const start = useCallback(() => {
    if (!isValidYouTubeUrl(url)) {
      setError("That doesn't look like a YouTube link.");
      return;
    }
    setError("");
    setPhase("processing");
    setTimeout(() => {
      setGuide(SAMPLE_GUIDES.default);
      setPhase("ready");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 5400);
  }, [url]);

  const startSample = useCallback(() => {
    setUrl("https://youtube.com/watch?v=sample-sourdough");
    setError("");
    setPhase("processing");
    setTimeout(() => {
      setGuide(SAMPLE_GUIDES.default);
      setPhase("ready");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 5400);
  }, []);

  const reset = useCallback(() => {
    setPhase("idle");
    setUrl("");
    setGuide(null);
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="app">
      <Header onSample={startSample} onReset={reset} hasResult={phase === "ready"} />

      <main className="stage">
        {phase === "idle" && (
          <>
            {tweaks.heroLayout === "centered" && <HeroCentered url={url} setUrl={setUrl} onSubmit={start} error={error} showBlobs={tweaks.showBlobs} />}
            {tweaks.heroLayout === "split"    && <HeroSplit    url={url} setUrl={setUrl} onSubmit={start} error={error} showBlobs={tweaks.showBlobs} />}
            {tweaks.heroLayout === "dock"     && <HeroDock     url={url} setUrl={setUrl} onSubmit={start} error={error} showBlobs={tweaks.showBlobs} />}
            <HowItWorks />
          </>
        )}
        {phase === "processing" && <Processing url={url} />}
        {phase === "ready" && guide && <GuideResult guide={guide} url={url} onReset={reset} />}
      </main>

      <footer className="footer no-print">
        <div className="ft-l">© 2026 · video-to-pdf-guide-creator</div>
        <div className="ft-r">
          <span>Streamlit hosted</span>
          <span className="sep">·</span>
          <a href="#" onClick={(e) => e.preventDefault()}>Privacy</a>
          <span className="sep">·</span>
          <a href="#" onClick={(e) => e.preventDefault()}>GitHub</a>
        </div>
      </footer>

      <TweaksPanel title="Tweaks">
        <TweakSection title="Hero layout">
          <TweakSelect
            label="Variant"
            value={tweaks.heroLayout}
            options={[
              { value: "centered", label: "Centered Spotlight" },
              { value: "split",    label: "Split Console" },
              { value: "dock",     label: "Bottom Dock" }
            ]}
            onChange={(v) => setTweaks("heroLayout", v)}
          />
          <TweakToggle
            label="Show 3D blob shapes"
            value={tweaks.showBlobs}
            onChange={(v) => setTweaks("showBlobs", v)}
          />
        </TweakSection>
        <TweakSection title="Accent">
          <TweakColor
            label="Accent hue"
            value={tweaks.accent}
            options={["#b794ff", "#8a7fff", "#7dd3fc", "#fb7185"]}
            onChange={(v) => setTweaks("accent", v)}
          />
        </TweakSection>
        <TweakSection title="Try it">
          <TweakButton label="Run sample guide" onClick={startSample} />
          <TweakButton label="Reset to landing" onClick={reset} />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

/* ============================================================
   STYLES
   ============================================================ */
const STYLES = `
${BLOB_CSS}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ---------- Header ---------- */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 48px;
  position: relative;
  z-index: 5;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-mark {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
}
.brand-text {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
  display: flex; gap: 6px; align-items: baseline;
}
.brand-faint { color: var(--muted); font-weight: 500; }
.brand-text .dot { color: var(--muted); }

.topnav { display: flex; gap: 24px; align-items: center; }
.link-btn {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--fg-dim);
  letter-spacing: -0.005em;
  text-decoration: none;
  transition: color 0.15s;
}
.link-btn:hover { color: var(--fg); }

/* ---------- Hero shared ---------- */
.stage {
  flex: 1;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 48px 80px;
  position: relative;
}
.hero { position: relative; }

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-dim);
  padding: 6px 12px 6px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: oklch(1 0 0 / 0.015);
}
.hero-eyebrow.center { justify-content: center; }
.eyebrow-dot {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.5 } }

.display {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: clamp(56px, 9vw, 124px);
  line-height: 0.95;
  letter-spacing: -0.045em;
  margin: 0;
  text-wrap: balance;
}
.accent-grad {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 60%, var(--accent-deep) 110%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.display em {
  font-style: italic;
  font-weight: 600;
  color: var(--fg-dim);
}
.hero-sub {
  font-size: 17px;
  color: var(--fg-dim);
  line-height: 1.55;
  max-width: 540px;
  margin: 20px auto 36px;
  text-align: center;
  text-wrap: pretty;
}
.hero-sub.left { margin-left: 0; margin-right: 0; text-align: left; max-width: 460px; }

.hero-trust {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.04em;
  color: var(--muted);
}
.hero-trust.left { justify-content: flex-start; }
.hero-trust .sep { color: var(--line-strong); }

/* Centered hero */
.hero.centered {
  text-align: center;
  padding: 40px 0 60px;
  display: flex; flex-direction: column; align-items: center;
}
.hero.centered .hero-eyebrow { margin-bottom: 18px; }
.hero-blobs {
  margin-bottom: -40px;
  position: relative;
  z-index: 1;
}
.hero-input-wrap {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

/* Split hero */
.hero.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  align-items: center;
  padding: 40px 0;
  min-height: 580px;
}
.split-left { display: flex; flex-direction: column; align-items: flex-start; }
.split-left .hero-eyebrow { margin-bottom: 28px; }
.split-display {
  font-size: clamp(48px, 6.5vw, 96px);
  text-align: left;
}
.split-right {
  position: relative;
  height: 540px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  border-radius: var(--r-lg);
}
.split-right .blob-wrap {
  position: absolute;
  top: 10%;
  right: 0%;
  z-index: 0;
  max-width: 100%;
}
.preview-stack {
  position: relative;
  z-index: 2;
  width: 100%; max-width: 360px;
}
.preview-card {
  background: oklch(0.13 0.018 295 / 0.85);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-md);
  padding: 18px;
  backdrop-filter: blur(8px);
  box-shadow: 0 30px 60px -20px oklch(0 0 0 / 0.5);
}
.pc-1 {
  transform: rotate(-2deg) translate(0, 0);
  position: relative;
  z-index: 3;
}
.pc-2 {
  transform: rotate(4deg) translate(40px, -30px);
  margin-top: 20px;
  opacity: 0.85;
  position: relative;
  z-index: 2;
}
.pc-bar { display: flex; gap: 5px; margin-bottom: 14px; }
.pc-bar span { width: 8px; height: 8px; border-radius: 50%; background: var(--line-strong); }
.pc-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 14px;
}
.pc-line {
  height: 8px;
  background: var(--line-strong);
  border-radius: 4px;
  margin-bottom: 8px;
  width: 100%;
}
.pc-line.w70 { width: 70%; }
.pc-line.w80 { width: 80%; }
.pc-line.w50 { width: 50%; }

/* Dock hero */
.hero.dock {
  position: relative;
  min-height: 600px;
  padding: 20px 0 30px;
}
.dock-top {
  text-align: center;
}
.dock-top .hero-eyebrow { margin-bottom: 28px; }
.dock-display {
  font-size: clamp(64px, 10vw, 140px);
  text-align: center;
}
.dock-blobs {
  position: absolute;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: -1;
  opacity: 0.6;
}
.dock-bottom {
  margin-top: 60px;
  max-width: 720px;
  margin-left: auto; margin-right: auto;
}
.dock-feature-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 28px;
}
.feat-chip {
  background: oklch(0.11 0.015 295 / 0.6);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  padding: 12px 14px;
  backdrop-filter: blur(8px);
}
.feat-label {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 2px;
}
.feat-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--muted);
  text-transform: uppercase;
}

/* ---------- URL Input ---------- */
.url-form { width: 100%; }
.url-field {
  display: flex;
  align-items: stretch;
  background: oklch(0.13 0.018 295 / 0.7);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 6px 6px 6px 22px;
  backdrop-filter: blur(10px);
  transition: border-color 0.2s, box-shadow 0.2s;
  position: relative;
}
.url-field:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px oklch(0.78 0.16 300 / 0.12), 0 20px 50px -20px oklch(0.5 0.25 295 / 0.5);
}
.url-form.has-error .url-field { border-color: var(--danger); }
.url-prefix {
  display: flex; align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--muted);
  padding-right: 4px;
  user-select: none;
}
.url-field input {
  flex: 1;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  padding: 14px 8px;
  min-width: 0;
}
.url-field input::placeholder { color: oklch(0.45 0.015 290); }

.url-form.lg .url-field { padding: 7px 7px 7px 26px; }
.url-form.lg .url-field input { font-size: 15px; padding: 17px 8px; }

.url-go {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 22px;
  border-radius: 999px;
  background: oklch(0.2 0.02 295);
  color: var(--muted);
  font-weight: 600;
  font-size: 13.5px;
  letter-spacing: -0.005em;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.url-go.ready {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
  color: oklch(0.12 0.02 295);
  box-shadow: 0 8px 24px -8px var(--accent-deep);
}
.url-go.ready:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 32px -10px var(--accent-deep);
}
.url-go:disabled { cursor: not-allowed; }

.url-error {
  margin-top: 12px;
  font-size: 13px;
  color: var(--danger);
  padding-left: 22px;
}

/* ---------- Processing ---------- */
.processing {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 60px 0;
}
.proc-blobs {
  position: absolute;
  top: 10%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 0;
  opacity: 0.5;
}
.proc-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 560px;
}
.proc-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 20px;
}
.proc-eyebrow .pulse {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent);
  animation: pulse 1.4s ease-in-out infinite;
}
.proc-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 48px;
  letter-spacing: -0.03em;
  margin: 0 0 14px;
}
.proc-url {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--muted);
  background: oklch(0.11 0.015 295 / 0.6);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 32px;
  word-break: break-all;
}
.proc-steps {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column;
  gap: 4px;
}
.ps {
  display: flex;
  gap: 14px;
  padding: 14px;
  border-radius: 10px;
  transition: all 0.3s;
  border: 1px solid transparent;
}
.ps.active {
  background: oklch(0.13 0.02 295 / 0.7);
  border-color: var(--line);
}
.ps-marker {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  margin-top: 2px;
}
.ps.done .ps-marker { background: var(--accent); color: var(--bg); }
.ps.active .ps-marker { background: oklch(0.78 0.16 300 / 0.18); color: var(--accent); }
.ps.pending .ps-marker { background: oklch(0.2 0.015 295); }
.ps-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--muted);
}
.spinner {
  width: 12px; height: 12px;
  border: 2px solid oklch(0.78 0.16 300 / 0.25);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.ps-label {
  font-weight: 600;
  font-size: 14.5px;
  letter-spacing: -0.01em;
}
.ps.pending .ps-label { color: var(--muted); }
.ps-detail {
  font-size: 12.5px;
  color: var(--muted);
  margin-top: 1px;
}

/* ---------- Result / Guide ---------- */
.result {
  padding: 12px 0;
}
.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 28px;
  position: sticky;
  top: 0;
  z-index: 4;
  background: linear-gradient(180deg, var(--bg) 70%, transparent);
}
.ghost-btn, .pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: -0.005em;
  background: transparent;
  color: var(--fg-dim);
  border: 1px solid var(--line);
  transition: all 0.18s;
}
.ghost-btn:hover { color: var(--fg); border-color: var(--line-strong); }
.result-bar-right { display: flex; gap: 8px; }
.pill-btn {
  background: oklch(0.13 0.018 295 / 0.6);
  backdrop-filter: blur(8px);
}
.pill-btn:hover {
  background: oklch(0.18 0.02 295);
  color: var(--fg);
  border-color: var(--line-strong);
}
.pill-btn.primary {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
  color: oklch(0.12 0.02 295);
  border-color: transparent;
  font-weight: 600;
}
.pill-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px -10px var(--accent-deep);
}
.pill-btn.ok { color: var(--ok); border-color: oklch(0.78 0.15 155 / 0.4); }
.pill-btn.lg { height: 44px; padding: 0 22px; font-size: 14px; }

/* Document */
.guide-doc {
  background: oklch(0.99 0.005 290);
  color: oklch(0.18 0.012 290);
  border-radius: var(--r-lg);
  padding: 56px 64px;
  box-shadow: 0 40px 80px -30px oklch(0 0 0 / 0.5), 0 0 0 1px var(--line);
  position: relative;
  overflow: hidden;
}
.guide-doc::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 6px;
  background: linear-gradient(90deg, var(--accent), var(--accent-deep), oklch(0.85 0.1 195));
}

.doc-head { margin-bottom: 36px; }
.doc-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: oklch(0.4 0.012 290);
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid oklch(0.9 0.005 290);
}
.doc-source, .doc-stamp { display: inline-flex; align-items: center; gap: 7px; }
.doc-source .sep, .src-meta .sep { color: oklch(0.7 0.012 290); }
.doc-stamp {
  background: oklch(0.96 0.015 295);
  padding: 4px 10px;
  border-radius: 999px;
  color: oklch(0.45 0.12 295);
}
.doc-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 44px;
  line-height: 1.05;
  letter-spacing: -0.03em;
  margin: 0 0 16px;
  color: oklch(0.15 0.015 290);
  text-wrap: balance;
}
.doc-summary {
  font-size: 16px;
  line-height: 1.55;
  color: oklch(0.35 0.012 290);
  max-width: 640px;
  margin: 0;
}

.doc-cols {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 48px;
  margin-top: 32px;
}
.doc-side { display: flex; flex-direction: column; gap: 18px; }
.doc-card {
  background: oklch(0.97 0.008 290);
  border: 1px solid oklch(0.92 0.005 290);
  border-radius: var(--r-md);
  padding: 18px 20px;
}
.doc-card-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: oklch(0.45 0.012 290);
  margin-bottom: 12px;
}
.tool-list, .tips-list {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column;
  gap: 8px;
}
.tool-list li, .tips-list li {
  font-size: 13.5px;
  line-height: 1.5;
  color: oklch(0.25 0.012 290);
  padding-left: 16px;
  position: relative;
}
.tool-list li::before {
  content: '';
  position: absolute;
  left: 0; top: 8px;
  width: 5px; height: 5px;
  background: var(--accent);
  border-radius: 50%;
}
.tips-list li::before {
  content: '✦';
  position: absolute;
  left: 0; top: 0;
  font-size: 10px;
  color: var(--accent);
}
.tips-card { background: oklch(0.96 0.012 295); border-color: oklch(0.88 0.02 295); }

.doc-source-card {
  display: flex; gap: 12px;
  align-items: center;
  padding: 14px;
  background: oklch(0.15 0.015 290);
  color: oklch(0.95 0.005 290);
  border-radius: var(--r-md);
}
.src-thumb {
  width: 56px; height: 42px;
  background: linear-gradient(135deg, var(--accent-deep), oklch(0.3 0.02 295));
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.src-thumb-inner {
  color: oklch(0.98 0.005 290);
  opacity: 0.9;
}
.src-meta { min-width: 0; flex: 1; }
.src-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  opacity: 0.6;
  margin-bottom: 3px;
}
.src-url {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  word-break: break-all;
  line-height: 1.3;
}

.doc-main { min-width: 0; }
.steps-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.steps-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: oklch(0.4 0.012 290);
}
.steps-line {
  flex: 1;
  height: 1px;
  background: oklch(0.88 0.005 290);
}

.step-list {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column;
  gap: 28px;
}
.step {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 18px;
  padding-bottom: 28px;
  border-bottom: 1px solid oklch(0.92 0.005 290);
}
.step:last-child { border-bottom: none; padding-bottom: 0; }
.step-num {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 36px;
  letter-spacing: -0.03em;
  color: var(--accent);
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-deep) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  line-height: 1;
  padding-top: 4px;
}
.step-headline {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}
.step-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 20px;
  letter-spacing: -0.02em;
  margin: 0;
  color: oklch(0.15 0.015 290);
  text-wrap: balance;
}
.step-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: oklch(0.5 0.012 290);
  background: oklch(0.95 0.005 290);
  padding: 3px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.step-text {
  font-size: 14.5px;
  line-height: 1.6;
  color: oklch(0.3 0.012 290);
  margin: 0;
  text-wrap: pretty;
}
.doc-foot {
  margin-top: 32px;
  padding-top: 18px;
  border-top: 1px solid oklch(0.92 0.005 290);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: oklch(0.55 0.012 290);
  display: flex; align-items: center; gap: 8px;
}

/* ---------- Modal ---------- */
.modal-shroud {
  position: fixed; inset: 0;
  background: oklch(0.04 0.01 290 / 0.7);
  backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  z-index: 50;
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
.modal {
  background: oklch(0.12 0.018 295);
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  padding: 36px;
  width: 100%; max-width: 460px;
  box-shadow: 0 40px 100px -20px oklch(0 0 0 / 0.6), 0 0 0 1px oklch(1 0 0 / 0.02) inset;
  position: relative;
  animation: pop 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes pop {
  from { transform: scale(0.92) translateY(8px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}
.modal-close {
  position: absolute;
  top: 16px; right: 16px;
  width: 32px; height: 32px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: var(--muted);
  transition: all 0.15s;
}
.modal-close:hover { color: var(--fg); background: oklch(0.18 0.02 295); }
.modal-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 16px;
}
.modal-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 24px;
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.modal-sub {
  font-size: 14px;
  color: var(--fg-dim);
  line-height: 1.5;
  margin: 0 0 24px;
}
.modal-form {
  display: flex;
  gap: 8px;
}
.modal-form input {
  flex: 1;
  background: oklch(0.08 0.015 295);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 12px 18px;
  font-size: 14px;
  transition: border-color 0.15s;
}
.modal-form input:focus { border-color: var(--accent); }

/* ---------- How it works ---------- */
.how {
  margin-top: 80px;
  padding-top: 40px;
}
.how-rule {
  height: 1px;
  background: var(--line);
  margin-bottom: 32px;
}
.how-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 32px;
}
.how-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 42px;
  letter-spacing: -0.03em;
  margin: 0;
}
.how-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
}
.how-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
}
.how-cell {
  background: oklch(0.09 0.015 295);
  padding: 28px;
  display: flex; flex-direction: column;
  gap: 14px;
}
.how-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--accent);
}
.how-t {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 600;
  font-size: 22px;
  letter-spacing: -0.02em;
}
.how-b {
  font-size: 14px;
  color: var(--fg-dim);
  line-height: 1.5;
}

/* ---------- Footer ---------- */
.footer {
  border-top: 1px solid var(--line);
  padding: 24px 48px;
  margin-top: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted);
  max-width: 1280px;
  margin-left: auto; margin-right: auto;
  width: 100%;
}
.footer .ft-r { display: flex; gap: 12px; align-items: center; }
.footer .sep { color: var(--line-strong); }
.footer a { color: inherit; text-decoration: none; transition: color 0.15s; }
.footer a:hover { color: var(--fg); }

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .topbar, .stage, .footer { padding-left: 24px; padding-right: 24px; }
  .hero.split { grid-template-columns: 1fr; gap: 40px; }
  .split-right { height: 360px; }
  .doc-cols { grid-template-columns: 1fr; gap: 32px; }
  .guide-doc { padding: 36px 28px; }
  .doc-title { font-size: 32px; }
  .dock-feature-row { grid-template-columns: repeat(2, 1fr); }
  .how-grid { grid-template-columns: 1fr; }
  .url-prefix { display: none; }
  .url-go .go-text { display: none; }
  .url-go { padding: 0 16px; }
}

/* ---------- Print (Save as PDF) ---------- */
@media print {
  @page { margin: 18mm; }
  body { background: white; }
  body::before, body::after { display: none; }
  .no-print { display: none !important; }
  .stage { max-width: none; padding: 0; }
  .result { padding: 0; }
  .guide-doc {
    background: white;
    color: black;
    box-shadow: none;
    border-radius: 0;
    padding: 0;
  }
  .guide-doc::before { display: none; }
  .doc-source-card { background: #1a1a1a; }
  .step { page-break-inside: avoid; }
  .doc-card { background: #f8f8f8; }
}
`;

/* Inject styles */
const styleEl = document.createElement("style");
styleEl.textContent = STYLES;
document.head.appendChild(styleEl);

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
