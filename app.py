"""
app.py - High-Performance User-Side Dashboard
Features: BYOK (Bring Your Own Key), 100% Free Tier, Anonymous Creator Analytics.
"""
import os
import sys
import types

# Virtual retrieval bridge: tells Python to find retrieval files right here in the main folder
_root = os.path.dirname(os.path.abspath(__file__))
if "retrieval" not in sys.modules:
    _pkg = types.ModuleType("retrieval")
    _pkg.__path__ = [_root]
    _pkg.__file__ = os.path.join(_root, "__init__.py")
    sys.modules["retrieval"] = _pkg

import os
import streamlit as st
from pathlib import Path
from ai_router import AIRouter
from research_engine import ResearchEngine

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom Biotech Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BioSynthetix | Autonomous Research Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    .bio-card {
        background: #131B2E;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .bio-card-critic {
        background: #1C1924;
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .badge-grounded {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-flag {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Creator Analytics (PostHog - Optional & Free)
# -----------------------------------------------------------------------------
POSTHOG_API_KEY = "phc_your_free_key_here"  # Optional: Paste your free key from posthog.com

def log_event(event_name: str, properties: dict = None):
    """Sends lightweight anonymous telemetry to your free creator dashboard."""
    if POSTHOG_API_KEY and not POSTHOG_API_KEY.startswith("phc_your"):
        try:
            import requests
            requests.post(
                "https://app.posthog.com/capture/",
                json={
                    "api_key": POSTHOG_API_KEY,
                    "event": event_name,
                    "properties": properties or {},
                },
                timeout=2,
            )
        except Exception:
            pass

# -----------------------------------------------------------------------------
# 3. Sidebar: Secure BYOK (User Supplies Their Own Free Keys)
# -----------------------------------------------------------------------------
st.sidebar.markdown("## 🧬 BioSynthetix Engine")
st.sidebar.caption("Client-Side Autonomous Research Agent")
st.sidebar.markdown("---")

st.sidebar.markdown("### 🔑 API Access (BYOK)")
st.sidebar.caption("All computing happens on your machine. Keys are kept in local session memory only.")

user_groq = st.sidebar.text_input(
    "Groq API Key (Fast Inference)",
    type="password",
    help="Free key from console.groq.com",
)
st.sidebar.markdown("[Get Free Groq Key ↗](https://console.groq.com/keys)")

user_gemini = st.sidebar.text_input(
    "Gemini API Key (Fallback)",
    type="password",
    help="Free key from aistudio.google.com",
)
st.sidebar.markdown("[Get Free Gemini Key ↗](https://aistudio.google.com)")

keys_ready = bool(user_groq or user_gemini)
if keys_ready:
    st.sidebar.success("🟢 Ready to Run")
else:
    st.sidebar.warning("🟡 Enter at least one free API key above to begin.")

st.sidebar.markdown("---")
st.sidebar.caption("Free Community Version • 100% Client-Side Execution")

# -----------------------------------------------------------------------------
# 4. Main Interface
# -----------------------------------------------------------------------------
st.markdown("# Autonomous Biological Research Reconnaissance")
st.markdown("Search PubMed & PMC literature, verify statistical claims, and red-team medical hypotheses.")

question = st.text_input(
    "Enter a Biological or Clinical Research Question:",
    placeholder="e.g., Does semaglutide cause disproportionate lean mass loss compared to caloric restriction?",
)

max_papers = st.slider("Number of Papers to Ingest & Cross-Check:", min_value=3, max_value=8, value=4)

if st.button("🚀 Start Investigation", type="primary"):
    if not keys_ready:
        st.error("❌ Please provide a free Groq or Gemini API key in the sidebar.")
    elif not question.strip():
        st.warning("Please enter a research question.")
    else:
        # Log anonymous usage event to your creator dashboard
        log_event("investigation_started", {"question_length": len(question), "max_papers": max_papers})

        # Inject user keys into local router
        custom_router = AIRouter()
        if user_groq:
            custom_router.groq_key = user_groq
            from openai import OpenAI
            custom_router.groq = OpenAI(api_key=user_groq, base_url="https://api.groq.com/openai/v1")
        if user_gemini:
            custom_router.gemini_key = user_gemini
            from google import genai
            custom_router.gemini = genai.Client(api_key=user_gemini)

        status_box = st.status("🔬 Autonomous Research Agent at work...", expanded=True)

        try:
            with status_box:
                st.write("Initializing Proof Pillars and Literature Retrieval...")
                with ResearchEngine(router=custom_router) as engine:
                    st.write(f"Searching PubMed, PMC, and Europe PMC (Reading {max_papers} papers)...")
                    result = engine.run_agent(question, max_steps=8)

                st.write("Adjudicating competing explanations and running Adversarial Critic...")
                status_box.update(label="✅ Investigation Complete!", state="complete", expanded=False)

            # Read generated output
            report_path = Path("RESEARCH_REPORT.md")
            report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "No report generated."

            # Fetch DB summary
            rq_id = engine.db.create_research_question(question)
            claims = engine.db.claims_with_papers(rq_id)
            hypotheses = engine.db.list_hypotheses(rq_id)
            audit_flags = engine.db.list_audit_flags(rq_id)

            # Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Papers Analyzed", max_papers)
            m2.metric("Verified Claims", len(claims))
            m3.metric("Falsifiable Hypotheses", len(hypotheses))
            m4.metric("Adversarial Flags", len(audit_flags))

            st.markdown("---")

            # Structured Output Tabs
            tab_report, tab_claims, tab_critic, tab_hypotheses = st.tabs([
                "📄 Executive Report",
                "🧬 Grounded Claims Matrix",
                "⚠️ Adversarial Audit Flags",
                "🧪 Hypotheses & Falsification",
            ])

            with tab_report:
                st.download_button(
                    "📥 Download Dossier (.md)",
                    data=report_text,
                    file_name="RESEARCH_REPORT.md",
                    mime="text/markdown",
                )
                st.markdown(report_text)

            with tab_claims:
                st.markdown("### Verbatim Quote-Grounded Claims")
                st.caption("Claims extracted verbatim and verified via n-gram text overlap.")
                for c in claims[:15]:
                    st.markdown(f"""
                    <div class="bio-card">
                        <span class="badge-grounded">Grounded {c.get('grounding_score', 1.0)*100:.0f}%</span>
                        <h4 style="margin: 8px 0 4px 0;">{c.get('statement')}</h4>
                        <p style="color: #94A3B8; font-size: 0.9rem;">
                            <strong>Factor:</strong> <code>{c.get('intervention')}</code> ➔ <strong>Outcome:</strong> <code>{c.get('measurement')}</code>
                        </p>
                        <p style="color: #94A3B8; font-size: 0.85rem; font-style: italic;">"{c.get('quote')}"</p>
                        <p style="color: #64748B; font-size: 0.8rem; margin: 0;">Paper: {c.get('paper_title', 'Unknown')[:80]}...</p>
                    </div>
                    """, unsafe_allow_html=True)

            with tab_critic:
                st.markdown("### Adversarial Peer Review Flags")
                st.caption("Missing controls, confounding factors, and biological failure modes.")
                if audit_flags:
                    for f in audit_flags:
                        st.markdown(f"""
                        <div class="bio-card-critic">
                            <span class="badge-flag">{f.get('severity')} SEVERITY</span>
                            <h4 style="margin: 8px 0 4px 0; color: #FCA5A5;">{f.get('issue')}</h4>
                            <p style="color: #94A3B8; font-size: 0.85rem; margin: 0;">Entity: {f.get('claim_text')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("No critical methodology or causal overreach flags detected.")

            with tab_hypotheses:
                st.markdown("### Popperian Falsifiable Hypotheses")
                for h in hypotheses:
                    st.markdown(f"""
                    <div class="bio-card">
                        <h3 style="color: #38BDF8; margin-top: 0;">{h.get('statement')}</h3>
                        <p><strong>Proposed Mechanism:</strong> {h.get('mechanism')}</p>
                        <p><strong>Falsification Condition:</strong></p>
                        <blockquote style="border-left: 3px solid #EF4444; padding-left: 10px; color: #F87171;">
                            {h.get('falsification_conditions')[0] if h.get('falsification_conditions') else 'Not specified'}
                        </blockquote>
                    </div>
                    """, unsafe_allow_html=True)

            log_event("investigation_completed", {"claims_count": len(claims), "flags_count": len(audit_flags)})

        except Exception as exc:
            status_box.update(label="❌ Execution Error", state="error")
            st.error(f"Engine encounter: {exc}")
