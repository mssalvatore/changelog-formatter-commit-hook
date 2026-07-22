#!/usr/bin/env python3
"""
Tests for changelog_formatter.py
"""
import pytest
from pathlib import Path
from changelog_formatter import ChangelogLinter, VALID_SUBSECTIONS


@pytest.fixture
def temp_changelog(tmp_path):
    """Create a temporary changelog file."""
    changelog_path = tmp_path / "CHANGELOG.md"
    return changelog_path


class TestVersionHeaders:
    """Test Rule 1: Version header format validation."""

    def test_valid_version_header(self, temp_changelog):
        content = "## [1.2.3] - 2024-01-15\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        version_violations = [v for v in violations if v.rule == "Rule 1"]
        assert len(version_violations) == 0

    def test_valid_unreleased_header(self, temp_changelog):
        content = "## [Unreleased]\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        version_violations = [v for v in violations if v.rule == "Rule 1"]
        assert len(version_violations) == 0

    def test_invalid_version_format(self, temp_changelog):
        content = "## [1.2] - 2024-01-15\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        version_violations = [v for v in violations if v.rule == "Rule 1"]
        assert len(version_violations) == 1


class TestSubsectionHeaders:
    """Test Rule 2: Subsection header validation."""

    def test_valid_subsection_headers(self, temp_changelog):
        content = "### Added\n### Changed\n### Fixed\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        subsection_violations = [v for v in violations if v.rule == "Rule 2"]
        assert len(subsection_violations) == 0

    def test_invalid_subsection_header(self, temp_changelog):
        content = "### Updated\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        subsection_violations = [v for v in violations if v.rule == "Rule 2"]
        assert len(subsection_violations) == 1
        assert "Updated" in subsection_violations[0].message


class TestSubsectionOrdering:
    """Test Rule 3: Subsection ordering."""

    def test_correct_subsection_order(self, temp_changelog):
        content = """## [1.0.0] - 2024-01-15
### Added
### Changed
### Fixed
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        order_violations = [v for v in violations if v.rule == "Rule 3"]
        assert len(order_violations) == 0

    def test_incorrect_subsection_order(self, temp_changelog):
        content = """## [1.0.0] - 2024-01-15
### Fixed
### Added
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        order_violations = [v for v in violations if v.rule == "Rule 3"]
        assert len(order_violations) == 1

    def test_subsection_order_fix(self, temp_changelog):
        content = """## [1.0.0] - 2024-01-15
### Fixed
- Fix 1
### Added
- Feature 1
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()

        # Check that Added comes before Fixed
        lines = fixed_content.split('\n')
        added_idx = next(i for i, line in enumerate(lines) if line.strip() == "### Added")
        fixed_idx = next(i for i, line in enumerate(lines) if line.strip() == "### Fixed")
        assert added_idx < fixed_idx


class TestBulletFormatting:
    """Test Rules 4 & 5: Bullet formatting and continuation lines."""

    def test_valid_bullet_formatting(self, temp_changelog):
        content = "- Feature one\n  continuation line\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        bullet_violations = [v for v in violations if v.rule in ["Rule 4", "Rule 5"]]
        assert len(bullet_violations) == 0

    def test_bullet_with_extra_space(self, temp_changelog):
        content = "-  Feature with extra space\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        bullet_violations = [v for v in violations if v.rule == "Rule 4"]
        assert len(bullet_violations) == 1

    def test_bullet_extra_space_fix(self, temp_changelog):
        content = "-  Feature\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()
        assert fixed_content == "- Feature\n"

    def test_continuation_wrong_indent(self, temp_changelog):
        content = "- Feature\n continuation\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        indent_violations = [v for v in violations if v.rule == "Rule 5"]
        assert len(indent_violations) == 1

    def test_continuation_indent_fix(self, temp_changelog):
        content = "- Feature\ncontinuation\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()
        assert fixed_content == "- Feature\n  continuation\n"


class TestIssueReferences:
    """Test Rules 6, 7, 8: Issue reference formatting."""

    def test_valid_issue_references(self, temp_changelog):
        content = "- Feature JIRA-123, PROJ-456\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if v.rule in ["Rule 6", "Rule 7", "Rule 8"]]
        assert len(ref_violations) == 0

    def test_issue_reference_with_hash(self, temp_changelog):
        content = "- Feature #123\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if v.rule in ["Rule 6", "Rule 7", "Rule 8"]]
        assert len(ref_violations) == 0

    def test_missing_space_between_refs(self, temp_changelog):
        content = "- Feature JIRA-123,JIRA-456\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if v.rule == "Rule 8"]
        assert len(ref_violations) == 1

    def test_missing_space_fix(self, temp_changelog):
        content = "- Feature JIRA-123,JIRA-456\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()
        assert "JIRA-123, JIRA-456" in fixed_content

    def test_trailing_comma(self, temp_changelog):
        content = "- Feature JIRA-123,\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if v.rule == "Rule 8"]
        assert len(ref_violations) == 1

    def test_trailing_comma_fix(self, temp_changelog):
        content = "- Feature JIRA-123,\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()
        assert fixed_content == "- Feature JIRA-123\n"


class TestBlankLines:
    """Test Rules 9 & 10: Blank line requirements."""

    def test_no_blank_line_after_version_header(self, temp_changelog):
        content = """# Changelog

## [1.0.0] - 2024-01-15
### Added
- Feature
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        blank_violations = [v for v in violations if v.rule == "Rule 9"]
        # Should have no violations - no blank line needed between version and first subsection
        first_subsection_violations = [v for v in blank_violations if "### Added" in str(v.line_number)]
        assert len(first_subsection_violations) == 0

    def test_blank_line_between_subsections_with_content(self, temp_changelog):
        content = """## [1.0.0] - 2024-01-15
### Added
- Feature

### Fixed
- Bug fix
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        blank_violations = [v for v in violations if v.rule == "Rule 9"]
        assert len(blank_violations) == 0

    def test_two_blank_lines_between_versions(self, temp_changelog):
        content = """## [1.0.0] - 2024-01-15
### Added
- Feature


## [0.9.0] - 2024-01-01
### Added
- Old feature
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        version_blank_violations = [v for v in violations if v.rule == "Rule 10"]
        assert len(version_blank_violations) == 0


class TestLineLength:
    """Test Rule 11: Line length wrapping."""

    def test_line_exceeds_max_length(self, temp_changelog):
        long_line = "- " + "x" * 100 + "\n"
        temp_changelog.write_text(long_line)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        length_violations = [v for v in violations if v.rule == "Rule 11"]
        assert len(length_violations) == 1

    def test_line_length_fix_with_wrapping(self, temp_changelog):
        content = "- A very long line that definitely exceeds eighty characters and should be wrapped automatically. JIRA-123\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()

        lines = fixed_content.split('\n')
        for line in lines:
            if line:  # Skip empty lines
                assert len(line) <= 80

    def test_line_wrapping_preserves_issue_refs(self, temp_changelog):
        content = "- A very long line that definitely exceeds eighty characters and should be wrapped automatically by the formatter. JIRA-123\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()

        # Issue reference should still be present
        assert "JIRA-123" in fixed_content


class TestLineLengthReflow:
    """Test that multi-line bullets are reflowed as a unit, not line-by-line."""

    def test_long_first_line_reflows_with_existing_continuations(self, temp_changelog):
        """Regression test: a long bullet whose first line just exceeds 80 chars
        should be reflowed together with its existing continuation lines, not
        wrapped in isolation leaving orphaned words on their own lines."""
        content = (
            "- A `OCP_WEEKLY_READINESS_CALCULATION_DAY` environment variable"
            " that allows setting\n"
            "  the day of the week when the daily readiness calculation will"
            " also send\n"
            "  weekly statistics. OCPSG-1101\n"
        )
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()

        lines = [l for l in fixed_content.split("\n") if l]
        for line in lines:
            assert len(line) <= 80

        # "allows setting" must not appear alone on its own line
        assert "  allows setting\n" not in fixed_content
        assert "OCPSG-1101" in fixed_content


class TestCompleteFormatting:
    """Integration tests for complete changelog formatting."""

    def test_full_changelog_formatting(self, temp_changelog):
        content = """# Changelog

## [Unreleased]

### Added
- A very long feature description that definitely exceeds the maximum line length and needs to be wrapped. JIRA-123
### Fixed
- Bug fix JIRA-456,JIRA-789,

## [1.0.0] - 2024-01-15
### Fixed
- First fix
### Added
- First feature
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        fixed_content = linter.apply_fixes()

        # Verify the file was formatted
        lines = fixed_content.split('\n')

        # Check line length
        for line in lines:
            if line:
                assert len(line) <= 80

        # Check issue reference spacing
        assert "JIRA-456, JIRA-789" in fixed_content

        # Verify no trailing commas
        assert ",\n" not in fixed_content or "," not in [line.rstrip()[-1] for line in lines if line.strip() and not line.strip().endswith(',')]

    def test_no_violations_passes_cleanly(self, temp_changelog):
        content = """# Changelog

## [1.0.0] - 2024-01-15
### Added
- Feature one

### Fixed
- Bug fix
"""
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        assert len(violations) == 0


class TestGenericIssueReferences:
    """Test that various issue reference formats are recognized."""

    def test_jira_style_references(self, temp_changelog):
        content = "- Feature PROJ-123\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        # Should not have any violations for valid JIRA-style references
        ref_violations = [v for v in violations if "reference" in v.message.lower()]
        assert len(ref_violations) == 0

    def test_github_style_references(self, temp_changelog):
        content = "- Feature #456\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if "reference" in v.message.lower()]
        assert len(ref_violations) == 0

    def test_short_prefix_references(self, temp_changelog):
        content = "- Feature AI-789\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if "reference" in v.message.lower()]
        assert len(ref_violations) == 0

    def test_long_prefix_references(self, temp_changelog):
        content = "- Feature LONGPREFIX-123\n"
        temp_changelog.write_text(content)
        linter = ChangelogLinter(temp_changelog)
        violations = linter.lint()
        ref_violations = [v for v in violations if "reference" in v.message.lower()]
        assert len(ref_violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
