"""Calibrate the likelihood-tempering exponent beta for PosteriorEngine.

Simulated respondents: draw ground-truth personas theta* from the pool, then
sample 12 answers from the emulated option probabilities sharpened by a
decisiveness power gamma (real people answer far more deterministically than
the LLM simulator's soft probabilities; gamma=3 is the reference user model,
with gamma=2 and 5 as sensitivity checks).

For each beta on the grid we score, over all available (ip, lang) tables:
  - acc:  P(predicted dominant character == theta*'s largest component)
  - conf: mean reported P(dominant) of the winner (should track acc)
  - gap:  conf - acc  (positive = overconfident, negative = underconfident)
  - ess:  mean effective sample size (resampling stability guard)

Pick the beta with the best accuracy whose |gap| stays small at gamma=3.

Run:  .venv/bin/python scripts/calibrate_beta.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ip_loader import ARTIFACTS  # noqa: E402

BETAS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]
GAMMAS = [2.0, 3.0, 5.0]
N_USERS = 200
SEED = 7


def tables():
    for d in sorted(ARTIFACTS.iterdir()):
        if not d.is_dir():
            continue
        for lang in ("zh", "en"):
            p = d / f"infer_table_{lang}.npz"
            if p.exists():
                yield d.name, lang, p


def simulate_users(theta, probs, gamma, rng):
    """Pick N_USERS pool personas, sample decisive answers. -> (idx, answers)"""
    idx = rng.choice(theta.shape[0], size=N_USERS, replace=False)
    p = probs[idx] ** gamma                                  # (U, 12, 3)
    p /= p.sum(-1, keepdims=True)
    u = rng.random((N_USERS, 12, 1))
    answers = (p.cumsum(-1) < u).sum(-1)                     # inverse-CDF sample
    return idx, answers.astype(int)


def batch_posterior(logP, dom, answers, beta):
    """answers (U,12) -> dominant-char posterior (U,6), ess (U,)."""
    U = answers.shape[0]
    P = logP.shape[0]
    ll = np.zeros((P, U), dtype=np.float32)
    for q in range(12):
        ll += logP[:, q, answers[:, q]]
    ll *= beta
    ll -= ll.max(axis=0, keepdims=True)
    w = np.exp(ll)
    w /= w.sum(axis=0, keepdims=True)                        # (P, U)
    ess = 1.0 / (w**2).sum(axis=0)
    dom_p = np.zeros((6, U), dtype=np.float64)
    for c in range(6):
        dom_p[c] = w[dom == c].sum(axis=0)
    return dom_p.T, ess


def main():
    rng = np.random.default_rng(SEED)
    per_gamma = {g: {b: {"acc": [], "conf": [], "ess": []} for b in BETAS} for g in GAMMAS}
    tabs = list(tables())
    print(f"calibrating over {len(tabs)} tables, {N_USERS} users each, "
          f"gammas={GAMMAS}, betas={BETAS}\n")
    for ip, lang, path in tabs:
        d = np.load(path)
        theta = d["theta"].astype(np.float32)
        probs = d["probs"].astype(np.float32)
        logP = np.log(np.clip(probs, 1e-9, 1.0)).astype(np.float32)
        dom = theta.argmax(1)
        for g in GAMMAS:
            idx, answers = simulate_users(theta, probs, g, rng)
            truth = dom[idx]
            for b in BETAS:
                dom_p, ess = batch_posterior(logP, dom, answers, b)
                pred = dom_p.argmax(1)
                per_gamma[g][b]["acc"].append(float((pred == truth).mean()))
                per_gamma[g][b]["conf"].append(float(dom_p.max(1).mean()))
                per_gamma[g][b]["ess"].append(float(ess.mean()))
        print(f"  done {ip}/{lang}")

    report = {}
    for g in GAMMAS:
        print(f"\n=== gamma={g} (user decisiveness) ===")
        print(f"  {'beta':>5} {'acc':>6} {'conf':>6} {'gap':>7} {'ess':>9}")
        report[str(g)] = {}
        for b in BETAS:
            r = per_gamma[g][b]
            acc, conf = np.mean(r["acc"]), np.mean(r["conf"])
            print(f"  {b:>5} {acc:>6.3f} {conf:>6.3f} {conf-acc:>+7.3f} {np.mean(r['ess']):>9.0f}")
            report[str(g)][str(b)] = {"acc": round(acc, 4), "conf": round(conf, 4),
                                      "ess": round(float(np.mean(r["ess"])), 1)}

    out = ARTIFACTS / "beta_calibration.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
