"""Which-friend-are-you CLI: 12 answers -> your six-character mix.

Usage (from friends-sbi/):
    python whoami.py --lang zh --answers 1,3,2,1,2,3,1,1,2,3,2,1
    python whoami.py --lang zh --interactive
"""
import argparse

import numpy as np

from emulator import ResponseEmulator
from inference import infer, summarize
from prompts import CHARACTERS, QUESTIONS_BY_ID, QUESTIONS


def parse_answers(s):
    vals = [int(x) for x in s.replace(" ", "").split(",") if x != ""]
    if len(vals) != 12 or any(v not in (1, 2, 3) for v in vals):
        raise SystemExit("--answers must be 12 comma-separated values in {1,2,3}")
    return [v - 1 for v in vals]  # to 0-indexed


def interactive(lang):
    print("回答下面 12 个情境题（输入 1/2/3）：\n" if lang == "zh"
          else "Answer the 12 scenarios (type 1/2/3):\n")
    answers = []
    for q in QUESTIONS:
        print(q[f"scenario_{lang}"])
        for k, opt in enumerate(q[f"options_{lang}"]):
            print(f"  {k+1}. {opt}")
        while True:
            raw = input("> ").strip()
            if raw in ("1", "2", "3"):
                answers.append(int(raw) - 1)
                break
            print("请输入 1 / 2 / 3" if lang == "zh" else "Please type 1 / 2 / 3")
        print()
    return answers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="zh", choices=["zh", "en"])
    ap.add_argument("--answers", help="12 comma-separated values in {1,2,3}")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--M", type=int, default=50000)
    args = ap.parse_args()

    emu = ResponseEmulator(args.lang).fit()

    if args.interactive:
        answers = interactive(args.lang)
    elif args.answers:
        answers = parse_answers(args.answers)
    else:
        raise SystemExit("provide --answers or --interactive")

    res = infer(answers, emu, alpha=args.alpha, M=args.M)
    print("\n" + summarize(res, args.lang))

    order = res["order"]
    top, second = order[0], order[1]
    nm = f"name_{args.lang}"
    print()
    if args.lang == "zh":
        print(f"你最像 {CHARACTERS[top][nm]}（{res['post_mean'][top]*100:.0f}%），"
              f"其次是 {CHARACTERS[second][nm]}（{res['post_mean'][second]*100:.0f}%）。")
    else:
        print(f"You're most like {CHARACTERS[top][nm]} "
              f"({res['post_mean'][top]*100:.0f}%), then {CHARACTERS[second][nm]} "
              f"({res['post_mean'][second]*100:.0f}%).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
