"""Build system + user prompts for the persona simulator.

One template per language (zh / en); a single `build_*` function selects via `lang`.
The system prompt encodes the keyword-shortcut prohibition (Step-2 protocol).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / "characters.json", encoding="utf-8") as f:
    CHARACTERS = json.load(f)["characters"]

with open(ROOT / "questions.json", encoding="utf-8") as f:
    QUESTIONS = json.load(f)["questions"]

assert len(CHARACTERS) == 6, f"Expected 6 characters, got {len(CHARACTERS)}"
assert len(QUESTIONS) == 12, f"Expected 12 questions, got {len(QUESTIONS)}"

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}


SYSTEM_TEMPLATE_ZH = """\
你正在扮演一个混合人格。这个人格由以下角色按指定权重叠加而成：

{persona_block}

现在你会收到一个日常情境和 3 个选项。请输出一个 JSON 对象 `{{"probs": [p1, p2, p3]}}`，三个浮点数代表该混合人格分别选择三个选项的概率。三者之和必须等于 1。

严格约束（必须遵守）：
- 你的判断**仅**基于人格层面的特质，例如：钻牛角尖式的自我辩护、嗓门大、控制欲爆棚、用幽默当盾牌、感情上直接忠诚、毫无社交滤镜、玄学世界观、戏剧化形象、神经质的自我安慰、对承诺的恐惧、对当下快乐的拥抱。
- **禁止**根据职业、领域名词、作品名、专业术语等表面身份线索来匹配选项。如果你发现自己想说"这个选项提到了 X，所以一定是 Y 角色"——立刻停下，重新去看选项背后的**人格反应方式**。
- 只输出 JSON。不要任何解释、不要前言后语、不要 markdown 包裹。"""


SYSTEM_TEMPLATE_EN = """\
You are roleplaying a blended persona, a weighted mixture of the following characters:

{persona_block}

You will be given an everyday scenario and 3 response options. Output a JSON object `{{"probs": [p1, p2, p3]}}` — three floats representing the probability that this blended persona would pick each option respectively. The three values MUST sum to 1.

STRICT CONSTRAINTS (must follow):
- Decide ONLY based on personality-level traits, such as: looping self-justification, loud volume, control-freak energy, humor-as-shield, blunt loyalty, no social filter, mystical worldview, dramatic flair, neurotic self-soothing, commitment phobia, present-moment hedonism.
- DO NOT match options based on profession, domain terms, work titles, or jargon. If you catch yourself thinking "this option mentions X, so it must be character Y" — stop, and re-read the option for the underlying **personality response pattern**.
- Output ONLY the JSON. No prose, no preamble, no markdown fences, no explanation."""


USER_TEMPLATE_ZH = """\
情境：{scenario}

选项：
1. {opt1}
2. {opt2}
3. {opt3}

输出 JSON：{{"probs": [p1, p2, p3]}}"""


USER_TEMPLATE_EN = """\
Scenario: {scenario}

Options:
1. {opt1}
2. {opt2}
3. {opt3}

Return JSON: {{"probs": [p1, p2, p3]}}"""


def build_system_prompt(theta, lang):
    """theta: list/array of 6 floats on the 6-character simplex. lang: 'zh' | 'en'."""
    assert len(theta) == 6, f"theta must have length 6, got {len(theta)}"
    assert lang in ("zh", "en"), f"lang must be zh or en, got {lang}"
    name_key = f"name_{lang}"
    persona_key = f"persona_{lang}"
    sep = "：" if lang == "zh" else ": "

    lines = []
    for ch, w in zip(CHARACTERS, theta):
        if w < 1e-6:
            continue
        pct = round(float(w) * 100)
        lines.append(f"- {pct}% — {ch[name_key]}{sep}{ch[persona_key]}")
    persona_block = "\n".join(lines)
    template = SYSTEM_TEMPLATE_ZH if lang == "zh" else SYSTEM_TEMPLATE_EN
    return template.format(persona_block=persona_block)


def build_user_prompt(question_id, lang):
    q = QUESTIONS_BY_ID[question_id]
    scenario = q[f"scenario_{lang}"]
    opts = q[f"options_{lang}"]
    assert len(opts) == 3, f"q{question_id} {lang} must have 3 options, got {len(opts)}"
    template = USER_TEMPLATE_ZH if lang == "zh" else USER_TEMPLATE_EN
    return template.format(scenario=scenario, opt1=opts[0], opt2=opts[1], opt3=opts[2])
