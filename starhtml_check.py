#!/usr/bin/env python3
"""
starhtml-check — Static analyzer for StarHTML code.
Designed for LLM tool-call loops: minimal tokens, maximum signal.

Usage:
    python starhtml_check.py <file.py>
    python starhtml_check.py --code "..."
    python starhtml_check.py --fix <file.py>
    python starhtml_check.py --summary <file.py>
    python starhtml_check.py --help-llm
"""

import ast
import re
import sys
import argparse
import textwrap
from dataclasses import dataclass, field
from typing import Literal, Optional

HELP_LLM = textwrap.dedent("""
    # StarHTML Checker — LLM Integration Guide

    ## COMMANDS

        python starhtml_check.py <file.py>      # full analysis
        python starhtml_check.py --summary f.py # compact output (fewer tokens)
        python starhtml_check.py --fix f.py     # auto-fix safe issues
        python starhtml_check.py --code "..."   # analyze inline snippet
        python starhtml_check.py --help-llm     # this guide

    ## LLM WORKFLOW

    1. **Write** — Generate StarHTML component
    2. **Check** — Run: `python starhtml_check.py file.py`
    3. **Fix ERRORs** — Address all ERROR-level issues first
    4. **Re-run** — Repeat until no errors, then fix WARNINGs

    ## OUTPUT FORMAT

    - **ERRORS** — must fix, will break runtime or reactivity
    - **WARNINGS** — should fix, may cause subtle bugs or UX issues
    - **INFO** — informational, review if unexpected
    - **SUMMARY** — signal inventory + total counts

    ## ERROR CODES (must fix)

    - **E001** — positional arg after keyword → caught by Python parser
      GOT:  Div(cls="container", "Hello")
      FIX:  Div("Hello", cls="container")
      Note: This is a Python SyntaxError — your editor/IDE should catch it

    - **E002** — f-string in reactive attribute → static, won't update in browser
      GOT:  data_text=f"Count: {counter}"
      FIX:  data_text="Count: " + counter
            data_text=f("Count: {c}", c=counter)  # for 3+ signals

    - **E003** — f-string URL in HTTP action → Python-static, signal value not reactive
      GOT:  data_on_click=get(f"/api/{item_id}")
      FIX:  data_on_click=get("/api/item", id=item_id_sig)

    - **E004** — special chars (`:` `/` `[` `]`) in `data_class_*` keyword name → Python parse error
      GOT:  data_class_hover:bg-blue=sig
      FIX:  data_attr_class=sig.if_("hover:bg-blue-500", "")

    - **E005** — camelCase Signal name → must be snake_case
      GOT:  Signal("myCounter", 0)
      FIX:  Signal("my_counter", 0)

    - **E006** — `f()` helper used without import → NameError at runtime
      GOT:  (uses f() but no import)
      FIX:  from starhtml.datastar import f

    - **E007** — `data_attr_class` and `data_attr_cls` on same element → different behaviors
      GOT:  Div(data_attr_class=..., data_attr_cls=...)
      FIX:  Use only one (data_attr_class replaces, data_attr_cls adds)

    ## WARNING CODES (should fix)

    - **W001** — `data_show` without flash prevention → element flashes visible before JS loads
      GOT:  Div("content", data_show=is_open)
      FIX:  Div("content", style="display:none", data_show=is_open)

    - **W002** — form submit fires `post()` without `is_valid` guard → submits invalid data
      GOT:  data_on_submit=(post("/api/save"), {"prevent": True})
      FIX:  data_on_submit=(is_valid.then(post("/api/save")), {"prevent": True})

    - **W003** — walrus `:=` Signal without outer parentheses → won't register as positional arg
      GOT:  name := Signal("name", "")
      FIX:  (name := Signal("name", ""))

    - **W004** — `data_on_scroll` without throttle or `data_on_input` without debounce → performance
      GOT:  data_on_scroll=handler
      FIX:  data_on_scroll=(handler, {"throttle": 16})

    - **W005** — `@sse` endpoint without `yield signals()` reset → client state not cleaned up
      GOT:  @sse def fn(): yield elements(...)
      FIX:  @sse def fn(): yield elements(...); yield signals(...)

    - **W006** — `Icon()` without explicit size → inherits 1em from font-size
      GOT:  Icon("lucide:home")
      FIX:  Icon("lucide:home", size=24)

    - **W007** — `js()` raw JavaScript → verify no user-controlled input in expression
      GOT:  js("doSomething(" + user_input + ")")
      FIX:  (item := Signal("item", user_input)); js("doSomething($item)")

    - **W008** — Signal name too short → prefer descriptive snake_case names
      GOT:  Signal("x", 0)
      FIX:  Signal("counter", 0)

    - **W012** — Signal with empty name → use descriptive snake_case names
      GOT:  Signal("", 0)
      FIX:  Signal("counter", 0)

    ## INFO CODES (informational)

    - **I001** — Computed Signal detected (expression as initial value, auto-updates)
    - **I002** — `elements()` replace-mode → ensure returned element preserves `id` for future targeting
    - **I003** — `delete()` HTTP action → ensure user confirmation UX exists
    - **I004** — `_ref_only=True` Signal → correctly excluded from `data-signals` HTML output
    - **I005** — f-string in `elements()` selector — verify selector is static or use signal concatenation

    ## STARHTML RULES (5 non-negotiable)

    - **R1** — No f-strings in reactive attributes (become static)
    - **R2** — `data_show` always needs flash prevention
    - **R3** — Positional arguments BEFORE keyword arguments
    - **R4** — Signal names must be snake_case
    - **R5** — Walrus `:=` must be wrapped in outer parentheses
""")


@dataclass
class Issue:
    level: Literal["ERROR", "WARNING", "INFO"]
    line: int
    code: str
    message: str
    original: str = ""
    fix: str = ""

    def __str__(self):
        lines = [f"  L{self.line} [{self.code}] {self.message}"]
        if self.original:
            lines.append(f"    GOT:  {self.original.strip()}")
        if self.fix:
            fix_lines = self.fix.strip().split("\n")
            for i, fl in enumerate(fix_lines):
                prefix = "    FIX:  " if i == 0 else "          "
                lines.append(prefix + fl)
        return "\n".join(lines)


REACTIVE_FSTRING_ATTRS = {
    "data_text", "data_html", "data_value", "data_href", "data_src",
    "data_style_left", "data_style_top", "data_style_width", "data_style_height",
    "data_style_opacity", "data_style_transform", "data_style_background",
}

REACTIVE_PREFIXES = ("data_on_", "data_class_", "data_style_", "data_attr_", "data_bind")

HTTP_ACTIONS = {"get", "post", "put", "patch", "delete"}

TAILWIND_SIZE_PATTERN = re.compile(r"(size-|w-|h-)(\d+|\d+/\d+|full|screen|min|max|px|auto|fit)")


class StarHTMLAnalyzer(ast.NodeVisitor):
    def __init__(self, source: str):
        self.lines = source.splitlines()
        self.issues: list[Issue] = []
        self.signals: list[str] = []
        self.events: list[str] = []
        self.reactive_attrs: list[str] = []
        self._seen_signals: set[str] = set()
        self._has_f_import = False
        self._uses_f_helper: list[int] = []
        self._sse_functions: list[str] = []
        self._sse_has_yield_signals: set[str] = set()
        self._current_func: str = ""

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "starhtml.datastar":
            for alias in node.names:
                if alias.name == "f":
                    self._has_f_import = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._current_func = node.name
        for decorator in node.decorator_list:
            is_sse = False
            # Handle @sse, @app.sse, and aliased imports
            if isinstance(decorator, ast.Name) and decorator.id == "sse":
                is_sse = True
            elif isinstance(decorator, ast.Attribute) and decorator.attr == "sse":
                is_sse = True  # Handles @app.sse, @starhtml.sse, etc.
            if is_sse:
                self._sse_functions.append((node.name, node.lineno))
        self.generic_visit(node)
        self._current_func = ""

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # E001: positional arg after keyword — SyntaxError
        # Note: Python's parser catches this, but we document it for completeness
        # The AST won't even be generated if this error exists in the source

        # E002: f-string in reactive attribute
        for kw in node.keywords:
            if kw.arg:
                arg_name = kw.arg
                is_reactive = (arg_name in REACTIVE_FSTRING_ATTRS or
                               any(arg_name.startswith(p) for p in REACTIVE_PREFIXES))
                if is_reactive and isinstance(kw.value, ast.JoinedStr):
                    self.issues.append(Issue(
                        level="ERROR",
                        line=kw.lineno,
                        code="E002",
                        message="f-string in reactive attribute — static, won't update in browser",
                        original=self._get_line(kw.lineno),
                        fix='Use + operator: "Label: " + signal\n'
                            'Or f() helper: f("Label: {s}", s=signal) for 3+ signals'
                    ))

        # E003: f-string URL in HTTP action
        if func_name in HTTP_ACTIONS:
            if node.args and isinstance(node.args[0], ast.JoinedStr):
                self.issues.append(Issue(
                    level="ERROR",
                    line=node.lineno,
                    code="E003",
                    message="f-string URL in HTTP action — Python-static, signal value not reactive",
                    original=self._get_line(node.lineno),
                    fix='Pass signal as parameter: get("/api/item", id=item_id_sig)'
                ))

        # E004: special chars in data_class_* keyword name
        for kw in node.keywords:
            if kw.arg and kw.arg.startswith("data_class_"):
                suffix = kw.arg[len("data_class_"):]
                if any(c in suffix for c in ":/[\\]"):
                    self.issues.append(Issue(
                        level="ERROR",
                        line=kw.lineno,
                        code="E004",
                        message=f"special chars in `data_class_*` keyword name — Python parse error",
                        original=self._get_line(kw.lineno),
                        fix='Use data_attr_class: data_attr_class=sig.if_("hover:bg-blue-500", "")'
                    ))

        # E007: data_attr_class and data_attr_cls on same element
        kw_args = {kw.arg for kw in node.keywords if kw.arg}
        if "data_attr_class" in kw_args and "data_attr_cls" in kw_args:
            self.issues.append(Issue(
                level="ERROR",
                line=node.lineno,
                code="E007",
                message="`data_attr_class` and `data_attr_cls` on same element — different behaviors",
                original=self._get_line(node.lineno),
                fix="Use only one: data_attr_class replaces, data_attr_cls adds to base cls="
            ))

        # W001: data_show without flash prevention
        has_data_show = any(kw.arg == "data_show" for kw in node.keywords)
        if has_data_show:
            has_flash_prevention = False
            for kw in node.keywords:
                if kw.arg == "style" and isinstance(kw.value, ast.Constant):
                    if "display" in str(kw.value.value).lower():
                        has_flash_prevention = True
                if kw.arg == "data_style_display" and isinstance(kw.value, ast.Constant):
                    if str(kw.value.value).lower() == "none":
                        has_flash_prevention = True
                if kw.arg == "cls" and isinstance(kw.value, ast.Constant):
                    if "hidden" in str(kw.value.value).lower():
                        has_flash_prevention = True
                if kw.arg == "data_class_hidden":
                    has_flash_prevention = True
                if kw.arg == "data_style_opacity":
                    has_flash_prevention = True
            if not has_flash_prevention:
                # Check if it's an input-like element
                is_input_like = func_name in {"Input", "Form", "Select", "Textarea", "Script"}
                if not is_input_like:
                    self.issues.append(Issue(
                        level="WARNING",
                        line=node.lineno,
                        code="W001",
                        message="`data_show` without flash prevention — element flashes visible before JS loads",
                        original=self._get_line(node.lineno),
                        fix='Add style="display:none": Div("content", style="display:none", data_show=is_open)'
                    ))

        # W004: data_on_scroll without throttle or data_on_input without debounce
        for kw in node.keywords:
            if kw.arg == "data_on_scroll":
                has_throttle = self._has_modifier(kw.value, "throttle")
                if not has_throttle:
                    self.issues.append(Issue(
                        level="WARNING",
                        line=kw.lineno,
                        code="W004",
                        message="`data_on_scroll` without throttle — performance issue",
                        original=self._get_line(kw.lineno),
                        fix='Add throttle: data_on_scroll=(handler, {"throttle": 16})'
                    ))
            if kw.arg == "data_on_input":
                has_debounce = self._has_modifier(kw.value, "debounce")
                if not has_debounce:
                    self.issues.append(Issue(
                        level="WARNING",
                        line=kw.lineno,
                        code="W004",
                        message="`data_on_input` without debounce — performance issue",
                        original=self._get_line(kw.lineno),
                        fix='Add debounce: data_on_input=(handler, {"debounce": 300})'
                    ))

        # W006: Icon() without explicit size
        if func_name == "Icon":
            has_size = False
            for kw in node.keywords:
                if kw.arg in ("size", "width", "height"):
                    has_size = True
                if kw.arg == "cls" and isinstance(kw.value, ast.Constant):
                    cls_val = str(kw.value.value)
                    if TAILWIND_SIZE_PATTERN.search(cls_val):
                        has_size = True
            if not has_size:
                self.issues.append(Issue(
                    level="WARNING",
                    line=node.lineno,
                    code="W006",
                    message="`Icon()` without explicit size — inherits 1em from font-size",
                    original=self._get_line(node.lineno),
                    fix='Add size: Icon("lucide:home", size=24)'
                ))

        # W007: js() raw JavaScript
        if func_name == "js":
            self.issues.append(Issue(
                level="WARNING",
                line=node.lineno,
                code="W007",
                message="`js()` raw JavaScript — verify no user-controlled input in expression",
                original=self._get_line(node.lineno),
                fix="Use signal references: (item := Signal('item', val)); js('doSomething($item)')"
            ))

        # I001: Computed Signal
        if func_name == "Signal":
            if len(node.args) >= 2:
                second_arg = node.args[1]
                is_literal = isinstance(second_arg, (ast.Constant, ast.List, ast.Dict, ast.Set, ast.Tuple))
                if not is_literal:
                    self.issues.append(Issue(
                        level="INFO",
                        line=node.lineno,
                        code="I001",
                        message="Computed Signal detected (expression as initial value, auto-updates)",
                        original=self._get_line(node.lineno)
                    ))
            # I004: _ref_only=True
            for kw in node.keywords:
                if kw.arg == "_ref_only" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.issues.append(Issue(
                        level="INFO",
                        line=node.lineno,
                        code="I004",
                        message="`_ref_only=True` Signal — correctly excluded from `data-signals` HTML output",
                        original=self._get_line(node.lineno)
                    ))

        # I003: delete() HTTP action
        if func_name == "delete":
            self.issues.append(Issue(
                level="INFO",
                line=node.lineno,
                code="I003",
                message="`delete()` HTTP action — ensure user confirmation UX exists",
                original=self._get_line(node.lineno)
            ))

        # W009: f-string in elements() selector
        if func_name == "elements":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.JoinedStr):
                self.issues.append(Issue(
                    level="INFO",
                    line=node.lineno,
                    code="I005",
                    message="f-string in elements() selector — verify selector is static or use signal concatenation",
                    original=self._get_line(node.lineno),
                    fix='If dynamic: elements(content, "#target-" + id_sig)\nIf static: elements(content, "#todo-123")  # OK'
                ))

        # Track f() usage
        if func_name == "f":
            self._uses_f_helper.append(node.lineno)

        # Track SSE yield signals
        if func_name == "signals" and self._current_func:
            # Check if current function is an SSE function
            for sse_name, _ in self._sse_functions:
                if sse_name == self._current_func:
                    self._sse_has_yield_signals.add(self._current_func)
                    break

        # Collect events and reactive attrs
        for kw in node.keywords:
            if kw.arg:
                if kw.arg.startswith("data_on_"):
                    self.events.append(f"{kw.arg}(L{kw.lineno})")
                elif kw.arg.startswith("data_"):
                    self.reactive_attrs.append(kw.arg)

        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr):
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "Signal":
                if isinstance(node.target, ast.Name):
                    sig_name = node.target.id
                    if sig_name not in self._seen_signals:
                        self.signals.append(sig_name)
                        self._seen_signals.add(sig_name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "Signal":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        sig_name = target.id
                        if sig_name not in self._seen_signals:
                            self.signals.append(sig_name)
                            self._seen_signals.add(sig_name)
        self.generic_visit(node)

    def _get_line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1]
        return ""

    def _has_modifier(self, value: ast.AST, modifier: str) -> bool:
        """Check if a value has a modifier (throttle/debounce)."""
        if isinstance(value, ast.Tuple) and len(value.elts) >= 2:
            second = value.elts[1]
            if isinstance(second, ast.Dict):
                for key in second.keys:
                    if isinstance(key, ast.Constant) and key.value == modifier:
                        return True
            if isinstance(second, ast.Call):
                if isinstance(second.func, ast.Name) and second.func.id == "dict":
                    for kw in second.keywords:
                        if kw.arg == modifier:
                            return True
        return False


def check_regex(source: str, issues: list[Issue], lines: list[str]) -> None:
    """Regex-based checks that complement AST analysis."""

    # E005: camelCase Signal name
    signal_name_pattern = re.compile(r'Signal\s*\(\s*["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']')
    for i, line in enumerate(lines, 1):
        match = signal_name_pattern.search(line)
        if match:
            name = match.group(1)
            if re.search(r"[a-z][A-Z]", name):
                snake_case = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).lower()
                issues.append(Issue(
                    level="ERROR",
                    line=i,
                    code="E005",
                    message="camelCase Signal name — must be snake_case",
                    original=line.strip(),
                    fix=f'Rename to snake_case: Signal("{snake_case}", ...)'
                ))

    # W012: Empty Signal name
    empty_signal_pattern = re.compile(r'Signal\s*\(\s*["\']["\']')
    for i, line in enumerate(lines, 1):
        if empty_signal_pattern.search(line):
            issues.append(Issue(
                level="WARNING",
                line=i,
                code="W012",
                message="Signal with empty name — use descriptive snake_case names",
                original=line.strip(),
                fix='Signal("counter", 0) instead of Signal("", 0)'
            ))

    # W003: walrus := without outer parens
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if ":= Signal(" in line and not stripped.startswith("("):
            issues.append(Issue(
                level="WARNING",
                line=i,
                code="W003",
                message="walrus `:=` Signal without outer parentheses — won't register as positional arg",
                original=line.strip(),
                fix="Wrap in parens: (name := Signal(\"name\", \"\"))"
            ))

    # W002: form submit without is_valid guard
    for i, line in enumerate(lines, 1):
        if "data_on_submit" in line and "post(" in line:
            has_guard = any(x in line for x in ["is_valid", ".then(", "if_("])
            if not has_guard:
                issues.append(Issue(
                    level="WARNING",
                    line=i,
                    code="W002",
                    message="form submit fires `post()` without `is_valid` guard — submits invalid data",
                    original=line.strip(),
                    fix="Add guard: is_valid.then(post(\"/api/save\"))"
                ))

    # W008: Signal name too short
    short_signal_pattern = re.compile(r'Signal\s*\(\s*["\']([a-z_]{1,2})["\']')
    for i, line in enumerate(lines, 1):
        match = short_signal_pattern.search(line)
        if match:
            name = match.group(1)
            # Count non-underscore chars
            useful_chars = len([c for c in name if c != "_"])
            if useful_chars <= 1:
                issues.append(Issue(
                    level="WARNING",
                    line=i,
                    code="W008",
                    message="Signal name too short — prefer descriptive snake_case names",
                    original=line.strip(),
                    fix='Use descriptive name: Signal("counter", 0) instead of Signal("x", 0)'
                ))

    # I002: elements() replace-mode
    for i, line in enumerate(lines, 1):
        if "elements(" in line:
            has_append_prepend = any(x in line for x in ["\"append\"", "\"prepend\"", "'append'", "'prepend'"])
            if not has_append_prepend:
                issues.append(Issue(
                    level="INFO",
                    line=i,
                    code="I002",
                    message="`elements()` replace-mode — ensure returned element preserves `id` for future targeting",
                    original=line.strip()
                ))


def check_post(analyzer: StarHTMLAnalyzer, issues: list[Issue]) -> None:
    """Post-AST checks that require full context."""

    # E006: f() used without import
    if analyzer._uses_f_helper and not analyzer._has_f_import:
        for lineno in analyzer._uses_f_helper:
            issues.append(Issue(
                level="ERROR",
                line=lineno,
                code="E006",
                message="`f()` helper used without import — NameError at runtime",
                original=analyzer._get_line(lineno),
                fix="Add import: from starhtml.datastar import f"
            ))

    # W005: @sse function without yield signals (function-level with line number)
    for func_name, lineno in analyzer._sse_functions:
        if func_name not in analyzer._sse_has_yield_signals:
            issues.append(Issue(
                level="WARNING",
                line=lineno,
                code="W005",
                message=f"`@sse` function `{func_name}` missing `yield signals()` reset — client state not cleaned up",
                original=f"def {func_name}(): ...",
                fix="Add at end: yield signals(is_sending=False, message=\"\")"
            ))


def auto_fix(source: str) -> str:
    """Apply safe automatic fixes."""
    lines = source.splitlines()
    fixed_lines = []

    for line in lines:
        stripped = line.lstrip()
        # W003: wrap walrus := in parens
        if re.match(r"^\w+\s*:=\s*Signal\s*\(", stripped) and not stripped.startswith("("):
            indent = line[:len(line) - len(stripped)]
            fixed_lines.append(indent + "(" + stripped + ")")
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def format_report(issues: list[Issue], analyzer: StarHTMLAnalyzer, filename: str, summary_only: bool = False) -> str:
    """Format the analysis report."""
    errors = [i for i in issues if i.level == "ERROR"]
    warnings = [i for i in issues if i.level == "WARNING"]
    infos = [i for i in issues if i.level == "INFO"]

    lines = [f"── starhtml-check: {filename} ──"]

    if not summary_only:
        if errors:
            lines.append(f"\nERRORS ({len(errors)}):")
            for issue in errors:
                lines.append(str(issue))

        if warnings:
            lines.append(f"\nWARNINGS ({len(warnings)}):")
            for issue in warnings:
                lines.append(str(issue))

        if infos:
            lines.append(f"\nINFO ({len(infos)}):")
            for issue in infos:
                lines.append(str(issue))

    # Summary
    lines.append("\nSUMMARY:")
    signals_str = ", ".join(analyzer.signals[:10])
    if len(analyzer.signals) > 10:
        signals_str += f" ... (+{len(analyzer.signals) - 10})"
    lines.append(f"  SIGNALS  : {signals_str if analyzer.signals else '(none)'}")

    events_str = ", ".join(analyzer.events[:5])
    if len(analyzer.events) > 5:
        events_str += f" ... (+{len(analyzer.events) - 5})"
    lines.append(f"  EVENTS   : {events_str if analyzer.events else '(none)'}")

    reactive_str = ", ".join(list(set(analyzer.reactive_attrs))[:10])
    lines.append(f"  REACTIVE : {reactive_str if analyzer.reactive_attrs else '(none)'}")

    error_word = "error" if len(errors) == 1 else "errors"
    warning_word = "warning" if len(warnings) == 1 else "warnings"
    lines.append(f"  ISSUES   : {len(errors)} {error_word}, {len(warnings)} {warning_word}")

    if not errors and not warnings:
        lines.append("\n  ✓ No issues found")
    elif summary_only:
        lines.append(f"\n  ✗ Fix {len(errors)} {error_word} before proceeding")

    return "\n".join(lines)


def analyze(source: str, filename: str = "<stdin>", summary_only: bool = False) -> str:
    """Run full analysis on source code."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"── starhtml-check: {filename} ──\n\nSYNTAX ERROR at line {e.lineno}:\n  {e.text.strip() if e.text else ''}\n  {' ' * (e.offset or 0)}^\n  {e.msg}"

    analyzer = StarHTMLAnalyzer(source)
    analyzer.visit(tree)

    issues = analyzer.issues
    lines = source.splitlines()
    check_regex(source, issues, lines)
    check_post(analyzer, issues)

    # Deduplicate by (line, code, message[:40])
    seen = set()
    unique_issues = []
    for issue in issues:
        key = (issue.line, issue.code, issue.message[:40])
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    # Sort by line number
    unique_issues.sort(key=lambda i: (i.line != 0, i.line))

    return format_report(unique_issues, analyzer, filename, summary_only)


def main():
    parser = argparse.ArgumentParser(
        description="starhtml-check — Static analyzer for StarHTML code"
    )
    parser.add_argument("file", nargs="?", help="File to analyze")
    parser.add_argument("--code", help="Analyze inline code snippet")
    parser.add_argument("--fix", metavar="FILE", help="Auto-fix safe issues and print result")
    parser.add_argument("--summary", metavar="FILE", help="Compact output (fewer tokens)")
    parser.add_argument("--help-llm", action="store_true", help="Print LLM integration guide")

    args = parser.parse_args()

    if args.help_llm:
        print(HELP_LLM)
        sys.exit(0)

    if args.fix:
        with open(args.fix, "r") as f:
            source = f.read()
        fixed = auto_fix(source)
        print(fixed)
        # Also run analysis on fixed code
        report = analyze(fixed, args.fix, summary_only=True)
        print("\n" + report, file=sys.stderr)
        sys.exit(0)

    if args.summary:
        with open(args.summary, "r") as f:
            source = f.read()
        report = analyze(source, args.summary, summary_only=True)
        print(report)
        sys.exit(0)

    if args.code:
        report = analyze(args.code, "<code>")
        print(report)
        sys.exit(0)

    if args.file:
        with open(args.file, "r") as f:
            source = f.read()
        report = analyze(source, args.file)
        print(report)
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
