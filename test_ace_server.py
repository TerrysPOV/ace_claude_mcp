"""Tests for ACE Core Logic."""

import json
import tempfile
from pathlib import Path

import pytest

import ace_core


@pytest.fixture(autouse=True)
def isolated_test_dir(monkeypatch, tmp_path):
    """Use isolated temp directory for each test."""
    test_ace_dir = tmp_path / ".ace"
    test_playbook = test_ace_dir / "playbook.md"
    test_reflections = test_ace_dir / "reflections.jsonl"

    monkeypatch.setattr(ace_core, "ACE_DIR", test_ace_dir)
    monkeypatch.setattr(ace_core, "PLAYBOOK_PATH", test_playbook)
    monkeypatch.setattr(ace_core, "REFLECTIONS_PATH", test_reflections)

    yield {
        "dir": test_ace_dir,
        "playbook": test_playbook,
        "reflections": test_reflections,
    }


class TestReadPlaybook:
    def test_creates_default_playbook_if_missing(self):
        result = ace_core.read_playbook()
        assert "## STRATEGIES & INSIGHTS" in result
        assert "## FORMULAS & CALCULATIONS" in result
        assert "## COMMON MISTAKES TO AVOID" in result
        assert "## DOMAIN KNOWLEDGE" in result

    def test_returns_existing_playbook(self, isolated_test_dir):
        isolated_test_dir["dir"].mkdir(parents=True, exist_ok=True)
        isolated_test_dir["playbook"].write_text("Custom playbook content")
        result = ace_core.read_playbook()
        assert result == "Custom playbook content"


class TestGetSection:
    def test_returns_section_content(self):
        ace_core.read_playbook()  # Initialize default
        result = ace_core.get_section("STRATEGIES & INSIGHTS")
        assert "## STRATEGIES & INSIGHTS" in result
        assert "[str-" in result

    def test_invalid_section_returns_error(self):
        result = ace_core.get_section("INVALID SECTION")
        assert "Invalid section" in result

    def test_all_valid_sections(self):
        ace_core.read_playbook()  # Initialize default
        for section in ace_core.SECTION_PREFIXES.keys():
            result = ace_core.get_section(section)
            assert f"## {section}" in result


class TestAddEntry:
    def test_adds_entry_to_strategies(self):
        ace_core.read_playbook()  # Initialize default
        result = ace_core.add_entry("STRATEGIES & INSIGHTS", "Test strategy content")
        assert "Added entry" in result
        assert "str-" in result

        playbook = ace_core.read_playbook()
        assert "Test strategy content" in playbook

    def test_adds_entry_to_formulas(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("FORMULAS & CALCULATIONS", "E = mc^2")
        assert "cal-" in result

    def test_adds_entry_to_mistakes(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("COMMON MISTAKES TO AVOID", "Never divide by zero")
        assert "mis-" in result

    def test_adds_entry_to_domain(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("DOMAIN KNOWLEDGE", "Python uses GIL")
        assert "dom-" in result

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
        # Default has str-00001 and str-00002
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
        result = ace_core.update_counters(
            "str-00001", helpful_delta=-10, harmful_delta=0
        )
        assert "helpful=0->0" in result  # Can't go below 0

    def test_entry_not_found(self):
        ace_core.read_playbook()
        result = ace_core.update_counters(
            "str-99999", helpful_delta=1, harmful_delta=0
        )
        assert "not found" in result

    def test_multiple_updates(self):
        ace_core.read_playbook()
        ace_core.update_counters("str-00001", helpful_delta=5, harmful_delta=0)
        ace_core.update_counters("str-00001", helpful_delta=3, harmful_delta=1)
        playbook = ace_core.read_playbook()
        assert "[str-00001] helpful=8 harmful=1" in playbook


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
    def test_logs_reflection_to_file(self, isolated_test_dir):
        result = ace_core.log_reflection(
            task_summary="Test task",
            outcome="success",
            learnings=["Learning 1", "Learning 2"],
        )
        assert "Logged reflection" in result
        assert "2 learning(s)" in result

        with open(isolated_test_dir["reflections"], "r") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["task_summary"] == "Test task"
            assert data["outcome"] == "success"
            assert len(data["learnings"]) == 2

    def test_appends_multiple_reflections(self, isolated_test_dir):
        ace_core.log_reflection("Task 1", "success", ["L1"])
        ace_core.log_reflection("Task 2", "failure", ["L2"])

        with open(isolated_test_dir["reflections"], "r") as f:
            lines = f.readlines()
            assert len(lines) == 2


class TestCuratePlaybook:
    def test_removes_harmful_entries(self, isolated_test_dir):
        isolated_test_dir["dir"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=0 harmful=5 :: Bad strategy
[str-00002] helpful=5 harmful=0 :: Good strategy
"""
        isolated_test_dir["playbook"].write_text(playbook)

        result = ace_core.curate_playbook(harmful_threshold=3)
        assert "Removed 1 harmful entries" in result
        assert "str-00001" in result

        updated = ace_core.read_playbook()
        assert "[str-00001]" not in updated
        assert "[str-00002]" in updated

    def test_respects_threshold(self, isolated_test_dir):
        isolated_test_dir["dir"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=2 harmful=4 :: Slightly harmful
"""
        isolated_test_dir["playbook"].write_text(playbook)

        # harmful (4) > helpful (2) + threshold (3) = 5? No, so keep it
        result = ace_core.curate_playbook(harmful_threshold=3)
        assert "No harmful entries" in result

        # With threshold=1: harmful (4) > helpful (2) + 1 = 3? Yes, remove
        result = ace_core.curate_playbook(harmful_threshold=1)
        assert "Removed 1" in result

    def test_detects_duplicates(self, isolated_test_dir):
        isolated_test_dir["dir"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=1 harmful=0 :: Always validate user input
[str-00002] helpful=1 harmful=0 :: Always validate user inputs
"""
        isolated_test_dir["playbook"].write_text(playbook)

        result = ace_core.curate_playbook()
        assert "duplicates found" in result
        assert "str-00001" in result and "str-00002" in result


class TestSearchPlaybook:
    def test_finds_matching_entries(self):
        ace_core.read_playbook()
        result = ace_core.search_playbook("validate")
        assert "Found" in result
        assert "Validate assumptions" in result or "validate" in result.lower()

    def test_no_matches(self):
        ace_core.read_playbook()
        result = ace_core.search_playbook("xyznonexistent")
        assert "No entries found" in result

    def test_case_insensitive(self):
        ace_core.read_playbook()
        result1 = ace_core.search_playbook("PROBLEMS")
        result2 = ace_core.search_playbook("problems")
        # Both should find the same entries
        assert ("Found" in result1) == ("Found" in result2)

    def test_multiple_keywords(self, isolated_test_dir):
        isolated_test_dir["dir"].mkdir(parents=True, exist_ok=True)
        playbook = """## STRATEGIES & INSIGHTS
[str-00001] helpful=0 harmful=0 :: Always validate data
[str-00002] helpful=0 harmful=0 :: Check user permissions
"""
        isolated_test_dir["playbook"].write_text(playbook)

        result = ace_core.search_playbook("validate data")
        assert "str-00001" in result


class TestParseEntry:
    def test_parses_valid_entry(self):
        line = "[str-00001] helpful=5 harmful=2 :: Test content here"
        result = ace_core._parse_entry(line)
        assert result["id"] == "str-00001"
        assert result["helpful"] == 5
        assert result["harmful"] == 2
        assert result["content"] == "Test content here"

    def test_returns_none_for_invalid(self):
        assert ace_core._parse_entry("## HEADER") is None
        assert ace_core._parse_entry("random text") is None
        assert ace_core._parse_entry("") is None


class TestFormatEntry:
    def test_formats_correctly(self):
        result = ace_core._format_entry("str-00001", 5, 2, "Content")
        assert result == "[str-00001] helpful=5 harmful=2 :: Content"


class TestGetNextId:
    def test_increments_from_existing(self):
        content = "[str-00005] helpful=0 harmful=0 :: Test"
        result = ace_core._get_next_id(content, "str")
        assert result == "str-00006"

    def test_starts_at_one_if_none(self):
        content = "No entries"
        result = ace_core._get_next_id(content, "str")
        assert result == "str-00001"

    def test_finds_max_across_multiple(self):
        content = """[str-00001] helpful=0 harmful=0 :: A
[str-00010] helpful=0 harmful=0 :: B
[str-00005] helpful=0 harmful=0 :: C"""
        result = ace_core._get_next_id(content, "str")
        assert result == "str-00011"


class TestThreadSafety:
    def test_concurrent_reads(self):
        import concurrent.futures

        ace_core.read_playbook()  # Initialize

        def read_task():
            return ace_core.read_playbook()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_task) for _ in range(20)]
            results = [f.result() for f in futures]

        # All reads should succeed and return same content
        assert all(r == results[0] for r in results)

    def test_concurrent_writes(self):
        import concurrent.futures

        ace_core.read_playbook()  # Initialize

        def write_task(i):
            return ace_core.add_entry("STRATEGIES & INSIGHTS", f"Strategy {i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_task, i) for i in range(10)]
            results = [f.result() for f in futures]

        # All writes should succeed
        assert all("Added entry" in r for r in results)

        # All entries should be in playbook
        playbook = ace_core.read_playbook()
        for i in range(10):
            assert f"Strategy {i}" in playbook


class TestEdgeCases:
    def test_empty_content_entry(self):
        ace_core.read_playbook()
        result = ace_core.add_entry("STRATEGIES & INSIGHTS", "   ")
        assert "Added entry" in result

    def test_special_characters_in_content(self):
        ace_core.read_playbook()
        special = "Use regex pattern: \\d+\\.\\d+ for decimals"
        ace_core.add_entry("STRATEGIES & INSIGHTS", special)
        playbook = ace_core.read_playbook()
        assert special in playbook

    def test_very_long_content(self):
        ace_core.read_playbook()
        long_content = "A" * 10000
        ace_core.add_entry("STRATEGIES & INSIGHTS", long_content)
        playbook = ace_core.read_playbook()
        assert long_content in playbook

    def test_unicode_content(self):
        ace_core.read_playbook()
        unicode_content = "Использовать эмодзи 🚀 для маркировки"
        ace_core.add_entry("STRATEGIES & INSIGHTS", unicode_content)
        playbook = ace_core.read_playbook()
        assert unicode_content in playbook
