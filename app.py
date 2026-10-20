"""Streamlit UI.  Run:  python -m streamlit run app.py"""
import html
import io
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

from autofill.answer import ABSTAIN_STRENGTH, draft_answer
from autofill.llm import get_llm
from autofill.fill import build_retriever, fill
from autofill.questionnaire import read_xlsx, write_answers_xlsx

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "data" / "samples" / "vsaq_questionnaire.xlsx"
RESULTS = ROOT / "eval" / "results.json"

MODES = {
    "bm25+expand": "Keyword + compliance synonyms (recommended)",
    "bm25": "Keyword only (baseline)",
    "hybrid": "Hybrid: keyword + embeddings",
    "dense": "Embeddings only",
}
SHORT = {"bm25+expand": "Keyword + synonyms", "bm25": "Keyword only", "hybrid": "Hybrid", "dense": "Embeddings"}
EXAMPLES = [
    "Do you require multi-factor authentication?",
    "How long are security logs retained?",
    "Is a third-party penetration test performed annually?",
    "Do you place externally exposed systems in a DMZ?",
]
ANSWER_COLOURS = {"Yes": "green", "No": "red", "Partial": "amber", "Not covered": "grey", "See policy": "blue"}

st.set_page_config(page_title="Questionnaire Auto-Filler", page_icon="🛡️", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero {background: linear-gradient(120deg, #312e81 0%, #4f46e5 55%, #0ea5e9 100%); color: #fff;
       padding: 28px 32px; border-radius: 16px; margin-bottom: 1.2rem;}
.hero h1 {color: #fff; font-size: 2rem; margin: 0 0 6px 0; padding: 0;}
.hero p {color: #e0e7ff; margin: 0 0 14px 0; font-size: 1.02rem; max-width: 780px;}
.pill {display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.25);
       padding: 4px 12px; border-radius: 999px; margin: 0 6px 6px 0; font-size: .85rem;}
.card {border: 1px solid rgba(128,128,128,.25); border-radius: 14px; padding: 18px 20px; margin: 8px 0 12px 0;
       background: rgba(128,128,128,.04);}
.card h4 {margin: 0 0 8px 0;}
.badge {display: inline-block; padding: 3px 11px; border-radius: 999px; font-weight: 600; font-size: .82rem;
        margin-right: 6px;}
.green {background: #dcfce7; color: #166534;} .red {background: #fee2e2; color: #991b1b;}
.amber {background: #fef3c7; color: #92400e;} .grey {background: #e5e7eb; color: #374151;}
.blue {background: #dbeafe; color: #1e40af;}
.bar {height: 8px; border-radius: 6px; background: rgba(128,128,128,.2); overflow: hidden; margin: 10px 0 4px 0;}
.bar > div {height: 100%; border-radius: 6px;}
.muted {opacity: .7; font-size: .85rem;}
.cite {display: block; border-left: 3px solid #4f46e5; padding: 6px 12px; margin: 6px 0;
       background: rgba(79,70,229,.06); border-radius: 0 8px 8px 0; text-decoration: none;}
.stat {border: 1px solid rgba(128,128,128,.25); border-radius: 14px; padding: 14px 18px;}
.stat .v {font-size: 1.7rem; font-weight: 700;} .stat .l {opacity: .7; font-size: .85rem;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Indexing policies…")
def get_retriever(mode):
    return build_retriever(mode)


def esc(s) -> str:
    return html.escape(str(s))


def stat(col, value, label):
    col.markdown(f"<div class='stat'><div class='v'>{esc(value)}</div><div class='l'>{esc(label)}</div></div>",
                 unsafe_allow_html=True)


def confidence_bar(conf: float) -> str:
    colour = "#16a34a" if conf >= 0.7 else "#f59e0b" if conf >= 0.4 else "#dc2626"
    return f"<div class='bar'><div style='width:{min(conf, 1) * 100:.0f}%;background:{colour}'></div></div>"


def answer_card(res: dict):
    status_cls = "green" if res["status"] == "Drafted" else "amber"
    cites = "".join(
        f"<a class='cite' href='{esc(c['url'])}' target='_blank'>📄 <b>{esc(c['title'])}</b>"
        f"<br><span class='muted'>{esc(c['section'])}</span></a>"
        for c in res["citations"]
    )
    st.markdown(
        f"""<div class='card'>
<span class='badge {ANSWER_COLOURS.get(res['answer'], 'blue')}'>{esc(res['answer'])}</span>
<span class='badge {status_cls}'>{esc(res['status'])}</span>
{confidence_bar(res['confidence'])}<div class='muted'>Confidence {res['confidence']:.0%}</div>
<p style='margin:14px 0 10px 0'>{esc(res['explanation'])}</p>
<div class='muted' style='margin-top:6px'>Evidence</div>{cites}</div>""",
        unsafe_allow_html=True,
    )


# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    mode = st.selectbox("Search method", list(MODES), format_func=MODES.get)
    try:
        r = get_retriever(mode)
    except Exception as e:  # embeddings model missing or offline
        st.error(f"{MODES[mode]} isn't available here ({type(e).__name__}). Falling back to keyword search.")
        mode = "bm25+expand"
        r = get_retriever(mode)
    llm = get_llm()
    if llm:
        order = "\n".join(f"{i}. **{p.name}** · `{p.model}`" for i, p in enumerate(llm.providers, 1))
        st.success(f"**AI drafting on.** Tried in this order:\n\n{order}")
    else:
        st.info("**Offline mode.** Answers quote the best policy passage. Add `GEMINI_API_KEY` or "
                "`GROQ_API_KEY` to `.env`, or start Ollama, to have an AI write them.")
    docs = sorted({(c.title, c.url) for c in r.chunks})
    st.markdown("### 📚 Policy library")
    st.caption(f"{len(docs)} GitLab security policies · {len(r.chunks)} sections")
    with st.expander("Browse documents"):
        for title, url in docs:
            st.markdown(f"- [{title}]({url})")
    st.caption("Sources: GitLab Handbook (public) · Google VSAQ (Apache-2.0)")

# ---------- header ----------
st.markdown(
    f"""<div class='hero'>
<h1>🛡️ Security Questionnaire Auto-Filler</h1>
<p>Drafts answers to vendor security questionnaires from a company's own policies, cites the exact section
behind every answer, and flags what the policies don't cover for a human to answer.</p>
<span class='pill'>📚 {len(docs)} real policies</span><span class='pill'>🧩 {len(r.chunks)} citable sections</span>
<span class='pill'>🎯 75% top-1 · 94% top-5 retrieval</span><span class='pill'>🚩 Flags unanswerable questions</span>
</div>""",
    unsafe_allow_html=True,
)

ask, bulk, evals, how = st.tabs(["💬 Ask a question", "📋 Fill a questionnaire", "📊 Evaluation", "🔍 How it works"])

# ---------- ask ----------
with ask:
    st.markdown("Try an example, or type any question from a security questionnaire.")
    cols = st.columns(len(EXAMPLES))
    for col, ex in zip(cols, EXAMPLES):
        if col.button(ex, use_container_width=True):
            st.session_state["q"] = ex
    q = st.text_input("Question", key="q", placeholder="e.g. Do you encrypt laptops?", label_visibility="collapsed")
    if q:
        with st.spinner("Searching policies…"):
            res = draft_answer(q, r)
        left, right = st.columns([3, 2], gap="large")
        with left:
            st.markdown("#### Drafted answer")
            answer_card(res)
        with right:
            st.markdown("#### Top matching sections")
            hits = r.search(q, k=5)
            best = max(s for _, s in hits) or 1
            for c, score in hits:
                st.markdown(
                    f"**{esc(c.title)}**  \n<span class='muted'>{esc(c.section)}</span>"
                    f"{confidence_bar(score / best)}",
                    unsafe_allow_html=True,
                )
                with st.expander("Read section"):
                    st.write(c.text)

# ---------- bulk ----------
with bulk:
    up_col, opt_col = st.columns([3, 2], gap="large")
    with up_col:
        up = st.file_uploader("Upload a questionnaire (.xlsx with a **Question** column)", type=["xlsx"])
    with opt_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        use_sample = st.toggle("Use sample: Google VSAQ (126 real questions)", value=up is None)
        run = st.button("✨ Fill questionnaire", type="primary", use_container_width=True,
                        disabled=up is None and not use_sample)
    if run:
        source = up if up is not None else SAMPLE
        try:
            questions = read_xlsx(source)
        except ValueError as e:
            st.error(str(e))
            questions = []
        if questions:
            bar = st.progress(0.0, "Starting…")
            st.session_state["results"] = fill(
                questions, r, on_progress=lambda i, n: bar.progress(i / n, f"Answering {i} of {n}"))
            bar.empty()

    results = st.session_state.get("results")
    if results:
        counts = Counter(x["status"] for x in results)
        avg = sum(x["confidence"] for x in results) / len(results)
        a, b, c, d = st.columns(4)
        stat(a, len(results), "Questions")
        stat(b, counts["Drafted"], "✅ Drafted")
        stat(c, counts["Needs review"], "🚩 Needs review")
        stat(d, f"{avg:.0%}", "Average confidence")
        st.write("")

        f1, f2 = st.columns([2, 3])
        show = f1.radio("Show", ["All", "Drafted", "Needs review"], horizontal=True)
        search = f2.text_input("Filter", placeholder="Search questions…", label_visibility="collapsed")
        rows = [x for x in results if (show == "All" or x["status"] == show)
                and search.lower() in x["question"].lower()]
        st.dataframe(
            [{"ID": x["id"], "Status": ("✅ " if x["status"] == "Drafted" else "🚩 ") + x["status"],
              "Question": x["question"], "Answer": x["answer"], "Confidence": x["confidence"],
              "Source": x["citations"][0]["title"], "Link": x["citations"][0]["url"]} for x in rows],
            use_container_width=True, hide_index=True, height=420,
            column_config={
                "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
                "Link": st.column_config.LinkColumn(display_text="Open ↗"),
                "ID": st.column_config.TextColumn(width=170),
                "Status": st.column_config.TextColumn(width=130),
                "Answer": st.column_config.TextColumn(width=105),
                "Question": st.column_config.TextColumn(width="large"),
                "Source": st.column_config.TextColumn(width="medium"),
            },
        )
        with st.expander("🔎 Inspect one answer"):
            pick = st.selectbox("Question", rows, format_func=lambda x: f"{x['id']} · {x['question'][:90]}")
            if pick:
                answer_card(pick)
        buf = io.BytesIO()
        write_answers_xlsx(results, buf)
        st.download_button("⬇️ Download filled questionnaire (.xlsx)", buf.getvalue(), "answers.xlsx",
                           type="primary")
    elif not run:
        st.info("Upload a questionnaire or use the sample, then click **Fill questionnaire**.")

# ---------- evaluation ----------
with evals:
    if RESULTS.exists():
        res = json.loads(RESULTS.read_text())
        best_mode = max(res, key=lambda m: res[m]["mrr"])
        b = res[best_mode]
        st.markdown(f"Measured on **42 real VSAQ questions**, hand-labelled against GitLab's policies. "
                    f"Best method: **{MODES.get(best_mode, best_mode)}**.")
        a, c, d = st.columns(3)
        stat(a, f"{b['hit@1']:.0%}", "Hit@1: right policy ranked first")
        stat(c, f"{b['recall@5']:.0%}", "Recall@5: right policy in top 5")
        stat(d, f"{b['mrr']:.2f}", "MRR (1.0 = always first)")
        st.write("")
        chart = pd.DataFrame.from_dict(
            {SHORT.get(m, m): {"Hit@1": v["hit@1"], "Recall@5": v["recall@5"]} for m, v in res.items()},
            orient="index",
        )
        st.bar_chart(chart, horizontal=True, stack=False, height=260, color=["#4f46e5", "#0ea5e9"])
        st.markdown(
            f"**Knowing when not to answer.** A match-strength score below **{ABSTAIN_STRENGTH}** sends a question "
            "to human review before any AI call. It catches 6 of the 10 questions GitLab's policies don't cover, "
            "and wrongly flags 3 of the 32 they do (AUROC 0.90). With an API key, Claude's own "
            "\"Not covered\" verdict catches the rest."
        )
        st.caption("Run `python eval/run_eval.py --dense --answers` to add embedding search and AI answer accuracy.")
    else:
        st.info("Run `python eval/run_eval.py` to generate results.")

# ---------- how it works ----------
with how:
    steps = [
        ("1 · Ingest", "Policy Markdown is cleaned and split by heading into citable sections, each keeping its "
                       "title, heading path and public URL."),
        ("2 · Retrieve", "BM25 keyword search, plus a compliance synonym map that translates questionnaire wording "
                         "(\"malware\") into policy wording (\"endpoint detection and response\")."),
        ("3 · Gate", "If even the best section matches weakly, the question is flagged for human review instead "
                     "of being answered."),
        ("4 · Draft", "Claude answers only from the top 5 sections and must cite them. Low confidence, no citation "
                      "or \"Not covered\" sends it to review."),
        ("5 · Export", "The filled questionnaire downloads as Excel, with review rows highlighted and every "
                       "citation linked."),
    ]
    for col, (title, body) in zip(st.columns(len(steps)), steps):
        col.markdown(f"<div class='card' style='min-height:300px'><h4>{title}</h4>{esc(body)}</div>",
                     unsafe_allow_html=True)
