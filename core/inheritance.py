"""
日本民法に基づく法定相続分計算モジュール

対応するエッジケース:
- 無限代襲（直系卑属）— 子→孫→ひ孫…と続く
- 直系尊属の繰り上がり — 親が全員死亡なら祖父母が相続
- 兄弟姉妹の一代限り代襲 — 甥姪まで（民法889条2項）
- 半血兄弟姉妹 — 全血の1/2（民法900条4号但書）
- 相続放棄 — 放棄者は枝ごと除外（代襲も発生しない）
- 同時死亡推定 — 民法32条の2（互いに相続権なし、代襲は発生）
- 特別養子縁組 — 民法817条の9（実方との親族関係は終了）
"""
from fractions import Fraction
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────
# 内部ヘルパー: 順位別の相続人解決
# ─────────────────────────────────────────────────────────────────

def _resolve_descendants(
    ft, ancestor_id: str, total_share: Fraction
) -> Dict[str, Fraction]:
    """
    直系卑属に total_share を分配する（無限代襲対応）。
    放棄者は枝ごと除外（民法939条: 代襲も発生しない）。
    """
    children = ft.get_legal_children(ancestor_id)
    branches: List[Tuple[str, bool]] = []  # (child_id, is_living)

    for cid in children:
        if cid not in ft.persons:
            continue
        c = ft.persons[cid]
        if c.is_renounced:
            continue  # 放棄者: 枝ごと無視、代襲も発生しない
        if c.is_alive:
            branches.append((cid, True))
        else:
            # 死亡している子 — その子孫が生存していれば代襲が成立
            sub = _resolve_descendants(ft, cid, Fraction(1))
            if sub:
                branches.append((cid, False))

    if not branches:
        return {}

    per_branch = total_share / Fraction(len(branches))
    result: Dict[str, Fraction] = {}

    for cid, is_living in branches:
        if is_living:
            result[cid] = result.get(cid, Fraction(0)) + per_branch
        else:
            sub = _resolve_descendants(ft, cid, per_branch)
            for k, v in sub.items():
                result[k] = result.get(k, Fraction(0)) + v

    return result


def _resolve_ascendants(ft, propositus_id: str) -> List[str]:
    """
    直系尊属を取得（親等の近い者のみ）。
    親→祖父母→曾祖父母…と上に繰り上がる。
    """
    current_generation: List[str] = list(ft.get_legal_parents(propositus_id))
    visited: set = set()

    while current_generation:
        living = [
            p for p in current_generation
            if p in ft.persons and ft.persons[p].is_alive
            and not ft.persons[p].is_renounced
        ]
        if living:
            return list(dict.fromkeys(living))  # 重複除去 & 順序保持

        # この世代に生存者がいないので、次の上の世代へ
        next_generation: List[str] = []
        for pid in current_generation:
            if pid in visited:
                continue
            visited.add(pid)
            if pid in ft.persons:
                next_generation.extend(ft.get_legal_parents(pid))

        if not next_generation:
            return []
        current_generation = next_generation

    return []


def _resolve_siblings(
    ft, propositus_id: str, total_share: Fraction
) -> Tuple[Dict[str, Fraction], Dict[str, str]]:
    """
    兄弟姉妹の相続分を計算（半血は全血の1/2、代襲は甥姪まで）。
    Returns: (shares_dict, labels_dict)
    """
    siblings = ft.get_siblings(propositus_id)
    propositus_parents = set(ft.get_legal_parents(propositus_id))

    info = []  # (sib_id, is_full_blood, is_alive, niece_ids)
    for sid in siblings:
        if sid not in ft.persons:
            continue
        s = ft.persons[sid]
        if s.is_renounced:
            continue

        s_parents = set(ft.get_legal_parents(sid))
        common = propositus_parents & s_parents
        # 被相続人の親が2人登録されている場合のみ全血判定が可能
        # 共有親が2以上なら全血、1なら半血
        if len(propositus_parents) >= 2:
            is_full_blood = len(common) >= 2
        else:
            is_full_blood = True  # 判定不能の場合は全血として扱う

        if s.is_alive:
            info.append((sid, is_full_blood, True, None))
        else:
            # 兄弟姉妹の代襲は一代限り（甥姪まで・民法889条2項）
            nieces = [
                n for n in ft.get_legal_children(sid)
                if n in ft.persons and ft.persons[n].is_alive
                and not ft.persons[n].is_renounced
            ]
            if nieces:
                info.append((sid, is_full_blood, False, nieces))

    if not info:
        return {}, {}

    # 全血=2単位, 半血=1単位 で按分
    units = sum(2 if fb else 1 for _, fb, _, _ in info)
    if units == 0:
        return {}, {}

    shares: Dict[str, Fraction] = {}
    labels: Dict[str, str] = {}

    for sid, is_full_blood, is_alive, nieces in info:
        unit = 2 if is_full_blood else 1
        branch_share = total_share * Fraction(unit, units)
        blood_label = "" if is_full_blood else "（半血）"

        if is_alive:
            shares[sid] = branch_share
            labels[sid] = blood_label
        else:
            per_niece = branch_share / Fraction(len(nieces))
            sib_name = ft.persons[sid].name
            for n in nieces:
                shares[n] = per_niece
                labels[n] = f"（{sib_name}の代襲・甥姪{blood_label}）"

    return shares, labels


# ─────────────────────────────────────────────────────────────────
# メイン関数
# ─────────────────────────────────────────────────────────────────

def calculate_legal_shares(
    family_tree, propositus_id: str
) -> Tuple[Dict[str, Fraction], str]:
    """日本民法に基づく法定相続分を計算する"""
    ft = family_tree
    if propositus_id not in ft.persons:
        return {}, "被相続人が設定されていません"

    spouse_id = ft.get_spouse(propositus_id)
    has_spouse = (
        spouse_id is not None and spouse_id in ft.persons
        and ft.persons[spouse_id].is_alive
        and not ft.persons[spouse_id].is_renounced
    )

    shares: Dict[str, Fraction] = {}
    lines: List[str] = []

    # ── 第1順位: 直系卑属（無限代襲）────────────────────────────
    descendants_total = Fraction(1, 2) if has_spouse else Fraction(1)
    descendant_shares = _resolve_descendants(ft, propositus_id, descendants_total)

    if descendant_shares:
        rule = (
            "配偶者 1/2 ＋ 直系卑属（子・孫等）1/2"
            if has_spouse else "直系卑属（子・孫等）が全部相続"
        )
        if has_spouse:
            shares[spouse_id] = Fraction(1, 2)
            lines.append(f"配偶者 **{ft.persons[spouse_id].name}**: 1/2")

        direct_children = set(ft.get_legal_children(propositus_id))
        for hid, share in descendant_shares.items():
            shares[hid] = share
            name = ft.persons[hid].name
            suffix = "" if hid in direct_children else "（代襲相続）"
            lines.append(f"{name}{suffix}: {share}")

        return _build_result(shares, rule, lines)

    # ── 第2順位: 直系尊属（親→祖父母…と繰り上がり）────────────
    ascendants = _resolve_ascendants(ft, propositus_id)
    if ascendants:
        ascendants_total = Fraction(1, 3) if has_spouse else Fraction(1)
        rule = (
            "配偶者 2/3 ＋ 直系尊属 1/3"
            if has_spouse else "直系尊属が全部相続"
        )

        # 親世代に生存者がいるか確認（繰り上がり判定）
        parents_alive = any(
            p in ft.persons and ft.persons[p].is_alive
            and not ft.persons[p].is_renounced
            for p in ft.get_legal_parents(propositus_id)
        )
        level_label = "" if parents_alive else "（祖父母世代に繰上）"

        if has_spouse:
            shares[spouse_id] = Fraction(2, 3)
            lines.append(f"配偶者 **{ft.persons[spouse_id].name}**: 2/3")

        per_person = ascendants_total / Fraction(len(ascendants))
        for pid in ascendants:
            shares[pid] = per_person
            lines.append(f"{ft.persons[pid].name}{level_label}: {per_person}")

        return _build_result(shares, rule, lines)

    # ── 第3順位: 兄弟姉妹（半血対応、代襲は甥姪まで）──────────
    siblings_total = Fraction(1, 4) if has_spouse else Fraction(1)
    sibling_shares, sib_labels = _resolve_siblings(ft, propositus_id, siblings_total)

    if sibling_shares:
        rule = (
            "配偶者 3/4 ＋ 兄弟姉妹 1/4（全血:半血 = 2:1）"
            if has_spouse else "兄弟姉妹が全部相続（全血:半血 = 2:1）"
        )
        if has_spouse:
            shares[spouse_id] = Fraction(3, 4)
            lines.append(f"配偶者 **{ft.persons[spouse_id].name}**: 3/4")

        for hid, share in sibling_shares.items():
            shares[hid] = share
            suffix = sib_labels.get(hid, "")
            lines.append(f"{ft.persons[hid].name}{suffix}: {share}")

        return _build_result(shares, rule, lines)

    # ── 配偶者のみ／法定相続人なし ───────────────────────────
    if has_spouse:
        shares[spouse_id] = Fraction(1)
        rule = "配偶者が全部相続"
        lines.append(f"配偶者 **{ft.persons[spouse_id].name}**: 全部")
    else:
        rule = "法定相続人なし（特別縁故者または国庫帰属を検討してください）"

    return _build_result(shares, rule, lines)


def _build_result(shares, rule, lines):
    explanation = f"**適用ルール**: {rule}\n\n" + "\n\n".join(f"- {l}" for l in lines)
    return shares, explanation


# ─────────────────────────────────────────────────────────────────
# 補助関数
# ─────────────────────────────────────────────────────────────────

def format_shares_table(
    shares: Dict[str, Fraction], family_tree, total_assets_yen: int = 0
) -> List[dict]:
    rows = []
    for pid, frac in shares.items():
        p = family_tree.persons.get(pid)
        if not p:
            continue
        row: dict = {
            "氏名": p.name,
            "法定相続分": f"{frac.numerator}/{frac.denominator}",
            "割合": f"{float(frac)*100:.2f}%",
        }
        if total_assets_yen > 0:
            row["相続財産（円）"] = f"¥{int(float(frac) * total_assets_yen):,}"
        rows.append(row)
    return rows


def get_business_risks(family_tree, propositus_id: str) -> List[str]:
    """事業承継リスクのアラートリストを返す"""
    ft = family_tree
    propositus = ft.persons.get(propositus_id)
    risks: List[str] = []

    if not propositus or not propositus.has_business_shares:
        return risks

    shares, _ = calculate_legal_shares(ft, propositus_id)
    num_heirs = len(shares)

    if num_heirs >= 3:
        risks.append(
            f"⚠️ **自社株の分散リスク**: {num_heirs}名の相続人に株式が分散する可能性があります。"
            "経営権の集中を図るため、遺言書による株式の指定や、生前の持株会社設立を検討してください。"
        )
    elif num_heirs == 2:
        risks.append(
            "⚠️ **自社株の共有リスク**: 複数の相続人が株式を共有すると、経営上の意思決定が困難になる場合があります。"
        )

    spouse_id = ft.get_spouse(propositus_id)
    if spouse_id and spouse_id in shares:
        spouse_share = float(shares[spouse_id])
        if spouse_share >= 0.5 and ft.get_legal_children(propositus_id):
            risks.append(
                "⚠️ **配偶者への株式集中**: 配偶者が50%以上の株式を相続すると、"
                "後継者（子）の経営権が不安定になるリスクがあります。後継者への集中策を検討してください。"
            )

    risks.append(
        "ℹ️ **非上場株式の評価**: 非上場株式は相続税の計算において、"
        "純資産価額方式・類似業種比準方式等で評価されます。事前に税理士による試算をお勧めします。"
    )
    return risks


def calculate_legitimes(family_tree, propositus_id: str) -> dict:
    """
    遺留分（民法1042条以下）を計算する。

    総体的遺留分:
      - 直系卑属 または 配偶者 がいる場合: 1/2
      - 直系尊属のみ（配偶者なし）の場合: 1/3
      - 兄弟姉妹（およびその代襲）のみの場合: 0（遺留分権利者ではない）

    個別的遺留分: 法定相続分 × 総体的遺留分（兄弟姉妹を除く）

    Returns: {
        "individual": {heir_id: Fraction},  # 各人の個別遺留分（兄弟は0）
        "overall": Fraction,                # 総体的遺留分（0 = 遺留分なし）
        "rule": str,                        # 適用ルール説明
        "has_legitime": bool,               # 遺留分が発生する相続人がいるか
    }
    """
    ft = family_tree
    shares, _ = calculate_legal_shares(ft, propositus_id)
    if not shares:
        return {
            "individual": {}, "overall": Fraction(0),
            "rule": "相続人なし", "has_legitime": False,
        }

    spouse_id = ft.get_spouse(propositus_id)
    has_spouse_in_shares = spouse_id in shares

    # 第1順位（直系卑属）が成立しているか
    has_descendants = bool(_resolve_descendants(ft, propositus_id, Fraction(1)))
    # 第2順位（直系尊属）が成立しているか
    has_ascendants_only = (not has_descendants) and bool(_resolve_ascendants(ft, propositus_id))

    # 総体的遺留分の決定
    if has_descendants or has_spouse_in_shares:
        # 配偶者または直系卑属が相続人 → 1/2
        overall = Fraction(1, 2)
        if has_descendants and has_spouse_in_shares:
            rule = "配偶者または直系卑属がいるため、総体的遺留分は **1/2**"
        elif has_descendants:
            rule = "直系卑属がいるため、総体的遺留分は **1/2**"
        else:
            rule = "配偶者がいるため、総体的遺留分は **1/2**"
    elif has_ascendants_only:
        # 直系尊属のみ → 1/3
        overall = Fraction(1, 3)
        rule = "直系尊属のみが相続人のため、総体的遺留分は **1/3**"
    else:
        # 兄弟姉妹のみ
        return {
            "individual": {hid: Fraction(0) for hid in shares},
            "overall": Fraction(0),
            "rule": "兄弟姉妹（およびその代襲）のみが相続人のため、**遺留分は発生しません**",
            "has_legitime": False,
        }

    # 個別遺留分（兄弟姉妹・甥姪は0）
    siblings = set(ft.get_siblings(propositus_id))
    niece_nephew = set()
    for sid in siblings:
        for nid in ft.get_legal_children(sid):
            niece_nephew.add(nid)

    individual: dict = {}
    for hid, share in shares.items():
        if hid in siblings or hid in niece_nephew:
            individual[hid] = Fraction(0)
        else:
            individual[hid] = share * overall

    return {
        "individual": individual,
        "overall": overall,
        "rule": rule,
        "has_legitime": any(v > 0 for v in individual.values()),
    }


def count_tax_legal_heirs(family_tree, propositus_id: str) -> dict:
    """
    相続税法15条2項に基づく「相続税の基礎控除算定上の法定相続人数」を計算する。

    養子の算入制限:
      - 被相続人に実子がいる場合: 養子は1名まで算入
      - 被相続人に実子がいない場合: 養子は2名まで算入
      - 特別養子・配偶者の連れ子養子・代襲相続人の養子はこの制限を受けず全員算入

    Returns: {
      "total": int,           # 控除算定に使う法定相続人数
      "biological": int,      # 算入された実子数
      "adopted_counted": int, # 算入された養子数
      "adopted_excluded": int,# 算入されなかった養子数
      "note": str,            # 算定の説明
    }
    """
    ft = family_tree
    shares, _ = calculate_legal_shares(ft, propositus_id)

    direct_child_ids = set(ft.get_legal_children(propositus_id))

    bio_children_in_heirs = 0
    adopted_children_in_heirs = 0
    other_heirs = 0

    for heir_id in shares:
        if heir_id in direct_child_ids:
            adoption = ft.get_adoption_type(propositus_id, heir_id)
            if adoption == "biological":
                bio_children_in_heirs += 1
            else:
                adopted_children_in_heirs += 1
        else:
            # 配偶者・親・兄弟・代襲相続人など
            other_heirs += 1

    # 養子算入制限
    if bio_children_in_heirs > 0:
        max_adopted = 1
    else:
        max_adopted = 2
    adopted_counted = min(adopted_children_in_heirs, max_adopted)
    adopted_excluded = adopted_children_in_heirs - adopted_counted

    total = bio_children_in_heirs + adopted_counted + other_heirs

    note_parts = []
    if adopted_excluded > 0:
        note_parts.append(
            f"養子 {adopted_children_in_heirs}名のうち {adopted_counted}名のみを算入"
            f"（相続税法15条2項により、実子{'あり' if bio_children_in_heirs > 0 else 'なし'}のため上限{max_adopted}名）"
        )
    elif adopted_children_in_heirs > 0:
        note_parts.append(f"養子 {adopted_children_in_heirs}名は全員算入")

    return {
        "total": total,
        "biological": bio_children_in_heirs,
        "adopted_counted": adopted_counted,
        "adopted_excluded": adopted_excluded,
        "other": other_heirs,
        "note": " / ".join(note_parts) if note_parts else "養子なし",
    }


# ─────────────────────────────────────────────────────────────────
# 相続税の正規計算ロジック（相続税法16条準拠）
# ─────────────────────────────────────────────────────────────────
#
# 速算表（国税庁公表・各取得金額ごとの税率と速算控除額）
# 「各法定相続人が法定相続分どおり取得した」と仮定した取得金額に適用する
INHERITANCE_TAX_BRACKETS = [
    # (上限額, 税率, 速算控除額)
    (10_000_000,   0.10,         0),
    (30_000_000,   0.15,   500_000),
    (50_000_000,   0.20, 2_000_000),
    (100_000_000,  0.30, 7_000_000),
    (200_000_000,  0.40, 17_000_000),
    (300_000_000,  0.45, 27_000_000),
    (600_000_000,  0.50, 42_000_000),
    (float("inf"), 0.55, 72_000_000),
]


def _inheritance_tax_per_bracket(taxable_share: int) -> int:
    """法定相続分按分後の各人取得分に税率表を適用（速算控除額を差し引く）"""
    if taxable_share <= 0:
        return 0
    for limit, rate, deduction in INHERITANCE_TAX_BRACKETS:
        if taxable_share <= limit:
            return max(0, int(taxable_share * rate - deduction))
    return 0


def _calculate_inheritance_tax_total(
    taxable_estate: int, num_legal_heirs: int
) -> int:
    """
    均等按分版（相続人がそれぞれ均等な相続分を持つケース：子のみ・兄弟のみ等）。
    配偶者+子の標準パターンには _calculate_inheritance_tax_with_spouse_pattern を使うこと。
    """
    if taxable_estate <= 0 or num_legal_heirs <= 0:
        return 0
    per_heir_share = taxable_estate // num_legal_heirs
    per_heir_tax = _inheritance_tax_per_bracket(per_heir_share)
    return per_heir_tax * num_legal_heirs


def _calculate_inheritance_tax_with_spouse_pattern(
    taxable_estate: int, num_children: int
) -> int:
    """
    配偶者+子の標準パターンで「相続税の総額」を正確に計算する。
    配偶者: 1/2、子: 残り1/2を均等按分（民法900条1号）。
    num_children=0 の場合は配偶者のみ（全額相続）として扱う。
    """
    if taxable_estate <= 0:
        return 0
    if num_children <= 0:
        # 配偶者のみが相続人 → 配偶者が全額取得
        return _inheritance_tax_per_bracket(taxable_estate)
    spouse_share = taxable_estate // 2
    spouse_tax = _inheritance_tax_per_bracket(spouse_share)
    child_share = (taxable_estate - spouse_share) // num_children
    child_tax = _inheritance_tax_per_bracket(child_share)
    return spouse_tax + child_tax * num_children


def _calculate_total_tax_from_shares(
    taxable_estate: int, shares: Dict[str, Fraction]
) -> int:
    """
    任意の法定相続分（shares）に従って課税遺産を按分し、相続税の総額を算出する。
    相続税法16条準拠: 法定相続分どおりに取得したと仮定 → 各人の税率適用 → 合算

    これにより以下のすべてのパターンを正確に計算できる:
    - 配偶者+子: 1/2 : 1/2÷N
    - 配偶者+直系尊属: 2/3 : 1/3÷N
    - 配偶者+兄弟姉妹: 3/4 : 1/4÷N（半血含む）
    - 配偶者のみ: 1
    - 子のみ・直系尊属のみ・兄弟のみ: 均等
    """
    if taxable_estate <= 0 or not shares:
        return 0
    total = 0
    for _, frac in shares.items():
        person_share = int(taxable_estate * float(frac))
        total += _inheritance_tax_per_bracket(person_share)
    return total


def calculate_secondary_inheritance(
    primary_total_yen: int,
    num_children: int,
    spouse_own_assets_yen: int = 0,
) -> dict:
    """
    二次相続（配偶者死亡時）の税負担を、一次相続での配偶者取得割合別に比較する。

    一次相続の配偶者控除（相続税法19条の2）:
      配偶者の取得財産が「法定相続分」または「1億6,000万円」のいずれか多い方まで非課税。

    Args:
        primary_total_yen: 一次相続の財産総額（被相続人の遺産）
        num_children: 子の人数（二次相続の相続人）
        spouse_own_assets_yen: 配偶者の固有財産（二次相続で加算される）

    Returns:
        {
          "scenarios": [
            {
              "label": "配偶者0%取得", "spouse_ratio": 0.0,
              "primary_spouse_amount": 0, "primary_tax": int,
              "secondary_total": int, "secondary_tax": int,
              "total_tax": int,
            }, ...3パターン
          ],
          "best_label": str,  # 合計税額が最小のラベル
          "best_savings": int, # 最大-最小
        }
    """
    if primary_total_yen <= 0 or num_children <= 0:
        return {"scenarios": [], "best_label": "", "best_savings": 0}

    SPOUSE_DEDUCTION_FLOOR = 160_000_000  # 配偶者控除の下限（1億6,000万円）

    # ── 一次相続の前提計算（全シナリオ共通）─────────────────────────
    n_primary_heirs = 1 + num_children  # 配偶者+子
    primary_basic = 30_000_000 + 6_000_000 * n_primary_heirs
    primary_taxable_estate = max(0, primary_total_yen - primary_basic)

    # 「相続税の総額」は法定相続分按分（配偶者1/2、子で残り1/2均等）で計算
    primary_total_tax = _calculate_inheritance_tax_with_spouse_pattern(
        primary_taxable_estate, num_children
    )

    # 配偶者控除の上限額（取得財産ベース）: max(法定相続分=1/2, 1.6億)
    spouse_legal_share = primary_total_yen // 2
    spouse_deduction_amount = max(spouse_legal_share, SPOUSE_DEDUCTION_FLOOR)

    scenarios = []
    for label, ratio in [
        ("配偶者0%取得（子に全部）", 0.0),
        ("配偶者法定相続分（1/2）取得", 0.5),
        ("配偶者100%取得（最大限活用）", 1.0),
    ]:
        spouse_amt = int(primary_total_yen * ratio)

        # ── 一次相続税の按分（相続税法17条）─────────────────
        # 各人の納付税額 = 相続税の総額 × (各人の取得財産 / 課税価格の合計)
        if primary_total_yen > 0 and primary_total_tax > 0:
            spouse_tax_before_deduction = (
                primary_total_tax * spouse_amt // primary_total_yen
            )
        else:
            spouse_tax_before_deduction = 0

        # ── 配偶者控除の適用（相続税法19条の2）──────────────
        # 控除額 = 相続税の総額 × min(配偶者取得財産, 控除上限) / 課税価格合計
        if primary_total_yen > 0:
            deductible_base = min(spouse_amt, spouse_deduction_amount)
            spouse_tax_credit = (
                primary_total_tax * deductible_base // primary_total_yen
            )
        else:
            spouse_tax_credit = 0

        # 配偶者の実際納付税額（控除適用後）
        spouse_tax_after = max(0, spouse_tax_before_deduction - spouse_tax_credit)
        # 子の納付税額合計
        children_tax = primary_total_tax - spouse_tax_before_deduction
        primary_tax = spouse_tax_after + children_tax

        # ── 二次相続: 配偶者の固有財産 + 一次取得分を子で相続 ──
        secondary_total = spouse_amt + spouse_own_assets_yen
        secondary_basic = 30_000_000 + 6_000_000 * num_children
        secondary_taxable = max(0, secondary_total - secondary_basic)
        secondary_tax = _calculate_inheritance_tax_total(
            secondary_taxable, num_children
        )

        scenarios.append({
            "label": label,
            "spouse_ratio": ratio,
            "primary_spouse_amount": spouse_amt,
            "primary_tax": max(0, primary_tax),
            "secondary_total": secondary_total,
            "secondary_tax": secondary_tax,
            "total_tax": max(0, primary_tax) + secondary_tax,
        })

    totals = [s["total_tax"] for s in scenarios]
    best_idx = totals.index(min(totals))
    return {
        "scenarios": scenarios,
        "best_label": scenarios[best_idx]["label"],
        "best_savings": max(totals) - min(totals),
    }


def compare_gift_strategies(
    annual_amount_yen: int,
    years: int,
    num_recipients: int,
    estimated_marginal_rate: float = 0.20,
) -> dict:
    """
    生前贈与の節税効果を比較する。

    暦年贈与（相続税法21条の5～）:
      年110万円までは非課税。受贈者1人あたり年間110万円。
      ただし2024年以降は相続開始前7年以内の贈与は相続財産に持戻し（旧3年→7年）。

    相続時精算課税（相続税法21条の9～）:
      累計2,500万円までは贈与税非課税、超過分は一律20%。
      ただし相続時に全額が相続財産に持戻し（節税効果は限定的）。

    Args:
        annual_amount_yen: 1人あたり年間贈与額
        years: 贈与年数
        num_recipients: 受贈者の人数
        estimated_marginal_rate: 推定される相続税の限界税率（0.0〜0.55）

    Returns:
        {
          "annual_exempt_yen": 1_100_000,
          "total_gifted": int,
          "annual": { "tax_free_portion": int, "taxable_gift_tax": int, "inheritance_tax_saved": int, "net_savings": int },
          "lump_sum_2500": { "tax_free_portion": int, "taxable_gift_tax": int, "inheritance_tax_saved": int, "net_savings": int, "note": str },
          "recommendation": str,
        }
    """
    ANNUAL_EXEMPT = 1_100_000  # 年110万円
    LUMP_EXEMPT = 25_000_000   # 相続時精算課税2,500万円
    total_gifted = annual_amount_yen * years * num_recipients

    # ── 暦年贈与シナリオ ──────────────────────────────────────
    tax_free_per_year_per_person = min(annual_amount_yen, ANNUAL_EXEMPT)
    annual_tax_free_total = tax_free_per_year_per_person * years * num_recipients
    annual_taxable = max(0, total_gifted - annual_tax_free_total)

    # 贈与税（特例税率: 直系尊属→18歳以上の子・孫への贈与、国税庁公表値）
    # ※ 一般贈与財産用の税率もあるが、相続対策では通常こちらが適用される
    def _gift_tax_special(taxable_per_year: int) -> int:
        if taxable_per_year <= 0: return 0
        # (上限額, 税率, 速算控除額)
        brackets = [
            (2_000_000,    0.10,         0),
            (4_000_000,    0.15,   100_000),
            (6_000_000,    0.20,   300_000),
            (10_000_000,   0.30,   900_000),
            (15_000_000,   0.40, 1_900_000),
            (30_000_000,   0.45, 2_650_000),
            (45_000_000,   0.50, 4_150_000),
            (float("inf"), 0.55, 6_400_000),
        ]
        for limit, rate, deduction in brackets:
            if taxable_per_year <= limit:
                return max(0, int(taxable_per_year * rate - deduction))
        return 0
    _gift_tax_general = _gift_tax_special  # エイリアス（後方互換）

    annual_excess_per_year = max(0, annual_amount_yen - ANNUAL_EXEMPT)
    annual_gift_tax = (
        _gift_tax_general(annual_excess_per_year) * years * num_recipients
    )
    # 注: 2024年改正により相続開始前7年以内の贈与は相続財産に持戻し対象
    # （ただし4-7年前の贈与は合計100万円まで持戻し対象外）。
    # 厳密には贈与開始年と相続発生年の関係で持戻し額が変動するが、
    # 本シミュレーションでは「7年超前の贈与のみ節税効果あり」として概算する。
    if years > 7:
        effective_gifted = annual_amount_yen * (years - 7) * num_recipients
    else:
        # 全期間が持戻し対象の場合、効果はほぼゼロ（100万円控除のみ）
        effective_gifted = max(0, total_gifted - 1_000_000 * num_recipients)
    annual_inheritance_saved = int(effective_gifted * estimated_marginal_rate)
    annual_net = annual_inheritance_saved - annual_gift_tax

    # ── 相続時精算課税シナリオ ──────────────────────────────
    lump_total_per_person = annual_amount_yen * years
    lump_taxfree_per_person = min(lump_total_per_person, LUMP_EXEMPT)
    lump_taxable_per_person = max(0, lump_total_per_person - LUMP_EXEMPT)
    lump_gift_tax = int(lump_taxable_per_person * 0.20) * num_recipients

    # 相続時精算課税は基本的に「贈与しても全額相続財産に持戻し」のため節税効果は限定的
    # ただし2024年改正で年110万円の基礎控除が新設（持戻し対象外）
    lump_basic_deduction = ANNUAL_EXEMPT * years * num_recipients  # 新基礎控除
    lump_inheritance_saved = int(
        min(lump_basic_deduction, total_gifted) * estimated_marginal_rate
    )
    lump_net = lump_inheritance_saved - lump_gift_tax

    # ── 推奨判定 ──────────────────────────────────────────
    if annual_net > lump_net:
        recommendation = (
            f"💡 **暦年贈与が有利**（差額: {(annual_net - lump_net):,}円）。"
            f"年110万円以内なら贈与税ゼロで {annual_inheritance_saved:,}円 の節税効果が"
            f"期待できます。ただし2024年改正で相続開始前7年以内の贈与は持戻し対象です。"
        )
    elif lump_net > annual_net:
        recommendation = (
            f"💡 **相続時精算課税が有利**（差額: {(lump_net - annual_net):,}円）。"
            f"2024年改正で年110万円の基礎控除が新設され、暦年贈与より有利になるケースが増えました。"
        )
    else:
        recommendation = "💡 両者ほぼ同等。受贈者の年齢・将来の生前贈与計画で選択してください。"

    return {
        "annual_exempt_yen": ANNUAL_EXEMPT,
        "total_gifted": total_gifted,
        "annual": {
            "tax_free_portion": annual_tax_free_total,
            "taxable_gift_tax": annual_gift_tax,
            "inheritance_tax_saved": annual_inheritance_saved,
            "net_savings": annual_net,
        },
        "lump_sum_2500": {
            "tax_free_portion": lump_taxfree_per_person * num_recipients,
            "taxable_gift_tax": lump_gift_tax,
            "inheritance_tax_saved": lump_inheritance_saved,
            "net_savings": lump_net,
            "note": "2024年改正で年110万円の基礎控除（持戻し対象外）が新設",
        },
        "recommendation": recommendation,
    }


def calculate_small_residential_deduction(
    land_type: str,
    land_value_yen: int,
    area_sqm: float,
) -> dict:
    """
    小規模宅地等の特例（租税特別措置法69条の4）の減額を概算する。

    Args:
        land_type: "residential"（特定居住用）/ "business"（特定事業用）/
                   "rental"（貸付事業用）/ "none"（適用なし）
        land_value_yen: 宅地の相続税評価額（円）
        area_sqm: 宅地の面積（㎡）

    Returns:
        {
          "applicable": bool,
          "limit_sqm": float,        # 適用面積の上限
          "reduction_rate": float,   # 減額割合
          "reduced_amount": int,     # 減額される金額
          "after_deduction": int,    # 特例適用後の評価額
          "rule": str,               # 適用ルール説明
        }
    """
    config = {
        "residential": (330.0, 0.80, "特定居住用宅地等: 330㎡まで80%減額"),
        "business":    (400.0, 0.80, "特定事業用宅地等: 400㎡まで80%減額"),
        "rental":      (200.0, 0.50, "貸付事業用宅地等: 200㎡まで50%減額"),
    }
    if land_type not in config or land_value_yen <= 0 or area_sqm <= 0:
        return {
            "applicable": False, "limit_sqm": 0.0, "reduction_rate": 0.0,
            "reduced_amount": 0, "after_deduction": land_value_yen,
            "rule": "適用なし",
        }

    limit_sqm, rate, rule = config[land_type]
    # 上限面積を超える部分には適用しない
    eligible_ratio = min(area_sqm, limit_sqm) / area_sqm
    eligible_value = land_value_yen * eligible_ratio
    reduced = int(eligible_value * rate)
    after = land_value_yen - reduced

    return {
        "applicable": True,
        "limit_sqm": limit_sqm,
        "reduction_rate": rate,
        "reduced_amount": reduced,
        "after_deduction": after,
        "rule": rule,
    }


def get_inheritance_tax_estimate(
    shares: Dict[str, Fraction],
    total_assets_yen: int,
    num_legal_heirs: int,
    num_tax_heirs: Optional[int] = None,
) -> dict:
    """
    相続税の概算（相続税法16条準拠の正規計算ロジック）

    手順:
    1. 課税遺産総額 = 課税価格 - 基礎控除（3,000万 + 600万×法定相続人数）
    2. 法定相続人が法定相続分どおりに取得したと仮定して按分
    3. 各人の取得分に速算表を適用して個別税額を算出
    4. 合算して「相続税の総額」とする（配偶者控除は本関数では適用しない）

    num_tax_heirs: 相続税法上の法定相続人数（養子算入制限適用後）
    """
    if num_tax_heirs is None:
        num_tax_heirs = num_legal_heirs
    basic_deduction = 30_000_000 + 6_000_000 * num_tax_heirs
    taxable_estate = max(0, total_assets_yen - basic_deduction)

    # 正規計算: 実際の法定相続分（shares）に従って按分 → 各人税率 → 合算
    # shares が空の場合（法定相続人なし）は均等按分にフォールバック
    if shares:
        estimated_tax = _calculate_total_tax_from_shares(taxable_estate, shares)
    else:
        estimated_tax = _calculate_inheritance_tax_total(taxable_estate, num_tax_heirs)

    return {
        "total_assets": total_assets_yen,
        "basic_deduction": basic_deduction,
        "taxable_estate": taxable_estate,
        "estimated_tax": estimated_tax,
        "num_legal_heirs": num_legal_heirs,
        "num_tax_heirs": num_tax_heirs,
    }
