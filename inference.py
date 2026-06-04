"""Bayesian inference of the six-character mix theta from 12 answers.

Because the GP emulator gives an explicit likelihood P(answers | theta), and a
user's 12 categorical answers are a *weak* constraint (the posterior is diffuse,
not a spike), self-normalized importance sampling (SNIS) from the prior is both
exact and well-suited here: proposal == prior == Dirichlet(alpha), so weights are
proportional to the likelihood alone. We report the effective sample size (ESS)
so diffuse/over-concentrated cases are visible rather than hidden.
"""
import numpy as np

from prompts import CHARACTERS

N_CHARS = 6


def infer(answers, emu, alpha=0.5, M=50000, seed=0):
    """answers: len-12 ints in {0,1,2}. emu: fitted ResponseEmulator.

    Returns a dict with posterior summaries over theta in Delta^5.
    """
    answers = np.asarray(answers, dtype=int)
    assert answers.shape == (12,), f"need 12 answers, got {answers.shape}"
    assert set(np.unique(answers)).issubset({0, 1, 2}), "answers must be in {0,1,2}"

    rng = np.random.default_rng(seed)
    theta = rng.dirichlet(np.full(N_CHARS, alpha), size=M)  # (M, 6) prior == proposal

    ll = emu.loglik(theta, answers)                         # (M,)
    ll -= ll.max()
    w = np.exp(ll)
    w /= w.sum()                                            # SNIS weights ∝ likelihood

    ess = float(1.0 / np.sum(w**2))
    post_mean = w @ theta                                   # (6,)

    # Resample for credible intervals / downstream sampling.
    idx = rng.choice(M, size=min(M, 20000), p=w)
    post = theta[idx]                                       # (R, 6)
    q05, q50, q95 = np.percentile(post, [5, 50, 95], axis=0)

    order = np.argsort(post_mean)[::-1]
    return {
        "answers": answers.tolist(),
        "alpha": alpha,
        "M": M,
        "ess": ess,
        "post_mean": post_mean,
        "q05": q05,
        "q50": q50,
        "q95": q95,
        "order": order,
        "post_samples": post,
    }


def summarize(res, lang="zh"):
    name_key = f"name_{lang}" if lang in ("zh", "en") else "name_zh"
    lines = []
    lines.append(f"ESS = {res['ess']:.0f} / {res['M']}  "
                 f"({'diffuse' if res['ess'] > res['M'] * 0.3 else 'concentrated'})")
    lines.append("posterior mix (mean [90% CI]):")
    for c in res["order"]:
        nm = CHARACTERS[c][name_key]
        mean = res["post_mean"][c] * 100
        lo = res["q05"][c] * 100
        hi = res["q95"][c] * 100
        bar = "#" * int(round(mean / 3))
        lines.append(f"  {nm:<12} {mean:5.1f}%  [{lo:4.1f}-{hi:4.1f}]  {bar}")
    return "\n".join(lines)
