import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autofill.answer import draft_answer  # noqa: E402
from autofill.ingest import clean_markdown, doc_url, split_sections  # noqa: E402
from autofill.questionnaire import load_vsaq, read_xlsx, write_questions_xlsx  # noqa: E402
from autofill.retrieve import Retriever, rrf, stem  # noqa: E402
from autofill.fill import build_retriever  # noqa: E402
from autofill import llm as llm_mod  # noqa: E402
from autofill.llm import Chain  # noqa: E402


def test_clean_markdown_strips_front_matter_and_shortcodes():
    meta, body = clean_markdown('---\ntitle: "Policy"\n---\n{{< label name="x" >}}\nSee [the doc](http://x).')
    assert meta["title"] == "Policy"
    assert body == "See the doc."


def test_sections_keep_heading_path():
    sections = list(split_sections("## Policy\n### Access reviews\nReviews happen quarterly."))
    assert sections == [("Policy > Access reviews", "Reviews happen quarterly.")]


def test_doc_url():
    assert doc_url(Path("handbook/security/isms.md")) == "https://handbook.gitlab.com/handbook/security/isms/"


def test_stem_matches_word_forms():
    assert stem("reviews") == stem("reviewed") == "review"


def test_rrf_prefers_items_ranked_high_by_both():
    fused = rrf([[3, 2, 1], [1, 3, 2]])
    assert fused.index(max(fused)) == 1


def test_vsaq_parses_real_questions():
    qs = load_vsaq(ROOT / "data" / "raw" / "vsaq" / "security_privacy_programs.json")
    assert any(q["id"] == "secprog_incidents_procedures" for q in qs)


def test_xlsx_round_trip(tmp_path):
    p = tmp_path / "q.xlsx"
    write_questions_xlsx([{"id": "Q1", "section": "S", "question": "Is data encrypted?"}], p)
    assert read_xlsx(p) == [{"id": "Q1", "section": "S", "question": "Is data encrypted?"}]


def test_retrieves_password_standard():
    r = build_retriever()
    top = r.search("What is the minimum password length?", k=1)[0][0]
    assert top.doc.endswith("password-standard")


def test_uncovered_question_is_flagged(monkeypatch):
    res = draft_answer("Does your company place all externally exposed systems in a DMZ, separated from the internal network by a network filter?", build_retriever(), llm=None)
    assert res["status"] == "Needs review"


class FakeLLM:
    """Stands in for a real provider so the LLM path is tested without a key."""

    name = "Fake"

    def __init__(self, reply):
        self.reply = reply

    def complete(self, prompt):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_llm_answer_with_citation():
    reply = '{"answer": "Yes", "explanation": "Minimum 12 characters.", "citations": [1], "confidence": 0.9}'
    res = draft_answer("What is the minimum password length?", build_retriever(), llm=FakeLLM(reply))
    assert res["status"] == "Drafted" and res["citations"] and res["mode"] == "Fake"


def test_llm_not_covered_goes_to_review():
    reply = '{"answer": "Not covered", "explanation": "", "citations": [], "confidence": 0.2}'
    res = draft_answer("What is the minimum password length?", build_retriever(), llm=FakeLLM(reply))
    assert res["status"] == "Needs review"


def test_chain_falls_through_to_next_provider():
    good = '{"answer": "Yes", "explanation": "ok", "citations": [1], "confidence": 0.9}'
    chain = Chain([FakeLLM(RuntimeError("HTTP 429: quota")), FakeLLM(good)])
    chain.providers[1].name = "Second"
    res = draft_answer("What is the minimum password length?", build_retriever(), llm=chain)
    assert res["status"] == "Drafted" and res["mode"] == "Second"


def test_all_providers_failing_falls_back_to_quote():
    chain = Chain([FakeLLM(RuntimeError("down"))])
    res = draft_answer("What is the minimum password length?", build_retriever(), llm=chain)
    assert res["mode"] == "extractive" and "AI unavailable" in res["explanation"]


def test_env_priority(tmp_path, monkeypatch):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_DISABLED", "1")
    env = tmp_path / ".env"
    env.write_text("GROQ_API_KEY=gsk_test\nGEMINI_API_KEY=AIza_test\n")
    llm_mod.load_env(env)
    llm_mod.get_llm.cache_clear()
    monkeypatch.setattr(llm_mod, "load_env", lambda *a: None)
    names = [p.name for p in llm_mod.get_llm().providers]
    llm_mod.get_llm.cache_clear()
    assert names == ["Gemini", "Groq"]
