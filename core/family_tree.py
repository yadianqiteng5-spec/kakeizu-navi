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

    # ── デモシナリオ集（典型事例） ────────────────────────────────

    @classmethod
    def create_scenario(cls, scenario_id: str) -> "FamilyTree":
        """
        シナリオIDから典型事例を生成する。
        scenario_id: "standard" / "no_children" / "siblings_only" /
                     "half_blood" / "adoption" / "special_adoption" /
                     "simultaneous_death" / "renounce"
        """
        builders = {
            "standard":           cls._scenario_standard,
            "no_children":        cls._scenario_no_children,
            "siblings_only":      cls._scenario_siblings_only,
            "half_blood":         cls._scenario_half_blood,
            "adoption":           cls._scenario_adoption,
            "special_adoption":   cls._scenario_special_adoption,
            "simultaneous_death": cls._scenario_simultaneous_death,
            "renounce":           cls._scenario_renounce,
        }
        return builders.get(scenario_id, cls.create_demo)()

    @classmethod
    def _scenario_standard(cls) -> "FamilyTree":
        """標準: 配偶者+子3名（うち1名は先死亡→代襲）— 既存のデモ"""
        return cls.create_demo()

    @classmethod
    def _scenario_no_children(cls) -> "FamilyTree":
        """子なし夫婦+両親（直系尊属が相続人）"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人・夫", Gender.MALE, 1960, False, True, 60_000_000),
            "w": ft.add_person("妻", Gender.FEMALE, 1962, True),
            "p_f": ft.add_person("父", Gender.MALE, 1935, True),
            "p_m": ft.add_person("母", Gender.FEMALE, 1938, True),
        }
        ft.add_spouse(ids["f"], ids["w"])
        ft.add_parent_child(ids["p_f"], ids["f"])
        ft.add_parent_child(ids["p_m"], ids["f"])
        return ft

    @classmethod
    def _scenario_siblings_only(cls) -> "FamilyTree":
        """子なし・両親死亡 → 配偶者+兄弟姉妹（遺留分発生せず）"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人", Gender.MALE, 1955, False, True, 40_000_000),
            "w": ft.add_person("妻", Gender.FEMALE, 1958, True),
            "p_f": ft.add_person("父", Gender.MALE, 1925, False),
            "p_m": ft.add_person("母", Gender.FEMALE, 1928, False),
            "b1": ft.add_person("兄", Gender.MALE, 1953, True),
            "b2": ft.add_person("妹", Gender.FEMALE, 1960, True),
        }
        ft.add_spouse(ids["f"], ids["w"])
        for p in (ids["p_f"], ids["p_m"]):
            ft.add_parent_child(p, ids["f"])
            ft.add_parent_child(p, ids["b1"])
            ft.add_parent_child(p, ids["b2"])
        return ft

    @classmethod
    def _scenario_half_blood(cls) -> "FamilyTree":
        """半血兄弟あり: 全血1名+半血1名（全血2:半血1 で按分）"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人", Gender.MALE, 1950, False, True, 30_000_000,
                               notes="独身・子なし"),
            "p_f": ft.add_person("父", Gender.MALE, 1920, False),
            "p_m1": ft.add_person("実母", Gender.FEMALE, 1925, False),
            "p_m2": ft.add_person("継母", Gender.FEMALE, 1935, False),
            "b1": ft.add_person("全血兄", Gender.MALE, 1948, True),
            "b2": ft.add_person("半血弟", Gender.MALE, 1965, True, notes="父+継母の子"),
        }
        ft.add_parent_child(ids["p_f"], ids["f"])
        ft.add_parent_child(ids["p_m1"], ids["f"])
        ft.add_parent_child(ids["p_f"], ids["b1"])
        ft.add_parent_child(ids["p_m1"], ids["b1"])
        ft.add_parent_child(ids["p_f"], ids["b2"])
        ft.add_parent_child(ids["p_m2"], ids["b2"])
        return ft

    @classmethod
    def _scenario_adoption(cls) -> "FamilyTree":
        """普通養子あり: 実子2+養子2（相続税法15条2項で養子は1名のみ算入）"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人", Gender.MALE, 1945, False, True, 100_000_000,
                               has_business_shares=True),
            "w": ft.add_person("妻", Gender.FEMALE, 1948, True),
            "c1": ft.add_person("実子・長男", Gender.MALE, 1972, True),
            "c2": ft.add_person("実子・長女", Gender.FEMALE, 1975, True),
            "a1": ft.add_person("普通養子A", Gender.MALE, 1980, True,
                                notes="婿養子・後継者候補"),
            "a2": ft.add_person("普通養子B", Gender.FEMALE, 1985, True),
        }
        ft.add_spouse(ids["f"], ids["w"])
        ft.add_parent_child(ids["f"], ids["c1"], adoption_type="biological")
        ft.add_parent_child(ids["f"], ids["c2"], adoption_type="biological")
        ft.add_parent_child(ids["f"], ids["a1"], adoption_type="regular_adoption")
        ft.add_parent_child(ids["f"], ids["a2"], adoption_type="regular_adoption")
        return ft

    @classmethod
    def _scenario_special_adoption(cls) -> "FamilyTree":
        """特別養子: 養親側からのみ相続（実親との関係は終了）"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人（養親）", Gender.MALE, 1950, False, True, 40_000_000),
            "w": ft.add_person("妻（養親）", Gender.FEMALE, 1953, True),
            "c": ft.add_person("特別養子", Gender.FEMALE, 2010, True,
                               notes="幼少期に特別養子縁組"),
            "rp": ft.add_person("実親（参考表示）", Gender.MALE, 1985, True,
                                notes="特別養子で親族関係は終了"),
        }
        ft.add_spouse(ids["f"], ids["w"])
        ft.add_parent_child(ids["f"], ids["c"], adoption_type="special_adoption")
        ft.add_parent_child(ids["w"], ids["c"], adoption_type="special_adoption")
        ft.add_parent_child(ids["rp"], ids["c"], adoption_type="biological")
        return ft

    @classmethod
    def _scenario_simultaneous_death(cls) -> "FamilyTree":
        """同時死亡: 親子が事故で同時死亡 → 代襲が成立"""
        ft = cls()
        ids = {
            "f": ft.add_person("祖父・被相続人", Gender.MALE, 1940, False, True, 80_000_000),
            "w": ft.add_person("祖母", Gender.FEMALE, 1942, True),
            "c1": ft.add_person("長男", Gender.MALE, 1968, True,
                                died_simultaneously=True,
                                notes="祖父と同時に交通事故で死亡"),
            "c2": ft.add_person("次男", Gender.MALE, 1970, True),
            "gc": ft.add_person("孫（長男の子）", Gender.MALE, 1995, True,
                                notes="代襲相続人"),
        }
        ft.add_spouse(ids["f"], ids["w"])
        ft.add_parent_child(ids["f"], ids["c1"])
        ft.add_parent_child(ids["f"], ids["c2"])
        ft.add_parent_child(ids["c1"], ids["gc"])
        return ft

    @classmethod
    def _scenario_renounce(cls) -> "FamilyTree":
        """相続放棄: 長男が放棄 → 代襲は発生せず、他の子で按分"""
        ft = cls()
        ids = {
            "f": ft.add_person("被相続人", Gender.MALE, 1950, False, True, 50_000_000,
                               notes="多額の借金あり"),
            "w": ft.add_person("妻", Gender.FEMALE, 1953, True, is_renounced=True,
                               notes="債務超過のため放棄"),
            "c1": ft.add_person("長男", Gender.MALE, 1975, True, is_renounced=True,
                                notes="債務超過のため放棄"),
            "c2": ft.add_person("次男", Gender.MALE, 1978, True),
            "gc": ft.add_person("孫（長男の子）", Gender.MALE, 2005, True,
                                notes="放棄者の子は代襲しない（民法939条）"),
        }
        ft.add_spouse(ids["f"], ids["w"])
        ft.add_parent_child(ids["f"], ids["c1"])
        ft.add_parent_child(ids["f"], ids["c2"])
        ft.add_parent_child(ids["c1"], ids["gc"])
        return ft

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
