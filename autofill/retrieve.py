"""Search over policy chunks: BM25, compliance-aware query expansion, optional dense embeddings, and hybrid fusion.

BM25 and expansion are pure Python and always available. Dense retrieval uses fastembed
(a small ONNX model, no GPU) when it is installed and the model can be downloaded.
"""
import math
import re
from collections import Counter

from .ingest import Chunk

STOPWORDS = set("""
a an and are as at be by can do does for from has have how if in into is it its of on or our
such that the their them there these they this to was we were what when where which who will with
you your yours any all also other than then so not no yes may must should would could each per
company companies employees ensure place process processes procedures system systems regularly
""".split())

# Questionnaires and policies describe the same control in different words. Each entry maps a
# trigger (matched as a phrase in the question) to the vocabulary policies tend to use instead.
SYNONYMS = {
    "mfa": "multi-factor authentication two-factor 2fa",
    "two-factor": "mfa multi-factor",
    "encrypt": "encryption cryptographic aes",
    "hard disk": "full-disk encryption laptop",
    "malware": "endpoint detection response antivirus",
    "antivirus": "endpoint detection response malware",
    "patch": "vulnerability remediation sla update",
    "security updates": "vulnerability remediation sla patch",
    "penetration test": "pentest penetration testing annually",
    "incident": "sirt security incident response",
    "service provider": "vendor third-party tprm",
    "subcontractor": "vendor third-party tprm",
    "outsourc": "vendor third-party tprm",
    "training": "awareness training",
    "temps": "contractors tsps",
    "interns": "contractors team members",
    "background check": "background screening",
    "log": "logging logs audit",
    "backup": "recovery restore business continuity",
    "need-to-know": "least privilege access review",
    "administrative access": "access review privileged",
    "change management": "change request approval",
    "change review board": "change approval",
    "password": "credential",
    "ssl": "tls cryptographic cipher",
    "tls": "cryptographic cipher",
    "forward secrecy": "ecdhe tls cipher",
    "cipher": "tls cryptographic",
    "report security vulnerabilities": "bug bounty hackerone responsible disclosure",
    "researchers": "bug bounty hackerone",
    "standard": "iso 27001 isms",
    "security program": "isms information security management system",
    "job description": "roles responsibilities job descriptions",
    "mobile media": "removable storage usb external",
    "thumb drive": "removable storage usb",
    "release testing": "testing approval merge request review",
    "audit": "internal audit assessment",
}

TOKEN = re.compile(r"[a-z0-9][a-z0-9\-/]*")


def tokenize(text: str) -> list[str]:
    toks = []
    for t in TOKEN.findall(text.lower()):
        t = t.strip("-/")
        if t and t not in STOPWORDS and len(t) > 1:
            toks.append(stem(t))
    return toks


def stem(t: str) -> str:
    """A deliberately light suffix stripper (review/reviews/reviewed). A heavier stemmer scored worse on the eval set."""
    for suf in ("ations", "ation", "ings", "ing", "ies", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def expand(question: str) -> list[str]:
    q = question.lower()
    extra = []
    for trigger, words in SYNONYMS.items():
        if trigger in q:
            extra.extend(tokenize(words))
    return extra


def doc_text(c: Chunk) -> str:
    # headings carry a lot of signal in policy documents, so they are repeated to weight them up
    return f"{c.title} {c.section} {c.section} {c.text}"


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.4, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(doc_text(c))) for c in chunks]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / len(self.lens)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, weighted_terms: dict[str, float]) -> list[float]:
        out = []
        for d, L in zip(self.docs, self.lens):
            s = 0.0
            for t, w in weighted_terms.items():
                f = d.get(t)
                if f:
                    s += w * self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            out.append(s)
        return out


class DenseIndex:
    """Embedding search with fastembed. Raises at construction if the model is unavailable."""

    def __init__(self, chunks: list[Chunk], model: str = "BAAI/bge-small-en-v1.5"):
        import numpy as np
        from fastembed import TextEmbedding

        self.np = np
        self.model = TextEmbedding(model)
        self.matrix = np.array(list(self.model.embed([doc_text(c) for c in chunks])))
        self.matrix /= np.linalg.norm(self.matrix, axis=1, keepdims=True)

    def scores(self, question: str) -> list[float]:
        q = self.np.array(list(self.model.query_embed(question)))[0]
        q /= self.np.linalg.norm(q)
        return list(self.matrix @ q)


class Retriever:
    """mode: 'bm25' | 'bm25+expand' | 'dense' | 'hybrid' (bm25+expand fused with dense via RRF)."""

    def __init__(self, chunks: list[Chunk], mode: str = "bm25+expand", dense: DenseIndex | None = None):
        self.chunks = chunks
        self.mode = mode
        self.bm25 = BM25(chunks)
        self.dense = dense
        if mode in ("dense", "hybrid") and dense is None:
            self.dense = DenseIndex(chunks)

    def _lexical(self, question: str, use_expansion: bool) -> list[float]:
        terms = Counter({t: 1.0 for t in tokenize(question)})
        if use_expansion:
            for t in expand(question):
                terms[t] = max(terms[t], 0.5)
        return self.bm25.scores(terms)

    def search(self, question: str, k: int = 5) -> list[tuple[Chunk, float]]:
        if self.mode == "bm25":
            scores = self._lexical(question, False)
        elif self.mode == "bm25+expand":
            scores = self._lexical(question, True)
        elif self.mode == "dense":
            scores = self.dense.scores(question)
        elif self.mode == "hybrid":
            scores = rrf([self._lexical(question, True), self.dense.scores(question)])
        else:
            raise ValueError(self.mode)
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(self.chunks[i], scores[i]) for i in ranked]

    def match_strength(self, question: str) -> float:
        """How well the best section matches, relative to a perfect match on every question term.

        The lexical BM25 score of the top chunk divided by the sum of the question terms' IDF, so it is
        comparable across short and long questions. Low values mean the policies probably don't
        cover the question; used to flag it for human review before spending an LLM call.
        """
        terms = set(tokenize(question))
        if not terms:
            return 0.0
        n = len(self.chunks)
        unseen = math.log(1 + (n + 0.5) / 0.5)  # a term no policy uses at all counts as maximally specific
        ideal = sum(self.bm25.idf.get(t, unseen) for t in terms)
        top = max(self._lexical(question, True))
        return top / ideal


def rrf(score_lists: list[list[float]], k: int = 60) -> list[float]:
    """Reciprocal rank fusion: robust to the very different scales of BM25 and cosine scores."""
    fused = [0.0] * len(score_lists[0])
    for scores in score_lists:
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        for rank, i in enumerate(order):
            fused[i] += 1.0 / (k + rank + 1)
    return fused
