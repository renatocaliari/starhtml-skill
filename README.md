# starhtml-llm

Skill for AI coding agents + static analyzer CLI for developing with [StarHTML](https://github.com/banditburai/starHTML).

StarHTML is a Python-first framework for building reactive web applications using Datastar.
This repo helps AI agents (Claude Code, OpenCode, Cursor, etc.) write correct StarHTML code
and catch framework-specific bugs before runtime.

---

## What's included

    starhtml-llm/
    ├── starhtml_check.py        static analyzer CLI (zero dependencies)
    └── starhtml/                agent skill
        ├── SKILL.md             core skill — loaded by agents automatically
        └── reference/           sub-references loaded on demand
            ├── demos.md         index of 30 official demo files with descriptions
            ├── icons.md         Icon() component reference
            ├── js.md            js(), f(), value(), regex() reference
            ├── handlers.md      built-in handlers reference
            └── slots.md         slot system reference

---

## Install the skill

> **Note on paths:** `~/.agents/skills/` is an emerging cross-agent convention.
> Individual agents also support their own paths. Use whichever matches your setup.

**Option A — Personal skill (all your projects)**

    git clone https://github.com/renatocaliari/starhtml-llm.git \
      ~/.agents/skills/starhtml

**Option B — Project skill (shared with team)**

    git clone https://github.com/renatocaliari/starhtml-llm.git \
      .agents/skills/starhtml

**Option C — OpenCode (personal)**

    git clone https://github.com/renatocaliari/starhtml-llm.git \
      ~/.opencode/skills/starhtml

Then add to your `opencode.json`:

    {
      "instructions": ["~/.opencode/skills/starhtml/starhtml/SKILL.md"]
    }

**Option D — Claude Code (personal)**

    git clone https://github.com/renatocaliari/starhtml-llm.git \
      ~/.claude/skills/starhtml

**Option E — Manual (any agent)**

Copy `starhtml/SKILL.md` and `starhtml/reference/` into either:
- `~/.agents/skills/starhtml/` (personal — all projects)
- `.agents/skills/starhtml/` (project — shared with team)

Then configure your agent to load skills from that path.

**Update to latest version**

    cd ~/.agents/skills/starhtml   # or wherever you installed
    git pull

---

## Install the checker

**Option A — pip install**

    pip install git+https://github.com/renatocaliari/starhtml-llm.git

**Option B — single file (zero dependencies)**

    # Get the file
    curl -O https://raw.githubusercontent.com/renatocaliari/starhtml-llm/main/starhtml_check.py

    # Or clone the whole repo
    git clone https://github.com/renatocaliari/starhtml-llm.git
    cd starhtml-llm

**Run after every component:**

    python starhtml_check.py component.py      # full analysis
    python starhtml_check.py --summary f.py    # compact output (fewer tokens for LLMs)
    python starhtml_check.py --fix f.py        # auto-fix safe issues, print result
    python starhtml_check.py --code "Div(...)" # analyze inline snippet
    python starhtml_check.py --help-llm        # full LLM integration guide

**LLM loop:**

    write component → starhtml_check.py file.py → fix ERRORs → re-run → ✓ no issues → done

---

## Error codes reference

### Errors (must fix)

| Code | Issue |
|------|-------|
| E001 | Positional arg after keyword — caught by Python parser |
| E002 | f-string in reactive attribute — static, won't update in browser |
| E003 | f-string URL in HTTP action — Python-static, signal value not reactive |
| E004 | Special chars (`:` `/` `[` `]`) in `data_class_*` keyword name — Python parse error |
| E005 | camelCase Signal name — must be snake_case |
| E006 | `f()` reactive helper used without import — NameError at runtime |
| E007 | `data_attr_class` and `data_attr_cls` on same element — different behaviors, likely confusion |

### Warnings (should fix)

| Code | Issue |
|------|-------|
| W001 | `data_show` without flash prevention — element flashes visible before JS loads |
| W002 | Form submit fires `post()` without `is_valid` guard — submits invalid data |
| W003 | Walrus `:=` Signal without outer parentheses — won't register as positional arg |
| W004 | `data_on_scroll` without throttle or `data_on_input` without debounce — performance issue |
| W005 | `@sse` endpoint without `yield signals()` reset — client state not cleaned up |
| W006 | `Icon()` without explicit size — inherits 1em from font-size |
| W007 | `js()` raw JavaScript — verify no user-controlled input in expression |
| W008 | Signal name too short — prefer descriptive snake_case names |

### Info (informational)

| Code | Issue |
|------|-------|
| I001 | Computed Signal detected (expression as initial value, auto-updates) |
| I002 | `elements()` replace-mode — ensure returned element preserves `id` for future targeting |
| I003 | `delete()` HTTP action — ensure user confirmation UX exists |
| I004 | `_ref_only=True` Signal — correctly excluded from `data-signals` HTML output |

---

## Contributing

Issues and PRs welcome.

For new checker rules, include:
- The bug it prevents (real example)
- `GOT:` example of wrong code
- `FIX:` example of corrected code

For skill improvements, test with at least one LLM agent before submitting.
