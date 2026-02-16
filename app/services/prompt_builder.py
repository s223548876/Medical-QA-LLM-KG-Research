from typing import List
from collections import Counter
import re


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


def _clean_term(term: str) -> str:
    t = (term or "").strip()
    t = re.sub(r"\[[^\]]+\]", "", t)
    t = t.replace("(disorder)", "").replace("(finding)", "").replace("(procedure)", "")
    t = " ".join(t.split())
    return t


def extract_condition_categories(pairs: List[str]) -> tuple[str, list[str]]:
    rows: list[tuple[str, str]] = []
    for p in pairs or []:
        if "→" not in p:
            continue
        source, target = p.split("→", 1)
        source = _clean_term(source)
        target = _clean_term(target)
        if source and target:
            rows.append((source, target))

    if not rows:
        return "", []

    source_counter = Counter(src for src, _ in rows)
    condition = source_counter.most_common(1)[0][0]

    target_counter = Counter(tgt for src, tgt in rows if src == condition)
    categories = [target for target, _ in target_counter.most_common(3)]
    return condition, categories


def build_evidence_narrative(pairs: List[str]) -> str:
    condition, categories = extract_condition_categories(pairs)
    if not condition or len(categories) < 2:
        return "目前知識圖譜對此問題的直接證據有限，僅提供概略定位。"

    category_text = "、".join(categories)
    return (
        f"{condition}在知識圖譜中主要落在{category_text}等分類。"
        f"目前可先用這些分類定位理解其臨床脈絡。"
    )


def build_prompt_kg(qtype: str, question: str, pairs: List[str]) -> str:
    return build_prompt_kg_with_mode(qtype=qtype, question=question, pairs=pairs, mode="research")


def build_prompt_kg_with_mode(
    qtype: str,
    question: str,
    pairs: List[str],
    mode: str = "research",
) -> str:
    limits = facet_limits(qtype)
    bullets = compress_pairs(
        pairs, max_items=limits["max_items"], max_chars=limits["max_chars"])
    rels = "- " + "\n- ".join(bullets) if bullets else "(無明確證據)"
    evidence_narrative = build_evidence_narrative(pairs)
    short_bullets = compress_pairs(pairs, max_items=3, max_chars=120)
    short_bullet_text = "- " + "\n- ".join(short_bullets) if short_bullets else "- (無)"

    facet = facet_text(qtype)
    guidance = {
        "definition": "請用 1 到 2 句中文下定義，優先沿用 Evidence 中的醫學詞彙，不要加入背景段落。",
        "symptoms": "請用中文列出 3 到 6 個重點症狀，可用條列或逗號分隔，不要加入不必要前言。",
        "treatments": "請用中文列出 3 到 6 個治療重點，至少包含 1 到 2 項非藥物作法（例如生活型態、復健、行為或程序），不要預設一定用藥。",
    }.get(qtype, "請用中文簡潔回答。")

    if mode == "user":
        return f"""你是醫療問答助理，請以繁體中文回答。

請嚴格依照以下兩段格式輸出（標題不可改）：
[根據知識圖譜]
- 僅能使用 Evidence 的內容整理重點。
- 不要逐字抄寫 Evidence 的長清單，請轉寫成 1 到 2 句自然中文。
- 若同一分類詞重複出現，請去重後再表達。
- 不要輸出其他段落標題（例如「治療重點」）。
- 若 Evidence 對「{facet}」不足，請明確寫「目前知識圖譜對{facet}的直接證據有限，以下先提供分類定位。」

[一般性補充（LLM 常識，非知識圖譜證據）]
- 提供 1 到 3 點一般醫學常識補充，需與題目相關。
- 治療題至少要有 1 點非藥物方案（如生活調整、復健、行為治療或程序）。

問題：
{question}

Evidence 摘要（優先使用）：
{evidence_narrative}

Evidence 細節（可選引用，最多取 3 條）：
{short_bullet_text}

寫作指示：
{guidance}
"""

    return f"""你是醫療問答助理，請以繁體中文回答。

任務：只回答「{facet}」。
規則：
1. 內容要精簡（最多 3 句或 6 個條列）。
2. 僅可使用 Evidence，不可加入外部推測或常識補充。
3. 若 Evidence 沒有明確提到「{facet}」，請明確說明「Evidence不足」，不要硬湊答案。
4. 不得輸出任何「一般性補充」段落。
5. 不得輸出「(非 Evidence)」或「(Non-Evidence)」字樣。

問題：
{question}

Evidence（由知識圖譜壓縮）：
{rels}

寫作指示：
{guidance}
"""
