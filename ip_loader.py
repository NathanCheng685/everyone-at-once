"""Load per-IP characters and questions from ips/<ip_id>/."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IPS_DIR = ROOT / "ips"
ARTIFACTS = ROOT / "artifacts"

PLAYABLE_IPS = ("friends", "harry-potter", "avengers", "naruto")


def ip_dir(ip_id):
    d = IPS_DIR / ip_id
    if not d.is_dir():
        raise FileNotFoundError(f"unknown IP {ip_id!r}; expected {d}")
    return d


def load_characters(ip_id):
    with open(ip_dir(ip_id) / "characters.json", encoding="utf-8") as f:
        chars = json.load(f)["characters"]
    if len(chars) != 6:
        raise ValueError(f"{ip_id}: expected 6 characters, got {len(chars)}")
    return chars


def load_questions(ip_id):
    with open(ip_dir(ip_id) / "questions.json", encoding="utf-8") as f:
        qs = json.load(f)["questions"]
    if len(qs) != 12:
        raise ValueError(f"{ip_id}: expected 12 questions, got {len(qs)}")
    return qs


def questions_by_id(ip_id):
    return {q["id"]: q for q in load_questions(ip_id)}


def artifacts_dir(ip_id):
    d = ARTIFACTS / ip_id
    d.mkdir(parents=True, exist_ok=True)
    return d
