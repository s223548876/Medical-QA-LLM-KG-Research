import pandas as pd

# 檔名：舊 v5c（before） vs 新 fix（after）
R1_BEFORE = "res105_v5c_rouge1.csv"
R1_AFTER = "res105_v5c_rouge1_fix_b.csv"
RL_BEFORE = "res105_v5c_rougel.csv"
RL_AFTER = "res105_v5c_rougel_fix.csv"


def facet_stats(path):
    df = pd.read_csv(path)
    return df.groupby("qtype")[["precision", "recall", "f1"]].mean()


def delta_table(before_csv, after_csv, metric_name):
    b = facet_stats(before_csv).round(3)
    a = facet_stats(after_csv).round(3)
    j = b.join(a, lsuffix="_before", rsuffix="_after")
    for col in ["precision", "recall", "f1"]:
        j[f"{col}_Δ"] = (j[f"{col}_after"] - j[f"{col}_before"]).round(3)
    j.insert(0, "metric", metric_name)
    return j.reset_index()


tables = []
tables.append(delta_table(R1_BEFORE, R1_AFTER, "ROUGE-1"))
tables.append(delta_table(RL_BEFORE, RL_AFTER, "ROUGE-L"))
out = pd.concat(tables, ignore_index=True)
print(out)
out.to_csv("facet_compare_105_before_after.csv", index=False)
print("Saved: facet_compare_105_before_after.csv")
