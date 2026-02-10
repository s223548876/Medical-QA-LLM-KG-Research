from typing import List, Dict
from fastapi import Request
from core.security import require_api_key
from core.settings import settings
from repositories import neo4j_repository
from clients import ollama_client
from services import nlp_service, prompt_builder


ENABLE_FALLBACK = True
ENABLE_LOW_OVERLAP = False


def generate_answer(question: str, subgraph: list, lite: int = 0, qtype: str = "definition") -> str:
    if not subgraph:
        return "--找不到足夠的知識圖資訊來回答問題。--"

    pairs = [
        f"{r.get('sourceTerm')} → {r.get('targetTerm')}"
        for r in subgraph
        if r.get('sourceTerm') and r.get('targetTerm')
    ]
    top_pairs = pairs[:10]

    if lite:
        bullets = [p.replace(" → ", " is-a ") for p in top_pairs[:8]]
        if qtype == "symptoms":
            return ("Based on the knowledge graph hierarchy, the condition is related to: " +
                    "; ".join(bullets) +
                    ". Common symptoms include shortness of breath, wheeze, cough, chest tightness, and variable airflow limitation.")
        if qtype == "treatments":
            return ("Based on the knowledge graph hierarchy, the condition is linked to these categories: " +
                    "; ".join(bullets) +
                    ". Treatments include inhaled bronchodilators, inhaled corticosteroids, trigger avoidance, vaccinations, and action plans.")
        return ("Based on the knowledge graph, key hierarchical relations include: " +
                "; ".join(bullets) +
                ". This provides a concise definition with parent/child categories.")

    prompt = prompt_builder.build_prompt_kg(qtype, question, pairs)
    limits = prompt_builder.facet_limits(qtype)
    return ollama_client.call_llm(prompt, num_predict=limits["num_predict"])


def llm_only(request: Request, question: str | None = None, model: str | None = None):
    require_api_key(request, settings)
    qtype = nlp_service.detect_qtype(question)
    if qtype == "symptoms":
        prompt = f"""You are a medical assistant. Answer in about 120 English words.

Question: {question}

Write: 1 sentence to set context, then "Common symptoms include ..." followed by 5–7 concise symptom phrases separated by commas, then one short caution."""
    elif qtype == "treatments":
        prompt = f"""You are a medical assistant. Answer in about 120 English words.

Question: {question}

Write: 1 sentence definition, then "Treatments include ..." listing 5–7 items (medications, procedures, self-care), end with a brief note on individualized plans."""
    else:
        prompt = f"""You are a medical assistant. Answer in about 120 English words.

Question: {question}

Write a clear definition first, followed by 2–3 compact supporting facts on classification, typical features, or context."""
    ans = ollama_client.call_llm(
        prompt, model_name=model or "cwchang/llama-3-taiwan-8b-instruct")
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
          lite: int = 0,
          max_k: int = 1,
          model: str | None = None,
          symtx_k: int | None = None,
          no_facet_fallback: int = 0):
    require_api_key(request, settings)

    qtype = nlp_service.detect_qtype(question)
    terms = nlp_service.extract_terms(question)

    if ENABLE_FALLBACK and not terms:
        ans = llm_only(request=request, question=question, model=model)["results"][0]["answer"]
        return {
            "question": question, "qtype": qtype, "extracted_terms": [],
            "debug": [{"fallback": "no_terms_to_kg"}],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": [], "answer": ans, "relevance": 0.0
            }]
        }

    candidates, debug_matches = [], []
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

    if ENABLE_FALLBACK and not candidates:
        ans = llm_only(request=request, question=question, model=model)["results"][0]["answer"]
        return {
            "question": question, "qtype": qtype, "extracted_terms": terms,
            "debug": debug_matches + [{"fallback": "no_candidates_from_kg"}],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": [], "answer": ans, "relevance": 0.0
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
    no_facet_hit = (not nlp_service.has_facet_evidence(sorted_pairs, qtype))

    if ENABLE_FALLBACK and ENABLE_LOW_OVERLAP and no_facet_hit and ratio < LOW_OVL:
        lite_ans = generate_answer(
            question,
            [{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
            lite=1, qtype=qtype
        )
        if nlp_service.is_bad_answer(lite_ans):
            ans = llm_only(request=request, question=question, model=model)["results"][0]["answer"]
            note = "facet_llm_only_low_overlap_after_lite"
        else:
            ans = lite_ans
            note = "facet_lite_low_overlap"

        return {
            "question": question, "qtype": qtype, "extracted_terms": terms,
            "debug": debug_matches + [{"fallback": note, "overlap": ratio}],
            "results": [{
                "term": None, "conceptId": None, "subgraph_size": 0,
                "subgraph_summary": sorted_pairs[:3],
                "answer": ans, "relevance": 0.0,
                "note": note
            }]
        }

    if ENABLE_FALLBACK and (not no_facet_fallback) and qtype in ("symptoms", "treatments") and not nlp_service.has_facet_evidence(sorted_pairs, qtype):
        ans = llm_only(request=request, question=question, model=model)["results"][0]["answer"]
        return {
            "question": question,
            "qtype": qtype,
            "extracted_terms": terms,
            "debug": debug_matches + [{"fallback": "llm_only_due_to_poor_facet_evidence",
                                       "pairs_after_merge": len(combined_pairs)}],
            "results": [{
                "term": topk[0]["term"],
                "conceptId": topk[0]["conceptId"],
                "subgraph_size": sum(c["subgraph_size"] for c in topk),
                "subgraph_summary": sorted_pairs[:3],
                "answer": ans,
                "relevance": topk[0]["relevance"],
                "note": "facet_llm_only"
            }]
        }

    note = None
    if lite:
        ans = generate_answer(
            question,
            [{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
            lite=1, qtype=qtype
        )
    else:
        prompt = prompt_builder.build_prompt_kg(qtype, question, sorted_pairs)
        limits = prompt_builder.facet_limits(qtype)
        ans = ollama_client.call_llm(
            prompt,
            model_name=(model or "cwchang/llama-3-taiwan-8b-instruct"),
            num_predict=limits["num_predict"]
        )
        if ENABLE_FALLBACK and nlp_service.is_bad_answer(ans):
            lite_ans = generate_answer(
                question,
                [{"sourceTerm": p.split(" → ")[0], "targetTerm": p.split(" → ")[1]} for p in sorted_pairs],
                lite=1, qtype=qtype
            )
            if nlp_service.is_bad_answer(lite_ans):
                ans = llm_only(request=request, question=question, model=model)["results"][0]["answer"]
                note = "fallback_llm_only_after_bad_llm_and_lite"
            else:
                ans = lite_ans
                note = "fallback_lite_after_bad_llm"

    return {
        "question": question,
        "qtype": qtype,
        "extracted_terms": terms,
        "debug": debug_matches,
        "results": [{
            "term": topk[0]["term"],
            "conceptId": topk[0]["conceptId"],
            "subgraph_size": sum(c["subgraph_size"] for c in topk),
            "subgraph_summary": sorted_pairs[:3],
            "answer": ans,
            "relevance": topk[0]["relevance"],
            **({"note": note} if note else {})
        }]
    }


def demo_search_compat_response(
    request: Request,
    question: str,
    lite: int = 0,
    max_k: int = 1,
    model: str | None = None,
    symtx_k: int | None = None,
    no_facet_fallback: int = 0
):
    core = query(
        request=request,
        question=question,
        lite=lite,
        max_k=max_k,
        model=model,
        symtx_k=symtx_k,
        no_facet_fallback=no_facet_fallback
    )

    first = ((core.get("results") or [{}])[0] or {})
    answer_b = first.get("answer", "")
    concept_id = first.get("conceptId")
    qtype = core.get("qtype")

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
            "a_label": "Answer A",
            "a_text": answer_b,
            "b_label": "Answer B",
            "b_text": answer_b
        }
    })
    return resp


def health():
    return {"status": "ok"}
