# summarize_efficiency.py
import pandas as pd
from pathlib import Path

FILES = [
    "res105_llm_only_latency.csv",
    "res105_v5c_latency.csv",
    "res969_llm_only_latency.csv",
    "res969_v5c_latency.csv",
]


def brief(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"file": path, "n": 0, "latency_mean": None, "latency_p95": None, "ans_len_mean": None}
    df = pd.read_csv(p)
    latency_mean = round(df["latency_sec"].mean(),
                         3) if "latency_sec" in df.columns else None
    latency_p95 = round(df["latency_sec"].quantile(
        0.95), 3) if "latency_sec" in df.columns else None
    ans_len_mean = round(df["answer_len"].mean(),
                         1) if "answer_len" in df.columns else None
    return {
        "file": path,
        "n": len(df),
        "latency_mean": latency_mean,
        "latency_p95": latency_p95,
        "ans_len_mean": ans_len_mean,
    }


def main():
    rows = [brief(f) for f in FILES]
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv("efficiency_summary.csv", index=False)
    print("\nSaved: efficiency_summary.csv")


if __name__ == "__main__":
    main()
