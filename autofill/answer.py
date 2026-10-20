"""Draft an answer to one questionnaire question, grounded in retrieved policy sections.

When an LLM is configured in .env (Gemini, then Groq, then a local Ollama, then Claude; see llm.py),
it writes the answer from the retrieved excerpts only and must cite them. Without one, an extractive
fallback quotes the most relevant policy sentences, so the tool still works (and is testable) offline. Either way, a question the policies do not cover is
flagged for human review instead of being answered.
"""
import json
import re

from .llm import get_llm
from .retrieve import Retriever, tokenize

# Below this match strength the policies probably don't cover the question. Chosen on eval/gold.jsonl
# to keep false flags under ~10%; the LLM's own "Not covered" verdict catches the rest.
ABSTAIN_STRENGTH = 0.35
REVIEW_CONFIDENCE = 0.6

PROMPT = """You are filling in a customer's security questionnaire on behalf of the company whose policy excerpts are below.

Answer ONLY from the excerpts. If they do not clearly answer the question, say "Not covered" — never guess or rely on general knowledge.

Question: {question}

Policy excerpts:
{excerpts}

Reply with JSON only, no prose around it:
{{"answer": "Yes" | "No" | "Partial" | "Not covered",
  "explanation": "1-3 sentences a security reviewer would accept, stating what the policy requires",
  "citations": [excerpt numbers you relied on],
  "confidence": number between 0 and 1}}"""


def _citation(chunk):
    return {"doc": chunk.doc, "title": chunk.title, "section": chunk.section, "url": chunk.url, "chunk_id": chunk.id}


def _best_sentences(question: str, text: str, n: int = 2) -> str:
    q = set(tokenize(question))
    sentences = [s.strip(" -*|") for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 25]
    ranked = sorted(sentences, key=lambda s: -len(q & set(tokenize(s))))
    return " ".join(ranked[:n])


def _extractive(base, question, top, strength, note=""):
    return {
        **base,
        "answer": "See policy",
        "explanation": _best_sentences(question, top.text) + note,
        "confidence": round(min(strength, 1.0), 2),
        "status": "Drafted",
        "citations": [_citation(top)],
        "mode": "extractive",
    }


def draft_answer(question: str, retriever: Retriever, k: int = 5, llm="auto") -> dict:
    """llm: "auto" uses the provider chain from .env; None forces offline mode; or pass any object with
    .complete(prompt) -> str (used by the tests)."""
    results = retriever.search(question, k=k)
    top = results[0][0]
    strength = retriever.match_strength(question)
    base = {"question": question, "match_strength": round(strength, 2)}

    if strength < ABSTAIN_STRENGTH:
        return {
            **base,
            "answer": "Not covered",
            "explanation": "No policy section clearly addresses this question. Closest match shown for the reviewer.",
            "confidence": round(min(strength, 1.0), 2),
            "status": "Needs review",
            "citations": [_citation(top)],
            "mode": "abstain",
        }

    if llm == "auto":
        llm = get_llm()
    if llm is None:
        return _extractive(base, question, top, strength)

    excerpts = "\n\n".join(
        f"[{i + 1}] {c.title} > {c.section}\n{c.text}" for i, (c, _) in enumerate(results)
    )
    try:
        text = llm.complete(PROMPT.format(question=question, excerpts=excerpts))
    except Exception as e:
        return _extractive(base, question, top, strength, note=f" [AI unavailable: {str(e)[:120]}]")
    try:
        data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    except (AttributeError, json.JSONDecodeError):
        data = {"answer": "Not covered", "explanation": "Model reply could not be parsed.", "citations": [], "confidence": 0}

    cited = [results[n - 1][0] for n in data.get("citations", []) if isinstance(n, int) and 1 <= n <= len(results)]
    confidence = float(data.get("confidence", 0))
    needs_review = data.get("answer") == "Not covered" or confidence < REVIEW_CONFIDENCE or not cited
    return {
        **base,
        "answer": data.get("answer", "Not covered"),
        "explanation": data.get("explanation", ""),
        "confidence": round(confidence, 2),
        "status": "Needs review" if needs_review else "Drafted",
        "citations": [_citation(c) for c in (cited or [top])],
        "mode": getattr(getattr(llm, "last_used", None) or llm, "name", "llm"),
    }
