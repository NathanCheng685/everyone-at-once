"""Sanity tensor: simulate 6 one-hot personas × 12 questions × 2 langs.

Builds a (6, 12, 2, 3) tensor of simulator probabilities, then runs 3 checks +
a std diagnostic. Stops with non-zero exit code if any check fails.

Run from `friends-sbi/`:  python sanity_tensor.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

from ip_loader import artifacts_dir, load_characters, load_questions
from simulator import simulate, SimulatorError

N_CHARS = 6
N_QS = 12
LANGS = ["zh", "en"]


def js_divergence(p, q):
    """Jensen-Shannon divergence, base 2, in [0, 1]."""
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = (a > 0) & (b > 0)
        if not mask.any():
            return 0.0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def build_tensor(ip_id, characters, questions):
    tensor = np.zeros((N_CHARS, N_QS, len(LANGS), 3), dtype=float)
    t0 = time.time()
    for ci, ch in enumerate(characters):
        theta = [0.0] * N_CHARS
        theta[ci] = 1.0
        for qi, q in enumerate(questions):
            for li, lang in enumerate(LANGS):
                print(
                    f"  [{ci+1}/{N_CHARS}] {ch['name_zh']:<10} q{q['id']:>2} {lang} ...",
                    end="", flush=True,
                )
                t1 = time.time()
                probs = simulate(theta, q["id"], lang, ip_id)
                tensor[ci, qi, li, :] = probs
                print(f"  {[round(float(x), 3) for x in probs]}  ({time.time()-t1:.1f}s)")
    print(f"\nbuilt tensor in {time.time()-t0:.1f}s, shape={tensor.shape}")
    return tensor


def check_distribution_validity(tensor, tol=1e-3):
    sums = tensor.sum(axis=-1)
    nonneg = bool((tensor >= -tol).all())
    sum_ok = bool(np.allclose(sums, 1.0, atol=tol))
    max_dev = float(np.max(np.abs(sums - 1.0)))
    return {
        "passed": nonneg and sum_ok,
        "nonneg_ok": nonneg,
        "sum_ok": sum_ok,
        "max_sum_deviation": max_dev,
    }


def check_persona_distinguishability(tensor):
    """For each question, count how many distinct argmax options the 6 one-hot
    personas pick (averaged over zh/en). If most questions only produce 1 distinct
    answer, the simulator can't tell characters apart — bail out.
    Pass: median distinct argmaxes per question >= 2.
    """
    mean = tensor.mean(axis=2)  # (C, Q, 3)
    per_q = [len(set(mean[:, qi, :].argmax(axis=-1).tolist())) for qi in range(N_QS)]
    median_distinct = float(np.median(per_q))
    return {
        "passed": median_distinct >= 2,
        "median_distinct_argmax_per_q": median_distinct,
        "per_q_distinct_count": per_q,
    }


def check_cross_lingual_invariance(tensor, threshold=0.05):
    jsd = np.zeros((N_CHARS, N_QS), dtype=float)
    for ci in range(N_CHARS):
        for qi in range(N_QS):
            jsd[ci, qi] = js_divergence(tensor[ci, qi, 0], tensor[ci, qi, 1])
    median = float(np.median(jsd))
    return {
        "passed": median < threshold,
        "median_jsd": median,
        "max_jsd": float(jsd.max()),
        "pct_under_threshold": float((jsd < threshold).mean()),
        "threshold": threshold,
        "_jsd_matrix": jsd,
    }


def top5_jsd_diag(invar_result):
    jsd = invar_result["_jsd_matrix"]
    flat = [(float(jsd[c, q]), c, q) for c in range(N_CHARS) for q in range(N_QS)]
    flat.sort(reverse=True)
    return flat[:5]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="friends")
    args = ap.parse_args()
    characters = load_characters(args.ip)
    questions = load_questions(args.ip)
    adir = artifacts_dir(args.ip)

    print(f"=== sanity_tensor ip={args.ip} (6×12×2) ===\n")
    try:
        tensor = build_tensor(args.ip, characters, questions)
    except SimulatorError as e:
        print(f"\nFAIL — simulator error during build: {e}")
        return 2

    np.save(adir / "sanity_tensor.npy", tensor)

    c1 = check_distribution_validity(tensor)
    c2 = check_persona_distinguishability(tensor)
    c3 = check_cross_lingual_invariance(tensor)

    print("\n=== checks ===")
    print(
        f"[1] Distribution validity:        "
        f"{'PASS' if c1['passed'] else 'FAIL'}   "
        f"max |sum-1| = {c1['max_sum_deviation']:.4f}"
    )
    print(
        f"[2] Persona distinguishability:   "
        f"{'PASS' if c2['passed'] else 'FAIL'}   "
        f"median distinct argmax / q = {c2['median_distinct_argmax_per_q']}  "
        f"per-q: {c2['per_q_distinct_count']}"
    )
    print(
        f"[3] Cross-lingual invariance:     "
        f"{'PASS' if c3['passed'] else 'FAIL'}   "
        f"median JSD = {c3['median_jsd']:.4f}  max JSD = {c3['max_jsd']:.4f}  "
        f"{c3['pct_under_threshold']*100:.0f}% under {c3['threshold']}"
    )

    print("\n=== std diagnostic — top-5 (char, q) by cross-lingual JS divergence ===")
    for jsd_val, c, q in top5_jsd_diag(c3):
        ch_name = characters[c]["name_zh"]
        sc = questions[q]["scenario_zh"][:30]
        print(f"  JSD={jsd_val:.4f}  {ch_name:<10} q{questions[q]['id']:>2}  {sc}...")

    out = {
        "shape": list(tensor.shape),
        "checks": {
            "distribution_validity": c1,
            "persona_distinguishability": c2,
            "cross_lingual_invariance": {
                k: v for k, v in c3.items() if not k.startswith("_")
            },
        },
        "top5_cross_lingual_jsd": [
            {
                "jsd": jsd,
                "character": characters[c]["name_zh"],
                "question_id": questions[q]["id"],
            }
            for jsd, c, q in top5_jsd_diag(c3)
        ],
    }
    with open(adir / "sanity_tensor_report.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    all_pass = c1["passed"] and c2["passed"] and c3["passed"]
    print()
    print("ALL CHECKS:", "PASS" if all_pass else "FAIL — stop and review")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
