# -*- coding: utf-8 -*-
"""
法语学习内容种子数据（V0）

说明：
- 这是 V0 的演示内容库，字段严格对齐 PRD 4.2 节 flashcards / lessons / levels 表 DDL。
- 内容取向"地道法语"：优先真实口语高频表达，标注语域（familier/courant/formel）与常见误用。
- tags 用于标签筛选；语域以 tag 形式承载（PRD DDL 没有独立的 register 字段，不擅自加列）。
- is_sensitive=True 的卡片为脏话/冒犯性表达，仅在用户 sensitive_opt_in=True 时下发。

后续接入后台管理后，这些内容由 /api/admin/flashcards 录入，此文件仅作为种子与离线演示数据。
"""

LEVELS = [
    {"code": "A1", "name": "A1 - 入门级", "description": "掌握基础日常用语，能进行简单的自我介绍", "sort_order": 1},
    {"code": "A2", "name": "A2 - 初级", "description": "能理解日常生活中的基本对话和简单文本", "sort_order": 2},
    {"code": "B1", "name": "B1 - 中级", "description": "能在大多数旅行场景中应对，能描述经历和事件", "sort_order": 3},
    {"code": "B2", "name": "B2 - 中高级", "description": "能理解复杂文章的核心观点，能流利地进行交流", "sort_order": 4},
]

# lesson_type: vocabulary | grammar | listening | speaking | culture （对齐 PRD DDL 枚举）
LESSONS = [
    {
        "key": "a1-greetings",
        "level_code": "A1",
        "title": "Salutations — 地道问候与开场",
        "description": "法国人每天真正会说的问候语，含教科书不教的口语版本",
        "lesson_type": "vocabulary",
        "sort_order": 1,
        "status": "published",
    },
    {
        "key": "a1-cafe",
        "level_code": "A1",
        "title": "Au café — 咖啡馆点单",
        "description": "走进巴黎咖啡馆，从点单到买单的完整表达",
        "lesson_type": "vocabulary",
        "sort_order": 2,
        "status": "published",
    },
    {
        "key": "a1-shopping",
        "level_code": "A1",
        "title": "Faire les courses — 购物与市场",
        "description": "集市、面包店、便利店里的高频对话",
        "lesson_type": "vocabulary",
        "sort_order": 3,
        "status": "published",
    },
    {
        "key": "a1-slang",
        "level_code": "A1",
        "title": "Expressions orales — 法国人挂在嘴边的小词",
        "description": "让法语听起来“像法语”的口头禅与语气词（含敏感词，需手动开启）",
        "lesson_type": "vocabulary",
        "sort_order": 4,
        "status": "published",
    },
    {
        "key": "a2-daily",
        "level_code": "A2",
        "title": "La vie quotidienne — 日常生活",
        "description": "租房、就医、出行场景常用表达（V0 示例课时）",
        "lesson_type": "vocabulary",
        "sort_order": 1,
        "status": "draft",  # V0 演示：草稿态，小程序端不展示，用于验证"0 课时/灰显"分支
    },
]

# 字段: front_text, back_text, example_sentence, example_translation,
#       difficulty('A1'|'A2'|'B1'|'B2' CEFR 等级), tags(list), is_sensitive(bool), sort_order
FLASHCARDS = {
    "a1-greetings": [
        {
            "front_text": "Bonjour",
            "back_text": "你好 / 早上好（白天通用，最安全、最正式的问候）",
            "example_sentence": "Bonjour madame, je voudrais un café, s'il vous plaît.",
            "example_translation": "您好女士，我想要一杯咖啡。",
            "difficulty": "A1", "tags": ["问候", "courant"], "is_sensitive": False,
            "tip": "对陌生人和长辈一律用 Bonjour，永远不出错。注意别用它道别——那是 Au revoir。",
        },
        {
            "front_text": "Salut",
            "back_text": "嗨 / 拜拜（朋友、同龄人之间；既能打招呼也能道别）",
            "example_sentence": "Salut ! Ça fait longtemps !",
            "example_translation": "嘿！好久不见！",
            "difficulty": "A1", "tags": ["问候", "familier", "口语"], "is_sensitive": False,
            "tip": "对老板、店员、陌生人别用 Salut。它同时是 hello 和 bye，看语境。",
        },
        {
            "front_text": "Ça va ?",
            "back_text": "最近咋样？/ 你好吗（法国人最常用的寒暄，不是真的问病情）",
            "example_sentence": "— Salut, ça va ? — Ça va bien, et toi ?",
            "example_translation": "— 嘿，最近怎么样？— 挺好的，你呢？",
            "difficulty": "A1", "tags": ["问候", "courant", "口语"], "is_sensitive": False,
            "tip": "教科书教你 Comment allez-vous ? 但法国人日常几乎只说 Ça va ? 前者只在很正式场合出现。",
        },
        {
            "front_text": "Enchanté(e)",
            "back_text": "很高兴认识您（初次见面；男士说 enchanté，女士说 enchantée）",
            "example_sentence": "Bonjour, je m'appelle Léa. — Enchanté, moi c'est Thomas.",
            "example_translation": "你好，我叫 Léa。—— 幸会，我是 Thomas。",
            "difficulty": "A2", "tags": ["问候", "formel"], "is_sensitive": False,
            "tip": "书面要按性别加 -e，口语里男女发音几乎一样。握手是标准动作，贴面礼留给熟人。",
        },
        {
            "front_text": "Bonne journée",
            "back_text": "祝你一天愉快（离开商店、结束对话时的标准收尾）",
            "example_sentence": "Merci beaucoup, bonne journée !",
            "example_translation": "非常感谢，祝您一天愉快！",
            "difficulty": "A1", "tags": ["问候", "courant"], "is_sensitive": False,
            "tip": "法国人结账、挂电话、进电梯都会说一句。不说会显得生硬；晚上换 Bonne soirée。",
        },
        {
            "front_text": "À plus (tard)",
            "back_text": "回头见 / 待会儿见（口语缩写，完整形式是 À plus tard）",
            "example_sentence": "Bon, je dois y aller. À plus !",
            "example_translation": "好啦，我得走了。回头见！",
            "difficulty": "A2", "tags": ["道别", "familier", "口语"], "is_sensitive": False,
            "tip": "年轻人打字常写成 A+。正式场合用 Au revoir 或 À bientôt。",
        },
        {
            "front_text": "De rien",
            "back_text": "不客气（回应对感谢；更口语还能说 Il n'y a pas de quoi）",
            "example_sentence": "— Merci pour ton aide. — De rien !",
            "example_translation": "— 谢谢你的帮忙。—— 不客气！",
            "difficulty": "A1", "tags": ["礼貌", "courant"], "is_sensitive": False,
            "tip": "别用 Pas de problème 回应感谢（那是“没问题”，语义偏移），de rien 最稳。",
        },
        {
            "front_text": "S'il vous plaît",
            "back_text": "请 / 麻烦您（vous 敬称；对朋友用 s'il te plaît）",
            "example_sentence": "Un café au lait, s'il vous plaît.",
            "example_translation": "请给我一杯拿铁。",
            "difficulty": "A1", "tags": ["礼貌", "courant"], "is_sensitive": False,
            "tip": "法语里“请”几乎不可省略。少了它，点单听起来像命令句。",
        },
        {
            "front_text": "Comment tu vas ?",
            "back_text": "你好吗（朋友间；对长辈/陌生人用 Comment vous allez ?）",
            "example_sentence": "Comment tu vas ? Ça fait longtemps qu'on s'est pas vus !",
            "example_translation": "你怎么样？咱们好久没见了！",
            "difficulty": "A2", "tags": ["问候", "courant"], "is_sensitive": False,
            "tip": "严格来说这是“你身体好吗”，熟人之间 == 寒暄；对刚认识的人问这个会显得过度关心。",
        },
        {
            "front_text": "À bientôt",
            "back_text": "回头见 / 很快再见（比 Au revoir 更轻，暗示近期会再见）",
            "example_sentence": "On se voit jeudi ? — Oui, à bientôt !",
            "example_translation": "周四见？—— 好，回头见！",
            "difficulty": "A2", "tags": ["道别", "courant"], "is_sensitive": False,
            "tip": "和 À plus 的区别：À bientôt 通用、礼貌；À plus 偏朋友、偏口语。",
        },
    ],
    "a1-cafe": [
        {
            "front_text": "Je voudrais...",
            "back_text": "我想要……（点单万能句，礼貌程度刚好）",
            "example_sentence": "Je voudrais un café allongé, s'il vous plaît.",
            "example_translation": "我想要一杯美式（加长浓缩），谢谢。",
            "difficulty": "A2", "tags": ["点单", "courant"], "is_sensitive": False,
            "tip": "别用 Je veux（我要）——听起来像小孩提要求。Je voudrais 是条件式，天然礼貌。",
        },
        {
            "front_text": "Un café, s'il vous plaît",
            "back_text": "一杯咖啡（在法国默认是一小杯浓缩 espresso）",
            "example_sentence": "Bonjour, un café s'il vous plaît.",
            "example_translation": "你好，来一杯咖啡。",
            "difficulty": "A1", "tags": ["点单", "courant"], "is_sensitive": False,
            "tip": "想喝美式要专门说 un allongé 或 un café américain；说 un café 上来的会是小小一杯。",
        },
        {
            "front_text": "L'addition, s'il vous plaît",
            "back_text": "买单（法餐没有“服务员主动送账单”的习惯，必须自己要）",
            "example_sentence": "L'addition, s'il vous plaît. On peut payer par carte ?",
            "example_translation": "麻烦买单。可以刷卡吗？",
            "difficulty": "A2", "tags": ["点单", "餐厅", "courant"], "is_sensitive": False,
            "tip": "法国餐厅不会主动给你账单——那是怕赶客。坐着等账单只会等到天荒地老。",
        },
        {
            "front_text": "À emporter",
            "back_text": "外带（反义：sur place 堂食）",
            "example_sentence": "C'est à emporter ou sur place ? — À emporter, merci.",
            "example_translation": "外带还是堂食？—— 外带，谢谢。",
            "difficulty": "A2", "tags": ["点单", "courant"], "is_sensitive": False,
            "tip": "同一杯咖啡堂食和外带价格可能不同（法国常见），点单时会先问你这句。",
        },
        {
            "front_text": "Sur place",
            "back_text": "堂食 / 在这儿吃",
            "example_sentence": "Sur place, s'il vous plaît.",
            "example_translation": "在这吃，谢谢。",
            "difficulty": "A2", "tags": ["点单", "courant"], "is_sensitive": False,
            "tip": "和 à emporter 成对出现，店员提问时只回其中一个词就够了。",
        },
        {
            "front_text": "Je peux avoir... ?",
            "back_text": "我能要……吗？（比 Je voudrais 更口语自然的请求方式）",
            "example_sentence": "Je peux avoir un verre d'eau, s'il vous plaît ?",
            "example_translation": "能给我一杯水吗？",
            "difficulty": "A2", "tags": ["点单", "courant", "口语"], "is_sensitive": False,
            "tip": "法国自来水免费，直接说 un verre d'eau 或 une carafe d'eau 就行，不必买瓶装。",
        },
        {
            "front_text": "C'est délicieux",
            "back_text": "太好吃了（夸食物；也可说 C'est très bon）",
            "example_sentence": "Ce croissant est vraiment délicieux !",
            "example_translation": "这个牛角包真好吃！",
            "difficulty": "A2", "tags": ["餐厅", "courant"], "is_sensitive": False,
            "tip": "别用 C'est très délicieux——délicieux 本身已含程度，再加 très 显得堆砌。",
        },
        {
            "front_text": "Un croissant",
            "back_text": "牛角包（法语发音 /kʁwa.sɑ̃/，词尾 -nt 不发音）",
            "example_sentence": "Je prends un croissant et un café.",
            "example_translation": "我要一个牛角包和一杯咖啡。",
            "difficulty": "A1", "tags": ["食物", "courant"], "is_sensitive": False,
            "tip": "经典法式早餐就是 café + croissant，价格通常 3-5 欧，站着吧台吃更便宜。",
        },
        {
            "front_text": "Ça vous fera ... euros",
            "back_text": "一共……欧（店员报价格的标准说法）",
            "example_sentence": "Ça vous fera cinq euros cinquante, s'il vous plaît.",
            "example_translation": "一共 5.5 欧，谢谢。",
            "difficulty": "B1", "tags": ["点单", "courant"], "is_sensitive": False,
            "tip": "听到这句就该掏钱了。法语小数点是逗号：5,50 € 读作 cinq euros cinquante。",
        },
        {
            "front_text": "Je regarde, merci",
            "back_text": "我随便看看，谢谢（店员问“需要帮忙吗”时的标准回绝）",
            "example_sentence": "— Je peux vous aider ? — Non merci, je regarde.",
            "example_translation": "— 需要帮忙吗？— 不用谢谢，我随便看看。",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "法国店员主动搭话很常见。只说 Non 会显得冷淡，加一句 je regarde 就自然了。",
        },
    ],
    "a1-shopping": [
        {
            "front_text": "Combien ça coûte ?",
            "back_text": "这个多少钱？（最标准的问价句）",
            "example_sentence": "Excusez-moi, combien ça coûte ?",
            "example_translation": "不好意思，这个多少钱？",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "口语里法国人常缩成 Ça coûte combien ? 或更短的 C'est combien ?",
        },
        {
            "front_text": "C'est trop cher",
            "back_text": "太贵了（法国集市可以讲价吗？——基本不行，这句话更多是感叹）",
            "example_sentence": "Ah, c'est trop cher pour moi.",
            "example_translation": "啊，对我来说太贵了。",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "在法国商店、超市不讲价（跳蚤市场除外）。说这句只是表达“我买不起”。",
        },
        {
            "front_text": "Je vais prendre ça",
            "back_text": "我要这个（决定购买时的自然说法）",
            "example_sentence": "Bon, je vais prendre celui-là.",
            "example_translation": "好，我要那个。",
            "difficulty": "A2", "tags": ["购物", "courant", "口语"], "is_sensitive": False,
            "tip": "比 Je l'achète 更口语。celui-là = 那个（阳性），celle-là = 那个（阴性）。",
        },
        {
            "front_text": "Vous acceptez la carte ?",
            "back_text": "可以刷卡吗？（法国不少小店有最低消费才让刷卡）",
            "example_sentence": "Vous acceptez la carte bancaire ?",
            "example_translation": "你们接受银行卡支付吗？",
            "difficulty": "B1", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "集市摊位和小型面包店常只收现金或设 10 欧起刷。随身带点现金省事。",
        },
        {
            "front_text": "Avez-vous ... ?",
            "back_text": "你们有……吗？（礼貌询问商品有无）",
            "example_sentence": "Bonjour, avez-vous du pain complet ?",
            "example_translation": "你好，你们有全麦面包吗？",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "du/ de la/ des 是部分冠词，表示“一些”。买整个面包用 un pain，买一些用 du pain。",
        },
        {
            "front_text": "Bon marché",
            "back_text": "便宜（形容词短语，不变化）",
            "example_sentence": "Ce fromage est vraiment bon marché.",
            "example_translation": "这个奶酪真便宜。",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "别被字面骗了：bon marché 是一个词，意思是“便宜”，不是“好市场”。",
        },
        {
            "front_text": "Un sac, s'il vous plaît",
            "back_text": "请给我一个袋子",
            "example_sentence": "Vous voulez un sac ? — Oui, un sac s'il vous plaît.",
            "example_translation": "需要袋子吗？—— 要的，麻烦给我一个。",
            "difficulty": "A1", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "法国自 2016 年起禁一次性塑料袋，很多店不再免费提供，带个布袋更地道。",
        },
        {
            "front_text": "Je cherche...",
            "back_text": "我在找……（向店员求助时的开场）",
            "example_sentence": "Je cherche un cadeau pour ma sœur.",
            "example_translation": "我在找我妹妹的礼物。",
            "difficulty": "A2", "tags": ["购物", "courant"], "is_sensitive": False,
            "tip": "chercher 是“寻找”，不是“研究”。想说“我在研究法语”要用 j'étudie。",
        },
    ],
    "a1-slang": [
        {
            "front_text": "Du coup",
            "back_text": "所以 / 结果（法国年轻人最高频的口头禅，几乎每句都塞）",
            "example_sentence": "Il pleuvait, du coup on est restés à la maison.",
            "example_translation": "下雨了，所以我们就待在家里了。",
            "difficulty": "A2", "tags": ["口语", "familier", "连接词"], "is_sensitive": False,
            "tip": "教科书不会教，但法国人一天说几十次。它已经从“结果”虚化成纯连接词，写作中慎用。",
        },
        {
            "front_text": "Trop",
            "back_text": "太……/ 超级（口语副词，相当于 très；不是“太……以至于不能”）",
            "example_sentence": "Ce film est trop bien !",
            "example_translation": "这电影太棒了！",
            "difficulty": "A2", "tags": ["口语", "familier", "程度"], "is_sensitive": False,
            "tip": "书面语里 trop 带负面意味（太多、过头）。口语里 trop bien = 超棒，是纯褒义。",
        },
        {
            "front_text": "Grave",
            "back_text": "超级 / 特别（口语副词；原意是“严重的”）",
            "example_sentence": "C'était grave sympa, ta soirée !",
            "example_translation": "你那个派对超好玩！",
            "difficulty": "B1", "tags": ["口语", "familier", "程度"], "is_sensitive": False,
            "tip": "年轻人爱用：grave bien = 特别好。老年人听着会觉得怪，正式场合别用。",
        },
        {
            "front_text": "Ouais",
            "back_text": "嗯 / 对（oui 的口语发音版，约等于 yeah）",
            "example_sentence": "— On y va ? — Ouais, allez !",
            "example_translation": "— 走吗？— 走啊，来吧！",
            "difficulty": "A1", "tags": ["口语", "familier"], "is_sensitive": False,
            "tip": "朋友间、短信里随便用；面对客户、老师、警察请说 Oui。",
        },
        {
            "front_text": "Bof",
            "back_text": "一般般 / 不太样（语气词，配耸肩动作使用）",
            "example_sentence": "— Ça t'a plu ? — Bof, sans plus.",
            "example_translation": "— 你喜欢吗？— 一般吧，就这样。",
            "difficulty": "A2", "tags": ["口语", "familier", "语气词"], "is_sensitive": False,
            "tip": "法语的灵魂词之一。发音像“啵夫”，配合耸肩（avec les épaules）就是标准法国表情包。",
        },
        {
            "front_text": "Ça marche",
            "back_text": "行 / 就这么定了 / 成交（接受提议时的万能应答）",
            "example_sentence": "— On se retrouve à 20h ? — Ça marche !",
            "example_translation": "— 我们 8 点见？— 行！",
            "difficulty": "A2", "tags": ["口语", "courant"], "is_sensitive": False,
            "tip": "字面是“这行得通”，实际就是 OK。比 D'accord 更随意，比 OK 更法语。",
        },
        {
            "front_text": "Pas de souci",
            "back_text": "没问题 / 别担心（回应感谢或安抚对方）",
            "example_sentence": "— Merci de me déposer. — Pas de souci, à demain !",
            "example_translation": "— 谢谢你送我。—— 没事儿，明天见！",
            "difficulty": "A2", "tags": ["口语", "courant"], "is_sensitive": False,
            "tip": "法语里 souci 是“担忧”，不是英语 sorry。别拿它道歉——道歉用 Pardon / Désolé。",
        },
        {
            "front_text": "Carrément",
            "back_text": "完全 / 绝对（口语强调词，类似“妥妥的”）",
            "example_sentence": "— Tu viens ce soir ? — Carrément !",
            "example_translation": "— 你今晚来吗？— 那必须来！",
            "difficulty": "B1", "tags": ["口语", "familier", "程度"], "is_sensitive": False,
            "tip": "原意“直截了当地”，口语里成了万能加强词。年轻人高频，中年人以上很少用。",
        },
        {
            "front_text": "Merde",
            "back_text": "靠 / 卧槽（最常见的法语脏话，约等于英语 shit）",
            "example_sentence": "Merde, j'ai oublié mon portable.",
            "example_translation": "靠，我忘带手机了。",
            "difficulty": "A2", "tags": ["脏话", "familier", "敏感"], "is_sensitive": True,
            "tip": "街头极常见，但在长辈、老师、正式场合绝对不说。委婉版：Mince ! / Zut !",
        },
        {
            "front_text": "Putain",
            "back_text": "妈的 / 我靠（比 merde 更重的脏话，字面意思非常粗俗）",
            "example_sentence": "Putain, il fait froid aujourd'hui.",
            "example_translation": "我靠，今天真冷。",
            "difficulty": "B1", "tags": ["脏话", "familier", "敏感"], "is_sensitive": True,
            "tip": "字面义极具冒犯性，虽已被大量用作语气词，但在正式场合或与不熟的人说话时绝不能出口。",
        },
        {
            "front_text": "Génial",
            "back_text": "太棒了 / 绝了（万能褒义感叹词）",
            "example_sentence": "On va à la plage demain ? — Génial !",
            "example_translation": "明天去海滩？—— 太棒了！",
            "difficulty": "A1", "tags": ["口语", "courant"], "is_sensitive": False,
            "tip": "发音 /ʒe.njal/，注意是硬 g。比 Super 更强调“令人兴奋”。",
        },
        {
            "front_text": "Allez",
            "back_text": "来吧 / 走吧 / 加油（万能语气词，还能表示“算了、走人了”）",
            "example_sentence": "Allez, on y va !",
            "example_translation": "来吧，我们走！",
            "difficulty": "A2", "tags": ["口语", "courant", "语气词"], "is_sensitive": False,
            "tip": "法语气场词之王：催促、鼓励、告别都能用。体育场上全场喊的就是 Allez !",
        },
    ],
    "a2-daily": [
        {
            "front_text": "Je cherche un appartement",
            "back_text": "我在找房子",
            "example_sentence": "Je cherche un appartement dans le 11e arrondissement.",
            "example_translation": "我在找十一区的一套房。",
            "difficulty": "B1", "tags": ["生活", "courant"], "is_sensitive": False,
            "tip": "巴黎按区号(arrondissement)说位置，不说具体街道。11e 读 onzième。",
        },
    ],
}


def build_seed():
    """把上面的内容组装成 PRD 表结构形状的数据（levels / lessons / flashcards）。"""
    levels, lessons, flashcards = [], [], []
    level_id, lesson_id, card_id = 1, 1, 1

    level_id_map = {}
    for lv in LEVELS:
        row = dict(lv)
        row["id"] = level_id
        row["is_active"] = True
        levels.append(row)
        level_id_map[lv["code"]] = level_id
        level_id += 1

    lesson_id_map = {}
    for ls in LESSONS:
        row = {k: v for k, v in ls.items() if k != "key"}
        row["id"] = lesson_id
        row["level_id"] = level_id_map[ls["level_code"]]
        row["content"] = {"sections": []}
        row["metadata"] = {}
        row["created_by"] = None
        lessons.append(row)
        lesson_id_map[ls["key"]] = lesson_id
        lesson_id += 1

    for key, cards in FLASHCARDS.items():
        for idx, c in enumerate(cards):
            row = dict(c)
            row["id"] = card_id
            row["lesson_id"] = lesson_id_map[key]
            row["front_audio_url"] = None
            row["back_audio_url"] = None
            row["status"] = "published"
            row["sort_order"] = idx + 1
            flashcards.append(row)
            card_id += 1

    return levels, lessons, flashcards
