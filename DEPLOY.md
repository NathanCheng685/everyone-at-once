# Deploy EveryoneAtOnce to Railway

## What gets deployed (~50 MB)

- Flask app + precomputed `artifacts/<ip>/infer_table_{en,zh}.npz` per playable IP
- `web/` (UI + images)
- **Not** uploaded: `.venv`, LLM training surfaces, `.env`

## 1. Push to GitHub

```bash
cd friends-sbi
git init
git add .
git commit -m "Railway deploy: EAO web app"
```

Create a **new empty repo** on GitHub (e.g. `everyone-at-once`), then:

```bash
git remote add origin https://github.com/YOUR_USER/everyone-at-once.git
git branch -M main
git push -u origin main
```

## 2. Railway (matches your dashboard)

1. [railway.com](https://railway.com) → **New project**
2. **GitHub Repository** → authorize GitHub → select your repo
3. If the repo root is not `friends-sbi`, set **Root Directory** to `friends-sbi` (or push only `friends-sbi` as repo root — recommended)
4. Railway reads `railway.toml` + `Procfile` automatically
5. **Settings → Networking → Generate Domain** → copy `https://….up.railway.app`
6. Send that link to HR

## 3. First deploy notes

- **Build** ~2–3 min (install numpy + gunicorn)
- **Start** loads all playable `infer_table_{en,zh}.npz` into RAM — currently 8
  tables (friends, harry-potter, avengers, naruto × en/zh), ~24 MB each
  (~60–120 s cold start on free tier)
- **Health check** hits `/api/langs` — needs at least `en` or `zh` engine loaded
- **RAM**: 8 tables expand to **~400 MB+** live (float64 log-probs), so use
  **≥ 1 GB**. The 512 MB tier will OOM. If you add more IPs, budget ~50 MB RAM per
  (IP × lang). Bump service memory in Railway settings if it restarts on boot.

## 4. Optional: custom domain

Settings → Networking → Custom Domain → add `eao.mylit.net` (DNS CNAME to Railway target)

## Local prod smoke test

```bash
pip install -r requirements-railway.txt
PORT=8000 gunicorn app:app --bind 0.0.0.0:8000 --workers 1
```
