# starhtml-skill

> **Skill for AI coding agents** + static analyzer CLI for developing with [StarHTML](https://github.com/banditburai/starHTML).

StarHTML is a Python-first framework for building reactive web applications using Datastar.
This repo helps AI agents (Claude Code, OpenCode, Cursor, etc.) write correct StarHTML code
and catch framework-specific bugs before runtime.

---

## 🤖 For AI Agents

If you are an AI agent reading this repo:

### Step 1 — Install the Skill

Clone this repo to your skills directory and load `starhtml/SKILL.md`:

```bash
# Personal skill (all projects)
git clone https://github.com/renatocaliari/starhtml-skill.git ~/.agents/skills/starhtml

# Or project skill (shared with team)
git clone https://github.com/renatocaliari/starhtml-skill.git .agents/skills/starhtml
```

Then load the skill:
- **Claude Code**: Already loads from `~/.claude/skills/` or `.claude/skills/`
- **OpenCode**: Add to `opencode.json`: `{"instructions": ["~/.opencode/skills/starhtml/starhtml/SKILL.md"]}`
- **Cursor**: Create `.cursor/rules/starhtml.mdc` with SKILL.md content
- **Other agents**: Load `starhtml/SKILL.md` + `starhtml/reference/*.md` as context

### Step 2 — Install the Checker

```bash
# Option A: pip install
pip install git+https://github.com/renatocaliari/starhtml-skill.git

# Option B: single file (zero dependencies)
curl -O https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py
```

### Step 3 — Use in Development Loop

After generating any StarHTML component:

```bash
python starhtml_check.py component.py      # full analysis
python starhtml_check.py --summary f.py    # compact output (fewer tokens)
python starhtml_check.py --fix f.py        # auto-fix safe issues
```

**Loop:** write → check → fix ERRORs → re-run → ✓ no issues

---

## What's Included

```
starhtml-skill/
├── starhtml_check.py        # static analyzer CLI (zero dependencies)
└── starhtml/                # agent skill
    ├── SKILL.md             # core skill — load this first
    └── reference/           # sub-references (load on demand)
        ├── demos.md         # index of 30 official demo files
        ├── icons.md         # Icon() component reference
        ├── js.md            # js(), f(), value(), regex() reference
        ├── handlers.md      # plugins: persist, scroll, motion, drag, canvas...
        └── slots.md         # slot system reference
```

---

## Quick Reference

### StarHTML Basics

```python
from starhtml import *

# Define reactive state (walrus := in outer parens)
(counter := Signal("counter", 0))
(name    := Signal("name", ""))
(visible := Signal("visible", True))

# Reactive attributes
data_show=visible              # show/hide
data_text=name                 # display value
data_bind=name                 # two-way binding
data_class_active=visible      # toggle class

# Events
data_on_click=counter.add(1)
data_on_input=(search, {"debounce": 300})
data_on_submit=(post("/api/save"), {"prevent": True})

# Signal operations
counter.add(1)                 # increment
counter.set(0)                 # assign
visible.toggle()               # boolean flip
name.upper()                   # string method
count.default(0)               # nullish fallback
theme.one_of("light", "dark")  # enum guard
```

### The 5 Rules

1. **No f-strings in reactive attrs** → use `+` or `f()` helper
2. **data_show needs flash prevention** → `style="display:none"`
3. **Positional args BEFORE keywords** → `Div("Hello", cls="container")`
4. **Signal names must be snake_case** → `my_count`, not `myCount`
5. **Walrus `:=` in outer parens** → `(name := Signal("name", ""))`

---

## Error Codes Reference

### Errors (must fix)

| Code | Issue |
|------|-------|
| E001 | Positional arg after keyword — Python SyntaxError |
| E002 | f-string in reactive attr — static, won't update |
| E003 | f-string URL in HTTP action — not reactive |
| E004 | Special chars in `data_class_*` — parse error |
| E005 | camelCase Signal name — must be snake_case |
| E006 | `f()` helper without import — NameError |
| E007 | `data_attr_class` + `data_attr_cls` — confusion |

### Warnings (should fix)

| Code | Issue |
|------|-------|
| W001 | `data_show` without flash prevention |
| W002 | Form submit without `is_valid` guard |
| W003 | Walrus `:=` without outer parens |
| W004 | Scroll/input without throttle/debounce |
| W005 | `@sse` without `yield signals()` reset |
| W006 | `Icon()` without explicit size |
| W007 | `js()` raw — verify no user input |
| W008 | Signal name too short |

### Info (informational)

| Code | Issue |
|------|-------|
| I001 | Computed Signal (auto-updates) |
| I002 | `elements()` replace-mode — check id |
| I003 | `delete()` — ensure confirmation UX |
| I004 | `_ref_only=True` — excluded from HTML |

---

## Contributing

Issues and PRs welcome.

For new checker rules, include:
- The bug it prevents (real example)
- `GOT:` example of wrong code
- `FIX:` example of corrected code

For skill improvements, test with at least one LLM agent before submitting.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
