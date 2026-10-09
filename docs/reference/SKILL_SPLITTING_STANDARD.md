# Standard for Splitting Large Skills

**Date:** 2026-10-09  
**Purpose:** Unified approach to splitting skills exceeding 500 lines into multiple files

---

## Structure

Each skill directory (`skills/<skill-name>/`) contains:

```
skills/<skill-name>/
├── SKILL.md          # Core file (≤500 lines) — required
├── advanced.md       # Advanced patterns, edge cases, deep dives — optional
└── examples.md       # Code examples, case studies, templates — optional
```

---

## File Responsibilities

### SKILL.md (Core — ≤500 lines)

**Must contain:**
1. YAML frontmatter (name, description, paths, priority)
2. Core patterns (top 5-7 most important patterns)
3. Key pitfalls (top 5-7 critical mistakes)
4. Quick reference tables
5. Links to additional files:

```markdown
## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates
```

**Must NOT contain:**
- Extensive code examples (move to examples.md)
- Deep dives into edge cases (move to advanced.md)
- Lengthy explanations beyond core patterns

### advanced.md (Optional)

**Contains:**
- Advanced patterns beyond the core 5-7
- Edge cases and special scenarios
- Deep dives into complex topics
- Performance considerations
- Migration guides
- Troubleshooting

**Structure:**
```markdown
# Advanced Patterns: <Skill Name>

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## <Advanced Pattern 1>
...

## <Advanced Pattern 2>
...
```

### examples.md (Optional)

**Contains:**
- Complete working code examples
- Templates and boilerplate
- Case studies (before/after)
- Integration examples
- Testing examples

**Structure:**
```markdown
# Code Examples: <Skill Name>

> This file provides working examples for [`SKILL.md`](SKILL.md).

## Example 1: <Basic Usage>
```python
# code here
```

## Example 2: <Advanced Usage>
```python
# code here
```
```

---

## Splitting Guidelines

### What stays in SKILL.md:
- Pattern name + 1-2 sentence description
- Key code snippet (≤10 lines)
- Critical pitfall + fix
- Quick reference table

### What moves to advanced.md:
- Pattern variations and edge cases
- Deep technical explanations
- Performance implications
- Migration strategies
- Complex scenarios

### What moves to examples.md:
- Complete working examples (>10 lines)
- Full templates
- Before/after comparisons
- Integration patterns
- Test cases

---

## Target Sizes

| File | Target | Hard Limit |
|------|:------:|:----------:|
| SKILL.md | 300-400 lines | 500 lines |
| advanced.md | 200-400 lines | 600 lines |
| examples.md | 200-400 lines | 600 lines |

---

## Cross-References

**From SKILL.md:**
```markdown
## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md)
- **Code examples:** See [`examples.md`](examples.md)
```

**From advanced.md:**
```markdown
> This file extends [`SKILL.md`](SKILL.md) with advanced patterns.
```

**From examples.md:**
```markdown
> Working examples for [`SKILL.md`](SKILL.md).
```

---

## Checklist

Before finalizing the split:
- [ ] SKILL.md ≤ 500 lines
- [ ] SKILL.md contains top 5-7 core patterns
- [ ] SKILL.md links to advanced.md and examples.md
- [ ] advanced.md starts with link back to SKILL.md
- [ ] examples.md starts with link back to SKILL.md
- [ ] No duplicate content between files
- [ ] Code examples are complete and working
- [ ] Cross-references are correct

---

## Skills to Split (12 files)

| Skill | Current Lines | Target Structure |
|-------|:-------------:|------------------|
| javascript-typescript-professional | 1179 | SKILL.md + advanced.md + examples.md |
| kotlin-professional | 1049 | SKILL.md + advanced.md + examples.md |
| database-patterns | 1010 | SKILL.md + advanced.md + examples.md |
| java-professional | 913 | SKILL.md + advanced.md + examples.md |
| python-professional | 899 | SKILL.md + advanced.md + examples.md |
| api-design-principles | 899 | SKILL.md + advanced.md + examples.md |
| observability-patterns | 889 | SKILL.md + advanced.md + examples.md |
| ci-cd-patterns | 888 | SKILL.md + advanced.md + examples.md |
| secure-coding-patterns | 790 | SKILL.md + advanced.md + examples.md |
| performance-optimization | 728 | SKILL.md + advanced.md + examples.md |
| testing-patterns | 719 | SKILL.md + advanced.md + examples.md |
| git-workflow-patterns | 630 | SKILL.md + advanced.md |

---

## Notes

- Maintain consistent formatting across all skills
- Preserve all existing content — do not delete, only reorganize
- Ensure code examples are syntactically correct
- Test cross-references after splitting
- Update SKILL.md "See also" section if present
