import requests
from core.settings import settings


def call_llm(
    prompt: str,
    model_name: str = "cwchang/llama-3-taiwan-8b-instruct",
    num_predict: int = 256,
) -> str:
    try:
        ollama_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        r = requests.post(
            ollama_url,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": num_predict,
                    "repeat_penalty": 1.05,
                },
            },
            timeout=120,
        )
        r.raise_for_status()
        ans = (r.json().get("response") or "").strip()
        return ans
    except Exception as e:
        return f"呼叫 LLM 失敗：{e}"
