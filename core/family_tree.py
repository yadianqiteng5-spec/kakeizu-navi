from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import uuid


class Gender(str, Enum):
    MALE = "男性"
    FEMALE = "女性"
    UNKNOWN = "不明"


@dataclass
class Person:
    id: str
    name: str
    gender: Gender = Gender.UNKNOWN
    birth_year: Optional[int] = None
    is_alive: bool = True             # False = 故人
    is_propositus: bool = False       # 被相続人
    assets_yen: int = 0
    has_business_shares: bool = False
    is_renounced: bool = False         # 相続放棄
    died_simultaneously: bool = False  # 被相続人と同時死亡（民法32条の2推定）
    notes: str = ""

    def __post_init__(self):
        # 同時死亡推定 → 自動的に「故人」扱い
        if self.died_simultaneously:
            self.is_alive = False


# 養子区分（民法・相続税法での扱い）
# - "biological": 実子（生物学的な親子）
# - "regular_adoption": 普通養子（実親・養親いずれからも相続可）
# - "special_adoption": 特別養子（実親との関係は終了、養親のみ）
ADOPTION_TYPES = ("biological", "regular_adoption", "special_adoption")
ADOPTION_LABELS = {
    "biological": "実子",
    "regular_adoption": "普通養子",
    "special_adoption": "特別養子",
}


@dataclass
class Relationship:
    person1_id: str
    person2_id: str
    rel_type: str  # "spouse" | "parent_child"
    adoption_type: str = "biological"  # parent_child の場合のみ意味を持つ


class FamilyTree:
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.relationships: List[Relationship] = []

    # ── CRUD ─────────────────────────────────────────────

    def add_person(
        self,
        name: str,
        gender: Gender = Gender.UNKNOWN,
        birth_year: Optional[int] = None,
        is_alive: bool = True,
        is_propositus: bool = False,
        assets_yen: int = 0,
        has_business_shares: bool = False,
        is_renounced: bool = False,
        died_simultaneously: bool = False,
        notes: str = "",
    ) -> str:
        pid = str(uuid.uuid4())[:8]
        self.persons[pid] = Person(
            id=pid, name=name, gender=gender, birth_year=birth_year,
            is_alive=is_alive, is_propositus=is_propositus,
            assets_yen=assets_yen, has_business_shares=has_business_shares,
            is_renounced=is_renounced,
            died_simultaneously=died_simultaneously,
            notes=notes,
        )
        return pid

    def add_spouse(self, person1_id: str, person2_id: str):
        self.relationships.append(Relationship(person1_id, person2_id, "spouse"))

    def add_parent_child(
        self,
        parent_id: str,
        child_id: str,
        adoption_type: str = "biological",
    ):
        self.relationships.append(Relationship(
            parent_id, child_id, "parent_child",
            adoption_type=adoption_type,
        ))

    def get_adoption_type(self, parent_id: str, child_id: str) -> str:
        """指定された親子関係の養子区分を返す（存在しなければ 'biological'）"""
        for r in self.relationships:
            if (r.rel_type == "parent_child"
                and r.person1_id == parent_id
                and r.person2_id == child_id):
                return getattr(r, "adoption_type", "biological")
        return "biological"

    def remove_person(self, person_id: str):
        self.persons.pop(person_id, None)
        self.relationships = [
            r for r in self.relationships
            if r.person1_id != person_id and r.person2_id != person_id
        ]

    # ── クエリ ───────────────────────────────────────────

    def get_spouse(self, person_id: str) -> Optional[str]:
        for r in self.relationships:
            if r.rel_type == "spouse":
                if r.person1_id == person_id:
                    return r.person2_id
                if r.person2_id == person_id:
                    return r.person1_id
        return None

    def get_children(self, person_id: str) -> List[str]:
        return [r.person2_id for r in self.relationships
                if r.rel_type == "parent_child" and r.person1_id == person_id]

    def get_parents(self, person_id: str) -> List[str]:
        return [r.person1_id for r in self.relationships
                if r.rel_type == "parent_child" and r.person2_id == person_id]

    def get_siblings(self, person_id: str) -> List[str]:
        parents = self.get_legal_parents(person_id)
        siblings: set = set()
        for pid in parents:
            for cid in self.get_legal_children(pid):
                if cid != person_id:
                    siblings.add(cid)
        return list(siblings)

    # ── 民法上の親族関係（特別養子縁組による断絶を考慮）─────────────────────
    # 民法817条の9: 特別養子と実方の父母及びその血族との親族関係は終了する

    def _has_special_adoption_parent(self, child_id: str) -> bool:
        """この子に特別養子の養親が存在するか"""
        return any(
            r.rel_type == "parent_child" and r.person2_id == child_id
            and getattr(r, "adoption_type", "biological") == "special_adoption"
            for r in self.relationships
        )

    def get_legal_parents(self, person_id: str) -> List[str]:
        """
        民法上の親（相続権が発生する親）を返す。
        - 特別養子の場合: 養親のみ（実親は除外）
        - それ以外: すべての親（実親＋普通養子の養親）
        """
        if self._has_special_adoption_parent(person_id):
            return [
                r.person1_id for r in self.relationships
                if r.rel_type == "parent_child" and r.person2_id == person_id
                and getattr(r, "adoption_type", "biological") == "special_adoption"
            ]
        return self.get_parents(person_id)

    def get_legal_children(self, person_id: str) -> List[str]:
        """
        民法上の子（相続権が発生する子）を返す。
        - 実親としての関係でも、その子が他者に特別養子として迎えられた場合は除外
        - 普通養子はそのまま含む
        """
        result: List[str] = []
        for r in self.relationships:
            if r.rel_type != "parent_child" or r.person1_id != person_id:
                continue
            child_id = r.person2_id
            adoption = getattr(r, "adoption_type", "biological")

            if adoption == "special_adoption":
                # 自分が特別養子の養親 → 完全な親子関係
                result.append(child_id)
            elif adoption == "regular_adoption":
                # 普通養子 → 親子関係あり（実親との関係も残存）
                result.append(child_id)
            else:
                # 実親関係: その子が他者の特別養子になっていたら断絶
                if not self._has_special_adoption_parent(child_id):
                    result.append(child_id)
                # else: 実子だが他者の特別養子 → 民法817条の9により断絶
        return result

    def get_propositus(self) -> Optional[str]:
        for pid, p in self.persons.items():
            if p.is_propositus:
                return pid
        return None

    def is_empty(self) -> bool:
        return len(self.persons) == 0

    def summary(self) -> str:
        if self.is_empty():
            return "家族情報なし"
        parts = []
        for pid, p in self.persons.items():
            desc = p.name
            tags = []
            if p.is_propositus:
                tags.append("被相続人・故人")
            elif not p.is_alive:
                tags.append("故人")
            if p.is_renounced:
                tags.append("相続放棄")
            if tags:
                desc += f"（{'・'.join(tags)}）"

            rels = []
            spouse_id = self.get_spouse(pid)
            if spouse_id and spouse_id in self.persons:
                rels.append(f"配偶者:{self.persons[spouse_id].name}")
            children = self.get_children(pid)
            if children:
                names = [self.persons[c].name for c in children if c in self.persons]
                rels.append(f"子:{', '.join(names)}")
            if rels:
                desc += f"［{'; '.join(rels)}］"
            parts.append(desc)
        return "、".join(parts)

    # ── 可視化 ───────────────────────────────────────────

    def to_dot(self) -> str:
        propositus_id = self.get_propositus()
        lines = [
            "digraph family {",
            "  rankdir=TB;",
            "  node [style=filled, shape=box, fontsize=11];",
            "  graph [splines=ortho];",
        ]
        for pid, p in self.persons.items():
            if p.gender == Gender.MALE:
                color = "#AED6F1"
            elif p.gender == Gender.FEMALE:
                color = "#F9C0D0"
            else:
                color = "#FDEBD0"
            if not p.is_alive:
                color = "#BDC3C7"
            if pid == propositus_id:
                color = "#F9E79F"
            if p.is_renounced:
                color = "#E8DAEF"

            extra = ", penwidth=3" if pid == propositus_id else ""
            label_parts = [p.name]
            if p.birth_year:
                label_parts.append(f"{p.birth_year}年生")
            if p.died_simultaneously:
                label_parts.append("(同時死亡)")
            elif not p.is_alive:
                label_parts.append("(故人)")
            if p.is_renounced:
                label_parts.append("[相続放棄]")
            if p.is_propositus:
                label_parts.append("★被相続人")
            label = "\\n".join(label_parts)
            lines.append(f'  "{pid}" [label="{label}", fillcolor="{color}"{extra}];')

        rendered_spouse: set = set()
        for r in self.relationships:
            if r.rel_type == "spouse":
                pair = tuple(sorted([r.person1_id, r.person2_id]))
                if pair not in rendered_spouse:
                    rendered_spouse.add(pair)
                    lines.append(
                        f'  "{r.person1_id}" -> "{r.person2_id}"'
                        f' [dir=none, style=bold, color="#E74C3C"];'
                    )
            elif r.rel_type == "parent_child":
                adoption = getattr(r, "adoption_type", "biological")
                if adoption == "regular_adoption":
                    lines.append(
                        f'  "{r.person1_id}" -> "{r.person2_id}"'
                        f' [label="養子", color="#9B59B6", fontcolor="#9B59B6"];'
                    )
                elif adoption == "special_adoption":
                    lines.append(
                        f'  "{r.person1_id}" -> "{r.person2_id}"'
                        f' [label="特別養子", color="#9B59B6", fontcolor="#9B59B6", style=dashed];'
                    )
                else:
                    lines.append(f'  "{r.person1_id}" -> "{r.person2_id}";')
        lines.append("}")
        return "\n".join(lines)

    # ── デモデータ ────────────────────────────────────────

    @classmethod
    def create_demo(cls) -> "FamilyTree":
        """
        代襲相続を含む標準的な家族構成のデモデータ。
        被相続人の次男が先に死亡しており、その子（孫）が代襲相続人となる。
        """
        ft = cls()
        demo_persons = [
            Person(id="p_taro",   name="山田太郎", gender=Gender.MALE,   birth_year=1945,
                   is_alive=False, is_propositus=True,
                   assets_yen=50_000_000, has_business_shares=True,
                   notes="自社株・不動産（3,000万）・預金（2,000万）保有"),
            Person(id="p_hanako", name="山田花子", gender=Gender.FEMALE, birth_year=1948,
                   is_alive=True, assets_yen=10_000_000),
            Person(id="p_ichiro", name="山田一郎", gender=Gender.MALE,   birth_year=1970,
                   is_alive=True),
            Person(id="p_niko",   name="山田二子", gender=Gender.FEMALE, birth_year=1972,
                   is_alive=True),
            Person(id="p_saburo", name="山田三郎", gender=Gender.MALE,   birth_year=1975,
                   is_alive=False, notes="被相続人より先に死亡（代襲相続が発生）"),
            Person(id="p_shiro",  name="山田四郎", gender=Gender.MALE,   birth_year=2000,
                   is_alive=True, notes="三郎の子・代襲相続人"),
        ]
        for p in demo_persons:
            ft.persons[p.id] = p

        ft.relationships = [
            Relationship("p_taro",   "p_hanako", "spouse"),
            Relationship("p_taro",   "p_ichiro", "parent_child"),
            Relationship("p_taro",   "p_niko",   "parent_child"),
            Relationship("p_taro",   "p_saburo", "parent_child"),
            Relationship("p_saburo", "p_shiro",  "parent_child"),
        ]
        return ft
