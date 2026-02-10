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
        return "the symptoms"
    if qtype == "treatments":
        return "the treatments"
    return "the definition"


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
    rels = "- " + "\n- ".join(bullets) if bullets else "(no evidence)"

    facet = facet_text(qtype)
    guidance = {
        "definition": (
            "Write ONE compact definitional sentence using terms from Evidence when possible. "
            "No background; avoid paraphrasing named medical terms."
        ),
        "symptoms": (
            "Start with: 'Common symptoms include:' then list 2–4 concise items (comma-separated or bullets) "
            "using Evidence terms when available. No background."
        ),
        "treatments": (
            "Start with: 'Treatments include:' then list 2–4 concise options (comma-separated or bullets) "
            "using Evidence terms when available. No background."
        ),
    }.get(qtype, "Write ONE compact definitional sentence using Evidence terms.")

    return f"""You are a medical QA assistant.

Answer ONLY {facet} of the condition asked.
Prefer short bullet points when applicable. Reuse exact medical terms appearing in the Evidence.
If the Evidence does not specify {facet}, answer exactly:
"The provided sources do not specify {facet}."

Question:
{question}

Evidence (compressed from a medical knowledge graph):
{rels}

Now provide ONLY {facet}:
- Keep it brief (<= 3 bullets OR <= 3 short sentences).
- Prefer Evidence terms; if Evidence is limited, you may add 1–2 widely accepted items.
- Do NOT add background, caveats, or extra context.
"""
