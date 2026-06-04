"""Generate the LLM *response surface*: theta -> (12, 3) per-question option probs.

This is the expensive, method-agnostic dataset that Step-3 inference is built on.
Because the blend is non-linear (see blend_linearity_check.py), we must actually
query the LLM across the simplex; later we fit a smooth GP emulator to this surface
and do explicit-likelihood Bayesian inference on top.

Design points (space-filling over the 6-simplex):
  - 6 one-hot corners        (pure characters; should match the sanity tensor)
  - 15 pairwise 50/50 edges  (two-character blends)
  - Dirichlet(alpha) fill     (interior; alpha<1 favors sparse, realistic personas)

Resumable: appends one JSON line per completed theta to
artifacts/response_surface_<lang>.jsonl, and skips indices already present on rerun.
Consolidates to artifacts/response_surface_<lang>.npz at the end.

Run from friends-sbi/:
    python build_response_surface.py --n 48  --lang zh --workers 4         # pilot
    python build_response_surface.py --n 400 --lang zh --workers 4         # full
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from prompts import CHARACTERS, QUESTIONS
from simulator import client, simulate, SimulatorError

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

N_CHARS = 6
N_QS = 12
LANGS = ["zh", "en"]


def design_thetas(n, alpha, seed):
    """Deterministic space-filling design on the 6-simplex (seed-stable)."""
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(N_CHARS):  # corners
        e = np.zeros(N_CHARS)
        e[c] = 1.0
        rows.append(e)
    for i in range(N_CHARS):  # pairwise 50/50 edges
        for j in range(i + 1, N_CHARS):
            e = np.zeros(N_CHARS)
            e[i] = e[j] = 0.5
            rows.append(e)
    n_anchor = len(rows)  # 21
    n_fill = max(0, n - n_anchor)
    for _ in range(n_fill):
        rows.append(rng.dirichlet(np.full(N_CHARS, alpha)))
    return np.array(rows, dtype=float)


def load_done(jsonl_path):
    """Return {idx: (theta(6,), probs(12,3))} already computed (for resume)."""
    done = {}
    if not jsonl_path.exists():
        return done
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            done[int(rec["idx"])] = (
                np.asarray(rec["theta"], dtype=float),
                np.asarray(rec["probs"], dtype=float),
            )
    return done


def preflight():
    """Fast reachability probe so we abort cleanly instead of grinding through
    hundreds of doomed calls when the ROG box is offline."""
    try:
        client.with_options(timeout=8.0).models.list()
        return True
    except Exception as e:
        print(f"PREFLIGHT FAILED: simulator backend unreachable "
              f"({type(e).__name__}: {e}).")
        print("  Wake/boot the ROG box, confirm `ollama serve` is up and its IP "
              "in .env is current, then re-run this command (it resumes).")
        return False


def consolidate(lang):
    """Rebuild the .npz surface from the JSONL checkpoint (no LLM calls)."""
    jsonl = ARTIFACTS / f"response_surface_{lang}.jsonl"
    done = load_done(jsonl)
    if not done:
        print("nothing to consolidate.")
        return 0
    idx_sorted = sorted(done)
    theta_arr = np.stack([done[i][0] for i in idx_sorted])
    probs = np.stack([done[i][1] for i in idx_sorted])
    qids = [q["id"] for q in QUESTIONS]
    np.savez(
        ARTIFACTS / f"response_surface_{lang}.npz",
        thetas=theta_arr, probs=probs, qids=np.array(qids), lang=lang,
    )
    return probs.shape[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=48)
    ap.add_argument("--lang", default="zh", choices=LANGS)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--alpha", type=float, default=0.5, help="Dirichlet conc. for fill")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--consolidate-only", action="store_true",
                    help="rebuild .npz from the JSONL checkpoint and exit (no LLM)")
    args = ap.parse_args()

    if args.consolidate_only:
        m = consolidate(args.lang)
        print(f"consolidated {m} thetas -> artifacts/response_surface_{args.lang}.npz")
        return 0

    thetas = design_thetas(args.n, args.alpha, args.seed)
    n = len(thetas)
    qids = [q["id"] for q in QUESTIONS]
    jsonl = ARTIFACTS / f"response_surface_{args.lang}.jsonl"

    print("=== build_response_surface ===")
    print(f"n={n}  lang={args.lang}  workers={args.workers}  alpha={args.alpha}  seed={args.seed}")
    print(f"checkpoint -> {jsonl.name}\n")

    if not preflight():
        return 3

    done = load_done(jsonl)
    todo_idx = [i for i in range(n) if i not in done]
    print(f"resuming: {len(done)} done, {len(todo_idx)} to go "
          f"(~{len(todo_idx)*N_QS*1.4/60:.0f} min est.)\n")

    # Global task pool across (theta, question); checkpoint a theta only when ALL
    # 12 of its questions succeed. A theta with any failed question is left
    # un-checkpointed so a later resume retries it cleanly (no polluted data).
    tasks = [(i, qi, qids[qi]) for i in todo_idx for qi in range(N_QS)]
    buf = {i: np.full((N_QS, 3), np.nan) for i in todo_idx}
    remaining_q = {i: N_QS for i in todo_idx}
    failed_theta = set()
    n_call_fail = 0

    def work(t):
        i, qi, qid = t
        return i, qi, simulate(thetas[i], qid, args.lang)

    t0 = time.time()
    completed_theta = 0
    with open(jsonl, "a", encoding="utf-8") as fout:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(work, t): t for t in tasks}
            for f in as_completed(futs):
                t = futs[f]
                i = t[0]
                try:
                    _, qi, p = f.result()
                    buf[i][qi] = p
                except Exception as e:  # never let one bad call kill the run
                    n_call_fail += 1
                    if i not in failed_theta:
                        failed_theta.add(i)
                        print(f"  ! theta {i} failed ({type(e).__name__}); "
                              f"will retry on resume", flush=True)
                remaining_q[i] -= 1
                if remaining_q[i] == 0 and i not in failed_theta:
                    rec = {"idx": i, "theta": thetas[i].tolist(),
                           "probs": np.round(buf[i], 4).tolist()}
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    completed_theta += 1
                    if completed_theta % 4 == 0:
                        el = time.time() - t0
                        rate = completed_theta / el if el > 0 else 0
                        eta = (len(todo_idx) - completed_theta) / rate if rate > 0 else 0
                        print(f"  theta {completed_theta}/{len(todo_idx)}  "
                              f"({el:.0f}s, ETA {eta:.0f}s)", flush=True)
                    if completed_theta % 25 == 0:  # crash-safe periodic save
                        consolidate(args.lang)

    if failed_theta:
        print(f"\nWARNING: {len(failed_theta)} thetas had failures "
              f"({n_call_fail} calls); they were NOT saved and will retry on resume.")

    m = consolidate(args.lang)
    print(f"\nsaved surface: {m} thetas x {N_QS} q x 3  "
          f"-> artifacts/response_surface_{args.lang}.npz")
    if failed_theta:
        print("re-run the same command once the ROG box is reachable to fill the rest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
