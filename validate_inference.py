"""End-to-end validation of the inference pipeline.

Checks:
  [A] Emulator fidelity at one-hot corners vs the sanity tensor.
  [B] Persona recovery: feed the prototypical (argmax) answers of each pure
      character; the posterior should rank that character #1.
  [C] Blend recovery: feed the prototypical answers of a known 50/50 edge
      (a design anchor in the response surface); the top-2 should be those two
      characters.

Run from friends-sbi/:  python validate_inference.py [zh|en]
"""
import sys
from pathlib import Path

import numpy as np

from emulator import ResponseEmulator, corner_report
from inference import infer
from prompts import CHARACTERS

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
N_CHARS = 6


def true_corner_answers(lang):
    tensor = np.load(ARTIFACTS / "sanity_tensor.npy")  # (6,12,2,3)
    li = ["zh", "en"].index(lang)
    return tensor[:, :, li, :].argmax(-1)              # (6,12)


def find_edges(emu):
    """Return list of (i, j, answers) for 50/50 design edges in the surface."""
    out = []
    for r, th in enumerate(emu.thetas):
        nz = np.where(th > 1e-6)[0]
        if len(nz) == 2 and np.allclose(th[nz], 0.5, atol=1e-6):
            ans = emu.probs[r].argmax(-1)
            out.append((int(nz[0]), int(nz[1]), ans))
    return out


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh"
    emu = ResponseEmulator(lang).fit()
    print(f"=== validate_inference ({lang}) — emulator on {emu.thetas.shape[0]} thetas ===\n")

    cr = corner_report(emu)
    print(f"[A] emulator @corners vs sanity tensor:  "
          f"MAE={cr['corner_mae']:.3f}  argmax-agree={cr['corner_argmax_agree']*100:.0f}%\n")

    print("[B] one-hot persona recovery (feed prototypical/argmax answers):")
    ans = true_corner_answers(lang)
    hits = 0
    for c in range(N_CHARS):
        res = infer(ans[c], emu, alpha=0.5, M=40000, seed=0)
        order = list(res["order"])
        rank = order.index(c) + 1
        top = order[0]
        ok = top == c
        hits += ok
        print(f"  {CHARACTERS[c]['name_zh']:<12} -> top={CHARACTERS[top]['name_zh']:<12} "
              f"self={res['post_mean'][c]*100:4.1f}%  rank={rank}/6  "
              f"ESS={res['ess']:.0f}  {'OK' if ok else 'MISS'}")
    print(f"  --> {hits}/{N_CHARS} personas correctly top-ranked\n")

    print("[C] blend recovery (50/50 design edges):")
    edges = find_edges(emu)
    if not edges:
        print("  (no 50/50 edges in current surface yet)")
    for i, j, eans in edges[:6]:
        res = infer(eans, emu, alpha=0.5, M=40000, seed=0)
        top2 = set(res["order"][:2].tolist())
        ok = top2 == {i, j}
        nm = f"{CHARACTERS[i]['name_zh']}+{CHARACTERS[j]['name_zh']}"
        got = "+".join(CHARACTERS[k]["name_zh"] for k in res["order"][:2])
        print(f"  {nm:<22} -> top2={got:<22} "
              f"({res['post_mean'][i]*100:.0f}/{res['post_mean'][j]*100:.0f}%)  "
              f"{'OK' if ok else 'partial'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
