from pathlib import Path
from uuid import uuid4

import pytest

from myagent.skills import SkillRegistry, discover_skills
from myagent.skills.loader import discover_skills_with_conflicts


def test_discover_skills_loads_builtin_skill_manifests() -> None:
    builtin_root = Path("src") / "myagent" / "builtin_skills"
    manifests = discover_skills(
        builtin_root=builtin_root,
        project_root=Path(".missing-project-skills"),
    )

    names = sorted(manifest.name for manifest in manifests)
    assert "repo_explainer" in names
    assert "code_debugger" in names
    assert "feature_implementer" in names


def test_project_skill_overrides_builtin_skill() -> None:
    root = Path(".data") / "test-project-skill-override" / str(uuid4())
    skill_dir = root / "repo_explainer"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: repo_explainer
description: Custom repo explainer.
triggers: [仓库]
preferred-tools: [read_file]
response-style: Custom style.
---

Use the custom repo explanation policy.
""",
        encoding="utf-8",
    )

    manifests = discover_skills(
        builtin_root=Path("src") / "myagent" / "builtin_skills",
        project_root=root,
    )
    registry = SkillRegistry(manifests)
    skill = registry.get("repo_explainer")

    assert skill is not None
    assert skill.description == "Custom repo explainer."
    assert "Use the custom repo explanation policy." in skill.to_prompt()


def test_skill_manifest_loads_references_and_scripts() -> None:
    root = Path(".data") / "test-skill-references" / str(uuid4())
    skill_dir = root / "repo_helper"
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: repo_helper
description: Repo helper.
version: 2
triggers: [repo]
preferred-tools: [read_file]
---

Use repository helper policy.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "guide.md").write_text("Reference guidance.", encoding="utf-8")
    (skill_dir / "scripts" / "helper.ps1").write_text("Write-Output 'helper'", encoding="utf-8")

    manifests = discover_skills(builtin_root=Path(".missing"), project_root=root)
    skill = SkillRegistry(manifests).get("repo_helper")

    assert skill is not None
    prompt = skill.to_prompt()
    assert "Skill version: 2" in prompt
    assert "Reference guidance." in prompt
    assert "scripts/helper.ps1" in prompt


def test_skill_manifest_selects_references_and_scripts_by_query() -> None:
    root = Path(".data") / "test-skill-selective" / str(uuid4())
    skill_dir = root / "repo_helper"
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: repo_helper
description: Repo helper.
---

Use repository helper policy.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "repo-guide.md").write_text("Repo guide.", encoding="utf-8")
    (skill_dir / "references" / "debug-guide.md").write_text("Debug guide.", encoding="utf-8")
    (skill_dir / "scripts" / "repo_scan.ps1").write_text("repo", encoding="utf-8")
    (skill_dir / "scripts" / "debug_trace.ps1").write_text("debug", encoding="utf-8")

    manifests = discover_skills(builtin_root=Path(".missing"), project_root=root)
    skill = SkillRegistry(manifests).get("repo_helper")

    assert skill is not None
    repo_prompt = skill.build_prompt(query="repo structure", max_reference_files=1, max_script_files=1)
    debug_prompt = skill.build_prompt(query="debug error", max_reference_files=1, max_script_files=1)

    assert "Repo guide." in repo_prompt
    assert "scripts/repo_scan.ps1" in repo_prompt
    assert "Debug guide." in debug_prompt
    assert "scripts/debug_trace.ps1" in debug_prompt


def test_skill_loader_rejects_unknown_front_matter_field() -> None:
    root = Path(".data") / "test-skill-invalid" / str(uuid4())
    skill_dir = root / "bad_skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: bad_skill
description: Invalid skill.
unknown-field: nope
---

Invalid.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown skill metadata field"):
        discover_skills(builtin_root=Path(".missing"), project_root=root)


def test_skill_discovery_reports_conflicts() -> None:
    root = Path(".data") / "test-skill-conflict" / str(uuid4())
    skill_dir = root / "repo_explainer"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: repo_explainer
description: Override.
---

Override.
""",
        encoding="utf-8",
    )

    result = discover_skills_with_conflicts(
        builtin_root=Path("src") / "myagent" / "builtin_skills",
        project_root=root,
    )

    assert any(conflict.name == "repo_explainer" for conflict in result.conflicts)
