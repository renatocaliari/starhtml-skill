# starhtml-skill

> **Skill for AI coding agents** + static analyzer CLI for developing with [StarHTML](https://github.com/banditburai/starHTML).

StarHTML is a Python-first reactive web framework using Datastar.
This repo helps AI agents (Claude Code, OpenCode, Cursor, etc.) write correct StarHTML code
and catch framework-specific bugs before runtime.

---

## 🎯 Why CLI + Skill Instead of MCP or LSP?

This project follows the **Bash + Code philosophy**: agents already know Bash and Python—leverage that instead of adding protocol overhead.

| Approach | Token Cost | Composable | Extensible | Agent Knowledge |
|----------|------------|------------|------------|-----------------|
| **starhtml-skill (CLI + Skill)** | ~4.5k tokens | ✅ Output to files, chain commands | ✅ Single Python file | ✅ Bash + Python |
| MCP Server | High (protocol + tools) | ❌ Must pass through agent context | ❌ Full codebase to understand | ❌ MCP-specific protocol |
| LSP | High (config + capabilities) | ❌ Tied to editor/IDE | ❌ Language server protocol | ❌ LSP-specific protocol |

### Advantages of This Approach

**1. Token Efficient**
- Skill file: ~4.5k tokens (SKILL.md is 14.7KB) — one-time load
- Checker output: concise, structured, designed for LLM loops
- No protocol overhead—just Python and CLI
- MCP/LSP require additional context for protocol configuration and tool definitions

**2. Composable**
```bash
# Chain commands, save to files, integrate anywhere
starhtml_check component.py --summary > issues.txt
starhtml_check --fix f.py && git commit -m "fix: $(cat issues.txt)

Co-authored-by: Qwen-Coder <qwen-coder@alibabacloud.com>"
```

**3. Extensible**
- Single Python file (`starhtml_check.py`) — no dependencies
- Add new rules in minutes, not hours
- Agents can read and modify the checker itself

**4. Agent-Agnostic**
- Works with any coding agent (Claude Code, Cursor, OpenCode, Qwen, etc.)
- No MCP host required
- No LSP server configuration
- Load skill via `npx skills add` or manual install

**5. Framework-Specific Intelligence**
- Catches StarHTML-specific bugs (reactivity, signal naming, f-string traps)
- Locality of Behavior checks (W028, W030) — LSP can't detect these
- HTTP action validation, plugin registration, SSE handler resets
- Designed for the way StarHTML actually works, not generic Python linting

For StarHTML development with AI agents, **CLI + Skill** is simpler, faster, and more flexible.

---

## 🤖 For AI Agents

### Recommended: Install via `npx skills`

```bash
# Install the skill using the skills manager
npx skills add renatocaliari/starhtml-skill
```

This will:
1. Download this repository
2. Find `skills/starhtml/SKILL.md` (where `name: starhtml`)
3. Install to `~/.agents/skills/starhtml/` (or project-level `.agents/skills/`)

### Manual Installation (alternative)

If you prefer manual installation:

```bash
# Clone to skills directory
git clone https://github.com/renatocaliari/starhtml-skill.git ~/.agents/skills/starhtml-temp

# Move the skill to correct location (name must match directory)
mv ~/.agents/skills/starhtml-temp/skills/starhtml ~/.agents/skills/starhtml
rm -rf ~/.agents/skills/starhtml-temp
```

Then load the skill based on your agent:
- **Claude Code**: Already loads from `~/.claude/skills/` or `.claude/skills/`
- **OpenCode**: Add to `opencode.json`: `{"instructions": ["~/.opencode/skills/starhtml/SKILL.md"]}`
- **Cursor**: Create `.cursor/rules/starhtml.mdc` with SKILL.md content
- **Other agents**: Load `~/.agents/skills/starhtml/SKILL.md` + `reference/*.md` as context

---

## 🔧 Install the Checker

**Option A — Global install (recommended):**
```bash
# macOS / Linux - system-wide (may require sudo)
curl -L https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py -o /usr/local/bin/starhtml_check && chmod +x /usr/local/bin/starhtml_check

# Or user-local (no sudo required)
curl -L https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py -o ~/.local/bin/starhtml_check && chmod +x ~/.local/bin/starhtml_check
```

**Option B — pip install:**
```bash
pip install git+https://github.com/renatocaliari/starhtml-skill.git
```

**Option C — Local download (per-project):**
```bash
curl -O https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py
```

---

## 📋 Usage

```bash
# If installed globally:
starhtml_check component.py           # full analysis
starhtml_check --summary f.py         # compact output
starhtml_check --fix f.py             # auto-fix safe issues
starhtml_check --help-llm             # full guide + all error codes

# If downloaded locally:
python starhtml_check.py component.py
python starhtml_check.py --summary f.py
python starhtml_check.py --fix f.py
```

**Loop:** write → check → fix ERRORs → re-run → ✓ no issues

---

## 📦 Repository Structure

```
starhtml-skill/
├── starhtml_check.py        # static analyzer CLI (zero dependencies)
├── pyproject.toml           # for pip install
├── skills/                  # skills directory (for npx skills add)
│   └── starhtml/
│       ├── SKILL.md         # core skill — load this first
│       └── reference/       # sub-references (load on demand)
│           ├── demos.md     # index of 30 official demo files
│           ├── icons.md     # Icon() component reference
│           ├── js.md        # js(), f(), value(), regex() reference
│           ├── handlers.md  # plugins: persist, scroll, motion, drag, canvas...
│           └── slots.md     # slot system reference
└── README.md                # this file
```

---

## ⚡ Quick Reference

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

## 📝 Error Codes Reference

### Errors (must fix — broken code, do not ship)

| Code | Issue |
|------|-------|
| E001 | Positional arg after keyword — Python SyntaxError |
| E002 | f-string in reactive attr — static, won't update in browser |
| E003 | f-string URL in HTTP action — Python-static, not reactive |
| E004 | Special chars (`:` `/` `[` `]`) in `data_class_*` — parse error |
| E005 | camelCase Signal name — must be snake_case |
| E006 | `f()` helper used without import — NameError at runtime |
| E007 | `data_attr_class` and `data_attr_cls` on same element — different behaviors |
| E008 | Walrus `:=` Signal without outer parentheses — breaks reactivity |
| E009 | `data_show` without flash prevention — element flashes before JS loads |
| E010 | Form submit without `is_valid` guard — submits invalid data |
| E011 | `data_on_scroll`/`data_on_input` without throttle/debounce — performance bug |
| E012 | `@sse` endpoint without `yield signals()` reset — client state not cleaned |
| E013 | `Icon()` without explicit size — inherits 1em from font-size |
| E014 | `js()` raw JavaScript — potential security risk |
| E015 | Plugin data attribute used without plugin registration |
| E016 | `data_on_submit` with `post()` without `{"prevent": True}` — page reloads |

### Warnings (should fix — review, may be intentional)

| Code | Issue |
|------|-------|
| W003 | 3+ signals with `&` operator — prefer `all()` for readability |
| W008 | Signal name too short — prefer descriptive snake_case names |
| W012 | Signal with empty name — use descriptive snake_case names |
| W015 | `delete()` HTTP action without confirmation — data loss risk |
| W016 | Signal used but not defined — will cause runtime error |
| W017 | Computed Signal detected — auto-updates on dependencies |
| W018 | `_ref_only=True` Signal — excluded from `data-signals` (correct) |
| W019 | f-string in `elements()` selector — verify selector is static |
| W020 | `elements()` replace-mode without explicit `id` — may not be targetable |
| W021 | `switch()` used for CSS classes — use `collect()` to combine |
| W022 | `collect()` used for exclusive logic — use `switch()` or `if_()` |
| W023 | `.then()` without conditional signal — verify boolean signal is used |
| W024 | `data_effect` without `.set()` — use `signal.set(expression)` |
| W025 | Component function without `**kwargs` — limits pass-through attributes |
| W026 | `f()` helper with < 3 signals — prefer `+` operator for 1-2 signals |
| W027 | File > 400 lines — consider splitting into smaller modules |
| W028 | Deep nesting (>3 levels) — extract to sub-component for better LoB |
| W029 | Signal not used in backend without `_` prefix — indicate frontend-only |
| W030 | `js()` that StarHTML can handle — Locality of Behavior violation |

---

## 🤝 Contributing

Issues and PRs welcome.

For new checker rules, include:
- The bug it prevents (real example)
- `GOT:` example of wrong code
- `FIX:` example of corrected code

For skill improvements, test with at least one LLM agent before submitting.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
