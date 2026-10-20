"""Fill a whole questionnaire.

Usage:  python -m autofill.fill data/samples/vsaq_questionnaire.xlsx answers.xlsx [--mode bm25+expand]
"""
import argparse
from collections import Counter
from pathlib import Path

from .answer import draft_answer
from .ingest import load
from .questionnaire import read_xlsx, write_answers_xlsx
from .retrieve import Retriever

ROOT = Path(__file__).resolve().parent.parent


def build_retriever(mode: str = "bm25+expand") -> Retriever:
    return Retriever(load(ROOT / "data" / "chunks.jsonl"), mode)


def fill(questions: list[dict], retriever: Retriever, on_progress=None) -> list[dict]:
    results = []
    for i, q in enumerate(questions):
        results.append({"id": q["id"], **draft_answer(q["question"], retriever)})
        if on_progress:
            on_progress(i + 1, len(questions))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--mode", default="bm25+expand", choices=["bm25", "bm25+expand", "dense", "hybrid"])
    args = ap.parse_args()
    questions = read_xlsx(args.input)
    results = fill(questions, build_retriever(args.mode))
    write_answers_xlsx(results, args.output)
    counts = Counter(r["status"] for r in results)
    print(f"{len(results)} questions: {counts['Drafted']} drafted, {counts['Needs review']} flagged for review "
          f"-> {args.output}")


if __name__ == "__main__":
    main()
