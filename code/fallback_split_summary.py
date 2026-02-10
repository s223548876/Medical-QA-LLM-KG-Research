import pandas as pd


def summarize(path, tag):
    df = pd.read_csv(path)
    note_col = None
    if "results_0_note" in df.columns:
        note_col = "results_0_note"
    elif "note" in df.columns:
        note_col = "note"

    if note_col is None:
        df["fallback_on"] = False
    else:
        df["fallback_on"] = df[note_col].fillna("").str.contains(
            "fallback|lite", case=False, regex=True)

    out = []
    for facet in ["definition", "symptoms", "treatments", "ALL"]:
        sub = df if facet == "ALL" else df[df["qtype"] == facet]
        for on in [True, False]:
            s = sub[sub["fallback_on"] == on]
            if len(s) == 0:
                continue
            out.append({
                "run": tag, "qtype": facet,
                "fallback_on": on,
                "n": len(s),
                "precision": s["precision"].mean(),
                "recall": s["recall"].mean(),
                "f1": s["f1"].mean()
            })
    return pd.DataFrame(out)


rows = []
rows.append(summarize("res105_v5c_rouge1_fix_b.csv", "105 / v5c / R1"))
rows.append(summarize("res105_v5c_rougel_fix.csv",  "105 / v5c / RL"))
rows.append(summarize("res969_v5c_rouge1.csv",      "858 / v5c / R1"))
rows.append(summarize("res969_v5c_rougel.csv",      "858 / v5c / RL"))

out = pd.concat(rows, ignore_index=True)
print(out.to_string(index=False))
out.to_csv("fallback_split_summary.csv", index=False)
print("Saved: fallback_split_summary.csv")
