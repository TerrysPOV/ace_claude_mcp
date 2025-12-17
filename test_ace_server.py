"""Tests for ACE Core Logic with multi-project support."""

import json
from pathlib import Path

import pytest

import ace_core


@pytest.fixture(autouse=True)
def isolated_test_dir(monkeypatch, tmp_path):
    """Use isolated temp directory for each test."""
    test_ace_dir = tmp_path / ".ace"
    test_playbooks_dir = test_ace_dir / "playbooks"
    test_reflections_dir = test_ace_dir / "reflections"
    test_projects_file = test_ace_dir / "projects.json"

    monkeypatch.setattr(ace_core, "ACE_DIR", test_ace_dir)
    monkeypatch.setattr(ace_core, "PLAYBOOKS_DIR", test_playbooks_dir)
    monkeypatch.setattr(ace_core, "REFLECTIONS_DIR", test_reflections_dir)
    monkeypatch.setattr(ace_core, "PROJECTS_FILE", test_projects_file)

    yield {
        "dir": test_ace_dir,
        "playbooks": test_playbooks_dir,
        "reflections": test_reflections_dir,
        "projects": test_projects_file,
    }


class TestReadPlaybook:
    def test_creates_default_playbook_if_missing(self):
        result = ace_core.read_playbook()
        assert "## STRATEGIES & INSIGHTS" in result
        assert "## FORMULAS & CALCULATIONS" in result
        assert "## COMMON MISTAKES TO AVOID" in result
        assert "## DOMAIN KNOWLEDGE" in result

    def test_returns_existing_playbook(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "## STRATEGIES & INSIGHTS\n[str-00001] helpful=0 harmful=0 :: Custom content"
        )
        result = ace_core.read_playbook()
        assert "Custom content" in result

    def test_merges_global_and_project(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "## STRATEGIES & INSIGHTS\n[str-00001] helpful=0 harmful=0 :: Global strategy"
        )
        (isolated_test_dir["playbooks"] / "finance.md").write_text(
            "## STRATEGIES & INSIGHTS\n[str-00002] helpful=0 harmful=0 :: Finance strategy"
        )
        result = ace_core.read_playbook("finance")
        assert "Global strategy" in result
        assert "Finance strategy" in result
        assert "[finance]" in result  # Project marker


class TestGetSection:
    def test_returns_section_content(self):
        ace_core.read_playbook()
        result = ace_core.get_section("STRATEGIES & INSIGHTS")
        assert "## STRATEGIES & INSIGHTS" in result
        assert "[str-" in result

    def test_invalid_section_returns_error(self):
        result = ace_core.get_section("INVALID SECTION")
        assert "Invalid section" in result

    def test_all_valid_sections(self):
        ace_core.read_playbook()
        for section in ace_core.SECTION_PREFIXES.keys():
            result = ace_core.get_section(section)
            assert f"## {section}" in result


class TestAddEntry:
    def test_adds_entry_to_global(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("STRATEGIES & INSIGHTS", "Test strategy content")
        assert "Added entry" in result
        assert "str-" in result
        assert "(project: global)" in result

        playbook = ace_core.read_playbook()
        assert "Test strategy content" in playbook

    def test_adds_entry_to_project(self, isolated_test_dir):
        ace_core.create_project("finance", "Finance domain")
        result = ace_core.add_entry("DOMAIN KNOWLEDGE", "FCA regulation info", "finance")
        assert "Added entry" in result
        assert "(project: finance)" in result

        playbook = ace_core.read_playbook("finance")
        assert "FCA regulation info" in playbook

    def test_invalid_section_returns_error(self):
        result = ace_core.add_entry("INVALID", "content")
        assert "Invalid section" in result

    def test_entry_has_zero_counters(self):
        ace_core.read_playbook()
        ace_core.add_entry("STRATEGIES & INSIGHTS", "New insight")
        playbook = ace_core.read_playbook()
        assert "helpful=0 harmful=0 :: New insight" in playbook

    def test_increments_id_correctly(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("STRATEGIES & INSIGHTS", "Third strategy")
        assert "str-00003" in result


class TestUpdateCounters:
    def test_increments_helpful(self):
        ace_core.read_playbook()
        result = ace_core.update_counters("str-00001", helpful_delta=1, harmful_delta=0)
        assert "helpful=0->1" in result
        playbook = ace_core.read_playbook()
        assert "[str-00001] helpful=1 harmful=0" in playbook

    def test_increments_harmful(self):
        ace_core.read_playbook()
        result = ace_core.update_counters("str-00001", helpful_delta=0, harmful_delta=2)
        assert "harmful=0->2" in result

    def test_decrements_with_floor_at_zero(self):
        ace_core.read_playbook()
        result = ace_core.update_counters("str-00001", helpful_delta=-10, harmful_delta=0)
        assert "helpful=0->0" in result

    def test_entry_not_found(self):
        ace_core.read_playbook()
        result = ace_core.update_counters("str-99999", helpful_delta=1, harmful_delta=0)
        assert "not found" in result

    def test_updates_entry_in_project(self, isolated_test_dir):
        ace_core.create_project("finance")
        ace_core.add_entry("STRATEGIES & INSIGHTS", "Finance tip", "finance")
        result = ace_core.update_counters("str-00003", helpful_delta=1, harmful_delta=0)
        assert "helpful=0->1" in result


class TestRemoveEntry:
    def test_removes_existing_entry(self):
        ace_core.read_playbook()
        result = ace_core.remove_entry("str-00001")
        assert "Removed entry" in result
        playbook = ace_core.read_playbook()
        assert "[str-00001]" not in playbook

    def test_entry_not_found(self):
        ace_core.read_playbook()
        result = ace_core.remove_entry("str-99999")
        assert "not found" in result


class TestLogReflection:
    def test_logs_reflection_to_global(self, isolated_test_dir):
        result = ace_core.log_reflection(
            task_summary="Test task",
            outcome="success",
            learnings=["Learning 1", "Learning 2"],
        )
        assert "Logged reflection" in result
        assert "2 learning(s)" in result

        refl_path = isolated_test_dir["reflections"] / "global.jsonl"
        with open(refl_path, "r") as f:
            data = json.loads(f.readline())
            assert data["task_summary"] == "Test task"
            assert data["outcome"] == "success"
            assert len(data["learnings"]) == 2

    def test_logs_reflection_to_project(self, isolated_test_dir):
        ace_core.create_project("finance")
        ace_core.log_reflection("Finance task", "success", ["Learned X"], "finance")

        refl_path = isolated_test_dir["reflections"] / "finance.jsonl"
        assert refl_path.exists()
        with open(refl_path, "r") as f:
            data = json.loads(f.readline())
            assert data["task_summary"] == "Finance task"


class TestCuratePlaybook:
    def test_removes_harmful_entries(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=0 harmful=5 :: Bad strategy
[str-00002] helpful=5 harmful=0 :: Good strategy
"""
        (isolated_test_dir["playbooks"] / "global.md").write_text(playbook)

        result = ace_core.curate_playbook(harmful_threshold=3)
        assert "Removed 1 harmful entries" in result
        assert "str-00001" in result

        updated = ace_core.read_playbook()
        assert "[str-00001]" not in updated
        assert "[str-00002]" in updated

    def test_curates_specific_project(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "## STRATEGIES & INSIGHTS\n[str-00001] helpful=0 harmful=5 :: Bad global"
        )
        (isolated_test_dir["playbooks"] / "finance.md").write_text(
            "## STRATEGIES & INSIGHTS\n[str-00002] helpful=0 harmful=5 :: Bad finance"
        )

        # Only curate finance
        result = ace_core.curate_playbook("finance", harmful_threshold=3)
        assert "str-00002" in result
        assert "str-00001" not in result

    def test_detects_duplicates(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=1 harmful=0 :: Always validate user input
[str-00002] helpful=1 harmful=0 :: Always validate user inputs
"""
        (isolated_test_dir["playbooks"] / "global.md").write_text(playbook)

        result = ace_core.curate_playbook()
        assert "duplicates found" in result


class TestSearchPlaybook:
    def test_finds_matching_entries(self):
        ace_core.read_playbook()
        result = ace_core.search_playbook("validate")
        assert "Found" in result

    def test_no_matches(self):
        ace_core.read_playbook()
        result = ace_core.search_playbook("xyznonexistent")
        assert "No entries found" in result

    def test_searches_merged_playbook(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "## DOMAIN KNOWLEDGE\n[dom-00001] helpful=0 harmful=0 :: Global knowledge"
        )
        (isolated_test_dir["playbooks"] / "finance.md").write_text(
            "## DOMAIN KNOWLEDGE\n[dom-00002] helpful=0 harmful=0 :: Finance knowledge"
        )

        result = ace_core.search_playbook("knowledge", "finance")
        assert "dom-00001" in result
        assert "dom-00002" in result


class TestListProjects:
    def test_lists_default_global(self):
        result = ace_core.list_projects()
        assert "global" in result

    def test_lists_created_projects(self):
        ace_core.create_project("finance", "Financial domain")
        ace_core.create_project("web-dev", "Web development")
        result = ace_core.list_projects()
        assert "finance" in result
        assert "web-dev" in result
        assert "Financial domain" in result


class TestCreateProject:
    def test_creates_new_project(self, isolated_test_dir):
        result = ace_core.create_project("finance", "Financial analysis")
        assert "Created project" in result
        assert "finance" in result

        # Check playbook file created
        assert (isolated_test_dir["playbooks"] / "finance.md").exists()

    def test_duplicate_project_returns_error(self):
        ace_core.create_project("finance")
        result = ace_core.create_project("finance")
        assert "already exists" in result


class TestParseEntry:
    def test_parses_entry_without_project(self):
        line = "[str-00001] helpful=5 harmful=2 :: Test content"
        result = ace_core._parse_entry(line)
        assert result["id"] == "str-00001"
        assert result["helpful"] == 5
        assert result["harmful"] == 2
        assert result["project_id"] is None
        assert result["content"] == "Test content"

    def test_parses_entry_with_project(self):
        line = "[str-00001] helpful=5 harmful=2 [finance] :: Test content"
        result = ace_core._parse_entry(line)
        assert result["id"] == "str-00001"
        assert result["project_id"] == "finance"
        assert result["content"] == "Test content"

    def test_returns_none_for_invalid(self):
        assert ace_core._parse_entry("## HEADER") is None
        assert ace_core._parse_entry("random text") is None
        assert ace_core._parse_entry("") is None


class TestFormatEntry:
    def test_formats_without_project(self):
        result = ace_core._format_entry("str-00001", 5, 2, "Content")
        assert result == "[str-00001] helpful=5 harmful=2 :: Content"

    def test_formats_with_project(self):
        result = ace_core._format_entry("str-00001", 5, 2, "Content", "finance")
        assert result == "[str-00001] helpful=5 harmful=2 [finance] :: Content"


class TestGetNextId:
    def test_increments_from_existing(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "[str-00005] helpful=0 harmful=0 :: Test"
        )
        result = ace_core._get_next_id("str", "global")
        assert result == "str-00006"

    def test_finds_max_across_projects(self, isolated_test_dir):
        isolated_test_dir["playbooks"].mkdir(parents=True, exist_ok=True)
        (isolated_test_dir["playbooks"] / "global.md").write_text(
            "[str-00003] helpful=0 harmful=0 :: Global"
        )
        (isolated_test_dir["playbooks"] / "finance.md").write_text(
            "[str-00010] helpful=0 harmful=0 :: Finance"
        )
        result = ace_core._get_next_id("str", "global", "finance")
        assert result == "str-00011"


class TestThreadSafety:
    def test_concurrent_reads(self):
        import concurrent.futures

        ace_core.read_playbook()

        def read_task():
            return ace_core.read_playbook()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_task) for _ in range(20)]
            results = [f.result() for f in futures]

        assert all(r == results[0] for r in results)

    def test_concurrent_writes(self):
        import concurrent.futures

        ace_core.read_playbook()

        def write_task(i):
            return ace_core.add_entry("STRATEGIES & INSIGHTS", f"Strategy {i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_task, i) for i in range(10)]
            results = [f.result() for f in futures]

        assert all("Added entry" in r for r in results)

        playbook = ace_core.read_playbook()
        for i in range(10):
            assert f"Strategy {i}" in playbook


class TestEdgeCases:
    def test_unicode_content(self):
        ace_core.read_playbook()
        unicode_content = "Использовать эмодзи 🚀"
        ace_core.add_entry("STRATEGIES & INSIGHTS", unicode_content)
        playbook = ace_core.read_playbook()
        assert unicode_content in playbook

    def test_special_characters_in_content(self):
        ace_core.read_playbook()
        special = "Use regex: \\d+\\.\\d+"
        ace_core.add_entry("STRATEGIES & INSIGHTS", special)
        playbook = ace_core.read_playbook()
        assert special in playbook
