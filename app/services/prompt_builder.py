from typing import List


def facet_limits(qtype: str):
    if qtype == "definition":
        return dict(max_items=6, max_chars=260, num_predict=220)
    if qtype in ("symptoms",):
        return dict(max_items=12, max_chars=380, num_predict=340)
    if qtype in ("treatments",):
        return dict(max_items=14, max_chars=400, num_predict=360)
    return dict(max_items=8, max_chars=300, num_predict=260)


def facet_text(qtype: str) -> str:
    if qtype == "symptoms":
        return "症狀"
    if qtype == "treatments":
        return "治療方式"
    return "定義"


def compress_pairs(pairs: List[str], max_items: int = 8, max_chars: int = 300) -> List[str]:
    out = []
    for p in (pairs or [])[:max_items]:
        t = (p or "").replace("\n", " ").strip()
        if len(t) > max_chars:
            t = t[:max_chars].rsplit(" ", 1)[0] + " ..."
        if t:
            out.append(t)
    return out


def build_prompt_kg(qtype: str, question: str, pairs: List[str]) -> str:
    limits = facet_limits(qtype)
    bullets = compress_pairs(
        pairs, max_items=limits["max_items"], max_chars=limits["max_chars"])
    rels = "- " + "\n- ".join(bullets) if bullets else "(無明確證據)"

    facet = facet_text(qtype)
    guidance = {
        "definition": "請用 1 到 2 句中文下定義，優先沿用 Evidence 中的醫學詞彙，不要加入背景段落。",
        "symptoms": "請用中文列出 3 到 6 個重點症狀，可用條列或逗號分隔，不要加入不必要前言。",
        "treatments": "請用中文列出 3 到 6 個治療重點，至少包含 1 到 2 項非藥物作法（例如生活型態、復健、行為或程序）。不要預設一定用藥。",
    }.get(qtype, "請用中文簡潔回答。")

    return f"""你是醫療問答助理，請以繁體中文回答。

任務：只回答「{facet}」。
規則：
1. 內容要精簡（最多 3 句或 6 個條列）。
2. 優先採用 Evidence 中的詞彙，不要額外延伸背景。
3. 若 Evidence 沒有明確提到「{facet}」，請只回覆：目前提供的資料未明確指出{facet}。

問題：
{question}

Evidence（由知識圖譜壓縮）：
{rels}

寫作指示：
{guidance}
"""
