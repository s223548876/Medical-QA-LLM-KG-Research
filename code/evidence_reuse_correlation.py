import re
import pandas as pd
from scipy.stats import pearsonr


def pick_evidence_text(row):
    if "results_0_subgraph_summary" in row and pd.notna(row["results_0_subgraph_summary"]):
        return str(row["results_0_subgraph_summary"])
    if "subgraph_summary" in row and pd.notna(row["subgraph_summary"]):
        return str(row["subgraph_summary"])
    return ""


def reuse_rate(row):
    import re
    pred = str(row.get("pred_answer", "")).lower()
    ev = pick_evidence_text(row).lower()
    if not ev:
        return 0.0

    # 把 "A → B|C → D" 擴成術語袋
    terms = []
    for seg in ev.split("|"):
        seg = seg.strip()
        if not seg:
            continue
        if "→" in seg:
            a, b = seg.split("→", 1)
            terms.extend([a.strip(), b.strip()])
        else:
            terms.append(seg)

    def tok(s): return set(re.findall(r"[a-z]+", s))
    E = set()
    for t in terms:
        E |= tok(t)

    P = tok(pred)
    if not P or not E:
        return 0.0
    return len(P & E) / max(1, len(P))


def one_file(path, tag):
    df = pd.read_csv(path)
    if "subgraph_summary" not in df.columns:
        df["subgraph_summary"] = df["top_conceptId"].fillna("").astype(str)
    df["reuse_rate"] = df.apply(reuse_rate, axis=1)
    r, p = pearsonr(df["reuse_rate"], df["f1"])
    return {"run": tag, "n": len(df), "pearson_r": r, "p_value": p}


rows = []
rows.append(one_file("res105_v5c_rouge1_fix_b.csv", "105 / v5c / R1"))
rows.append(one_file("res105_v5c_rougel_fix.csv",  "105 / v5c / RL"))
rows.append(one_file("res969_v5c_rouge1.csv",      "858 / v5c / R1"))
rows.append(one_file("res969_v5c_rougel.csv",      "858 / v5c / RL"))

out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv("evidence_reuse_correlation.csv", index=False)
print("Saved: evidence_reuse_correlation.csv")
