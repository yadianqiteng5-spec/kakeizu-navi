# -*- coding: utf-8 -*-
"""対話ヒアリング → 家系図組み立て → 法定相続分 の回帰テスト。

python -X utf8 tests/test_hearing.py で実行。
"""
import sys
from pathlib import Path
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hearing import build_question_list, assemble
from core.family_tree import FamilyTree, Gender
from core.inheritance import calculate_legal_shares


def _build(ans):
    data = assemble(ans)
    ft = FamilyTree()
    idm = {}
    gm = {"male": Gender.MALE, "female": Gender.FEMALE, "unknown": Gender.UNKNOWN}
    for p in data["persons"]:
        idm[p["id"]] = ft.add_person(
            p["name"], gm[p["gender"]], p["birth_year"], p["is_alive"],
            p["is_propositus"], p["assets_yen"], p["has_business_shares"],
            is_renounced=p["is_renounced"], notes=p["notes"],
        )
    for r in data["relationships"]:
        a, b = idm[r["person1_id"]], idm[r["person2_id"]]
        if r["rel_type"] == "spouse":
            ft.add_spouse(a, b)
        else:
            ft.add_parent_child(a, b)
    return ft


def _shares_by_name(ans):
    ft = _build(ans)
    pid = ft.get_propositus()
    sh, _ = calculate_legal_shares(ft, pid)
    return {ft.persons[k].name: v for k, v in sh.items()}


CASES = [
    ("配偶者+子2(1人死亡→孫1人代襲)",
     {"d_name": "太郎", "d_gender": "男性", "has_spouse": "はい", "spouse_name": "花子",
      "spouse_alive": "健在", "num_children": "2",
      "child_0_name": "一郎", "child_0_alive": "健在",
      "child_1_name": "三郎", "child_1_alive": "すでに死亡", "child_1_gc": "1", "child_1_gc_0_name": "孫太",
      "asset_cash": "5000", "has_shares": "いいえ", "insurance": "0"},
     {"花子": Fraction(1, 2), "一郎": Fraction(1, 4), "孫太": Fraction(1, 4)}),

    ("配偶者のみ",
     {"d_name": "太郎", "d_gender": "男性", "has_spouse": "はい", "spouse_name": "花子",
      "spouse_alive": "健在", "num_children": "0",
      "father_alive": "すでに死亡・いない", "mother_alive": "すでに死亡・いない", "num_siblings": "0",
      "asset_cash": "5000", "has_shares": "いいえ", "insurance": "0"},
     {"花子": Fraction(1)}),

    ("配偶者+兄弟2",
     {"d_name": "太郎", "d_gender": "男性", "has_spouse": "はい", "spouse_name": "花子",
      "spouse_alive": "健在", "num_children": "0",
      "father_alive": "すでに死亡・いない", "mother_alive": "すでに死亡・いない", "num_siblings": "2",
      "sib_0_name": "兄", "sib_1_name": "妹", "asset_cash": "4000", "has_shares": "いいえ", "insurance": "0"},
     {"花子": Fraction(3, 4), "兄": Fraction(1, 8), "妹": Fraction(1, 8)}),

    ("配偶者+親(両親健在)",
     {"d_name": "太郎", "d_gender": "男性", "has_spouse": "はい", "spouse_name": "花子",
      "spouse_alive": "健在", "num_children": "0",
      "father_alive": "健在", "mother_alive": "健在", "asset_cash": "6000",
      "has_shares": "いいえ", "insurance": "0"},
     {"花子": Fraction(2, 3), "父": Fraction(1, 6), "母": Fraction(1, 6)}),

    ("子のみ3人",
     {"d_name": "母", "d_gender": "女性", "has_spouse": "いいえ", "num_children": "3",
      "child_0_name": "A", "child_0_alive": "健在",
      "child_1_name": "B", "child_1_alive": "健在",
      "child_2_name": "C", "child_2_alive": "健在",
      "asset_cash": "15000", "has_shares": "いいえ", "insurance": "0"},
     {"A": Fraction(1, 3), "B": Fraction(1, 3), "C": Fraction(1, 3)}),
]


def main():
    passed = failed = 0
    for label, ans, expected in CASES:
        got = _shares_by_name(ans)
        if got == expected:
            passed += 1
            print(f"  PASS {label}")
        else:
            failed += 1
            print(f"  FAIL {label}\n    期待: {expected}\n    実際: {got}")

    # 質問リストが回答に応じて伸びることの確認
    base = len(build_question_list({}))
    with_kids = len(build_question_list({"num_children": "2"}))
    assert with_kids > base, "子の人数に応じて質問が増えること"
    print(f"  PASS 動的質問生成（base={base} → 子2人={with_kids}）")

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
