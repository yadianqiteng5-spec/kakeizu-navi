"""
AI出力クロスバリデーション機構のテスト
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai_validation import (
    validate_ai_output, cross_check_tax_amount, KNOWN_FACTS, DANGEROUS_PATTERNS
)


def test_validate_detects_wrong_spouse_deduction():
    """配偶者控除を1.5億円と誤記したAI出力を検出"""
    bad = "配偶者控除の上限は1億5,000万円までです。"
    result = validate_ai_output(bad)
    assert len(result["errors"]) > 0


def test_validate_detects_old_carryback_period():
    """暦年贈与の持戻し期間を旧3年と記載したAI出力を検出"""
    bad = "暦年贈与は持戻し3年です。"
    result = validate_ai_output(bad)
    assert any("持戻し" in e or "3年" in e for e in result["errors"])


def test_validate_detects_wrong_small_land_rate():
    """小規模宅地等の特例の減額割合を90%超で誤記したAI出力を検出"""
    bad = "小規模宅地等の特例で95%減額できます。"
    result = validate_ai_output(bad)
    assert len(result["errors"]) > 0


def test_validate_detects_special_adoption_error():
    """特別養子と実親の相続関係の誤情報を検出"""
    bad = "特別養子は実親からも相続することができます。"
    result = validate_ai_output(bad)
    assert any("特別養子" in e for e in result["errors"])


def test_validate_accepts_correct_facts():
    """正確な情報を含むAI出力は事実認識として記録される"""
    good = (
        "配偶者控除は1億6,000万円または法定相続分のいずれか多い方まで非課税です。"
        "暦年贈与の非課税枠は年110万円までです。"
        "基礎控除は3,000万円 + 600万円×法定相続人数です。"
    )
    result = validate_ai_output(good)
    assert len(result["errors"]) == 0
    assert len(result["facts_mentioned"]) >= 2


def test_cross_check_tax_amount_detects_large_discrepancy():
    """AI出力の税額と自社計算値が30%以上ズレている場合に警告"""
    ai_text = "相続税は約2,000万円と概算されます。"
    calculated = 6_300_000  # 630万円
    warning = cross_check_tax_amount(ai_text, calculated)
    assert warning is not None
    assert "乖離" in warning


def test_cross_check_tax_amount_no_discrepancy():
    """近い値なら警告なし"""
    ai_text = "相続税は約650万円程度になる可能性があります。"
    calculated = 6_300_000  # 630万円
    warning = cross_check_tax_amount(ai_text, calculated)
    assert warning is None


def test_cross_check_no_amount_mentioned():
    """金額の言及がなければ警告なし"""
    ai_text = "配偶者控除を活用することが選択肢として考えられます。"
    calculated = 6_300_000
    assert cross_check_tax_amount(ai_text, calculated) is None


def test_dangerous_patterns_are_well_formed():
    """全ての危険パターン正規表現が有効であること"""
    import re
    for pattern, reason in DANGEROUS_PATTERNS:
        # コンパイルできることを確認
        re.compile(pattern)


if __name__ == "__main__":
    import traceback
    tests = [(n, fn) for n, fn in globals().items()
             if n.startswith("test_") and callable(fn)]
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
