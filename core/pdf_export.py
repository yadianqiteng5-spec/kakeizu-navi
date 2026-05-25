"""
PDF出力モジュール

reportlab + 組み込み CID フォント（HeiseiKakuGo-W5）を使用するため、
外部の日本語フォントファイル不要で動作する。
"""
from io import BytesIO
from datetime import datetime
from typing import Optional


def _try_register_jp_font() -> str:
    """日本語フォントを登録し、フォント名を返す（失敗時は Helvetica）"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        name = "HeiseiKakuGo-W5"
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
            return name
        except Exception:
            return "Helvetica"
    except ImportError:
        return "Helvetica"


def is_pdf_available() -> bool:
    """reportlab がインストールされているか"""
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False


def generate_pdf_report(
    family_tree,
    propositus_id: str,
    shares: dict,
    total_assets_yen: int,
    tax_info: Optional[dict] = None,
    tax_heir_info: Optional[dict] = None,
    legitime_info: Optional[dict] = None,
) -> Optional[bytes]:
    """
    相続シミュレーション結果の PDF を生成して bytes を返す。
    reportlab が無い場合は None。
    """
    if not is_pdf_available():
        return None

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    font_name = _try_register_jp_font()

    # ── スタイル定義 ──────────────────────────────────────────────────
    base = getSampleStyleSheet()
    s_title = ParagraphStyle(
        name="JpTitle", parent=base["Title"],
        fontName=font_name, fontSize=18, spaceAfter=14,
        textColor=colors.HexColor("#2C3E50"),
    )
    s_heading = ParagraphStyle(
        name="JpHeading", parent=base["Heading2"],
        fontName=font_name, fontSize=13,
        spaceBefore=14, spaceAfter=8,
        textColor=colors.HexColor("#2C3E50"),
        borderPadding=(0, 0, 4, 0),
    )
    s_body = ParagraphStyle(
        name="JpBody", parent=base["BodyText"],
        fontName=font_name, fontSize=10, leading=16,
    )
    s_caption = ParagraphStyle(
        name="JpCaption", parent=base["BodyText"],
        fontName=font_name, fontSize=8,
        textColor=colors.grey, leading=12,
    )
    s_warn = ParagraphStyle(
        name="JpWarn", parent=base["BodyText"],
        fontName=font_name, fontSize=9, leading=14,
        textColor=colors.HexColor("#8B6914"),
        backColor=colors.HexColor("#FFF3CD"),
        borderColor=colors.HexColor("#FFC107"),
        borderWidth=0.5, borderPadding=8,
        spaceBefore=4, spaceAfter=8,
    )

    # ── ドキュメント構築 ──────────────────────────────────────────────
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title="家系図Navi 相続シミュレーション結果",
    )
    story = []

    # タイトル + 生成日時
    story.append(Paragraph("家系図Navi 相続シミュレーション結果", s_title))
    story.append(Paragraph(
        f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
        s_caption,
    ))
    story.append(Spacer(1, 6))

    # 利用上の注意（弁護士法72条への配慮を明記）
    story.append(Paragraph(
        "<b>【ご利用上の注意】</b><br/>"
        "本書面は一般的なシミュレーション結果であり、<b>法的な助言ではありません</b>。"
        "具体的な手続き・判断は、必ず弁護士・税理士・司法書士等の専門家にご相談ください。"
        "本アプリは弁護士法72条に抵触しないよう、特定事案への法律事務は一切行いません。",
        s_warn,
    ))

    # ── 1. 家族構成 ───────────────────────────────────────────────────
    story.append(Paragraph("1. 家族構成", s_heading))
    propositus = family_tree.persons[propositus_id]
    birth = f"{propositus.birth_year}年生・" if propositus.birth_year else ""
    story.append(Paragraph(
        f"<b>被相続人:</b> {propositus.name}（{birth}故人）",
        s_body,
    ))
    if propositus.assets_yen > 0:
        story.append(Paragraph(
            f"　　保有資産: ¥{propositus.assets_yen:,}"
            f"（{propositus.assets_yen//10000:,}万円）"
            + ("　・自社株保有" if propositus.has_business_shares else ""),
            s_body,
        ))

    spouse_id = family_tree.get_spouse(propositus_id)
    if spouse_id and spouse_id in family_tree.persons:
        sp = family_tree.persons[spouse_id]
        status = _status_label(sp)
        b = f"{sp.birth_year}年生・" if sp.birth_year else ""
        story.append(Paragraph(
            f"<b>配偶者:</b> {sp.name}（{b}{status}）", s_body,
        ))

    children = family_tree.get_children(propositus_id)
    if children:
        story.append(Paragraph("<b>子:</b>", s_body))
        for cid in children:
            c = family_tree.persons.get(cid)
            if not c:
                continue
            adoption = family_tree.get_adoption_type(propositus_id, cid)
            adoption_label = {
                "biological": "",
                "regular_adoption": "・普通養子",
                "special_adoption": "・特別養子",
            }.get(adoption, "")
            status = _status_label(c)
            b = f"{c.birth_year}年生・" if c.birth_year else ""
            story.append(Paragraph(
                f"　・{c.name}（{b}{status}{adoption_label}）",
                s_body,
            ))
            if not c.is_alive:
                grandchildren = family_tree.get_children(cid)
                for gcid in grandchildren:
                    gc = family_tree.persons.get(gcid)
                    if gc and gc.is_alive and not gc.is_renounced:
                        bg = f"{gc.birth_year}年生・" if gc.birth_year else ""
                        story.append(Paragraph(
                            f"　　└ {gc.name}（{bg}代襲相続人）", s_body,
                        ))

    # ── 1-2. 親子関係一覧（養子区分明示） ─────────────────────────────
    adoption_rows = [["親", "子", "区分"]]
    for r in family_tree.relationships:
        if r.rel_type != "parent_child":
            continue
        p1 = family_tree.persons.get(r.person1_id)
        p2 = family_tree.persons.get(r.person2_id)
        if not p1 or not p2:
            continue
        adoption = getattr(r, "adoption_type", "biological")
        adoption_label = {
            "biological": "実子",
            "regular_adoption": "普通養子",
            "special_adoption": "特別養子（実方と断絶）",
        }.get(adoption, "実子")
        adoption_rows.append([p1.name, p2.name, adoption_label])

    if len(adoption_rows) > 1:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>親子関係一覧</b>（養子区分）", s_body))
        ad_tbl = Table(adoption_rows, colWidths=[45*mm, 45*mm, 60*mm])
        ad_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), font_name, 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5D6D7E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ]))
        story.append(ad_tbl)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "※ 特別養子（民法817条の9）は実親との親族関係が法律上終了するため、"
            "実親からの相続権はありません。",
            s_caption,
        ))

    # ── 2. 法定相続分 ─────────────────────────────────────────────────
    story.append(Paragraph("2. 法定相続分", s_heading))

    rows = [["氏名", "法定相続分", "割合", "相続財産"]]
    for pid, frac in shares.items():
        person = family_tree.persons.get(pid)
        if not person:
            continue
        amt = ""
        if total_assets_yen > 0:
            amt = f"¥{int(float(frac) * total_assets_yen):,}"
        rows.append([
            person.name,
            f"{frac.numerator}/{frac.denominator}",
            f"{float(frac)*100:.2f}%",
            amt,
        ])

    tbl = Table(rows, colWidths=[45*mm, 30*mm, 25*mm, 50*mm])
    tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), font_name, 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
    ]))
    story.append(tbl)

    if total_assets_yen > 0:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"相続財産総額: ¥{total_assets_yen:,}"
            f"（{total_assets_yen//10000:,}万円）",
            s_caption,
        ))

    # ── 2.5. 遺留分 ───────────────────────────────────────────────────
    if legitime_info:
        story.append(Paragraph("2-2. 遺留分（民法1042条以下）", s_heading))
        # 法的根拠の説明
        rule_text = legitime_info.get("rule", "").replace("**", "")
        story.append(Paragraph(rule_text, s_body))

        if not legitime_info.get("has_legitime", False):
            story.append(Paragraph(
                "<b>遺留分は発生しません</b>。"
                "遺言書で遺産分割の指定をしても、遺留分侵害額請求のリスクはありません。",
                s_body,
            ))
        else:
            lg_rows = [["氏名", "個別遺留分", "割合", "最低保障額"]]
            for hid, frac in legitime_info["individual"].items():
                person = family_tree.persons.get(hid)
                if not person:
                    continue
                if frac > 0:
                    frac_str = f"{frac.numerator}/{frac.denominator}"
                    pct = f"{float(frac)*100:.2f}%"
                    amt = f"¥{int(float(frac)*total_assets_yen):,}" if total_assets_yen > 0 else ""
                else:
                    frac_str = "—"
                    pct = "—"
                    amt = "—（遺留分なし）"
                lg_rows.append([person.name, frac_str, pct, amt])

            lg_tbl = Table(lg_rows, colWidths=[45*mm, 30*mm, 25*mm, 50*mm])
            lg_tbl.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), font_name, 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8E44AD")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ]))
            story.append(lg_tbl)
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                "※ 遺留分は遺言の内容にかかわらず一定の相続人に最低限保障される取り分です。"
                "遺言書作成時はこの金額を侵害しないことが選択肢として考えられます。",
                s_caption,
            ))

    # ── 3. 相続税の概算 ──────────────────────────────────────────────
    if tax_info and total_assets_yen > 0:
        story.append(Paragraph("3. 相続税の概算（参考値）", s_heading))
        tax_rows = [
            ["項目", "金額"],
            ["相続財産総額",  f"¥{tax_info['total_assets']:,}"],
            ["基礎控除額",    f"¥{tax_info['basic_deduction']:,}"],
            ["課税遺産総額",  f"¥{tax_info['taxable_estate']:,}"],
            ["相続税概算",    f"¥{tax_info['estimated_tax']:,}"],
        ]
        tax_tbl = Table(tax_rows, colWidths=[75*mm, 75*mm])
        tax_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), font_name, 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tax_tbl)

        if tax_heir_info and tax_heir_info.get("note") and tax_heir_info["note"] != "養子なし":
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"<i>※ {tax_heir_info['note']}（相続税法15条2項）</i>",
                s_caption,
            ))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "※ 上記は概算値です。小規模宅地等の特例・配偶者控除・債務控除等により実際の税額は大きく異なります。",
            s_caption,
        ))

    # ── 4. 次のステップ ───────────────────────────────────────────────
    story.append(Paragraph("4. 次のステップ・専門家への相談", s_heading))
    story.append(Paragraph(
        "本シミュレーション結果は、専門家にご相談される際の参考資料としてご活用ください。"
        "一般的に以下の専門家への相談が選択肢として考えられます:",
        s_body,
    ))
    advice = [
        "・<b>税理士</b>: 相続税の正確な計算、各種特例の適用、申告手続き",
        "・<b>弁護士</b>: 遺産分割協議、遺留分侵害、遺言書作成のアドバイス",
        "・<b>司法書士</b>: 不動産の相続登記、戸籍収集等",
        "・<b>事業承継コンサルタント</b>: 自社株対策、後継者育成（自社株保有の場合）",
    ]
    for a in advice:
        story.append(Paragraph(a, s_body))

    # ── 免責 ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(Paragraph("免責事項", s_heading))
    story.append(Paragraph(
        "本書面の内容は、家系図Navi（相続・事業承継シミュレーター）が入力情報を基に"
        "機械的に算出した一般的なシミュレーション結果です。個別の事案における法的判断・"
        "税務判断は、必ず弁護士・税理士等の専門家にご相談ください。本書面の利用により"
        "生じたいかなる損害についても、開発者は責任を負いません。<br/><br/>"
        "本アプリは <b>弁護士法72条</b>（非弁護士による法律事務の取扱禁止）に抵触しないよう、"
        "特定事案への法律事務は一切行わない設計となっています。",
        s_body,
    ))

    doc.build(story)
    data = buf.getvalue()
    buf.close()
    return data


def _status_label(person) -> str:
    """人物の状態ラベル（表示用）"""
    if person.died_simultaneously:
        return "同時死亡"
    if not person.is_alive:
        return "故人"
    if person.is_renounced:
        return "存命・相続放棄"
    return "存命"
