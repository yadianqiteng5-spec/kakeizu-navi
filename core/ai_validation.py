"""
AI出力（Gemini）に対するクロスバリデーション機構

ハルシネーション防止のため、AIが返した数値・主張を
自社の確定的計算ロジックと照合し、矛盾を検出する。

【検証対象】
- 法定相続分の比率 (1/2, 1/4, 1/8 等)
- 相続税額の概算
- 配偶者控除の上限値 (1.6億円)
- 速算表の境界値
- 民法・相続税法の条文番号
"""
import re
from typing import List, Dict, Optional


# ─────────────────────────────────────────────────────────────────
# 既知の正しい事実（AIが間違えやすいポイント）
# ─────────────────────────────────────────────────────────────────

KNOWN_FACTS = {
    "配偶者控除上限": ("1億6,000万円", "1.6億円", "160,000,000円"),
    "暦年贈与非課税枠": ("110万円", "1,100,000円"),
    "相続時精算課税非課税枠": ("2,500万円", "25,000,000円"),
    "基礎控除式": ("3,000万円 + 600万円", "3000万+600万"),
    "生命保険非課税": ("500万円", "5,000,000円"),
    "持戻し期間2024": ("7年", "7年以内"),
    "小規模宅地居住用": ("330", "80%"),
    "小規模宅地事業用": ("400", "80%"),
    "小規模宅地貸付": ("200", "50%"),
}


# ─────────────────────────────────────────────────────────────────
# 危険な誤情報パターン（AIがよく間違える表現）
# ─────────────────────────────────────────────────────────────────

DANGEROUS_PATTERNS = [
    # (正規表現, 理由)
    (r"配偶者控除.{0,30}(?:1億[57-9],?000万|1\.[57-9]億|1[57-9],?000万円?|15億)",
     "配偶者控除上限を1.5億等と誤記している可能性（正: 1.6億円）"),
    (r"暦年贈与.{0,20}1[1-2][1-9],?000円?(?!.{0,10}非課税)",
     "暦年贈与非課税枠を110万円以外で記載している可能性"),
    (r"持戻し.{0,10}[3-6]年(?!以内)(?!.{0,20}改正前)",
     "暦年贈与の持戻し期間を旧3年で記載している可能性（2024年改正で7年）"),
    (r"小規模宅地.{0,30}(?:90|95|99)\s*%",
     "小規模宅地等の特例の減額割合を90%超で誤記している可能性（正: 50% or 80%）"),
    (r"特別養子.{0,30}実親.{0,10}相続",
     "特別養子と実親の相続関係を誤記している可能性（民法817条の9で断絶）"),
    (r"民法\s*(?:900|889|887).{0,5}条の?[6-9]",
     "民法の条文番号が誤っている可能性（条文の存在を確認）"),
]


def validate_ai_output(text: str) -> Dict[str, List[str]]:
    """
    AI出力テキストを検証し、警告・エラーをリストで返す。

    Returns:
        {
          "warnings": [str, ...],   # 軽微な疑念点
          "errors":   [str, ...],   # 明確な誤情報
          "facts_mentioned": [str, ...],  # 確認済みの正確な事実
        }
    """
    warnings = []
    errors = []
    facts_mentioned = []

    # 危険パターン検出
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"⚠️ {reason}")

    # 既知の正しい事実が言及されているかチェック（信頼度を上げる材料）
    for fact_name, variations in KNOWN_FACTS.items():
        for v in variations:
            if v in text:
                facts_mentioned.append(fact_name)
                break

    # 「断定的法的助言」っぽい表現の検出（弁護士法72条配慮）
    advice_patterns = [
        (r"必ず[^。]*してください(?!.{0,30}専門家)",
         "断定的指示が含まれています（「〜が選択肢として考えられます」推奨）"),
        (r"あなたの場合は[^。]*べき",
         "個別事案への断定的助言の可能性（一般情報提供に留めるべき）"),
    ]
    for pattern, reason in advice_patterns:
        if re.search(pattern, text):
            warnings.append(f"💡 {reason}")

    return {
        "warnings": warnings,
        "errors": errors,
        "facts_mentioned": list(set(facts_mentioned)),
    }


def cross_check_tax_amount(ai_text: str, calculated_tax: int) -> Optional[str]:
    """
    AI出力テキストから「相続税○○円/○○万円」等を抽出し、
    自社計算値と大幅にズレていないかチェックする。

    Returns:
        ズレが検出されたら警告メッセージ、なければNone
    """
    # 「相続税」「税額」周辺の金額を抽出
    matches = re.findall(
        r"(?:相続税|税額|納税額)[^。\n]{0,30}?([0-9,]+)\s*(万円|円)",
        ai_text,
    )
    if not matches:
        return None

    for amount_str, unit in matches:
        try:
            amount_num = int(amount_str.replace(",", ""))
            ai_amount_yen = amount_num * 10000 if unit == "万円" else amount_num
            # 計算値の30%以上ズレていたら警告
            if calculated_tax > 0:
                ratio = abs(ai_amount_yen - calculated_tax) / calculated_tax
                if ratio > 0.30:
                    return (
                        f"⚠️ AIが提示した税額（{amount_num:,}{unit}）と"
                        f"自社計算値（{calculated_tax//10000:,}万円）に"
                        f"大きな乖離があります（{int(ratio*100)}%差）。"
                        f"自社計算値を信頼してください。"
                    )
        except (ValueError, ZeroDivisionError):
            continue
    return None


def format_validation_badge(result: Dict[str, List[str]]) -> str:
    """検証結果をUI表示用のバッジHTMLに整形"""
    n_err = len(result["errors"])
    n_warn = len(result["warnings"])
    n_facts = len(result["facts_mentioned"])

    if n_err > 0:
        return (
            f'<div style="background:#FADBD8;border-left:4px solid #E74C3C;'
            f'padding:10px;border-radius:6px;font-size:13px;">'
            f'<b>🚨 AI出力に {n_err} 件の疑念検出</b><br>'
            + "<br>".join(result["errors"])
            + '</div>'
        )
    if n_warn > 0:
        return (
            f'<div style="background:#FDEBD0;border-left:4px solid #E67E22;'
            f'padding:10px;border-radius:6px;font-size:13px;">'
            f'<b>💡 {n_warn} 件の改善余地</b><br>'
            + "<br>".join(result["warnings"])
            + '</div>'
        )
    if n_facts > 0:
        return (
            f'<div style="background:#D5F4E6;border-left:4px solid #27AE60;'
            f'padding:10px;border-radius:6px;font-size:13px;">'
            f'✅ <b>AI出力の検証OK</b>: {n_facts} 個の正確な事実を確認 '
            f'<span style="opacity:0.7;">({", ".join(result["facts_mentioned"])})</span>'
            f'</div>'
        )
    return ""
