import json
import argparse
import collections
import pandas as pd


def load_gold(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            items.append(obj)
    return items


def load_judge(path):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            items.append(obj)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True,
                        help="例如 medline_eval_105.jsonl")
    parser.add_argument("--judge", required=True,
                        help="例如 judge_105_kw_fix2_gpt4omini.jsonl")
    parser.add_argument("--out", required=True,
                        help="輸出統計 CSV，例如 judge_105_stats.csv")
    args = parser.parse_args()

    gold_items = load_gold(args.gold)
    judge_items = load_judge(args.judge)

    if len(gold_items) != len(judge_items):
        print(
            f"[警告] gold({len(gold_items)}) 與 judge({len(judge_items)}) 行數不一致，將以 zip 對齊較短的一方。")

    rows = []
    for idx, (g, j) in enumerate(zip(gold_items, judge_items), start=1):
        qtype = g.get("qtype", "unknown")
        score = j.get("score", None)
        rows.append({
            "index": idx,
            "qtype": qtype,
            "score": score,
            "question": g.get("question", ""),
        })

    df = pd.DataFrame(rows)

    # 只保留有分數的
    df_valid = df[df["score"].notna()].copy()
    n = len(df_valid)
    overall_mean = df_valid["score"].mean()

    print("=== LLM-as-a-Judge 統計（GPT-4o mini）===")
    print(f"總題數 (有分數)：{n}")
    print(f"整體平均分數：{overall_mean:.3f}")

    # 各 qtype 平均
    print("\n--- 各題型平均分數 ---")
    by_qtype = df_valid.groupby("qtype")["score"].agg(
        ["mean", "count"]).reset_index()
    by_qtype = by_qtype.sort_values("qtype")
    print(by_qtype.to_string(index=False))

    # 分數分佈
    print("\n--- 分數分佈 (1~5) ---")
    cnt = collections.Counter(df_valid["score"])
    dist_rows = []
    for s in range(1, 6):
        c = cnt.get(s, 0)
        p = c / n if n > 0 else 0.0
        dist_rows.append({"score": s, "count": c, "ratio": round(p, 3)})
    df_dist = pd.DataFrame(dist_rows)
    print(df_dist.to_string(index=False))

    # 全部寫出到 CSV
    # 1) 每題一列
    df_valid.to_csv(args.out.replace(".csv", "_per_question.csv"),
                    index=False, encoding="utf-8-sig")
    # 2) 題型平均
    by_qtype.to_csv(args.out.replace(".csv", "_by_qtype.csv"),
                    index=False, encoding="utf-8-sig")
    # 3) 分數分佈
    df_dist.to_csv(args.out.replace(".csv", "_dist.csv"),
                   index=False, encoding="utf-8-sig")

    print("\n已輸出：")
    print(" -", args.out.replace(".csv", "_per_question.csv"))
    print(" -", args.out.replace(".csv", "_by_qtype.csv"))
    print(" -", args.out.replace(".csv", "_dist.csv"))


if __name__ == "__main__":
    main()
