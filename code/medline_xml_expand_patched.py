import xml.etree.ElementTree as ET
import random
import json
import argparse
import re
from collections import defaultdict
from pathlib import Path

# 預設的領域對應關鍵字（可擴充）
DOMAIN_KEYWORDS = {
    "cardiovascular": ["heart", "cardio", "stroke", "blood pressure"],
    "metabolic_endocrine": ["diabetes", "thyroid", "metabolic", "insulin"],
    "infectious": ["infection", "virus", "bacteria", "hepatitis", "HIV", "AIDS", "COVID", "tuberculosis"],
    "oncology": ["cancer", "tumor", "leukemia", "carcinoma"],
    "neurological": ["brain", "neuro", "parkinson", "epilepsy", "alzheimer", "migraine"],
    "respiratory": ["asthma", "lung", "pneumonia", "bronchitis", "respiratory"],
    "psychiatric": ["mental", "depression", "anxiety", "psychiatric"],
    "digestive": ["stomach", "bowel", "colon", "ibs", "digestive", "liver", "pancreas"],
    "renal_urologic": ["kidney", "renal", "urinary", "bladder"],
    "musculoskeletal": ["bone", "arthritis", "muscle", "osteoporosis"],
    "dermatology": ["skin", "eczema", "psoriasis", "rash"],
    "hematology": ["blood", "anemia", "hematology"],
    "obgyn": ["pregnancy", "cervical", "menopause", "breast"],
    "pediatrics": ["children", "infant", "pediatric"],
    "immunology_allergy": ["immune", "allergy", "immunodeficiency"],
}

def classify_topic(title: str) -> list[str]:
    title_lower = title.lower()
    matched = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(k in title_lower for k in keywords):
            matched.append(domain)
    return matched

def clean_text(text: str, max_words=120) -> str:
    text = re.sub(r"<[^>]+>", "", text)  # remove HTML tags
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    return " ".join(words[:max_words])

def generate_questions(title: str) -> list[str]:
    return [
        f"What is {title}?",
        f"What are the symptoms of {title}?",
        f"How is {title} treated?"
    ]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--domains", type=str, required=True)
    parser.add_argument("--per_topic", type=int, default=3)
    parser.add_argument("--max_words", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()

def main():
    args = parse_args()
    random.seed(args.seed)
    output_file = Path(args.out)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 解析 XML
    print("[INFO] Loading XML:", args.xml)
    tree = ET.parse(args.xml)
    root = tree.getroot()
    topics = root.findall("health-topic")
    print("[INFO] Parsed topics:", len(topics))

    # 處理目標 domains
    target_domains = {}
    for item in args.domains.split(","):
        k, v = item.split("=")
        target_domains[k.strip()] = int(v.strip())

    domain_topics = defaultdict(list)

    for topic in topics:
        title_elem = topic.find("title")
        summary_elem = topic.find("full-summary")
        if title_elem is None or summary_elem is None:
            continue
        title = title_elem.text.strip()
        summary = clean_text(summary_elem.text or "", args.max_words)
        if not title or not summary:
            continue
        domains = classify_topic(title)
        for d in domains:
            domain_topics[d].append((title, summary))

    # 分類統計
    print("[INFO] Domain candidate counts:")
    for domain in target_domains:
        print(f"  - {domain}: {len(domain_topics[domain])} candidates")

    # 隨機選擇每個領域的代表 topic
    qa_items = []
    for domain, num_required in target_domains.items():
        pool = domain_topics[domain]
        if not pool:
            print(f"[WARN] domain '{domain}' has 0 candidates")
            continue
        selected = random.sample(pool, min(len(pool), num_required))
        for title, summary in selected:
            questions = generate_questions(title)
            for q in questions[:args.per_topic]:
                qa_items.append({
                    "question": q,
                    "answer": summary,
                    "topic": title,
                    "domain": domain
                })

    print(f"[INFO] Total selected topics: {len(qa_items)//args.per_topic}")
    with open(output_file, "w", encoding="utf-8") as f:
        for item in qa_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[DONE] Wrote {len(qa_items)} QA items to {output_file}")

if __name__ == "__main__":
    main()
