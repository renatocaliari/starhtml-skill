---
name: starhtml
description: Builds reactive web applications with StarHTML, a Python-first framework over Datastar. Use when writing StarHTML components, signals, event handlers, reactive attributes, conditional helpers, CSS classes, computed signals, HTTP actions, SSE endpoints, or plugins (persist, scroll, resize, drag, canvas, motion, markdown, katex, mermaid, split, nodegraph). After generating any StarHTML file, always run starhtml_check.py for validation.
---

# StarHTML — Core Skill

StarHTML = Python objects that compile to reactive Datastar HTML.
**After generating any component, run: `python starhtml_check.py <file>`**

> **Sub-references** (load when needed, same directory as this file):
> `./reference/icons.md` · `./reference/js.md` · `./reference/handlers.md` · `./reference/slots.md` · `./reference/demos.md`
>
> **Official demos** (canonical runnable examples, always from official framework repo):
> `https://raw.githubusercontent.com/banditburai/starHTML/main/web/demos/NN_name.py`

---

## The 5 Rules You Must Not Break

**R1 — No f-strings in reactive attributes (they become static)**

    # WRONG — evaluated once in Python, never updates in browser:
    data_text=f"Count: {counter}"

    # RIGHT — reactive, updates when signal changes:
    data_text="Count: " + counter           # for 1-2 signals
    data_text=f("Count: {c}", c=counter)    # for 3+ signals
    # f() requires: from starhtml.datastar import f

**R2 — data_show always needs flash prevention**

    # WRONG — element flashes visible before JS loads:
    Div("modal content", data_show=is_open)

    # RIGHT — hidden by default, shown reactively:
    Div("modal content", style="display: none", data_show=is_open)
    # Alternatives:
    Div("modal content", cls="hidden", data_class_hidden=~is_open)
    Div("modal content", style="opacity:0;transition:opacity .3s",
        data_style_opacity=is_open.if_("1", "0"))

**R3 — Positional arguments BEFORE keyword arguments**

    # WRONG — SyntaxError at runtime:
    Div(cls="container", "Hello World")

    # RIGHT:
    Div("Hello World", cls="container")

    # Rule: content/signals first, then attributes/handlers

**R4 — Signal names must be snake_case**

    # WRONG — will error at runtime:
    (myCounter := Signal("myCounter", 0))

    # RIGHT:
    (my_counter := Signal("my_counter", 0))

**R5 — Walrus operator := must be wrapped in outer parentheses**

    # WRONG — won't register as positional argument:
    name := Signal("name", "")

    # RIGHT — works as positional argument in HTML elements:
    (name := Signal("name", ""))

---

## Quick Reference

    from starhtml import *

    # Define reactive state — walrus := always in outer ()
    (counter  := Signal("counter", 0))
    (name     := Signal("name", ""))
    (visible  := Signal("visible", True))

    # Reactive attributes
    data_show=visible              # show/hide element
    data_text=name                 # display signal value as text
    data_bind=name                 # two-way binding (inputs)
    data_class_active=visible      # toggle class "active"

    # Events
    data_on_click=counter.add(1)
    data_on_input=(search_fn, {"debounce": 300})    # wait 300ms after typing
    data_on_scroll=(update_fn, {"throttle": 16})    # max 60fps
    data_on_submit=(post("/api/save"), {"prevent": True})

    # Signal operations
    counter.add(1)                 # increment: $counter + 1
    counter.set(0)                 # assign: $counter = 0
    visible.toggle()               # flip boolean: !$visible
    name.upper()                   # string method: $name.toUpperCase()
    count.default(0)               # nullish fallback: $count ?? 0
    count.default(0).clamp(0, 99)  # chain with other methods
    theme.one_of("light","dark")   # constrain to valid values
    sig.then(action)               # conditional execute if truthy

    # Value guards (chainable)
    status.one_of("draft", "published")     # validate enum
    theme.one_of("light", "dark", default="light")

    # Logical operators
    name & email                   # → $name && $email
    ~is_visible                    # → !$is_visible
    all(a, b, c)                   # → !!$a && !!$b && !!$c  (preferred for 3+)
    any(a, b)                      # → $a || $b
    age >= 18                      # → $age >= 18

📄 Runnable example: `01_basic_signals.py` (fetch from demos URL above)

---

## Conditional Helpers

| Helper | Behavior | Use for |
|--------|----------|---------|
| `sig.if_("a", "b")` | exclusive — one result | simple true/false choice |
| `match(sig, a="x", default="z")` | exclusive — maps value to output | value-based mapping |
| `switch([(cond, "msg"), ...], default="")` | exclusive — first match wins | validation chains |
| `collect([(cond, "cls"), ...])` | **inclusive** — ALL true combined | CSS class building |

    # EXCLUSIVE — only one result ever returned
    data_text=status.if_("Active", "Inactive")

    data_attr_class=match(theme,
        light="bg-white text-black",
        dark="bg-gray-900 text-white",
        default="bg-white")

    msg = switch([
        (~name, "Name is required"),
        (name.length < 2, "Name too short"),
        (~email.contains("@"), "Invalid email"),
    ], default="")

    # INCLUSIVE — combines ALL true conditions (correct for CSS classes)
    data_attr_class=collect([
        (True, "btn"),
        (is_primary, "btn-primary"),
        (is_large, "btn-lg"),
        (is_disabled, "opacity-50 cursor-not-allowed"),
    ])

    # WRONG: using collect() for exclusive logic (use switch or if_ instead)
    # WRONG: using switch() to combine CSS classes (use collect instead)

📄 See: `06_control_attributes.py`, `25_advanced_toggle_patterns.py`, `28_datastar_helpers_showcase.py`

---

## Forms and Binding

    Form(
        (name  := Signal("name", "")),
        (email := Signal("email", "")),
        (valid := Signal("valid", all(name, email.contains("@")))),

        Input(type="text",  data_bind=name,  placeholder="Name"),
        Span(
            data_text=switch([(~name, "Required"), (name.length < 2, "Too short")],
                             default=""),
            data_show=~name, style="display:none"
        ),

        Input(type="email", data_bind=email, placeholder="Email"),

        Button("Submit",
               data_attr_disabled=~valid,
               type="submit"),

        data_on_submit=(is_valid.then(post("/api/submit", name=name, email=email)),
                        {"prevent": True})
    )

📄 See: `03_forms_binding.py`

---

## HTTP Actions and SSE

    # HTTP actions — pass signals as params, never f-strings
    data_on_click=get("/api/data")
    data_on_click=post("/api/submit", name=name_sig, email=email_sig)
    data_on_click=is_valid.then(post("/api/submit"))         # conditional
    data_on_click=delete("/api/item")

    # Conditional execution with .then()
    data_on_click=is_confirmed.then(delete("/api/item"))     # only if confirmed
    data_effect=is_form_complete.then(auto_save)             # side effect

    # WRONG — f-string URL is Python-static, signal value not reactive:
    data_on_click=get(f"/api/{item_id}")
    # RIGHT — pass signal as parameter:
    data_on_click=get("/api/item", id=item_id_sig)

    # SSE endpoint — always yield signals() at end to reset client state
    @rt("/send", methods=["POST"])
    @sse
    def send():
        yield signals(is_sending=True)
        yield elements(Div("msg", cls="msg"), "#chat", "append")  # append mode
        yield elements(Div("x", id="chat"), "#chat")              # replace/morph mode
        yield signals(is_sending=False, message="")               # REQUIRED: reset state

    # Hypermedia morph rule: returned element id MUST match the target selector
    @rt("/partial")
    def partial():
        return Div("new content", id="target")   # id="target" matches get("/partial") target

    # SSE Best Practices:
    # 1. Always yield signals() at end to reset client state
    # 2. For replace-mode: preserve id attribute for future targeting
    # 3. Use append/prepend for lists, replace for single elements

📄 See: `02_sse_elements.py`, `04_live_updates.py`, `05_background_tasks.py`, `08_routing_patterns.py`

---

## Styling

### SSR vs Reactive Attributes

| Use Case | SSR Needed? | Pattern |
|----------|-------------|---------|
| Toggle single class | No | `data_class_active=signal` |
| Tailwind special chars | No | `data_attr_class=signal.if_("hover:bg-blue-500", "")` |
| **Show/hide elements** | **Yes** | `style="display: none"` + `data_show=signal` |
| Base + toggle classes | Yes | `cls="base"` + `data_class_*` |
| Base + dynamic classes | Yes | `cls="base"` + `data_attr_cls=reactive` |

### CSS Classes

    # Simple class names (no special characters) → data_class_*
    data_class_active=is_active          # adds/removes class "active"
    data_class_hidden=~is_visible        # adds/removes class "hidden"

    # Special characters (:  /  [  ]) in class names → data_attr_class
    # WRONG — colon in keyword name is a Python parse error:
    data_class_hover:bg-blue=sig
    # RIGHT:
    data_attr_class=is_active.if_("hover:bg-blue-500 focus:ring-2", "")
    data_attr_class=is_loading.if_("bg-blue-500/50", "bg-blue-500")
    data_attr_class=is_custom.if_("bg-[#1da1f2]", "bg-gray-500")

    # data_attr_cls vs data_attr_class — DIFFERENT behaviors:
    # data_attr_cls   = ADDITIVE — merges with base cls= classes
    # data_attr_class = REPLACES — sets the full class attribute

    Button("OK",
           cls="btn",                                        # base classes
           data_attr_cls=is_valid.if_("btn-success", "btn-error"))  # additive

    Button("OK",
           data_attr_class=collect([(True, "btn"),
                                    (is_primary, "btn-primary")]))  # replaces

    # Dictionary syntax for conditional classes
    data_class={"active selected": role == "admin", "disabled": role == "guest"}

### CSS Properties

    # Static CSS (SSR)
    style="background-color: red; font-size: 16px"

    # Reactive CSS properties
    data_style_width=progress + "px"
    data_style_opacity=is_visible.if_("1", "0")

    # CSS template with multiple signals
    from starhtml.datastar import f
    data_attr_style=f("color: {c}; opacity: {o}", c=theme_color, o=opacity)

---

## Computed Signals and Effects

    # Computed Signal — pass expression (not literal) as initial value
    # auto-updates whenever dependencies change
    (first := Signal("first", ""))
    (last  := Signal("last", ""))
    (full_name := Signal("full_name", first + " " + last))       # string computed
    (is_valid  := Signal("is_valid", all(name, email)))          # boolean computed
    (total     := Signal("total", price * quantity))             # math computed

    # data_effect — side effects when signals change (assignments, not return values)
    data_effect=total.set(price * quantity)
    data_effect=[
        total.set(price * quantity),
        tax.set(total * 0.1),
        final.set(total + tax),
    ]

    # Performance: exclude internal-only signals from HTML output
    (cache := Signal("cache", {}, _ref_only=True))

📄 See: `27_nested_property_chaining.py`

---

## Plugins

Each plugin requires import from `starhtml.plugins` and registration with the app.
Fetch the demo file for the exact integration pattern — demo files are complete, runnable examples.

Base URL for all demos: `https://raw.githubusercontent.com/banditburai/starHTML/main/web/demos/`

```python
from starhtml.plugins import persist, scroll, resize, drag, canvas, position, motion, markdown, split

app, rt = star_app()
app.register(persist)   # register each plugin you need
app.register(motion)
```

| Plugin | Demo file(s) | What it does |
|--------|-------------|--------------|
| persist | `09_persist_plugin.py` | Sync signals to localStorage/sessionStorage |
| scroll | `10_scroll_plugin.py` | Track scroll position, page progress |
| resize | `11_resize_plugin.py` | Window/element resize events |
| drag | `12_drag_plugin.py`, `16_freeform_drag.py` | Drag and drop, sortable lists |
| canvas | `17_canvas_plugin.py`, `18_canvas_fullpage.py`, `29_drawing_canvas.py` | Canvas drawing |
| position | `20_position_plugin.py` | Element positioning |
| motion | `23_motion_plugin.py`, `24_motion_svg_plugin.py` | CSS/SVG animations (enter, exit, hover, in_view) |
| markdown | `13_markdown_plugin.py` | Render markdown content via `data_markdown` |
| katex | `14_katex_plugin.py` | Math / LaTeX rendering |
| mermaid | `15_mermaid_plugin.py` | Diagram rendering |
| split | `21_split_responsive.py`, `22_split_universal.py` | Resizable split panes |
| nodegraph | `19_nodegraph_demo.py` | Node graph UI |

Also fetch: `07_todo_list.py` (complete real-world app), `30_debugger_demo.py` (debugger tool)

For full demo index with descriptions: see `./reference/demos.md`
For Icon() component: see `./reference/icons.md`
For js(), f(), regex(): see `./reference/js.md`
For plugins API (persist, scroll, resize, drag, canvas, position, motion): see `./reference/handlers.md`
For slot system: see `./reference/slots.md`

---

## Checker Tool

The checker is a standalone CLI (zero dependencies, stdlib only) that validates StarHTML components.

### Install (one-time)

**Option A — Global install (recommended):**
```bash
# macOS / Linux
curl -L https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py -o /usr/local/bin/starhtml_check && chmod +x /usr/local/bin/starhtml_check

# Or to user local bin (no sudo)
curl -L https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py -o ~/.local/bin/starhtml_check && chmod +x ~/.local/bin/starhtml_check
```

**Option B — Local download (per-project):**
```bash
curl -O https://raw.githubusercontent.com/renatocaliari/starhtml-skill/main/starhtml_check.py
```

### Usage

```bash
# If installed globally:
starhtml_check component.py           # full analysis
starhtml_check --summary f.py         # compact output (fewer tokens)
starhtml_check --fix f.py             # auto-fix safe issues
starhtml_check --help-llm             # full guide + all error codes

# If downloaded locally:
python starhtml_check.py component.py
python starhtml_check.py --summary f.py
python starhtml_check.py --fix f.py
```

**Development Loop:** write → check → fix ERRORs → re-run → ✓ no issues

### Output Levels

- **ERRORS** — must fix, will break runtime or reactivity
- **WARNINGS** — should fix, may cause subtle bugs or UX issues
- **INFO** — informational, review if unexpected
- **SUMMARY** — signal inventory + total counts
