"""End-to-end smoke test: one simulator call to verify ROG/Ollama reachability + JSON.

Run from `friends-sbi/`:  python connectivity_check.py
"""
import sys
import time

from config import SIMULATOR_BASE_URL, SIMULATOR_MODEL
from simulator import simulate, SimulatorError


def main():
    print("=== connectivity_check ===")
    print(f"SIMULATOR_BASE_URL = {SIMULATOR_BASE_URL}")
    print(f"SIMULATOR_MODEL    = {SIMULATOR_MODEL}")
    print()

    # One-hot θ for character index 0 (Ross / 罗斯), question 1, language zh.
    theta = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    print("Probing simulator: θ = one-hot Ross, question 1, lang = zh ...")
    t0 = time.time()
    try:
        probs = simulate(theta, 1, "zh")
        dt = time.time() - t0
        print()
        print(f"OK   ({dt:.2f}s)")
        print(f"  probs  = {probs.tolist()}")
        print(f"  sum    = {probs.sum():.4f}")
        print(f"  argmax = option {int(probs.argmax()) + 1}")
        return 0
    except SimulatorError as e:
        dt = time.time() - t0
        print()
        print(f"FAIL ({dt:.2f}s)")
        print(f"  {e}")
        print()
        print("Things to check on the ROG side:")
        print("  1. Is `ollama serve` running?")
        print("     Test on ROG:    curl http://localhost:11434/v1/models")
        print(f"  2. Is the model pulled? Expect '{SIMULATOR_MODEL}' in the list.")
        print("     Test on ROG:    ollama list")
        print("  3. OLLAMA_HOST=0.0.0.0:11434 (must NOT be 127.0.0.1, or LAN can't reach).")
        print("     Test on ROG:    echo $OLLAMA_HOST")
        print(f"  4. Is the host/port in .env right? Current: {SIMULATOR_BASE_URL}")
        print("  5. Firewall on ROG allowing inbound TCP 11434?")
        print(f"     Test from THIS machine:  curl {SIMULATOR_BASE_URL}/models")
        print("  6. Same LAN / VLAN? Routing in place?")
        return 1


if __name__ == "__main__":
    sys.exit(main())
