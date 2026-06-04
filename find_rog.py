"""Auto-discover the Ollama (ROG) box on the local /24 and fix .env.

The ROG box gets its LAN IP via DHCP, which keeps changing and breaking the
SIMULATOR_BASE_URL in .env. This scans the current subnet for a host serving
Ollama with the expected model, then rewrites .env's SIMULATOR_BASE_URL.

Run from friends-sbi/:  python find_rog.py
"""
import json
import re
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import SIMULATOR_MODEL

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".env"
PORT = 11434


def my_subnet_prefix():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip.rsplit(".", 1)[0], ip


def probe(host):
    try:
        with urllib.request.urlopen(f"http://{host}:{PORT}/api/tags", timeout=1.5) as r:
            data = json.load(r)
        return host, [m["name"] for m in data.get("models", [])]
    except Exception:
        return host, None


def main():
    prefix, my_ip = my_subnet_prefix()
    print(f"scanning {prefix}.0/24 for Ollama serving '{SIMULATOR_MODEL}' "
          f"(me={my_ip}) ...")
    hosts = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != my_ip]

    serving, exact = [], None
    with ThreadPoolExecutor(max_workers=64) as ex:
        for host, names in ex.map(probe, hosts):
            if names is None:
                continue
            serving.append(host)
            if SIMULATOR_MODEL in names:
                exact = host
                break

    if exact is None and serving:
        exact = serving[0]
        print(f"  note: Ollama found at {serving} but none list '{SIMULATOR_MODEL}'.")

    if exact is None:
        print("  no Ollama host found on this subnet. Is the ROG box on / awake / "
              "on the same LAN, with `ollama serve` running?")
        return 1

    new_url = f"http://{exact}:{PORT}/v1"
    text = ENV.read_text(encoding="utf-8")
    if f"SIMULATOR_BASE_URL={new_url}" in text:
        print(f"  found ROG at {exact} — .env already correct ({new_url}).")
        return 0
    text = re.sub(r"SIMULATOR_BASE_URL=.*", f"SIMULATOR_BASE_URL={new_url}", text)
    ENV.write_text(text, encoding="utf-8")
    print(f"  found ROG at {exact} -> updated .env SIMULATOR_BASE_URL={new_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
