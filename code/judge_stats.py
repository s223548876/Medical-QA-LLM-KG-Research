# judge_stats.py
import json
import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True)
    ap.add_argument("--qtype_csv", required=True)
    ap.add_argument("--prefix", default="judge")
    args = ap.parse_args()

    # load judge results
    rows = []
    with open(args.judge, "r", encoding="utf-8") as f:
        for line in f:
            j = json.loads(line)
            if j.get("score") is not None:
                rows.append(j)

    judge_df = pd.DataFrame(rows)
    print(f"Loaded {len(judge_df)} judged items.")

    # load qtype
    q_df = pd.read_csv(args.qtype_csv)
    if "qtype" not in q_df.columns:
        raise ValueError("CSV must contain qtype column.")

    # merge on question text
    merged = judge_df.merge(
        q_df[["question", "qtype"]], on="question", how="left")

    # overall mean
    overall_mean = merged["score"].mean()
    print("\n=== LLM-as-a-Judge 統計（GPT-4o mini）===")
    print(f"整體平均分數：{overall_mean:.3f}")

    # per qtype
    grp = merged.groupby("qtype")["score"].agg(["mean", "count"])
    print("\n--- 各題型平均分數 ---")
    print(grp)

    # score distribution
    dist = merged["score"].value_counts().sort_index()
    total = len(merged)
    print("\n--- 分數分佈 (1~5) ---")
    print(pd.DataFrame({
        "score": dist.index,
        "count": dist.values,
        "ratio": (dist.values / total).round(3)
    }))

    # save csvs
    merged.to_csv(f"{args.prefix}_stats_per_question.csv", index=False)
    grp.to_csv(f"{args.prefix}_stats_by_qtype.csv")
    pd.DataFrame({
        "score": dist.index,
        "count": dist.values,
        "ratio": (dist.values / total).round(3)
    }).to_csv(f"{args.prefix}_stats_dist.csv", index=False)

    print("\n已輸出：")
    print(f" - {args.prefix}_stats_per_question.csv")
    print(f" - {args.prefix}_stats_by_qtype.csv")
    print(f" - {args.prefix}_stats_dist.csv")


if __name__ == "__main__":
    main()
