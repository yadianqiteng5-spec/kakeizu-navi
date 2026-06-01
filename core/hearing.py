# -*- coding: utf-8 -*-
"""
対話ヒアリング・モジュール

アプリが1問ずつ質問し、ユーザーが音声/テキスト/選択で答える。
集めた回答から家系図（persons/relationships）を機械的に組み立てるため、
AI抽出に依存せず確実に動作する（Geminiは音声文字起こしと最終診断のみに使用）。

公開関数:
  build_question_list(answers) -> list[dict]   回答に応じた質問リストを動的生成
  assemble(answers)            -> dict          回答から {persons, relationships} を構築
"""
from typing import List, Dict


def _yn(answers, key) -> bool:
    return answers.get(key) == "はい"


def _int(answers, key, default=0) -> int:
    v = answers.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def build_question_list(answers: Dict) -> List[Dict]:
    """これまでの回答 answers をもとに、出すべき質問を順番に並べて返す。
    回答が増えるとリストも伸びる（純粋関数なので冪等）。"""
    q: List[Dict] = []

    # ── 被相続人 ──
    q.append({"key": "d_name", "type": "text",
              "q": "まず、亡くなった方（被相続人）のお名前を教えてください。",
              "placeholder": "例：山田 太郎"})
    q.append({"key": "d_gender", "type": "choice", "options": ["男性", "女性"],
              "q": "その方の性別は？"})
    q.append({"key": "d_birth", "type": "text", "optional": True,
              "q": "生まれた年（西暦）は？　分からなければ空欄のままでOKです。",
              "placeholder": "例：1945"})

    # ── 配偶者 ──
    q.append({"key": "has_spouse", "type": "choice", "options": ["はい", "いいえ"],
              "q": "配偶者（夫または妻）はいますか？"})
    if _yn(answers, "has_spouse"):
        q.append({"key": "spouse_name", "type": "text",
                  "q": "配偶者のお名前を教えてください。", "placeholder": "例：山田 花子"})
        q.append({"key": "spouse_alive", "type": "choice", "options": ["健在", "すでに死亡"],
                  "q": "配偶者はご健在ですか？"})

    # ── 子 ──
    q.append({"key": "num_children", "type": "number", "min": 0, "max": 15,
              "q": "お子さんは何人いますか？（実子・養子を含みます）",
              "help": "いない場合は 0 を選んでください。"})
    n_child = _int(answers, "num_children")
    for i in range(n_child):
        q.append({"key": f"child_{i}_name", "type": "text",
                  "q": f"{i + 1}人目のお子さんのお名前は？", "placeholder": "例：山田 一郎"})
        q.append({"key": f"child_{i}_alive", "type": "choice", "options": ["健在", "すでに死亡"],
                  "q": f"{answers.get(f'child_{i}_name', f'{i + 1}人目のお子さん')} は、ご健在ですか？"})
        if answers.get(f"child_{i}_alive") == "すでに死亡":
            q.append({"key": f"child_{i}_gc", "type": "number", "min": 0, "max": 15,
                      "q": f"{answers.get(f'child_{i}_name', 'そのお子さん')} に、お子さん（被相続人から見て孫）はいますか？何人ですか？",
                      "help": "代襲相続の判定に使います。いなければ 0。"})
            for j in range(_int(answers, f"child_{i}_gc")):
                q.append({"key": f"child_{i}_gc_{j}_name", "type": "text",
                          "q": f"そのお孫さん（{j + 1}人目）のお名前は？", "placeholder": "例：山田 孫太"})

    # ── 子がいない場合：両親 ──
    if n_child == 0:
        q.append({"key": "father_alive", "type": "choice", "options": ["健在", "すでに死亡・いない"],
                  "q": "被相続人のお父様はご健在ですか？"})
        q.append({"key": "mother_alive", "type": "choice", "options": ["健在", "すでに死亡・いない"],
                  "q": "被相続人のお母様はご健在ですか？"})

        parents_alive = (answers.get("father_alive") == "健在") or (answers.get("mother_alive") == "健在")
        # 両親とも健在でない場合のみ兄弟姉妹を聞く（親がいれば兄弟は相続しないため）
        if answers.get("father_alive") and answers.get("mother_alive") and not parents_alive:
            q.append({"key": "num_siblings", "type": "number", "min": 0, "max": 15,
                      "q": "ご兄弟姉妹は何人いますか？",
                      "help": "被相続人の兄弟姉妹の人数。いなければ 0。"})
            for k in range(_int(answers, "num_siblings")):
                q.append({"key": f"sib_{k}_name", "type": "text",
                          "q": f"{k + 1}人目のご兄弟姉妹のお名前は？", "placeholder": "例：山田 次郎"})

    # ── 資産 ──
    q.append({"key": "asset_home", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
              "q": "ご自宅などの不動産の評価額は、だいたいいくらですか？（万円）",
              "help": "固定資産税の評価額や購入価格などの目安でOK。分からなければ 0。"})
    q.append({"key": "asset_cash", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
              "q": "預貯金の合計は、およそいくらですか？（万円）"})
    q.append({"key": "asset_sec", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
              "q": "株式・投資信託などの有価証券は、およそいくらですか？（万円）"})
    q.append({"key": "asset_other", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
              "q": "その他の資産（自動車・貴金属など）は、およそいくらですか？（万円）"})

    # ── 事業・保険 ──
    q.append({"key": "has_shares", "type": "choice", "options": ["はい", "いいえ"],
              "q": "自社株や非上場会社の株式をお持ちでしたか？（事業承継の判定に使います）"})
    if _yn(answers, "has_shares"):
        q.append({"key": "shares_value", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
                  "q": "その株式の評価額は、だいたいいくらですか？（万円）"})
    q.append({"key": "insurance", "type": "number", "min": 0, "max": 1000000, "unit": "万円",
              "q": "死亡保険金は、およそいくらですか？（万円・なければ 0）"})

    # ── 特別な事情（任意・自由記述） ──
    q.append({"key": "special", "type": "text", "optional": True, "multiline": True,
              "q": "最後に、養子・相続放棄・生前贈与など、特別な事情があれば教えてください。",
              "placeholder": "例：長男を養子に出した／次女が相続放棄した　など。なければ空欄でOK"})

    return q


def _gender(answers, key) -> str:
    return "female" if answers.get(key) == "女性" else "male"


def assemble(answers: Dict) -> Dict:
    """回答から {persons, relationships} を構築する。金額は万円→円に変換。"""
    persons: List[Dict] = []
    rels: List[Dict] = []
    counter = {"n": 0}

    def new_id() -> str:
        counter["n"] += 1
        return f"p{counter['n']}"

    def add(name, gender="unknown", birth=None, alive=True, prop=False,
            assets=0, shares=False, renounced=False, notes=""):
        pid = new_id()
        persons.append({
            "id": pid, "name": name or "不明", "gender": gender,
            "birth_year": birth, "is_alive": alive, "is_propositus": prop,
            "assets_yen": int(assets), "has_business_shares": shares,
            "is_renounced": renounced, "notes": notes,
        })
        return pid

    def birth_of(key):
        v = (answers.get(key) or "").strip()
        if v.isdigit():
            return int(v)
        return None

    man = 10000  # 万円→円

    # ── 資産合計（被相続人に集約） ──
    estate = (
        _int(answers, "asset_home") + _int(answers, "asset_cash")
        + _int(answers, "asset_sec") + _int(answers, "asset_other")
    ) * man
    has_shares = _yn(answers, "has_shares")
    if has_shares:
        estate += _int(answers, "shares_value") * man

    notes_parts = []
    ins = _int(answers, "insurance")
    if ins > 0:
        notes_parts.append(f"死亡保険金 約{ins}万円")
    special = (answers.get("special") or "").strip()
    if special and special not in ("特になし", "なし"):
        notes_parts.append(f"特記事項: {special}")
    prop_notes = " / ".join(notes_parts)

    # ── 被相続人 ──
    prop_id = add(
        answers.get("d_name", "被相続人"), _gender(answers, "d_gender"),
        birth_of("d_birth"), alive=False, prop=True,
        assets=estate, shares=has_shares, notes=prop_notes,
    )

    # ── 配偶者 ──
    if _yn(answers, "has_spouse"):
        sp_alive = answers.get("spouse_alive", "健在") == "健在"
        sp_id = add(answers.get("spouse_name", "配偶者"), "unknown", alive=sp_alive)
        rels.append({"person1_id": prop_id, "person2_id": sp_id, "rel_type": "spouse"})

    # ── 子・孫（代襲） ──
    n_child = _int(answers, "num_children")
    for i in range(n_child):
        c_alive = answers.get(f"child_{i}_alive", "健在") == "健在"
        c_id = add(answers.get(f"child_{i}_name", f"子{i + 1}"), "unknown", alive=c_alive)
        rels.append({"person1_id": prop_id, "person2_id": c_id, "rel_type": "parent_child"})
        if not c_alive:
            for j in range(_int(answers, f"child_{i}_gc")):
                gc_id = add(answers.get(f"child_{i}_gc_{j}_name", f"孫{j + 1}"), "unknown", alive=True)
                rels.append({"person1_id": c_id, "person2_id": gc_id, "rel_type": "parent_child"})

    # ── 子がいない場合：両親・兄弟姉妹 ──
    if n_child == 0:
        father_alive = answers.get("father_alive") == "健在"
        mother_alive = answers.get("mother_alive") == "健在"
        num_sib = _int(answers, "num_siblings")
        need_parents = father_alive or mother_alive or num_sib > 0

        father_id = mother_id = None
        if need_parents:
            father_id = add("父", "male", alive=father_alive)
            mother_id = add("母", "female", alive=mother_alive)
            rels.append({"person1_id": father_id, "person2_id": prop_id, "rel_type": "parent_child"})
            rels.append({"person1_id": mother_id, "person2_id": prop_id, "rel_type": "parent_child"})

        for k in range(num_sib):
            s_alive = answers.get(f"sib_{k}_alive", "健在") == "健在"
            s_id = add(answers.get(f"sib_{k}_name", f"兄弟姉妹{k + 1}"), "unknown", alive=s_alive)
            if father_id:
                rels.append({"person1_id": father_id, "person2_id": s_id, "rel_type": "parent_child"})
            if mother_id:
                rels.append({"person1_id": mother_id, "person2_id": s_id, "rel_type": "parent_child"})

    return {"persons": persons, "relationships": rels}
