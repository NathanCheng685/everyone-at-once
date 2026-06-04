"""Web backend for the friends-mix quiz.

Loads precomputed inference tables at startup (one per language) so every request
is a sub-millisecond array op. Serves the single-page frontend + a tiny JSON API.

Run from friends-sbi/:  python app.py    then open http://127.0.0.1:8000
"""
import json
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from engine import PosteriorEngine
from prompts import CHARACTERS, QUESTIONS

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
ARTIFACTS = ROOT / "artifacts"
IP_REQUESTS = ARTIFACTS / "ip_requests.jsonl"

app = Flask(__name__, static_folder=str(WEB), static_url_path="")

# The home gallery. Only "available" IPs are playable; the rest are teasers.
# Adding a new IP later = build its response surface + flip status to available.
IPS = [
    {"id": "friends", "title": "Friends", "tagline": "Which of the six live in you?",
     "status": "available", "image": "/img/ip-friends.jpg", "accent": "#C8553D"},
    {"id": "harry-potter", "title": "Harry Potter", "tagline": "Beyond the four houses.",
     "status": "coming_soon", "image": "/img/ip-hp.jpg", "accent": "#7A5C2E"},
    {"id": "got", "title": "Game of Thrones", "tagline": "Which houses share your blood?",
     "status": "coming_soon", "image": "/img/ip-got.jpg", "accent": "#3E5C6B"},
    {"id": "the-office", "title": "The Office", "tagline": "Your Dunder-Mifflin mix.",
     "status": "coming_soon", "image": "/img/ip-office.jpg", "accent": "#5C7A53"},
    {"id": "greek-myth", "title": "Greek Mythology", "tagline": "Which gods move through you?",
     "status": "coming_soon", "image": "/img/ip-greek.jpg", "accent": "#9A7B4F"},
    {"id": "avengers", "title": "Avengers", "tagline": "Your hero composition.",
     "status": "coming_soon", "image": "/img/ip-avengers.jpg", "accent": "#8E4B5C"},
]

ENGINES = {}
for _lang in ("en", "zh"):
    try:
        ENGINES[_lang] = PosteriorEngine(_lang)
        print(f"[engine] loaded {_lang} (pool={ENGINES[_lang].pool})")
    except FileNotFoundError as e:
        print(f"[engine] {_lang} not ready: {e}")


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/api/langs")
def langs():
    return jsonify({"langs": sorted(ENGINES.keys())})


@app.get("/api/ips")
def ips():
    # An IP is only really playable if its inference engine is loaded.
    out = []
    for ip in IPS:
        item = dict(ip)
        if ip["id"] != "friends":
            item["status"] = "coming_soon"
        elif not ENGINES:
            item["status"] = "coming_soon"
        out.append(item)
    return jsonify({"ips": out})


@app.post("/api/submit_ip")
def submit_ip():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not (1 <= len(name) <= 120):
        return jsonify({"error": "please enter an IP name (1-120 chars)"}), 400
    ARTIFACTS.mkdir(exist_ok=True)
    rec = {"name": name, "note": (data.get("note") or "").strip()[:500],
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(IP_REQUESTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    release = time.strftime("%b %-d", time.localtime(time.time() + 86400))
    return jsonify({"ok": True, "release": release})


@app.get("/api/questions")
def questions():
    lang = request.args.get("lang", "en")
    if lang not in ("en", "zh"):
        lang = "en"
    qs = [
        {"id": q["id"], "scenario": q[f"scenario_{lang}"],
         "options": q[f"options_{lang}"]}
        for q in QUESTIONS
    ]
    chars = [{"id": c["id"], "name": c[f"name_{lang}"]} for c in CHARACTERS]
    return jsonify({"lang": lang, "questions": qs, "characters": chars})


@app.post("/api/infer")
def infer():
    data = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip", "friends")
    if ip != "friends":
        return jsonify({"error": f"IP '{ip}' is not available yet"}), 400
    lang = data.get("lang", "en")
    if lang not in ENGINES:
        return jsonify({"error": f"language '{lang}' not available"}), 400
    try:
        answers = [int(x) for x in data.get("answers", [])]
        assert len(answers) == 12
    except Exception:
        return jsonify({"error": "answers must be 12 integers in 0..2"}), 400
    return jsonify(ENGINES[lang].infer(answers))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
