# evaluate_bertscore.py (patched)
import argparse
import json
import time
import requests
from bert_score import score

COMMON_KEYS = [
    "answer", "output", "result", "text", "response", "content"
]


def extract_text(payload, resp_key=None):
    # 1) 使用者指定欄位優先
    if resp_key and isinstance(payload, dict):
        v = payload.get(resp_key)
        if isinstance(v, str):
            return v
        # 支援 nested: a.b.c
        if "." in resp_key:
            cur = payload
            for k in resp_key.split("."):
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                elif isinstance(cur, list):
                    try:
                        idx = int(k)
                        cur = cur[idx]
                    except:
                        return ""
                else:
                    return ""
            return cur if isinstance(cur, str) else ""
    # 2) 自動猜測常見結構
    if isinstance(payload, dict):
        # OpenAI/Chat Completions 類
        try:
            ch = payload.get("choices")
            if isinstance(ch, list) and ch:
                msg = ch[0].get("message", {})
                if isinstance(msg, dict) and "content" in msg:
                    return msg["content"]
        except:
            pass
        # 常見扁平欄位
        for k in COMMON_KEYS:
            v = payload.get(k)
            if isinstance(v, str) and v.strip():
                return v
    # 3) 字串本體
    if isinstance(payload, str):
        return payload
    return ""


def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def call_api(base_url, endpoint, question, timeout=90):
    url = base_url.rstrip("/") + endpoint
    r = requests.get(url, params={"question": question}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_url", default="http://localhost:8000")
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=999999)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--resp_key", default=None, help="指定回傳欄位（支援 a.b.0.c 路徑）")
    args = ap.parse_args()

    refs, hyps = [], []
    empty_count = 0
    n = 0
    for ex in iter_jsonl(args.input):
        q, ref = ex.get("question", ""), ex.get("answer", "")
        if not q or not ref:
            continue
        try:
            payload = call_api(args.base_url, args.endpoint,
                               q, timeout=args.timeout)
        except Exception:
            payload = ""
        hyp = extract_text(payload, resp_key=args.resp_key)
        if not hyp.strip():
            empty_count += 1
        refs.append(ref)
        hyps.append(hyp)
        n += 1
        if n % 20 == 0:
            print(f"Fetched {n} responses... (empty so far: {empty_count})")
        if n >= args.limit:
            break
        time.sleep(args.sleep)

    print(
        f"Total: {n}, empty candidates: {empty_count} ({empty_count/max(1,n)*100:.1f}%)")

    P, R, F1 = score(hyps, refs, lang="en", verbose=True)
    out = {
        "count": n,
        "precision_mean": float(P.mean()),
        "recall_mean": float(R.mean()),
        "f1_mean": float(F1.mean())
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Saved:", args.out)


if __name__ == "__main__":
    main()
