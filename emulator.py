"""Smooth emulator of the LLM response surface:  theta (6-simplex) -> (12, 3) probs.

Fits one Gaussian-Process regressor per question in additive-log-ratio (ALR) space
(anchor = option 3), so predictions are always valid 3-simplices on inversion.
Trained on artifacts/response_surface_<lang>.npz (from build_response_surface.py).

The emulator turns the intractable LLM likelihood into an explicit, cheap,
vectorized function P(option | question, theta) — the basis for Bayesian inference.
"""
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel as C
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
N_QS = 12
EPS = 0.02  # floor so log-ratios stay finite (LLM probs are rounded, can hit 0)


def _floor_norm(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, None)
    return p / p.sum(axis=-1, keepdims=True)


def alr(p):
    """(.., 3) simplex -> (.., 2) log-ratios vs option index 2."""
    p = _floor_norm(p)
    return np.stack([np.log(p[..., 0] / p[..., 2]),
                     np.log(p[..., 1] / p[..., 2])], axis=-1)


def inv_alr(y):
    """(.., 2) -> (.., 3) simplex."""
    y = np.asarray(y, dtype=float)
    e = np.concatenate([np.exp(y), np.ones(y.shape[:-1] + (1,))], axis=-1)
    return e / e.sum(axis=-1, keepdims=True)


class ResponseEmulator:
    def __init__(self, lang="zh"):
        self.lang = lang
        self.gprs = None
        self.thetas = None
        self.probs = None

    def _new_gpr(self):
        # Noise ceiling kept low: in normalized-y space a large noise term lets the
        # GP treat the sharp, distinctive corner/edge responses as "noise" and
        # regress them toward the mushy interior mean (the dense Dirichlet fill).
        # Keeping it small preserves corner fidelity (the high-signal regime).
        kernel = (
            C(1.0, (1e-2, 1e2))
            * RBF(length_scale=[0.5] * 6, length_scale_bounds=(0.05, 20.0))
            + WhiteKernel(noise_level=0.02, noise_level_bounds=(1e-5, 0.3))
        )
        return GaussianProcessRegressor(
            kernel=kernel, normalize_y=True, n_restarts_optimizer=3, alpha=1e-6,
        )

    def fit(self, npz_path=None):
        if npz_path is None:
            npz_path = ARTIFACTS / f"response_surface_{self.lang}.npz"
        data = np.load(npz_path, allow_pickle=True)
        self.thetas = data["thetas"]            # (N, 6)
        self.probs = data["probs"]              # (N, 12, 3)
        self.gprs = []
        # Kernel hyperparams hitting bounds is expected for small N; not fatal.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=ConvergenceWarning)
            for qi in range(N_QS):
                Y = alr(self.probs[:, qi, :])   # (N, 2)
                gpr = self._new_gpr()
                gpr.fit(self.thetas, Y)
                self.gprs.append(gpr)
        return self

    def predict_all(self, thetas):
        """thetas (M, 6) -> probs (M, 12, 3)."""
        thetas = np.atleast_2d(np.asarray(thetas, dtype=float))
        out = np.empty((thetas.shape[0], N_QS, 3))
        for qi in range(N_QS):
            y = self.gprs[qi].predict(thetas)   # (M, 2)
            out[:, qi, :] = inv_alr(y)
        return out

    def loglik(self, thetas, answers):
        """Log-likelihood of `answers` (len-12 ints in {0,1,2}) for each theta row.

        thetas (M,6) -> (M,) log P(answers | theta).
        """
        answers = np.asarray(answers, dtype=int)
        probs = self.predict_all(thetas)        # (M, 12, 3)
        picked = np.take_along_axis(
            probs, answers[None, :, None], axis=2
        )[:, :, 0]                               # (M, 12)
        return np.log(np.clip(picked, 1e-12, 1.0)).sum(axis=1)


def corner_report(emu, sanity_path=None):
    """Compare emulator at one-hot corners vs the sanity tensor (sanity check)."""
    if sanity_path is None:
        sanity_path = ARTIFACTS / "sanity_tensor.npy"
    tensor = np.load(sanity_path)               # (6, 12, 2, 3)
    li = ["zh", "en"].index(emu.lang)
    corners = np.eye(6)
    pred = emu.predict_all(corners)             # (6, 12, 3)
    truth = tensor[:, :, li, :]                 # (6, 12, 3)
    mae = float(np.mean(np.abs(pred - truth)))
    argmax_agree = float((pred.argmax(-1) == truth.argmax(-1)).mean())
    return {"corner_mae": mae, "corner_argmax_agree": argmax_agree}


if __name__ == "__main__":
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh"
    emu = ResponseEmulator(lang).fit()
    print(f"fitted emulator on {emu.thetas.shape[0]} thetas ({lang}).")
    print("corner check vs sanity tensor:", corner_report(emu))
