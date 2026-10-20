"""Pick an LLM provider from .env, in priority order, and fall through on failure.

Priority (first one that is configured and reachable wins):
  1. Google Gemini  - GEMINI_API_KEY   (free tier: https://aistudio.google.com/apikey)
  2. Groq           - GROQ_API_KEY     (free tier: https://console.groq.com/keys)
  3. Ollama         - local server     (free, runs on your machine: https://ollama.com)
  4. Anthropic      - ANTHROPIC_API_KEY (paid)

If a call fails (rate limit, quota, network), the next provider in the chain is tried, so a free
tier running out mid-questionnaire doesn't stop the run. Only the standard library is used for
HTTP, so no extra packages are needed for Gemini, Groq or Ollama.
"""
import json
import os
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 60


def load_env(path: Path = ROOT / ".env"):
    """Minimal .env reader: KEY=value lines; real environment variables take precedence."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {detail}") from None


class Gemini:
    name = "Gemini"

    def __init__(self):
        self.key = os.environ["GEMINI_API_KEY"]
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def complete(self, prompt: str) -> str:
        data = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}},
            {"x-goog-api-key": self.key},
        )
        return data["candidates"][0]["content"]["parts"][0]["text"]


class Groq:
    name = "Groq"

    def __init__(self):
        self.key = os.environ["GROQ_API_KEY"]
        self.model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    def complete(self, prompt: str) -> str:
        data = _post(
            "https://api.groq.com/openai/v1/chat/completions",
            {"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
             "messages": [{"role": "user", "content": prompt}]},
            {"Authorization": f"Bearer {self.key}"},
        )
        return data["choices"][0]["message"]["content"]


class Ollama:
    name = "Ollama"

    def __init__(self):
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.2")

    def available(self) -> bool:
        """Server running and the model pulled (`ollama pull llama3.2`)."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as resp:
                models = [m["name"] for m in json.loads(resp.read()).get("models", [])]
        except (OSError, ValueError):
            return False
        return any(m == self.model or m.startswith(self.model + ":") for m in models)

    def complete(self, prompt: str) -> str:
        data = _post(
            f"{self.host}/api/chat",
            {"model": self.model, "stream": False, "format": "json", "options": {"temperature": 0},
             "messages": [{"role": "user", "content": prompt}]},
            {},
        )
        return data["message"]["content"]


class Anthropic:
    name = "Claude"

    def __init__(self):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    def complete(self, prompt: str) -> str:
        msg = self.client.messages.create(model=self.model, max_tokens=500,
                                          messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class Chain:
    """Tries each provider in order; remembers the one that last worked."""

    def __init__(self, providers: list):
        self.providers = providers
        self.last_used = None
        self.errors: list[str] = []

    @property
    def name(self) -> str:
        return " → ".join(f"{p.name} ({p.model})" for p in self.providers)

    def complete(self, prompt: str) -> str:
        for p in self.providers:
            try:
                out = p.complete(prompt)
                self.last_used = p
                return out
            except Exception as e:  # rate limit, quota, network: fall through to the next provider
                self.errors.append(f"{p.name}: {e}")
        raise RuntimeError("All LLM providers failed: " + " | ".join(self.errors[-len(self.providers):]))


@lru_cache(maxsize=1)
def get_llm():
    """The provider chain configured in .env / the environment, or None for offline mode."""
    load_env()
    providers = []
    if os.environ.get("GEMINI_API_KEY"):
        providers.append(Gemini())
    if os.environ.get("GROQ_API_KEY"):
        providers.append(Groq())
    if os.environ.get("OLLAMA_DISABLED", "").lower() not in ("1", "true"):
        ollama = Ollama()
        if ollama.available():
            providers.append(ollama)
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            providers.append(Anthropic())
        except ImportError:
            pass
    return Chain(providers) if providers else None
