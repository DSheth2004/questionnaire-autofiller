"""Measure retrieval quality and abstention on the gold set.

Gold set: 42 real questions from Google's VSAQ, each hand-labelled with the GitLab policy
documents that answer it (32), or with nothing when GitLab's published policies do not
cover it (10). Labels were checked by reading the cited sections.

Usage:  python eval/run_eval.py              # lexical modes, no network needed
        python eval/run_eval.py --dense      # also dense and hybrid (needs the embedding model)
        python eval/run_eval.py --answers    # also LLM answer drafting (needs a provider in .env)
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autofill.ingest import load  # noqa: E402
from autofill.questionnaire import load_vsaq  # noqa: E402
from autofill.retrieve import DenseIndex, Retriever  # noqa: E402

K = 5


def load_gold():
    questions = {}
    for f in ("security_privacy_programs", "infrastructure", "webapp"):
        for q in load_vsaq(ROOT / "data" / "raw" / "vsaq" / f"{f}.json"):
            questions[q["id"]] = q["question"]
    gold = [json.loads(l) for l in (ROOT / "eval" / "gold.jsonl").open()]
    for g in gold:
        g["question"] = questions[g["id"]]
    return gold


def doc_name(chunk) -> str:
    return chunk.doc.rsplit("/", 1)[-1]


def eval_retrieval(retriever, gold):
    hit1, recall, rr, lat = [], [], [], []
    misses = []
    for g in gold:
        if not g["relevant_docs"]:
            continue
        t = time.perf_counter()
        results = retriever.search(g["question"], k=K)
        lat.append(time.perf_counter() - t)
        docs = [doc_name(c) for c, _ in results]
        rel = set(g["relevant_docs"])
        first = next((i for i, d in enumerate(docs) if d in rel), None)
        hit1.append(first == 0)
        recall.append(first is not None)
        rr.append(0 if first is None else 1 / (first + 1))
        if first is None:
            misses.append(g["id"])
    return {
        "hit@1": statistics.mean(hit1),
        f"recall@{K}": statistics.mean(recall),
        "mrr": statistics.mean(rr),
        "ms/query": 1000 * statistics.mean(lat),
        "misses": misses,
    }


def eval_abstention(retriever, gold):
    """How well match strength separates covered from not-covered questions."""
    from autofill.answer import ABSTAIN_STRENGTH

    rows = [(retriever.match_strength(g["question"]), bool(g["relevant_docs"])) for g in gold]
    pos = [s for s, covered in rows if covered]
    neg = [s for s, covered in rows if not covered]
    auroc = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
    return {
        "auroc": round(auroc, 2),
        "threshold": ABSTAIN_STRENGTH,
        "not-covered caught": f"{sum(s < ABSTAIN_STRENGTH for s in neg)}/{len(neg)}",
        "covered wrongly flagged": f"{sum(s < ABSTAIN_STRENGTH for s in pos)}/{len(pos)}",
    }


def eval_answers(retriever, gold):
    from autofill.answer import draft_answer

    correct_flag, cited_ok = [], []
    for g in gold:
        r = draft_answer(g["question"], retriever)
        flagged = r["status"] != "Drafted"
        correct_flag.append(flagged == (not g["relevant_docs"]))
        if g["relevant_docs"] and not flagged:
            cited_ok.append(any(c["doc"].rsplit("/", 1)[-1] in g["relevant_docs"] for c in r["citations"]))
    return {
        "drafted-vs-review decision accuracy": statistics.mean(correct_flag),
        "citation precision (drafted answers)": statistics.mean(cited_ok) if cited_ok else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense", action="store_true")
    ap.add_argument("--answers", action="store_true")
    args = ap.parse_args()

    chunks = load(ROOT / "data" / "chunks.jsonl")
    gold = load_gold()
    print(f"Corpus: {len(chunks)} chunks | gold: {len(gold)} questions "
          f"({sum(1 for g in gold if g['relevant_docs'])} covered)\n")

    modes = ["bm25", "bm25+expand"]
    dense = None
    if args.dense:
        dense = DenseIndex(chunks)
        modes += ["dense", "hybrid"]

    results = {}
    for mode in modes:
        r = Retriever(chunks, mode, dense=dense)
        results[mode] = eval_retrieval(r, gold)

    print(f"| Retriever | Hit@1 | Recall@{K} | MRR | ms/query |")
    print("|---|---|---|---|---|")
    for mode, m in results.items():
        print(f"| {mode} | {m['hit@1']:.0%} | {m[f'recall@{K}']:.0%} | {m['mrr']:.2f} | {m['ms/query']:.1f} |")
    for mode, m in results.items():
        if m["misses"]:
            print(f"  {mode} misses: {', '.join(m['misses'])}")

    best = Retriever(chunks, "hybrid" if dense else "bm25+expand", dense=dense)
    abstention = eval_abstention(best, gold)
    print("\nAbstention (flag for human review):", abstention)
    (ROOT / "eval" / "abstention.json").write_text(json.dumps(abstention, indent=2))
    if args.answers:
        print("Answer drafting:", eval_answers(best, gold))
    out = ROOT / "eval" / "results.json"
    out.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
