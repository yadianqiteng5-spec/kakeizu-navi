"""
PDF出力のスモークテスト（reportlab導入時のみ実行）。
最大の成果物である generate_pdf_report が、氏名に < & > 等の特殊文字を含んでも
例外なく有効なPDF bytes を生成することを担保する（Paragraphはエスケープ済・Table cellは素のため
どちらの経路でも壊れないことの回帰保護）。
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_pdf_generates_with_special_chars_in_names():
    from core.family_tree import FamilyTree
    from core.inheritance import (
        calculate_legal_shares,
        calculate_legitimes,
        count_tax_legal_heirs,
        get_inheritance_tax_estimate,
    )
    from core.pdf_export import is_pdf_available, generate_pdf_report

    if not is_pdf_available():
        return  # reportlab 未導入時はスキップ（CIでは導入済み）

    ft = FamilyTree.create_scenario("standard")
    pid = ft.get_propositus()
    # 特殊文字を注入（< & > がPDF生成を壊さないことを確認）
    for p in ft.persons.values():
        p.name = f"{p.name} <&>"

    shares, _ = calculate_legal_shares(ft, pid)
    legitime = calculate_legitimes(ft, pid)
    thi = count_tax_legal_heirs(ft, pid)
    total = 50_000_000
    tax = get_inheritance_tax_estimate(shares, total, len(shares), thi["total"])

    pdf = generate_pdf_report(
        family_tree=ft,
        propositus_id=pid,
        shares=shares,
        total_assets_yen=total,
        tax_info=tax,
        tax_heir_info=thi,
        legitime_info=legitime,
    )
    assert pdf is not None and len(pdf) > 1000
