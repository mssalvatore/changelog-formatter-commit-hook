# Changelog Formatter Commit Hook

## Description
This is a pre-commit hook that automatically formats `CHANGELOG.md` files according to the [Keep a Changelog](https://keepachangelog.com/) standard.

The formatter enforces the following rules:
1. Version headers in the format `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD` or `## [Unreleased]`
2. Valid subsection headers: `Added`, `Changed`, `Deprecated`, `Fixed`, `Removed`, `Security`
3. Subsections in standard order
4. Bullet items start with `- ` (hyphen + single space)
5. Continuation lines indented with exactly 2 spaces
6. Issue references at the end of entries (e.g., `JIRA-1234`, `#123`)
7. Multiple references separated by `, ` (no trailing comma)
8. No blank line between version header and first subsection
9. No blank line after empty subsection headers
10. 1 blank line between subsections with content
11. 2 blank lines between version sections
12. Lines wrapped at 80 characters

The hook automatically fixes all violations when you commit changes to `CHANGELOG.md`.

## Warning!!!

Claude built this. Use with caution.

## Installation

Add the following to your `.pre-commit-config.yaml`:
```yaml
  - repo: https://github.com/mssalvatore/changelog-formatter-commit-hook
    rev: v1.0.0
    hooks:
      - id: changelog-formatter
```

Then run:
```bash
pre-commit install
```

## Example

Before formatting:
```markdown
## [1.0.0] - 2024-01-01
### Added
- A really long feature description that exceeds the maximum line length and needs to be wrapped properly. JIRA-123
### Fixed
- Bug fix JIRA-456,JIRA-789
```

After formatting:
```markdown
## [1.0.0] - 2024-01-01
### Added
- A really long feature description that exceeds the maximum line length and
  needs to be wrapped properly. JIRA-123

### Fixed
- Bug fix JIRA-456, JIRA-789
```

## License
GPLv3
