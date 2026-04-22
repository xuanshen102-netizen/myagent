from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(slots=True, frozen=True)
class SkillManifest:
    name: str
    description: str
    source_dir: Path
    source_type: str
    content_path: Path
    version: str = "1"
    triggers: tuple[str, ...] = ()
    preferred_tools: tuple[str, ...] = ()
    disallowed_tools: tuple[str, ...] = ()
    response_style: str | None = None
    references: tuple[Path, ...] = ()
    scripts: tuple[Path, ...] = ()

    def load_instruction(self) -> str:
        text = self.content_path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                return parts[2].strip()
        return text.strip()

    def to_prompt(self) -> str:
        return self.build_prompt()

    def build_prompt(
        self,
        query: str = "",
        *,
        max_reference_files: int = 2,
        max_script_files: int = 2,
    ) -> str:
        parts = [f"Active skill: {self.name}", f"Skill goal: {self.description}", self.load_instruction()]
        parts.append(f"Skill version: {self.version}")
        if self.preferred_tools:
            parts.append("Preferred tools: " + ", ".join(self.preferred_tools))
        if self.disallowed_tools:
            parts.append("Avoid tools: " + ", ".join(self.disallowed_tools))
        if self.response_style:
            parts.append(f"Response style: {self.response_style}")
        references = self.load_references(query=query, limit=max_reference_files)
        if references:
            parts.append("Skill references:\n" + "\n\n".join(references))
        scripts = self.select_scripts(query=query, limit=max_script_files)
        if scripts:
            parts.append(
                "Available skill scripts: "
                + ", ".join(path.relative_to(self.source_dir).as_posix() for path in scripts)
            )
        return "\n".join(part for part in parts if part)

    def load_references(self, query: str = "", *, limit: int = 2) -> list[str]:
        loaded: list[str] = []
        for reference in self.select_references(query=query, limit=limit):
            loaded.append(reference.read_text(encoding="utf-8").strip())
        return [item for item in loaded if item]

    def select_references(self, query: str = "", *, limit: int = 2) -> list[Path]:
        return self._rank_paths(self.references, query=query, limit=limit)

    def select_scripts(self, query: str = "", *, limit: int = 2) -> list[Path]:
        return self._rank_paths(self.scripts, query=query, limit=limit)

    def _rank_paths(self, paths: tuple[Path, ...], *, query: str, limit: int) -> list[Path]:
        if len(paths) <= limit:
            return list(paths)
        ranked = sorted(
            enumerate(paths),
            key=lambda item: (
                self._score_path_relevance(item[1], query),
                item[0],
            ),
            reverse=True,
        )
        selected = sorted(ranked[:limit], key=lambda item: item[0])
        return [path for _, path in selected]

    def _score_path_relevance(self, path: Path, query: str) -> int:
        if not query.strip():
            return 0
        query_tokens = self._tokenize(query)
        candidate_tokens = self._tokenize(" ".join(path.parts))
        return len(query_tokens & candidate_tokens) * 3

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text.lower())
            if len(token) >= 2
        }


class SkillRegistry:
    def __init__(self, manifests: list[SkillManifest] | None = None) -> None:
        self._skills: dict[str, SkillManifest] = {}
        if manifests is None:
            manifests = self.with_defaults()._skills.values()
        for manifest in manifests:
            self.register(manifest)

    @classmethod
    def with_defaults(cls) -> "SkillRegistry":
        from myagent.skills.loader import discover_skills

        builtin_root = Path(__file__).resolve().parent.parent / "builtin_skills"
        registry = cls([])
        for manifest in discover_skills(builtin_root=builtin_root, project_root=Path(".nonexistent")):
            registry.register(manifest)
        return registry

    def register(self, manifest: SkillManifest, *, override: bool = False) -> None:
        if manifest.name in self._skills and not override:
            raise ValueError(f"Skill already registered: {manifest.name}")
        self._skills[manifest.name] = manifest

    def get(self, name: str | None) -> SkillManifest | None:
        if not name:
            return None
        return self._skills.get(name)

    def choose_for_query(self, query: str) -> SkillManifest | None:
        lowered = query.lower()
        best: tuple[int, SkillManifest] | None = None
        for manifest in self._skills.values():
            score = sum(1 for keyword in manifest.triggers if keyword.lower() in lowered)
            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, manifest)
        return best[1] if best else None

    def names(self) -> list[str]:
        return sorted(self._skills)
