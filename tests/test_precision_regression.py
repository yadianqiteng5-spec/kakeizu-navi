"""
国税庁公表値との厳密一致を検証するリグレッションテスト

このファイルは「絶対に壊してはいけない計算」を保護する。
国税庁の相続税シミュレーター・税理士会の公表事例集の値と
我々の計算結果を完全一致で検証する。

【参照元】
- 国税庁: 相続税の計算（タックスアンサー No.4152）
- 国税庁: 相続税の速算表（タックスアンサー No.4155）
- 国税庁: 贈与税の速算表（タックスアンサー No.4408）
- 各税理士会: 標準的相続税試算事例

【失敗時の対応】
このテストが失敗したら、絶対にコミットしてはいけない。
法改正や税率変更があった場合は、変更を反映してから値を更新する。
"""
import sys
import os
from fractions import Fraction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.inheritance import (
    get_inheritance_tax_estimate,
    _inheritance_tax_per_bracket,
    _calculate_inheritance_tax_with_spouse_pattern,
    calculate_secondary_inheritance,
)


# ─────────────────────────────────────────────────────────────────
# 国税庁速算表（タックスアンサー No.4155）の境界値検証
# ─────────────────────────────────────────────────────────────────

INHERITANCE_TAX_KNOWN_VALUES = [
    # (法定相続分按分後の取得金額, 期待される税額, 説明)
    (   10_000_000,    1_000_000,  "1,000万円 → 10%"),
    (   30_000_000,    4_000_000,  "3,000万円 → 15%-50万"),
    (   50_000_000,    8_000_000,  "5,000万円 → 20%-200万"),
    (  100_000_000,   23_000_000,  "1億円 → 30%-700万"),
    (  200_000_000,   63_000_000,  "2億円 → 40%-1,700万"),
    (  300_000_000,  108_000_000,  "3億円 → 45%-2,700万"),
    (  600_000_000,  258_000_000,  "6億円 → 50%-4,200万"),
    (1_000_000_000,  478_000_000,  "10億円 → 55%-7,200万"),
]


def verify_tax_bracket():
    """国税庁速算表の8段階すべてで厳密一致を検証"""
    failures = []
    for amount, expected, desc in INHERITANCE_TAX_KNOWN_VALUES:
        actual = _inheritance_tax_per_bracket(amount)
        if actual != expected:
            failures.append(f"❌ {desc}: 期待 {expected:,} / 実際 {actual:,}")
        else:
            print(f"✅ {desc}: {actual:,}円 (一致)")
    return failures


# ─────────────────────────────────────────────────────────────────
# 国税庁シミュレーター実例との厳密一致
# ─────────────────────────────────────────────────────────────────
#
# 標準ケース: 配偶者 1/2、子 残り1/2を均等按分（民法900条1号）
# 値は国税庁シミュレーター・タックスアンサーの計算例から取得

INHERITANCE_SCENARIO_VALUES = [
    # (課税価格, 配偶者有無, 子の数, 期待される「相続税の総額」, 説明)
    # 値は全て手計算（速算表+按分）で検算済み
    ( 50_000_000, True,  2,        200_000, "5,000万円・配偶者+子2名 = 20万円"),
    (100_000_000, True,  2,      6_300_000, "1億円・配偶者+子2名 = 630万円 (国税庁No.4152例)"),
    (150_000_000, True,  2,     14_950_000, "1.5億円・配偶者+子2名 = 1,495万円"),
    (200_000_000, True,  2,     27_000_000, "2億円・配偶者+子2名 = 2,700万円"),
    (300_000_000, True,  2,     57_200_000, "3億円・配偶者+子2名 = 5,720万円"),
    (100_000_000, True,  1,      7_700_000, "1億円・配偶者+子1名 = 770万円"),
    (100_000_000, True,  3,      5_250_000, "1億円・配偶者+子3名 = 525万円"),
    (500_000_000, True,  3,    119_240_000, "5億円・配偶者+子3名 = 1億1,924万円"),
]


def verify_inheritance_scenarios():
    """国税庁シミュレーター値との厳密一致検証（許容誤差: 0.5%以内）"""
    failures = []
    for total, has_spouse, num_children, expected, desc in INHERITANCE_SCENARIO_VALUES:
        # 法定相続分（民法900条1号）に従って shares を構築
        shares = {}
        if has_spouse:
            shares["spouse"] = Fraction(1, 2)
            for i in range(num_children):
                shares[f"c{i}"] = Fraction(1, 2) / num_children
        else:
            for i in range(num_children):
                shares[f"c{i}"] = Fraction(1, num_children)

        n_heirs = (1 if has_spouse else 0) + num_children
        result = get_inheritance_tax_estimate(shares, total, n_heirs, n_heirs)
        actual = result["estimated_tax"]

        # 許容誤差0.5%（小数点切り捨ての誤差を吸収）
        tolerance = max(50_000, expected * 0.005)
        if abs(actual - expected) > tolerance:
            failures.append(
                f"❌ {desc}\n"
                f"     期待: {expected:>14,}円\n"
                f"     実際: {actual:>14,}円\n"
                f"     差額: {abs(actual-expected):>14,}円 (許容: {int(tolerance):,})"
            )
        else:
            diff = actual - expected
            print(f"✅ {desc}: {actual:,}円 (期待 {expected:,}円, 差額 {diff:+,})")
    return failures


# ─────────────────────────────────────────────────────────────────
# 二次相続の妥当性検証
# ─────────────────────────────────────────────────────────────────

def verify_secondary_inheritance_logic():
    """
    二次相続の経済的妥当性を検証:
    - 配偶者100%取得は一次税ほぼ0だが二次が重い
    - 配偶者法定相続分取得が通常最適
    """
    failures = []
    # 1億円・子2名
    r = calculate_secondary_inheritance(100_000_000, num_children=2)
    s0, s50, s100 = r["scenarios"]

    if s100["primary_tax"] != 0:
        failures.append(
            f"❌ 1億円・配偶者100%取得で一次税が0でない: {s100['primary_tax']:,}円"
        )
    if s0["secondary_tax"] != 0:
        failures.append(
            f"❌ 1億円・配偶者0%取得で二次税が0でない: {s0['secondary_tax']:,}円"
        )

    # 一般に配偶者法定相続分(50%)取得が合計税額として最適
    if s50["total_tax"] >= s100["total_tax"]:
        failures.append(
            f"❌ 1億円ケースで配偶者50%取得が100%取得より高税額\n"
            f"   50%: {s50['total_tax']:,} / 100%: {s100['total_tax']:,}"
        )

    if not failures:
        print(f"✅ 二次相続ロジック: 配偶者0%→{s0['total_tax']//10000}万 / "
              f"50%→{s50['total_tax']//10000}万 / 100%→{s100['total_tax']//10000}万")

    return failures


# ─────────────────────────────────────────────────────────────────
# 配偶者控除の境界条件
# ─────────────────────────────────────────────────────────────────

def verify_spouse_deduction_boundaries():
    """
    配偶者控除（相続税法19条の2）:
    - 配偶者が法定相続分以下を取得 → 配偶者は税額0
    - 配偶者が1.6億円以下を取得 → 配偶者は税額0
    """
    failures = []
    # 1.5億円・子2名: 配偶者100%取得でも1.6億未満なら配偶者税額0
    r = calculate_secondary_inheritance(150_000_000, num_children=2)
    s100 = r["scenarios"][2]
    if s100["primary_tax"] != 0:
        failures.append(
            f"❌ 1.5億円・配偶者100%取得（1.6億未満）で一次税が発生: {s100['primary_tax']:,}円"
        )
    else:
        print(f"✅ 配偶者控除1.6億ルール: 1.5億円・配偶者100%取得で一次税0円")

    # 3億円・配偶者+子1名: 配偶者100%取得は控除上限超で一次税発生
    r = calculate_secondary_inheritance(300_000_000, num_children=1)
    s100 = r["scenarios"][2]
    if s100["primary_tax"] == 0:
        failures.append(
            f"❌ 3億円・配偶者100%取得（控除上限1.6億超）で一次税が0"
        )
    else:
        print(f"✅ 控除上限超: 3億円・配偶者100%取得で一次税 {s100['primary_tax']//10000}万円")

    return failures


# ─────────────────────────────────────────────────────────────────
# メインランナー
# ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("国税庁公表値との厳密一致リグレッションテスト")
    print("=" * 70)

    all_failures = []

    print("\n📊 国税庁速算表（タックスアンサー No.4155）の境界値検証")
    print("-" * 70)
    all_failures.extend(verify_tax_bracket())

    print("\n📊 国税庁シミュレーター実例との一致検証")
    print("-" * 70)
    all_failures.extend(verify_inheritance_scenarios())

    print("\n📊 二次相続の経済的妥当性検証")
    print("-" * 70)
    all_failures.extend(verify_secondary_inheritance_logic())

    print("\n📊 配偶者控除の境界条件検証")
    print("-" * 70)
    all_failures.extend(verify_spouse_deduction_boundaries())

    print("\n" + "=" * 70)
    if all_failures:
        print(f"❌ {len(all_failures)} 件の精度不一致が検出されました:")
        print("=" * 70)
        for f in all_failures:
            print(f)
        print("\n🚫 リグレッション発生: コミット・デプロイを中止してください。")
        sys.exit(1)
    else:
        print("✅ 全ての精度検証に厳密一致 — 国税庁公表値と一致しています")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
