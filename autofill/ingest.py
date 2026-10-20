"""Parse policy documents into citable chunks.

Each chunk keeps the document title, its heading path and a public URL, so every
drafted answer can point an auditor to the exact section it came from.
"""
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

HANDBOOK_BASE = "https://handbook.gitlab.com/"
MAX_CHARS = 1200


@dataclass
class Chunk:
    id: str
    doc: str
    title: str
    section: str
    url: str
    text: str


def clean_markdown(md: str) -> tuple[dict, str]:
    """Strip Hugo front matter, shortcodes, HTML and link syntax. Returns (front_matter, body)."""
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", md, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        md = md[m.end():]
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"\{\{[<%].*?[>%]\}\}", "", md, flags=re.S)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"<[^>\n]+>", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return meta, md.strip()


def doc_url(rel: Path) -> str:
    """content path handbook/security/isms.md -> https://handbook.gitlab.com/handbook/security/isms/"""
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "_index":
        parts = parts[:-1]
    return HANDBOOK_BASE + "/".join(parts) + "/"


def split_sections(body: str):
    """Yield (heading_path, text) for each heading-delimited section."""
    path: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            yield " > ".join(h for _, h in path), text

    for line in body.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            yield from flush()
            buf = []
            level, heading = len(m.group(1)), m.group(2).strip()
            path = [(lv, h) for lv, h in path if lv < level] + [(level, heading)]
        else:
            buf.append(line)
    yield from flush()


def pack(text: str, limit: int = MAX_CHARS):
    """Split a long section on paragraph boundaries into pieces of at most ~limit chars."""
    pieces, cur = [], ""
    paras = []
    for para in re.split(r"\n\s*\n", text):
        # long tables and lists have no blank lines, so fall back to line boundaries
        paras.extend(para.splitlines() if len(para) > limit else [para])
    for para in paras:
        if cur and len(cur) + len(para) > limit:
            pieces.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        pieces.append(cur.strip())
    return pieces


def chunk_corpus(raw_dir: Path) -> list[Chunk]:
    chunks = []
    for path in sorted(raw_dir.rglob("*.md")):
        rel = path.relative_to(raw_dir)
        meta, body = clean_markdown(path.read_text(encoding="utf-8"))
        title = meta.get("title") or rel.stem.replace("-", " ").title()
        doc = rel.with_suffix("").as_posix()
        for i, (section, text) in enumerate(split_sections(body)):
            for j, piece in enumerate(pack(text)):
                if len(piece) < 40:  # skip label-only or empty fragments
                    continue
                chunks.append(Chunk(
                    id=f"{doc}#{i}.{j}", doc=doc, title=title, section=section or title,
                    url=doc_url(rel), text=piece,
                ))
    return chunks


def save(chunks: list[Chunk], out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c)) + "\n")


def load(path) -> list[Chunk]:
    return [Chunk(**json.loads(line)) for line in Path(path).open(encoding="utf-8")]


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    chunks = chunk_corpus(root / "data" / "raw" / "gitlab")
    save(chunks, root / "data" / "chunks.jsonl")
    print(f"{len(chunks)} chunks from {len({c.doc for c in chunks})} documents")
