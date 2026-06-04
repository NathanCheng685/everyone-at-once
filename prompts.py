"""Build system + user prompts for the persona simulator (multi-IP)."""
from ip_loader import load_characters, load_questions, questions_by_id

SYSTEM_TEMPLATE_ZH = """\
你正在扮演一个混合人格。这个人格由以下角色按指定权重叠加而成：

{persona_block}

现在你会收到一个日常情境和 3 个选项。请输出一个 JSON 对象 `{{"probs": [p1, p2, p3]}}`，三个浮点数代表该混合人格分别选择三个选项的概率。三者之和必须等于 1。

严格约束（必须遵守）：
- 你的判断**仅**基于人格层面的特质（勇气、控制欲、幽默当盾牌、忠诚、疏离、完美主义等）。
- **禁止**根据职业、领域名词、作品名、专业术语、标志性道具等表面身份线索来匹配选项。如果你发现自己想说"这个选项提到了 X，所以一定是 Y 角色"——立刻停下，重新去看选项背后的**人格反应方式**。
- 只输出 JSON。不要任何解释、不要前言后语、不要 markdown 包裹。"""

SYSTEM_TEMPLATE_EN = """\
You are roleplaying a blended persona, a weighted mixture of the following characters:

{persona_block}

You will be given an everyday scenario and 3 response options. Output a JSON object `{{"probs": [p1, p2, p3]}}` — three floats representing the probability that this blended persona would pick each option respectively. The three values MUST sum to 1.

STRICT CONSTRAINTS (must follow):
- Decide ONLY based on personality-level traits (courage, control, humor-as-shield, loyalty, detachment, perfectionism, etc.).
- DO NOT match options based on profession, domain terms, work titles, franchise jargon, or iconic props. If you catch yourself thinking "this option mentions X, so it must be character Y" — stop, and re-read the option for the underlying **personality response pattern**.
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


def build_system_prompt(theta, lang, ip_id="friends", characters=None):
    characters = characters or load_characters(ip_id)
    assert len(theta) == 6
    assert lang in ("zh", "en")
    name_key = f"name_{lang}"
    persona_key = f"persona_{lang}"
    sep = "：" if lang == "zh" else ": "

    lines = []
    for ch, w in zip(characters, theta):
        if w < 1e-6:
            continue
        pct = round(float(w) * 100)
        lines.append(f"- {pct}% — {ch[name_key]}{sep}{ch[persona_key]}")
    persona_block = "\n".join(lines)
    template = SYSTEM_TEMPLATE_ZH if lang == "zh" else SYSTEM_TEMPLATE_EN
    return template.format(persona_block=persona_block)


def build_user_prompt(question_id, lang, ip_id="friends", questions_map=None):
    qmap = questions_map or questions_by_id(ip_id)
    q = qmap[question_id]
    scenario = q[f"scenario_{lang}"]
    opts = q[f"options_{lang}"]
    assert len(opts) == 3
    template = USER_TEMPLATE_ZH if lang == "zh" else USER_TEMPLATE_EN
    return template.format(scenario=scenario, opt1=opts[0], opt2=opts[1], opt3=opts[2])
