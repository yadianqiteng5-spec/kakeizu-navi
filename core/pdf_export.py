"""
PDF出力モジュール

reportlab + 組み込み CID フォント（HeiseiKakuGo-W5）を使用するため、
外部の日本語フォントファイル不要で動作する。
"""
from io import BytesIO
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape as _xml_escape


def _esc(s) -> str:
    """reportlab Paragraph はミニHTML(<b>等)を解釈するため、ユーザー由来文字列の
    <,>,& を無害化し、氏名に記号が混入してもPDF生成が失敗しないようにする。"""
    return _xml_escape(str(s if s is not None else ""))


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
    small_land_info: Optional[dict] = None,
    secondary_info: Optional[dict] = None,
    gift_info: Optional[dict] = None,
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
        f"<b>被相続人:</b> {_esc(propositus.name)}（{birth}故人）",
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
            f"<b>配偶者:</b> {_esc(sp.name)}（{b}{status}）", s_body,
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
                f"　・{_esc(c.name)}（{b}{status}{adoption_label}）",
                s_body,
            ))
            if not c.is_alive:
                grandchildren = family_tree.get_children(cid)
                for gcid in grandchildren:
                    gc = family_tree.persons.get(gcid)
                    if gc and gc.is_alive and not gc.is_renounced:
                        bg = f"{gc.birth_year}年生・" if gc.birth_year else ""
                        story.append(Paragraph(
                            f"　　└ {_esc(gc.name)}（{bg}代襲相続人）", s_body,
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
            "※ 計算方式: 相続税法16条準拠の正規計算（法定相続分按分→速算表適用→合算）。"
            "国税庁公表の相続税速算表（8段階・速算控除額付き）を使用し、"
            "シンプルなケースでは国税庁シミュレーターと一致する精度で算出しています。"
            "ただし配偶者控除・小規模宅地等の特例・債務控除等の個別事情は反映されないため、"
            "正確な税額は税理士による精密試算が必要です。",
            s_caption,
        ))

    # ── 3-2. 小規模宅地等の特例 ──────────────────────────────────────
    if small_land_info and small_land_info.get("applicable"):
        story.append(Paragraph("3-2. 小規模宅地等の特例（租税特別措置法69条の4）", s_heading))
        story.append(Paragraph(small_land_info["rule"], s_body))
        sl_rows = [
            ["項目", "金額・割合"],
            ["減額前の評価額", f"¥{small_land_info.get('before', 0):,}"],
            ["減額割合",       f"{int(small_land_info['reduction_rate']*100)}%"],
            ["減額金額",       f"-¥{small_land_info['reduced_amount']:,}"],
            ["減額後の評価額",  f"¥{small_land_info['after_deduction']:,}"],
        ]
        sl_tbl = Table(sl_rows, colWidths=[75*mm, 75*mm])
        sl_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), font_name, 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16A085")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sl_tbl)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "※ 本特例には「相続開始前から居住・事業に使用」「相続後一定期間の継続利用」等の"
            "厳格な要件があります。適用可否は必ず税理士に確認してください。",
            s_caption,
        ))

    # ── 3-3. 二次相続シミュレーション ────────────────────────────────
    if secondary_info and secondary_info.get("scenarios"):
        story.append(Paragraph("3-3. 二次相続シミュレーション（相続税法19条の2）", s_heading))
        story.append(Paragraph(
            "配偶者が遺産を多く相続すると一次相続税は軽減されますが、"
            "配偶者死亡時（二次相続）の税負担が大きくなります。下記は配偶者取得割合別の比較です。",
            s_body,
        ))
        sec_rows = [["シナリオ", "配偶者取得額", "一次相続税", "二次相続税", "合計税額"]]
        for sc in secondary_info["scenarios"]:
            sec_rows.append([
                sc["label"],
                f"¥{sc['primary_spouse_amount']:,}",
                f"¥{sc['primary_tax']:,}",
                f"¥{sc['secondary_tax']:,}",
                f"¥{sc['total_tax']:,}",
            ])
        sec_tbl = Table(sec_rows, colWidths=[55*mm, 30*mm, 25*mm, 25*mm, 35*mm])
        sec_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), font_name, 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2980B9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (1, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EBF5FB")]),
        ]))
        story.append(sec_tbl)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<b>🏆 最も税負担が軽いシナリオ: {secondary_info['best_label']}</b>"
            f"（最大シナリオとの差額: ¥{secondary_info['best_savings']:,}）",
            s_body,
        ))
        story.append(Paragraph(
            "※ 配偶者の余命・物価変動・他の控除等を考慮した精密試算は税理士にご相談ください。",
            s_caption,
        ))

    # ── 3-4. 生前贈与シミュレーション ────────────────────────────────
    if gift_info and gift_info.get("total_gifted", 0) > 0:
        story.append(Paragraph("3-4. 生前贈与シミュレーション（相続税法21条の5～9）", s_heading))
        story.append(Paragraph(
            f"贈与総額: ¥{gift_info['total_gifted']:,}（"
            f"暦年贈与 vs 相続時精算課税の比較）",
            s_body,
        ))
        gift_rows = [
            ["戦略", "非課税枠", "贈与税", "節税効果", "正味節税額"],
            [
                "暦年贈与（年110万非課税）",
                f"¥{gift_info['annual']['tax_free_portion']:,}",
                f"¥{gift_info['annual']['taxable_gift_tax']:,}",
                f"¥{gift_info['annual']['inheritance_tax_saved']:,}",
                f"¥{gift_info['annual']['net_savings']:,}",
            ],
            [
                "相続時精算課税（2,500万非課税）",
                f"¥{gift_info['lump_sum_2500']['tax_free_portion']:,}",
                f"¥{gift_info['lump_sum_2500']['taxable_gift_tax']:,}",
                f"¥{gift_info['lump_sum_2500']['inheritance_tax_saved']:,}",
                f"¥{gift_info['lump_sum_2500']['net_savings']:,}",
            ],
        ]
        gift_tbl = Table(gift_rows, colWidths=[55*mm, 30*mm, 25*mm, 30*mm, 30*mm])
        gift_tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), font_name, 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E67E22")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (1, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(gift_tbl)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            gift_info.get("recommendation", ""),
            s_body,
        ))
        story.append(Paragraph(
            "※ 2024年改正で暦年贈与は相続開始前7年以内の贈与が持戻し対象。"
            "相続時精算課税は年110万円の新基礎控除（持戻し対象外）が新設されました。",
            s_caption,
        ))

    # ── 3-5. 国際相続の警告 ──────────────────────────────────────────
    story.append(Paragraph("3-5. 国際相続にご注意", s_heading))
    story.append(Paragraph(
        "本シミュレーションは<b>日本国内法</b>に基づく計算です。以下に該当する場合、"
        "外国の相続法・税制が併用適用される可能性があり、結果が大きく異なります:",
        s_body,
    ))
    intl = [
        "・被相続人または相続人に<b>外国籍</b>の方がいる",
        "・<b>海外に資産</b>（不動産・銀行口座・証券口座）がある",
        "・相続人が<b>海外に居住</b>している（日本の住所を有しない）",
        "・被相続人が<b>過去に海外居住歴</b>がある（10年以内）",
    ]
    for line in intl:
        story.append(Paragraph(line, s_body))
    story.append(Paragraph(
        "上記に該当する場合、<b>国際相続に詳しい弁護士・税理士</b>に必ずご相談ください。"
        "二重課税防止条約・準拠法の判断・海外資産の評価方法など、専門知識が不可欠です。",
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
