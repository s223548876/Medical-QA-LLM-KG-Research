import pandas as pd
IN_CSV = "res105_v5c_rouge1_fix_b.csv"
df = pd.read_csv(IN_CSV)

need = ["question", "gold_answer", "pred_answer",
        "f1", "precision", "recall", "qtype", "note"]
for col in need:
    if col not in df.columns:
        raise SystemExit(f"missing col: {col}")

out_frames = []
for facet in ["definition", "symptoms", "treatments"]:
    sub = df[df["qtype"] == facet].copy()
    sub = sub.sort_values("f1").head(20)
    sub.insert(0, "facet", facet)
    out_frames.append(sub[["facet"]+need])

out = pd.concat(out_frames, ignore_index=True)
out.to_csv("bottom20_by_facet_all.csv", index=False)
print("Saved: bottom20_by_facet_all.csv")
