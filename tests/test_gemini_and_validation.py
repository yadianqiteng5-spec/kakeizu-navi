"""
AI入力解析（JSON抽出）と検証バッジ・非弁警告のユニットテスト（外部API非依存）。
gemini_client._extract_json と ai_validation の表示/警告分岐を回帰保護する。
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.gemini_client import _extract_json
from core.ai_validation import validate_ai_output, format_validation_badge


# ── _extract_json（AI応答からのJSON抽出）──────────────────────────────
def test_extract_json_clean():
    assert _extract_json('{"persons": []}') == {"persons": []}


def test_extract_json_trailing_prose():
    # 旧来の貪欲正規表現 {...} はここで壊れた（後続の波括弧まで飲み込む）
    assert _extract_json('{"a": 1} という結果です。詳細は{別途}。') == {"a": 1}


def test_extract_json_code_fence():
    assert _extract_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_extract_json_nested_and_braces_in_strings():
    src = '前置き {"p": [{"id": "p1", "name": "山田 {太郎}"}], "x": 3} 末尾'
    assert _extract_json(src) == {"p": [{"id": "p1", "name": "山田 {太郎}"}], "x": 3}


def test_extract_json_none_on_garbage():
    assert _extract_json("no json here") is None
    assert _extract_json("") is None
    assert _extract_json("{壊れたJSON") is None


# ── format_validation_badge（errors > warnings > facts > 空 の4分岐）──────
def test_badge_errors_branch():
    html = format_validation_badge({"errors": ["x"], "warnings": [], "facts_mentioned": []})
    assert "🚨" in html


def test_badge_warnings_branch():
    html = format_validation_badge({"errors": [], "warnings": ["y"], "facts_mentioned": []})
    assert "💡" in html


def test_badge_facts_branch():
    html = format_validation_badge({"errors": [], "warnings": [], "facts_mentioned": ["配偶者控除上限"]})
    assert "✅" in html


def test_badge_empty_branch():
    assert format_validation_badge({"errors": [], "warnings": [], "facts_mentioned": []}) == ""


# ── validate_ai_output warnings（断定的助言＝弁護士法72条配慮）──────────
def test_validate_warns_on_imperative_advice():
    result = validate_ai_output("必ず生前贈与を実行してください。")
    assert len(result["warnings"]) > 0


def test_validate_no_warn_when_expert_referral_follows():
    # 「してください」直後に専門家への言及があれば非弁警告は出さない
    result = validate_ai_output("必ず生前贈与を実行してください。最終判断は専門家にご相談ください。")
    assert len(result["warnings"]) == 0
