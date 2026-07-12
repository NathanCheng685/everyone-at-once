"""Instant posterior inference from a precomputed table (no GP at query time).

PosteriorEngine loads artifacts/infer_table_<lang>.npz (a fixed theta pool + the
emulator's predicted option-probabilities) and turns a user's 12 answers into a
posterior over the six-character mix with pure array math — sub-millisecond.

Likelihood tempering (beta): the generative model assumes a user samples answers
from the persona's soft option distribution, but real respondents are far more
decisive than the LLM simulator's mushy probabilities. Untempered, 12 answers
barely move the posterior off the Dirichlet prior (ESS stays ~70-90% of the pool
and every character's mean hovers near 1/6 — the "everything is flat" bug).
Raising the log-likelihood by a calibrated power beta>1 corrects that
miscalibration; beta is chosen by scripts/calibrate_beta.py so that the reported
dominant-character confidence matches its empirical accuracy on simulated
decisive respondents.
"""
from pathlib import Path

import numpy as np

from ip_loader import artifacts_dir, load_characters

N_CHARS = 6

# Calibrated by scripts/calibrate_beta.py (see artifacts/beta_calibration.json).
BETA_DEFAULT = 3.0


class PosteriorEngine:
    def __init__(self, ip_id, lang, beta=None):
        self.ip_id = ip_id
        self.lang = lang
        self.characters = load_characters(ip_id)
        path = artifacts_dir(ip_id) / f"infer_table_{lang}.npz"
        if not path.exists():
            raise FileNotFoundError(
                f"missing {path}; run precompute_posterior_table.py --ip {ip_id} --lang {lang}"
            )
        d = np.load(path)
        self.theta = d["theta"].astype(np.float32)            # (P, 6)
        probs = d["probs"].astype(np.float64)                 # (P, 12, 3)
        # float32 halves resident memory (12 tables live in RAM in production);
        # log-prob precision loss is ~1e-7 relative — far below sampling noise.
        self.logP = np.log(np.clip(probs, 1e-9, 1.0)).astype(np.float32)
        self.pool = self.theta.shape[0]
        self.dom = self.theta.argmax(axis=1)                  # dominant char per pool persona
        self.beta = BETA_DEFAULT if beta is None else float(beta)

    def infer(self, answers, resample=4000, seed=0, beta=None):
        b = self.beta if beta is None else float(beta)
        a = np.asarray(answers, dtype=int)
        if a.shape != (12,) or not set(np.unique(a)).issubset({0, 1, 2}):
            raise ValueError("answers must be 12 ints in {0,1,2}")

        ll = np.zeros(self.pool)
        for q in range(12):
            ll += self.logP[:, q, a[q]]
        ll *= b                                               # tempering
        ll -= ll.max()
        w = np.exp(ll)
        w /= w.sum()

        ess = float(1.0 / np.sum(w**2))
        mean = w @ self.theta

        # P(dominant character = c | answers): weight mass of pool personas
        # whose largest component is c. Far more contrastive than the mean.
        dom_p = np.zeros(N_CHARS)
        np.add.at(dom_p, self.dom, w)

        rng = np.random.default_rng(seed)
        idx = rng.choice(self.pool, size=min(resample, self.pool), p=w)
        post = self.theta[idx]
        q05, q95 = np.percentile(post, [5, 95], axis=0)

        def entry(c):
            ch = self.characters[c]
            e = {
                "id": ch["id"],
                "name_en": ch["name_en"],
                "name_zh": ch["name_zh"],
                "mean": round(float(mean[c]), 4),
                "lo": round(float(q05[c]), 4),
                "hi": round(float(q95[c]), 4),
                "p_dom": round(float(dom_p[c]), 4),
            }
            if ch.get("color"):
                e["color"] = ch["color"]
            if ch.get(f"desc_{self.lang}"):
                e["desc"] = ch[f"desc_{self.lang}"]
            return e

        mix = [entry(c) for c in np.argsort(mean)[::-1]]
        dominant = [entry(c) for c in np.argsort(dom_p)[::-1]]
        return {
            "ip": self.ip_id,
            "lang": self.lang,
            "mix": mix,
            "dominant": dominant,
            "ess": round(ess, 1),
            "pool": self.pool,
            "beta": b,
            "top": dominant[0]["id"],
        }
