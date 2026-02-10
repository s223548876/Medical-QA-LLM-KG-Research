# paraphrase_delta_ci.py
import pandas as pd
import numpy as np


R1_ORIG = "res105_v5c_rouge1_fix_b.csv"
RL_ORIG = "res105_v5c_rougel_fix.csv"
R1_PARA = "res105_v5c_paraphrase_rouge1.csv"
RL_PARA = "res105_v5c_paraphrase_rougel.csv"


def delta_ci(orig_csv, para_csv, n_boot=2000, seed=0):
    a = pd.read_csv(orig_csv)["f1"].values
    b = pd.read_csv(para_csv)["f1"].values
    assert len(a) == len(b), "length mismatch"
    d = b - a
    rng = np.random.default_rng(seed)
    boot = []
    n = len(d)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        boot.append(d[idx].mean())
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi)


for metric, (orig, para) in {
    "ROUGE-1": (R1_ORIG, R1_PARA),
    "ROUGE-L": (RL_ORIG, RL_PARA),
}.items():
    mean, lo, hi = delta_ci(orig, para, seed=42)
    print(
        f"{metric}  ΔF1 (paraphrase - original) = {mean:.4f}   95% CI [{lo:.4f}, {hi:.4f}]")
