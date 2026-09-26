"""
app.py - All-In-One Scientific Research Workstation
BioSynthetix | Autonomous Literature Synthesis & Adversarial Audit Engine
"""

import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 1. Virtual Retrieval Bridge (Guarantees loose retrieval files load properly)
# -----------------------------------------------------------------------------
_root = os.path.dirname(os.path.abspath(__file__))
if "retrieval" not in sys.modules:
    _pkg = types.ModuleType("retrieval")
    _pkg.__path__ = [_root]
    _pkg.__file__ = os.path.join(_root, "__init__.py")
    sys.modules["retrieval"] = _pkg

import streamlit as st
from ai_router import AIRouter
from database import ResearchDB
from research_engine import ResearchEngine

# -----------------------------------------------------------------------------
# 2. Page Configuration & Embedded Dark Scientific Workstation Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Biology AI Research Workstation",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background-color: #0B0F14;
        color: #E6EDF3;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    code, pre, .stat-mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Top Workstation Header Bar */
    .workstation-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #24303A;
        padding: 10px 0 16px 0;
        margin-bottom: 24px;
    }
    .workstation-title {
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #E6EDF3;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .system-status {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #36D399;
        background: rgba(54, 211, 153, 0.1);
        border: 1px solid rgba(54, 211, 153, 0.3);
        padding: 4px 10px;
        border-radius: 4px;
    }

    /* Scientific Card Containers */
    .sc-card {
        background-color: #111820;
        border: 1px solid #24303A;
        border-radius: 6px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .sc-card-highlight {
        background-color: #111820;
        border: 1px solid #24303A;
        border-left: 4px solid #36D399;
        border-radius: 6px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .sc-card-alert {
        background-color: #161214;
        border: 1px solid rgba(255, 107, 107, 0.3);
        border-left: 4px solid #FF6B6B;
        border-radius: 6px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }

    /* Stat Metric Cells */
    .stat-cell {
        background-color: #0E131A;
        border: 1px solid #24303A;
        border-radius: 4px;
        padding: 10px 14px;
        text-align: center;
    }
    .stat-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        color: #E6EDF3;
    }
    .stat-lbl {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8B98A5;
        margin-top: 2px;
    }

    /* Pill Badges */
    .badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 3px;
        display: inline-block;
    }
    .badge-green { background: rgba(54, 211, 153, 0.15); color: #36D399; border: 1px solid rgba(54, 211, 153, 0.3); }
    .badge-yellow { background: rgba(242, 201, 76, 0.15); color: #F2C94C; border: 1px solid rgba(242, 201, 76, 0.3); }
    .badge-red { background: rgba(255, 107, 107, 0.15); color: #FF6B6B; border: 1px solid rgba(255, 107, 107, 0.3); }
    .badge-blue { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }

    /* Clean Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0A0D12 !important;
        border-right: 1px solid #24303A;
    }
    
    /* Input Boxes */
    .stTextInput > div > div > input {
        background: #111820 !important;
        border: 1px solid #24303A !important;
        border-radius: 4px !important;
        color: #E6EDF3 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Header & Shared Database
# -----------------------------------------------------------------------------
st.markdown("""
<div class="workstation-header">
    <div class="workstation-title">
        <span>🧬</span> BIOLOGY AI RESEARCH ENGINE
    </div>
    <div class="system-status">● SYSTEM READY</div>
</div>
""", unsafe_allow_html=True)

db = ResearchDB()

# -----------------------------------------------------------------------------
# 4. Sidebar: Navigation & BYOK Credentials
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🔬 WORKSTATION")
active_screen = st.sidebar.radio(
    "Navigation",
    [
        "Research Launchpad",
        "Live Investigation Feed",
        "Evidence & Claims",
        "Retrieved Literature",
        "Hypotheses & Falsification",
        "Adversarial Audit & Dossier",
    ],
    index=0,
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ AI ROUTER STATUS")

groq_key = st.session_state.get("groq_key", "")
gemini_key = st.session_state.get("gemini_key", "")

groq_active = bool(groq_key)
gemini_active = bool(gemini_key)

st.sidebar.markdown(f"""
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.8;">
    <div>{'🟢' if groq_active else '⚪'} GROQ LPU <span style="color: #8B98A5;">(llama-3.1-8b)</span></div>
    <div>{'🟢' if gemini_active else '⚪'} GEMINI <span style="color: #8B98A5;">(fallback)</span></div>
</div>
""", unsafe_allow_html=True)

with st.sidebar.expander("🔑 Configure API Keys (BYOK)", expanded=not (groq_active or gemini_active)):
    st.session_state["groq_key"] = st.text_input("Groq API Key", type="password", value=groq_key, help="console.groq.com/keys")
    st.session_state["gemini_key"] = st.text_input("Gemini API Key", type="password", value=gemini_key, help="aistudio.google.com")
    st.caption("Keys remain in memory and are never written to disk.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ KNOWLEDGE STORE")

try:
    papers_count = db._conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    claims_count = db._conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    hyp_count = db._conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
    flags_count = db._conn.execute("SELECT COUNT(*) FROM audit_flags").fetchone()[0]
except Exception:
    papers_count, claims_count, hyp_count, flags_count = 0, 0, 0, 0

st.sidebar.markdown(f"""
<div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.8;">
    <div>● <span style="color: #8B98A5;">Papers Ingested:</span> <strong>{papers_count}</strong></div>
    <div>● <span style="color: #8B98A5;">Grounded Claims:</span> <strong>{claims_count}</strong></div>
    <div>● <span style="color: #8B98A5;">Hypotheses:</span> <strong>{hyp_count}</strong></div>
    <div>● <span style="color: #8B98A5;">Audit Flags:</span> <strong style="color: #FF6B6B;">{flags_count}</strong></div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Screen 1: Research Launchpad
# -----------------------------------------------------------------------------
if active_screen == "Research Launchpad":
    st.markdown("### 🎯 Investigation Launchpad")
    st.markdown("<p style='color: #8B98A5; margin-top: -6px;'>Define a scientific question to initialize proof pillars and dispatch autonomous agents.</p>", unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns(3)
    prefill = ""
    if col_s1.button("💊 Semaglutide & Lean Mass Loss", use_container_width=True):
        prefill = "Does semaglutide cause disproportionate lean mass loss compared to diet-induced caloric restriction alone?"
    if col_s2.button("🧬 Metformin in Breast Cancer", use_container_width=True):
        prefill = "How does metformin affect breast cancer cell proliferation and apoptosis?"
    if col_s3.button("🧠 Dementia Clinical Biomarkers", use_container_width=True):
        prefill = "What are the primary symptoms and diagnostic biomarkers of early-stage dementia?"

    question = st.text_input(
        "Scientific Research Question:",
        value=prefill if prefill else st.session_state.get("active_question", ""),
        placeholder="Enter biological hypothesis, mechanism, or clinical comparison...",
    )
    st.session_state["active_question"] = question

    col_btn, col_scope = st.columns([1.5, 4])
    with col_btn:
        start_investigation = st.button("🚀 Dispatch Agent", type="primary", use_container_width=True)
    with col_scope:
        max_papers = st.selectbox("Search Depth", [3, 5, 8], index=0, format_func=lambda x: f"Batch Ingest {x} Studies (PubMed/PMC)")

    if start_investigation:
        groq_k = st.session_state.get("groq_key")
        gemini_k = st.session_state.get("gemini_key")
        
        if not (groq_k or gemini_k):
            st.error("Authentication Missing: Enter a free Groq or Gemini API key in the sidebar.")
        elif not question.strip():
            st.warning("Please enter a research question.")
        else:
            custom_router = AIRouter()
            if groq_k:
                from openai import OpenAI
                custom_router.groq_key = groq_k
                custom_router.groq = OpenAI(api_key=groq_k, base_url="https://api.groq.com/openai/v1")
            if gemini_k:
                from google import genai
                custom_router.gemini_key = gemini_k
                custom_router.gemini = genai.Client(api_key=gemini_k)

            with st.spinner("Dispatching agent... Querying PubMed/PMC, parsing JATS XML, and running stats..."):
                try:
                    with ResearchEngine(router=custom_router) as engine:
                        res = engine.run_agent(question, max_steps=8 if max_papers > 3 else 4)
                    st.session_state["last_investigation"] = res
                    st.session_state["last_rq_id"] = engine.db.create_research_question(question)
                    st.success("Investigation complete! Switch to 'Evidence & Claims' or 'Adversarial Audit' in the sidebar.")
                except Exception as e:
                    st.error(f"Investigation halted: {e}")

    st.markdown("<br><h4>📜 Previous Investigations in Store</h4>", unsafe_allow_html=True)
    rqs = db._rows(db._conn.execute("SELECT * FROM research_questions ORDER BY id DESC LIMIT 5").fetchall())
    if rqs:
        for r in rqs:
            summary = db.research_question_summary(r["id"])
            st.markdown(f"""
            <div class="sc-card" style="padding: 12px 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>[ID #{r['id']}] {r['question']}</strong>
                    <span class="badge badge-blue">{summary['claims']} claims • {summary['hypotheses']} hypotheses</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. Screen 2: Live Investigation Feed
# -----------------------------------------------------------------------------
elif active_screen == "Live Investigation Feed":
    st.markdown("### 🛰️ Live Agent Investigation Telemetry")
    res = st.session_state.get("last_investigation")
    if not res:
        st.info("No active investigation trace found in memory. Run a query from the Launchpad.")
    else:
        fin = res.get("final_synthesis", {})
        st.markdown(f"""
        <div class="sc-card-highlight">
            <span class="badge badge-green">SYNTHESIZED CONCLUSION</span>
            <h4 style="margin: 8px 0; color: #E6EDF3;">Executive Summary</h4>
            <p style="color: #8B98A5; line-height: 1.6;">{fin.get('executive_summary', 'No summary generated.')}</p>
            <h4 style="margin: 12px 0 6px 0; color: #E6EDF3;">Consensus Signaling Mechanism</h4>
            <p class="stat-mono" style="color: #38BDF8; font-size: 0.85rem; line-height: 1.6;">{fin.get('key_mechanism', 'No mechanism extracted.')}</p>
        </div>
        """, unsafe_allow_html=True)

        competing = fin.get("evaluated_competing_explanations", [])
        if competing:
            st.markdown("#### ⚖️ Counter-Mechanism Adjudication")
            for c in competing:
                st.markdown(f"""
                <div class="sc-card">
                    <span class="badge badge-yellow">EVALUATED RIVAL EXPLANATION</span>
                    <p style="margin: 8px 0 0 0; color: #E6EDF3;">{c}</p>
                </div>
                """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. Screen 3: Evidence & Claims Inspector (The Core Inspection Card)
# -----------------------------------------------------------------------------
elif active_screen == "Evidence & Claims":
    st.markdown("### 🧬 Verbatim Grounded Claims Inspector")
    st.markdown("<p style='color: #8B98A5; margin-top: -6px;'>Every claim below was extracted verbatim from literature and verified through n-gram token overlap.</p>", unsafe_allow_html=True)

    rq_id = st.session_state.get("last_rq_id")
    claims = db.claims_with_papers(rq_id) if rq_id else db.claims_with_papers()

    if not claims:
        st.info("No claims found in store. Run an investigation from the launchpad.")
    else:
        for c in claims[:25]:
            g_score = c.get("grounding_score", 1.0)
            p_val = c.get("p_value")
            dir_str = str(c.get("effect_direction", "unclear")).upper()
            dir_badge = "badge-blue" if dir_str == "INCREASE" else ("badge-red" if dir_str == "DECREASE" else "badge-yellow")

            st.markdown(f"""
            <div class="sc-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="stat-mono" style="font-size: 0.8rem; font-weight: 700; color: #8B98A5;">CLAIM #{c.get('id', 0):03d}</span>
                    <div>
                        <span class="badge {dir_badge}">{dir_str}</span>
                        <span class="badge badge-green">GROUNDED {g_score * 100:.0f}%</span>
                    </div>
                </div>
                
                <h4 style="margin: 0 0 10px 0; color: #E6EDF3; font-weight: 600;">{c.get('statement')}</h4>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0;">
                    <div class="stat-cell">
                        <div class="stat-val" style="font-size: 0.9rem;">{c.get('intervention') or 'N/A'}</div>
                        <div class="stat-lbl">Intervention</div>
                    </div>
                    <div class="stat-cell">
                        <div class="stat-val" style="font-size: 0.9rem;">{c.get('measurement') or 'N/A'}</div>
                        <div class="stat-lbl">Endpoint</div>
                    </div>
                    <div class="stat-cell">
                        <div class="stat-val" style="font-size: 0.9rem;">{f'p = {p_val:.4g}' if p_val is not None else 'Unspecified'}</div>
                        <div class="stat-lbl">Statistical P</div>
                    </div>
                    <div class="stat-cell">
                        <div class="stat-val" style="font-size: 0.9rem;">n = {c.get('sample_size') or 'N/A'}</div>
                        <div class="stat-lbl">Sample Size</div>
                    </div>
                </div>
                
                <div style="background: #0E131A; border: 1px solid #24303A; border-radius: 4px; padding: 12px; margin-top: 10px;">
                    <div style="font-size: 0.7rem; text-transform: uppercase; color: #8B98A5; font-weight: 700; margin-bottom: 4px;">VERBATIM EVIDENCE QUOTE</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #A7F3D0; font-style: italic;">"{c.get('quote')}"</div>
                    <div style="font-size: 0.75rem; color: #8B98A5; margin-top: 6px;">
                        Source: {c.get('paper_title', 'Unknown')[:80]}... (PMID: {c.get('pmid') or 'N/A'})
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. Screen 4: Retrieved Literature
# -----------------------------------------------------------------------------
elif active_screen == "Retrieved Literature":
    st.markdown("### 📚 Retrieved Peer-Reviewed Literature")
    papers = db.list_papers()
    if not papers:
        st.info("No papers currently ingested.")
    else:
        st.caption(f"Catalog of {len(papers)} scientific articles ingested from Europe PMC and PubMed:")
        for p in papers:
            sections = db.get_sections(p["id"])
            tables = db.get_tables(p["id"])
            st.markdown(f"""
            <div class="sc-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h4 style="margin: 0 0 6px 0; color: #E6EDF3;">{p.get('title') or 'Untitled'}</h4>
                        <p style="color: #8B98A5; font-size: 0.85rem; margin: 0 0 8px 0;">{p.get('journal', 'Journal')} ({p.get('year', 'N/A')}) • Authors: {p.get('authors', 'Unknown')[:60]}...</p>
                    </div>
                    <span class="badge badge-green">OPEN ACCESS</span>
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8;">
                    PMID: {p.get('pmid') or 'N/A'} | PMCID: {p.get('pmcid') or 'N/A'} | DOI: {p.get('doi') or 'N/A'}
                </div>
                <div style="font-size: 0.8rem; color: #8B98A5; margin-top: 8px;">
                    Sections parsed: {len(sections)} | Data tables extracted: {len(tables)}
                </div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. Screen 5: Hypotheses & Falsification
# -----------------------------------------------------------------------------
elif active_screen == "Hypotheses & Falsification":
    st.markdown("### 🧪 Popperian Falsifiable Hypotheses")
    rq_id = st.session_state.get("last_rq_id")
    hypotheses = db.list_hypotheses(rq_id) if rq_id else db.list_hypotheses()

    if not hypotheses:
        st.info("No hypotheses recorded yet.")
    else:
        for i, h in enumerate(hypotheses, 1):
            falsif = h.get("falsification_conditions") or ["Not specified"]
            st.markdown(f"""
            <div class="sc-card-highlight">
                <div style="display: flex; justify-content: space-between;">
                    <span class="stat-mono" style="font-size: 0.8rem; color: #8B98A5;">HYPOTHESIS #{i:02d}</span>
                    <span class="badge badge-green">{str(h.get('status', 'proposed')).upper()}</span>
                </div>
                <h3 style="color: #38BDF8; margin: 8px 0 6px 0;">{h.get('statement')}</h3>
                <p style="color: #E6EDF3; font-size: 0.95rem;"><strong>Molecular Mechanism:</strong> {h.get('mechanism')}</p>
                
                <div style="background: #0E131A; border: 1px solid rgba(255, 107, 107, 0.3); border-radius: 4px; padding: 12px; margin: 12px 0;">
                    <div style="font-size: 0.7rem; text-transform: uppercase; color: #FF6B6B; font-weight: 700; margin-bottom: 4px;">FALSIFICATION CONDITION</div>
                    <div style="color: #FCA5A5; font-size: 0.9rem;">{falsif[0]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 10. Screen 6: Adversarial Audit & Dossier
# -----------------------------------------------------------------------------
elif active_screen == "Adversarial Audit & Dossier":
    st.markdown("### ⚠️ Adversarial Audit & Quality Control")
    rq_id = st.session_state.get("last_rq_id")
    flags = db.list_audit_flags(rq_id) if rq_id else db.list_audit_flags()

    if flags:
        st.caption(f"Adversarial Flags Caught by Critic: {len(flags)}")
        for f in flags:
            sev = f.get("severity", "MEDIUM")
            sev_badge = "badge-red" if sev == "HIGH" else "badge-yellow"
            st.markdown(f"""
            <div class="sc-card-alert">
                <span class="badge {sev_badge}">{sev} RISK</span>
                <h4 style="margin: 8px 0 4px 0; color: #FF6B6B;">{f.get('issue')}</h4>
                <div style="font-size: 0.8rem; color: #8B98A5;">
                    Entity: <code>{f.get('claim_text')}</code> | Source: <code>{f.get('evidence_reference')}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sc-card-highlight">
            <span class="badge badge-green">ALL AUDITS PASSED</span>
            <p style="margin: 8px 0 0 0; color: #E6EDF3;">No causal overreach or missing controls detected.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><h4>📄 Export Complete Research Dossier</h4>", unsafe_allow_html=True)
    report_path = Path("RESEARCH_REPORT.md")
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        st.download_button(
            "📥 Download Full Dossier (.md)",
            data=report_text,
            file_name="RESEARCH_REPORT.md",
            mime="text/markdown",
            use_container_width=True,
        )
        with st.expander("Preview Raw Markdown"):
            st.text_area("Markdown Preview", value=report_text, height=350)
