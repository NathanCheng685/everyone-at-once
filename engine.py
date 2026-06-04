"""Instant posterior inference from a precomputed table (no GP at query time).

PosteriorEngine loads artifacts/infer_table_<lang>.npz (a fixed theta pool + the
emulator's predicted option-probabilities) and turns a user's 12 answers into a
posterior over the six-character mix with pure array math — sub-millisecond.
"""
from pathlib import Path

import numpy as np

from prompts import CHARACTERS

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
N_CHARS = 6


class PosteriorEngine:
    def __init__(self, lang):
        self.lang = lang
        path = ARTIFACTS / f"infer_table_{lang}.npz"
        if not path.exists():
            raise FileNotFoundError(
                f"missing {path.name}; run precompute_posterior_table.py --lang {lang}"
            )
        d = np.load(path)
        self.theta = d["theta"].astype(np.float64)            # (P, 6)
        probs = d["probs"].astype(np.float64)                 # (P, 12, 3)
        self.logP = np.log(np.clip(probs, 1e-9, 1.0))         # precompute log
        self.pool = self.theta.shape[0]

    def infer(self, answers, resample=4000, seed=0):
        a = np.asarray(answers, dtype=int)
        if a.shape != (12,) or not set(np.unique(a)).issubset({0, 1, 2}):
            raise ValueError("answers must be 12 ints in {0,1,2}")

        ll = np.zeros(self.pool)
        for q in range(12):
            ll += self.logP[:, q, a[q]]
        ll -= ll.max()
        w = np.exp(ll)
        w /= w.sum()

        ess = float(1.0 / np.sum(w**2))
        mean = w @ self.theta

        rng = np.random.default_rng(seed)
        idx = rng.choice(self.pool, size=min(resample, self.pool), p=w)
        post = self.theta[idx]
        q05, q95 = np.percentile(post, [5, 95], axis=0)

        order = np.argsort(mean)[::-1]
        mix = [
            {
                "id": CHARACTERS[c]["id"],
                "name_en": CHARACTERS[c]["name_en"],
                "name_zh": CHARACTERS[c]["name_zh"],
                "mean": round(float(mean[c]), 4),
                "lo": round(float(q05[c]), 4),
                "hi": round(float(q95[c]), 4),
            }
            for c in order
        ]
        return {
            "lang": self.lang,
            "mix": mix,
            "ess": round(ess, 1),
            "pool": self.pool,
            "top": mix[0]["id"],
        }
