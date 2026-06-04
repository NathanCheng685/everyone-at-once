"""Loads env config for the simulator backend (Ollama via OpenAI-compatible API)."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")

SIMULATOR_BASE_URL = os.environ.get("SIMULATOR_BASE_URL")
SIMULATOR_MODEL = os.environ.get("SIMULATOR_MODEL")

if not SIMULATOR_BASE_URL or not SIMULATOR_MODEL:
    raise RuntimeError(
        "Missing simulator config. Copy .env.example to .env and fill in "
        "SIMULATOR_BASE_URL (e.g. http://<ROG_IP>:11434/v1) + SIMULATOR_MODEL."
    )
