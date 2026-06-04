"""One-off generator for HP / Avengers / Naruto questions.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEMS = [
    (1, "周五傍晚刚下班，最想做的是？", "It's Friday at 6pm, you just finished work — what do you most want to do?"),
    (2, "最好的朋友凌晨两点哭着打电话来，说刚被分手。你的第一反应是？", "Your closest friend calls you at 2am, crying — they just got dumped. What's your first move?"),
    (3, "会议上你的方案被领导当众说\"逻辑不通\"，你的反应是？", "In a meeting, your boss publicly says your proposal 'doesn't make logical sense.' Your reaction?"),
    (4, "你突然收到一笔 5 万块的意外奖金，第一反应是？", "An unexpected bonus drops into your account. What's your gut move?"),
    (5, "第一次约会，你倾向于怎么安排？", "First date — how do you want to set it up?"),
    (6, "室友把你冰箱里准备明天招待客人的食材提前吃掉了。你的反应是？", "Your roommate ate the food you were saving in the fridge for tomorrow's guests. Your reaction?"),
    (7, "派对上你被介绍给一个看起来很有趣的陌生人，你的开场是？", "At a party, you get introduced to someone who looks interesting. Your opener?"),
    (8, "最好的朋友突然出大事，半夜来找你帮忙。你的第一反应是？", "Your best friend hits a sudden crisis and shows up at your door at midnight. First move?"),
    (9, "你最讨厌的人意外升职了。你心里的第一反应是？", "Someone you can't stand just got promoted. Your first internal reaction?"),
    (10, "想象十年后的自己，你最希望的画面是？", "Picture yourself ten years from now — what's the version you most hope for?"),
    (11, "凌晨三点你毫无征兆地醒了，再也睡不着。你最可能做什么？", "It's 3am and you're suddenly wide awake. Most likely move?"),
    (12, "朋友做了件不光彩的小事，求你在被问到时帮对方圆一下。你的反应是？", "A friend did something slightly off and asks you to cover for them if asked. Your reaction?"),
]

OPTS = {
    "harry-potter": [
        (["独自去能出汗的地方把这周憋着的火发泄掉", "打开笔记本，把对方说的每一点逐条写下反驳提纲", "立刻打车过去，先骂那个伤害朋友的人一顿再谈别的"],
         ["Find somewhere you can sweat out the anger you've been carrying all week", "Open your notes and write a point-by-point rebuttal outline", "Get in a car right now — yell at whoever hurt them before anything else"]),
        (["在电话里沉默很久，然后说我在，明天一早到你家", "先问清时间线、证据、谁说了什么，再列接下来 48 小时要做的事", "讲一个特别烂的冷笑话，逼对方笑一下，再订早餐外卖"],
         ["Stay on the line in silence, then say I'm here — at your door first thing", "Ask for timeline and who's involved — list the next 48 hours", "Tell an awful joke for one laugh, then order breakfast"]),
        (["当场开始逐条辩护，哪怕会议室已经尴尬到极点", "表面点头，心里记下下次汇报前多准备三套数据", "冷笑一声，之后再也不在这个人面前暴露真实想法"],
         ["Defend point by point right there — even when the room is painful", "Nod on the surface, note to bring three backup data sets next time", "One cold laugh, then never show this person your real thinking"]),
        (["大半存起来，留一小部分请最铁的两个人吃顿好的", "立刻做表格：还债、储蓄、学习基金各占多少", "先给最需要的人转一笔，再给自己买一样一直舍不得的东西"],
         ["Put most away, small slice for your two closest people", "Spreadsheet: debt, savings, learning fund — fixed percentages", "Transfer to whoever needs it most, then one thing you've denied yourself"]),
        (["选能认真说话的地方，看对方愿不愿意听你把话说完", "轻松的小馆子，边吃边观察对方会不会照顾你的节奏", "去一个有点奇怪、人少的地方，发生什么算什么"],
         ["Somewhere you can actually talk — see if they'll listen until you finish", "Casual spot — watch whether they match your pace", "Some odd quiet place — whatever happens, happens"]),
        (["嘴上说没事，心里把冰箱分层贴条，并记下这次", "当场讽刺一句，然后要求对方明天补一份回来", "平静问一句为什么，再一起定共享区规则"],
         ["Say it's fine, label fridge zones, file the incident", "One sarcastic line, demand they replace it tomorrow", "Ask calmly why, then co-write shared-zone rules"]),
        (["问对方最近在读什么，然后认真听完全部", "把对方拉去认识你最熟的那一圈人", "轻声说，你有没有觉得有些人其实一直在看着我们"],
         ["Ask what they've been reading — listen to all of it", "Drag them to introduce them to your inner circle", "Softly: do you feel some people have been watching us"]),
        (["让对方今晚就睡你家沙发，你先扛明天要打的电话", "一起把局面画在纸上，标出谁能帮、下一步是什么", "只说我见过更糟的你会走出来，然后泡一杯热的"],
         ["Couch tonight — you'll make the hard calls tomorrow", "Map on paper — who can help, step one", "I've seen worse — you'll walk out, and something hot"]),
        (["当晚就整理材料，准备把标准是否一致问清楚", "耸肩，他的路他的，我今晚照样看球", "觉得也许对方有你看不见的苦，先不浪费情绪"],
         ["Gather material that night to ask if standards were consistent", "Shrug — their path, my game tonight", "Maybe they carry something you never saw — don't spend emotion"]),
        (["终于不再被过去追着跑，身边有敢托付的人", "成为那个想都不用想就知道该怎么做的人", "还能开玩笑，但玩笑里不再有刺"],
         ["Not chased by the past, with people you can trust", "Someone who knows what to do without thinking", "Still joking, but jokes no longer have barbs"]),
        (["起来把一直没敢回的消息写完", "重排书架、列明天清单，用秩序换安心", "泡热饮、放老歌，等身体自己再睡过去"],
         ["Send the messages you've been avoiding", "Re-shelve, time-block tomorrow — order for calm", "Hot drink, old music, let sleep return"]),
        (["拒绝撒谎，但陪对方想一个不伤害第三方的说法", "可以帮圆，但对方得先承认自己做错了什么", "不帮圆谎，愿意陪对方去面对后果"],
         ["Refuse to lie, help words that don't harm a third party", "Cover only if they admit exactly what they did", "Won't cover — stand beside them through consequences"]),
    ],
    "avengers": [
        (["回工作室把那个一直卡住的点子做完", "五公里跑或体能训练，把纪律感拉回来", "叫上最信的几个人，去能大声说话的地方喝一杯"],
         ["Back to the studio and finish the stuck idea", "Five-k or training — pull discipline back", "The few you trust, somewhere you can talk loud"]),
        (["先远程把对方今晚需要的资源都安排好，再出现", "问清事实链，给出三步可执行方案", "人到了再说，先确保对方不是一个人"],
         ["Arrange resources tonight remotely, then show up", "Clarify facts, hand a three-step plan", "Just get there — they're not alone"]),
        (["当场用数据和类比把逻辑补完，语气可以硬", "记下反驳点，会后再用更冷静的方式提交", "表面不动，内心把这个人从可合作名单划掉"],
         ["Rebuild logic with data on the spot — tone can be hard", "Log counterpoints, submit calmer version later", "Still on surface, strike them from collaborate list"]),
        (["一半投进能放大影响力的项目，一半给团队", "先还债和应急金，再按清单买", "请所有人吃一顿，剩下的慢慢规划"],
         ["Half into scaling impact, half to the team", "Debt and emergency fund first, then list", "Feed everyone first, plan the rest"]),
        (["能深聊的安静场所，看对方是否诚实", "轻松场合，用观察判断值不值得第二次", "做点冒险的事，看对方敢不敢一起"],
         ["Quiet enough for depth — watch if they're honest", "Casual — observe whether a second date earns itself", "Something slightly risky — see if they'll go"]),
        (["嘴上说没事，心里升级冰箱协议", "讽刺后要求等价赔偿", "一起定规则，避免下次"],
         ["Say fine, upgrade fridge protocol in your head", "Sarcasm, then demand equivalent replacement", "Co-write rules so there's no next time"]),
        (["用自嘲开场，再认真问对方在做什么", "把对方介绍给最能帮到TA的人", "直接问你最怕的是什么并等答案"],
         ["Self-deprecation, then what they're working on", "Introduce them to whoever could actually help", "Ask what they're most afraid of and wait"]),
        (["接手最难的部分，让对方先睡", "列资源、联系人、时间线", "陪着，不多话，直到对方稳定"],
         ["Take hardest piece so they sleep", "Resources, contacts, timeline", "Stay, few words, until stable"]),
        (["准备质疑流程是否公平", "专注自己的任务，不分配恨意", "想一秒就放下，情绪太贵"],
         ["Question whether the process was fair", "Focus on your mission, don't budget hatred", "One second, drop it — emotions too expensive"]),
        (["影响力用来保护更多人，而不是表演", "有一段不需要盔甲的关系", "身体与意志仍服务于信念"],
         ["Influence to protect people, not perform", "A relationship without armor", "Body and will still serve conviction"]),
        (["处理一个一直拖延的硬问题", "拉伸、呼吸，把失控感压下去", "刷轻松内容直到困"],
         ["Tackle one hard problem you've avoided", "Stretch, breathe, push loss-of-control down", "Light content until sleep"]),
        (["不撒谎，帮想最小伤害的表述", "可以挡一句，但下次对方要还人情", "拒绝，陪对方去面对"],
         ["No lying — least-harm wording", "One shield sentence, they owe you next time", "Refuse — accompany through facing it"]),
    ],
    "naruto": [
        (["去训练场一个人练到力竭", "回家把笔记整理完，再给自己做顿热的", "约同伴吃拉面，把这周的事大声讲一遍"],
         ["Training ground alone until empty", "Home — finish notes, cook something warm", "Ramen with the crew — tell the week out loud"]),
        (["立刻说我在哪见你，人先到", "问清发生了什么，一起想明天第一步", "先逗对方笑，再认真听"],
         ["Where do I meet you — body first", "What happened — tomorrow's first step together", "One laugh, then actually listen"]),
        (["当场反驳，哪怕声音会变大", "记下问题，回去查资料再回应", "沉默，之后少在这人面前开口"],
         ["Push back even if your voice rises", "Note issues, research, respond later", "Go quiet — speak less around them after"]),
        (["请同伴吃饭，剩下的存起来", "列计划：训练、家用、应急", "给最亲的人，再给自己一点奖励"],
         ["Feed companions, save the rest", "Plan: training, household, emergency", "Closest people first, small reward for self"]),
        (["选能并肩走路聊很久的路", "简单见面，看自然不自然", "去对方没去过的店，一起闯一下"],
         ["Long walk side by side", "Simple meetup — see if natural", "Place they've never been — explore"]),
        (["说没事，但心里记一笔", "直接表达不满，要对方补上", "轻声说明天很重要，请尊重"],
         ["Say fine, but remember", "Not fine — they replace it", "Tomorrow matters — please respect that"]),
        (["大声打招呼，问对方最近在努力什么", "把对方介绍给可靠的人", "害羞地笑一下，认真听对方说"],
         ["Loud hello — what they've been working on", "Introduce to someone reliable", "Shy smile, listen seriously"]),
        (["说今晚我守着你", "一起想谁能帮忙、怎么做", "不多话，递水，陪着"],
         ["Tonight I stay with you", "Who can help and how", "Few words, water, stay"]),
        (["想证明自己也能做到，训练量加倍", "算了，专注自己的路", "有点酸，但把情绪咽下去继续走"],
         ["Prove you can too — double training", "Let it go — your path", "A sting, swallow it, keep walking"]),
        (["被所有人认可，还能保护同伴", "亲手了结心结，不再逃", "成为别人依靠的强者"],
         ["Recognized, still protecting your people", "Settle the heart, stop running", "The dependable one others lean on"]),
        (["起来练基础动作直到累", "看卷轴或书，心里安静一点", "泡面加老动画，等困意"],
         ["Basics until exhaustion", "Scrolls or books until quiet", "Noodles and old shows until sleep"]),
        (["不帮撒谎，但陪对方去说清楚", "帮一次，下不为例", "摇头，一起想不撒谎的办法"],
         ["Won't lie — help them tell truth", "Cover once, never again", "Find a way without lying"]),
    ],
}

for ip, opts in OPTS.items():
    qs = []
    for (sid, sz, se), (zh3, en3) in zip(STEMS, opts):
        qs.append({
            "id": sid,
            "scenario_zh": sz,
            "scenario_en": se,
            "options_zh": zh3,
            "options_en": en3,
        })
    path = ROOT / "ips" / ip / "questions.json"
    path.write_text(json.dumps({"questions": qs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", path)
