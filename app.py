"""Web backend for EveryoneAtOnce multi-IP personality-mix quiz."""
import json
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from engine import PosteriorEngine
from ip_loader import artifacts_dir, load_characters, load_questions

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
ARTIFACTS = ROOT / "artifacts"
IP_REQUESTS = ARTIFACTS / "ip_requests.jsonl"

app = Flask(__name__, static_folder=str(WEB), static_url_path="")

IPS = [
    {"id": "friends", "title": "Friends", "title_zh": "老友记",
     "tagline": "Which of the six live in you?", "tagline_zh": "六个人里,你住着哪几个?",
     "image": "/img/ip-friends.jpg", "accent": "#C8553D"},
    {"id": "harry-potter", "title": "Harry Potter", "title_zh": "哈利·波特",
     "tagline": "Beyond the four houses.", "tagline_zh": "四个学院之外的你。",
     "image": "/img/ip-hp.jpg", "accent": "#7A5C2E"},
    {"id": "avengers", "title": "Avengers", "title_zh": "复仇者联盟",
     "tagline": "Your hero composition.", "tagline_zh": "你的英雄构成。",
     "image": "/img/ip-avengers.jpg", "accent": "#8E4B5C"},
    {"id": "naruto", "title": "Naruto", "title_zh": "火影忍者",
     "tagline": "Your ninja-team blend.", "tagline_zh": "你的忍者小队配比。",
     "image": "/img/ip-naruto.svg", "accent": "#E67E22"},
    # Coming soon — no artifacts yet, so _ip_available() reports them as coming_soon.
    {"id": "greek-mythology", "title": "Greek Mythology", "title_zh": "希腊神话",
     "tagline": "Olympians in your blood.", "tagline_zh": "你血脉里的奥林匹斯众神。",
     "image": "/img/ip-greek.jpg", "accent": "#3E6B8E"},
    {"id": "chinese-mythology", "title": "Chinese Mythology", "title_zh": "中国神话",
     "tagline": "Gods and beasts of mountains and seas.", "tagline_zh": "山海之间的神与兽。",
     "image": "/img/ip-chinese-mythology.svg", "accent": "#9E2B2B"},
]

ENGINES = {}
for ip in IPS:
    for lang in ("en", "zh"):
        try:
            ENGINES[(ip["id"], lang)] = PosteriorEngine(ip["id"], lang)
            print(f"[engine] {ip['id']} / {lang} (pool={ENGINES[(ip['id'], lang)].pool})")
        except FileNotFoundError as e:
            print(f"[engine] {ip['id']} / {lang} not ready: {e}")


def _ip_available(ip_id):
    return any(k[0] == ip_id for k in ENGINES)


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/api/langs")
def langs():
    langs_set = sorted({lang for _, lang in ENGINES})
    return jsonify({"langs": langs_set})


@app.get("/api/ips")
def ips():
    out = []
    for ip in IPS:
        item = dict(ip)
        item["status"] = "available" if _ip_available(ip["id"]) else "coming_soon"
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
    ip = request.args.get("ip", "friends")
    lang = request.args.get("lang", "en")
    if lang not in ("en", "zh"):
        lang = "en"
    if not _ip_available(ip):
        return jsonify({"error": f"IP '{ip}' is not available yet"}), 400
    qs_raw = load_questions(ip)
    qs = [
        {"id": q["id"], "scenario": q[f"scenario_{lang}"],
         "options": q[f"options_{lang}"]}
        for q in qs_raw
    ]
    chars = []
    for c in load_characters(ip):
        ch = {"id": c["id"], "name": c[f"name_{lang}"]}
        if c.get("color"):
            ch["color"] = c["color"]
        if c.get(f"desc_{lang}"):
            ch["desc"] = c[f"desc_{lang}"]
        chars.append(ch)
    return jsonify({"ip": ip, "lang": lang, "questions": qs, "characters": chars})


@app.post("/api/infer")
def infer():
    data = request.get_json(force=True, silent=True) or {}
    ip = data.get("ip", "friends")
    lang = data.get("lang", "en")
    key = (ip, lang)
    if key not in ENGINES:
        return jsonify({"error": f"IP '{ip}' ({lang}) is not available yet"}), 400
    try:
        answers = [int(x) for x in data.get("answers", [])]
        assert len(answers) == 12
    except Exception:
        return jsonify({"error": "answers must be 12 integers in 0..2"}), 400
    return jsonify(ENGINES[key].infer(answers))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
