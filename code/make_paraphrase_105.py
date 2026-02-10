#!/usr/bin/env python3
# make_paraphrase_105.py
import argparse
import json
import time
import random
import sys
from pathlib import Path

import requests


PARA_PROMPT_TMPL = (
    "Paraphrase the following medical question while preserving the exact meaning and facet "
    "(definition / symptoms / treatments). Keep it concise and natural. Output only the paraphrased question, "
    "no quotes, no prefixes.\n\nQ: {q}\nParaphrase:"
)


def paraphrase_once(base_url: str, question: str, timeout: float) -> str:
    """Call /llm_only to get a paraphrase for a single question."""
    prompt = PARA_PROMPT_TMPL.format(q=question)
    r = requests.get(
        f"{base_url}/llm_only",
        params={"question": prompt},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    ans = (data.get("results") or [{}])[0].get("answer", "").strip()
    # sanitize: take first non-empty line, strip quotes and label-y prefixes
    if not ans:
        return ""
    line = ans.splitlines()[0].strip()
    # remove leading quotes or "Paraphrase:" etc.
    for bad in ('"', "“", "”", "Paraphrase:", "Paraphrase -", "Q:", "A:"):
        if line.startswith(bad):
            line = line[len(bad):].strip()
    return line


def paraphrase_with_retry(base_url: str, question: str, timeout: float, retries: int, backoff: float) -> str:
    """Retry wrapper with exponential backoff."""
    last_err = None
    for i in range(retries + 1):
        try:
            out = paraphrase_once(base_url, question, timeout)
            if out:
                return out
        except Exception as e:
            last_err = e
        # backoff
        sleep_s = backoff * (2 ** i)
        time.sleep(sleep_s)
    # if all failed, fall back to original question
    if last_err:
        print(f"[WARN] paraphrase failed after {retries+1} tries: {last_err}", file=sys.stderr)
    return question


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser(description="Generate paraphrased version of 105 QA questions via /llm_only.")
    ap.add_argument("--input", default="medline_eval_105.jsonl", help="Input JSONL (original 105)")
    ap.add_argument("--output", default="paraphrase_105.jsonl", help="Output JSONL (paraphrased questions)")
    ap.add_argument("--base", default="http://localhost:8000", help="Base URL of your FastAPI server")
    ap.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout (seconds)")
    ap.add_argument("--sleep", type=float, default=0.8, help="Sleep between requests (seconds)")
    ap.add_argument("--retries", type=int, default=2, help="Max retries per item (exponential backoff)")
    ap.add_argument("--backoff", type=float, default=0.5, help="Initial backoff seconds for retry")
    ap.add_argument("--limit", type=int, default=0, help="Process at most N items (0 = all)")
    ap.add_argument("--start", type=int, default=0, help="Start index (0-based) for processing")
    ap.add_argument("--shuffle", action="store_true", help="Shuffle order before processing")
    args = ap.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"[ERR] Input not found: {inp.resolve()}", file=sys.stderr)
        sys.exit(1)

    items = list(iter_jsonl(inp))
    idxs = list(range(len(items)))
    if args.shuffle:
        random.shuffle(idxs)

    # window by start/limit
    if args.start > 0:
        idxs = idxs[args.start:]
    if args.limit and args.limit > 0:
        idxs = idxs[:args.limit]

    outp = Path(args.output)
    done = 0
    t0 = time.time()

    with outp.open("w", encoding="utf-8") as fout:
        for n, i in enumerate(idxs, start=1):
            obj = items[i]
            q = obj.get("question", "").strip()
            if not q:
                # keep item as-is if no question field
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            new_q = paraphrase_with_retry(args.base, q, args.timeout, args.retries, args.backoff)
            obj2 = dict(obj)
            obj2["question"] = new_q
            fout.write(json.dumps(obj2, ensure_ascii=False) + "\n")
            done += 1

            # progress
            if n % 10 == 0 or n == len(idxs):
                elapsed = time.time() - t0
                print(f"[{n}/{len(idxs)}] saved… avg {elapsed/max(1,n):.2f}s/it")

            time.sleep(args.sleep)

    print(f"Saved: {outp} (items={done})")


if __name__ == "__main__":
    main()
