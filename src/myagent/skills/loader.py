from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from myagent.skills.registry import SkillManifest


FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
VALID_FRONT_MATTER_KEYS = {
    "name",
    "description",
    "version",
    "triggers",
    "preferred-tools",
    "disallowed-tools",
    "response-style",
}


@dataclass(slots=True, frozen=True)
class SkillConflict:
    name: str
    replaced_source: Path
    replacing_source: Path
    replaced_type: str
    replacing_type: str


@dataclass(slots=True, frozen=True)
class SkillDiscoveryResult:
    manifests: list[SkillManifest]
    conflicts: list[SkillConflict]


def discover_skills(
    *,
    builtin_root: Path,
    project_root: Path,
    user_roots: tuple[Path, ...] = (),
) -> list[SkillManifest]:
    return discover_skills_with_conflicts(
        builtin_root=builtin_root,
        project_root=project_root,
        user_roots=user_roots,
    ).manifests


def discover_skills_with_conflicts(
    *,
    builtin_root: Path,
    project_root: Path,
    user_roots: tuple[Path, ...] = (),
) -> SkillDiscoveryResult:
    manifests: dict[str, SkillManifest] = {}
    conflicts: list[SkillConflict] = []
    for source_type, root in [
        ("builtin", builtin_root),
        ("project", project_root),
        *[("user", user_root) for user_root in user_roots],
    ]:
        for manifest in _discover_from_root(root, source_type=source_type):
            previous = manifests.get(manifest.name)
            if previous is not None:
                conflicts.append(
                    SkillConflict(
                        name=manifest.name,
                        replaced_source=previous.source_dir,
                        replacing_source=manifest.source_dir,
                        replaced_type=previous.source_type,
                        replacing_type=manifest.source_type,
                    )
                )
            manifests[manifest.name] = manifest
    return SkillDiscoveryResult(manifests=list(manifests.values()), conflicts=conflicts)


def _discover_from_root(root: Path, *, source_type: str) -> list[SkillManifest]:
    if not root.exists() or not root.is_dir():
        return []
    manifests: list[SkillManifest] = []
    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        content_path = skill_dir / "SKILL.md"
        if not content_path.exists():
            continue
        metadata = _parse_front_matter(content_path.read_text(encoding="utf-8"))
        manifests.append(
            SkillManifest(
                name=_require_string(metadata, "name", fallback=skill_dir.name),
                description=_require_string(metadata, "description"),
                source_dir=skill_dir,
                source_type=source_type,
                content_path=content_path,
                version=_require_string(metadata, "version", fallback="1"),
                triggers=_tuple_of_strings(metadata.get("triggers")),
                preferred_tools=_tuple_of_strings(metadata.get("preferred-tools")),
                disallowed_tools=_tuple_of_strings(metadata.get("disallowed-tools")),
                response_style=_optional_string(metadata.get("response-style")),
                references=_discover_support_files(skill_dir / "references"),
                scripts=_discover_support_files(skill_dir / "scripts"),
            )
        )
    return manifests


def _parse_front_matter(text: str) -> dict[str, object]:
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        raise ValueError("SKILL.md must start with YAML-like front matter.")
    metadata: dict[str, object] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key not in VALID_FRONT_MATTER_KEYS:
            raise ValueError(f"Unknown skill metadata field: {normalized_key}")
        metadata[normalized_key] = _parse_value(raw_value.strip())
    if "description" not in metadata:
        raise ValueError("Skill front matter must define description.")
    return metadata


def _parse_value(raw: str) -> object:
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    return raw.strip().strip("\"'")


def _require_string(metadata: dict[str, object], key: str, *, fallback: str | None = None) -> str:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if fallback is not None:
        return fallback
    raise ValueError(f"Missing required skill metadata field: {key}")


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _tuple_of_strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("Expected a list or string in skill front matter.")


def _discover_support_files(root: Path) -> tuple[Path, ...]:
    if not root.exists() or not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.rglob("*") if path.is_file()))
