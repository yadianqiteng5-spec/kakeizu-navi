"""
日本民法に基づく法定相続分計算モジュール

対応するエッジケース:
- 無限代襲（直系卑属）— 子→孫→ひ孫…と続く
- 直系尊属の繰り上がり — 親が全員死亡なら祖父母が相続
- 兄弟姉妹の一代限り代襲 — 甥姪まで（民法889条2項）
- 半血兄弟姉妹 — 全血の1/2（民法900条4号但書）
- 相続放棄 — 放棄者は枝ごと除外（代襲も発生しない）
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
    children = ft.get_children(ancestor_id)
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
    current_generation: List[str] = list(ft.get_parents(propositus_id))
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
                next_generation.extend(ft.get_parents(pid))

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
    propositus_parents = set(ft.get_parents(propositus_id))

    info = []  # (sib_id, is_full_blood, is_alive, niece_ids)
    for sid in siblings:
        if sid not in ft.persons:
            continue
        s = ft.persons[sid]
        if s.is_renounced:
            continue

        s_parents = set(ft.get_parents(sid))
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
            # 兄弟姉妹の代襲は一代限り（甥姪まで）
            nieces = [
                n for n in ft.get_children(sid)
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

        direct_children = set(ft.get_children(propositus_id))
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
            for p in ft.get_parents(propositus_id)
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
        if spouse_share >= 0.5 and ft.get_children(propositus_id):
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
        for nid in ft.get_children(sid):
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

    direct_child_ids = set(ft.get_children(propositus_id))

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


def get_inheritance_tax_estimate(
    shares: Dict[str, Fraction],
    total_assets_yen: int,
    num_legal_heirs: int,
    num_tax_heirs: Optional[int] = None,
) -> dict:
    """
    相続税の概算（参考値）
    num_tax_heirs: 相続税法上の法定相続人数（養子算入制限適用後）。Noneの場合は num_legal_heirs を使用。
    """
    if num_tax_heirs is None:
        num_tax_heirs = num_legal_heirs
    basic_deduction = 30_000_000 + 6_000_000 * num_tax_heirs
    taxable_estate = max(0, total_assets_yen - basic_deduction)

    def rough_rate(amount: int) -> float:
        if amount <= 10_000_000:   return 0.10
        if amount <= 30_000_000:   return 0.15
        if amount <= 50_000_000:   return 0.20
        if amount <= 100_000_000:  return 0.30
        if amount <= 200_000_000:  return 0.40
        return 0.45

    estimated_tax = int(taxable_estate * rough_rate(taxable_estate))
    return {
        "total_assets": total_assets_yen,
        "basic_deduction": basic_deduction,
        "taxable_estate": taxable_estate,
        "estimated_tax": estimated_tax,
        "num_legal_heirs": num_legal_heirs,
        "num_tax_heirs": num_tax_heirs,
    }
