#!/usr/bin/env python3
"""
Changelog linter for Keep a Changelog format.

Enforces formatting rules for CHANGELOG.md files.

NOTE: Claude built this. Use with caution.
"""
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Violation:
    line_number: int
    rule: str
    message: str
    fixed: bool = False


VALID_SUBSECTIONS = ["Added", "Changed",
                     "Deprecated", "Fixed", "Removed", "Security"]
SUBSECTION_ORDER = {name: idx for idx, name in enumerate(VALID_SUBSECTIONS)}
MAX_LINE_LENGTH = 80

VERSION_HEADER_PATTERN = re.compile(
    r"^## \[(\d+\.\d+\.\d+|Unreleased)\](?: - \d{4}-\d{2}-\d{2})?$")
SUBSECTION_PATTERN = re.compile(r"^### (.+)$")
BULLET_PATTERN = re.compile(r"^- (.+)$")
ISSUE_REF_PATTERN = re.compile(r"\b(OCPSG-\d+|GC-\d+|AI-\d+|#\d+)\b")


class ChangelogLinter:
    def __init__(self, filepath: Path, fix: bool = False):
        self.filepath = filepath
        self.lines = filepath.read_text().splitlines()
        self.violations: List[Violation] = []
        self.fix = fix
        self.fixed_lines = None

    def lint(self) -> List[Violation]:
        """Run all linting rules."""
        self.check_version_headers()
        self.check_subsection_headers()
        self.check_subsection_order()
        self.check_bullet_formatting()
        self.check_issue_references()
        self.check_blank_lines()
        self.check_line_length()
        return self.violations

    def apply_fixes(self) -> str:
        """Apply all fixes and return the corrected content."""
        self.fixed_lines = self.lines.copy()

        # Fix bullet formatting (Rule 4 & 5)
        self._fix_bullet_formatting()

        # Fix issue references (Rule 8)
        self._fix_issue_references()

        # Fix subsection order (Rule 3)
        self._fix_subsection_order()

        # Fix line length (Rule 11)
        self._fix_line_length()

        # Fix blank lines (Rules 9 & 10) - must be last
        self._fix_blank_lines()

        return "\n".join(self.fixed_lines) + "\n"

    def check_version_headers(self):
        """Rule 1: Version headers must match the required format."""
        for i, line in enumerate(self.lines):
            if line.startswith("## ["):
                if not VERSION_HEADER_PATTERN.match(line):
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 1",
                            message=f"Invalid version header format: '{line}'",
                        )
                    )

    def check_subsection_headers(self):
        """Rule 2: Subsection headers must be valid types."""
        for i, line in enumerate(self.lines):
            match = SUBSECTION_PATTERN.match(line)
            if match:
                subsection_name = match.group(1)
                if subsection_name not in VALID_SUBSECTIONS:
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 2",
                            message=f"Invalid subsection name: '{
                                subsection_name}'. Must be one of: {', '.join(VALID_SUBSECTIONS)}",
                        )
                    )

    def check_subsection_order(self):
        """Rule 3: Subsections must appear in the standard order."""
        current_version_start = None
        subsections_in_version = []

        for i, line in enumerate(self.lines):
            if line.startswith("## ["):
                if current_version_start is not None and subsections_in_version:
                    self._validate_subsection_order(
                        current_version_start, subsections_in_version)
                current_version_start = i + 1
                subsections_in_version = []
            elif line.startswith("### "):
                match = SUBSECTION_PATTERN.match(line)
                if match:
                    subsection_name = match.group(1)
                    if subsection_name in VALID_SUBSECTIONS:
                        subsections_in_version.append((i + 1, subsection_name))

        if current_version_start is not None and subsections_in_version:
            self._validate_subsection_order(
                current_version_start, subsections_in_version)

    def _validate_subsection_order(self, version_line: int, subsections: List[tuple]):
        """Check if subsections are in the correct order."""
        orders = [SUBSECTION_ORDER[name] for line_num, name in subsections]
        if orders != sorted(orders):
            expected_order = sorted(
                subsections, key=lambda x: SUBSECTION_ORDER[x[1]])
            self.violations.append(
                Violation(
                    line_number=version_line,
                    rule="Rule 3",
                    message=f"Subsections out of order. Expected: {
                        ', '.join(name for _, name in expected_order)}",
                )
            )

    def check_bullet_formatting(self):
        """Rules 4 & 5: Bullets must start with '- ' and continuations with 2 spaces."""
        in_bullet = False
        bullet_start_line = None

        for i, line in enumerate(self.lines):
            if not line:
                in_bullet = False
                continue

            if line.startswith("## ") or line.startswith("### "):
                in_bullet = False
                continue

            if line.startswith("- "):
                in_bullet = True
                bullet_start_line = i + 1
                if line.startswith("-  "):
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 4",
                            message="Bullet has extra space after hyphen",
                        )
                    )
            elif line.startswith(" ") and in_bullet:
                if not line.startswith("  ") or line.startswith("   "):
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 5",
                            message=f"Continuation line must be indented with exactly 2 spaces",
                        )
                    )
            elif in_bullet and line and not line.startswith(" "):
                if not (line.startswith("## ") or line.startswith("### ")):
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 4",
                            message="Bullet item line has incorrect leading whitespace",
                        )
                    )
                in_bullet = False

    def check_issue_references(self):
        """Rules 6, 7, 8: Issue reference format and separation."""
        for i, line in enumerate(self.lines):
            if not line.startswith("- "):
                continue

            full_line = line
            line_num = i + 1

            while line_num < len(self.lines) and self.lines[line_num].startswith("  "):
                full_line += " " + self.lines[line_num].strip()
                line_num += 1

            refs = ISSUE_REF_PATTERN.findall(full_line)
            if not refs:
                continue

            # Check for proper spacing (but allow parentheses around references)
            for ref in refs:
                # Skip if in parentheses like (GC-145594, ...)
                if f"({ref}" in full_line or f", {ref}" in full_line or f" {ref}" in full_line or full_line.endswith(ref):
                    continue
                if f".{ref}" in full_line:
                    continue
                self.violations.append(
                    Violation(
                        line_number=i + 1,
                        rule="Rule 6",
                        message=f"Issue reference '{
                            ref}' must be separated from content by a single space",
                    )
                )

            # Check for missing space between references (but not in parentheses)
            if len(refs) > 1:
                for j in range(len(refs) - 1):
                    bad_pattern = f"{refs[j]},{refs[j+1]}"
                    if bad_pattern in full_line and f"({bad_pattern}" not in full_line:
                        self.violations.append(
                            Violation(
                                line_number=i + 1,
                                rule="Rule 8",
                                message="Multiple issue references must be separated by ', ' (comma + space)",
                            )
                        )

            # Check for trailing comma after last reference (but not if inside parentheses)
            if refs and full_line.rstrip().endswith(refs[-1] + ",") and not full_line.rstrip().endswith(")"):
                self.violations.append(
                    Violation(
                        line_number=i + 1,
                        rule="Rule 8",
                        message="Issue references must not have a trailing comma",
                    )
                )

    def check_blank_lines(self):
        """Rules 9 & 10: Blank lines between subsections and versions."""
        for i in range(len(self.lines)):
            if i == 0:
                continue

            line = self.lines[i]

            if line.startswith("### "):
                blank_count = 0
                j = i - 1
                while j >= 0 and not self.lines[j]:
                    blank_count += 1
                    j -= 1

                # Check if this is the first subsection after a version header
                is_first_subsection = j >= 0 and self.lines[j].startswith(
                    "## [")

                # Check if previous subsection was empty (no bullets)
                if j >= 0 and self.lines[j].startswith("### "):
                    # Previous line was also a subsection - it must have been empty
                    expected_blanks = 0
                else:
                    expected_blanks = 0 if is_first_subsection else 1

                if blank_count != expected_blanks:
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 9",
                            message=f"Subsection must be preceded by exactly {
                                expected_blanks} blank line(s) (found {blank_count})",
                        )
                    )

            if line.startswith("## [") and i > 0:
                blank_count = 0
                j = i - 1
                while j >= 0 and not self.lines[j]:
                    blank_count += 1
                    j -= 1

                # Check if this is right after the main header or preamble
                if j >= 0 and (self.lines[j].startswith("# ") or
                               any(self.lines[k].startswith("# ") for k in range(max(0, j - 5), j + 1))):
                    # Allow any number of blank lines after header/preamble
                    continue

                if blank_count != 2:
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 10",
                            message=f"Version section must be preceded by exactly 2 blank lines (found {
                                blank_count})",
                        )
                    )

    def check_line_length(self):
        """Rule 11: Bullet lines should not exceed max length."""
        for i, line in enumerate(self.lines):
            if line.startswith("- ") or line.startswith("  "):
                if len(line) > MAX_LINE_LENGTH:
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 11",
                            message=f"Line exceeds {
                                MAX_LINE_LENGTH} characters ({len(line)} characters)",
                        )
                    )

    def _fix_bullet_formatting(self):
        """Fix bullet and continuation line indentation."""
        in_bullet = False

        for i, line in enumerate(self.fixed_lines):
            # Track if we're in a bullet context
            if line.startswith("## ") or line.startswith("### ") or not line:
                in_bullet = False
                continue

            # Fix double space after bullet hyphen
            if line.startswith("-  ") and not line.startswith("-   "):
                self.fixed_lines[i] = line.replace("-  ", "- ", 1)
                self.violations.append(
                    Violation(
                        line_number=i + 1,
                        rule="Rule 4",
                        message="Fixed: Bullet had extra space after hyphen",
                        fixed=True,
                    )
                )
                in_bullet = True
            elif line.startswith("- "):
                in_bullet = True
            # Fix continuation line indentation
            elif in_bullet and line and not line.startswith("  ") and not line.startswith("## ") and not line.startswith("### "):
                # This should be a continuation line
                self.fixed_lines[i] = "  " + line.lstrip()
                self.violations.append(
                    Violation(
                        line_number=i + 1,
                        rule="Rule 4" if not line.startswith(
                            " ") else "Rule 5",
                        message="Fixed: Continuation line indentation",
                        fixed=True,
                    )
                )
            elif line.startswith("   "):
                # Too many spaces - check if it's a continuation
                if in_bullet:
                    self.fixed_lines[i] = "  " + line.lstrip()
                    self.violations.append(
                        Violation(
                            line_number=i + 1,
                            rule="Rule 5",
                            message="Fixed: Continuation line had too many spaces",
                            fixed=True,
                        )
                    )

    def _fix_issue_references(self):
        """Fix issue reference formatting."""
        for i, line in enumerate(self.fixed_lines):
            if not line.startswith("- ") and not line.startswith("  "):
                continue

            # Reconstruct full bullet (handle multi-line)
            full_line = line
            j = i + 1
            while j < len(self.fixed_lines) and self.fixed_lines[j].startswith("  "):
                full_line += " " + self.fixed_lines[j].strip()
                j += 1

            # Fix trailing comma after issue references
            refs = ISSUE_REF_PATTERN.findall(full_line)
            if refs:
                # Check if last ref is followed by comma at end
                last_ref = refs[-1]
                if full_line.rstrip().endswith(last_ref + ","):
                    # Remove trailing comma from the last line of this bullet
                    last_line_idx = i if j == i + 1 else j - 1
                    if self.fixed_lines[last_line_idx].rstrip().endswith(","):
                        self.fixed_lines[last_line_idx] = self.fixed_lines[last_line_idx].rstrip()[
                            :-1]
                        self.violations.append(
                            Violation(
                                line_number=i + 1,
                                rule="Rule 8",
                                message="Fixed: Removed trailing comma from issue references",
                                fixed=True,
                            )
                        )

            # Fix missing space between references (e.g., "OCPSG-1,OCPSG-2" -> "OCPSG-1, OCPSG-2")
            refs = ISSUE_REF_PATTERN.findall(self.fixed_lines[i])
            if len(refs) > 1:
                new_line = self.fixed_lines[i]
                for k in range(len(refs) - 1):
                    # Look for references without proper spacing
                    bad_pattern = f"{refs[k]},{refs[k+1]}"
                    if bad_pattern in new_line:
                        new_line = new_line.replace(
                            bad_pattern, f"{refs[k]}, {refs[k+1]}")
                        if new_line != self.fixed_lines[i]:
                            self.violations.append(
                                Violation(
                                    line_number=i + 1,
                                    rule="Rule 8",
                                    message="Fixed: Added space after comma in issue references",
                                    fixed=True,
                                )
                            )
                self.fixed_lines[i] = new_line

    def _fix_subsection_order(self):
        """Reorder subsections within each version."""
        i = 0
        while i < len(self.fixed_lines):
            if not self.fixed_lines[i].startswith("## ["):
                i += 1
                continue

            version_line = i
            i += 1

            # Find all subsections and their content for this version
            subsections = []
            current_subsection = None
            current_content = []

            while i < len(self.fixed_lines) and not self.fixed_lines[i].startswith("## ["):
                line = self.fixed_lines[i]

                if line.startswith("### "):
                    if current_subsection is not None:
                        subsections.append(
                            (current_subsection, current_content))
                    match = SUBSECTION_PATTERN.match(line)
                    if match:
                        current_subsection = (match.group(1), i)
                        current_content = [line]
                    else:
                        current_subsection = None
                        current_content = []
                elif current_subsection is not None:
                    current_content.append(line)
                else:
                    # Content before any subsection (keep as-is)
                    pass

                i += 1

            if current_subsection is not None:
                subsections.append((current_subsection, current_content))

            # Check if reordering is needed
            if subsections:
                valid_subsections = [
                    (name, line_num, content)
                    for (name, line_num), content in subsections
                    if name in VALID_SUBSECTIONS
                ]
                if valid_subsections:
                    orders = [SUBSECTION_ORDER[name]
                              for name, _, _ in valid_subsections]
                    if orders != sorted(orders):
                        # Need to reorder
                        sorted_subsections = sorted(
                            valid_subsections, key=lambda x: SUBSECTION_ORDER[x[0]])

                        # Find where subsections start
                        first_subsection_line = valid_subsections[0][1]

                        # Rebuild from the version header
                        new_section = []
                        for line_idx in range(version_line, first_subsection_line):
                            new_section.append(self.fixed_lines[line_idx])

                        # Add sorted subsections
                        for name, _, content in sorted_subsections:
                            new_section.extend(content)

                        # Replace in fixed_lines
                        end_line = i
                        self.fixed_lines[version_line:end_line] = new_section

                        self.violations.append(
                            Violation(
                                line_number=version_line + 1,
                                rule="Rule 3",
                                message=f"Fixed: Reordered subsections to standard order",
                                fixed=True,
                            )
                        )

    def _fix_line_length(self):
        """Fix lines that exceed max length by wrapping them."""
        result = []
        i = 0

        while i < len(self.fixed_lines):
            line = self.fixed_lines[i]

            # Only wrap bullet lines and continuation lines
            if not (line.startswith("- ") or line.startswith("  ")):
                result.append(line)
                i += 1
                continue

            if len(line) <= MAX_LINE_LENGTH:
                result.append(line)
                i += 1
                continue

            # Line needs wrapping
            if line.startswith("- "):
                # This is a bullet line
                prefix = "- "
                content = line[2:]
            else:
                # This is a continuation line
                prefix = "  "
                content = line[2:]

            # Find issue references at the end
            refs = ISSUE_REF_PATTERN.findall(content)
            suffix = ""
            if refs:
                # Check if refs are at the end (with possible punctuation/parens)
                for pattern in [
                    r'\s+' + r',\s+'.join(re.escape(r) for r in refs) + r'$',
                    r'\s+\(' + r',\s+'.join(re.escape(r)
                                            for r in refs) + r'\)$',
                ]:
                    match = re.search(pattern, content)
                    if match:
                        suffix = match.group(0)
                        content = content[:match.start()]
                        break

            # Wrap the content
            wrapped = self._wrap_text(
                content, MAX_LINE_LENGTH - len(prefix), suffix)

            # Add wrapped lines
            for j, wrapped_line in enumerate(wrapped):
                if j == 0:
                    result.append(prefix + wrapped_line)
                else:
                    result.append("  " + wrapped_line)

            self.violations.append(
                Violation(
                    line_number=i + 1,
                    rule="Rule 11",
                    message=f"Fixed: Wrapped line that exceeded {
                        MAX_LINE_LENGTH} characters",
                    fixed=True,
                )
            )

            i += 1

        self.fixed_lines = result

    def _wrap_text(self, text: str, max_width: int, suffix: str = "") -> List[str]:
        """Wrap text to max_width, preserving words. Add suffix to last line."""
        if not text.strip():
            return [suffix.lstrip()] if suffix else [""]

        words = text.split()
        if not words:
            return [suffix.lstrip()] if suffix else [""]

        lines = []
        current_line = []
        i = 0

        while i < len(words):
            word = words[i]
            test_line = " ".join(current_line + [word])

            # Check if this is the last word and if suffix fits
            is_last_word = (i == len(words) - 1)
            line_with_suffix = test_line + suffix if is_last_word else test_line

            if len(line_with_suffix) <= max_width:
                current_line.append(word)
                i += 1
            else:
                # Line would be too long
                if current_line:
                    # Check if we're about to create an orphan (single word on next line)
                    if i == len(words) - 1 and len(word + suffix) < max_width // 2:
                        # This is the last word and it's short - try to keep it with previous
                        # Only if removing one word from current line makes room
                        if len(current_line) > 1:
                            last_word = current_line.pop()
                            lines.append(" ".join(current_line))
                            current_line = [last_word, word]
                            i += 1
                        else:
                            lines.append(" ".join(current_line))
                            current_line = [word]
                            i += 1
                    else:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                        i += 1
                else:
                    # Single word exceeds max_width, add it anyway
                    lines.append(word)
                    current_line = []
                    i += 1

        if current_line:
            lines.append(" ".join(current_line) + suffix)
        elif suffix and lines:
            # Suffix didn't fit on last line, append to previous
            lines[-1] += suffix

        return lines

    def _fix_blank_lines(self):
        """Fix blank lines between subsections and versions."""
        result = []
        i = 0

        while i < len(self.fixed_lines):
            line = self.fixed_lines[i]

            # Handle version headers (Rule 10: need 2 blank lines before)
            if line.startswith("## ["):
                # Special case: first version or right after main header
                if i > 0 and not any(self.fixed_lines[j].startswith("# ") for j in range(max(0, i - 3), i)):
                    # Count preceding blank lines
                    blank_count = 0
                    j = len(result) - 1
                    while j >= 0 and result[j] == "":
                        blank_count += 1
                        j -= 1

                    if blank_count != 2:
                        # Remove existing blank lines
                        while result and result[-1] == "":
                            result.pop()
                        # Add exactly 2 blank lines
                        result.extend(["", ""])
                        self.violations.append(
                            Violation(
                                line_number=i + 1,
                                rule="Rule 10",
                                message=f"Fixed: Added 2 blank lines before version section",
                                fixed=True,
                            )
                        )

                result.append(line)
                i += 1
                continue

            # Handle subsection headers
            if line.startswith("### "):
                if result:  # Not at start of file
                    # Count preceding blank lines
                    blank_count = 0
                    j = len(result) - 1
                    while j >= 0 and result[j] == "":
                        blank_count += 1
                        j -= 1

                    # Check if this is the first subsection after a version header
                    is_first_subsection = j >= 0 and result[j].startswith(
                        "## [")

                    # Check if previous subsection was empty
                    prev_was_empty_subsection = j >= 0 and result[j].startswith(
                        "### ")

                    # Determine expected blank lines
                    if is_first_subsection or prev_was_empty_subsection:
                        expected_blanks = 0
                    else:
                        expected_blanks = 1

                    if blank_count != expected_blanks:
                        # Remove existing blank lines
                        while result and result[-1] == "":
                            result.pop()
                        # Add expected blank lines
                        for _ in range(expected_blanks):
                            result.append("")
                        self.violations.append(
                            Violation(
                                line_number=i + 1,
                                rule="Rule 9",
                                message=f"Fixed: Adjusted blank lines before subsection to {
                                    expected_blanks}",
                                fixed=True,
                            )
                        )

                result.append(line)
                i += 1
                continue

            # Regular line
            result.append(line)
            i += 1

        self.fixed_lines = result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Lint and format CHANGELOG.md files")
    parser.add_argument(
        "files",
        type=str,
        nargs="*",
        help="Path(s) to CHANGELOG.md file(s)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix formatting violations",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output, only return exit code",
    )

    args = parser.parse_args()

    # Pre-commit hook mode: files passed as arguments, always fix
    if args.files:
        changelog_files = [f for f in args.files if f.endswith("CHANGELOG.md")]
        if not changelog_files:
            return 0

        had_errors = False
        for filepath in changelog_files:
            path = Path(filepath)
            if not path.exists():
                continue

            # Read original content to detect changes
            original_content = path.read_text()

            linter = ChangelogLinter(path, fix=True)

            # Apply fixes in pre-commit mode
            fixed_content = linter.apply_fixes()
            path.write_text(fixed_content)

            # Re-lint after fixing to check for remaining violations
            linter_check = ChangelogLinter(path, fix=False)
            remaining_violations = linter_check.lint()

            if not args.quiet and fixed_content != original_content:
                print(f"Formatted {filepath}")

            if remaining_violations:
                if not args.quiet:
                    print(f"\n{len(remaining_violations)} violation(s) in {
                          filepath} could not be automatically fixed:\n")
                    for v in remaining_violations:
                        print(f"Line {v.line_number} [{v.rule}]: {v.message}")
                    print()
                had_errors = True

        return 1 if had_errors else 0

    # Standalone mode: single file with optional --fix flag
    else:
        file_path = Path("CHANGELOG.md")
        if not file_path.exists():
            print(f"Error: File 'CHANGELOG.md' not found", file=sys.stderr)
            return 1

        linter = ChangelogLinter(file_path, fix=args.fix)
        violations = linter.lint()

        if args.fix:
            # Apply fixes
            fixed_content = linter.apply_fixes()
            file_path.write_text(fixed_content)

            fixes = [v for v in linter.violations if v.fixed]
            unfixed = [v for v in violations if not any(
                f.line_number == v.line_number and f.rule == v.rule for f in fixes)]

            if not args.quiet:
                if fixes:
                    print(f"Fixed {len(fixes)} violation(s) in {file_path}")
                if unfixed:
                    print(
                        f"\n{len(unfixed)} violation(s) could not be automatically fixed:\n")
                    for v in unfixed:
                        print(f"Line {v.line_number} [{v.rule}]: {v.message}")
                    print()
                    return 1
                else:
                    if fixes:
                        print(f"✓ {file_path} now passes all checks")
                    else:
                        print(f"✓ {file_path} already passes all checks")
            return 0 if not unfixed else 1

        else:
            # Just lint, don't fix
            if violations:
                if not args.quiet:
                    print(f"Found {len(violations)} violation(s) in {
                          file_path}:\n")
                    for v in violations:
                        print(f"Line {v.line_number} [{v.rule}]: {v.message}")
                    print()
                return 1
            else:
                if not args.quiet:
                    print(f"✓ {file_path} passes all checks")
                return 0


if __name__ == "__main__":
    sys.exit(main())
