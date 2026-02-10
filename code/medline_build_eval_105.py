#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patched generator: 35 topics × 3 QAs (definition / symptoms / treatments) = 105 items
- Guarantees 3 items per topic
- Strong non-empty fallbacks
- Alias & keyword expansion
Output: ./data/medline_eval_35x3.jsonl
"""

import requests
import time
import re
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode

# ---------------- Config ----------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
API_BASE = "https://wsearch.nlm.nih.gov/ws/query"
OUT_PATH = Path("./data/medline_eval_35x3.jsonl")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

STUB = "No summary is available from MedlinePlus for this specific aspect. Please refer to the condition overview."

# 35 canonical topics（原始7 + 優先123）
CANON_TOPICS = [
    # 原始 7
    "Asthma", "Diabetes", "Heart disease", "Hypertension", "Influenza", "Tuberculosis", "Cancer",
    # 優先1
    "Stroke", "Alzheimer's disease", "Parkinson's disease", "Chronic kidney disease",
    "Osteoporosis", "Depression", "Anxiety disorders", "Obesity",
    # 優先2
    "Pneumonia", "Hepatitis", "HIV/AIDS", "COVID-19", "Allergies", "Arthritis",
    "Migraine", "Epilepsy", "Anemia", "Thyroid disorders",
    # 優先3
    "Skin cancer", "Breast cancer", "Cervical cancer", "Leukemia",
    "Sleep apnea", "GERD", "Irritable bowel syndrome", "Celiac disease", "Malaria",
    "Chronic obstructive pulmonary disease"
]

# 常見別名（增加命中率；新增一些容易 miss 的別名）
ALIASES = {
    "Asthma": ["Asthma", "Bronchial asthma"],
    "Diabetes": ["Diabetes", "Diabetes mellitus", "Type 2 diabetes", "Type 1 diabetes"],
    "Heart disease": ["Heart disease", "Heart diseases", "Coronary artery disease", "Cardiovascular disease"],
    "Hypertension": ["Hypertension", "High blood pressure"],
    "Influenza": ["Influenza", "Flu"],
    "Tuberculosis": ["Tuberculosis", "TB"],
    "Cancer": ["Cancer", "Cancer - overview", "Malignant neoplasms"],

    "Stroke": ["Stroke", "Cerebrovascular accident"],
    "Alzheimer's disease": ["Alzheimer's disease", "Alzheimer disease", "Dementia (Alzheimer's)"],
    "Parkinson's disease": ["Parkinson's disease", "Parkinson disease", "Parkinsonism"],
    "Chronic kidney disease": ["Chronic kidney disease", "CKD", "Kidney failure - chronic"],
    "Osteoporosis": ["Osteoporosis", "Bone loss (Osteoporosis)"],
    "Depression": ["Depression", "Depressive disorder", "Major depressive disorder"],
    "Anxiety disorders": ["Anxiety disorders", "Anxiety", "Generalized anxiety disorder"],
    "Obesity": ["Obesity", "Overweight and obesity"],

    "Pneumonia": ["Pneumonia"],
    "Hepatitis": ["Hepatitis", "Viral hepatitis"],
    "HIV/AIDS": ["HIV/AIDS", "HIV"],
    "COVID-19": ["COVID-19", "Coronavirus disease 2019"],
    "Allergies": ["Allergies", "Allergy", "Allergic conditions"],
    "Arthritis": ["Arthritis", "Osteoarthritis", "Rheumatoid arthritis"],
    "Migraine": ["Migraine", "Migraine headaches"],
    "Epilepsy": ["Epilepsy", "Seizure disorders"],
    "Anemia": ["Anemia", "Anaemia"],
    "Thyroid disorders": ["Thyroid disorders", "Thyroid disease", "Thyroid diseases", "Hypothyroidism", "Hyperthyroidism", "Thyroid conditions"],

    "Skin cancer": ["Skin cancer", "Melanoma", "Basal cell carcinoma", "Squamous cell skin cancer"],
    "Breast cancer": ["Breast cancer", "Breast neoplasms"],
    "Cervical cancer": ["Cervical cancer", "Cervical neoplasms", "Cervical carcinoma"],
    "Leukemia": ["Leukemia"],
    "Sleep apnea": ["Sleep apnea", "Obstructive sleep apnea", "OSA"],
    "GERD": ["GERD", "Gastroesophageal reflux disease", "Acid reflux"],
    "Irritable bowel syndrome": ["Irritable bowel syndrome", "IBS"],
    "Celiac disease": ["Celiac disease", "Coeliac disease"],
    "Malaria": ["Malaria"],
    "Chronic obstructive pulmonary disease": [
        "Chronic obstructive pulmonary disease", "COPD", "Chronic obstructive lung disease"
    ]
}

# ---------------- Helpers ----------------
HTML_TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def clean_text(t: str) -> str:
    t = HTML_TAG.sub(" ", t or "")
    t = t.replace("&nbsp;", " ")
    return WS.sub(" ", t).strip()


_SENT_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    sents = _SENT_END.split(text)
    return [s.strip() for s in sents if s.strip()]


def trim_words(text: str, max_words: int = 120, hard_cap: int = 4000) -> str:
    text = (text or "").strip()[:hard_cap]
    toks = text.split()
    return " ".join(toks[:max_words]) if len(toks) > max_words else text


def non_empty(text: str, fallback: str) -> str:
    """Return non-empty text; else fallback; else stub."""
    txt = (text or "").strip()
    if txt:
        return txt
    fb = (fallback or "").strip()
    return fb if fb else STUB


def contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)


SYMPTOM_KEYS = [
    "symptom", "symptoms", "sign", "signs", "clinical feature", "manifestation",
    "presents with", "present with", "warning signs", "indicators"
]
TREAT_KEYS = [
    "treat", "treated", "treatment", "therapy", "therapies", "medication", "drug",
    "manage", "management", "lifestyle", "procedure", "surgery", "intervention", "care"
]


def extract_by_keywords(full_summary: str, keywords: list[str], min_words=12, max_pick=3) -> str | None:
    sents = split_sentences(full_summary)
    picked = [s for s in sents if contains_any(s, keywords)]
    if not picked:
        return None
    out = " ".join(picked[:max_pick]).strip()
    return out if len(out.split()) >= min_words else None


def first_definition_sentences(full_summary: str, avoid_keywords: list[str], max_sent=2, min_words=12) -> str | None:
    sents = split_sentences(full_summary)
    filtered = [s for s in sents if not contains_any(s, avoid_keywords)]
    if not filtered:
        filtered = sents
    out = " ".join(filtered[:max_sent]).strip()
    if len(out.split()) < min_words and len(filtered) > max_sent:
        out = " ".join(filtered[:max_sent+1]).strip()
    return out if len(out.split()) >= min_words else None


def fetch_docs_by_term(term: str):
    params = {"db": "healthTopics", "term": term, "rettype": "all"}
    url = f"{API_BASE}?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return root.findall(".//document")


def parse_document_contents(doc_elem):
    contents = {}
    for c in doc_elem.findall("./content"):
        name = c.get("name") or ""
        vals = [(v.text or "").strip()
                for v in c.findall("./value") if (v.text or "").strip()]
        text = "\n".join(vals) if vals else (c.text or "")
        text = clean_text(text or "")
        if text:
            contents[name] = (contents.get(
                name, "") + ("\n" if contents.get(name) else "") + text).strip()
    return contents


def parse_links_with_category(doc_elem):
    links = []
    for link in doc_elem.findall(".//link"):
        url = link.get("url") or ""
        label = link.get("label") or ""
        cat = link.get("information-category") or ""
        if url or label or cat:
            links.append({"url": url, "label": label, "category": cat})
    return links


def pick_snippet_by_category(links, category_name: str) -> str | None:
    for link in links:
        if (link["category"] or "").lower() == category_name.lower():
            lbl = link["label"] or link["url"]
            if lbl:
                return f"[{link['category']}] {lbl}"
    return None


def title_score(title: str, aliases: list[str]) -> int:
    t = (title or "").lower().strip()
    best = 0
    for a in aliases:
        a = a.lower().strip()
        if t == a:
            return 3
        if a in t or t in a:
            best = max(best, 2)
    return max(best, 1 if t else 0)


def choose_best_document(docs, aliases):
    best, best_score = None, -1
    for d in docs:
        contents = parse_document_contents(d)
        title = contents.get("title") or contents.get("Title") or ""
        sc = title_score(title, aliases)
        if sc > best_score:
            best, best_score = d, sc
    return best


def build_three_qa(doc_elem, canonical_topic: str, max_words=120):
    contents = parse_document_contents(doc_elem)
    links = parse_links_with_category(doc_elem)

    title = clean_text(contents.get("title")
                       or contents.get("Title") or canonical_topic)
    full_summary = clean_text(contents.get(
        "FullSummary") or contents.get("full-summary") or "")

    # 1) 定義：摘要的前 1–2 句，盡量避開症狀/治療關鍵詞；再保底
    defin_raw = first_definition_sentences(
        full_summary, SYMPTOM_KEYS + TREAT_KEYS, max_sent=2, min_words=12)
    defin = trim_words(non_empty(defin_raw, full_summary), max_words)

    # 2) 症狀：優先分類連結；否則抽句；再保底
    sym_raw = (pick_snippet_by_category(links, "Symptoms")
               or extract_by_keywords(full_summary, SYMPTOM_KEYS, min_words=12, max_pick=3))
    sym = trim_words(non_empty(sym_raw, full_summary), max_words)

    # 3) 治療：優先分類連結；否則抽句；再保底
    trt_raw = (pick_snippet_by_category(links, "Treatments and Therapies")
               or extract_by_keywords(full_summary, TREAT_KEYS, min_words=12, max_pick=3))
    trt = trim_words(non_empty(trt_raw, full_summary), max_words)

    items = [
        {"question": f"What is {canonical_topic}?",
            "answer": defin, "topic_name": canonical_topic},
        {"question": f"What are the symptoms of {canonical_topic}?",
            "answer": sym, "topic_name": canonical_topic},
        {"question": f"How is {canonical_topic} treated?",
            "answer": trt, "topic_name": canonical_topic},
    ]
    # 保底：任何一題若仍 <12 詞，再用摘要或 STUB 填滿
    final = []
    for it in items:
        ans = it["answer"]
        if len(ans.split()) < 12:
            ans = trim_words(non_empty(full_summary, STUB), max_words)
        it["answer"] = ans
        final.append(it)
    return final

# ---------------- Main ----------------


def main():
    total = 0
    empty_cnt = 0
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for canonical in CANON_TOPICS:
            aliases = ALIASES.get(canonical, [canonical])
            logging.info(f"[Topic] {canonical} | aliases={aliases}")
            best_doc = None

            # 逐一以別名查詢，挑最匹配的一份 document
            for term in aliases:
                try:
                    docs = fetch_docs_by_term(term)
                except Exception as e:
                    logging.error(f"  fetch failed for '{term}': {e}")
                    continue
                if not docs:
                    time.sleep(0.2)
                    continue
                cand = choose_best_document(docs, aliases)
                if cand is not None:
                    best_doc = cand
                    break
                time.sleep(0.2)

            if best_doc is None:
                logging.warning(
                    f"  -> No document chosen for '{canonical}'. Using STUB.")
                triples = [
                    {"question": f"What is {canonical}?",
                        "answer": STUB, "topic_name": canonical},
                    {"question": f"What are the symptoms of {canonical}?",
                        "answer": STUB, "topic_name": canonical},
                    {"question": f"How is {canonical} treated?",
                        "answer": STUB, "topic_name": canonical},
                ]
            else:
                triples = build_three_qa(
                    best_doc, canonical_topic=canonical, max_words=120)

            # 嚴格只寫 3 筆 & 非空檢查
            wrote = 0
            for it in triples[:3]:
                ans = (it.get("answer") or "").strip()
                if not ans:
                    it["answer"] = STUB
                    empty_cnt += 1
                out.write(json.dumps(it, ensure_ascii=False) + "\n")
                total += 1
                wrote += 1

            logging.info(f"  -> wrote {wrote} QA for '{canonical}'")
            time.sleep(0.3)

    logging.info("=== SUMMARY ===")
    logging.info(f"Total topics: {len(CANON_TOPICS)} (expected 35)")
    logging.info(f"Total QA written: {total} (expected 105)")
    logging.info(f"Hard-empty items forced to STUB: {empty_cnt}")
    if total != len(CANON_TOPICS) * 3:
        logging.warning(
            "Not exactly 105 items — please recheck aliases/network.")
    elif empty_cnt > 0:
        logging.warning(
            "Some items required STUB fallback. Consider widening aliases or checking connectivity.")
    else:
        logging.info("All good: 35 topics × 3 QAs, no empty answers.")


if __name__ == "__main__":
    main()
