# ACE for Claude Code

**Agentic Context Engineering** - A lightweight, file-based approach to make Claude Code learn and improve across sessions.

## What is ACE?

ACE enables Claude to build a "playbook" of strategies, domain knowledge, and lessons learned that persists across sessions. Instead of starting fresh each time, Claude reads previous learnings and applies them automatically.

Based on the [ACE research paper](https://arxiv.org/abs/2510.04618) from Stanford & SambaNova.

## How It Works

```
Session 1: Claude solves problem → reflects → adds insight to playbook
Session 2: Claude reads playbook → applies learnings → solves faster → adds new insights
Session N: Claude has accumulated project-specific expertise
```

## Architecture

```
~/.claude/
└── skills/
    └── ace/
        └── SKILL.md              # Global ACE skill (works in all projects)

Your Project/
├── CLAUDE.md                     # Project config (references ACE)
└── .ace/
    ├── playbook.md               # Project-specific learnings
    └── reflections.jsonl         # Detailed reflection log
```

## Installation

### 1. Create the ACE Skill

```bash
mkdir -p ~/.claude/skills/ace
```

Create `~/.claude/skills/ace/SKILL.md`:

```markdown
# ACE - Agentic Context Engineering

## Activation
Activate when user says "/ace", "start learning", or at session start if .ace/ directory exists in project.

## On Session Start
If `.ace/playbook.md` exists in project root:
1. Read it silently
2. Apply strategies to this session
3. Briefly note: "ACE active"

## During Session
After completing any significant task:
1. Reflect: What worked? What didn't?
2. If new generalizable insight discovered, append to `.ace/playbook.md`
3. Format: `[prefix-NNNNN] helpful=0 harmful=0 :: insight`

Prefixes:
- `str` - Strategies (approaches that work)
- `dom` - Domain knowledge (project-specific facts)
- `mis` - Mistakes to avoid
- `cal` - Calculations/formulas

## On Task Failure
1. Log to `.ace/reflections.jsonl`:
   {"ts": "ISO8601", "task": "description", "error": "what failed", "insight": "lesson"}
2. If pattern identified, add to playbook

## Quality Filter
Only add entries that are:
- Generalizable (not one-off fixes)
- Actionable (concrete guidance)
- Non-obvious (Claude wouldn't know by default)

## Counter Updates
When an entry helps: increment helpful count
When an entry causes issues: increment harmful count

## Curation
When playbook exceeds 50 entries or on "/ace curate":
- Remove entries where harmful > helpful + 3
- Merge duplicates
- Archive stale entries

## Commands
- `/ace` - Trigger manual reflection
- `/ace curate` - Clean up playbook
- `/ace status` - Show playbook stats
```

### 2. Create the Init Script

```bash
mkdir -p ~/bin

cat > ~/bin/ace-init << 'EOF'
#!/bin/bash
# ace-init - Enable ACE in any project

mkdir -p .ace

cat > .ace/playbook.md << 'PLAYBOOK'
# ACE Playbook

## Strategies

## Domain Knowledge

## Mistakes to Avoid

## Calculations/Formulas
PLAYBOOK

touch .ace/reflections.jsonl

# Add ACE section to CLAUDE.md if not present
if [ ! -f CLAUDE.md ]; then
  echo "# $(basename $(pwd))" > CLAUDE.md
fi

if ! grep -q "ACE Integration" CLAUDE.md 2>/dev/null; then
  cat >> CLAUDE.md << 'CLAUDE'

## ACE Integration
This project uses ACE for continuous learning. 
On session start, read `.ace/playbook.md` silently and apply learnings.

Commands:
- `/ace` - Trigger reflection on recent work
- `/ace curate` - Clean up the playbook
- `/ace status` - Show playbook statistics
CLAUDE
fi

# Add .ace to .gitignore if using git
if [ -d .git ] && [ -f .gitignore ]; then
  if ! grep -q "^\.ace/$" .gitignore 2>/dev/null; then
    echo ".ace/" >> .gitignore
    echo "Added .ace/ to .gitignore"
  fi
fi

echo "✓ ACE initialized in $(pwd)"
echo "  Run 'claude' to start a learning session"
EOF

chmod +x ~/bin/ace-init
```

Add `~/bin` to PATH if needed:

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

### Initialize ACE in a Project

```bash
cd ~/my-project
ace-init
```

### Start Claude Code

```bash
claude
```

Claude will automatically:
1. Detect `.ace/` directory
2. Read `playbook.md`
3. Apply learnings to the session
4. Add new insights as work progresses

### Manual Commands

```
/ace              # Reflect on recent work, update playbook
/ace curate       # Clean up playbook (remove bad entries, merge duplicates)
/ace status       # Show playbook statistics
```

## Playbook Format

```markdown
# ACE Playbook

## Strategies
[str-00001] helpful=5 harmful=0 :: Always run tests before committing in this repo
[str-00002] helpful=3 harmful=1 :: Use TypeScript strict mode for new files

## Domain Knowledge
[dom-00001] helpful=4 harmful=0 :: API rate limit is 100 req/min, use exponential backoff
[dom-00002] helpful=2 harmful=0 :: Database migrations require DOWN migration for rollback

## Mistakes to Avoid
[mis-00001] helpful=0 harmful=0 :: Don't modify package-lock.json manually
[mis-00002] helpful=2 harmful=0 :: The /legacy endpoint requires auth header even for public data

## Calculations/Formulas
[cal-00001] helpful=1 harmful=0 :: Retry delay = min(base * 2^attempt, max_delay)
```

## Reflection Log Format

`.ace/reflections.jsonl` stores detailed reflections:

```json
{"ts":"2024-12-17T15:30:00Z","task":"fix auth bug","outcome":"success","insight":"Token refresh was failing silently - always log auth errors"}
{"ts":"2024-12-17T16:45:00Z","task":"add rate limiting","outcome":"partial","error":"Redis connection timeout","insight":"Need connection pooling for Redis in this environment"}
```

## Best Practices

1. **Let it accumulate naturally** - Don't force entries. Quality over quantity.

2. **Review periodically** - Run `/ace curate` weekly to clean up.

3. **Project-specific** - Each project gets its own `.ace/` directory. Learnings are contextual.

4. **Git ignore** - Add `.ace/` to `.gitignore`. Learnings are personal/local.

5. **Trust the counters** - Entries that consistently cause issues get removed automatically.

## Comparison with MCP-based ACE

| Feature | File-based (this) | MCP Server |
|---------|-------------------|------------|
| Setup | Zero config | Requires server |
| Works offline | ✓ | ✗ |
| Cross-device sync | ✗ | ✓ (via D1) |
| Claude.ai support | ✗ | ✓ |
| Git trackable | ✓ | ✗ |
| Multi-project global | ✗ | ✓ |

**Recommendation**: Use file-based for Claude Code, MCP server for Claude.ai web interface.

## Troubleshooting

**Claude doesn't read the playbook**
- Ensure `.ace/playbook.md` exists
- Check CLAUDE.md mentions ACE
- Verify skill is in `~/.claude/skills/ace/SKILL.md`

**Playbook getting too large**
- Run `/ace curate`
- Manually remove stale entries
- Increase quality threshold

**Entries not being added**
- Claude filters aggressively for quality
- Prompt with `/ace` after completing significant work

## License

MIT

## Credits

- [ACE Paper](https://arxiv.org/abs/2510.04618) - Stanford & SambaNova
- [Kayba ACE Framework](https://github.com/kayba-ai/agentic-context-engine) - Python implementation
- Anthropic - Claude Code
