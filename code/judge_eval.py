import json
import time
import argparse
import os
from openai import OpenAI

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
if not OPENAI_API_KEY:
    raise RuntimeError(
        "Missing OPENAI_API_KEY environment variable. "
        "Please set it before running judge_eval.py."
    )
client = OpenAI(**{"api_key": OPENAI_API_KEY})

# ===============================
# 評分用的 Judge Prompt
# ===============================
JUDGE_PROMPT = """
You are a highly reliable medical answer evaluator.
Your task is to evaluate how well the MODEL ANSWER matches the REFERENCE ANSWER.

Scores range from 1 to 5:

5 = Almost perfect match. Medically accurate, comprehensive, no errors.
4 = Mostly correct. Minor omissions but overall aligned with the reference.
3 = Partially correct. Key ideas missing or some inaccuracies.
2 = Mostly incorrect. Only fragments match.
1 = Incorrect, irrelevant, or medically wrong.

Your output MUST be ONLY a JSON object:
{{"score": X, "justification": "one short sentence"}}

Now evaluate:

QUESTION:
{question}

MODEL ANSWER:
{model_answer}

REFERENCE ANSWER:
{reference_answer}
""".strip()


def run_judge(question: str, model_answer: str, reference_answer: str):
    prompt = JUDGE_PROMPT.format(
        question=question,
        model_answer=model_answer,
        reference_answer=reference_answer,
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
        temperature=0,
    )

    text = resp.choices[0].message.content.strip()

    # 盡量用 JSON 解析；如果失敗，就把原始文字放到 justification
    try:
        data = json.loads(text)
        score = data.get("score", None)
        justification = data.get("justification", "")
    except Exception:
        score = None
        justification = text

    return score, justification


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        required=True,
        help="標準資料 jsonl，例如 medline_eval_105.jsonl",
    )
    parser.add_argument(
        "--answers",
        required=True,
        help="模型答案 jsonl，例如 res105_kw_fix2_answers.jsonl",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="輸出 jsonl，例如 judge_105_kw_fix2_gpt4omini.jsonl",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="每題之間的 sleep 秒數，避免太快打 API",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as fin_gold, \
            open(args.answers, "r", encoding="utf-8") as fin_pred, \
            open(args.out, "w", encoding="utf-8") as fout:

        total = 0
        for line_gold, line_pred in zip(fin_gold, fin_pred):
            gold = json.loads(line_gold)
            pred = json.loads(line_pred)

            # 問題文字
            question = gold.get("question", "")

            # 標準答案：先用 answer，沒有的話用 gold_answer
            reference_answer = gold.get(
                "answer") or gold.get("gold_answer", "")

            # 🔧 模型答案：支援多種欄位格式
            if "model_answer" in pred:
                model_answer = pred["model_answer"]
            elif "pred_answer" in pred:
                model_answer = pred["pred_answer"]
            elif "results" in pred and isinstance(pred["results"], list) and pred["results"]:
                model_answer = pred["results"][0].get("answer", "")
            else:
                # 萬一格式怪怪的，先給空字串，至少不要讓程式 crash
                model_answer = ""

            score, justification = run_judge(
                question=question,
                model_answer=model_answer,
                reference_answer=reference_answer,
            )

            fout.write(
                json.dumps(
                    {
                        "question": question,
                        "reference_answer": reference_answer,
                        "model_answer": model_answer,
                        "score": score,
                        "judge_note": justification,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

            total += 1
            print(f"[{total}] score={score}")
            time.sleep(args.sleep)

    print("Saved:", args.out)


if __name__ == "__main__":
    main()
