from typing import List, Dict
from spacy.util import load_model_from_path
from pathlib import Path
import re
import difflib
from repositories import neo4j_repository

# ========== Load scispaCy model ==========
nlp = load_model_from_path(
    Path("./models/en_core_sci_lg-0.5.4/en_core_sci_lg/en_core_sci_lg-0.5.4")
)

# ========== Aliases for common terms ==========
ALIASES = {
    "heart attack": "myocardial infarction",
    "uti": "urinary tract infection",
    "flu": "influenza",
    "tb": "tuberculosis",
    "copd": "chronic obstructive pulmonary disease",
    "high blood pressure": "hypertension",
    "gerd": "gastroesophageal reflux disease",
    "covid-19": "covid 19",
    "covid19": "covid 19",
}

NOISE_TERMS = {
    "what", "which", "who", "where", "when", "why", "how",
    "is", "are", "was", "were", "be", "to", "do", "does", "did",
    "a", "an", "the", "of", "for", "with", "and", "or", "in", "on",
    "symptom", "symptoms", "sign", "signs",
    "treat", "treated", "treating", "treatment", "treatments", "therapy", "management",
    "definition", "define", "disease", "disorder", "condition",
}

_LATIN_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9'/-]+){0,4}")

# 針對症狀與治療的關鍵詞線索
_SYM_HINTS = {"itching", "swelling", "dizziness", "weakness", "fatigue", "chills",
              "edema", "palpitations", "nausea", "vomiting", "cough", "fever", "pain"}
_TRT_HINTS = {"therapy", "medication", "drug", "procedure", "surgery",
              "insulin", "statin", "ace inhibitor", "arb", "beta-agonist",
              "antihistamine", "anticoagulant", "chemotherapy", "radiation",
              "steroid", "corticosteroid", "antibiotic", "inhaler", "bronchodilator"}

# ===== Facet keyword detector =====
KW_FIX2 = {
    "definition": {
        "High": [
            "what is", "what are",
            "define", "definition of",
            "is defined as",
            "refers to",
            "is called", "known as", "aka",
            "terminology", "term",
            "is a type of", "subtype of",
        ],
        "Supplement": [
            "classification of",
            "meaning of",
            "described as", "description",
            "synonymous with",
            "characterized by",
            "introduction", "intro",
            "nomenclature",
            "alias",
            "abbreviation",
        ],
    },
    "symptoms": {
        "High": [
            "symptom", "symptoms",
            "signs and symptoms",
            "clinical features",
            "presenting symptoms",
            "common symptoms",
            "warning signs", "red flags",
            "manifestations",
            "hallmark symptoms",
        ],
        "Supplement": [
            "how to recognize", "how to identify",
            "signs of",
            "early signs", "early symptoms",
            "symptom checklist", "symptom list",
            "symptom profile", "symptom pattern",
            "clinical presentation",
            "patient complains of",
            "associated symptoms",
        ],
    },
    "treatments": {
        "High": [
            "treatment", "treatments",
            "management",
            "therapy", "therapies",
            "medication", "medications", "drug therapy",
            "surgery", "surgical",
            "rehabilitation", "physical therapy",
            "lifestyle modification",
            "first-line", "second-line",
        ],
        "Supplement": [
            "how to treat", "treating",
            "management options", "management strategies",
            "supportive care",
            "self-care", "home remedies",
            "follow-up", "monitoring",
            "preventive therapy", "prophylaxis", "prophylactic",
            "complications management",
            "risk reduction",
        ],
    },
    "negation": {
        "High": [
            "no", "not", "without", "lack of",
            "ruled out", "rule out",
            "exclude", "excluding",
            "negative for",
            "contraindicated", "not indicated",
        ],
        "Supplement": [
            "except", "except for",
            "denied", "denies", "denial",
            "reject", "rejected",
            "symptom relief", "prevention only",
        ],
    },
}


def has_facet_evidence(pairs: list[str], qtype: str) -> bool:
    bag = " ".join(pairs).lower()
    if qtype == "symptoms":
        return any(w in bag for w in _SYM_HINTS)
    if qtype == "treatments":
        return any(w in bag for w in _TRT_HINTS)
    return True


def terms_to_regex(terms: list[str]) -> list[str]:
    pats = []
    for t in terms:
        s = t.strip()
        if not s:
            continue
        s_escaped = re.escape(s).replace(r"\ ", r"\s+")
        if re.match(r".*[A-Za-z]$", s) and not s.endswith((" of", " to")):
            s_escaped = s_escaped + r"(s)?"
        pats.append(rf"\b{s_escaped}\b")
    return pats


def compile_kw_fix2():
    cn_def = globals().get("_CN_DEF", [])
    cn_sym = globals().get("_CN_SYM", [])
    cn_tx = globals().get("_CN_TX", [])
    patterns = {
        "definition": {"hi": [], "lo": [], "zh": cn_def},
        "symptoms": {"hi": [], "lo": [], "zh": cn_sym},
        "treatments": {"hi": [], "lo": [], "zh": cn_tx},
    }
    for facet in ("definition", "symptoms", "treatments"):
        patterns[facet]["hi"].extend(terms_to_regex(KW_FIX2[facet]["High"]))
        patterns[facet]["lo"].extend(terms_to_regex(KW_FIX2[facet]["Supplement"]))
    neg_hi = terms_to_regex(KW_FIX2["negation"]["High"])
    neg_lo = terms_to_regex(KW_FIX2["negation"]["Supplement"])
    neg_union = "|".join([p[2:-2] for p in (neg_hi + neg_lo)])
    neg_pat = re.compile(rf"\b(?:{neg_union})\b", re.I)
    return patterns, neg_pat


_FACET_PATTERNS, _NEGATION_PAT = compile_kw_fix2()
_QTYPE_WEIGHTS = {"hi": 2, "lo": 1, "zh": 2}
_IGNORE_NEGATION = True
_NEGATION_WIN = 24


def negated_nearby(text: str, start_idx: int) -> bool:
    if not _IGNORE_NEGATION:
        return False
    s = max(0, start_idx - _NEGATION_WIN)
    window = text[s:start_idx]
    return bool(_NEGATION_PAT.search(window))


def kw_score(text: str, facet: str) -> int:
    t = (text or "").lower()
    score = 0
    pats = _FACET_PATTERNS[facet]
    for bucket in ("hi", "lo", "zh"):
        w = _QTYPE_WEIGHTS.get(bucket, 1)
        for pat in pats.get(bucket, []):
            for m in re.finditer(pat, t, flags=re.I):
                if not negated_nearby(t, m.start()):
                    score += w
    return score


def detect_qtype(question: str) -> str:
    q = (question or "").strip()
    s_def = kw_score(q, "definition")
    s_sym = kw_score(q, "symptoms")
    s_tx = kw_score(q, "treatments")

    s_sym += 1
    s_tx += 1

    scores = {"treatments": s_tx, "symptoms": s_sym, "definition": s_def}
    sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_label, top_score = sorted_items[0]
    second_score = sorted_items[1][1]

    if top_score - second_score <= 4:
        for cand in ("treatments", "symptoms", "definition"):
            if scores[cand] == top_score:
                qtype = cand
                break
    else:
        qtype = top_label

    if scores[qtype] == 0:
        qtype = "definition"
    return qtype


def is_bad_answer(ans: str) -> bool:
    if not ans or not isinstance(ans, str):
        return True
    s = ans.strip().lower()
    if s.startswith("!!!") or "呼叫 llm 失敗" in s:
        return True
    if len(s) < 24:
        return True
    return False


def pair_score(pair_text: str, question: str, qtype: str) -> float:
    t = (pair_text or "").lower()
    q = (question or "").lower()
    qset = set(re.findall(r"[a-z]+", q))
    pset = set(re.findall(r"[a-z]+", t))
    overlap = len(pset & qset)
    score = 0.5 * overlap + min(0.5, len(t) / 80.0)
    if qtype == "treatments" and any(h in t for h in _TRT_HINTS):
        score += 0.7
    elif qtype == "symptoms" and any(h in t for h in _SYM_HINTS):
        score += 0.3
    return score


def rerank_pairs(pairs: list[str], question: str, qtype: str) -> List[str]:
    return sorted(pairs or [], key=lambda p: pair_score(p, question, qtype), reverse=True)


def overlap_ratio(q: str, pairs: list[str], topn: int = 8) -> float:
    qset = set(re.findall(r"[a-z]+", (q or "").lower()))
    if not qset or not pairs:
        return 0.0
    hits, toks = 0, 0
    for p in pairs[:topn]:
        pset = set(re.findall(r"[a-z]+", (p or "").lower()))
        toks += len(pset)
        hits += len(pset & qset)
    return (hits / max(1, toks))


def extract_terms(text: str) -> List[str]:
    raw = []
    doc = nlp(text)
    for ent in doc.ents:
        raw.append(ent.text.lower().strip())

    # Mixed Chinese/English prompts from frontend templates often keep disease names in Latin script.
    for m in _LATIN_TERM_RE.finditer(text or ""):
        raw.append(m.group(0).lower().strip())

    return merge_terms(raw)


def merge_terms(seed_terms: list[str] | None, base_terms: list[str] | None = None, max_terms: int = 5) -> List[str]:
    merged: list[str] = []
    for src in (seed_terms or []), (base_terms or []):
        for item in src:
            t = (item or "").lower().strip()
            if not t:
                continue
            t = t.replace("（", "(").replace("）", ")").strip(" \t\r\n.,;:!?\"'()[]{}")
            mapped = ALIASES.get(t, t)
            for cand in [mapped] + [p.strip() for p in re.split(r"[()/]", mapped) if p.strip()]:
                if is_noise_term(cand):
                    continue
                if cand not in merged:
                    merged.append(cand)
                if len(merged) >= max_terms:
                    return merged
    return merged


def is_noise_term(term: str) -> bool:
    t = (term or "").lower().strip()
    if not t:
        return True
    if t in NOISE_TERMS:
        return True
    if len(t) <= 2:
        return True
    toks = re.findall(r"[a-z]+", t)
    if len(toks) > 6:
        return True
    if len(toks) >= 3:
        stop_cnt = sum(1 for tok in toks if tok in NOISE_TERMS)
        if stop_cnt >= 2:
            return True
    if re.fullmatch(r"[0-9\W_]+", t):
        return True
    return False


_VOCAB_TERMS: list[str] = []
_VOCAB_READY: bool = False


def ensure_vocab_terms() -> None:
    global _VOCAB_TERMS, _VOCAB_READY
    if _VOCAB_READY:
        return
    try:
        _VOCAB_TERMS = neo4j_repository.list_vocab_terms(limit=100000)
        _VOCAB_READY = True
    except Exception:
        _VOCAB_TERMS = []
        _VOCAB_READY = True


def fuzzy_candidates(term: str, n: int = 5, cutoff: float = 0.82) -> list[str]:
    ensure_vocab_terms()
    if not _VOCAB_TERMS:
        return []
    t = (term or "").lower().strip()
    return difflib.get_close_matches(t, _VOCAB_TERMS, n=n, cutoff=cutoff)


def lookup_concept_ids(term: str) -> List[Dict[str, str]]:
    term = (term or "").strip()
    if not term or is_noise_term(term):
        return []
    matches = neo4j_repository.lookup_concept_ids(term)
    toks = re.findall(r"[a-z]+", term.lower())
    can_fuzzy = (
        1 <= len(toks) <= 2
        and len(term) >= 5
        and not any(tok in NOISE_TERMS for tok in toks)
    )
    if not matches and can_fuzzy:
        fuzz_terms = fuzzy_candidates(term, n=5, cutoff=0.82)
        for ft in fuzz_terms:
            more = neo4j_repository.lookup_concept_ids(ft)
            if more:
                matches.extend(more)

    seen, dedup = set(), []
    for m in matches:
        cid = m.get("conceptId")
        if cid and cid not in seen:
            dedup.append(m)
            seen.add(cid)
    return dedup
