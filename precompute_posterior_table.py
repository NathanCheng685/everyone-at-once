"""Precompute a fixed inference table so per-user inference is instant (ms).

Offline (once per language):
  1. Fit the GP emulator on response_surface_<lang>.npz.
  2. Sample a large, fixed pool of personas theta ~ Dirichlet(alpha).
  3. Emulate P(option | question, theta) for the whole pool.
  4. Save (theta_pool, probs) to artifacts/infer_table_<lang>.npz.

Online (engine.py): a user's 12 answers become a likelihood by gathering the
answered options' precomputed probs — pure array math, no GP calls. This is what
makes the web app fast.

Run from friends-sbi/:  python precompute_posterior_table.py --lang zh --pool 150000
"""
import argparse
import time
from pathlib import Path

import numpy as np

from emulator import ResponseEmulator
from ip_loader import artifacts_dir

N_CHARS = 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="friends", help="IP id (folder under ips/)")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"])
    ap.add_argument("--pool", type=int, default=150000, help="theta pool size")
    ap.add_argument("--alpha", type=float, default=0.5, help="Dirichlet prior conc.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch", type=int, default=20000)
    args = ap.parse_args()

    print(f"=== precompute_posterior_table ip={args.ip} lang={args.lang} ===")
    t0 = time.time()
    emu = ResponseEmulator(args.lang, ip_id=args.ip).fit()
    print(f"emulator fit on {emu.thetas.shape[0]} thetas ({time.time()-t0:.0f}s)")

    rng = np.random.default_rng(args.seed)
    theta = rng.dirichlet(np.full(N_CHARS, args.alpha), size=args.pool)  # (P,6)

    probs = np.empty((args.pool, 12, 3), dtype=np.float32)
    t1 = time.time()
    for s in range(0, args.pool, args.batch):
        e = min(s + args.batch, args.pool)
        probs[s:e] = emu.predict_all(theta[s:e]).astype(np.float32)
        print(f"  emulated {e}/{args.pool}  ({time.time()-t1:.0f}s)", flush=True)

    out = artifacts_dir(args.ip) / f"infer_table_{args.lang}.npz"
    np.savez(out, theta=theta.astype(np.float32), probs=probs,
             alpha=args.alpha, seed=args.seed, lang=args.lang)
    print(f"\nsaved {args.pool}-persona table -> {out.name}  "
          f"(total {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
