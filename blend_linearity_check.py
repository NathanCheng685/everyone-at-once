"""Blend-linearity check — the pivotal Step-3 gate.

Question: is the LLM's *blended-persona* output approximately a linear mixture of
the one-hot character outputs already captured in the sanity tensor?

    pred(opt | q, theta) ?= sum_c theta_c * T[c, q, opt]      (T = sanity tensor)

Why it matters:
  - If YES (small JSD): the per-question likelihood is *explicit*. The user's 12
    answers then have a closed-form likelihood L(theta) = prod_q (sum_c theta_c T[c,q,a_q]),
    whose log is concave on the simplex -> direct, robust Bayesian inference with
    numpy/scipy. No LLM-in-the-loop, no torch, no neural SBI needed.
  - If NO: the blend is emergent/non-linear -> we must simulate each sampled theta
    with the LLM and fit a neural posterior estimator (SBI).

Run from friends-sbi/:
    python blend_linearity_check.py --n 12 --lang zh --workers 4
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from prompts import CHARACTERS, QUESTIONS
from simulator import simulate, SimulatorError

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

LANGS = ["zh", "en"]
N_CHARS = 6
N_QS = 12
UNIFORM = np.full(3, 1.0 / 3.0)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="number of random blended thetas")
    ap.add_argument("--lang", default="zh", choices=LANGS)
    ap.add_argument("--workers", type=int, default=4, help="concurrent simulator calls")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    print("=== blend_linearity_check ===")
    print(f"n={args.n} thetas  lang={args.lang}  workers={args.workers}  seed={args.seed}\n")

    tensor = np.load(ARTIFACTS / "sanity_tensor.npy")  # (6, 12, 2, 3)
    li = LANGS.index(args.lang)
    T = tensor[:, :, li, :]  # (6, 12, 3) — one-hot character response surface

    rng = np.random.default_rng(args.seed)
    # Uniform over the 6-simplex (alpha=1): the genuinely *blended* regime.
    thetas = rng.dirichlet(np.ones(N_CHARS), size=args.n)  # (n, 6)

    qids = [q["id"] for q in QUESTIONS]
    actual = np.full((args.n, N_QS, 3), np.nan)

    tasks = [(i, qi, qid) for i in range(args.n) for qi, qid in enumerate(qids)]

    def work(t):
        i, qi, qid = t
        return i, qi, simulate(thetas[i], qid, args.lang)

    t0 = time.time()
    done = 0
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, t): t for t in tasks}
        for f in as_completed(futs):
            try:
                i, qi, p = f.result()
                actual[i, qi] = p
            except SimulatorError as e:
                failures.append(str(e))
            done += 1
            if done % 12 == 0 or done == len(tasks):
                print(f"  {done}/{len(tasks)} calls  ({time.time()-t0:.0f}s)", flush=True)

    if failures:
        print(f"\nWARNING: {len(failures)} simulator failures (showing up to 3):")
        for msg in failures[:3]:
            print(f"  - {msg}")

    # Linear-mixture prediction: convex combo of one-hot rows (auto-normalized).
    pred = np.einsum("ic,cqo->iqo", thetas, T)  # (n, 12, 3)

    jsd_lin = np.full((args.n, N_QS), np.nan)
    jsd_unif = np.full((args.n, N_QS), np.nan)
    for i in range(args.n):
        for qi in range(N_QS):
            if np.isnan(actual[i, qi]).any():
                continue
            jsd_lin[i, qi] = js_divergence(actual[i, qi], pred[i, qi])
            jsd_unif[i, qi] = js_divergence(actual[i, qi], UNIFORM)

    valid = ~np.isnan(jsd_lin)
    lin = jsd_lin[valid]
    unif = jsd_unif[valid]

    # argmax agreement between actual and linear prediction
    a_arg = actual.argmax(-1)
    p_arg = pred.argmax(-1)
    agree = float((a_arg[valid] == p_arg[valid]).mean())

    median_lin = float(np.median(lin))
    mean_lin = float(np.mean(lin))
    p90_lin = float(np.percentile(lin, 90))
    max_lin = float(np.max(lin))
    median_unif = float(np.median(unif))

    # Decision: linear holds if it's well under the cross-lingual-grade 0.05 bar
    # in the median AND clearly beats the uniform baseline.
    linear_holds = bool(median_lin < 0.05 and median_lin < 0.5 * median_unif)

    print("\n=== blend linearity vs linear-mixture prediction ===")
    print(f"  median JSD (linear pred) : {median_lin:.4f}")
    print(f"  mean   JSD (linear pred) : {mean_lin:.4f}")
    print(f"  p90    JSD (linear pred) : {p90_lin:.4f}")
    print(f"  max    JSD (linear pred) : {max_lin:.4f}")
    print(f"  argmax agreement         : {agree*100:.0f}%")
    print(f"  --- baseline ---")
    print(f"  median JSD (uniform)     : {median_unif:.4f}  (how far actual is from flat)")
    print(f"  pct under 0.05           : {float((lin < 0.05).mean())*100:.0f}%")

    # Worst offenders
    flat = [
        (float(jsd_lin[i, qi]), i, qi)
        for i in range(args.n)
        for qi in range(N_QS)
        if valid[i, qi]
    ]
    flat.sort(reverse=True)
    print("\n=== top-5 worst-fit (theta_idx, q) by linear JSD ===")
    for jv, i, qi in flat[:5]:
        top2 = np.argsort(thetas[i])[::-1][:2]
        blend = " + ".join(
            f"{CHARACTERS[c]['name_zh']}={thetas[i][c]*100:.0f}%" for c in top2
        )
        print(
            f"  JSD={jv:.3f}  q{QUESTIONS[qi]['id']:>2}  [{blend} ...]  "
            f"actual={np.round(actual[i,qi],2).tolist()} pred={np.round(pred[i,qi],2).tolist()}"
        )

    print("\nDECISION:", "LINEAR HOLDS -> explicit-likelihood Bayesian inference"
          if linear_holds else "NON-LINEAR -> LLM-in-the-loop neural SBI")

    np.savez(
        ARTIFACTS / "blend_linearity.npz",
        thetas=thetas, actual=actual, pred=pred, jsd_lin=jsd_lin, jsd_unif=jsd_unif,
    )
    report = {
        "n": args.n, "lang": args.lang, "seed": args.seed,
        "n_failures": len(failures),
        "median_jsd_linear": median_lin,
        "mean_jsd_linear": mean_lin,
        "p90_jsd_linear": p90_lin,
        "max_jsd_linear": max_lin,
        "argmax_agreement": agree,
        "median_jsd_uniform_baseline": median_unif,
        "pct_under_0.05": float((lin < 0.05).mean()),
        "linear_holds": linear_holds,
    }
    with open(ARTIFACTS / "blend_linearity_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> artifacts/blend_linearity_report.json + blend_linearity.npz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
