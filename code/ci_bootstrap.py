import os
import pandas as pd
import numpy as np

# 四組比較：(資料集, 指標, 純LLM檔, v5c檔, 輸出delta分布檔名)
pairs = [
    ("105", "ROUGE-1", "res105_llm_only_rouge1_v5.csv", "res105_v5c_rouge1.csv", "ci_105_rouge1_delta.csv"),
    ("105", "ROUGE-L", "res105_llm_only_rougel_v5.csv", "res105_v5c_rougel.csv", "ci_105_rougel_delta.csv"),
    ("858", "ROUGE-1", "res969_llm_only_rouge1_v5c.csv", "res969_v5c_rouge1.csv", "ci_858_rouge1_delta.csv"),
    ("858", "ROUGE-L", "res969_llm_only_rougel_v5c.csv", "res969_v5c_rougel.csv", "ci_858_rougel_delta.csv"),
]

def bootstrap_ci(a_csv, b_csv, col="f1", n_boot=2000, seed=0):
    a = pd.read_csv(a_csv)[col].values
    b = pd.read_csv(b_csv)[col].values
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {a_csv}({len(a)}) vs {b_csv}({len(b)})")
    rng = np.random.default_rng(seed)
    diffs = []
    n = len(a)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        diffs.append(b[idx].mean() - a[idx].mean())
    diffs = np.array(diffs)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi), diffs

rows = []
seed = 0
for ds, metric, a_csv, b_csv, out_csv in pairs:
    if not (os.path.exists(a_csv) and os.path.exists(b_csv)):
        print(f"[SKIP] {ds} {metric}: missing files ({a_csv} / {b_csv})")
        continue
    mean, lo, hi, diffs = bootstrap_ci(a_csv, b_csv, seed=seed)
    seed += 1
    print(f"{ds} {metric}: ΔF1 mean={mean:.4f}  95% CI [{lo:.4f}, {hi:.4f}]")
    pd.DataFrame({"deltaF1": diffs}).to_csv(out_csv, index=False)
    rows.append({
        "dataset": ds, "metric": metric,
        "deltaF1_mean": round(mean, 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
        "n_boot": len(diffs)
    })

if rows:
    pd.DataFrame(rows).to_csv("ci_summary.csv", index=False)
    print("Saved: ci_summary.csv")
