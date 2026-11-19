"""Client LLM optionnel : Ollama en local, ou Groq/OpenAI via API.
Si aucun LLM n'est disponible, retourne None (le système fonctionne en heuristique pure)."""
import os
import requests

class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "none")  # ollama | groq | openai | none
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")

    def is_available(self) -> bool:
        if self.provider == "none":
            return False
        try:
            if self.provider == "ollama":
                r = requests.get(f"{self.base_url}/api/tags", timeout=2)
                return r.status_code == 200
            return bool(self.api_key)
        except Exception:
            return False

    def ask(self, prompt: str, system: str = "") -> str | None:
        if not self.is_available():
            return None
        try:
            if self.provider == "ollama":
                r = requests.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": f"{system}\n\n{prompt}", "stream": False},
                    timeout=120,
                )
                return r.json().get("response", "").strip()
            if self.provider == "groq":
                return self._openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions", prompt, system)
            if self.provider == "openai":
                return self._openai_compatible(
                    "https://api.openai.com/v1/chat/completions", prompt, system)
        except Exception as e:
            print(f"[LLM] Erreur : {e}")
        return None

    def _openai_compatible(self, url, prompt, system):
        r = requests.post(url, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }, json={
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or "Tu es un expert DBA."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }, timeout=120)
        return r.json()["choices"][0]["message"]["content"].strip()