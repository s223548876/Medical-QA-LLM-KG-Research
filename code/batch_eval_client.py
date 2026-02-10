#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import csv
import time
import re
import requests
from collections import Counter
from math import log, exp

# ============ Tokenization ============


def tokenize(text: str):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if t]

# ============ ROUGE-1 / ROUGE-L ============


def rouge1(pred: str, gold: str):
    p_toks, g_toks = tokenize(pred), tokenize(gold)
    if not p_toks or not g_toks:
        return 0.0, 0.0, 0.0
    pc, gc = Counter(p_toks), Counter(g_toks)
    overlap = sum((pc & gc).values())
    prec = overlap / len(p_toks)
    rec = overlap / len(g_toks)
    f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    return prec, rec, f1


def lcs_len(a, b):
    n, m = len(a), len(b)
    dp = [0]*(m+1)
    for i in range(1, n+1):
        prev = 0
        for j in range(1, m+1):
            tmp = dp[j]
            if a[i-1] == b[j-1]:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j-1])
            prev = tmp
    return dp[m]


def rougeL(pred: str, gold: str):
    p_toks, g_toks = tokenize(pred), tokenize(gold)
    if not p_toks or not g_toks:
        return 0.0, 0.0, 0.0
    lcs = lcs_len(p_toks, g_toks)
    prec = lcs / len(p_toks)
    rec = lcs / len(g_toks)
    f1 = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    return prec, rec, f1

# ============ BLEU-4（原生實作，無需外部套件） ============


def ngrams(tokens, n):
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def clipped_precision(candidate, reference, n):
    cand_ngrams = Counter(ngrams(candidate, n))
    ref_ngrams = Counter(ngrams(reference, n))
    if not cand_ngrams:
        return 0.0
    overlap = 0
    for g, c in cand_ngrams.items():
        overlap += min(c, ref_ngrams.get(g, 0))
    return overlap / sum(cand_ngrams.values())


def bleu4(pred: str, gold: str):
    cand = tokenize(pred)
    ref = tokenize(gold)
    if not cand or not ref:
        return 0.0
    # Brevity penalty
    c = len(cand)
    r = len(ref)
    bp = 1.0 if c > r else exp(1 - r / max(c, 1))
    # Modified precisions with smoothing
    precisions = []
    eps = 1e-9
    for n in range(1, 5):
        p_n = clipped_precision(cand, ref, n)
        precisions.append(max(p_n, eps))
    geo_mean = exp(sum(log(p) for p in precisions) / 4.0)
    return bp * geo_mean

# ============ Utils ============


def trim_words(text, max_words, hard_cap=2000):
    text = (text or "").strip()[:hard_cap]
    toks = text.split()
    return " ".join(toks[:max_words]) if len(toks) > max_words else text


def ensure_leading_slash(path: str) -> str:
    return path if path.startswith("/") else "/" + path

# ============ Main ============


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:8000", help="Base URL")
    ap.add_argument("--endpoint", default="/query",
                    help="API endpoint, e.g. /query or /llm_only")
    ap.add_argument("--input", default="medline_eval.jsonl", help="Gold JSONL")
    ap.add_argument("--limit", type=int, default=50, help="Max examples")
    ap.add_argument("--sleep", type=float, default=0.3,
                    help="Sleep seconds between requests")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="HTTP timeout seconds")
    ap.add_argument("--out", default="results.csv", help="Output CSV")
    ap.add_argument(
        "--metric", choices=["rouge1", "rougeL", "bleu4"], default="rougeL")
    ap.add_argument("--gold_max_words", type=int, default=120)
    ap.add_argument("--lite", action="store_true",
                    help="Pass lite=1 to API (skip LLM on server if supported)")
    ap.add_argument("--save_extra", type=str, default="",
                    help="Comma-separated JSONPaths from API response to save as columns, e.g. 'results.0.note,results.0.subgraph_summary'")
    args = ap.parse_args()
    # parse extra jsonpaths, and precompute csv-safe column names
    extra_paths = [p.strip()
                   for p in (args.save_extra or "").split(",") if p.strip()]
    extra_cols = [p.replace(".", "_") for p in extra_paths]

    def _get_path(obj, path):
        cur = obj
        for key in path.split("."):
            if isinstance(cur, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            elif isinstance(cur, dict):
                cur = cur.get(key, None)
            else:
                return None
        return cur

    endpoint = ensure_leading_slash(args.endpoint)
    base = args.host.rstrip("/")

    # Pick scorer
    if args.metric == "rouge1":
        def scorer(p, g): return rouge1(p, g)
    elif args.metric == "rougeL":
        def scorer(p, g): return rougeL(p, g)
    else:  # bleu4
        # store BLEU in F1 column
        def scorer(p, g): return (0.0, 0.0, bleu4(p, g))

    rows, n = [], 0

    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            if args.limit and n >= args.limit:
                break
            ex = json.loads(line)
            q = (ex.get("question") or "").strip()
            gold = trim_words(
                (ex.get("answer") or "").strip(), args.gold_max_words)
            if not q or not gold:
                continue

            pred = ""
            top_concept = ""
            subgraph_size = ""
            err = ""
            qtype = ""
            note = ""
            latency = 0.0

            try:
                params = {"question": q}
                if args.lite:
                    params["lite"] = 1

                t0 = time.time()
                r = requests.get(f"{base}{endpoint}",
                                 params=params, timeout=args.timeout)
                latency = time.time() - t0
                r.raise_for_status()
                data = r.json()
                results = data.get("results") or []
                qtype = data.get("qtype")  # << 新增：題型
                if results:
                    top = results[0]
                    pred = (top.get("answer") or "").strip()
                    top_concept = str(top.get("conceptId") or "")
                    subgraph_size = str(top.get("subgraph_size") or "")
                    note = top.get("note")
                else:
                    err = data.get("error") or "no results"
                    note = None  # << 新增：保持欄位
            except Exception as e:
                err = str(e)
                # 仍確保 latency 至少有值
                if latency == 0.0:
                    latency = time.time() - t0 if 't0' in locals() else 0.0

            prec, rec, f1 = scorer(pred, gold)
            base_row = [q, gold, pred,
                        f1, prec, rec,
                        latency,
                        len(pred) if isinstance(pred, str) else 0,
                        top_concept, subgraph_size,
                        qtype, note, err]
            # extras from raw json response (only if requested and we actually have a response)
            extra_vals = []
            if extra_paths:
                try:
                    # 用 data 這個變數（你上面 requests.get().json() 放在 data）
                    for p in extra_paths:
                        v = _get_path(data, p) if 'data' in locals(
                        ) and isinstance(data, (dict, list)) else None
                        if isinstance(v, list):
                            v = "|".join(map(str, v))
                        extra_vals.append(v)
                except Exception:
                    extra_vals = [None] * len(extra_paths)

            rows.append(base_row + extra_vals)
            n += 1
            time.sleep(args.sleep)

    with open(args.out, "w", encoding="utf-8", newline="") as wf:
        w = csv.writer(wf)
        header = [
            "question", "gold_answer", "pred_answer",
            "f1", "precision", "recall",
            "latency_sec", "answer_len",
            "top_conceptId", "subgraph_size",
            "qtype", "note", "error"
        ]
        if extra_cols:
            header += extra_cols
        w.writerow(header)
        w.writerows(rows)

    ERROR_COL_INDEX = 12

    valid = [r for r in rows if not r[ERROR_COL_INDEX]]
    if valid:
        avg_f1 = sum(r[3] for r in valid) / len(valid)
        avg_p = sum(r[4] for r in valid) / len(valid)
        avg_r = sum(r[5] for r in valid) / len(valid)
        print(f"Evaluated {len(rows)} items (valid={len(valid)}).")
        label = "BLEU-4" if args.metric == "bleu4" else args.metric.upper()
        # 對 BLEU-4，precision/recall 僅作佔位（0）
        print(
            f"Average {label} — F1: {avg_f1:.3f}  P: {avg_p:.3f}  R: {avg_r:.3f}")
    else:
        print(
            f"Evaluated {len(rows)} items — but no valid predictions (errors present).")


if __name__ == "__main__":
    main()
