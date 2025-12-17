# ACE Playbook Format Specification

## Overview

The playbook is a structured markdown file containing learnings that evolve through use. Each entry is tracked with counters to enable automated curation.

## File Location

Default: `~/.ace/playbook.md`

For multi-project setups with D1, entries are stored in SQLite with `project_id` field.

## Structure

```markdown
## SECTION NAME
[prefix-00001] helpful=N harmful=M :: Content text here

## ANOTHER SECTION
[prefix-00002] helpful=N harmful=M :: Another entry
```

## Entry Format

```
[{prefix}-{id}] helpful={n} harmful={m} :: {content}
```

| Component | Format | Description |
|-----------|--------|-------------|
| prefix | 3 lowercase letters | Section type identifier |
| id | 5 digits, zero-padded | Unique sequential ID |
| helpful | integer ≥ 0 | Times entry proved useful |
| harmful | integer ≥ 0 | Times entry was misleading |
| content | free text | The actual insight/strategy |

### Prefix Types

| Prefix | Section |
|--------|---------|
| `str` | STRATEGIES & INSIGHTS |
| `cal` | FORMULAS & CALCULATIONS |
| `mis` | COMMON MISTAKES TO AVOID |
| `dom` | DOMAIN KNOWLEDGE |

### Examples

```markdown
[str-00001] helpful=5 harmful=0 :: Always verify data types before processing
[cal-00003] helpful=8 harmful=0 :: NPV = Σ(Cash Flow / (1+r)^t)
[mis-00012] helpful=6 harmful=1 :: Don't forget timezone conversions in datetime comparisons
[dom-00007] helpful=3 harmful=0 :: UK FCA requires firms to maintain transaction records for 5 years
```

## Sections

### STRATEGIES & INSIGHTS
Mental models, approaches, heuristics that improve task execution.

**Good entries:**
- "Break complex problems into smaller, testable units"
- "When debugging, reproduce the issue first before attempting fixes"

**Bad entries (too vague):**
- "Be careful"
- "Think before acting"

### FORMULAS & CALCULATIONS
Repeatable computations, algorithms, mathematical relationships.

**Good entries:**
- "Compound Annual Growth Rate: CAGR = (End/Start)^(1/years) - 1"
- "Levenshtein distance for fuzzy string matching: min edits to transform A→B"

### COMMON MISTAKES TO AVOID
Pitfalls, antipatterns, gotchas learned from failures.

**Good entries:**
- "pandas .copy() required when modifying DataFrame slices to avoid SettingWithCopyWarning"
- "JavaScript Date months are 0-indexed (January = 0)"

**Bad entries (too specific):**
- "Don't use variable name 'x' in the login function"

### DOMAIN KNOWLEDGE
Facts, regulations, definitions specific to a domain.

**Good entries:**
- "GDPR Article 17: Right to erasure applies only to personal data, not anonymized data"
- "S&P 500 rebalances quarterly on the third Friday of March, June, September, December"

## Counter Logic

### When to Increment Helpful
- Entry directly contributed to successful task completion
- Entry prevented a mistake that would have occurred
- Entry provided useful framing or approach

### When to Increment Harmful
- Entry led to incorrect approach
- Entry was misleading in current context
- Following entry caused errors or rework

### Curation Threshold
Default rule: Remove entry when `harmful > helpful + 3`

This allows entries to survive occasional failures while pruning consistently bad advice.

## Multi-Project Architecture

### Project IDs
- `global` - Universal patterns applicable everywhere
- Domain-specific IDs: `finance`, `dev`, `legal`, etc.

### Inheritance
When reading playbook for project X:
1. Fetch all entries where `project_id = 'global'`
2. Fetch all entries where `project_id = 'X'`
3. Merge, with global entries first in each section

### Write Targeting
- Universal patterns → `global`
- Domain-specific knowledge → specific project_id

## Quality Criteria

Only add entries that pass all three:

1. **Generalizable** - Applies beyond the immediate task
2. **Actionable** - Specific enough to apply in practice
3. **Non-obvious** - Not common knowledge the model already has

### Anti-patterns

| Don't Add | Why |
|-----------|-----|
| "Check your work" | Too vague, obvious |
| "The API key was abc123" | Not generalizable, sensitive |
| "Python uses indentation" | Common knowledge |
| "Remember to save files" | Obvious |

## ID Generation

IDs are assigned sequentially per prefix:
1. Parse existing entries to find highest ID per prefix
2. New entry gets `max_id + 1`
3. Zero-pad to 5 digits

Example: If `str-00007` is highest strategy entry, next is `str-00008`

## File Integrity

- UTF-8 encoding
- Unix line endings (LF)
- No trailing whitespace on entry lines
- Single blank line between sections
- No duplicate IDs (enforced by curation)
