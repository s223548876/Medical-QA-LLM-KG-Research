from typing import List, Dict
from time import perf_counter
import re
from fastapi import Request
from core.security import require_api_key
from core.settings import settings
from repositories import neo4j_repository
from clients import ollama_client
from services import nlp_service, prompt_builder


ENABLE_FALLBACK = True
ENABLE_LOW_OVERLAP = False
SECTION_MARKERS = [
    "\n[一般性補充",
    "\n## 一般性補充",
    "\n一般性補充：",
]


def _ensure_user_sections(answer: str) -> str:
    text = (answer or "").strip()
    if not text:
        return text
    second_title = "[一般性補充（LLM 常識，非知識圖譜證據）]"
    text = re.sub(r"\[\s*一般性補充（?\s*非\s*Evidence\s*）?\s*\]", second_title, text, flags=re.I)
    text = re.sub(r"^\s*一般性補充：", second_title, text, flags=re.I | re.M)

    split_match = re.search(
        r"(?:^|\n)(?:\[\s*一般性補充[^\]]*\]|##\s*一般性補充|一般性補充：)",
        text,
        flags=re.I,
    )
    if split_match:
        first = text[:split_match.start()].strip()
        second = text[split_match.end():].strip()
    else:
        first = text
        second = "- 目前資料不足，請結合臨床評估與醫師建議。"

    first = re.sub(r"^\[?根據知識圖譜\]?\s*[-:：]?\s*", "", first)
    first = re.sub(r"\[\s*一般性補充[^\]]*\]", "", first, flags=re.I).strip()

    second = re.sub(r"^\s*[-:：]\s*", "", second).strip()
    second_lines = [line.strip() for line in second.splitlines() if line.strip()]
    if len(second_lines) > 3:
        second = "\n".join(second_lines[:3])
    elif second_lines:
        second = "\n".join(second_lines)
    if second and not second.startswith(("-", "1.", "1、", "1)")):
        second = f"- {second}"

    return f"[根據知識圖譜]\n{first}\n\n{second_title}\n{second}"


def _finalize_research_answer(text: str) -> str:
    output = (text or "").strip()
    if not output:
        return output

    output = re.sub(r"[（(]\s*非\s*Evidence\s*[）)]", "", output, flags=re.I)
    output = re.sub(r"[（(]\s*Non[- ]?Evidence\s*[）)]", "", output, flags=re.I)

    section_idx = -1
    for marker in SECTION_MARKERS:
        idx = output.find(marker)
        if idx != -1 and (section_idx == -1 or idx < section_idx):
            section_idx = idx
    if section_idx != -1:
        output = output[:section_idx].rstrip()
    return output


def _finalize_answer_by_mode(answer: str, mode: str) -> str:
    if mode == "user":
        return _ensure_user_sections(answer)
    if mode == "research":
        return _finalize_research_answer(answer)
    return answer


def _research_insufficient_answer(qtype: str, evidence_level: str, pairs: list[str]) -> str:
    facet_name = {"symptoms": "症狀", "treatments": "治療"}.get(qtype, "此題型")
    narrative = prompt_builder.build_evidence_narrative(pairs)
    if evidence_level == "weak":
        limitation = f"目前知識圖譜對「{facet_name}」僅有分類定位，缺乏直接證據，暫不提供具體{facet_name}清單。"
    else:
        limitation = f"目前知識圖譜對「{facet_name}」沒有可用直接證據，暫不提供具體{facet_name}內容。"
    return f"{narrative}\n{limitation}"


def _normalize_term(t: str) -> str:
    s = (t or "").strip()
    if not s:
        return ""
    s = re.sub(r"\[[^\]]+\]", "", s)
    s = re.sub(r"^[A-Z]{2,}\s*-\s*", "", s)
    s = s.replace("(disorder)", "").replace("(finding)", "").replace("(procedure)", "")
    s = s.replace("  ", " ").strip(" -_;:,")
    return " ".join(s.split())


def _normalize_lookup_term(term: str) -> str:
    return " ".join((term or "").strip().lower().split())


def _natural_lite_answer(question: str, pairs: list[str], qtype: str) -> str:
    parsed: list[tuple[str, str]] = []
    for p in pairs[:12]:
        if "→" not in p:
            continue
        src, tgt = p.split("→", 1)
        src_n = _normalize_term(src)
        tgt_n = _normalize_term(tgt)
        if src_n and tgt_n:
            parsed.append((src_n, tgt_n))

    if not parsed:
        if qtype == "symptoms":
            return "目前知識圖譜以分類資訊為主，尚未提供足夠症狀細節；建議依實際不適由醫師評估。"
        if qtype == "treatments":
            return "目前知識圖譜主要提供分類資訊，治療方案仍需依病因與嚴重度由醫師個別評估。"
        return "目前知識圖譜可用資訊有限，建議結合臨床背景再確認定義。"

    condition = parsed[0][0]
    categories: list[str] = []
    for _, tgt in parsed:
        if tgt not in categories:
            categories.append(tgt)
        if len(categories) >= 3:
            break
    cat_text = "、".join(categories)
    english_heavy = False
    if cat_text:
        en_chars = sum(1 for ch in cat_text if ("a" <= ch.lower() <= "z"))
        english_heavy = en_chars / max(1, len(cat_text)) > 0.45

    cn_alias = {
        "sleep apnea syndrome": "睡眠呼吸中止症",
        "sleep apnea": "睡眠呼吸中止症",
        "anemia": "貧血",
        "hypertension": "高血壓",
        "asthma": "氣喘",
        "diabetes": "糖尿病",
    }
    cond_l = condition.lower()
    for k, v in cn_alias.items():
        if k in cond_l:
            condition = v
            break

    if qtype == "symptoms":
        if english_heavy:
            return (
                f"{condition}在知識圖譜中屬於相關系統疾病分類。"
                "目前資料偏向分類定位，症狀細節不足，仍需依臨床評估確認。"
            )
        return (
            f"{condition}在知識圖譜中多歸於{cat_text}等類別。"
            "現有資料主要呈現分類關係，症狀仍需結合病程與身體檢查綜合判斷。"
        )
    if qtype == "treatments":
        if english_heavy:
            return (
                f"{condition}在知識圖譜中主要被歸類為相關系統疾病。"
                "目前證據以分類關係為主，尚不足以直接推導特定藥物。臨床上通常會先評估病因與嚴重度，再規劃個別化治療與追蹤。"
            )
        return (
            f"{condition}在知識圖譜中主要歸類於{cat_text}。"
            "目前資料以分類關係為主，尚缺乏完整處置細節；實際治療仍需依病因、嚴重度與共病情況做個別化安排。"
        )
    if english_heavy:
        return f"{condition}可視為相關系統疾病概念，知識圖譜目前主要提供其分類定位。"
    return (
        f"{condition}可視為與{cat_text}相關的臨床概念。"
        "目前知識圖譜主要提供分類資訊，仍需結合臨床資料做完整判讀。"
    )


def generate_answer(question: str, subgraph: list, lite: int = 0, qtype: str = "definition") -> str:
    return generate_answer_with_mode(question=question, subgraph=subgraph, lite=lite, qtype=qtype, mode="research")


def generate_answer_with_mode(
    question: str,
    subgraph: list,
    lite: int = 0,
    qtype: str = "definition",
    mode: str = "research",
) -> str:
    if not subgraph:
        return "--找不到足夠的知識圖資訊來回答問題。--"

    pairs = [
        f"{r.get('sourceTerm')} → {r.get('targetTerm')}"
        for r in subgraph
        if r.get('sourceTerm') and r.get('targetTerm')
    ]
    top_pairs = pairs[:10]

    if lite:
        return _natural_lite_answer(question, top_pairs, qtype)

    prompt = prompt_builder.build_prompt_kg_with_mode(
        qtype=qtype,
        question=question,
        pairs=pairs,
        mode=mode,
    )
    limits = prompt_builder.facet_limits(qtype)
    return ollama_client.call_llm(prompt, num_predict=limits["num_predict"])


def llm_only(
    request: Request,
    question: str | None = None,
    model: str | None = None,
    qtype_hint: str | None = None,
):
    require_api_key(request, settings)
    hint = (
        qtype_hint
        or request.query_params.get("qtype_hint")
        or request.query_params.get("qtype")
        or ""
    ).strip().lower()
    if hint in {"definition", "symptoms", "treatments"}:
        qtype = hint
    else:
        qtype = nlp_service.detect_qtype(question)
    if qtype == "symptoms":
        prompt = f"""你是醫療助理，請以繁體中文回答，約 80 字內。

問題：{question}

請先用 1 句說明疾病，再以「常見症狀包括：」開頭，列出 4 到 6 個重點症狀。"""
    elif qtype == "treatments":
        prompt = f"""你是醫療助理，請以繁體中文回答，約 80 字內。

問題：{question}

請先用 1 句定義疾病，再以「治療方式包括：」開頭，列出 4 到 6 項治療選項。
至少包含 1 到 2 項非藥物方式（如生活調整、復健、行為治療、裝置或手術），不要假設所有治療都需用藥。"""
    else:
        prompt = f"""你是醫療助理，請以繁體中文回答，約 80 字內。

問題：{question}

請先給出清楚定義，再補 2 到 3 個重點特徵或分類資訊。"""
    llm_tokens = {"definition": 180, "symptoms": 220, "treatments": 220}
    ans = ollama_client.call_llm(
        prompt,
        model_name=model or "cwchang/llama-3-taiwan-8b-instruct",
        num_predict=llm_tokens.get(qtype, 200),
    )
    return {
        "question": question,
        "qtype": qtype,
        "results": [{
            "term": None,
            "conceptId": None,
            "subgraph_size": 0,
            "subgraph_summary": [],
            "answer": ans,
            "relevance": 1.0
        }]
    }


def query(request: Request,
          question: str,
          topic_key: str | None = None,
          qtype_hint: str | None = None,
          mode: str = "research",
          lite: int = 0,
          max_k: int = 1,
          model: str | None = None,
          symtx_k: int | None = None,
          no_facet_fallback: int = 0):
    require_api_key(request, settings)
    mode = (request.query_params.get("mode") or mode or "research").strip().lower()
    if mode not in {"research", "user"}:
        mode = "research"

    t0 = perf_counter()
    qtype = (qtype_hint or "").strip().lower()
    if qtype not in {"definition", "symptoms", "treatments"}:
        qtype = nlp_service.detect_qtype(question)

    terms = nlp_service.extract_terms(question)
    if topic_key:
        topic_terms = nlp_service.merge_terms([topic_key], [])
        topic_norm = _normalize_lookup_term(topic_terms[0] if topic_terms else topic_key)
        ordered_terms = [topic_norm] + terms
        seen_norm: set[str] = set()
        prioritized_terms: list[str] = []
        for term in ordered_terms:
            clean_term = (term or "").strip()
            if not clean_term:
                continue
            norm_term = _normalize_lookup_term(clean_term)
            if norm_term in seen_norm:
                continue
            seen_norm.add(norm_term)
            prioritized_terms.append(clean_term)
        terms = prioritized_terms

    if ENABLE_FALLBACK and not terms:
        ans = llm_only(request=request, question=question, model=model, qtype_hint=qtype)["results"][0]["answer"]
        return {
            "question": question, "qtype": qtype, "extracted_terms": [],
            "debug": [{"fallback": "no_terms_to_kg"},
                      {"timing_ms": {"total": int((perf_counter() - t0) * 1000)}}],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": [], "answer": _finalize_answer_by_mode(ans, mode), "relevance": 0.0
            }]
        }

    candidates, debug_matches = [], []
    t_lookup_start = perf_counter()
    for term in terms:
        matches = nlp_service.lookup_concept_ids(term)
        debug_matches.append({"input_term": term, "match_count": len(matches)})
        for m in matches:
            cid = m["conceptId"]
            matched_term = m["term"]
            sub = neo4j_repository.get_subgraph(cid)
            pairs = [
                f"{r['sourceTerm']} → {r['targetTerm']}"
                for r in sub if r.get('sourceTerm') and r.get('targetTerm')
            ]
            candidates.append({
                "term": matched_term,
                "conceptId": cid,
                "subgraph_size": len(sub),
                "subgraph_pairs": pairs,
                "relevance": 1.0 if term in matched_term.lower() else 0.5
            })
    lookup_ms = int((perf_counter() - t_lookup_start) * 1000)

    if ENABLE_FALLBACK and not candidates:
        ans = llm_only(request=request, question=question, model=model, qtype_hint=qtype)["results"][0]["answer"]
        return {
            "question": question, "qtype": qtype, "extracted_terms": terms,
            "debug": debug_matches + [
                {"fallback": "no_candidates_from_kg"},
                {"timing_ms": {"lookup": lookup_ms, "total": int((perf_counter() - t0) * 1000)}},
            ],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": [], "answer": _finalize_answer_by_mode(ans, mode), "relevance": 0.0
            }]
        }

    candidates.sort(key=lambda x: (x["relevance"], x["subgraph_size"]), reverse=True)

    top_n_default = 2
    if qtype in ("symptoms", "treatments") and symtx_k:
        top_n_default = max(1, int(symtx_k))
    top_n = top_n_default
    if max_k:
        top_n = min(top_n, max(1, int(max_k)))
    topk = candidates[:top_n]
    combined_pairs = []
    for c in topk:
        combined_pairs.extend(c["subgraph_pairs"])

    seen = set()
    combined_pairs = [p for p in combined_pairs if not (p in seen or seen.add(p))]
    sorted_pairs = nlp_service.rerank_pairs(combined_pairs, question, qtype)

    ratio = nlp_service.overlap_ratio(question, sorted_pairs, topn=8)
    LOW_OVL = 0.008
    evidence_level = nlp_service.facet_evidence_level(sorted_pairs, qtype)
    if qtype in ("symptoms", "treatments"):
        _, narrative_categories = prompt_builder.extract_condition_categories(sorted_pairs)
        if len(narrative_categories) < 2:
            evidence_level = "none"
    no_facet_hit = evidence_level != "strong"

    if ENABLE_FALLBACK and ENABLE_LOW_OVERLAP and no_facet_hit and ratio < LOW_OVL:
        ans = generate_answer_with_mode(
            question=question,
            subgraph=[{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
            lite=0,
            qtype=qtype,
            mode=mode,
        )
        note = "kg_low_overlap_limited_evidence"
        return {
            "question": question, "qtype": qtype, "extracted_terms": terms,
            "debug": debug_matches + [{"fallback": note, "overlap": ratio, "facet_evidence_level": evidence_level}],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": sorted_pairs[:3],
                "answer": _finalize_answer_by_mode(ans, mode), "relevance": 0.0,
                "note": note
            }]
        }

    if ENABLE_FALLBACK and (not no_facet_fallback) and qtype in ("symptoms", "treatments") and evidence_level != "strong":
        if mode == "research":
            ans = _research_insufficient_answer(qtype, evidence_level, sorted_pairs)
            note = f"research_{evidence_level}_evidence_insufficient"
            fallback_note = f"strategy_a_research_{evidence_level}_insufficient"
        elif evidence_level == "none":
            ans = llm_only(request=request, question=question, model=model, qtype_hint=qtype)["results"][0]["answer"]
            note = "user_mode_llm_only_no_evidence"
            fallback_note = "strategy_a_user_none_to_llm_only"
        else:
            ans = generate_answer_with_mode(
                question=question,
                subgraph=[{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
                lite=0,
                qtype=qtype,
                mode=mode,
            )
            note = "user_mode_kg_with_weak_evidence"
            fallback_note = "strategy_a_user_weak_keep_kg"
        return {
            "question": question,
            "qtype": qtype,
            "extracted_terms": terms,
            "debug": debug_matches + [{"fallback": fallback_note,
                                       "pairs_after_merge": len(combined_pairs),
                                       "facet_evidence_level": evidence_level},
                                      {"timing_ms": {"lookup": lookup_ms, "total": int((perf_counter() - t0) * 1000)}}],
            "results": [{
                "term": topk[0]["term"],
                "conceptId": topk[0]["conceptId"],
                "subgraph_size": sum(c["subgraph_size"] for c in topk),
                "subgraph_summary": sorted_pairs[:3],
                "answer": _finalize_answer_by_mode(ans, mode),
                "relevance": topk[0]["relevance"],
                "note": note
            }]
        }

    note = None
    t_gen_start = perf_counter()
    if lite:
        ans = generate_answer_with_mode(
            question=question,
            subgraph=[{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
            lite=1,
            qtype=qtype,
            mode=mode,
        )
    else:
        prompt = prompt_builder.build_prompt_kg_with_mode(
            qtype=qtype,
            question=question,
            pairs=sorted_pairs,
            mode=mode,
        )
        limits = prompt_builder.facet_limits(qtype)
        ans = ollama_client.call_llm(
            prompt,
            model_name=(model or "cwchang/llama-3-taiwan-8b-instruct"),
            num_predict=limits["num_predict"]
        )
        if ENABLE_FALLBACK and nlp_service.is_bad_answer(ans):
            ans = llm_only(request=request, question=question, model=model, qtype_hint=qtype)["results"][0]["answer"]
            note = "fallback_llm_only_after_bad_llm"
    gen_ms = int((perf_counter() - t_gen_start) * 1000)

    return {
        "question": question,
        "qtype": qtype,
        "extracted_terms": terms,
        "debug": debug_matches + [{"facet_evidence_level": evidence_level}, {"timing_ms": {
            "lookup": lookup_ms,
            "generation": gen_ms,
            "total": int((perf_counter() - t0) * 1000),
        }}],
        "results": [{
            "term": topk[0]["term"],
            "conceptId": topk[0]["conceptId"],
            "subgraph_size": sum(c["subgraph_size"] for c in topk),
            "subgraph_summary": sorted_pairs[:3],
            "answer": _finalize_answer_by_mode(ans, mode),
            "relevance": topk[0]["relevance"],
            **({"note": note} if note else {})
        }]
    }


def demo_search_compat_response(
    request: Request,
    question: str,
    topic_key: str | None = None,
    qtype_hint: str | None = None,
    lite: int = 0,
    max_k: int = 1,
    model: str | None = None,
    symtx_k: int | None = None,
    no_facet_fallback: int = 0
):
    mode = (request.query_params.get("mode", "user") or "user").strip().lower()
    if mode not in {"user", "research"}:
        mode = "user"

    core = query(
        request=request,
        question=question,
        topic_key=topic_key,
        qtype_hint=qtype_hint,
        mode=mode,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback
    )

    first = ((core.get("results") or [{}])[0] or {})
    qtype = core.get("qtype")
    answer_kg = first.get("answer", "")
    answer_llm = llm_only(
        request=request,
        question=question,
        model=model,
        qtype_hint=(qtype_hint or qtype),
    )["results"][0]["answer"]
    concept_id = first.get("conceptId")

    resp = dict(core)
    resp.update({
        "matched": True,
        "similarity": 1.0,
        "mapped_to": {
            "bank_id": concept_id,
            "qtype": qtype,
            "question": question
        },
        "answers": {
            "a_label": "知識圖譜 + LLM",
            "a_text": answer_kg,
            "b_label": "純 LLM",
            "b_text": answer_llm
        }
    })
    return resp


def health():
    return {"status": "ok"}
