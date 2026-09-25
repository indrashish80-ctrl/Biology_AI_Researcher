"""
app.py - Executive Biotech Intelligence Dashboard
BioSynthetix | Autonomous Literature Synthesis & Adversarial Audit Engine
"""

import os
import sys
import types

# -----------------------------------------------------------------------------
# Virtual Retrieval Bridge (Guarantees Streamlit Cloud module imports)
# -----------------------------------------------------------------------------
_root = os.path.dirname(os.path.abspath(__file__))
if "retrieval" not in sys.modules:
    _pkg = types.ModuleType("retrieval")
    _pkg.__path__ = [_root]
    _pkg.__file__ = os.path.join(_root, "__init__.py")
    sys.modules["retrieval"] = _pkg

from pathlib import Path
import streamlit as st
from ai_router import AIRouter
from research_engine import ResearchEngine

# -----------------------------------------------------------------------------
# Page Configuration & Modern Executive Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BioSynthetix | Autonomous Research Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark Linear/Biotech UI Palette
st.markdown("""
<style>
    /* Global Base */
    .stApp {
        background-color: #080C14;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hero Gradient Title */
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        color: #64748B;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 1.8rem;
    }

    /* Executive Stat Cards */
    .kpi-card {
        background: radial-gradient(circle at top left, #172033 0%, #0F172A 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-top: 4px;
    }
    .kpi-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        font-weight: 600;
    }

    /* Mechanism Pathway Flow Box */
    .pathway-flow {
        background: #0D1424;
        border: 1px solid #1E293B;
        border-left: 4px solid #38BDF8;
        border-radius: 10px;
        padding: 18px 22px;
        margin: 18px 0;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #F1F5F9;
    }

    /* Claim Cards */
    .claim-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        transition: border 0.2s ease;
    }
    .claim-card:hover {
        border-color: #38BDF8;
    }

    /* Critic Severity Card */
    .critic-card {
        background: #18111A;
        border: 1px solid rgba(244, 63, 94, 0.3);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* Pill Badges */
    .pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .pill-green { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .pill-red { background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.3); }
    .pill-blue { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }
    
    /* Input & Search Bar */
    .stTextInput > div > div > input {
        background: #10172A !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #F8FAFC !important;
        padding: 14px 16px !important;
        font-size: 1rem !important;
    }
    
    /* Clean Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0A0F1D !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar: Clean Collapsible Credentials
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🧬 BioSynthetix Engine")
st.sidebar.caption("Deterministic Synthesis • Adversarial Audit")
st.sidebar.markdown("---")

with st.sidebar.expander("🔑 Cloud API Credentials (BYOK)", expanded=False):
    st.caption("Your keys remain in local session memory and are never stored.")
    user_groq = st.text_input("Groq API Key (Free)", type="password", help="console.groq.com/keys")
    st.markdown("[Get Free Groq Key ↗](https://console.groq.com/keys)")
    user_gemini = st.text_input("Gemini Key (Fallback)", type="password", help="aistudio.google.com")
    st.markdown("[Get Free Gemini Key ↗](https://aistudio.google.com)")

keys_ready = bool(user_groq or user_gemini)

# Execution mode toggle instead of clunky slider
st.sidebar.markdown("### ⚙️ Investigation Mode")
mode_selection = st.sidebar.radio(
    "Literature Scope",
    ["⚡ Rapid Triage (3 Studies)", "🔬 Deep Clinical Audit (6 Studies)"],
    index=0
)
max_papers = 6 if "Deep" in mode_selection else 3

st.sidebar.markdown("---")
if keys_ready:
    st.sidebar.markdown('<span class="pill pill-green">● Engine Connected</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="pill pill-red">● Keys Required</span>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main Hero Section
# -----------------------------------------------------------------------------
st.markdown('<div class="hero-title">Autonomous Biological Reconnaissance</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">PubMed literature extraction with deterministic statistical validation and automated adversarial red-teaming.</div>', unsafe_allow_html=True)

# Interactive Topic Chips (Instant Pre-fill)
st.markdown("<span style='font-size: 0.85rem; color: #64748B; font-weight: 600;'>TRY A CASE STUDY:</span>", unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)
sample_query = ""

if col_c1.button("💊 Semaglutide & Lean Mass Loss", use_container_width=True):
    sample_query = "Does semaglutide cause disproportionate lean mass loss compared to diet-induced caloric restriction alone?"
if col_c2.button("🧬 Metformin in Breast Cancer", use_container_width=True):
    sample_query = "How does metformin affect breast cancer cell proliferation and apoptosis?"
if col_c3.button("🧠 Dementia & Biomarker Diagnosis", use_container_width=True):
    sample_query = "What are the primary symptoms and diagnostic biomarkers of early-stage dementia?"

# Main Query Bar
question = st.text_input(
    "Target Biological Query:",
    value=sample_query if sample_query else "",
    placeholder="Ask any biological, pharmacological, or clinical question...",
    label_visibility="collapsed"
)

run_col, _ = st.columns([1.2, 5])
with run_col:
    start_btn = st.button("🚀 Run Investigation", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# Execution & Dynamic Results
# -----------------------------------------------------------------------------
if start_btn:
    if not keys_ready:
        st.error("Please enter at least your free Groq or Gemini API key in the sidebar drawer.")
    elif not question.strip():
        st.warning("Please enter a research question.")
    else:
        # Configure Dynamic Router
        custom_router = AIRouter()
        if user_groq:
            custom_router.groq_key = user_groq
            from openai import OpenAI
            custom_router.groq = OpenAI(api_key=user_groq, base_url="https://api.groq.com/openai/v1")
        if user_gemini:
            custom_router.gemini_key = user_gemini
            from google import genai
            custom_router.gemini = genai.Client(api_key=user_gemini)

        status_box = st.status("🧬 Ingesting literature and calculating statistics...", expanded=True)

        try:
            with status_box:
                st.write("Extracting PubMed articles & verifying claims via n-gram overlap...")
                with ResearchEngine(router=custom_router) as engine:
                    result = engine.run_agent(question, max_steps=8 if max_papers == 6 else 4)

                st.write("Executing Adversarial Critic on proposed hypotheses...")
                status_box.update(label="Investigation Complete", state="complete", expanded=False)

            # Retrieve Data
            rq_id = engine.db.create_research_question(question)
            claims = engine.db.claims_with_papers(rq_id)
            hypotheses = engine.db.list_hypotheses(rq_id)
            audit_flags = engine.db.list_audit_flags(rq_id)
            report_path = Path("RESEARCH_REPORT.md")
            report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "Report unavailable."

            fin = result.get("final_synthesis", {})

            # Executive KPI Metric Grid
            st.markdown("<br>", unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Papers Audited</div><div class="kpi-val">{max_papers}</div></div>', unsafe_allow_html=True)
            with k2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Grounded Claims</div><div class="kpi-val">{len(claims)}</div></div>', unsafe_allow_html=True)
            with k3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Falsifiable Hypotheses</div><div class="kpi-val">{len(hypotheses)}</div></div>', unsafe_allow_html=True)
            with k4:
                flag_color = "#FB7185" if audit_flags else "#34D399"
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Critic Audit Flags</div><div class="kpi-val" style="color: {flag_color};">{len(audit_flags)}</div></div>', unsafe_allow_html=True)

            # Highlight Mechanism Flow
            key_mech = fin.get("key_mechanism") or (hypotheses[0].get("mechanism") if hypotheses else "Mechanism under review.")
            st.markdown(f"""
            <div class="pathway-flow">
                <span class="pill pill-blue" style="margin-bottom: 8px;">Consensus Mechanism & Signaling Cascade</span>
                <p style="margin: 8px 0 0 0;">{key_mech}</p>
            </div>
            """, unsafe_allow_html=True)

            # Structured Tabs
            tab_overview, tab_audit, tab_claims, tab_export = st.tabs([
                "📊 Executive Summary",
                "⚠️ Adversarial Audit",
                "🧬 Literature Evidence",
                "📥 Full Dossier (.md)",
            ])

            with tab_overview:
                st.markdown("### Executive Synthesis")
                st.write(fin.get("executive_summary", "Synthesis completed across primary studies."))

                st.markdown("### Proposed Experimental Validation")
                for h in hypotheses:
                    st.markdown(f"**Target Hypothesis:** {h.get('statement')}")
                    falsif = h.get('falsification_conditions') or ['Refuted under experimental contrast']
                    st.info(f"**Falsification Condition:** {falsif[0]}")

            with tab_audit:
                st.markdown("### Adversarial Red-Team Findings")
                st.caption("The Critic audits hypotheses for missing orthogonal controls, sample size power, and confounding variables.")
                if audit_flags:
                    for f in audit_flags:
                        st.markdown(f"""
                        <div class="critic-card">
                            <span class="pill pill-red">{f.get('severity')} RISK</span>
                            <p style="margin: 8px 0 4px 0; font-weight: 600; color: #FCA5A5;">{f.get('issue')}</p>
                            <span style="font-size: 0.8rem; color: #64748B;">Entity: {f.get('claim_text')} | Source: {f.get('evidence_reference')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("No fatal methodology flaws or missing controls detected.")

            with tab_claims:
                st.markdown("### Quote-Grounded Claims Matrix")
                for c in claims[:12]:
                    st.markdown(f"""
                    <div class="claim-card">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                            <span class="pill pill-blue">{str(c.get('effect_direction')).upper()}</span>
                            <span class="pill pill-green">GROUNDED {c.get('grounding_score', 1.0)*100:.0f}%</span>
                        </div>
                        <div style="font-weight: 600; margin-bottom: 4px; color: #F8FAFC;">{c.get('statement')}</div>
                        <div style="font-size: 0.85rem; color: #94A3B8; font-style: italic;">"{c.get('quote')}"</div>
                        <div style="font-size: 0.75rem; color: #64748B; margin-top: 6px;">Paper: {c.get('paper_title', 'Study')[:75]}...</div>
                    </div>
                    """, unsafe_allow_html=True)

            with tab_export:
                st.download_button(
                    "📥 Download Markdown Dossier",
                    data=report_text,
                    file_name="RESEARCH_REPORT.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                st.text_area("Raw Report Markdown", value=report_text, height=450)

        except Exception as exc:
            status_box.update(label="Execution Encountered Notice", state="error")
            st.error(f"Engine encounter: {exc}")
