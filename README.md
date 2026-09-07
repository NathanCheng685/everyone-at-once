# EveryoneAtOnce (众我)

Answer a handful of everyday questions and find out which character from a story world you most resemble, and how confident that match really is.

Live: [eao.nathanchengyi.com](https://eao.nathanchengyi.com)

## How it works

EveryoneAtOnce does not use a hand-written scoring table. It treats "which character are you" as a Bayesian inference problem:

1. **Simulate.** For every character in a story world (IP), a local LLM (Ollama, `qwen2.5:14b-instruct`) role-plays that character answering each question many times. This builds an empirical likelihood of each answer given each character.
2. **Precompute.** The simulated answers are compressed into a per-IP inference table (`artifacts/<ip>/infer_table_{en,zh}.npz`), so the web app never calls an LLM at request time.
3. **Infer.** When a visitor answers, the app combines the likelihoods for their answers into a posterior over characters. The posterior is tempered so that a dominant match stands out instead of every character sitting near the prior.

The result page shows the dominant character and the full posterior, in English or Chinese.

## Story worlds

Friends, Harry Potter, Avengers, Naruto, FIFA, NBA. Each IP lives in `ips/<ip>/` as `characters.json` plus `questions.json`, and can be added without touching the inference code.

## Stack

- Backend: Python, Flask, NumPy
- Frontend: static HTML/JS in `web/`
- Data production: Ollama through its OpenAI-compatible API (`emulator.py`, `precompute_posterior_table.py`)
- Diagnostics: `blend_linearity_check.py`, `build_response_surface.py`, `connectivity_check.py`

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # only needed for data production, not for serving
python app.py
```

The precomputed tables in `artifacts/` are enough to serve the site. To regenerate them for a new IP, point `.env` at a machine running `ollama serve` and run the precompute script.

## Deployment

See `DEPLOY.md` (Railway) and `EC2_DEPLOY.md` (Nginx on AWS EC2, the current production setup).
