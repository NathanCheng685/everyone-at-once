"""LLM-as-simulator for friends-sbi.

Calls a local Ollama instance (e.g., qwen2.5:14b-instruct-q4_K_M on the LAN ROG box)
through the OpenAI-compatible /v1/chat/completions endpoint.

Returns a numpy array of shape (3,) — the categorical probability over the 3 options
of a single question, given a Dirichlet-mixed persona θ ∈ Δ^5 (6-simplex).
"""
import json
import time

import numpy as np
import openai
from openai import OpenAI

from config import SIMULATOR_BASE_URL, SIMULATOR_MODEL
from prompts import build_system_prompt, build_user_prompt


class SimulatorError(Exception):
    """Raised when the simulator fails after retries."""


# Per-request timeout so a hung socket fails fast (seconds) instead of stalling
# for hours; we drive our own retry/backoff below, so disable the SDK's.
client = OpenAI(base_url=SIMULATOR_BASE_URL, api_key="ollama",
                timeout=90.0, max_retries=0)

# Transient network/server conditions worth retrying with backoff.
RETRYABLE_NET = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
    openai.RateLimitError,
)
MAX_RETRIES = 4


def _parse_probs(content):
    obj = json.loads(content)
    probs = obj["probs"]
    if not isinstance(probs, list) or len(probs) != 3:
        raise ValueError(f"`probs` must be a 3-element list, got {probs!r}")
    p = np.asarray(probs, dtype=float)
    if not np.all(np.isfinite(p)):
        raise ValueError(f"probs contains non-finite values: {p}")
    if not np.all(p >= 0):
        raise ValueError(f"probs must be non-negative, got {p}")
    s = float(p.sum())
    if s <= 0:
        raise ValueError(f"probs sum is non-positive: {s}")
    if abs(s - 1.0) > 0.05:
        raise ValueError(f"probs deviates from sum=1 by >0.05: sum={s}, probs={p}")
    return p / s  # renormalize to be exactly on the simplex


def simulate(theta, question_id, lang, ip_id="friends", _retry=0):
    """One simulator call. Returns numpy array shape (3,).

    Retries up to MAX_RETRIES on both parse/shape errors and transient network
    errors (the latter with exponential backoff). Final failure raises
    SimulatorError with context (θ / q / lang / underlying error).
    """
    try:
        resp = client.chat.completions.create(
            model=SIMULATOR_MODEL,
            messages=[
                {"role": "system", "content": build_system_prompt(theta, lang, ip_id)},
                {"role": "user",   "content": build_user_prompt(question_id, lang, ip_id)},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
            max_tokens=128,
        )
        content = resp.choices[0].message.content
        return _parse_probs(content)
    except RETRYABLE_NET as e:
        if _retry < MAX_RETRIES:
            time.sleep(min(2 ** _retry, 15))  # backoff: 1,2,4,8,15s
            return simulate(theta, question_id, lang, ip_id, _retry + 1)
        raise SimulatorError(
            f"network failure after {MAX_RETRIES} retries: ip={ip_id}, q={question_id}, "
            f"lang={lang}, err={type(e).__name__}: {e}"
        ) from e
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        if _retry < MAX_RETRIES:
            return simulate(theta, question_id, lang, ip_id, _retry + 1)
        raise SimulatorError(
            f"parse failure after {MAX_RETRIES} retries: ip={ip_id}, q={question_id}, "
            f"lang={lang}, err={e}"
        ) from e
