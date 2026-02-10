#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import itertools
import requests, time, json, re, xml.etree.ElementTree as ET
from urllib.parse import urlencode

API_BASE = "https://wsearch.nlm.nih.gov/ws/query"

# === 主題清單（7 + A + B + C）===
TOPICS = [
    # 原始 7 主題
    "asthma", "diabetes", "hypertension",
    "pneumonia", "tuberculosis", "depression",
    "urinary tract infection",

    # A 組 8 主題
    "stroke", "Alzheimer's disease", "Parkinson's disease",
    "chronic kidney disease", "osteoporosis",
    "anxiety disorders", "obesity",

    # B 組 10 主題
    "hepatitis", "HIV/AIDS", "COVID-19",
    "allergies", "arthritis", "migraine",
    "epilepsy", "anemia", "thyroid disorders",

    # C 組 10 主題
    "skin cancer", "breast cancer", "cervical cancer",
    "leukemia", "rare diseases", "sleep apnea",
    "GERD", "irritable bowel syndrome", "celiac disease", "malaria"
]

def clean_text(t: str) -> str:
    t = (t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def trim_words(text: str, max_words=120, hard_cap=2000) -> str:
    text = (text or "").strip()[:hard_cap]
    toks = text.split()
    if len(toks) <= max_words:
        return text
    return " ".join(toks[:max_words])

def fetch_health_topic(term: str):
    params = {"db": "healthTopics", "term": term, "rettype": "all"}
    url = f"{API_BASE}?{urlencode(params)}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    docs = root.findall(".//document")
    return docs

def parse_document_contents(doc_elem):
    contents = {}
    for c in doc_elem.findall("./content"):
        name = c.get("name") or ""
        values = [(v.text or "").strip() for v in c.findall("./value") if (v.text or "").strip()]
        text = "\n".join(values) if values else (c.text or "")
        text = clean_text(text or "")
        if not text:
            continue
        if name in contents and contents[name]:
            contents[name] += "\n" + text
        else:
            contents[name] = text
    return contents

SYMPTOM_KEYWORDS = [
    "symptom", "sign", "signs", "symptoms", "clinical feature", "manifestation",
    "present with", "presents with", "common symptoms", "warning signs"
]
TREATMENT_KEYWORDS = [
    "treat", "treatment", "therapy", "therapies", "medication", "drug",
    "manage", "management", "lifestyle changes", "procedure", "surgery"
]

_SENT_END = re.compile(r"(?<=[.!?])\s+")

def split_sentences(text: str) -> list[str]:
    text = clean_text(text or "")
    sents = _SENT_END.split(text)
    return [s.strip() for s in sents if s.strip()]

def contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)

def extract_by_keywords(full_summary: str, keywords: list[str], min_words=12, max_pick=3) -> str | None:
    """從摘要中抓出含關鍵詞的句子，最多挑幾句接起來。"""
    sents = split_sentences(full_summary)
    picked = [s for s in sents if contains_any(s, keywords)]
    if not picked:
        return None
    # 依長度與出現順序挑前幾句
    out = " ".join(picked[:max_pick]).strip()
    if len(out.split()) < min_words:
        return None
    return out

def first_definition_sentences(full_summary: str, avoid_keywords: list[str], max_sent=2, min_words=12) -> str | None:
    """用前 1–2 句當定義，盡量避開含症狀/治療關鍵詞的句子。"""
    sents = split_sentences(full_summary)
    filtered = [s for s in sents if not contains_any(s, avoid_keywords)]
    if not filtered:
        filtered = sents
    out = " ".join(filtered[:max_sent]).strip()
    if len(out.split()) < min_words:
        # 再補一點句子
        out = " ".join(filtered[:max_sent+1]).strip()
    return out if len(out.split()) >= min_words else None

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
    """用分類連結的 label 當作貼題的精簡片段（不抓外頁）。"""
    for link in links:
        if (link["category"] or "").lower() == category_name.lower():
            lbl = link["label"] or link["url"]
            if lbl:
                return f"[{link['category']}] {lbl}"
    return None

def build_qa_for_document(doc_elem, max_words=120):
    contents = parse_document_contents(doc_elem)
    links = parse_links_with_category(doc_elem)

    title = clean_text(contents.get("title") or contents.get("Title") or "")
    full_summary = clean_text(contents.get("FullSummary") or contents.get("full-summary") or "")

    if not title or not full_summary:
        return []

    # 1) 定義：摘要的前 1–2 句，盡量避開症狀/治療關鍵詞
    defin = first_definition_sentences(
        full_summary,
        avoid_keywords=SYMPTOM_KEYWORDS + TREATMENT_KEYWORDS,
        max_sent=2, min_words=12
    ) or full_summary

    # 2) 症狀：優先用分類連結；否則用摘要中含症狀關鍵詞的句子
    sym = pick_snippet_by_category(links, "Symptoms") \
          or extract_by_keywords(full_summary, SYMPTOM_KEYWORDS, min_words=12, max_pick=3) \
          or full_summary

    # 3) 治療：優先用分類連結；否則用摘要中含治療關鍵詞的句子
    trt = pick_snippet_by_category(links, "Treatments and Therapies") \
          or extract_by_keywords(full_summary, TREATMENT_KEYWORDS, min_words=12, max_pick=3) \
          or full_summary

    defin = trim_words(defin, max_words=max_words)
    sym   = trim_words(sym,   max_words=max_words)
    trt   = trim_words(trt,   max_words=max_words)

    items = []
    # 定義
    if len(defin.split()) >= 12:
        items.append({
            "question": f"What is {title}?",
            "answer": defin,
            "topicTitle": title
        })
    # 症狀
    if len(sym.split()) >= 12:
        items.append({
            "question": f"What are the symptoms of {title}?",
            "answer": sym,
            "topicTitle": title
        })
    # 治療
    if len(trt.split()) >= 12:
        items.append({
            "question": f"How is {title} treated?",
            "answer": trt,
            "topicTitle": title
        })

    return items

def main():
    out_path = "medline_eval_full.jsonl"
    n_total = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for term in TOPICS:
            try:
                docs = fetch_health_topic(term)
            except Exception as e:
                print(f"[WARN] fetch '{term}' failed: {e}")
                continue

            for doc in docs:
                qa_items = build_qa_for_document(doc, max_words=120)
                for item in qa_items:
                    if len(item["answer"].split()) < 12:
                        continue
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    n_total += 1

            time.sleep(0.2)

    print(f"Done. Wrote {n_total} QA items to {out_path}")

if __name__ == "__main__":
    main()
