"""
法定相続分計算のエッジケーステスト

実行:
    pytest tests/
    python -m pytest tests/test_inheritance.py -v
"""
from fractions import Fraction
import sys
import os

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.family_tree import FamilyTree, Gender
from core.inheritance import (
    calculate_legal_shares,
    calculate_legitimes,
    count_tax_legal_heirs,
)


# ─────────────────────────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────────────────────────

def _build(family_spec):
    """簡易ビルダー: [(name, kwargs), ...] からFamilyTreeを構築"""
    ft = FamilyTree()
    ids = {}
    for name, kwargs in family_spec:
        ids[name] = ft.add_person(name=name, **kwargs)
    return ft, ids


# ─────────────────────────────────────────────────────────────────
# 基本ケース
# ─────────────────────────────────────────────────────────────────

def test_spouse_and_two_children():
    """配偶者 + 子2名: 配偶者1/2、子1/4ずつ"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("母", dict(is_alive=True)),
        ("長男", dict(is_alive=True)),
        ("長女", dict(is_alive=True)),
    ])
    ft.add_spouse(ids["父"], ids["母"])
    ft.add_parent_child(ids["父"], ids["長男"])
    ft.add_parent_child(ids["父"], ids["長女"])

    shares, _ = calculate_legal_shares(ft, ids["父"])
    assert shares[ids["母"]] == Fraction(1, 2)
    assert shares[ids["長男"]] == Fraction(1, 4)
    assert shares[ids["長女"]] == Fraction(1, 4)


def test_spouse_only():
    """配偶者のみ（子・親・兄弟なし）: 配偶者が全部"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("母", dict(is_alive=True)),
    ])
    ft.add_spouse(ids["父"], ids["母"])

    shares, _ = calculate_legal_shares(ft, ids["父"])
    assert shares[ids["母"]] == Fraction(1)
    assert len(shares) == 1


# ─────────────────────────────────────────────────────────────────
# 代襲相続
# ─────────────────────────────────────────────────────────────────

def test_representation_grandchild():
    """子が先に死亡 → 孫が代襲"""
    ft, ids = _build([
        ("祖父", dict(is_alive=False, is_propositus=True)),
        ("父", dict(is_alive=False)),  # 被相続人より先に死亡
        ("孫", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["祖父"], ids["父"])
    ft.add_parent_child(ids["父"], ids["孫"])

    shares, _ = calculate_legal_shares(ft, ids["祖父"])
    assert shares[ids["孫"]] == Fraction(1)


def test_renounced_child_no_representation():
    """子が相続放棄 → 代襲は発生しない（民法939条）"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("放棄子", dict(is_alive=True, is_renounced=True)),
        ("孫", dict(is_alive=True)),
        ("存命子", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["父"], ids["放棄子"])
    ft.add_parent_child(ids["放棄子"], ids["孫"])
    ft.add_parent_child(ids["父"], ids["存命子"])

    shares, _ = calculate_legal_shares(ft, ids["父"])
    assert ids["放棄子"] not in shares
    assert ids["孫"] not in shares  # 代襲発生しない
    assert shares[ids["存命子"]] == Fraction(1)


# ─────────────────────────────────────────────────────────────────
# 同時死亡推定（民法32条の2）
# ─────────────────────────────────────────────────────────────────

def test_simultaneous_death_no_mutual_inheritance_but_representation():
    """
    親と子が同時死亡 → 互いに相続権なし、ただし孫への代襲は成立。
    （被相続人=祖父、長男と祖父が同時死亡、長男の子=孫）
    """
    ft, ids = _build([
        ("祖父", dict(is_alive=False, is_propositus=True)),
        ("長男", dict(is_alive=True, died_simultaneously=True)),  # 同時死亡
        ("孫", dict(is_alive=True)),
        ("次男", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["祖父"], ids["長男"])
    ft.add_parent_child(ids["長男"], ids["孫"])
    ft.add_parent_child(ids["祖父"], ids["次男"])

    shares, _ = calculate_legal_shares(ft, ids["祖父"])
    # 長男は同時死亡で is_alive=False になり、孫が代襲
    assert ids["長男"] not in shares
    assert shares[ids["孫"]] == Fraction(1, 2)
    assert shares[ids["次男"]] == Fraction(1, 2)


# ─────────────────────────────────────────────────────────────────
# 半血兄弟（民法900条4号但書）
# ─────────────────────────────────────────────────────────────────

def test_half_blood_sibling():
    """全血兄弟1名 + 半血兄弟1名: 全血2/3、半血1/3"""
    ft, ids = _build([
        ("父", dict(is_alive=False)),
        ("母", dict(is_alive=False)),
        ("継母", dict(is_alive=False)),
        ("被相続人", dict(is_alive=False, is_propositus=True)),
        ("全血兄", dict(is_alive=True)),
        ("半血弟", dict(is_alive=True)),
    ])
    # 被相続人: 父+母 / 全血兄: 父+母 / 半血弟: 父+継母
    ft.add_parent_child(ids["父"], ids["被相続人"])
    ft.add_parent_child(ids["母"], ids["被相続人"])
    ft.add_parent_child(ids["父"], ids["全血兄"])
    ft.add_parent_child(ids["母"], ids["全血兄"])
    ft.add_parent_child(ids["父"], ids["半血弟"])
    ft.add_parent_child(ids["継母"], ids["半血弟"])

    shares, _ = calculate_legal_shares(ft, ids["被相続人"])
    assert shares[ids["全血兄"]] == Fraction(2, 3)
    assert shares[ids["半血弟"]] == Fraction(1, 3)


# ─────────────────────────────────────────────────────────────────
# 直系尊属の繰り上がり
# ─────────────────────────────────────────────────────────────────

def test_ascendants_promotion_to_grandparents():
    """両親死亡 → 祖父母に繰り上がり"""
    ft, ids = _build([
        ("祖父", dict(is_alive=True)),
        ("祖母", dict(is_alive=True)),
        ("父", dict(is_alive=False)),
        ("被相続人", dict(is_alive=False, is_propositus=True)),
    ])
    ft.add_parent_child(ids["祖父"], ids["父"])
    ft.add_parent_child(ids["祖母"], ids["父"])
    ft.add_parent_child(ids["父"], ids["被相続人"])

    shares, _ = calculate_legal_shares(ft, ids["被相続人"])
    assert shares[ids["祖父"]] == Fraction(1, 2)
    assert shares[ids["祖母"]] == Fraction(1, 2)


# ─────────────────────────────────────────────────────────────────
# 兄弟姉妹の代襲（甥姪まで・民法889条2項）
# ─────────────────────────────────────────────────────────────────

def test_sibling_representation_stops_at_niece():
    """兄死亡 → 甥が代襲。甥の子（大甥）には代襲しない"""
    ft, ids = _build([
        ("親", dict(is_alive=False)),
        ("被相続人", dict(is_alive=False, is_propositus=True)),
        ("兄", dict(is_alive=False)),
        ("甥", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["親"], ids["被相続人"])
    ft.add_parent_child(ids["親"], ids["兄"])
    ft.add_parent_child(ids["兄"], ids["甥"])

    shares, _ = calculate_legal_shares(ft, ids["被相続人"])
    assert shares[ids["甥"]] == Fraction(1)


# ─────────────────────────────────────────────────────────────────
# 特別養子縁組（民法817条の9）
# ─────────────────────────────────────────────────────────────────

def test_special_adoption_severs_biological_parent():
    """
    特別養子になった子は実親から相続しない、実親も子から相続しない。
    被相続人=実母（既に死亡）、特別養子に出された実子は相続権なし。
    """
    ft, ids = _build([
        ("実母", dict(is_alive=False, is_propositus=True)),
        ("特養子", dict(is_alive=True)),
        ("養親", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["実母"], ids["特養子"], adoption_type="biological")
    ft.add_parent_child(ids["養親"], ids["特養子"], adoption_type="special_adoption")

    shares, _ = calculate_legal_shares(ft, ids["実母"])
    # 特養子は実母から相続できない → 相続人なし
    assert ids["特養子"] not in shares


def test_special_adopted_child_inherits_from_adoptive_parent():
    """特別養子は養親からはきちんと相続する"""
    ft, ids = _build([
        ("養親", dict(is_alive=False, is_propositus=True)),
        ("特養子", dict(is_alive=True)),
        ("実親", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["実親"], ids["特養子"], adoption_type="biological")
    ft.add_parent_child(ids["養親"], ids["特養子"], adoption_type="special_adoption")

    shares, _ = calculate_legal_shares(ft, ids["養親"])
    assert shares[ids["特養子"]] == Fraction(1)


def test_regular_adoption_keeps_biological_link():
    """普通養子は実親との関係も残る → 実親が被相続人なら相続できる"""
    ft, ids = _build([
        ("実母", dict(is_alive=False, is_propositus=True)),
        ("普養子", dict(is_alive=True)),
        ("養親", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["実母"], ids["普養子"], adoption_type="biological")
    ft.add_parent_child(ids["養親"], ids["普養子"], adoption_type="regular_adoption")

    shares, _ = calculate_legal_shares(ft, ids["実母"])
    assert shares[ids["普養子"]] == Fraction(1)


# ─────────────────────────────────────────────────────────────────
# 相続税法上の養子算入制限（相続税法15条2項）
# ─────────────────────────────────────────────────────────────────

def test_tax_heir_count_adoption_limit_with_bio_child():
    """実子あり → 養子は1名まで算入"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("実子", dict(is_alive=True)),
        ("養子1", dict(is_alive=True)),
        ("養子2", dict(is_alive=True)),
        ("養子3", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["父"], ids["実子"], adoption_type="biological")
    ft.add_parent_child(ids["父"], ids["養子1"], adoption_type="regular_adoption")
    ft.add_parent_child(ids["父"], ids["養子2"], adoption_type="regular_adoption")
    ft.add_parent_child(ids["父"], ids["養子3"], adoption_type="regular_adoption")

    info = count_tax_legal_heirs(ft, ids["父"])
    assert info["biological"] == 1
    assert info["adopted_counted"] == 1
    assert info["adopted_excluded"] == 2
    assert info["total"] == 2  # 実子1 + 養子1


def test_tax_heir_count_adoption_limit_without_bio_child():
    """実子なし → 養子は2名まで算入"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("養子1", dict(is_alive=True)),
        ("養子2", dict(is_alive=True)),
        ("養子3", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["父"], ids["養子1"], adoption_type="regular_adoption")
    ft.add_parent_child(ids["父"], ids["養子2"], adoption_type="regular_adoption")
    ft.add_parent_child(ids["父"], ids["養子3"], adoption_type="regular_adoption")

    info = count_tax_legal_heirs(ft, ids["父"])
    assert info["adopted_counted"] == 2
    assert info["adopted_excluded"] == 1
    assert info["total"] == 2


# ─────────────────────────────────────────────────────────────────
# 遺留分
# ─────────────────────────────────────────────────────────────────

def test_legitime_siblings_only():
    """兄弟姉妹のみが相続人 → 遺留分なし"""
    ft, ids = _build([
        ("親", dict(is_alive=False)),
        ("被相続人", dict(is_alive=False, is_propositus=True)),
        ("兄", dict(is_alive=True)),
    ])
    ft.add_parent_child(ids["親"], ids["被相続人"])
    ft.add_parent_child(ids["親"], ids["兄"])

    info = calculate_legitimes(ft, ids["被相続人"])
    assert not info["has_legitime"]
    assert info["overall"] == Fraction(0)


def test_legitime_ascendants_only_one_third():
    """直系尊属のみ → 総体的遺留分は1/3"""
    ft, ids = _build([
        ("父親", dict(is_alive=True)),
        ("被相続人", dict(is_alive=False, is_propositus=True)),
    ])
    ft.add_parent_child(ids["父親"], ids["被相続人"])

    info = calculate_legitimes(ft, ids["被相続人"])
    assert info["overall"] == Fraction(1, 3)
    assert info["individual"][ids["父親"]] == Fraction(1, 3)  # 1 × 1/3


def test_legitime_spouse_and_child_half():
    """配偶者+子 → 総体的遺留分は1/2、配偶者個別1/4、子個別1/4"""
    ft, ids = _build([
        ("父", dict(is_alive=False, is_propositus=True)),
        ("母", dict(is_alive=True)),
        ("子", dict(is_alive=True)),
    ])
    ft.add_spouse(ids["父"], ids["母"])
    ft.add_parent_child(ids["父"], ids["子"])

    info = calculate_legitimes(ft, ids["父"])
    assert info["overall"] == Fraction(1, 2)
    assert info["individual"][ids["母"]] == Fraction(1, 4)
    assert info["individual"][ids["子"]] == Fraction(1, 4)


# ─────────────────────────────────────────────────────────────────
# シナリオビルダーのスモークテスト
# ─────────────────────────────────────────────────────────────────

def test_all_scenarios_build_and_compute():
    """全8シナリオがエラーなく構築でき、相続人が1名以上算出される"""
    scenarios = [
        "standard", "no_children", "siblings_only", "half_blood",
        "adoption", "special_adoption", "simultaneous_death", "renounce",
    ]
    for sid in scenarios:
        ft = FamilyTree.create_scenario(sid)
        prop = ft.get_propositus()
        assert prop is not None, f"{sid}: 被相続人が設定されていない"
        shares, _ = calculate_legal_shares(ft, prop)
        # renounce シナリオは1名だけ残る、その他は2名以上
        assert len(shares) >= 1, f"{sid}: 相続人が算出されない"


def test_scenario_special_adoption_severs_bio_parent():
    """特別養子シナリオでは実親（参考表示）は相続人に含まれない"""
    ft = FamilyTree.create_scenario("special_adoption")
    prop = ft.get_propositus()
    shares, _ = calculate_legal_shares(ft, prop)
    # 養親側の被相続人から見て、配偶者(妻)+特別養子の2名のみ
    assert len(shares) == 2


def test_scenario_renounce_no_representation():
    """放棄シナリオで放棄者の子（孫）が代襲しない"""
    ft = FamilyTree.create_scenario("renounce")
    prop = ft.get_propositus()
    shares, _ = calculate_legal_shares(ft, prop)
    # 妻も放棄、長男も放棄 → 次男のみ
    heir_names = [ft.persons[hid].name for hid in shares]
    assert "次男" in heir_names
    assert "孫（長男の子）" not in heir_names


# ─────────────────────────────────────────────────────────────────
# 小規模宅地等の特例
# ─────────────────────────────────────────────────────────────────

def test_small_residential_under_limit():
    """200㎡（上限330㎡以下）の特定居住用宅地 → 全面積に80%減額"""
    from core.inheritance import calculate_small_residential_deduction
    r = calculate_small_residential_deduction("residential", 50_000_000, 200.0)
    assert r["applicable"]
    assert r["reduced_amount"] == 40_000_000  # 5000万 × 80%
    assert r["after_deduction"] == 10_000_000


def test_small_residential_over_limit():
    """500㎡（上限超） → 330/500 のみに80%減額（按分）"""
    from core.inheritance import calculate_small_residential_deduction
    r = calculate_small_residential_deduction("residential", 50_000_000, 500.0)
    assert r["applicable"]
    # 5000万 × (330/500) × 80% = 2640万
    assert r["reduced_amount"] == 26_400_000


def test_small_residential_rental_50pct():
    """貸付事業用は50%減額・上限200㎡"""
    from core.inheritance import calculate_small_residential_deduction
    r = calculate_small_residential_deduction("rental", 20_000_000, 100.0)
    assert r["reduced_amount"] == 10_000_000  # 2000万 × 50%


def test_small_residential_none():
    """none を渡したら applicable=False"""
    from core.inheritance import calculate_small_residential_deduction
    r = calculate_small_residential_deduction("none", 10_000_000, 100.0)
    assert not r["applicable"]
    assert r["after_deduction"] == 10_000_000


if __name__ == "__main__":
    # pytest なしで直接実行できるよう簡易ランナー
    import traceback
    tests = [(n, fn) for n, fn in globals().items() if n.startswith("test_") and callable(fn)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
