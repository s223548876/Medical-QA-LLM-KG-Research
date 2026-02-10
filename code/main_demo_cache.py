from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import json
import re
from typing import Dict, List, Any, Tuple

app = FastAPI()

DEMO_BANK_PATH = Path("demo_bank.json")
STATIC_DIR = Path("static")

def load_demo_bank() -> List[Dict[str, Any]]:
    if not DEMO_BANK_PATH.exists():
        return []
    with DEMO_BANK_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)

def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def token_set(text: str) -> set:
    return set(normalize_text(text).split())

def jaccard_similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def find_best_match(user_question: str, bank: List[Dict[str, Any]]) -> Tuple[Dict[str, Any] | None, float]:
    user_tokens = token_set(user_question)
    best_item = None
    best_score = -1.0

    for item in bank:
        q = item.get("question", "")
        score = jaccard_similarity(user_tokens, token_set(q))
        if score > best_score:
            best_score = score
            best_item = item

    return best_item, best_score

@app.get("/demo/search")
def demo_search(question: str) -> Dict[str, Any]:
    bank = load_demo_bank()
    if not bank:
        return {"error": "demo_bank.json not found or empty"}

    best_item, score = find_best_match(question, bank)
    if best_item is None:
        return {"error": "no match found"}

    # 你可以設定一個門檻，太低就提示「請改寫問題」
    MIN_SCORE = 0.12
    if score < MIN_SCORE:
        return {
            "matched": False,
            "similarity": round(score, 3),
            "message": "未找到匹配項。請使用已知的醫學主題（例如，氣喘、糖尿病、中風）重新表達您的問題。"
        }

    # A/B 固定（也可隨機對調，但你這裡是 demo，不是正式評估，固定更直覺）
    return {
        "matched": True,
        "similarity": round(score, 3),
        "mapped_to": {
            "bank_id": best_item.get("bank_id"),
            "qtype": best_item.get("qtype"),
            "question": best_item.get("question")
        },
        "answers": {
            "a_label": "Answer A",
            "a_text": best_item.get("answer_llm_only", ""),
            "b_label": "Answer B",
            "b_text": best_item.get("answer_llm_kg", "")
        }
    }

# Static frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))
